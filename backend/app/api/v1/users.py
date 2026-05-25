"""
api/v1/users.py

User self-service endpoints:
  GET  /users/me/stats    — usage analytics for the profile page
  DELETE /users/me        — soft-delete (deactivate) own account
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.message_feedback import MessageFeedback

router = APIRouter(prefix="/users", tags=["users"])


class UserStats(BaseModel):
    full_name:           str
    email:               str
    member_since:        datetime
    total_agents:        int
    total_conversations: int
    total_messages:      int
    groq_messages:       int
    ollama_messages:     int
    most_used_provider:  str
    feedback_given:      int
    thumbs_up:           int
    thumbs_down:         int
    satisfaction_score:  Optional[int]
    prompts_improved:    int


@router.get("/me/stats", response_model=UserStats)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full usage analytics for the currently logged-in user.
    Used by the profile page to render all dashboard widgets.
    """
    uid = current_user.id

    # Agent count
    total_agents = db.query(Agent).filter(
        Agent.owner_user_id == uid,
        Agent.is_active == True,
    ).count()

    # Conversation count
    convs = db.query(Conversation).filter(
        Conversation.user_id == uid,
    ).all()
    total_conversations = len(convs)

    conv_ids = [c.id for c in convs]

    # Message count + provider split
    total_messages  = 0
    groq_messages   = 0
    ollama_messages = 0

    if conv_ids:
        # Count all user messages across conversations
        total_messages = db.query(Message).filter(
            Message.conversation_id.in_(conv_ids),
            Message.role == "user",
        ).count()

        # Provider split from conversation.current_provider
        for c in convs:
            prov = getattr(c, 'current_provider', 'groq') or 'groq'
            if prov == 'ollama':
                ollama_messages += 1
            else:
                groq_messages += 1

    most_used = "Ollama" if ollama_messages > groq_messages else "Groq"

    # Feedback stats
    feedback_rows = []
    if conv_ids:
        # Get all agent IDs owned by user
        agent_ids = [a.id for a in db.query(Agent).filter(
            Agent.owner_user_id == uid).all()]
        if agent_ids:
            feedback_rows = db.query(MessageFeedback).filter(
                MessageFeedback.agent_id.in_(agent_ids)
            ).all()

    thumbs_up       = sum(1 for f in feedback_rows if f.rating == "up")
    thumbs_down     = sum(1 for f in feedback_rows if f.rating == "down")
    feedback_given  = len(feedback_rows)
    prompts_improved = sum(1 for f in feedback_rows if f.applied)
    total_fb = thumbs_up + thumbs_down
    satisfaction = round((thumbs_up / total_fb) * 100) if total_fb else None

    return UserStats(
        full_name=current_user.full_name,
        email=current_user.email,
        member_since=current_user.created_at,
        total_agents=total_agents,
        total_conversations=total_conversations,
        total_messages=total_messages,
        groq_messages=groq_messages,
        ollama_messages=ollama_messages,
        most_used_provider=most_used,
        feedback_given=feedback_given,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        satisfaction_score=satisfaction,
        prompts_improved=prompts_improved,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-deletes the user's account by setting is_active=False.
    All agents, conversations and messages remain in the DB for
    audit purposes but the user can no longer log in.
    """
    current_user.is_active = False
    db.commit()