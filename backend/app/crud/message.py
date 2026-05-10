import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.message import Message


def add_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    token_count: Optional[int] = None,
) -> Message:
    """
    Inserts a single message row into the conversation.

    Called twice per chat turn by handle_chat_turn():
      1. Once for the user's incoming message (role='user')
      2. Once for the LLM's response (role='assistant')

    token_count is optional here — it's populated by the inference layer
    using count_tokens() before each call to add_message(). If the token
    counter isn't available for some reason, None is stored and the history
    trimmer will treat that message as zero tokens (safe fallback).

    role must be one of: 'user', 'assistant', 'system'
    The DB enforces this via a CheckConstraint on the messages table.
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        token_count=token_count,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_history(
    db: Session,
    conversation_id: uuid.UUID,
) -> list[Message]:
    """
    Returns all messages in a conversation ordered by created_at ASC.

    This is the exact list that gets passed to format_messages_for_groq()
    in the inference service. Order matters — the LLM must see the
    conversation in chronological sequence or the context will be incoherent.

    The ordering is also enforced at the ORM level via the relationship's
    order_by on the Conversation model, but this function applies it
    explicitly at the query level for safety when loading messages directly.
    """
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_message_by_id(
    db: Session,
    message_id: uuid.UUID,
) -> Message | None:
    """
    Fetches a single message by its ID.
    Not used in the core chat flow, but useful for testing and for any
    future endpoints that need to reference individual messages (e.g. reactions,
    editing, or regenerating a specific response).
    """
    return db.query(Message).filter(Message.id == message_id).first()


def get_last_user_message(
    db: Session,
    conversation_id: uuid.UUID,
) -> Message | None:
    """
    Returns the most recent user message in a conversation.

    Used by handle_chat_turn() to auto-generate the conversation title
    after the first turn — the title is derived from the first user
    message content. Fetching it here avoids passing the raw string
    through multiple layers.
    """
    return (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "user",
        )
        .order_by(Message.created_at.asc())
        .first()
    )