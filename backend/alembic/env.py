"""
alembic/env.py

Alembic migration environment configured for the Automated Agent Builder.
Supports both offline (SQL script generation) and online (live DB) modes.

After placing this file, run:
    alembic revision --autogenerate -m "initial schema"
    alembic upgrade head
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import settings so DATABASE_URL is available
import sys
import os

# Make sure `app` is importable from alembic/env.py
# (alembic runs from the backend/ directory)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.models.base import Base

# Import ALL models so Alembic can detect them for autogenerate.
# If you add a new model file, import it here too.
from app.models import (  # noqa: F401
    User,
    Model,
    Agent,
    AgentTool,
    Conversation,
    Message,
    APIKey,
)

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Override sqlalchemy.url from alembic.ini with our settings value.
# This means DATABASE_URL only needs to be set in .env — not duplicated
# in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from alembic.ini config.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData object that autogenerate inspects for schema changes.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates a SQL script without
    connecting to the DB. Useful for review or applying via a DBA.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # Detect column type changes
        compare_server_default=True, # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the live DB and
    applies migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections in migration context
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()