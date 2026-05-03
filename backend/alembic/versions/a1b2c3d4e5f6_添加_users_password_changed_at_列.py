"""添加 users.password_changed_at 列

Revision ID: a1b2c3d4e5f6
Revises: 519c97faaed2
Create Date: 2026-05-04

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '519c97faaed2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_changed_at')
