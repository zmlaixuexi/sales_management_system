"""异常路径：后端缺失必需字段 422 测试
验证 POST 端点在缺少必需字段时正确返回 422"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_missing_fields.db"
_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

_original_override = None
_admin_id = uuid.uuid4()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _Session()
    Base.metadata.create_all(bind=_engine)
    db = _Session()
    db.add(User(
        id=_admin_id, username="field_admin", display_name="管理员",
        hashed_password=hash_password("TestPass123!"), is_superuser=True, is_active=True,
    ))
    db.commit()
    db.close()


def teardown_module(module):
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]
    _engine.dispose()
    import contextlib
    import os
    with contextlib.suppress(FileNotFoundError):
        os.remove("test_missing_fields.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


def _assert_422(resp):
    assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert "message" in body["error"]


_UUID = str(uuid.uuid4())


class TestProductMissingFields:
    """商品创建缺失必需字段"""

    def test_create_product_empty_body(self):
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        _assert_422(resp)

    def test_create_product_empty_name(self):
        resp = client.post("/api/v1/products", json={"name": ""}, headers=_headers())
        _assert_422(resp)

    def test_create_product_name_whitespace_only(self):
        """min_length=1 但纯空格通过 Pydantic 后可能被 strip 处理"""
        resp = client.post("/api/v1/products", json={"name": "   "}, headers=_headers())
        assert resp.status_code in (200, 201, 400, 422)

    def test_create_product_null_name(self):
        resp = client.post("/api/v1/products", json={"name": None}, headers=_headers())
        _assert_422(resp)


class TestCustomerMissingFields:
    """客户创建缺失必需字段"""

    def test_create_customer_empty_body(self):
        resp = client.post("/api/v1/customers", json={}, headers=_headers())
        _assert_422(resp)

    def test_create_customer_empty_name(self):
        resp = client.post("/api/v1/customers", json={"name": ""}, headers=_headers())
        _assert_422(resp)

    def test_create_customer_null_name(self):
        resp = client.post("/api/v1/customers", json={"name": None}, headers=_headers())
        _assert_422(resp)


class TestOrderMissingFields:
    """订单创建缺失必需字段"""

    def test_create_order_empty_body(self):
        resp = client.post("/api/v1/sales-orders", json={}, headers=_headers())
        _assert_422(resp)

    def test_create_order_missing_customer_id(self):
        body = {"items": [{"product_id": _UUID, "quantity": 1}]}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_missing_items(self):
        body = {"customer_id": _UUID}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_empty_items(self):
        body = {"customer_id": _UUID, "items": []}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_item_missing_product_id(self):
        body = {"customer_id": _UUID, "items": [{"quantity": 1}]}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_item_missing_quantity(self):
        body = {"customer_id": _UUID, "items": [{"product_id": _UUID}]}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_item_zero_quantity(self):
        body = {"customer_id": _UUID, "items": [{"product_id": _UUID, "quantity": 0}]}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_order_item_negative_quantity(self):
        body = {"customer_id": _UUID, "items": [{"product_id": _UUID, "quantity": -1}]}
        resp = client.post("/api/v1/sales-orders", json=body, headers=_headers())
        _assert_422(resp)


class TestPaymentMissingFields:
    """收款创建缺失必需字段（POST /payments/orders/{order_id}/payments）"""

    _url = f"/api/v1/payments/orders/{_UUID}/payments"

    def test_create_payment_empty_body(self):
        resp = client.post(self._url, json={}, headers=_headers())
        _assert_422(resp)

    def test_create_payment_missing_amount(self):
        resp = client.post(self._url, json={"payment_method": "cash"}, headers=_headers())
        _assert_422(resp)

    def test_create_payment_missing_method(self):
        resp = client.post(self._url, json={"amount": "100"}, headers=_headers())
        _assert_422(resp)

    def test_create_payment_invalid_method(self):
        body = {"amount": "100", "payment_method": "bitcoin"}
        resp = client.post(self._url, json=body, headers=_headers())
        _assert_422(resp)

    def test_create_payment_null_amount(self):
        body = {"amount": None, "payment_method": "cash"}
        resp = client.post(self._url, json=body, headers=_headers())
        _assert_422(resp)


class TestUserMissingFields:
    """用户创建缺失必需字段"""

    def test_create_user_empty_body(self):
        resp = client.post("/api/v1/users", json={}, headers=_headers())
        _assert_422(resp)

    def test_create_user_missing_username(self):
        body = {"password": "TestPass123!"}
        resp = client.post("/api/v1/users", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_user_missing_password(self):
        body = {"username": "newuser"}
        resp = client.post("/api/v1/users", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_user_short_username(self):
        body = {"username": "a", "password": "TestPass123!"}
        resp = client.post("/api/v1/users", json=body, headers=_headers())
        _assert_422(resp)

    def test_create_user_short_password(self):
        body = {"username": "newuser2", "password": "12345"}
        resp = client.post("/api/v1/users", json=body, headers=_headers())
        _assert_422(resp)


class TestLoginMissingFields:
    """登录缺失必需字段"""

    def test_login_empty_body(self):
        resp = client.post("/api/v1/auth/login", json={})
        _assert_422(resp)

    def test_login_missing_username(self):
        body = {"password": "TestPass123!"}
        resp = client.post("/api/v1/auth/login", json=body)
        _assert_422(resp)

    def test_login_missing_password(self):
        body = {"username": "field_admin"}
        resp = client.post("/api/v1/auth/login", json=body)
        _assert_422(resp)

    def test_login_empty_username(self):
        body = {"username": "", "password": "TestPass123!"}
        resp = client.post("/api/v1/auth/login", json=body)
        _assert_422(resp)

    def test_login_empty_password(self):
        body = {"username": "field_admin", "password": ""}
        resp = client.post("/api/v1/auth/login", json=body)
        _assert_422(resp)


class TestErrorFormat:
    """422 错误格式一致性"""

    def test_error_has_field_location(self):
        """422 错误消息包含字段路径"""
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        body = resp.json()
        msg = body["error"]["message"]
        assert "name" in msg.lower()

    def test_error_no_stack_trace(self):
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        text = resp.text
        assert "Traceback" not in text
        assert "ValidationError" not in text

    def test_multiple_missing_fields_still_422(self):
        """同时缺少多个必需字段仍返回 422"""
        resp = client.post("/api/v1/sales-orders", json={}, headers=_headers())
        _assert_422(resp)
