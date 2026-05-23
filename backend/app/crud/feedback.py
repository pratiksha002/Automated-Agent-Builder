import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.models.message_feedback import MessageFeedback


def upsert_feedback(
    db: Session,
    message_id: uuid.UUID,
    agent_id: uuid.UUID,
    rating: str,
) -> MessageFeedback:
    """
    Creates or updates feedback for a message.
    Re-rating a message clears any previous suggestion so a fresh one
    can be generated based on the updated rating.
    """
    existing = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == message_id)
        .first()
    )
    if existing:
        existing.rating     = rating
        existing.suggestion = None
        existing.applied    = False
        db.commit()
        db.refresh(existing)
        return existing

    fb = MessageFeedback(
        message_id=message_id,
        agent_id=agent_id,
        rating=rating,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def get_feedback_by_message(
    db: Session,
    message_id: uuid.UUID,
) -> Optional[MessageFeedback]:
    return (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == message_id)
        .first()
    )


def get_agent_feedback(
    db: Session,
    agent_id: uuid.UUID,
    limit: int = 50,
) -> list[MessageFeedback]:
    """All feedback for an agent, newest first."""
    return (
        db.query(MessageFeedback)
        .filter(MessageFeedback.agent_id == agent_id)
        .order_by(MessageFeedback.created_at.desc())
        .limit(limit)
        .all()
    )


def get_pending_negative_feedback(
    db: Session,
    agent_id: uuid.UUID,
    limit: int = 10,
) -> list[MessageFeedback]:
    """
    Thumbs-down rows that have no suggestion yet and haven't been applied.
    These are fed to the LLM to produce prompt improvement suggestions.
    """
    return (
        db.query(MessageFeedback)
        .filter(
            MessageFeedback.agent_id   == agent_id,
            MessageFeedback.rating     == "down",
            MessageFeedback.suggestion == None,
            MessageFeedback.applied    == False,
        )
        .order_by(MessageFeedback.created_at.asc())
        .limit(limit)
        .all()
    )


def save_suggestion(
    db: Session,
    feedback_id: uuid.UUID,
    suggestion: str,
) -> Optional[MessageFeedback]:
    fb = db.query(MessageFeedback).filter(MessageFeedback.id == feedback_id).first()
    if not fb:
        return None
    fb.suggestion = suggestion
    db.commit()
    db.refresh(fb)
    return fb


def mark_applied(
    db: Session,
    feedback_id: uuid.UUID,
) -> Optional[MessageFeedback]:
    fb = db.query(MessageFeedback).filter(MessageFeedback.id == feedback_id).first()
    if not fb:
        return None
    fb.applied = True
    db.commit()
    db.refresh(fb)
    return fb


def get_feedback_stats(
    db: Session,
    agent_id: uuid.UUID,
) -> dict:
    rows    = db.query(MessageFeedback).filter(MessageFeedback.agent_id == agent_id).all()
    total   = len(rows)
    up      = sum(1 for r in rows if r.rating == "up")
    down    = sum(1 for r in rows if r.rating == "down")
    pending = sum(1 for r in rows if r.rating == "down" and not r.applied and not r.suggestion)
    applied = sum(1 for r in rows if r.applied)
    return {
        "total":   total,
        "up":      up,
        "down":    down,
        "pending": pending,
        "applied": applied,
        "score":   round((up / total) * 100) if total else None,
    }