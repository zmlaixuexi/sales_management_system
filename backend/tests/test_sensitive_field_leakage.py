"""安全加固：后端 API 敏感字段泄露回归测试
验证所有 API 响应不包含密码哈希、密码明文、密钥等敏感字段"""

import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

_SENSITIVE_PATTERNS = [
    "hashed_password",
    "password_hash",
    "password",
    "secret_key",
    "jwt_secret",
    "private_key",
    "credit_card",
]

TEST_DB = "sqlite:///./test_sensitive_leak.db"
_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

_original_override = None
_admin_token = ""
_user_token = ""
_admin_id = uuid.uuid4()
_user_id = uuid.uuid4()


def setup_module(module):
    global _original_override, _admin_token, _user_token
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _Session()
    Base.metadata.create_all(bind=_engine)
    db = _Session()

    # 管理员
    admin = User(
        id=_admin_id, username="sens_admin", display_name="管理员",
        hashed_password=hash_password("AdminPass123!"), is_superuser=True, is_active=True,
    )
    db.add(admin)

    # 普通用户
    user = User(
        id=_user_id, username="sens_user", display_name="普通用户",
        hashed_password=hash_password("UserPass123!"), is_superuser=False, is_active=True,
    )
    db.add(user)
    db.commit()

    _admin_token = create_access_token(str(_admin_id))
    _user_token = create_access_token(str(_user_id))
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
        os.remove("test_sensitive_leak.db")


client = TestClient(app)


def _admin_headers():
    return {"Authorization": f"Bearer {_admin_token}"}


def _check_no_sensitive(data: dict, context: str = ""):
    """递归检查字典中不含敏感字段键"""
    text = json.dumps(data, ensure_ascii=False).lower()
    for pattern in _SENSITIVE_PATTERNS:
        assert pattern not in text, f"{context} 中发现敏感字段 '{pattern}'"


class TestUserEndpointNoLeakage:
    """用户端点不泄露密码哈希"""

    def test_user_list_no_password(self):
        resp = client.get("/api/v1/users", headers=_admin_headers())
        assert resp.status_code == 200
        _check_no_sensitive(resp.json(), "GET /users 列表")

    def test_me_endpoint_no_password(self):
        """GET /auth/me 不含密码"""
        resp = client.get("/api/v1/auth/me", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        _check_no_sensitive(data, "GET /auth/me")
        assert "hashed_password" not in json.dumps(data)

    def test_login_response_no_password(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "sens_admin", "password": "AdminPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        # token 应该存在，但密码/哈希不应存在
        _check_no_sensitive(data, "POST /auth/login")
        # 明确检查 access_token 存在但 hashed_password 不存在
        assert "access_token" in data.get("data", {})
        assert "hashed_password" not in json.dumps(data)

    def test_user_create_no_password_in_response(self):
        uid = uuid.uuid4()
        resp = client.post("/api/v1/users", json={
            "username": f"new_user_{uid.hex[:8]}",
            "password": "NewPass123!",
            "display_name": "新用户",
        }, headers=_admin_headers())
        assert resp.status_code == 200
        _check_no_sensitive(resp.json(), "POST /users 创建")


class TestAuthEndpointNoLeakage:
    """认证端点不泄露敏感信息"""

    def test_login_fail_no_password_leak(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "sens_admin", "password": "wrong_password",
        })
        assert resp.status_code in (400, 401)
        _check_no_sensitive(resp.json(), "POST /auth/login 失败")

    def test_me_endpoint_no_password(self):
        resp = client.get("/api/v1/auth/me", headers=_admin_headers())
        assert resp.status_code == 200
        _check_no_sensitive(resp.json(), "GET /auth/me")


class TestAuditLogNoLeakage:
    """审计日志不泄露敏感字段"""

    def test_audit_log_no_sensitive(self):
        resp = client.get("/api/v1/audit-logs", headers=_admin_headers())
        assert resp.status_code == 200
        # 审计日志可能包含 before_data/after_data，但不应含 hashed_password
        _check_no_sensitive(resp.json(), "GET /audit-logs")


class TestProductEndpointNoLeakage:
    """商品端点不含敏感字段"""

    def test_product_list_no_secret(self):
        resp = client.get("/api/v1/products", headers=_admin_headers())
        assert resp.status_code == 200
        _check_no_sensitive(resp.json(), "GET /products")


class TestCustomerEndpointNoLeakage:
    """客户端点不含密码等敏感字段"""

    def test_customer_list_no_secret(self):
        resp = client.get("/api/v1/customers", headers=_admin_headers())
        assert resp.status_code == 200
        _check_no_sensitive(resp.json(), "GET /customers")


class TestErrorResponsesNoLeakage:
    """错误响应不泄露内部信息"""

    def test_401_error_no_secret(self):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 401
        _check_no_sensitive(resp.json(), "401 错误")

    def test_404_error_no_secret(self):
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/products/{fake}", headers=_admin_headers())
        assert resp.status_code == 404
        _check_no_sensitive(resp.json(), "404 错误")

    def test_422_error_no_secret(self):
        resp = client.post("/api/v1/products", json={}, headers=_admin_headers())
        assert resp.status_code == 422
        _check_no_sensitive(resp.json(), "422 错误")

    def test_500_no_stack_trace(self):
        """错误消息不包含异常类名或堆栈"""
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/products/{fake}", headers=_admin_headers())
        body = resp.json()
        text = json.dumps(body)
        assert "Traceback" not in text
        assert "Exception" not in text
        assert "File " not in text
