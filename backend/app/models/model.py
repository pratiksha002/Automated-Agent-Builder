from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .agent import Agent
    from .api_key import APIKey


class Model(Base):
    """
    Registry of LLMs available on the platform.
    Supports two providers: 'groq' (cloud) and 'ollama' (local).

    provider        : 'groq' or 'ollama'
    groq_model_id   : exact string sent to Groq API (null for ollama models)
    ollama_model_id : exact string sent to Ollama API (null for groq models)
    """

    __tablename__ = "models"

    __table_args__ = (
        CheckConstraint(
            "provider IN ('groq', 'ollama')",
            name="ck_model_provider",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable display name, e.g. 'LLaMA 3.3 70B'",
    )

    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="groq",
        comment="'groq' or 'ollama'",
    )

    groq_model_id: Mapped[Optional[str]] = mapped_column(
        String(150),
        unique=True,
        nullable=True,
        comment="Exact model string sent to Groq API, e.g. 'llama-3.3-70b-versatile'",
    )

    ollama_model_id: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Exact model string sent to Ollama API, e.g. 'llama3.2'",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Shown to users in the model selection UI",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Toggle a model off without deleting it",
    )

    # Relationships
    agents: Mapped[List["Agent"]] = relationship(
        "Agent",
        back_populates="model",
    )

    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="model",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        mid = self.groq_model_id or self.ollama_model_id
        return f"<Model id={self.id} provider={self.provider} model_id={mid}>"