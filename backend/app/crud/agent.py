import uuid
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


def get_platform_agents(db: Session) -> list[Agent]:
    """
    Returns all platform pre-built agents that are active.
    These are visible to every user on login.
    """
    return (
        db.query(Agent)
        .filter(Agent.is_platform_agent == True, Agent.is_active == True)
        .all()
    )


def get_user_agents(db: Session, user_id: uuid.UUID) -> list[Agent]:
    """
    Returns all active agents created by a specific user.
    Does not include platform agents.
    """
    return (
        db.query(Agent)
        .filter(Agent.owner_user_id == user_id, Agent.is_active == True)
        .all()
    )


def get_agent_by_id(db: Session, agent_id: uuid.UUID) -> Agent | None:
    """
    Fetches a single agent by ID regardless of ownership.
    Returns None if not found or soft deleted.
    Caller is responsible for ownership checks.
    """
    return (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.is_active == True)
        .first()
    )


def create_agent(db: Session, user_id: uuid.UUID, data: AgentCreate) -> Agent:
    """
    Creates a new user-owned agent.
    owner_user_id is always set to the creating user.
    is_platform_agent is always False — platform agents are seeded, never created via API.
    """
    agent = Agent(
        owner_user_id=user_id,
        model_id=data.model_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        is_platform_agent=False,
        is_public=False,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def update_agent(db: Session, agent_id: uuid.UUID, data: AgentUpdate) -> Agent | None:
    """
    Partial update — only touches fields that are explicitly provided.
    Fields left as None in AgentUpdate are skipped entirely.
    Returns the updated agent, or None if not found.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        return None

    # model_dump(exclude_unset=True) gives only fields the caller actually passed in
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return agent


def soft_delete_agent(db: Session, agent_id: uuid.UUID) -> bool:
    """
    Soft deletes an agent by setting is_active=False.
    Never hard deletes — conversations referencing this agent remain intact.
    Returns True if the agent was found and deleted, False if not found.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        return False

    agent.is_active = False
    db.commit()
    return True