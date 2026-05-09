import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .agent import Agent
    from .message import Message


class Conversation(Base):
    """
    A single chat session between a user and an agent.
    Acts as the container for messages. updated_at tracks the last
    message time and is used to sort conversations by recency.
    """

    __tablename__ = "conversations"

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
        String(255),
        nullable=True,
        comment="Auto-generated from first user message, or manually set by user",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="False for archived or closed conversations",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversations",
    )

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="conversations",
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id} agent_id={self.agent_id}>"