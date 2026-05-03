"""软删除边界测试 — 覆盖模型字段、过滤逻辑、删除防护、引用完整性、迁移文件"""

import inspect
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import DateTime
from sqlalchemy import inspect as sa_inspect

from app.api.deps import active_query, get_or_404, safe_commit
from app.models.customer import Customer
from app.models.order import InventoryMovement, Payment, SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import Permission, Role, User

# ═══════════════════════════════════════════════════════
# 1. 模型字段存在性
# ═══════════════════════════════════════════════════════


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_model_has_deleted_at(model):
    """核心模型拥有 deleted_at 属性"""
    assert hasattr(model, "deleted_at")


@pytest.mark.parametrize(
    "model", [ProductCategory, SalesOrderItem, InventoryMovement, Payment, Role, Permission]
)
def test_auxiliary_model_no_deleted_at(model):
    """辅助模型没有 deleted_at 属性"""
    assert not hasattr(model, "deleted_at")


# ═══════════════════════════════════════════════════════
# 2. deleted_at 列属性
# ═══════════════════════════════════════════════════════


def _col(model, name):
    return sa_inspect(model).columns[name]


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_deleted_at_nullable(model):
    """deleted_at 允许 NULL"""
    assert _col(model, "deleted_at").nullable


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_deleted_at_type_datetime(model):
    """deleted_at 类型为 DateTime"""
    assert isinstance(_col(model, "deleted_at").type, DateTime)


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_deleted_at_timezone_aware(model):
    """deleted_at 启用时区"""
    assert _col(model, "deleted_at").type.timezone is True


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_deleted_at_indexed(model):
    """deleted_at 有索引"""
    assert _col(model, "deleted_at").index is True


# ═══════════════════════════════════════════════════════
# 3. active_query 过滤行为
# ═══════════════════════════════════════════════════════


def test_active_query_adds_filter_for_soft_delete_model():
    """active_query 对有 deleted_at 的模型调用 filter"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query

    active_query(mock_db, Product)

    mock_query.filter.assert_called()


def test_active_query_no_filter_for_normal_model():
    """active_query 对没有 deleted_at 的模型不调用 filter"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query

    active_query(mock_db, Role)

    mock_query.filter.assert_not_called()


def test_active_query_returns_query():
    """active_query 返回 Query 对象"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query

    result = active_query(mock_db, Product)
    assert result is mock_query


# ═══════════════════════════════════════════════════════
# 4. get_or_404 行为
# ═══════════════════════════════════════════════════════


def test_get_or_404_invalid_uuid_raises_404():
    """无效 UUID 抛 404"""
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(mock_db, Product, "not-a-uuid", "商品")
    assert exc_info.value.status_code == 404


def test_get_or_404_invalid_uuid_error_detail():
    """无效 UUID 错误消息包含资源标签"""
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(mock_db, Product, "bad-uuid", "商品")
    assert exc_info.value.detail["code"] == "RESOURCE_NOT_FOUND"
    assert "商品" in exc_info.value.detail["message"]


def test_get_or_404_not_found_raises_404():
    """未找到记录抛 404"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query

    with pytest.raises(HTTPException) as exc_info:
        get_or_404(mock_db, Product, uuid.uuid4(), "商品")
    assert exc_info.value.status_code == 404


def test_get_or_404_found_returns_object():
    """找到记录返回对象"""
    mock_obj = object()
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_obj
    mock_db.query.return_value = mock_query

    result = get_or_404(mock_db, Product, uuid.uuid4(), "商品")
    assert result is mock_obj


def test_get_or_404_soft_deleted_model_calls_filter():
    """有 deleted_at 的模型触发额外 filter 调用"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query

    with pytest.raises(HTTPException):
        get_or_404(mock_db, Product, uuid.uuid4(), "商品")

    # 至少两次 filter：一次 id，一次 deleted_at
    assert mock_query.filter.call_count >= 2


def test_get_or_404_normal_model_single_filter():
    """没有 deleted_at 的模型只 filter 一次（id）"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query

    with pytest.raises(HTTPException):
        get_or_404(mock_db, Role, uuid.uuid4(), "角色")

    assert mock_query.filter.call_count == 1


# ═══════════════════════════════════════════════════════
# 5. 删除防护逻辑
# ═══════════════════════════════════════════════════════


def test_product_delete_checks_order_reference():
    """商品删除逻辑检查订单引用"""
    from app.api.v1 import products
    source = inspect.getsource(products)
    assert "SalesOrder.deleted_at.is_(None)" in source
    assert "PRODUCT_IN_USE" in source


def test_product_delete_uses_409():
    """商品被引用时返回 409"""
    from app.api.v1 import products
    source = inspect.getsource(products)
    assert 'status_code=409' in source


def test_customer_delete_checks_order_reference():
    """客户删除逻辑检查订单引用"""
    from app.api.v1 import customers
    source = inspect.getsource(customers)
    assert "CUSTOMER_HAS_ORDERS" in source


def test_customer_delete_uses_400():
    """客户有订单时返回 400"""
    from app.api.v1 import customers
    source = inspect.getsource(customers)
    assert 'status_code=400' in source


# ═══════════════════════════════════════════════════════
# 6. 删除实现方式
# ═══════════════════════════════════════════════════════


def test_product_delete_sets_deleted_at_timestamp():
    """商品删除设置 deleted_at = datetime.now()"""
    from app.api.v1 import products
    source = inspect.getsource(products)
    assert "product.deleted_at = datetime.now()" in source


def test_customer_delete_sets_deleted_at_timestamp():
    """客户删除设置 deleted_at = datetime.now()"""
    from app.api.v1 import customers
    source = inspect.getsource(customers)
    assert "customer.deleted_at = datetime.now()" in source


def test_product_delete_logs_action():
    """商品删除记录审计日志"""
    from app.api.v1 import products
    source = inspect.getsource(products)
    assert 'action="product_delete"' in source


def test_customer_delete_logs_action():
    """客户删除记录审计日志"""
    from app.api.v1 import customers
    source = inspect.getsource(customers)
    assert 'action="customer_delete"' in source


def test_product_delete_uses_safe_commit():
    """商品删除使用 safe_commit"""
    from app.api.v1 import products
    source = inspect.getsource(products)
    assert "safe_commit(db)" in source


def test_customer_delete_uses_safe_commit():
    """客户删除使用 safe_commit"""
    from app.api.v1 import customers
    source = inspect.getsource(customers)
    assert "safe_commit(db)" in source


# ═══════════════════════════════════════════════════════
# 7. 跨表查询过滤
# ═══════════════════════════════════════════════════════


def test_auth_filters_soft_deleted_users():
    """认证查询过滤软删除用户"""
    from app.api import deps
    source = inspect.getsource(deps)
    assert "User.deleted_at.is_(None)" in source


def test_reports_filter_soft_deleted_orders():
    """报表查询过滤软删除订单"""
    from app.api.v1 import reports
    source = inspect.getsource(reports)
    assert "deleted_at.is_(None)" in source


def test_exports_filter_soft_deleted():
    """导出查询过滤软删除记录"""
    from app.services import export_service
    source = inspect.getsource(export_service)
    assert "deleted_at.is_(None)" in source


def test_payments_filter_soft_deleted_orders():
    """收款查询过滤软删除订单"""
    from app.api.v1 import payments
    source = inspect.getsource(payments)
    assert "SalesOrder.deleted_at.is_(None)" in source


def test_seed_filters_soft_deleted_users():
    """种子数据过滤软删除用户"""
    from app.db import seed
    source = inspect.getsource(seed)
    assert "User.deleted_at.is_(None)" in source


# ═══════════════════════════════════════════════════════
# 8. 迁移文件验证
# ═══════════════════════════════════════════════════════


def test_soft_delete_migration_exists():
    """软删除迁移文件存在"""
    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    assert migration_dir.exists()
    migration_files = list(migration_dir.glob("*软删除*"))
    assert len(migration_files) > 0


def test_soft_delete_migration_creates_indexes():
    """软删除迁移包含索引创建"""
    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migration_files = list(migration_dir.glob("*软删除*"))
    content = migration_files[0].read_text()
    assert "deleted_at" in content
    assert "create_index" in content.lower() or "Index" in content


def test_soft_delete_migration_covers_all_tables():
    """软删除迁移覆盖所有四个表"""
    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migration_files = list(migration_dir.glob("*软删除*"))
    content = migration_files[0].read_text()
    for table in ["products", "customers", "sales_orders", "users"]:
        assert table in content, f"迁移缺少表 {table}"


# ═══════════════════════════════════════════════════════
# 9. safe_commit 函数
# ═══════════════════════════════════════════════════════


def test_safe_commit_calls_db_commit():
    """safe_commit 调用 db.commit()"""
    mock_db = MagicMock()
    safe_commit(mock_db)
    mock_db.commit.assert_called_once()


def test_safe_commit_rollback_on_error():
    """safe_commit 异常时回滚"""
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error"):
        safe_commit(mock_db)
    mock_db.rollback.assert_called_once()


def test_safe_commit_no_rollback_on_success():
    """safe_commit 成功时不回滚"""
    mock_db = MagicMock()
    safe_commit(mock_db)
    mock_db.rollback.assert_not_called()


# ═══════════════════════════════════════════════════════
# 10. 端点注册
# ═══════════════════════════════════════════════════════


def test_product_delete_endpoint_exists():
    """商品删除端点存在"""
    from app.api.v1.products import router
    routes = [(r.path, list(r.methods or set())) for r in router.routes]
    delete_routes = [p for p, m in routes if "DELETE" in m]
    assert any("/products/{product_id}" in p for p in delete_routes)


def test_customer_delete_endpoint_exists():
    """客户删除端点存在"""
    from app.api.v1.customers import router
    routes = [(r.path, list(r.methods or set())) for r in router.routes]
    delete_routes = [p for p, m in routes if "DELETE" in m]
    assert any("/customers/{customer_id}" in p for p in delete_routes)


def test_no_restore_endpoints():
    """没有恢复端点（软删除不可逆）"""
    from app.api.v1 import customers, products
    for module in [products, customers]:
        source = inspect.getsource(module)
        # 不应该有 restore/undelete 路由
        assert "/restore" not in source
        assert "/undelete" not in source


# ═══════════════════════════════════════════════════════
# 8. get_or_404 自动过滤软删除
# ═══════════════════════════════════════════════════════


def test_get_or_404_auto_filters_deleted_at():
    """get_or_404 对有 deleted_at 的模型自动添加过滤"""
    source = inspect.getsource(get_or_404)
    assert "deleted_at" in source


def test_get_or_404_uses_hasattr_check():
    """get_or_404 用 hasattr 检查模型是否有 deleted_at"""
    source = inspect.getsource(get_or_404)
    assert "hasattr" in source
    assert "deleted_at" in source


# ═══════════════════════════════════════════════════════
# 9. active_query 过滤逻辑
# ═══════════════════════════════════════════════════════


def test_active_query_filters_deleted_at():
    """active_query 添加 deleted_at IS NULL 过滤"""
    source = inspect.getsource(active_query)
    assert "deleted_at" in source


@pytest.mark.parametrize("model", [Product, Customer, SalesOrder, User])
def test_active_query_used_in_list_endpoints(model):
    """各模型的列表端点使用 active_query"""
    import app.api.v1.customers as customers_mod
    import app.api.v1.orders as orders_mod
    import app.api.v1.products as products_mod
    import app.api.v1.users as users_mod

    module_map = {Product: products_mod, Customer: customers_mod, SalesOrder: orders_mod, User: users_mod}
    source = inspect.getsource(module_map[model])
    assert "active_query" in source


# ═══════════════════════════════════════════════════════
# 10. 报表端点 JOIN 软删除过滤一致性
# ═══════════════════════════════════════════════════════


def test_order_period_filter_covers_sales_order():
    """_order_period_filter 包含 SalesOrder.deleted_at 过滤"""
    from app.api.v1.reports import _order_period_filter

    source = inspect.getsource(_order_period_filter)
    assert "deleted_at" in source


def test_reports_module_uses_order_period_filter():
    """报表模块使用 _order_period_filter"""
    from app.api.v1 import reports

    source = inspect.getsource(reports)
    # 应在多处调用
    assert source.count("_order_period_filter") >= 4


def test_customer_ranking_filters_customer_deleted():
    """customer-ranking 端点过滤 Customer.deleted_at"""
    from app.api.v1.reports import customer_ranking

    source = inspect.getsource(customer_ranking)
    assert "Customer.deleted_at" in source or "deleted_at" in source


def test_inventory_warning_uses_active_query():
    """inventory-warning 使用 active_query 过滤 Product"""
    from app.api.v1.reports import inventory_warning

    source = inspect.getsource(inventory_warning)
    assert "active_query" in source


# ═══════════════════════════════════════════════════════
# 11. 导出端点软删除过滤一致性
# ═══════════════════════════════════════════════════════


def test_export_products_uses_active_query():
    """导出商品使用 active_query"""
    from app.services.export_service import export_products

    source = inspect.getsource(export_products)
    assert "active_query" in source


def test_export_customers_uses_active_query():
    """导出客户使用 active_query"""
    from app.services.export_service import export_customers

    source = inspect.getsource(export_customers)
    assert "active_query" in source


def test_export_orders_uses_active_query():
    """导出订单使用 active_query"""
    from app.services.export_service import export_orders

    source = inspect.getsource(export_orders)
    assert "active_query" in source


def test_export_payments_filters_sales_order():
    """导出收款过滤 SalesOrder.deleted_at"""
    from app.services.export_service import export_payments

    source = inspect.getsource(export_payments)
    assert "deleted_at" in source


# ═══════════════════════════════════════════════════════
# 12. 认证端点软删除过滤
# ═══════════════════════════════════════════════════════


def test_login_uses_active_query():
    """登录端点使用 active_query 查找用户"""
    from app.api.v1.auth import login

    source = inspect.getsource(login)
    assert "active_query" in source


def test_get_current_user_filters_deleted():
    """get_current_user 过滤 deleted_at"""
    from app.api.deps import get_current_user

    source = inspect.getsource(get_current_user)
    assert "deleted_at" in source


def test_refresh_token_uses_active_query():
    """refresh token 端点使用 active_query"""
    from app.api.v1.auth import refresh_token

    source = inspect.getsource(refresh_token)
    assert "active_query" in source


# ═══════════════════════════════════════════════════════
# 13. 商品删除防护 — 有订单时不允许删除
# ═══════════════════════════════════════════════════════


def test_product_delete_checks_order_items():
    """商品删除检查是否有关联订单"""
    from app.api.v1.products import delete_product

    source = inspect.getsource(delete_product)
    assert "SalesOrderItem" in source or "order_item" in source.lower()


def test_customer_delete_checks_orders():
    """客户删除检查是否有关联订单"""
    from app.api.v1.customers import delete_customer

    source = inspect.getsource(delete_customer)
    assert "SalesOrder" in source or "order" in source.lower()


# ═══════════════════════════════════════════════════════
# 14. 迁移文件包含 deleted_at 列
# ═══════════════════════════════════════════════════════


def test_migration_files_contain_deleted_at():
    """迁移文件中包含 deleted_at 列定义"""
    migration_dir = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"
    if not migration_dir.exists():
        pytest.skip("迁移目录不存在")
    migration_files = list(migration_dir.glob("*.py"))
    if not migration_files:
        pytest.skip("无迁移文件")
    content = ""
    for f in migration_files:
        content += f.read_text()
    assert "deleted_at" in content


# ═══════════════════════════════════════════════════════
# 15. 没有 deleted_at 的模型 — 确认完整性
# ═══════════════════════════════════════════════════════


@pytest.mark.parametrize("model", [Role, Permission, SalesOrderItem, Payment, InventoryMovement, ProductCategory])
def test_models_without_deleted_at(model):
    """这些模型不应有 deleted_at（不支持软删除）"""
    assert not hasattr(model, "deleted_at") or model.__table__.c.get("deleted_at") is None


# ═══════════════════════════════════════════════════════
# 16. 商品导入 SKU 查重过滤软删除
# ═══════════════════════════════════════════════════════


def test_product_import_sku_dedup_filters_deleted():
    """商品导入 SKU 查重过滤已删除商品"""
    from app.api.v1.products import import_products_csv

    source = inspect.getsource(import_products_csv)
    assert "deleted_at" in source


# ═══════════════════════════════════════════════════════
# 17. 客户导入手机号查重过滤软删除
# ═══════════════════════════════════════════════════════


def test_customer_import_phone_dedup_filters_deleted():
    """客户导入手机号查重过滤已删除客户"""
    from app.api.v1.customers import import_customers_csv

    source = inspect.getsource(import_customers_csv)
    assert "deleted_at" in source


# ═══════════════════════════════════════════════════════
# 18. 收款列表 JOIN 过滤
# ═══════════════════════════════════════════════════════


def test_payments_list_filters_sales_order_deleted():
    """收款列表 JOIN SalesOrder 时过滤 deleted_at"""
    from app.api.v1.payments import list_payments

    source = inspect.getsource(list_payments)
    assert "deleted_at" in source


# ═══════════════════════════════════════════════════════
# 19. 商品销售统计 JOIN 过滤
# ═══════════════════════════════════════════════════════


def test_product_sales_stats_filters_order_deleted():
    """商品销售统计 JOIN SalesOrder 时过滤 deleted_at"""
    from app.api.v1.products import _batch_sales_stats

    source = inspect.getsource(_batch_sales_stats)
    assert "deleted_at" in source
