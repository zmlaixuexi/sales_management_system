"""收款登记 + 冲正测试 — 覆盖创建、列表、冲正、超额、状态联动"""

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
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_payment_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_confirmed_order_id: str = ""
_draft_order_id: str = ""
_payment_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


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
            username="pay_tester",
            hashed_password=hash_password("testpass123"),
            display_name="收款测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        cat = ProductCategory(id=uuid.uuid4(), name="收款测试分类", sort_order=0)
        db.add(cat)
        db.flush()

        prod = Product(
            id=uuid.uuid4(),
            name="收款测试商品",
            sku="PAY-TEST-01",
            sale_price=100.00,
            cost_price=60.00,
            stock_quantity=100,
            status="active",
            category_id=cat.id,
        )
        db.add(prod)

        cust = Customer(
            id=uuid.uuid4(),
            name="收款测试客户",
            phone="13900000001",
            source="offline",
            owner_user_id=user.id,
        )
        db.add(cust)
        db.flush()

        # 创建一个已确认订单（total=300）
        order1 = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-0001",
            customer_id=cust.id,
            sales_user_id=user.id,
            status="confirmed",
            total_amount=300,
            total_cost=180,
            gross_profit=120,
            gross_margin=0.4,
            paid_amount=0,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(order1)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(),
            order_id=order1.id,
            product_id=prod.id,
            product_sku_snapshot=prod.sku,
            product_name_snapshot=prod.name,
            quantity=3,
            unit_price=100,
            discount_amount=0,
            discount_rate=0,
            cost_price_snapshot=60,
            subtotal_amount=300,
            subtotal_cost=180,
        ))

        # 创建一个草稿订单（不能收款）
        order2 = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-0002",
            customer_id=cust.id,
            sales_user_id=user.id,
            status="draft",
            total_amount=200,
            total_cost=120,
            gross_profit=80,
            gross_margin=0.4,
            paid_amount=0,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(order2)

        db.commit()

        global _product_id, _customer_id, _confirmed_order_id, _draft_order_id
        _product_id = str(prod.id)
        _customer_id = str(cust.id)
        _confirmed_order_id = str(order1.id)
        _draft_order_id = str(order2.id)

        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_payment_crud.db"):
        os.remove("./test_payment_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


class TestPaymentCreate:
    """登记收款"""

    def test_01_create_payment_success(self):
        resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
            "amount": "100.00",
            "payment_method": "cash",
            "remark": "第一笔",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["amount"] == "100.00"
        assert data["payment_method"] == "cash"
        assert data["order_status"] == "partially_paid"
        global _payment_id
        _payment_id = data["id"]

    def test_02_create_second_payment_complete(self):
        """全额付完 → 订单完成"""
        resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
            "amount": "200.00",
            "payment_method": "bank_transfer",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_status"] == "completed"

    def test_03_payment_exceed_remaining_400(self):
        """超额收款"""
        # 新建一个已确认订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 200
        oid = resp.json()["data"]["id"]
        client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

        resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
            "amount": "999.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 400
        assert "超过剩余应收" in resp.json()["detail"]["message"]

    def test_04_payment_zero_amount_422(self):
        resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
            "amount": "0",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 422

    def test_05_payment_draft_order_400(self):
        resp = client.post(f"/api/v1/payments/orders/{_draft_order_id}/payments", json={
            "amount": "50.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 400

    def test_06_payment_bad_order_404(self):
        resp = client.post(f"/api/v1/payments/orders/{uuid.uuid4()}/payments", json={
            "amount": "50.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 404


class TestPaymentList:
    """收款列表"""

    def test_07_list_payments(self):
        resp = client.get("/api/v1/payments", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 2  # at least the 2 payments from test_01/test_02

    def test_08_list_payments_by_order(self):
        resp = client.get(f"/api/v1/payments?order_id={_confirmed_order_id}", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(p["order_id"] == _confirmed_order_id for p in items)
        assert len(items) == 2


class TestPaymentReverse:
    """冲正收款"""

    def test_09_reverse_payment(self):
        resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "reversed"

    def test_10_reverse_already_reversed_404(self):
        resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
        assert resp.status_code == 404

    def test_11_reverse_bad_id_404(self):
        resp = client.post(f"/api/v1/payments/{uuid.uuid4()}/reverse", headers=_auth())
        assert resp.status_code == 404


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
