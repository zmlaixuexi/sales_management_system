"""数据导出集成测试 — 验证 CSV 导出功能"""

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

TEST_DB_URL = "sqlite:///./test_export.db"
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
            username="export_tester",
            hashed_password=hash_password("testpass123"),
            display_name="导出测试员",
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
    if os.path.exists("./test_export.db"):
        os.remove("./test_export.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login_and_setup():
    """登录并准备测试数据"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "export_tester",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]

    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "导出测试商品",
        "cost_price": "50.00",
        "sale_price": "100.00",
        "stock_quantity": 30,
        "status": "active",
    }, headers=_auth())
    assert resp.status_code == 200
    global _product_id
    _product_id = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "导出测试客户",
        "contact_name": "王五",
        "phone": "13700137000",
    }, headers=_auth())
    assert resp.status_code == 200
    global _customer_id
    _customer_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 5, "unit_price": "100.00"}],
    }, headers=_auth())
    assert resp.status_code == 200
    global _order_id
    _order_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())

    # 登记收款
    client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "500.00",
        "payment_method": "cash",
    }, headers=_auth())


def test_02_export_products_csv():
    """导出商品 CSV"""
    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")

    content = resp.text
    assert "SKU" in content
    assert "商品名称" in content
    assert "导出测试商品" in content


def test_03_export_products_with_filter():
    """带筛选条件导出商品"""
    resp = client.get("/api/v1/exports/products?status=active", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "导出测试商品" in content


def test_04_export_customers_csv():
    """导出客户 CSV"""
    resp = client.get("/api/v1/exports/customers", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "客户名称" in content
    assert "导出测试客户" in content
    assert "13700137000" in content


def test_05_export_orders_csv():
    """导出订单 CSV"""
    resp = client.get("/api/v1/exports/orders", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "订单号" in content
    assert "ORD-" in content


def test_06_export_payments_csv():
    """导出收款 CSV"""
    resp = client.get("/api/v1/exports/payments", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "收款ID" in content
    assert "金额" in content


def test_07_export_requires_auth():
    """导出需要登录认证"""
    resp = client.get("/api/v1/exports/products")
    assert resp.status_code == 401


def test_08_export_empty_filter():
    """筛选条件无匹配时导出空数据（只有表头）"""
    resp = client.get("/api/v1/exports/products?status=nonexistent", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "SKU" in content
    # 只有一行表头
    lines = [l for l in content.strip().split("\n") if l.strip()]
    assert len(lines) == 1
