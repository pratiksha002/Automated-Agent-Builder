import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.agent import get_agent_by_id
from app.crud.conversation import (
    create_conversation,
    get_conversation_by_id,
    get_user_conversations,
    close_conversation,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationDetail,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def assert_conversation_ownership(conversation, user_id: uuid.UUID) -> None:
    """
    Raises 403 if the conversation does not belong to the given user.
    Called before any read or mutating operation on a specific conversation.
    Mirrors the assert_ownership() pattern from agents.py.
    """
    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )


def get_conversation_or_404(db: Session, conversation_id: uuid.UUID):
    """
    Fetches an active conversation by ID or raises 404.
    Centralises the not-found check so every route doesn't repeat it.
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Opens a new chat session between the current user and a given agent.

    Validates that the target agent exists and is accessible before creating
    the conversation row. A user can start a conversation with:
      - Any platform agent (is_platform_agent=True)
      - Any of their own agents (owner_user_id == current_user.id)

    The conversation starts with no messages and a null title. Both are
    filled in by the inference layer on the first chat turn.
    """
    agent = get_agent_by_id(db, payload.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Must be a platform agent or owned by the requesting user
    if not agent.is_platform_agent and agent.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this agent",
        )

    conversation = create_conversation(
        db=db,
        user_id=current_user.id,
        agent_id=payload.agent_id,
    )
    return conversation


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all active conversations for the current user, newest first.
    Uses ConversationRead — no message history in the list payload.
    The frontend uses this to render the conversation sidebar.
    """
    return get_user_conversations(db, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a single conversation with its full message history.
    Uses ConversationDetail which embeds the messages list — the frontend
    can render the entire chat thread from a single response.

    Raises 404 if the conversation doesn't exist or is closed.
    Raises 403 if it belongs to a different user.
    """
    conversation = get_conversation_or_404(db, conversation_id)
    assert_conversation_ownership(conversation, current_user.id)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Closes (soft deletes) a conversation by setting is_active=False.
    The conversation and all its messages remain in the DB — nothing is
    hard deleted. Returns 204 No Content on success, matching the agents
    delete pattern.

    Raises 404 if not found. Raises 403 if owned by another user.
    """
    conversation = get_conversation_or_404(db, conversation_id)
    assert_conversation_ownership(conversation, current_user.id)
    close_conversation(db, conversation_id)