import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ─── TOOL ────────────────────────────────────────────────────────────────────

class AgentToolConfig(BaseModel):
    tool_name: str
    tool_config: Optional[dict] = None


class AgentToolRead(BaseModel):
    id: uuid.UUID
    tool_name: str
    tool_config: Optional[dict] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ─── AGENT ───────────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model_id: uuid.UUID
    tools: list[AgentToolConfig] = []


class AgentUpdate(BaseModel):
    """
    All fields optional — only provided fields are written to the DB.
    Uses model_dump(exclude_unset=True) in the CRUD layer.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[uuid.UUID] = None
    tools: Optional[list[AgentToolConfig]] = None


class AgentRead(BaseModel):
    """
    Full agent detail — returned when opening a single agent.
    Includes system_prompt, model info, and full tool list.
    """
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    system_prompt: str
    model_id: uuid.UUID
    is_platform_agent: bool
    is_public: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tools: list[AgentToolRead] = []

    model_config = {"from_attributes": True}


class AgentListItem(BaseModel):
    """
    Lightweight agent representation for dashboard listing.
    Excludes system_prompt — no need to send it for card display.
    """
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    model_id: uuid.UUID
    is_platform_agent: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}