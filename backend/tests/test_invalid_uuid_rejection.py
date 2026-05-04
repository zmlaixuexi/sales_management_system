"""异常路径：后端无效 UUID 格式输入测试
验证所有接受 UUID 路径参数的端点正确拒绝无效格式"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_invalid_uuid.db"
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
        id=_admin_id, username="uuid_admin", display_name="管理员",
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
        os.remove("test_invalid_uuid.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))

INVALID_UUIDS = ["not-a-uuid", "12345", "gggggggg-gggg-gggg-gggg-gggggggggggg", ""]


def _headers():
    return {"Authorization": f"Bearer {_token}"}


class TestProductUUIDValidation:
    """商品端点 UUID 验证"""

    def test_get_product_invalid_uuid(self):
        for uid in INVALID_UUIDS[:2]:
            resp = client.get(f"/api/v1/products/{uid}", headers=_headers())
            assert resp.status_code in (400, 404, 422)

    def test_put_product_invalid_uuid(self):
        resp = client.put("/api/v1/products/not-uuid", json={"name": "x", "sale_price": "10"}, headers=_headers())
        assert resp.status_code in (400, 404, 422)

    def test_delete_product_invalid_uuid(self):
        resp = client.delete("/api/v1/products/not-uuid", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestCustomerUUIDValidation:
    """客户端点 UUID 验证"""

    def test_get_customer_invalid_uuid(self):
        resp = client.get("/api/v1/customers/not-a-uuid", headers=_headers())
        assert resp.status_code in (400, 404, 422)

    def test_put_customer_invalid_uuid(self):
        resp = client.put("/api/v1/customers/bad", json={"name": "x"}, headers=_headers())
        assert resp.status_code in (400, 404, 422)

    def test_delete_customer_invalid_uuid(self):
        resp = client.delete("/api/v1/customers/bad", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestOrderUUIDValidation:
    """订单端点 UUID 验证"""

    def test_get_order_invalid_uuid(self):
        resp = client.get("/api/v1/orders/invalid", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestPaymentUUIDValidation:
    """收款端点 UUID 验证"""

    def test_get_payment_invalid_uuid(self):
        resp = client.get("/api/v1/payments/invalid", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestUserUUIDValidation:
    """用户端点 UUID 验证"""

    def test_put_user_invalid_uuid(self):
        resp = client.put("/api/v1/users/not-a-uuid", json={"display_name": "x"}, headers=_headers())
        assert resp.status_code in (400, 404, 422)

    def test_put_user_valid_uuid(self):
        """有效 UUID 格式的 PUT 请求不触发格式错误"""
        resp = client.put(f"/api/v1/users/{_admin_id}", json={"display_name": "x"}, headers=_headers())
        # 可能 200 或其他业务错误，但不应是 422 格式错误
        assert resp.status_code in (200, 400, 404)


class TestUUIDErrorFormat:
    """无效 UUID 错误响应格式"""

    def test_invalid_uuid_returns_error_structure(self):
        resp = client.get("/api/v1/products/not-a-uuid", headers=_headers())
        body = resp.json()
        assert body["success"] is False
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_invalid_uuid_no_stack_trace(self):
        resp = client.get("/api/v1/products/not-a-uuid", headers=_headers())
        body = resp.json()
        text = str(body)
        assert "Traceback" not in text
        assert "ValueError" not in text

    def test_valid_uuid_returns_not_422(self):
        """有效 UUID 格式不触发格式错误（可能 404 但不是 422/400）"""
        valid = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/products/{valid}", headers=_headers())
        # 404 是正常的（资源不存在），但不应是 422（格式错误）
        assert resp.status_code in (200, 404)
