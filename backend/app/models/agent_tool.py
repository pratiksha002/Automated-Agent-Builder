import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .agent import Agent


class AgentTool(Base):
    """
    One row per tool enabled on an agent.
    Keeps the agents table clean and makes tool expansion trivial —
    adding a new tool type requires no schema change.

    tool_config holds tool-specific params as JSONB, e.g.:
      { "max_results": 5 }            for web_search
      { "timeout_seconds": 10 }       for code_executor
      {}                              for tools with no config
    """

    __tablename__ = "agent_tools"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Registered tool identifier, e.g. 'web_search', 'calculator', 'code_executor'",
    )

    tool_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Tool-specific configuration params",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Disable a tool without removing the row",
    )

    # Relationship
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="tools",
    )

    def __repr__(self) -> str:
        return f"<AgentTool agent_id={self.agent_id} tool={self.tool_name}>"