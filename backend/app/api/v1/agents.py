import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.crud.agent import (
    get_platform_agents,
    get_user_agents,
    get_agent_by_id,
    create_agent,
    update_agent,
    soft_delete_agent,
)
from app.crud.agent_tool import get_agent_tools, set_agent_tools
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentRead,
    AgentListItem,
    AgentToolRead,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def assert_ownership(agent, user_id: uuid.UUID):
    """
    Raises 403 if the agent is not owned by the given user.
    Platform agents are never owned — they cannot be edited or deleted via API.
    """
    if agent.is_platform_agent or agent.owner_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this agent",
        )


def serialize_agent_read(agent, tools) -> AgentRead:
    """
    Manually assembles AgentRead from ORM objects since tools are
    loaded separately and need to be attached before serialization.
    """
    return AgentRead(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        model_id=agent.model_id,
        is_platform_agent=agent.is_platform_agent,
        is_public=agent.is_public,
        is_active=agent.is_active,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        tools=[
            AgentToolRead(
                id=t.id,
                tool_name=t.tool_name,
                tool_config=t.tool_config,
                is_active=t.is_active,
            )
            for t in tools
        ],
    )


@router.get("", response_model=list[AgentListItem])
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns platform agents + the current user's own agents combined.
    Uses AgentListItem — lighter payload, no system_prompt.
    """
    platform_agents = get_platform_agents(db)
    user_agents = get_user_agents(db, current_user.id)
    return platform_agents + user_agents


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full agent detail including system_prompt and tools.
    Accessible if the agent is a platform agent or owned by the current user.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Must be a platform agent or owned by the requesting user
    if not agent.is_platform_agent and agent.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this agent",
        )

    tools = get_agent_tools(db, agent_id)
    return serialize_agent_read(agent, tools)


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_new_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new agent owned by the current user.
    If tools are provided, they are inserted after the agent row is created.
    """
    agent = create_agent(db=db, user_id=current_user.id, data=payload)

    tools = []
    if payload.tools:
        tools = set_agent_tools(db=db, agent_id=agent.id, tools=payload.tools)

    return serialize_agent_read(agent, tools)


@router.patch("/{agent_id}", response_model=AgentRead)
def update_existing_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Partial update on an agent.
    Only fields explicitly provided in the request body are updated.
    If tools are provided (even as empty list), the full tool list is replaced.
    If tools field is absent entirely, existing tools are left unchanged.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    assert_ownership(agent, current_user.id)

    # Update agent fields (tools handled separately)
    update_data = payload.model_dump(exclude_unset=True, exclude={"tools"})
    if update_data:
        agent = update_agent(db=db, agent_id=agent_id, data=AgentUpdate(**update_data))

    # Only replace tools if the tools field was explicitly sent
    if payload.tools is not None:
        tools = set_agent_tools(db=db, agent_id=agent_id, tools=payload.tools)
    else:
        tools = get_agent_tools(db, agent_id)

    return serialize_agent_read(agent, tools)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft deletes an agent by setting is_active=False.
    Returns 204 No Content on success.
    Platform agents and agents owned by other users cannot be deleted.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    assert_ownership(agent, current_user.id)
    soft_delete_agent(db=db, agent_id=agent_id)