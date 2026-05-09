import uuid
from sqlalchemy.orm import Session

from app.models.agent_tool import AgentTool
from app.schemas.agent import AgentToolConfig


def get_agent_tools(db: Session, agent_id: uuid.UUID) -> list[AgentTool]:
    """
    Returns all active tools for a given agent.
    Used by the inference service when building the agent's runtime config.
    """
    return (
        db.query(AgentTool)
        .filter(AgentTool.agent_id == agent_id, AgentTool.is_active == True)
        .all()
    )


def set_agent_tools(
    db: Session, agent_id: uuid.UUID, tools: list[AgentToolConfig]
) -> list[AgentTool]:
    """
    Replaces the full tool list for an agent.
    Deletes all existing tool rows for this agent, then inserts the new list.
    Simpler and safer than diffing — avoids partial update bugs entirely.

    Called on agent creation (with initial tools) and on agent update
    (when the user changes the tool selection).

    Passing an empty list clears all tools from the agent.
    """
    # Delete all existing tools for this agent
    db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

    # Insert the new tool list
    new_tools = []
    for tool in tools:
        agent_tool = AgentTool(
            agent_id=agent_id,
            tool_name=tool.tool_name,
            tool_config=tool.tool_config or {},
        )
        db.add(agent_tool)
        new_tools.append(agent_tool)

    db.commit()

    # Refresh each tool so IDs and timestamps are populated
    for tool in new_tools:
        db.refresh(tool)

    return new_tools