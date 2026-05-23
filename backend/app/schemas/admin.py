import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ─── Auth ─────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Global Stats ─────────────────────────────────────────────────────────────

class GlobalStats(BaseModel):
    total_users:           int
    banned_users:          int
    total_agents:          int
    platform_agents:       int
    user_agents:           int
    total_messages:        int
    total_conversations:   int
    unreviewed_flags:      int
    total_flags:           int
    messages_24h:          int
    messages_7d:           int
    messages_30d:          int
    most_used_agent:       Optional[str]
    most_used_agent_count: int
    groq_usage_pct:        float
    ollama_usage_pct:      float
    avg_response_ms:       int
    active_users_today:    int


# ─── User Cards ───────────────────────────────────────────────────────────────

class UserCard(BaseModel):
    id:         uuid.UUID
    email:      str
    full_name:  str
    is_active:  bool
    is_banned:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Per-User Stats ───────────────────────────────────────────────────────────

class DailyUsage(BaseModel):
    date:  str
    count: int


class FlagSummary(BaseModel):
    id:          str
    flag_type:   str
    flag_reason: Optional[str]
    is_reviewed: bool
    created_at:  str


class UserStats(BaseModel):
    total_messages:      int
    total_agents:        int
    total_conversations: int
    total_flags:         int
    avg_response_ms:     int
    most_used_agent:     Optional[str]
    daily_usage:         list[DailyUsage]
    recent_flags:        list[FlagSummary]


class UserDetail(BaseModel):
    user:  UserCard
    stats: UserStats


# ─── Flags ────────────────────────────────────────────────────────────────────

class FlagRead(BaseModel):
    id:              uuid.UUID
    message_id:      uuid.UUID
    conversation_id: uuid.UUID
    user_id:         uuid.UUID
    agent_id:        uuid.UUID
    flag_type:       str
    flag_reason:     Optional[str]
    is_reviewed:     bool
    created_at:      datetime

    model_config = {"from_attributes": True}
