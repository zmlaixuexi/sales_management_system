"""审计日志集成测试 — 验证业务操作产生审计日志记录"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.main import app
from app.api.deps import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.product import ProductCategory

TEST_DB_URL = "sqlite:///./test_audit_log.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_order_id: str = ""


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
            is_superuser=False,
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
