"""
conversation_service.py — chat turn orchestrator with Groq→Ollama fallback.
"""
import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.conversation import (
    get_conversation_by_id, update_conversation_title, touch_conversation,
)
from app.crud.message import (
    add_message, get_conversation_history, get_last_user_message,
)
from app.services.agent_service import build_agent_config
from app.services.inference_service import (
    get_model_context_window, trim_history, format_messages_for_llm,
    call_llm, call_ollama, is_groq_rate_limited, count_tokens,
)
from app.models.conversation import Conversation
from app.models.usage_log import UsageLog

logger = logging.getLogger(__name__)
_TITLE_MAX = 60


def _title(text: str) -> str:
    text = text.strip()
    return text if len(text) <= _TITLE_MAX else text[:_TITLE_MAX].rstrip() + "..."


def _get_ollama_fallback(db: Session) -> Optional[tuple[str, str]]:
    from app.models.model import Model
    preference = ["llama3.2", "llama3.1:8b", "mistral", "phi3:mini"]
    for mid in preference:
        m = db.query(Model).filter_by(provider="ollama", ollama_model_id=mid, is_active=True).first()
        if m:
            return ("ollama", m.ollama_model_id)
    m = db.query(Model).filter_by(provider="ollama", is_active=True).first()
    return ("ollama", m.ollama_model_id) if m else None


def _set_provider(db: Session, conv: Conversation, provider: str) -> None:
    conv.current_provider  = provider
    conv.provider_switched = True
    db.commit()
    logger.info(f"provider switched to {provider} conv={conv.id}")


def _log_usage(
    db: Session,
    conv: Conversation,
    provider_used: str,
    user_message: str,
    response: str,
    response_time_ms: int,
) -> None:
    """Write one UsageLog row for this chat turn."""
    try:
        log = UsageLog(
            user_id=conv.user_id,
            agent_id=conv.agent_id,
            conversation_id=conv.id,
            model_id=None,               # optional — can resolve later if needed
            model_provider=provider_used,
            input_tokens=count_tokens(user_message),
            output_tokens=count_tokens(response),
            response_time_ms=response_time_ms,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # Never let logging failure break the chat turn
        logger.warning(f"UsageLog write failed: {e}")
        db.rollback()


def switch_provider(db: Session, conversation_id: uuid.UUID, provider: str) -> Conversation:
    """Manual provider switch from API route."""
    if provider not in ("groq", "ollama"):
        raise HTTPException(422, "provider must be 'groq' or 'ollama'")
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    conv.current_provider  = provider
    conv.provider_switched = (provider == "ollama")
    db.commit()
    db.refresh(conv)
    return conv


def handle_chat_turn(
    db: Session,
    conversation_id: uuid.UUID,
    user_message: str,
) -> tuple[str, uuid.UUID, str, bool]:
    """
    Runs one chat turn. Returns (response, message_id, provider_used, was_fallback).
    was_fallback=True means Groq was rate-limited and Ollama took over automatically.
    """
    # 1. Load conversation
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    current_provider = conv.current_provider   # 'groq' or 'ollama'

    # 2. Load agent config
    cfg = build_agent_config(db, conv.agent_id)
    system_prompt   = cfg["system_prompt"]
    groq_model_id   = cfg["model"].get("groq_model_id")
    ollama_model_id = cfg["model"].get("ollama_model_id")

    active_model_id = groq_model_id if current_provider == "groq" else ollama_model_id

    if not active_model_id and current_provider == "ollama":
        fb = _get_ollama_fallback(db)
        if not fb:
            raise HTTPException(503, "No Ollama models available. Run: ollama pull llama3.2")
        current_provider, active_model_id = fb

    # 3. Save user message
    user_msg = add_message(db, conversation_id, "user", user_message, count_tokens(user_message))

    # 4. Fetch full history
    history = get_conversation_history(db, conversation_id)

    # 5. Trim to context window
    ctx     = get_model_context_window(active_model_id, current_provider)
    trimmed = trim_history(history, ctx, system_prompt)

    # 6. Format
    formatted = format_messages_for_llm(system_prompt, trimmed)

    # 7. Call LLM — track response time for usage logging
    was_fallback  = False
    provider_used = current_provider
    t_start       = time.monotonic()

    try:
        response = call_llm(current_provider, active_model_id, formatted)

    except Exception as exc:
        if is_groq_rate_limited(exc) and current_provider == "groq":
            logger.warning(f"Groq rate limit — falling back to Ollama conv={conversation_id}")

            fb = _get_ollama_fallback(db)
            if not fb:
                raise HTTPException(429,
                    "Groq rate limit reached. No Ollama fallback available. "
                    "Install Ollama (ollama.com) and run: ollama pull llama3.2")

            fb_provider, fb_model = fb
            fb_ctx       = get_model_context_window(fb_model, "ollama")
            fb_history   = trim_history(history, fb_ctx, system_prompt)
            fb_formatted = format_messages_for_llm(system_prompt, fb_history)

            response = call_ollama(fb_model, fb_formatted)

            _set_provider(db, conv, "ollama")
            provider_used = "ollama"
            was_fallback  = True
        else:
            raise

    response_time_ms = int((time.monotonic() - t_start) * 1000)

    # 8. Save assistant response
    asst_msg = add_message(db, conversation_id, "assistant", response, count_tokens(response))

    # 9. Write usage log
    _log_usage(db, conv, provider_used, user_message, response, response_time_ms)

    # 10. Bump updated_at
    touch_conversation(db, conversation_id)

    # 11. Auto-title on first turn
    if conv.title is None:
        first = get_last_user_message(db, conversation_id)
        if first and first.id == user_msg.id:
            update_conversation_title(db, conversation_id, _title(user_message))

    logger.info(f"turn complete conv={conversation_id} provider={provider_used} fallback={was_fallback} time={response_time_ms}ms")
    return response, asst_msg.id, provider_used, was_fallback
