"""
conversation_service.py

The orchestrator for a single chat turn. This is the only place in the
codebase where the DB layer and the inference layer meet.

handle_chat_turn() is the single entry point — the chat route calls it
with a conversation ID and a user message string, and gets back the
assistant's response string. Everything else is an implementation detail.

Sequence per turn:
  1. Load conversation + validate it's active
  2. Load agent config (system prompt, model, tools)
  3. Save user message to DB (with token count)
  4. Fetch full conversation history
  5. Trim history to fit the model's context window
  6. Format messages for Groq
  7. Call Groq
  8. Save assistant response to DB (with token count)
  9. Bump conversation.updated_at
  10. Auto-set title on first turn
  11. Return assistant response string
"""

import logging
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.conversation import (
    get_conversation_by_id,
    update_conversation_title,
    touch_conversation,
)
from app.crud.message import (
    add_message,
    get_conversation_history,
    get_last_user_message,
)
from app.services.agent_service import build_agent_config
from app.services.inference_service import (
    get_model_context_window,
    trim_history,
    format_messages_for_groq,
    call_groq,
    count_tokens,
)

logger = logging.getLogger(__name__)

# Maximum characters used when auto-generating a conversation title
# from the first user message. Truncated with an ellipsis if longer.
_TITLE_MAX_CHARS = 60


def _generate_title(text: str) -> str:
    """
    Derives a conversation title from the first user message.
    Strips whitespace, truncates to _TITLE_MAX_CHARS chars, and appends
    an ellipsis if truncated. Keeps it simple — no LLM call for this.
    """
    text = text.strip()
    if len(text) <= _TITLE_MAX_CHARS:
        return text
    return text[:_TITLE_MAX_CHARS].rstrip() + "..."


def handle_chat_turn(
    db: Session,
    conversation_id: uuid.UUID,
    user_message: str,
) -> str:
    """
    Executes one full chat turn: takes a user message, gets an LLM response,
    persists both, and returns the response string.

    This function is deliberately synchronous — Groq's Python SDK is
    synchronous and FastAPI will run this in a thread pool automatically
    when called from an async route with run_in_executor, or directly
    from a sync route. The chat route (Step 4.7) handles this.

    Args:
        db:              Active SQLAlchemy session from get_db().
        conversation_id: The conversation to send the message to.
        user_message:    The raw user input string (already validated
                         non-blank by ChatRequest).

    Returns:
        The assistant's response as a plain string.

    Raises:
        HTTPException 404 — if the conversation doesn't exist or is closed.
        HTTPException 502 — if Groq returns an API error.
        HTTPException 500 — on any unexpected failure.
    """
    # ── 1. Load and validate conversation ────────────────────────────────────
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    logger.info(
        f"handle_chat_turn: start "
        f"conversation_id={conversation_id} "
        f"agent_id={conversation.agent_id}"
    )

    # ── 2. Load agent config ──────────────────────────────────────────────────
    # build_agent_config() raises 404/500 itself if agent is missing or broken.
    agent_config = build_agent_config(db, conversation.agent_id)
    system_prompt  = agent_config["system_prompt"]
    groq_model_id  = agent_config["model"]["groq_model_id"]

    # ── 3. Save user message ──────────────────────────────────────────────────
    user_token_count = count_tokens(user_message)
    user_msg = add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        token_count=user_token_count,
    )
    logger.debug(
        f"handle_chat_turn: saved user message id={user_msg.id} "
        f"tokens={user_token_count}"
    )

    # ── 4. Fetch full history (includes the message we just saved) ────────────
    history = get_conversation_history(db, conversation_id)

    # ── 5. Trim history to fit context window ─────────────────────────────────
    context_window = get_model_context_window(groq_model_id)
    trimmed_history = trim_history(
        messages=history,
        max_tokens=context_window,
        system_prompt=system_prompt,
    )

    if len(trimmed_history) < len(history):
        logger.info(
            f"handle_chat_turn: trimmed history "
            f"from {len(history)} to {len(trimmed_history)} messages "
            f"for model={groq_model_id!r} window={context_window}"
        )

    # ── 6. Format for Groq ────────────────────────────────────────────────────
    formatted_messages = format_messages_for_groq(
        system_prompt=system_prompt,
        history=trimmed_history,
    )

    # ── 7. Call Groq ──────────────────────────────────────────────────────────
    # call_groq() raises HTTPException on any API failure — no try/except
    # needed here, let it propagate to the route handler.
    assistant_response = call_groq(
        groq_model_id=groq_model_id,
        messages=formatted_messages,
    )

    # ── 8. Save assistant response ────────────────────────────────────────────
    assistant_token_count = count_tokens(assistant_response)
    assistant_msg = add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_response,
        token_count=assistant_token_count,
    )
    logger.debug(
        f"handle_chat_turn: saved assistant message id={assistant_msg.id} "
        f"tokens={assistant_token_count}"
    )

    # ── 9. Bump conversation.updated_at ───────────────────────────────────────
    # This keeps the conversation at the top of the user's list after each turn.
    touch_conversation(db, conversation_id)

    # ── 10. Auto-set title on first turn ──────────────────────────────────────
    # Title is null when the conversation is created. We set it exactly once —
    # when the first user message is also the only user message (count == 1).
    # get_last_user_message() returns the FIRST user message by created_at ASC,
    # so checking `id == user_msg.id` tells us this is the opening message.
    if conversation.title is None:
        first_user_msg = get_last_user_message(db, conversation_id)
        if first_user_msg and first_user_msg.id == user_msg.id:
            title = _generate_title(user_message)
            update_conversation_title(db, conversation_id, title)
            logger.info(
                f"handle_chat_turn: set title={title!r} "
                f"for conversation_id={conversation_id}"
            )

    # ── 11. Return assistant response ─────────────────────────────────────────
    logger.info(
        f"handle_chat_turn: complete "
        f"conversation_id={conversation_id} "
        f"response_tokens={assistant_token_count}"
    )
    return assistant_response