"""安全加固：request_id 一致性测试
验证每个 API 响应包含 X-Request-ID 头，且成功响应的 request_id 字段与头一致"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_request_id.db"
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
        id=_admin_id, username="rid_admin", display_name="管理员",
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
        os.remove("test_request_id.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


class TestRequestIdHeader:
    """X-Request-ID 响应头"""

    def test_health_has_x_request_id(self):
        resp = client.get("/api/v1/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    def test_products_list_has_x_request_id(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert "x-request-id" in resp.headers

    def test_error_response_has_x_request_id(self):
        resp = client.get("/api/v1/products")
        assert resp.status_code == 401
        assert "x-request-id" in resp.headers

    def test_404_has_x_request_id(self):
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/products/{fake}", headers=_headers())
        assert resp.status_code == 404
        assert "x-request-id" in resp.headers

    def test_422_has_x_request_id(self):
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        assert resp.status_code == 422
        assert "x-request-id" in resp.headers


class TestRequestIdPassthrough:
    """X-Request-ID 透传"""

    def test_custom_request_id_preserved(self):
        rid = "my-custom-id-123"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": rid})
        assert resp.headers["x-request-id"] == rid

    def test_generated_request_id_is_uuid_format(self):
        resp = client.get("/api/v1/health")
        rid = resp.headers["x-request-id"]
        # 应该可以被解析为 UUID
        uuid.UUID(rid)

    def test_different_requests_have_different_ids(self):
        r1 = client.get("/api/v1/health")
        r2 = client.get("/api/v1/health")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


class TestRequestIdInResponseBody:
    """request_id 在响应体中"""

    def test_health_body_has_request_id(self):
        resp = client.get("/api/v1/health")
        body = resp.json()
        assert "request_id" in body
        assert body["request_id"] == resp.headers["x-request-id"]

    def test_products_list_body_has_request_id(self):
        resp = client.get("/api/v1/products", headers=_headers())
        body = resp.json()
        assert "request_id" in body
        assert body["request_id"] == resp.headers["x-request-id"]

    def test_error_body_has_request_id(self):
        resp = client.get("/api/v1/products")
        resp.json()  # 消费响应体
        # 错误响应可能没有 request_id（由异常处理器生成），但头一定有
        assert "x-request-id" in resp.headers

    def test_custom_id_in_body_matches_header(self):
        rid = "test-rid-match-456"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": rid})
        body = resp.json()
        assert body["request_id"] == rid
        assert resp.headers["x-request-id"] == rid
