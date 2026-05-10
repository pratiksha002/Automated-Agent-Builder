import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ─── RESPONSE SCHEMAS ────────────────────────────────────────────────────────

class MessageRead(BaseModel):
    """
    Single message as returned by the API.
    token_count is intentionally excluded — it's an internal implementation
    detail for context window management, not useful to the frontend.
    """
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── REQUEST SCHEMAS ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """
    Payload for POST /conversations/{conversation_id}/messages.
    Just the user's message text — everything else (role, conversation_id,
    user identity) is derived from the path param and JWT.
    """
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be blank")
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response from POST /conversations/{conversation_id}/messages.
    Returns the assistant's reply so the frontend can render it immediately,
    without needing a second GET to fetch the updated history.
    """
    role: str
    content: str