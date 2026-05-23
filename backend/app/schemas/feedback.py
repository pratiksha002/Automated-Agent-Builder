import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class FeedbackSubmit(BaseModel):
    rating: str

    @field_validator("rating")
    @classmethod
    def valid_rating(cls, v: str) -> str:
        if v not in ("up", "down"):
            raise ValueError("rating must be 'up' or 'down'")
        return v


class FeedbackRead(BaseModel):
    id:              uuid.UUID
    message_id:      uuid.UUID
    agent_id:        uuid.UUID
    rating:          str
    suggestion:      Optional[str] = None
    applied:         bool
    created_at:      datetime
    model_config = {"from_attributes": True}


class ApplyRequest(BaseModel):
    """
    Agent owner sends the (possibly edited) suggestion text to apply
    as the new system prompt.
    """
    new_prompt: str


class ApplyResponse(BaseModel):
    agent_id:  uuid.UUID
    new_prompt: str