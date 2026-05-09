import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.agent import get_agent_by_id
from app.crud.agent_tool import get_agent_tools


def build_agent_config(db: Session, agent_id: uuid.UUID) -> dict:
    """
    Loads the agent, its model, and its active tools from the DB and
    returns a clean runtime dictionary consumed by the inference service.

    This is the bridge between what's stored and what gets executed.
    The inference service never touches ORM objects directly — it only
    sees this dict.

    Returns:
    {
        "agent_id": UUID,
        "name": str,
        "system_prompt": str,
        "model": {
            "id": UUID,
            "groq_model_id": str,   # the exact string sent to Groq API
            "name": str,
        },
        "tools": [
            {
                "tool_name": str,
                "tool_config": dict,
            },
            ...
        ]
    }

    Raises 404 if the agent doesn't exist or is soft deleted.
    Raises 500 if the agent has no model attached (data integrity issue).
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    if not agent.model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent {agent_id} has no model attached — data integrity issue",
        )

    tools = get_agent_tools(db, agent_id)

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "model": {
            "id": agent.model.id,
            "groq_model_id": agent.model.groq_model_id,
            "name": agent.model.name,
        },
        "tools": [
            {
                "tool_name": t.tool_name,
                "tool_config": t.tool_config or {},
            }
            for t in tools
        ],
    }