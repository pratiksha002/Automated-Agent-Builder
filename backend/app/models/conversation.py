import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .agent import Agent
    from .message import Message


class Conversation(Base):
    """
    A persistent chat session between a user and an agent.

    current_provider : which backend is currently handling inference
                       ('groq' or 'ollama'). Starts as the agent's
                       model provider. Switches automatically on Groq
                       rate-limit or manually by the user.
    provider_switched: True once an automatic fallback has occurred.
                       Used by the frontend to show a notification.
    """

    __tablename__ = "conversations"

    __table_args__ = (
        CheckConstraint(
            "current_provider IN ('groq', 'ollama')",
            name="ck_conversation_provider",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Auto-generated from the first user message",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    current_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="groq",
        comment="'groq' or 'ollama' — which backend is currently active",
    )

    provider_switched: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if an automatic fallback from Groq to Ollama occurred",
    )

    # Relationships
    user:     Mapped["User"]         = relationship("User")
    agent:    Mapped["Agent"]        = relationship("Agent")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} provider={self.current_provider}>"