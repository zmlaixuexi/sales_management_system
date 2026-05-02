"""审计日志集成测试 — 验证业务操作产生审计日志记录"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_audit_log.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_order_id: str = ""
_payment_id: str = ""


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
            username="audit_tester",
            hashed_password=hash_password("testpass123"),
            display_name="审计测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_audit_log.db"):
        os.remove("./test_audit_log.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login_creates_audit_log():
    """登录成功产生审计日志"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]

    # 查询审计日志
    resp = client.get("/api/v1/audit-logs?action=login_success", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "login_success"
    assert log["actor_name"] == "审计测试员"


def test_02_login_failed_creates_audit_log():
    """登录失败产生审计日志"""
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "wrong_password",
    })

    resp = client.get("/api/v1/audit-logs?action=login_failed", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["action"] == "login_failed"


def test_03_product_crud_audit_logs():
    """商品 CRUD 操作产生审计日志"""
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "审计测试商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 50,
        "status": "active",
    }, headers=_auth())
    assert resp.status_code == 200
    global _product_id
    _product_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=product_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["resource_type"] == "product"
    assert log["after_data"]["name"] == "审计测试商品"

    # 编辑商品
    client.put(f"/api/v1/products/{_product_id}", json={
        "sale_price": "25.00",
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=product_update", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 停用商品
    client.post(f"/api/v1/products/{_product_id}/disable", headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=product_disable", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["after_data"]["status"] == "disabled"


def test_04_customer_crud_audit_logs():
    """客户 CRUD 操作产生审计日志"""
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "审计测试客户",
        "contact_name": "李四",
        "phone": "13900139000",
    }, headers=_auth())
    assert resp.status_code == 200
    global _customer_id
    _customer_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=customer_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "customer"

    # 编辑客户
    client.put(f"/api/v1/customers/{_customer_id}", json={
        "level": "vip",
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=customer_update", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 客户归属转移
    other_user = User(
        id=uuid.uuid4(), username="transfer_target",
        hashed_password=hash_password("testpass123"),
        display_name="转移目标用户", is_active=True, is_superuser=False,
    )
    db2 = TestSession()
    db2.add(other_user)
    db2.commit()
    other_uid = str(other_user.id)
    db2.close()

    client.post(f"/api/v1/customers/{_customer_id}/transfer", json={
        "owner_user_id": other_uid,
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=customer_transfer", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "customer"
    assert items[0]["after_data"]["owner_user_id"] == other_uid


def test_05_order_audit_logs():
    """订单操作产生审计日志"""
    # 先重新启用商品
    client.put(f"/api/v1/products/{_product_id}", json={"status": "active"}, headers=_auth())

    # 创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2, "unit_price": "20.00"}],
    }, headers=_auth())
    assert resp.status_code == 200
    global _order_id
    _order_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=order_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 确认订单
    client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=order_confirm", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1


def test_06_payment_audit_logs():
    """收款操作产生审计日志"""
    resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "40.00",
        "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=payment_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "payment"

    # 保存收款 ID 用于冲正测试
    global _payment_id
    _payment_id = items[0]["resource_id"]


def test_06a_payment_reverse_audit_log():
    """冲正收款产生审计日志"""
    resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=payment_reverse", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "payment"
    assert items[0]["before_data"]["status"] == "normal"
    assert items[0]["after_data"]["status"] == "reversed"


def test_06b_order_cancel_audit_log():
    """取消订单产生审计日志"""
    resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=order_cancel", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "order"


def test_07_inventory_adjust_audit_log():
    """库存调整产生审计日志"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id,
        "quantity_change": 5,
        "remark": "测试补货",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["after_data"]["stock_quantity"] is not None


def test_08_audit_log_filter_by_resource_type():
    """按资源类型筛选审计日志"""
    resp = client.get("/api/v1/audit-logs?resource_type=product", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all(i["resource_type"] == "product" for i in items)


def test_09_audit_actions_list():
    """获取操作类型列表"""
    resp = client.get("/api/v1/audit-logs/actions", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "actions" in data
    assert "resource_types" in data
    assert "login_success" in data["actions"]
    assert "product" in data["resource_types"]


def test_10_audit_log_filter_by_actor_id():
    """按操作人筛选审计日志"""
    resp = client.get("/api/v1/audit-logs", headers=_auth())
    actor_id = resp.json()["data"]["items"][0]["actor_id"]
    resp = client.get(f"/api/v1/audit-logs?actor_id={actor_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] > 0


def test_11_audit_log_filter_by_date_range():
    """按日期范围筛选审计日志"""
    resp = client.get("/api/v1/audit-logs?start_date=2020-01-01&end_date=2099-12-31", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] > 0


# ── 异常路径测试 ──────────────────────────────────────────


def test_12_audit_log_list_requires_auth():
    """审计日志列表未认证返回 401"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


def test_13_audit_actions_requires_auth():
    """操作类型列表未认证返回 401"""
    resp = client.get("/api/v1/audit-logs/actions")
    assert resp.status_code == 401


def test_14_audit_log_invalid_actor_id_422():
    """无效 actor_id 格式返回 422"""
    resp = client.get("/api/v1/audit-logs?actor_id=not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_15_audit_log_page_size_zero_422():
    """page_size=0 返回 422"""
    resp = client.get("/api/v1/audit-logs?page_size=0", headers=_auth())
    assert resp.status_code == 422


def test_16_audit_log_page_size_over_max_422():
    """page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/audit-logs?page_size=101", headers=_auth())
    assert resp.status_code == 422


def test_17_audit_log_page_zero_422():
    """page=0 返回 422"""
    resp = client.get("/api/v1/audit-logs?page=0", headers=_auth())
    assert resp.status_code == 422


def _admin_auth():
    from helpers import admin_auth_header
    return admin_auth_header(TestSession, "audit_tester")


def test_18_audit_log_keyword_like_percent():
    """关键字搜索含 % 不应匹配全部审计日志"""
    resp = client.get("/api/v1/audit-logs", params={"keyword": "%"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all("%" not in log.get("actor_name", "") for log in items)


def test_19_audit_log_keyword_like_underscore():
    """关键字搜索含 _ 只匹配实际含 _ 的 actor_name"""
    resp = client.get("/api/v1/audit-logs", params={"keyword": "_"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all("_" in log.get("actor_name", "") for log in items)


def test_20_audit_log_page_size_100():
    """审计日志列表 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/audit-logs", params={"page_size": 100}, headers=_admin_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_21_audit_log_no_permission_403():
    """无 audit:log 权限用户获取审计日志返回 403"""
    from helpers import make_user_with_perms

    token = make_user_with_perms(TestSession, "no_audit_log", ["audit:export"])
    resp = client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_22_audit_log_requires_auth():
    """未认证获取审计日志返回 401"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


def test_23_order_confirm_audit_log_fields():
    """订单确认审计日志 after_data 含 order_no 和 status"""
    # 重新启用商品
    client.put(f"/api/v1/products/{_product_id}", json={"status": "active"}, headers=_auth())

    # 创建新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    order_no = resp.json()["data"]["order_no"]

    # 确认订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 查询确认审计日志
    resp = client.get("/api/v1/audit-logs?action=order_confirm", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["after_data"]["status"] == "confirmed"
    assert log["after_data"]["order_no"] == order_no
    assert log["resource_type"] == "order"
