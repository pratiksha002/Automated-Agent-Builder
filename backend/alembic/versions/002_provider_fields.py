"""add provider fields to models and conversations

Revision ID: 002_provider_fields
Revises: (set to your current head)
"""
from alembic import op
import sqlalchemy as sa

revision     = '002_provider_fields'
down_revision = 'f5019480b499'   # set to your current latest revision ID
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── models table ──────────────────────────────────────────────────────────
    # Add provider column (default 'groq' so existing rows stay valid)
    op.add_column('models', sa.Column(
        'provider', sa.String(20), nullable=False, server_default='groq'
    ))
    # ollama_model_id alongside the existing groq_model_id
    op.add_column('models', sa.Column(
        'ollama_model_id', sa.String(150), nullable=True
    ))
    op.create_check_constraint(
        'ck_model_provider', 'models', "provider IN ('groq', 'ollama')"
    )

    # ── conversations table ───────────────────────────────────────────────────
    op.add_column('conversations', sa.Column(
        'current_provider', sa.String(20), nullable=False, server_default='groq'
    ))
    op.add_column('conversations', sa.Column(
        'provider_switched', sa.Boolean, nullable=False, server_default='false'
    ))
    op.create_check_constraint(
        'ck_conversation_provider', 'conversations',
        "current_provider IN ('groq', 'ollama')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_conversation_provider', 'conversations', type_='check')
    op.drop_column('conversations', 'provider_switched')
    op.drop_column('conversations', 'current_provider')

    op.drop_constraint('ck_model_provider', 'models', type_='check')
    op.drop_column('models', 'ollama_model_id')
    op.drop_column('models', 'provider')