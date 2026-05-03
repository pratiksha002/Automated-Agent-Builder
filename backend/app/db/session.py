from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.models.base import Base

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Reconnect on stale connections
    pool_size=10,             # Connections kept open
    max_overflow=20,          # Connections allowed beyond pool_size under load
    echo=settings.DEBUG,      # Log SQL in debug mode only
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency. Yields a DB session per request and
    guarantees cleanup whether or not the request succeeds.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Called once at startup to create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)