import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, CheckConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .message import Message
    from .agent import Agent


class MessageFeedback(Base):
    """
    Stores thumbs-up / thumbs-down ratings on assistant messages.

    One row per assistant message (unique on message_id).
    Works identically for Groq and Ollama responses — the feedback loop
    improves the agent's system prompt, which applies to both providers.

    Fields:
      rating     : 'up' or 'down'
      suggestion : LLM-generated improvement to the agent system prompt
      applied    : True once the agent owner applied the suggestion
    """

    __tablename__ = "message_feedback"

    __table_args__ = (
        CheckConstraint("rating IN ('up', 'down')", name="ck_feedback_rating"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    rating: Mapped[str] = mapped_column(String(4), nullable=False)

    suggestion: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="LLM-generated prompt improvement for this failure case",
    )

    applied: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True once the owner applied the suggestion",
    )

    message: Mapped["Message"] = relationship("Message")
    agent:   Mapped["Agent"]   = relationship("Agent")

    def __repr__(self) -> str:
        return f"<MessageFeedback id={self.id} rating={self.rating}>"