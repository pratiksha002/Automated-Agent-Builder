import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def create_conversation(
    db: Session,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    initial_provider: str = "groq",   # set from agent.model.provider at route layer
) -> Conversation:
    """
    Opens a new chat session. initial_provider is taken from the agent's
    model so the first turn goes to the right backend automatically.
    """
    conversation = Conversation(
        user_id=user_id,
        agent_id=agent_id,
        title=None,
        is_active=True,
        current_provider=initial_provider,
        provider_switched=False,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_by_id(
    db: Session,
    conversation_id: uuid.UUID,
) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.is_active == True,
        )
        .first()
    )


def get_user_conversations(
    db: Session,
    user_id: uuid.UUID,
) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.is_active == True,
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def update_conversation_title(
    db: Session,
    conversation_id: uuid.UUID,
    title: str,
) -> Optional[Conversation]:
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        return None
    conv.title = title
    db.commit()
    db.refresh(conv)
    return conv


def touch_conversation(db: Session, conversation_id: uuid.UUID) -> None:
    conv = get_conversation_by_id(db, conversation_id)
    if conv:
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()


def close_conversation(db: Session, conversation_id: uuid.UUID) -> bool:
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        return False
    conv.is_active = False
    db.commit()
    return True