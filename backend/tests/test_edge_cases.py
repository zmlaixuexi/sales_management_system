"""异常路径和边界值集成测试 — 验证 API 错误处理"""

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
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_edge_cases.db"
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
            username="edge_tester",
            hashed_password=hash_password("testpass123"),
            display_name="边界测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)

        product = Product(
            id=uuid.uuid4(), sku="SPU-EDGE-001", name="边界测试商品",
            sale_price=100, cost_price=50, stock_quantity=5,
            category_id=cat.id, status="active",
            created_by=user.id, updated_by=user.id,
        )
        db.add(product)
        global _product_id
        _product_id = str(product.id)

        customer = Customer(
            id=uuid.uuid4(), name="边界测试客户", phone="13800000001",
            owner_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(customer)
        global _customer_id
        _customer_id = str(customer.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_edge_cases.db"):
        os.remove("./test_edge_cases.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "edge_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


# ─── 商品异常路径 ────────────────────────────────────────────

def test_02_product_create_missing_name():
    """创建商品缺少名称"""
    resp = client.post("/api/v1/products", json={
        "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 422


def test_03_product_create_negative_price():
    """创建商品价格为负"""
    resp = client.post("/api/v1/products", json={
        "name": "负价商品", "sale_price": "-10", "cost_price": "5",
    }, headers=_auth())
    assert resp.status_code == 400


def test_04_product_create_duplicate_sku():
    """创建商品 SKU 重复"""
    resp = client.post("/api/v1/products", json={
        "name": "重复SKU", "sku": "SPU-EDGE-001",
        "sale_price": "10", "cost_price": "5",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PRODUCT_SKU_DUPLICATED"


def test_05_product_get_not_found():
    """获取不存在的商品"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/products/{fake_id}", headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_06_product_update_not_found():
    """编辑不存在的商品"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/products/{fake_id}", json={"name": "x"}, headers=_auth())
    assert resp.status_code == 404


def test_07_product_delete_not_found():
    """删除不存在的商品"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/products/{fake_id}", headers=_auth())
    assert resp.status_code == 404


# ─── 客户异常路径 ────────────────────────────────────────────

def test_08_customer_create_empty_name():
    """创建客户名称为空"""
    resp = client.post("/api/v1/customers", json={"name": "  "}, headers=_auth())
    assert resp.status_code == 400


def test_09_customer_create_duplicate_phone():
    """创建客户手机号重复"""
    resp = client.post("/api/v1/customers", json={
        "name": "重复手机号客户", "phone": "13800000001",
    }, headers=_auth())
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CUSTOMER_DUPLICATED_WARNING"


def test_10_customer_get_not_found():
    """获取不存在的客户"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/customers/{fake_id}", headers=_auth())
    assert resp.status_code == 404


# ─── 订单异常路径 ────────────────────────────────────────────

def test_11_order_create_no_customer():
    """创建订单未选客户"""
    resp = client.post("/api/v1/sales-orders", json={
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 422


def test_12_order_create_empty_items():
    """创建订单明细为空"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id, "items": [],
    }, headers=_auth())
    assert resp.status_code == 422


def test_13_order_create_invalid_product():
    """创建订单引用不存在的商品"""
    fake_product = str(uuid.uuid4())
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": fake_product, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 404


def test_14_order_create_zero_quantity():
    """创建订单数量为 0"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 0}],
    }, headers=_auth())
    assert resp.status_code == 422


def test_15_order_create_negative_price():
    """创建订单成交单价为负"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "-10"}],
    }, headers=_auth())
    assert resp.status_code == 422


def test_16_order_confirm_insufficient_stock():
    """确认订单库存不足"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 999}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVENTORY_NOT_ENOUGH"


def test_17_order_confirm_not_draft():
    """确认非草稿订单"""
    # 创建并确认一个订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]
    global _order_id
    _order_id = order_id

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 再次确认
    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ORDER_INVALID_STATUS"


def test_18_order_cancel_already_cancelled():
    """取消已取消的订单"""
    # 创建一个新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 取消
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    # 再次取消
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 400


def test_19_order_update_not_draft():
    """编辑非草稿订单"""
    resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
        "remark": "尝试编辑",
    }, headers=_auth())
    assert resp.status_code == 400


# ─── 收款异常路径 ────────────────────────────────────────────

def test_20_payment_zero_amount():
    """收款金额为 0"""
    resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "0", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 422


def test_21_payment_exceed_remaining():
    """收款超过剩余应收"""
    resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "99999", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PAYMENT_AMOUNT_EXCEEDED"


def test_22_payment_order_not_found():
    """为不存在的订单收款"""
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/payments/orders/{fake_id}/payments", json={
        "amount": "10", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 404


def test_23_payment_reverse_not_found():
    """冲正不存在的收款"""
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/payments/{fake_id}/reverse", headers=_auth())
    assert resp.status_code == 404


# ─── 库存异常路径 ────────────────────────────────────────────

def test_24_inventory_adjust_zero():
    """库存调整为 0"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 0,
    }, headers=_auth())
    assert resp.status_code == 400


def test_25_inventory_adjust_no_product():
    """库存调整未指定商品"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "quantity_change": 10,
    }, headers=_auth())
    assert resp.status_code == 422


def test_26_inventory_adjust_below_zero():
    """库存调整导致负库存"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": -9999,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVENTORY_NOT_ENOUGH"


# ─── 认证异常路径 ────────────────────────────────────────────

def test_27_expired_token():
    """伪造 Token 返回 401"""
    resp = client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.fake",
    })
    assert resp.status_code == 401
