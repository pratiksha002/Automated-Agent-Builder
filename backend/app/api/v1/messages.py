import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.conversation import get_conversation_by_id
from app.schemas.message import ChatRequest, ChatResponse
from app.services.conversation_service import handle_chat_turn
from app.main import limiter

router = APIRouter(prefix="/conversations", tags=["messages"])


# ─── STEP 5.2 — OWNERSHIP ENFORCEMENT ────────────────────────────────────────

def assert_conversation_ownership(
    conversation,
    user_id: uuid.UUID,
) -> None:
    """
    Reusable ownership guard for conversation resources.

    Raises 403 if the conversation does not belong to the given user.
    Called before any read or mutating operation on a specific conversation.

    Design rule: always call get_conversation_or_404() BEFORE this function.
    404 must come before 403 — never reveal whether a resource exists
    to a user who doesn't own it.
    """
    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )


# ─── STEP 5.3 — RATE LIMITED CHAT ROUTE ──────────────────────────────────────

@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.CHAT_RATE_LIMIT)
def send_message(
    request: Request,           # Required by slowapi — must be first param
    conversation_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends a user message to a conversation and returns the LLM's response.

    Rate limited to settings.CHAT_RATE_LIMIT (default: 20 requests/minute
    per IP). Exceeding the limit returns a 429 with a JSON error body.

    Flow:
      1. Rate limit check (slowapi, before any logic runs)
      2. Verify conversation exists → 404 if not
      3. Verify conversation belongs to current user → 403 if not
      4. Run inference pipeline via handle_chat_turn()
      5. Return assistant response

    Raises:
        401 — missing or invalid JWT (get_current_user)
        403 — conversation belongs to a different user
        404 — conversation not found or closed
        422 — blank or invalid message content (ChatRequest validator)
        429 — rate limit exceeded
        502 — Groq API error
        500 — unexpected server error
    """
    # ── 404 check ─────────────────────────────────────────────────────────────
    conversation = get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # ── 403 check (Step 5.2) ──────────────────────────────────────────────────
    assert_conversation_ownership(conversation, current_user.id)

    # ── Inference pipeline ────────────────────────────────────────────────────
    assistant_response = handle_chat_turn(
        db=db,
        conversation_id=conversation_id,
        user_message=payload.content,
    )

    return ChatResponse(
        role="assistant",
        content=assistant_response,
    )