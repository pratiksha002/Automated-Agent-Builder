"""
inference_service.py

Responsible for everything that touches the Groq API:
  - Resolving the correct API key per model        (Step 4.1)
  - Trimming history to fit the context window     (Step 4.2)
  - Formatting messages for the Groq SDK           (Step 4.3)
  - Making the Groq API call                       (Step 4.4)
  - Counting tokens                                (Step 4.5)

This file is intentionally stateless — it takes data in, returns data out,
and never touches the database directly. All DB operations live in the
conversation service (conversation_service.py).
"""

import logging
from fastapi import HTTPException, status
from groq import Groq, APIError

from app.core.config import settings
from app.models.message import Message

logger = logging.getLogger(__name__)


# ─── STEP 4.1 — GROQ KEY RESOLVER ────────────────────────────────────────────

# Maps every groq_model_id (as seeded in seed.py) to its corresponding
# env var key from settings. If a new model is added to GROQ_MODELS in
# seed.py, it must also be added here and in config.py.
_GROQ_KEY_MAP: dict[str, str] = {
    "llama-3.3-70b-versatile": settings.GROQ_KEY_LLAMA_70B,
    "llama-3.1-8b-instant":    settings.GROQ_KEY_LLAMA_8B,
    "mixtral-8x7b-32768":      settings.GROQ_KEY_MIXTRAL,
    "gemma2-9b-it":            settings.GROQ_KEY_GEMMA,
}

# Per-model context window sizes (in tokens).
# Used by trim_history() to decide how much history to keep.
# These are conservative limits — slightly under the real Groq limits
# to leave room for the response itself.
_MODEL_CONTEXT_WINDOW: dict[str, int] = {
    "llama-3.3-70b-versatile": 28_000,   # real limit: 32k
    "llama-3.1-8b-instant":    28_000,   # real limit: 32k
    "mixtral-8x7b-32768":      30_000,   # real limit: 32k
    "gemma2-9b-it":            7_500,    # real limit: 8k
}


def get_groq_key(groq_model_id: str) -> str:
    """
    Resolves the Groq API key for a given model ID.

    Each model has its own key so Groq usage can be tracked and rate-limited
    per model independently. If someone adds a model to the DB but forgets
    to add it here, this raises a 500 immediately rather than silently
    sending requests with a wrong key.

    Raises:
        HTTPException 500 — if the model ID is not in the key map.
    """
    key = _GROQ_KEY_MAP.get(groq_model_id)
    if not key:
        logger.error(f"No Groq API key configured for model: {groq_model_id!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{groq_model_id}' is not supported or has no API key configured.",
        )
    return key


def get_model_context_window(groq_model_id: str) -> int:
    """
    Returns the usable context window size (in tokens) for a given model.
    Falls back to a safe conservative default if the model isn't in the map.
    """
    return _MODEL_CONTEXT_WINDOW.get(groq_model_id, 7_500)


# ─── STEP 4.2 — HISTORY TRIMMER ──────────────────────────────────────────────

def trim_history(
    messages: list[Message],
    max_tokens: int,
    system_prompt: str = "",
) -> list[Message]:
    """
    Trims the oldest messages from history until the total token count fits
    within max_tokens, always preserving the most recent exchange.

    Strategy:
      - System prompt tokens are accounted for first (it's always sent).
      - Messages are walked from OLDEST to NEWEST and dropped until the
        remaining list fits in the context window.
      - The most recent user message is ALWAYS kept — dropping it would
        mean sending Groq a conversation with no question to answer.
      - If a message has no token_count (None), it's estimated at 0.
        This is safe: it means we keep slightly more history than is
        precisely accurate, which is better than dropping too aggressively.

    Args:
        messages:      Full ordered history from get_conversation_history()
                       (chronological, ASC).
        max_tokens:    The model's usable context window from
                       get_model_context_window().
        system_prompt: The agent's system prompt string. Its tokens are
                       pre-deducted from max_tokens before any trimming.

    Returns:
        A trimmed list of Message objects in the same chronological order.
        May be the original list unchanged if it already fits.
    """
    if not messages:
        return messages

    # Reserve tokens for the system prompt so we don't crowd it out.
    # count_tokens() isn't available yet at this point in the file,
    # but it will be defined in Step 4.5. For now we use a direct
    # tiktoken call here to keep this function self-contained.
    import tiktoken
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        system_tokens = len(enc.encode(system_prompt)) if system_prompt else 0
    except Exception:
        # If tiktoken fails for any reason, make a conservative estimate.
        system_tokens = len(system_prompt) // 4

    budget = max_tokens - system_tokens

    # Count total tokens in the current history.
    total = sum(m.token_count or 0 for m in messages)

    # Fast path — history already fits, nothing to trim.
    if total <= budget:
        return messages

    # Walk from the front (oldest) and drop messages until we're under budget.
    # We never drop the last message — it's the user's current question.
    trimmed = list(messages)
    while len(trimmed) > 1 and total > budget:
        dropped = trimmed.pop(0)
        total -= dropped.token_count or 0
        logger.debug(
            f"trim_history: dropped message id={dropped.id} "
            f"role={dropped.role} tokens={dropped.token_count} "
            f"remaining_total={total} budget={budget}"
        )

    if total > budget:
        # Even a single message exceeds the budget (extremely long message).
        # Log a warning but send it anyway — truncating mid-message would
        # produce worse results than a slightly oversized payload.
        logger.warning(
            f"trim_history: single message exceeds token budget "
            f"(message_tokens={total}, budget={budget}). Sending anyway."
        )

    return trimmed


# ─── STEP 4.3 — MESSAGE FORMATTER ────────────────────────────────────────────

def format_messages_for_groq(
    system_prompt: str,
    history: list[Message],
) -> list[dict]:
    """
    Converts a system prompt string and a list of DB Message rows into the
    exact payload format the Groq SDK expects.

    Output shape:
        [
            {"role": "system",    "content": "<agent system prompt>"},
            {"role": "user",      "content": "<first user message>"},
            {"role": "assistant", "content": "<first assistant reply>"},
            {"role": "user",      "content": "<second user message>"},
            ...
        ]

    Rules enforced here:
      1. The system message is ALWAYS first and ALWAYS present — Groq requires
         it to be the first element when included.
      2. History is appended in chronological order (the list from
         get_conversation_history() / trim_history() is already ASC).
      3. Empty content is replaced with a single space — Groq rejects
         messages with empty string content with a 400 error.
      4. Roles are passed through as-is from the DB. The CheckConstraint on
         the messages table ensures only 'user'/'assistant'/'system' are
         stored, so no re-validation is needed here.

    Args:
        system_prompt: The agent's system_prompt field. Can be empty string
                       for agents with no custom instructions (rare but valid).
        history:       Ordered list of Message ORM objects — already trimmed
                       by trim_history() before this function is called.

    Returns:
        A list of dicts ready to be passed directly to the Groq SDK's
        `messages` parameter.
    """
    formatted: list[dict] = []

    # System message always goes first.
    # Fall back to a neutral prompt if the agent has none — an empty system
    # message causes some models to behave unpredictably.
    formatted.append({
        "role": "system",
        "content": system_prompt.strip() if system_prompt.strip() else "You are a helpful assistant.",
    })

    # Append each history message in order.
    for message in history:
        content = message.content.strip()

        # Groq rejects empty content with a 400. Replace with a single space
        # as a safe fallback — this should never happen in practice since
        # ChatRequest.content_must_not_be_blank validates on the way in.
        if not content:
            logger.warning(
                f"format_messages_for_groq: empty content on message id={message.id} "
                f"role={message.role}, substituting single space."
            )
            content = " "

        formatted.append({
            "role": message.role,
            "content": content,
        })

    return formatted


# ─── STEP 4.4 — GROQ CALL ────────────────────────────────────────────────────

def call_groq(
    groq_model_id: str,
    messages: list[dict],
) -> str:
    """
    Makes the API call to Groq and returns the assistant's response as a
    plain string.

    Instantiates a fresh Groq client per call using the model-specific API
    key resolved by get_groq_key(). This is intentional — it keeps each
    call fully self-contained and makes key rotation trivial (update the
    env var, restart, done).

    Args:
        groq_model_id: The exact model string, e.g. 'llama-3.3-70b-versatile'.
                       Must match a key in _GROQ_KEY_MAP.
        messages:      The formatted message list from format_messages_for_groq().
                       Must start with a system message.

    Returns:
        The assistant's reply as a plain string, stripped of leading/trailing
        whitespace.

    Raises:
        HTTPException 502 — on any Groq API error (bad key, rate limit,
                            model unavailable, token limit exceeded, etc.)
        HTTPException 500 — on any unexpected error during the call.
    """
    api_key = get_groq_key(groq_model_id)

    # Log the call without the key — safe for production logs.
    logger.info(
        f"call_groq: model={groq_model_id!r} "
        f"messages={len(messages)} turns"
    )

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=groq_model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        response_text = completion.choices[0].message.content

        if not response_text:
            # Groq returned an empty response — rare but possible when the
            # model hits a content filter. Return a safe fallback rather than
            # saving an empty assistant message to the DB.
            logger.warning(
                f"call_groq: empty response from model={groq_model_id!r}, "
                f"finish_reason={completion.choices[0].finish_reason!r}"
            )
            return "I wasn't able to generate a response. Please try again."

        logger.info(
            f"call_groq: success model={groq_model_id!r} "
            f"finish_reason={completion.choices[0].finish_reason!r} "
            f"prompt_tokens={completion.usage.prompt_tokens} "
            f"completion_tokens={completion.usage.completion_tokens}"
        )

        return response_text.strip()

    except APIError as e:
        # Groq SDK raises APIError for all HTTP-level failures:
        # 401 bad key, 429 rate limit, 413 token limit, 503 unavailable, etc.
        logger.error(
            f"call_groq: Groq APIError model={groq_model_id!r} "
            f"status={e.status_code} message={e.message!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API error: {e.message}",
        )

    except Exception as e:
        # Catch-all for network errors, SDK bugs, or anything unexpected.
        logger.error(
            f"call_groq: unexpected error model={groq_model_id!r} "
            f"error={type(e).__name__}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while calling the inference API.",
        )

# ─── STEP 4.5 — TOKEN COUNTER ────────────────────────────────────────────────

# Module-level encoder — loaded once at import time, reused on every call.
# cl100k_base is the encoding used by GPT-4 and is the closest publicly
# available approximation for LLaMA and Mixtral token counts.
# It won't be perfectly accurate for every model, but it's consistent and
# good enough for context window management decisions.
try:
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception as _enc_err:
    logger.warning(
        f"count_tokens: failed to load tiktoken encoder: {_enc_err}. "
        "Falling back to char/4 estimate."
    )
    _encoder = None


def count_tokens(text: str) -> int:
    """
    Returns an approximate token count for a given string.

    Used by handle_chat_turn() to populate message.token_count before
    saving each message to the DB. Those stored counts are what
    trim_history() reads when deciding what to drop.

    Encoding: cl100k_base (tiktoken) — consistent across all models in
    this fleet. Slightly over-counts for LLaMA/Mixtral vs their native
    tokenisers, which means trim_history() will trim a little earlier
    than strictly necessary. That's the safer direction to err.

    Fallback: if tiktoken fails (import error, encoding unavailable),
    falls back to len(text) // 4 — the standard rule-of-thumb approximation
    of ~4 characters per token for English text. Less accurate but never
    crashes.

    Args:
        text: Any string — user message, assistant reply, system prompt.

    Returns:
        Integer token count. Always >= 1 for non-empty strings.
        Returns 0 for empty or whitespace-only input.
    """
    if not text or not text.strip():
        return 0

    if _encoder is not None:
        try:
            return len(_encoder.encode(text))
        except Exception as e:
            logger.warning(
                f"count_tokens: tiktoken encode failed ({e}), "
                "falling back to char/4 estimate."
            )

    # Fallback: character count divided by 4, minimum 1.
    return max(1, len(text) // 4)