import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.admin import Admin
from app.models.user import User
from app.models.agent import Agent
from app.models.usage_log import UsageLog
from app.models.flag import Flag
from app.models.conversation import Conversation
from app.models.message import Message
from app.core.security import hash_password


# ─── Admin Auth ───────────────────────────────────────────────────────────────

def get_admin_by_email(db: Session, email: str) -> Admin | None:
    return db.query(Admin).filter(Admin.email == email, Admin.is_active == True).first()


def get_admin_by_id(db: Session, admin_id: uuid.UUID) -> Admin | None:
    return db.query(Admin).filter(Admin.id == admin_id, Admin.is_active == True).first()


def create_admin(db: Session, email: str, password: str) -> Admin:
    admin = Admin(email=email, password_hash=hash_password(password))
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


# ─── User Management ──────────────────────────────────────────────────────────

def get_all_users(db: Session) -> list[User]:
    return db.query(User).order_by(desc(User.created_at)).all()


def get_user_by_id_admin(db: Session, user_id: uuid.UUID) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def ban_user(db: Session, user_id: uuid.UUID) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = True
        db.commit()
        db.refresh(user)
    return user


def unban_user(db: Session, user_id: uuid.UUID) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = False
        db.commit()
        db.refresh(user)
    return user


# ─── Global Dashboard Stats ───────────────────────────────────────────────────

def get_global_stats(db: Session) -> dict:
    now = datetime.now(timezone.utc)

    total_users        = db.query(func.count(User.id)).scalar()
    banned_users       = db.query(func.count(User.id)).filter(User.is_banned == True).scalar()
    total_agents       = db.query(func.count(Agent.id)).filter(Agent.is_active == True).scalar()
    platform_agents    = db.query(func.count(Agent.id)).filter(Agent.is_platform_agent == True, Agent.is_active == True).scalar()
    user_agents        = total_agents - platform_agents
    total_messages     = db.query(func.count(Message.id)).scalar()
    total_conversations= db.query(func.count(Conversation.id)).scalar()
    unreviewed_flags   = db.query(func.count(Flag.id)).filter(Flag.is_reviewed == False).scalar()
    total_flags        = db.query(func.count(Flag.id)).scalar()

    # Messages in last 24h, 7d, 30d
    msgs_24h = db.query(func.count(UsageLog.id)).filter(
        UsageLog.created_at >= now - timedelta(hours=24)
    ).scalar()
    msgs_7d = db.query(func.count(UsageLog.id)).filter(
        UsageLog.created_at >= now - timedelta(days=7)
    ).scalar()
    msgs_30d = db.query(func.count(UsageLog.id)).filter(
        UsageLog.created_at >= now - timedelta(days=30)
    ).scalar()

    # Most used agent
    most_used = (
        db.query(Agent.name, func.count(UsageLog.id).label("count"))
        .join(UsageLog, UsageLog.agent_id == Agent.id)
        .group_by(Agent.id, Agent.name)
        .order_by(desc("count"))
        .first()
    )

    # Groq vs Ollama split
    groq_count   = db.query(func.count(UsageLog.id)).filter(UsageLog.model_provider == "groq").scalar()
    ollama_count = db.query(func.count(UsageLog.id)).filter(UsageLog.model_provider == "ollama").scalar()
    total_logged = groq_count + ollama_count
    groq_pct     = round((groq_count / total_logged * 100) if total_logged else 0, 1)
    ollama_pct   = round((ollama_count / total_logged * 100) if total_logged else 0, 1)

    # Avg response time
    avg_response_ms = db.query(func.avg(UsageLog.response_time_ms)).scalar()

    # Active users today
    active_today = db.query(func.count(func.distinct(UsageLog.user_id))).filter(
        UsageLog.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).scalar()

    return {
        "total_users":         total_users,
        "banned_users":        banned_users,
        "total_agents":        total_agents,
        "platform_agents":     platform_agents,
        "user_agents":         user_agents,
        "total_messages":      total_messages,
        "total_conversations": total_conversations,
        "unreviewed_flags":    unreviewed_flags,
        "total_flags":         total_flags,
        "messages_24h":        msgs_24h,
        "messages_7d":         msgs_7d,
        "messages_30d":        msgs_30d,
        "most_used_agent":     most_used[0] if most_used else None,
        "most_used_agent_count": most_used[1] if most_used else 0,
        "groq_usage_pct":      groq_pct,
        "ollama_usage_pct":    ollama_pct,
        "avg_response_ms":     round(avg_response_ms) if avg_response_ms else 0,
        "active_users_today":  active_today,
    }


# ─── Per-User Stats ───────────────────────────────────────────────────────────

def get_user_stats(db: Session, user_id: uuid.UUID) -> dict:
    total_messages = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user_id
    ).scalar()

    total_agents = db.query(func.count(Agent.id)).filter(
        Agent.owner_user_id == user_id,
        Agent.is_active == True,
    ).scalar()

    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == user_id
    ).scalar()

    total_flags = db.query(func.count(Flag.id)).filter(
        Flag.user_id == user_id
    ).scalar()

    avg_response_ms = db.query(func.avg(UsageLog.response_time_ms)).filter(
        UsageLog.user_id == user_id
    ).scalar()

    # Most used agent for this user
    most_used = (
        db.query(Agent.name, func.count(UsageLog.id).label("count"))
        .join(UsageLog, UsageLog.agent_id == Agent.id)
        .filter(UsageLog.user_id == user_id)
        .group_by(Agent.id, Agent.name)
        .order_by(desc("count"))
        .first()
    )

    # Messages per day for last 30 days (for chart)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_usage = (
        db.query(
            func.date(UsageLog.created_at).label("date"),
            func.count(UsageLog.id).label("count"),
        )
        .filter(UsageLog.user_id == user_id, UsageLog.created_at >= thirty_days_ago)
        .group_by(func.date(UsageLog.created_at))
        .order_by(func.date(UsageLog.created_at))
        .all()
    )

    # Recent flags
    recent_flags = (
        db.query(Flag)
        .filter(Flag.user_id == user_id)
        .order_by(desc(Flag.created_at))
        .limit(5)
        .all()
    )

    return {
        "total_messages":      total_messages,
        "total_agents":        total_agents,
        "total_conversations": total_conversations,
        "total_flags":         total_flags,
        "avg_response_ms":     round(avg_response_ms) if avg_response_ms else 0,
        "most_used_agent":     most_used[0] if most_used else None,
        "daily_usage":         [{"date": str(r.date), "count": r.count} for r in daily_usage],
        "recent_flags":        [
            {
                "id":          str(f.id),
                "flag_type":   f.flag_type,
                "flag_reason": f.flag_reason,
                "is_reviewed": f.is_reviewed,
                "created_at":  f.created_at.isoformat(),
            }
            for f in recent_flags
        ],
    }


# ─── Flags ────────────────────────────────────────────────────────────────────

def get_all_flags(db: Session, reviewed: bool | None = None) -> list[Flag]:
    q = db.query(Flag)
    if reviewed is not None:
        q = q.filter(Flag.is_reviewed == reviewed)
    return q.order_by(desc(Flag.created_at)).all()


def mark_flag_reviewed(db: Session, flag_id: uuid.UUID) -> Flag | None:
    flag = db.query(Flag).filter(Flag.id == flag_id).first()
    if flag:
        flag.is_reviewed = True
        db.commit()
        db.refresh(flag)
    return flag


def create_flag(
    db: Session,
    message_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    flag_type: str,
    flag_reason: str | None = None,
) -> Flag:
    flag = Flag(
        message_id=message_id,
        conversation_id=conversation_id,
        user_id=user_id,
        agent_id=agent_id,
        flag_type=flag_type,
        flag_reason=flag_reason,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag