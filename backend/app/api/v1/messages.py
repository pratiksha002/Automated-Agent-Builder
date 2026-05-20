import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.conversation import get_conversation_by_id
from app.schemas.message import ChatRequest, ChatResponse
from app.services.conversation_service import handle_chat_turn, switch_provider
from app.core.limiter import limiter

router = APIRouter(prefix="/conversations", tags=["messages"])


def assert_ownership(conv, user_id):
    if conv.user_id != user_id:
        raise HTTPException(403, "You do not have access to this conversation")


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
@limiter.limit(settings.CHAT_RATE_LIMIT)
def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    assert_ownership(conv, current_user.id)

    response, message_id, provider_used, was_fallback = handle_chat_turn(
        db=db, conversation_id=conversation_id, user_message=payload.content,
    )
    return ChatResponse(
        id=message_id, role="assistant", content=response,
        provider=provider_used, was_fallback=was_fallback,
    )


class SwitchReq(BaseModel):
    provider: str


class SwitchResp(BaseModel):
    conversation_id: uuid.UUID
    provider: str
    message: str


@router.post("/{conversation_id}/switch-provider", response_model=SwitchResp)
def switch_conversation_provider(
    conversation_id: uuid.UUID,
    payload: SwitchReq,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually switch provider for a conversation.
    All previous history is shared with the new provider — no context lost.
    """
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    assert_ownership(conv, current_user.id)

    updated = switch_provider(db, conversation_id, payload.provider)
    label = "Ollama (local)" if payload.provider == "ollama" else "Groq (cloud)"
    return SwitchResp(
        conversation_id=conversation_id,
        provider=updated.current_provider,
        message=f"Switched to {label}. Your conversation history is fully preserved.",
    )