import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class MessageRead(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be blank")
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response from POST /conversations/{id}/messages.
    Includes id for feedback wiring, and provider info for the UI banner.
    """
    id:           uuid.UUID
    role:         str
    content:      str
    provider:     str   # 'groq' or 'ollama'
    was_fallback: bool  # True if Groq was rate-limited and Ollama took over