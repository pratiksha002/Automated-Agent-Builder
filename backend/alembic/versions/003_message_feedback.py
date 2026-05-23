"""add message_feedback table

Revision ID: 003_message_feedback
Revises: 002_provider_fields
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = '003_message_feedback'
down_revision = '002_provider_fields'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'message_feedback',
        sa.Column('id',
            postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False),
        sa.Column('message_id',
            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id',
            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating',      sa.String(4),  nullable=False),
        sa.Column('suggestion',  sa.Text,       nullable=True),
        sa.Column('applied',     sa.Boolean,    nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'],   ['agents.id'],   ondelete='CASCADE'),
        sa.CheckConstraint("rating IN ('up', 'down')", name='ck_feedback_rating'),
    )
    # One rating per message
    op.create_index(
        'ix_message_feedback_message_id',
        'message_feedback', ['message_id'], unique=True,
    )
    op.create_index(
        'ix_message_feedback_agent_id',
        'message_feedback', ['agent_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_message_feedback_agent_id',   table_name='message_feedback')
    op.drop_index('ix_message_feedback_message_id', table_name='message_feedback')
    op.drop_table('message_feedback')