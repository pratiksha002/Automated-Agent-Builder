import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .model import Model
    from .agent_tool import AgentTool
    from .conversation import Conversation


class Agent(Base):
    """
    Core agent config. Covers both platform pre-built agents (owner_user_id=NULL,
    is_platform_agent=True) and user-created agents.

    At runtime, this config is loaded and used to build the LLM pipeline:
    system_prompt is injected, model_id routes to the correct Groq model,
    and active tools are attached.
    """

    __tablename__ = "agents"

    # NULL for platform agents; set for user-created agents
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="RESTRICT"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Shown on the agent card in the dashboard",
    )

    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Injected as the system message at the start of every conversation",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Platform agents are public; user agents are private by default",
    )

    is_platform_agent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True for the 3 pre-built agents seeded at startup",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Soft delete flag",
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="agents",
        foreign_keys=[owner_user_id],
    )

    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="agents",
    )

    tools: Mapped[List["AgentTool"]] = relationship(
        "AgentTool",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="agent",
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} platform={self.is_platform_agent}>"