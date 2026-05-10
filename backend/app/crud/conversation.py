import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def create_conversation(
    db: Session,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> Conversation:
    """
    Opens a new chat session between a user and an agent.
    Title is NULL on creation — it gets auto-set after the first message
    by handle_chat_turn() in the conversation service.
    """
    conversation = Conversation(
        user_id=user_id,
        agent_id=agent_id,
        title=None,
        is_active=True,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_by_id(
    db: Session,
    conversation_id: uuid.UUID,
) -> Conversation | None:
    """
    Fetches a single active conversation by ID.
    Returns None if it doesn't exist or has been closed (is_active=False).
    Caller is responsible for ownership checks — this function does not
    enforce that the conversation belongs to any particular user.
    """
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
    """
    Lists all active conversations for a user, newest first.
    updated_at is bumped every time a message is added, so this ordering
    naturally surfaces the most recently active chats at the top.
    """
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
) -> Conversation | None:
    """
    Sets the conversation title.
    Called by the inference layer after the first user message is processed —
    the title is derived from the first ~50 chars of that message.
    Returns None if the conversation is not found.
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        return None

    conversation.title = title
    db.commit()
    db.refresh(conversation)
    return conversation


def touch_conversation(
    db: Session,
    conversation_id: uuid.UUID,
) -> None:
    """
    Bumps updated_at to now so the conversation rises to the top of the
    user's conversation list after each chat turn.
    SQLAlchemy's onupdate hook handles this automatically when any field
    changes, but this explicit call is used when only the timestamp needs
    updating (e.g. after saving a message).
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()


def close_conversation(
    db: Session,
    conversation_id: uuid.UUID,
) -> bool:
    """
    Soft deletes a conversation by setting is_active=False.
    The conversation and all its messages remain in the DB — nothing is
    hard deleted. Returns True if found and closed, False if not found.
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        return False

    conversation.is_active = False
    db.commit()
    return True