"""报表和审计日志端点测试"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import Permission, Role, RolePermission, User, UserRole

TEST_DB_URL = "sqlite:///./test_reports_audit.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_user_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="report_tester",
            hashed_password=hash_password("testpass123"),
            display_name="报表测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()
        global _user_id
        _user_id = str(user.id)

        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        db.flush()

        # 商品（低库存）
        product = Product(
            id=uuid.uuid4(), sku="SPU-RPT-001", name="报表测试商品",
            sale_price=100, cost_price=60, stock_quantity=3,
            category_id=cat.id, status="active",
            created_by=user.id, updated_by=user.id,
        )
        db.add(product)
        db.flush()

        # 客户
        customer = Customer(
            id=uuid.uuid4(), name="报表测试客户", phone="13900009999",
            owner_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(customer)
        db.flush()

        # 已确认订单
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-RPT-001",
            customer_id=customer.id, status="confirmed",
            total_amount=500, total_cost=300, gross_profit=200,
            gross_margin=40, paid_amount=0,
            sales_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=product.id,
            product_name_snapshot="报表测试商品", cost_price_snapshot=60,
            quantity=5, unit_price=100, subtotal_amount=500, subtotal_cost=300,
        ))

        # 审计日志
        db.add(AuditLog(
            id=uuid.uuid4(), action="product_create", resource_type="product",
            actor_id=user.id, actor_name="报表测试员",
            resource_id=str(product.id),
            after_data='{"name": "报表测试商品"}',
        ))
        db.add(AuditLog(
            id=uuid.uuid4(), action="login_success", resource_type="user",
            actor_id=user.id, actor_name="报表测试员",
            resource_id=str(user.id),
        ))

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_reports_audit.db"):
        os.remove("./test_reports_audit.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


# ─── 登录 ────────────────────────────────────────────────────

def test_01_login():
    resp = client.post("/api/v1/auth/login", json={
        "username": "report_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


# ─── 报表：销售汇总 ─────────────────────────────────────────

def test_02_sales_summary_default():
    """默认 30 天销售汇总"""
    resp = client.get("/api/v1/reports/sales-summary", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_amount" in data
    assert "order_count" in data
    assert data["period"] == "30d"


def test_03_sales_summary_today():
    """今日销售汇总"""
    resp = client.get("/api/v1/reports/sales-summary?period=today", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["period"] == "today"


def test_04_sales_summary_7d():
    """7 天销售汇总"""
    resp = client.get("/api/v1/reports/sales-summary?period=7d", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["period"] == "7d"
    # 有确认订单
    assert int(data["order_count"]) >= 1


def test_05_sales_summary_this_month():
    """本月销售汇总"""
    resp = client.get("/api/v1/reports/sales-summary?period=this_month", headers=_auth())
    assert resp.status_code == 200


def test_06_sales_summary_last_month():
    """上月销售汇总"""
    resp = client.get("/api/v1/reports/sales-summary?period=last_month", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["period"] == "last_month"
    assert "order_count" in data


def test_07_sales_summary_invalid_period():
    """无效 period 回退到 30d"""
    resp = client.get("/api/v1/reports/sales-summary?period=invalid", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["period"] == "invalid"


# ─── 报表：销售趋势 ─────────────────────────────────────────

def test_08_sales_trend():
    """7 天销售趋势"""
    resp = client.get("/api/v1/reports/sales-trend?period=7d", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 7  # 7 天应返回 7 条数据（含空日期填充）
    # 每条记录都应有 date, amount, order_count
    for item in items:
        assert "date" in item
        assert "amount" in item
        assert "order_count" in item


# ─── 报表：商品排行 ─────────────────────────────────────────

def test_09_product_ranking():
    """商品销售排行"""
    resp = client.get("/api/v1/reports/product-ranking?period=30d", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    first = items[0]
    assert "rank" in first
    assert "product_name" in first
    assert "total_sales" in first
    assert first["product_name"] == "报表测试商品"


def test_10_product_ranking_limit():
    """排行 limit 参数"""
    resp = client.get("/api/v1/reports/product-ranking?limit=1", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) <= 1


# ─── 报表：库存预警 ─────────────────────────────────────────

def test_11_inventory_warning_default():
    """默认阈值库存预警"""
    resp = client.get("/api/v1/reports/inventory-warning", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert data["threshold"] == 10  # settings 默认值


def test_12_inventory_warning_custom_threshold():
    """自定义阈值库存预警"""
    resp = client.get("/api/v1/reports/inventory-warning?threshold=5", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["threshold"] == 5
    # 库存=3 的商品应出现在预警列表
    names = [i["name"] for i in data["items"]]
    assert "报表测试商品" in names


def test_13_inventory_warning_zero():
    """阈值为 0 时只显示无库存商品"""
    resp = client.get("/api/v1/reports/inventory-warning?threshold=0", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    # 库存=3 的商品不应出现
    names = [i["name"] for i in data["items"]]
    assert "报表测试商品" not in names


# ─── 审计日志 ────────────────────────────────────────────────

def test_14_audit_log_list():
    """审计日志列表"""
    resp = client.get("/api/v1/audit-logs", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


def test_15_audit_log_filter_by_action():
    """按操作类型筛选"""
    resp = client.get("/api/v1/audit-logs?action=product_create", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["action"] == "product_create"


def test_16_audit_log_filter_by_resource_type():
    """按资源类型筛选"""
    resp = client.get("/api/v1/audit-logs?resource_type=user", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["resource_type"] == "user"


def test_17_audit_log_pagination():
    """审计日志分页"""
    resp = client.get("/api/v1/audit-logs?page=1&page_size=1", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["page_size"] == 1


def test_18_audit_log_keyword_search():
    """审计日志关键词搜索"""
    resp = client.get("/api/v1/audit-logs?keyword=报表测试员", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_19_audit_actions():
    """获取操作类型列表"""
    resp = client.get("/api/v1/audit-logs/actions", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "actions" in data
    assert "resource_types" in data
    assert "product_create" in data["actions"]
    assert "product" in data["resource_types"]


def test_20_audit_log_after_data_parsed():
    """审计日志 after_data 应被解析为 JSON"""
    resp = client.get("/api/v1/audit-logs?action=product_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert isinstance(log["after_data"], dict)
    assert log["after_data"]["name"] == "报表测试商品"


# ─── 报表权限检查 ────────────────────────────────────────────

def test_21_reports_require_permission():
    """报表需要 report:sales 权限"""
    # 创建无权限用户
    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_perm_user",
            hashed_password=hash_password("pass123456"),
            display_name="无权限用户", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(subject=str(nop.id))
    finally:
        db.close()

    resp = client.get("/api/v1/reports/sales-summary", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 403


def test_22_audit_requires_permission():
    """审计日志需要 audit:view 权限"""
    db = TestSession()
    try:
        nop = db.query(User).filter(User.username == "no_perm_user").first()
        token = create_access_token(subject=str(nop.id))
    finally:
        db.close()

    resp = client.get("/api/v1/audit-logs", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 403


# ─── 报表数据范围过滤 ─────────────────────────────────────────

def test_23_report_data_scope_filtered():
    """非 view_all 用户的报表只包含本人订单数据"""
    db = TestSession()
    try:
        # 创建只有 report:sales 权限的角色
        perm = Permission(id=uuid.uuid4(), code="report:sales", name="查看报表", module="report")
        db.add(perm)
        db.flush()
        role = Role(id=uuid.uuid4(), name="report_only", display_name="报表查看")
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        # 创建非超管用户
        sales_user = User(
            id=uuid.uuid4(), username="scope_tester",
            hashed_password=hash_password("testpass123"),
            display_name="范围测试员", is_active=True, is_superuser=False,
        )
        db.add(sales_user)
        db.flush()
        db.add(UserRole(user_id=sales_user.id, role_id=role.id))

        # 该用户的订单
        customer2 = Customer(
            id=uuid.uuid4(), name="范围测试客户", phone="13800001111",
            owner_user_id=sales_user.id, created_by=sales_user.id, updated_by=sales_user.id,
        )
        db.add(customer2)
        db.flush()
        order2 = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-SCOPE-001",
            customer_id=customer2.id, status="confirmed",
            total_amount=200, total_cost=100, gross_profit=100,
            gross_margin=50, paid_amount=0,
            sales_user_id=sales_user.id, created_by=sales_user.id, updated_by=sales_user.id,
        )
        db.add(order2)
        db.commit()

        token = create_access_token(subject=str(sales_user.id))
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 销售汇总：只看本人订单（200，不含超管的 500）
    resp = client.get("/api/v1/reports/sales-summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_amount"] == "200.00"
    assert data["order_count"] == 1

    # 销售趋势：只看本人订单
    resp = client.get("/api/v1/reports/sales-trend", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    total_amount = sum(Decimal(i["amount"]) for i in items)
    assert total_amount == Decimal("200")

    # 商品排行：只看本人订单的商品
    resp = client.get("/api/v1/reports/product-ranking", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 0  # scope_tester 的订单没有 SalesOrderItem
