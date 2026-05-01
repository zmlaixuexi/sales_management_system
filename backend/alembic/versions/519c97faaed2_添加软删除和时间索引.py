"""添加软删除和时间索引

Revision ID: 519c97faaed2
Revises: c3f8a1d2e9b4
Create Date: 2026-05-02 02:43:51.987261
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = '519c97faaed2'
down_revision: Union[str, None] = 'c3f8a1d2e9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 软删除索引：所有软删除表在列表查询中都过滤 deleted_at IS NULL
    op.create_index('ix_sales_orders_deleted_at', 'sales_orders', ['deleted_at'])
    op.create_index('ix_products_deleted_at', 'products', ['deleted_at'])
    op.create_index('ix_customers_deleted_at', 'customers', ['deleted_at'])
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])

    # created_at 单列索引（仅 sales_orders 已有，其余表缺少）
    op.create_index('ix_products_created_at', 'products', [sa.text('created_at DESC')])
    op.create_index('ix_customers_created_at', 'customers', [sa.text('created_at DESC')])
    op.create_index('ix_users_created_at', 'users', [sa.text('created_at DESC')])
    op.create_index('ix_payments_created_at', 'payments', [sa.text('created_at DESC')])


def downgrade() -> None:
    op.drop_index('ix_payments_created_at', 'payments')
    op.drop_index('ix_users_created_at', 'users')
    op.drop_index('ix_customers_created_at', 'customers')
    op.drop_index('ix_products_created_at', 'products')
    op.drop_index('ix_users_deleted_at', 'users')
    op.drop_index('ix_customers_deleted_at', 'customers')
    op.drop_index('ix_products_deleted_at', 'products')
    op.drop_index('ix_sales_orders_deleted_at', 'sales_orders')
