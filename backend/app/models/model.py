from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .agent import Agent
    from .api_key import APIKey


class Model(Base):
    """
    Registry of Groq-hosted LLMs available on the platform.
    Seeded at startup. Not user-editable.
    """

    __tablename__ = "models"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable display name, e.g. 'LLaMA 3.3 70B'",
    )

    groq_model_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        comment="Exact model string sent to Groq API, e.g. 'llama-3.3-70b-versatile'",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Shown to users in the model selection dropdown",
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
        return f"<Model id={self.id} groq_model_id={self.groq_model_id}>"