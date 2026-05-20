import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.message import MessageRead


class ConversationCreate(BaseModel):
    agent_id: uuid.UUID


class ConversationRead(BaseModel):
    id:               uuid.UUID
    agent_id:         uuid.UUID
    title:            Optional[str] = None
    is_active:        bool
    current_provider: str          # 'groq' or 'ollama' — shown in chat UI
    provider_switched: bool
    created_at:       datetime
    updated_at:       datetime
    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id:               uuid.UUID
    agent_id:         uuid.UUID
    title:            Optional[str] = None
    is_active:        bool
    current_provider: str
    provider_switched: bool
    created_at:       datetime
    updated_at:       datetime
    messages:         list[MessageRead] = []
    model_config = {"from_attributes": True}