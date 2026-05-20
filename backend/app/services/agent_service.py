import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.agent import get_agent_by_id
from app.crud.agent_tool import get_agent_tools


def build_agent_config(db: Session, agent_id: uuid.UUID) -> dict:
    """
    Loads the agent, its model, and its active tools from the DB and
    returns a clean runtime dictionary consumed by the inference service.

    Now includes provider, groq_model_id, and ollama_model_id so the
    conversation service can route to the correct backend without
    additional DB lookups.

    Returns:
    {
        "agent_id": UUID,
        "name": str,
        "system_prompt": str,
        "model": {
            "id": UUID,
            "name": str,
            "provider": str,              # 'groq' or 'ollama'
            "groq_model_id": str | None,  # set for Groq models
            "ollama_model_id": str | None # set for Ollama models
        },
        "tools": [{"tool_name": str, "tool_config": dict}, ...]
    }
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
        "agent_id":      agent.id,
        "name":          agent.name,
        "system_prompt": agent.system_prompt,
        "model": {
            "id":              agent.model.id,
            "name":            agent.model.name,
            "provider":        agent.model.provider,
            "groq_model_id":   agent.model.groq_model_id,
            "ollama_model_id": agent.model.ollama_model_id,
        },
        "tools": [
            {"tool_name": t.tool_name, "tool_config": t.tool_config or {}}
            for t in tools
        ],
    }