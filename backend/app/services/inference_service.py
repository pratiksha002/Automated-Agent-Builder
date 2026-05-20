"""
inference_service.py

Handles all LLM inference — both Groq (cloud) and Ollama (local).

Provider routing:
  - call_groq()   → Groq cloud API via groq SDK
  - call_ollama() → local Ollama via HTTP API (no SDK needed)
  - call_llm()    → unified entry point; routes by provider string

Rate-limit detection:
  - is_groq_rate_limited(err) → True when Groq returns HTTP 429
  - conversation_service uses this to trigger automatic fallback

Context sharing:
  - format_messages_for_llm() produces the same message list format
    for both providers — Ollama's /api/chat uses the same
    OpenAI-compatible role/content structure as Groq's SDK.
    Full conversation history is always passed, so switching
    providers mid-conversation loses no context.
"""

import logging
import requests
from typing import Optional

from fastapi import HTTPException, status
from groq import Groq, APIError, RateLimitError

from app.core.config import settings
from app.models.message import Message

logger = logging.getLogger(__name__)


# ─── Groq key map ────────────────────────────────────────────────────────────

_GROQ_KEY_MAP: dict[str, str] = {
    "llama-3.3-70b-versatile": settings.GROQ_KEY_LLAMA_70B,
    "llama-3.1-8b-instant":    settings.GROQ_KEY_LLAMA_8B,
    "mixtral-8x7b-32768":      settings.GROQ_KEY_MIXTRAL,
    "gemma2-9b-it":            settings.GROQ_KEY_GEMMA,
}

_GROQ_CONTEXT_WINDOW: dict[str, int] = {
    "llama-3.3-70b-versatile": 28_000,
    "llama-3.1-8b-instant":    28_000,
    "mixtral-8x7b-32768":      30_000,
    "gemma2-9b-it":            7_500,
}

# Ollama context windows (conservative; model-dependent)
_OLLAMA_CONTEXT_WINDOW: dict[str, int] = {
    "llama3.2":    28_000,
    "llama3.1:8b": 28_000,
    "mistral":     28_000,
    "phi3:mini":   14_000,
}


def get_groq_key(groq_model_id: str) -> str:
    key = _GROQ_KEY_MAP.get(groq_model_id)
    if not key:
        logger.error(f"No Groq API key configured for model: {groq_model_id!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{groq_model_id}' has no API key configured.",
        )
    return key


def get_model_context_window(model_id: str, provider: str = "groq") -> int:
    if provider == "ollama":
        return _OLLAMA_CONTEXT_WINDOW.get(model_id, 14_000)
    return _GROQ_CONTEXT_WINDOW.get(model_id, 7_500)


def is_groq_rate_limited(exc: Exception) -> bool:
    """
    Returns True when the exception is a Groq 429 rate-limit error.
    Used by conversation_service to decide whether to fall back to Ollama.
    """
    return isinstance(exc, RateLimitError)


# ─── History trimmer ─────────────────────────────────────────────────────────

def trim_history(
    messages: list[Message],
    max_tokens: int,
    system_prompt: str = "",
) -> list[Message]:
    if not messages:
        return messages

    import tiktoken
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        system_tokens = len(enc.encode(system_prompt)) if system_prompt else 0
    except Exception:
        system_tokens = len(system_prompt) // 4

    budget = max_tokens - system_tokens
    total  = sum(m.token_count or 0 for m in messages)

    if total <= budget:
        return messages

    trimmed = list(messages)
    while len(trimmed) > 1 and total > budget:
        dropped = trimmed.pop(0)
        total  -= dropped.token_count or 0
        logger.debug(f"trim_history: dropped msg id={dropped.id} tokens={dropped.token_count}")

    if total > budget:
        logger.warning(f"trim_history: single message exceeds budget ({total} > {budget})")

    return trimmed


# ─── Message formatter (shared for both providers) ───────────────────────────

def format_messages_for_llm(
    system_prompt: str,
    history: list[Message],
) -> list[dict]:
    """
    Produces the standard role/content message list accepted by both
    Groq (via SDK) and Ollama (/api/chat endpoint).
    Context is fully preserved — all history messages are included.
    """
    formatted: list[dict] = []

    formatted.append({
        "role":    "system",
        "content": system_prompt.strip() if system_prompt.strip() else "You are a helpful assistant.",
    })

    for message in history:
        content = message.content.strip()
        if not content:
            logger.warning(f"format_messages_for_llm: empty content on message id={message.id}")
            content = " "
        formatted.append({"role": message.role, "content": content})

    return formatted


# ─── Groq call ───────────────────────────────────────────────────────────────

def call_groq(
    groq_model_id: str,
    messages: list[dict],
) -> str:
    """
    Calls the Groq cloud API.
    Raises RateLimitError (a subclass of APIError) on 429 so the caller
    can detect it and fall back to Ollama.
    Raises HTTPException 502 on other Groq API errors.
    """
    api_key = get_groq_key(groq_model_id)
    logger.info(f"call_groq: model={groq_model_id!r} messages={len(messages)}")

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
            logger.warning(f"call_groq: empty response model={groq_model_id!r}")
            return "I wasn't able to generate a response. Please try again."

        logger.info(
            f"call_groq: success model={groq_model_id!r} "
            f"prompt_tokens={completion.usage.prompt_tokens} "
            f"completion_tokens={completion.usage.completion_tokens}"
        )
        return response_text.strip()

    except RateLimitError:
        # Re-raise as-is so conversation_service can detect it specifically
        logger.warning(f"call_groq: rate limit hit model={groq_model_id!r}")
        raise

    except APIError as e:
        logger.error(f"call_groq: APIError model={groq_model_id!r} status={e.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API error: {e.message}",
        )

    except Exception as e:
        logger.error(f"call_groq: unexpected error model={groq_model_id!r} {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error calling Groq API.",
        )


# ─── Ollama call ──────────────────────────────────────────────────────────────

def call_ollama(
    ollama_model_id: str,
    messages: list[dict],
) -> str:
    """
    Calls the local Ollama server via its HTTP API.
    Uses /api/chat which accepts the same role/content format as Groq.

    Ollama must be running: `ollama serve`
    The model must be pulled: `ollama pull <ollama_model_id>`

    Raises HTTPException 503 if Ollama is not reachable.
    Raises HTTPException 502 on API-level errors from Ollama.
    """
    if not settings.OLLAMA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not enabled in this deployment.",
        )

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model":    ollama_model_id,
        "messages": messages,
        "stream":   False,
        "options": {
            "temperature": 0.7,
            "num_predict": 1024,
        },
    }

    logger.info(f"call_ollama: model={ollama_model_id!r} url={url} messages={len(messages)}")

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT,
        )

        if resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Ollama model '{ollama_model_id}' not found. "
                    f"Run: ollama pull {ollama_model_id}"
                ),
            )

        if not resp.ok:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama returned {resp.status_code}: {resp.text[:200]}",
            )

        data = resp.json()
        content = data.get("message", {}).get("content", "").strip()

        if not content:
            logger.warning(f"call_ollama: empty response model={ollama_model_id!r}")
            return "I wasn't able to generate a response. Please try again."

        logger.info(
            f"call_ollama: success model={ollama_model_id!r} "
            f"eval_count={data.get('eval_count', '?')}"
        )
        return content

    except HTTPException:
        raise

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Could not connect to Ollama. "
                "Make sure Ollama is running: ollama serve"
            ),
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Ollama timed out after {settings.OLLAMA_TIMEOUT}s. Try a smaller model.",
        )

    except Exception as e:
        logger.error(f"call_ollama: unexpected error {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error calling Ollama.",
        )


# ─── Unified call (routes by provider) ───────────────────────────────────────

def call_llm(
    provider: str,
    model_id: str,
    messages: list[dict],
) -> str:
    """
    Unified LLM call. Routes to Groq or Ollama based on provider.
    This is what conversation_service calls — it never calls
    call_groq / call_ollama directly.

    provider: 'groq' or 'ollama'
    model_id: groq_model_id for Groq, ollama_model_id for Ollama
    """
    if provider == "ollama":
        return call_ollama(model_id, messages)
    elif provider == "groq":
        return call_groq(model_id, messages)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider!r}. Must be 'groq' or 'ollama'.",
        )


# ─── Token counter ────────────────────────────────────────────────────────────

try:
    import tiktoken as _tiktoken
    _encoder = _tiktoken.get_encoding("cl100k_base")
except Exception as _e:
    logger.warning(f"count_tokens: tiktoken unavailable ({_e}), using char/4 fallback")
    _encoder = None


def count_tokens(text: str) -> int:
    if not text or not text.strip():
        return 0
    if _encoder is not None:
        try:
            return len(_encoder.encode(text))
        except Exception:
            pass
    return max(1, len(text) // 4)