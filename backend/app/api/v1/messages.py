import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.conversation import get_conversation_by_id
from app.schemas.message import ChatRequest, ChatResponse
from app.services.conversation_service import handle_chat_turn

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def send_message(
    conversation_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends a user message to a conversation and returns the LLM's response.

    This is the core endpoint of the entire application — every chat turn
    flows through here.

    Flow:
      1. Verify the conversation exists and belongs to the current user.
      2. Hand off to handle_chat_turn() which runs the full inference
         pipeline: save user message → trim history → call Groq →
         save assistant response → bump updated_at → set title.
      3. Return the assistant response so the frontend can render it
         immediately without a second GET.

    Ownership is checked here at the route layer before any DB writes
    happen. handle_chat_turn() trusts that the caller has already
    validated ownership — it does not re-check.

    Returns:
        ChatResponse — {"role": "assistant", "content": "<response>"}

    Raises:
        401 — no token or invalid token (handled by get_current_user)
        403 — conversation belongs to a different user
        404 — conversation not found or closed
        422 — blank message content (handled by ChatRequest validator)
        502 — Groq API error
        500 — unexpected server error
    """
    # ── Ownership check ───────────────────────────────────────────────────────
    # Fetch the conversation first to verify it exists and is owned by the
    # current user. 404 before 403 — don't reveal whether the resource
    # exists to users who don't own it.
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )

    # ── Inference pipeline ────────────────────────────────────────────────────
    # payload.content is already stripped and validated non-blank by
    # ChatRequest.content_must_not_be_blank. Pass it directly.
    assistant_response = handle_chat_turn(
        db=db,
        conversation_id=conversation_id,
        user_message=payload.content,
    )

    return ChatResponse(
        role="assistant",
        content=assistant_response,
    )