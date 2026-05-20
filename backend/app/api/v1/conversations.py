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


def assert_conversation_ownership(conversation, user_id: uuid.UUID) -> None:
    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )


def get_conversation_or_404(db: Session, conversation_id: uuid.UUID):
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Opens a new chat session. Sets initial_provider from the agent's
    model provider so Ollama agents start on Ollama from the first turn.
    """
    agent = get_agent_by_id(db, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not agent.is_platform_agent and agent.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Derive initial provider from the agent's model
    initial_provider = "groq"
    if agent.model and hasattr(agent.model, 'provider'):
        initial_provider = agent.model.provider or "groq"

    conversation = create_conversation(
        db=db,
        user_id=current_user.id,
        agent_id=payload.agent_id,
        initial_provider=initial_provider,
    )
    return conversation


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_conversations(db, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_conversation_or_404(db, conversation_id)
    assert_conversation_ownership(conversation, current_user.id)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_conversation_or_404(db, conversation_id)
    assert_conversation_ownership(conversation, current_user.id)
    close_conversation(db, conversation_id)