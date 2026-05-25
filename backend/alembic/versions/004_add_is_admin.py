"""add is_admin to users

Revision ID: 004_add_is_admin
Revises: 003_message_feedback
"""
from alembic import op
import sqlalchemy as sa

revision      = '004_add_is_admin'
down_revision = '003_message_feedback'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'is_admin', sa.Boolean, nullable=False, server_default='false'
    ))


def downgrade() -> None:
    op.drop_column('users', 'is_admin')