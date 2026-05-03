"""订单状态机边界测试 — 覆盖所有非法状态转换"""

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

TEST_DB_URL = "sqlite:///./test_state_machine.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_user_id: str = ""
_customer_id: str = ""
_product_id: str = ""


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


def _db():
    return TestSession()


def setup_module(module):
    global _original_override, _tokens, _user_id, _customer_id, _product_id
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(), username="sm_tester",
            hashed_password=hash_password("testpass123"),
            display_name="状态机测试员", is_active=True, is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="SM分类", sort_order=0)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(), name="SM商品", sku="SM-PROD-01",
            sale_price=100, cost_price=60, stock_quantity=200,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="SM客户", phone="13800000001",
            owner_user_id=user.id,
        )
        db.add(cust)
        db.commit()

        _user_id = str(user.id)
        _customer_id = str(cust.id)
        _product_id = str(prod.id)
        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_state_machine.db"):
        os.remove("./test_state_machine.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


def _create_draft(extra_items=None):
    """创建草稿订单并返回 order_id"""
    items = extra_items or [{"product_id": _product_id, "quantity": 1}]
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id, "items": items,
    }, headers=_auth())
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_confirmed(extra_items=None):
    """创建并确认订单，返回 order_id"""
    oid = _create_draft(extra_items)
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200
    return oid


def _create_cancelled_from_draft():
    """创建草稿订单并取消，返回 order_id"""
    oid = _create_draft()
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200
    return oid


def _create_cancelled_from_confirmed():
    """创建确认订单并取消，返回 order_id"""
    oid = _create_confirmed()
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200
    return oid


def _create_completed_via_db():
    """直接在数据库创建已完成订单，返回 order_id"""
    db = _db()
    try:
        prod = db.query(Product).first()
        cust = db.query(Customer).first()
        user = db.query(User).first()
        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"ORD-COMP-{uuid.uuid4().hex[:6]}",
            customer_id=cust.id, sales_user_id=user.id,
            status="completed", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=100,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        return str(order.id)
    finally:
        db.close()


def _create_partially_paid_via_db(paid_amount=50):
    """直接在数据库创建部分收款订单，返回 (order_id, paid_amount)"""
    db = _db()
    try:
        prod = db.query(Product).first()
        cust = db.query(Customer).first()
        user = db.query(User).first()
        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"ORD-PP-{uuid.uuid4().hex[:6]}",
            customer_id=cust.id, sales_user_id=user.id,
            status="partially_paid", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=paid_amount,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        return str(order.id)
    finally:
        db.close()


# ─── 已取消订单（从草稿取消）非法转换 ───────────────────────────────


class TestCancelledFromDraftTransitions:
    """从草稿取消的订单：终态，不允许任何转换"""

    def test_confirm_cancelled_draft_order_400(self):
        oid = _create_cancelled_from_draft()
        resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"

    def test_update_cancelled_draft_order_400(self):
        oid = _create_cancelled_from_draft()
        resp = client.put(f"/api/v1/sales-orders/{oid}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400

    def test_cancel_cancelled_draft_order_again_400(self):
        oid = _create_cancelled_from_draft()
        resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


# ─── 已取消订单（从确认取消）非法转换 ───────────────────────────────


class TestCancelledFromConfirmedTransitions:
    """从确认取消的订单：终态，不允许任何转换"""

    def test_confirm_cancelled_confirmed_order_400(self):
        oid = _create_cancelled_from_confirmed()
        resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"

    def test_update_cancelled_confirmed_order_400(self):
        oid = _create_cancelled_from_confirmed()
        resp = client.put(f"/api/v1/sales-orders/{oid}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400


# ─── 已完成订单非法转换 ─────────────────────────────────────────


class TestCompletedTransitions:
    """已完成订单：终态，不允许任何转换"""

    def test_confirm_completed_order_400(self):
        oid = _create_completed_via_db()
        resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"

    def test_cancel_completed_order_400(self):
        oid = _create_completed_via_db()
        resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"

    def test_update_completed_order_400(self):
        oid = _create_completed_via_db()
        resp = client.put(f"/api/v1/sales-orders/{oid}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400


# ─── 部分收款订单边界 ───────────────────────────────────────────


class TestPartiallyPaidTransitions:
    """部分收款订单的取消和编辑边界"""

    def test_cancel_partially_paid_with_payments_400(self):
        """部分收款且有收款记录的订单不允许取消"""
        oid = _create_partially_paid_via_db(paid_amount=50)
        resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_HAS_PAYMENTS"

    def test_update_partially_paid_order_400(self):
        """部分收款订单不允许编辑"""
        oid = _create_partially_paid_via_db(paid_amount=30)
        resp = client.put(f"/api/v1/sales-orders/{oid}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400

    def test_confirm_partially_paid_order_400(self):
        """部分收款订单不允许再次确认"""
        oid = _create_partially_paid_via_db(paid_amount=30)
        resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


# ─── 已确认订单非法操作 ─────────────────────────────────────────


class TestConfirmedTransitions:
    """已确认订单的非法操作"""

    def test_update_confirmed_order_400(self):
        """已确认订单不允许编辑"""
        oid = _create_confirmed()
        resp = client.put(f"/api/v1/sales-orders/{oid}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400

    def test_confirm_confirmed_order_again_400(self):
        """已确认订单不允许再次确认"""
        oid = _create_confirmed()
        resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"
