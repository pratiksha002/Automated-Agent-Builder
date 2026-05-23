import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Flag(Base):
    """
    One row per flagged message.
    Flags are raised automatically by the inference service when
    the LLM response or user input triggers a concern, or manually
    by the admin after review.

    flag_type options:
      - 'hallucination'  : response contains likely fabricated information
      - 'inappropriate'  : user asked for harmful/offensive content
      - 'jailbreak'      : user attempted to bypass agent instructions
      - 'other'          : catch-all for manual admin flags
    """

    __tablename__ = "flags"

    __table_args__ = (
        CheckConstraint(
            "flag_type IN ('hallucination', 'inappropriate', 'jailbreak', 'other')",
            name="ck_flags_flag_type",
        ),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    )

    flag_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    flag_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Auto-generated or admin-written explanation of why this was flagged",
    )

    is_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Admin has seen and reviewed this flag",
    )

    def __repr__(self) -> str:
        return f"<Flag id={self.id} type={self.flag_type} reviewed={self.is_reviewed}>"
