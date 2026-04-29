"""添加复合索引优化查询性能

Revision ID: c3f8a1d2e9b4
Revises: baf204f3ea66
Create Date: 2026-04-30 05:15:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'c3f8a1d2e9b4'
down_revision: Union[str, None] = 'baf204f3ea66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 订单：状态 + 时间（列表筛选、报表聚合）
    op.create_index('ix_sales_orders_status_created_at', 'sales_orders', ['status', sa.text('created_at DESC')])

    # 订单：销售员 + 时间（数据范围查询）
    op.create_index('ix_sales_orders_owner_created_at', 'sales_orders', ['sales_user_id', sa.text('created_at DESC')])

    # 客户：归属 + 时间（数据范围查询）
    op.create_index('ix_customers_owner_created', 'customers', ['owner_user_id', sa.text('created_at DESC')])

    # 审计日志：操作 + 资源类型 + 时间（筛选排序）
    op.create_index(
        'ix_audit_logs_action_resource_created', 'audit_logs',
        ['action', 'resource_type', sa.text('created_at DESC')],
    )

    # 审计日志：操作人 + 时间
    op.create_index('ix_audit_logs_actor_created', 'audit_logs', ['actor_id', sa.text('created_at DESC')])

    # 收款：状态 + 订单 + 时间
    op.create_index('ix_payments_status_order_created', 'payments', ['status', 'order_id', sa.text('created_at DESC')])

    # 库存流水：产品 + 类型 + 时间
    op.create_index(
        'ix_inventory_mov_product_type_created', 'inventory_movements',
        ['product_id', 'movement_type', sa.text('created_at DESC')],
    )

    # 库存流水：时间排序（无筛选时）
    op.create_index('ix_inventory_movements_created_at', 'inventory_movements', [sa.text('created_at DESC')])

    # 订单明细：产品 ID（报表关联查询）
    op.create_index('ix_sales_order_items_product_id', 'sales_order_items', ['product_id'])

    # 产品：状态 + 库存（库存预警报表）
    op.create_index('ix_products_status_stock', 'products', ['status', 'stock_quantity'])


def downgrade() -> None:
    op.drop_index('ix_products_status_stock', 'products')
    op.drop_index('ix_sales_order_items_product_id', 'sales_order_items')
    op.drop_index('ix_inventory_movements_created_at', 'inventory_movements')
    op.drop_index('ix_inventory_mov_product_type_created', 'inventory_movements')
    op.drop_index('ix_payments_status_order_created', 'payments')
    op.drop_index('ix_audit_logs_actor_created', 'audit_logs')
    op.drop_index('ix_audit_logs_action_resource_created', 'audit_logs')
    op.drop_index('ix_customers_owner_created', 'customers')
    op.drop_index('ix_sales_orders_owner_created_at', 'sales_orders')
    op.drop_index('ix_sales_orders_status_created_at', 'sales_orders')
