"""权限校验和数据范围集成测试 — 验证 RBAC、数据范围过滤、敏感字段控制"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.product import Product, ProductCategory
from app.models.user import Permission, Role, RolePermission, User, UserRole

TEST_DB_URL = "sqlite:///./test_permissions.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_admin_tokens: dict = {}
_sale_user_id: str = ""
_customer_id_own: str = ""
_customer_id_other: str = ""
_product_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def _create_user_with_perms(db, username, perm_codes):
    """创建带指定权限的非超级用户"""
    user = User(
        id=uuid.uuid4(),
        username=username,
        hashed_password=hash_password("TestPass123!"),
        display_name=username,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    role = Role(id=uuid.uuid4(), name=f"role_{username}", display_name=f"角色-{username}")
    db.add(role)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))

    for code in perm_codes:
        perm = Permission(id=uuid.uuid4(), code=code, name=code, module=code.split(":")[0])
        db.add(perm)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    return user


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        # 超级管理员
        admin = User(
            id=uuid.uuid4(),
            username="perm_admin",
            hashed_password=hash_password("TestPass123!"),
            display_name="权限管理员",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)

        # 销售员（有 customer:list/create 但无 customer:view_all）
        sale_user = _create_user_with_perms(db, "sale01", [
            "customer:list", "customer:create", "customer:update", "customer:delete",
            "order:list", "order:create", "order:view",
            "order:update", "order:confirm", "order:cancel",
            "product:list",
            "report:sales",
        ])
        global _sale_user_id
        _sale_user_id = str(sale_user.id)

        # 分类
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)

        # 商品
        product = Product(
            id=uuid.uuid4(), sku="SPU-TEST-001", name="权限测试商品",
            sale_price=100, cost_price=50, stock_quantity=100,
            category_id=cat.id, status="active",
            created_by=admin.id, updated_by=admin.id,
        )
        db.add(product)
        global _product_id
        _product_id = str(product.id)

        # 归属管理员的客户
        c_other = Customer(
            id=uuid.uuid4(), name="管理员客户", phone="13900000001",
            owner_user_id=admin.id, created_by=admin.id, updated_by=admin.id,
        )
        db.add(c_other)
        global _customer_id_other
        _customer_id_other = str(c_other.id)

        # 归属销售员的客户
        c_own = Customer(
            id=uuid.uuid4(), name="销售员客户", phone="13900000002",
            owner_user_id=sale_user.id, created_by=admin.id, updated_by=admin.id,
        )
        db.add(c_own)
        global _customer_id_own
        _customer_id_own = str(c_own.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_permissions.db"):
        os.remove("./test_permissions.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _ensure_token(username: str, store: dict):
    """确保 token 存在，不存在则自动登录"""
    if not store.get("access"):
        resp = client.post("/api/v1/auth/login", json={"username": username, "password": "TestPass123!"})
        assert resp.status_code == 200, f"自动登录 {username} 失败: {resp.status_code}"
        store["access"] = resp.json()["data"]["access_token"]


def _auth(username="sale01"):
    if username == "perm_admin":
        _ensure_token("perm_admin", _admin_tokens)
        return {"Authorization": f"Bearer {_admin_tokens['access']}"}
    _ensure_token("sale01", _tokens)
    return {"Authorization": f"Bearer {_tokens['access']}"}


def test_01_login_both_users():
    """登录管理员和销售员"""
    resp = client.post("/api/v1/auth/login", json={"username": "sale01", "password": "TestPass123!"})
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/login", json={"username": "perm_admin", "password": "TestPass123!"})
    assert resp.status_code == 200
    _admin_tokens["access"] = resp.json()["data"]["access_token"]


def test_02_customer_data_scope_own_only():
    """销售员只能看到本人客户"""
    resp = client.get("/api/v1/customers", headers=_auth("sale01"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    customer_ids = [c["id"] for c in items]
    assert _customer_id_own in customer_ids, "销售员应能看到本人客户"
    assert _customer_id_other not in customer_ids, "销售员不应看到其他人的客户"


def test_03_customer_data_scope_admin_sees_all():
    """管理员能看到所有客户"""
    resp = client.get("/api/v1/customers", headers=_auth("perm_admin"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    customer_ids = [c["id"] for c in items]
    assert _customer_id_own in customer_ids
    assert _customer_id_other in customer_ids


def test_04_product_no_cost_permission():
    """销售员无 product:view_cost 权限，不应看到成本价"""
    resp = client.get("/api/v1/products", headers=_auth("sale01"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    product = items[0]
    assert "cost_price" not in product, "无 view_cost 权限不应返回 cost_price"
    assert "unit_profit" not in product, "无 view_cost 权限不应返回 unit_profit"
    assert "gross_margin" not in product, "无 view_cost 权限不应返回 gross_margin"
    assert "sale_price" in product, "应返回 sale_price"


def test_05_product_admin_sees_cost():
    """管理员能看到成本价"""
    resp = client.get("/api/v1/products", headers=_auth("perm_admin"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    product = items[0]
    assert "cost_price" in product, "管理员应看到 cost_price"
    assert "unit_profit" in product, "管理员应看到 unit_profit"
    assert "gross_margin" in product, "管理员应看到 gross_margin"


def test_06_forbidden_without_permission():
    """无权限的接口返回 403"""
    # sale01 没有 product:create 权限
    resp = client.post("/api/v1/products", json={
        "name": "非法商品", "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_07_order_data_scope_own_only():
    """销售员只能看到本人订单"""
    # 管理员创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_other,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("perm_admin"))
    assert resp.status_code == 200

    # 销售员创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_own,
        "items": [{"product_id": _product_id, "quantity": 2}],
    }, headers=_auth("sale01"))
    assert resp.status_code == 200
    sale_order_id = resp.json()["data"]["id"]

    # 销售员查看订单列表
    resp = client.get("/api/v1/sales-orders", headers=_auth("sale01"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    order_ids = [o["id"] for o in items]
    assert sale_order_id in order_ids, "销售员应能看到本人订单"
    assert len(items) == 1, f"销售员只应看到 1 个订单，实际看到 {len(items)}"


def test_08_export_customer_data_scope():
    """客户导出也应用数据范围过滤"""
    resp = client.get("/api/v1/exports/customers", headers=_auth("sale01"))
    assert resp.status_code == 200
    content = resp.text
    assert "销售员客户" in content, "应包含本人客户"
    # 管理员客户可能出现在表头行之外
    lines = [line for line in content.strip().split("\n") if line.strip() and "客户名称" not in line]
    assert len(lines) == 1, "销售员导出只应有 1 个客户数据行"


def test_09_export_order_data_scope():
    """订单导出也应用数据范围过滤"""
    resp = client.get("/api/v1/exports/orders", headers=_auth("sale01"))
    assert resp.status_code == 200
    content = resp.text
    lines = [line for line in content.strip().split("\n") if line.strip() and "订单号" not in line]
    assert len(lines) == 1, "销售员导出只应有 1 个订单数据行"


def test_10_order_logs_strip_cost_fields():
    """无 product:view_cost 权限用户查看订单日志不含成本字段"""
    # 管理员创建订单（含成本数据）
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_own,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("sale01"))
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 销售员查看日志
    resp = client.get(f"/api/v1/sales-orders/{order_id}/logs", headers=_auth("sale01"))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    create_logs = [i for i in items if i["action"] == "order_create"]
    assert len(create_logs) >= 1
    after = create_logs[0].get("after_data")
    if after and isinstance(after, dict):
        # 销售员无 product:view_cost，不应看到成本字段
        assert "cost_price" not in after
        assert "subtotal_cost" not in after


def test_11_export_products_no_cost_columns():
    """无 product:view_cost 权限用户导出商品 CSV 不含成本价列"""
    resp = client.get("/api/v1/exports/products", headers=_auth("sale01"))
    assert resp.status_code == 200
    content = resp.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "成本价" not in header, "无 view_cost 权限导出不应含成本价列"
    assert "利润" not in header, "无 view_cost 权限导出不应含利润列"


def test_12_export_products_admin_has_cost_columns():
    """管理员导出商品 CSV 含成本价列"""
    resp = client.get("/api/v1/exports/products", headers=_auth("perm_admin"))
    assert resp.status_code == 200
    content = resp.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "成本价" in header, "管理员导出应含成本价列"


def test_13_export_orders_no_profit_columns():
    """无 product:view_cost 权限用户导出订单 CSV 不含成本/毛利列"""
    resp = client.get("/api/v1/exports/orders", headers=_auth("sale01"))
    assert resp.status_code == 200
    content = resp.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "成本" not in header, "无 view_cost 权限导出订单不应含成本列"
    assert "毛利" not in header, "无 view_cost 权限导出订单不应含毛利列"


def test_14_export_orders_admin_has_profit_columns():
    """管理员导出订单 CSV 含成本/毛利列"""
    resp = client.get("/api/v1/exports/orders", headers=_auth("perm_admin"))
    assert resp.status_code == 200
    content = resp.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "成本" in header, "管理员导出订单应含成本列"
    assert "毛利" in header, "管理员导出订单应含毛利列"


def test_15_report_summary_no_profit():
    """无 report:profit 权限用户查看报表不含成本/毛利数据"""
    resp = client.get("/api/v1/reports/sales-summary?period=30d", headers=_auth("sale01"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_cost" not in data, "无 report:profit 不应返回 total_cost"
    assert "gross_profit" not in data, "无 report:profit 不应返回 gross_profit"
    assert "gross_margin" not in data, "无 report:profit 不应返回 gross_margin"
    assert "total_amount" in data, "应返回 total_amount"
    assert "order_count" in data, "应返回 order_count"


def test_16_report_summary_admin_has_profit():
    """管理员查看报表含成本/毛利数据"""
    resp = client.get("/api/v1/reports/sales-summary?period=30d", headers=_auth("perm_admin"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_cost" in data, "管理员应看到 total_cost"
    assert "gross_profit" in data, "管理员应看到 gross_profit"
    assert "gross_margin" in data, "管理员应看到 gross_margin"


# --- 对象级权限测试：check_owner_or_forbid ---


def test_17_customer_detail_non_owner_forbidden():
    """非所有者查看客户详情返回 403"""
    resp = client.get(f"/api/v1/customers/{_customer_id_other}", headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_18_customer_detail_owner_allowed():
    """所有者查看客户详情返回 200"""
    resp = client.get(f"/api/v1/customers/{_customer_id_own}", headers=_auth("sale01"))
    assert resp.status_code == 200


def test_19_customer_update_non_owner_forbidden():
    """非所有者编辑客户返回 403"""
    resp = client.put(f"/api/v1/customers/{_customer_id_other}", json={
        "name": "被篡改",
    }, headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_20_customer_update_owner_allowed():
    """所有者编辑客户返回 200"""
    resp = client.put(f"/api/v1/customers/{_customer_id_own}", json={
        "remark": "自己改的",
    }, headers=_auth("sale01"))
    assert resp.status_code == 200


def test_21_customer_delete_non_owner_forbidden():
    """非所有者删除客户返回 403"""
    resp = client.delete(f"/api/v1/customers/{_customer_id_other}", headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_22_customer_transfer_non_owner_forbidden():
    """非所有者转移客户返回 403"""
    resp = client.post(f"/api/v1/customers/{_customer_id_other}/transfer", json={
        "owner_user_id": _sale_user_id,
    }, headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_23_order_detail_non_owner_forbidden():
    """非所有者查看订单详情返回 403"""
    # 管理员创建一个订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_other,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("perm_admin"))
    assert resp.status_code == 200
    admin_order_id = resp.json()["data"]["id"]

    # 销售员不能看管理员订单详情
    resp = client.get(f"/api/v1/sales-orders/{admin_order_id}", headers=_auth("sale01"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_24_order_update_non_owner_forbidden():
    """非所有者编辑订单返回 403"""
    # 管理员创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_other,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("perm_admin"))
    admin_order_id = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/sales-orders/{admin_order_id}", json={
        "remark": "被篡改",
    }, headers=_auth("sale01"))
    assert resp.status_code == 403


def test_25_order_confirm_non_owner_forbidden():
    """非所有者确认订单返回 403"""
    # 管理员创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_other,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("perm_admin"))
    admin_order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{admin_order_id}/confirm", headers=_auth("sale01"))
    assert resp.status_code == 403


def test_26_order_cancel_non_owner_forbidden():
    """非所有者取消订单返回 403"""
    # 管理员创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id_other,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth("perm_admin"))
    admin_order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{admin_order_id}/cancel", headers=_auth("sale01"))
    assert resp.status_code == 403


def test_27_admin_bypasses_owner_check():
    """超级管理员绕过所有权检查"""
    # 管理员可以查看销售员的客户详情
    resp = client.get(f"/api/v1/customers/{_customer_id_own}", headers=_auth("perm_admin"))
    assert resp.status_code == 200

    # 管理员可以编辑销售员的客户
    resp = client.put(f"/api/v1/customers/{_customer_id_own}", json={
        "remark": "管理员修改",
    }, headers=_auth("perm_admin"))
    assert resp.status_code == 200
