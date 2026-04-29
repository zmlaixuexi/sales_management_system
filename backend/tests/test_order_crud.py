"""订单 CRUD + 状态流转测试 — 覆盖创建、详情、编辑、确认、取消、库存联动"""

import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_order_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_product2_id: str = ""
_customer_id: str = ""
_order_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens['access']}"}


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="order_tester",
            hashed_password=hash_password("testpass123"),
            display_name="订单测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        cat = ProductCategory(id=uuid.uuid4(), name="订单测试分类", sort_order=0)
        db.add(cat)
        db.flush()

        p1 = Product(
            id=uuid.uuid4(),
            name="订单测试商品A",
            sku="ORD-TEST-A",
            sale_price=100.00,
            cost_price=60.00,
            stock_quantity=50,
            status="active",
            category_id=cat.id,
        )
        p2 = Product(
            id=uuid.uuid4(),
            name="订单测试商品B",
            sku="ORD-TEST-B",
            sale_price=200.00,
            cost_price=120.00,
            stock_quantity=10,
            status="active",
            category_id=cat.id,
        )
        db.add_all([p1, p2])

        cust = Customer(
            id=uuid.uuid4(),
            name="订单测试客户",
            phone="13800000001",
            source="offline",
            owner_user_id=user.id,
        )
        db.add(cust)
        db.commit()

        global _product_id, _product2_id, _customer_id
        _product_id = str(p1.id)
        _product2_id = str(p2.id)
        _customer_id = str(cust.id)

        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_order_crud.db"):
        os.remove("./test_order_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


class TestOrderCreate:
    """创建订单"""

    def test_01_create_draft_order(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [
                {"product_id": _product_id, "quantity": 3, "unit_price": "90.00"},
            ],
            "remark": "测试订单",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "draft"
        assert data["total_amount"] == "270.00"
        assert data["order_no"].startswith("ORD-")
        global _order_id
        _order_id = data["id"]

    def test_02_create_order_empty_items_400(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [],
        }, headers=_auth())
        assert resp.status_code == 422

    def test_03_create_order_bad_customer_404(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 404

    def test_04_create_order_bad_product_404(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 404

    def test_05_create_order_zero_quantity_422(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 0}],
        }, headers=_auth())
        assert resp.status_code == 422

    def test_05b_create_order_negative_price_422(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "-10.00"}],
        }, headers=_auth())
        assert resp.status_code == 422
        assert "不能为负" in resp.json()["detail"][0]["msg"]


class TestOrderRead:
    """查询订单"""

    def test_06_get_order_detail(self):
        resp = client.get(f"/api/v1/sales-orders/{_order_id}", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_no"].startswith("ORD-")
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name_snapshot"] == "订单测试商品A"
        assert data["items"][0]["quantity"] == 3
        assert data["items"][0]["unit_price"] == "90.00"

    def test_07_get_order_404(self):
        resp = client.get(f"/api/v1/sales-orders/{uuid.uuid4()}", headers=_auth())
        assert resp.status_code == 404

    def test_08_list_orders(self):
        resp = client.get("/api/v1/sales-orders", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_09_list_orders_filter_status(self):
        resp = client.get("/api/v1/sales-orders?status=draft", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(o["status"] == "draft" for o in items)


class TestOrderUpdate:
    """编辑草稿订单"""

    def test_10_update_draft_order(self):
        resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
            "items": [
                {"product_id": _product_id, "quantity": 5, "unit_price": "85.00"},
                {"product_id": _product2_id, "quantity": 2},
            ],
            "remark": "修改后",
        }, headers=_auth())
        assert resp.status_code == 200

    def test_11_verify_update(self):
        resp = client.get(f"/api/v1/sales-orders/{_order_id}", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["remark"] == "修改后"
        # 5*85 + 2*200 = 425 + 400 = 825
        assert data["total_amount"] == "825.00"

    def test_11b_update_order_negative_price_422(self):
        """验证 update_order 也拒绝负价（之前遗漏的 bug）"""
        # 先创建一个新草稿订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 200
        draft_id = resp.json()["data"]["id"]

        resp = client.put(f"/api/v1/sales-orders/{draft_id}", json={
            "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "-5.00"}],
        }, headers=_auth())
        assert resp.status_code == 422
        assert "不能为负" in resp.json()["detail"][0]["msg"]


class TestOrderConfirm:
    """确认订单 — 库存扣减"""

    def test_12_confirm_draft_order(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "confirmed"

    def test_13_verify_inventory_deducted(self):
        resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["stock_quantity"] == 45  # 50 - 5

    def test_14_confirm_already_confirmed_400(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())
        assert resp.status_code == 400

    def test_15_update_confirmed_order_400(self):
        resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400


class TestOrderCancel:
    """取消订单 — 库存回滚"""

    def test_16_cancel_confirmed_order(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_17_verify_inventory_restored(self):
        resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["stock_quantity"] == 50  # 恢复

    def test_18_cancel_already_cancelled_400(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
        assert resp.status_code == 400


class TestOrderInventoryInsufficient:
    """库存不足确认失败"""

    def test_19_create_order_exceed_stock(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product2_id, "quantity": 999}],
        }, headers=_auth())
        assert resp.status_code == 200
        order_id = resp.json()["data"]["id"]

        resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]["message"]
