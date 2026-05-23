import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UsageLog(Base):
    """
    One row per message exchange (user message + assistant response).
    Powers all usage analytics in the admin dashboard.
    response_time_ms tracks how long the Groq call took.
    model_provider distinguishes 'groq' from 'ollama' for preference analytics.
    """

    __tablename__ = "usage_logs"

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

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
    )

    model_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="groq",
        comment="'groq' or 'ollama' — used for preference split analytics",
    )

    input_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens in the user message + history sent to the model",
    )

    output_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens in the assistant response",
    )

    response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time taken for the Groq/Ollama API call in milliseconds",
    )

    def __repr__(self) -> str:
        return f"<UsageLog id={self.id} user_id={self.user_id} agent_id={self.agent_id}>"
