import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.message import MessageRead


# ─── REQUEST SCHEMAS ─────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    """
    Payload for POST /conversations.
    The user picks which agent they want to chat with — that's all that's
    needed. user_id comes from the JWT via get_current_user, never from
    the request body.
    """
    agent_id: uuid.UUID


# ─── RESPONSE SCHEMAS ────────────────────────────────────────────────────────

class ConversationRead(BaseModel):
    """
    Lightweight conversation summary — used in list views.
    Does not include the full message history to keep the payload small.
    title is None until the first chat turn completes.
    """
    id: uuid.UUID
    agent_id: uuid.UUID
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    """
    Full conversation payload — returned when opening a single conversation.
    Includes the complete message history so the frontend can render the
    chat thread immediately without a second request.

    messages are always in chronological order (created_at ASC) — the CRUD
    layer and ORM relationship both enforce this.
    """
    id: uuid.UUID
    agent_id: uuid.UUID
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = []

    model_config = {"from_attributes": True}