"""
api/v1/feedback.py

Routes:
  POST /messages/{message_id}/feedback
      — submit thumbs up/down on any assistant message
        (works for both Groq and Ollama responses)

  GET  /agents/{agent_id}/feedback
      — list all feedback + stats for an agent

  POST /agents/{agent_id}/feedback/suggestions
      — trigger the LLM to analyse thumbs-down responses
        and generate prompt improvement suggestions

  POST /agents/{agent_id}/feedback/{feedback_id}/apply
      — apply a suggestion as the new system prompt
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.feedback import (
    upsert_feedback,
    get_agent_feedback,
    get_feedback_stats,
)
from app.crud.message import get_message_by_id
from app.crud.conversation import get_conversation_by_id
from app.crud.agent import get_agent_by_id
from app.schemas.feedback import FeedbackSubmit, FeedbackRead, ApplyRequest, ApplyResponse
from app.services.feedback_service import generate_suggestions, apply_suggestion

router = APIRouter(tags=["feedback"])


def _assert_agent_owner(agent, user_id: uuid.UUID) -> None:
    if agent.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not own this agent")


# ── Submit thumbs up/down ─────────────────────────────────────────────────

@router.post("/messages/{message_id}/feedback", response_model=FeedbackRead)
def submit_feedback(
    message_id: uuid.UUID,
    payload: FeedbackSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rate any assistant message thumbs-up or thumbs-down.
    Works identically whether the response came from Groq or Ollama.
    Re-submitting changes the rating (upsert).

    IMPORTANT: Requires the message_feedback table to exist.
    Run: alembic upgrade head
    """
    try:
        message = get_message_by_id(db, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.role != "assistant":
            raise HTTPException(status_code=422, detail="Only assistant messages can be rated")

        conv = get_conversation_by_id(db, message.conversation_id)
        if not conv or conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return upsert_feedback(db, message_id, conv.agent_id, payload.rating)

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "message_feedback" in error_str or "relation" in error_str or "no such table" in error_str:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Feedback table not found. "
                    "Run the database migration: alembic upgrade head"
                ),
            )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── Get all feedback + stats ──────────────────────────────────────────────

@router.get("/agents/{agent_id}/feedback")
def get_feedback(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all feedback rows and a stats summary for an agent.
    Only the agent owner can view this.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _assert_agent_owner(agent, current_user.id)

    rows  = get_agent_feedback(db, agent_id)
    stats = get_feedback_stats(db, agent_id)

    return {
        "stats": stats,
        "feedback": [
            {
                "id":              str(fb.id),
                "message_id":      str(fb.message_id),
                "rating":          fb.rating,
                "suggestion":      fb.suggestion,
                "applied":         fb.applied,
                "created_at":      fb.created_at.isoformat(),
                "message_content": fb.message.content if fb.message else "",
            }
            for fb in rows
        ],
    }


# ── Generate LLM improvement suggestions ─────────────────────────────────

@router.post("/agents/{agent_id}/feedback/suggestions")
def request_suggestions(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers the agent's own LLM (Groq or Ollama) to analyse recent
    thumbs-down messages and suggest targeted improvements to the
    system prompt. One suggestion per pending thumbs-down, up to 5.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _assert_agent_owner(agent, current_user.id)

    suggestions = generate_suggestions(db, agent_id)
    return {"generated": len(suggestions), "suggestions": suggestions}


# ── Apply a suggestion to the agent prompt ────────────────────────────────

@router.post("/agents/{agent_id}/feedback/{feedback_id}/apply", response_model=ApplyResponse)
def apply_feedback_suggestion(
    agent_id:    uuid.UUID,
    feedback_id: uuid.UUID,
    payload:     ApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Agent owner accepts a suggestion (possibly edited) and applies it
    as the new system prompt. Takes effect immediately on ALL future
    turns for this agent — on both Groq and Ollama.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _assert_agent_owner(agent, current_user.id)

    result = apply_suggestion(db, agent_id, feedback_id, payload.new_prompt)
    return ApplyResponse(agent_id=uuid.UUID(result["agent_id"]), new_prompt=result["new_prompt"])