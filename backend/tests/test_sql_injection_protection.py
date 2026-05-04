"""安全加固：后端 SQL 注入防护回归测试
验证用户输入中的 SQL 注入字符串被安全处理"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_sql_injection.db"
_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

_original_override = None
_admin_id = uuid.uuid4()

SQL_INJECTION_STRINGS = [
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "' UNION SELECT * FROM users --",
    "Robert'); DROP TABLE students; --",
    "\" OR \"\"=\"\"",
    "1; EXEC xp_cmdshell 'dir' --",
    "' AND 1=CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))--",
]

_original_override = None


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _Session()
    Base.metadata.create_all(bind=_engine)
    db = _Session()
    db.add(User(
        id=_admin_id, username="sqli_admin", display_name="管理员",
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
        os.remove("test_sql_injection.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


class TestProductSQLInjection:
    """商品端点 SQL 注入防护"""

    def test_create_product_with_sql_in_name(self):
        for s in SQL_INJECTION_STRINGS[:3]:
            resp = client.post("/api/v1/products", json={"name": s}, headers=_headers())
            assert resp.status_code in (200, 201, 400, 422)
            if resp.status_code in (200, 201):
                body = resp.json()
                assert body["data"]["name"] == s

    def test_search_product_with_sql(self):
        resp = client.get(
            "/api/v1/products",
            params={"keyword": "' OR 1=1 --"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_product_uuid_path_with_sql(self):
        """路径参数中的 SQL 注入被格式校验拦截"""
        resp = client.get("/api/v1/products/1 OR 1=1", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestCustomerSQLInjection:
    """客户端点 SQL 注入防护"""

    def test_create_customer_with_sql_in_name(self):
        resp = client.post(
            "/api/v1/customers",
            json={"name": "'; DROP TABLE customers; --"},
            headers=_headers(),
        )
        assert resp.status_code in (200, 201, 400, 422)
        if resp.status_code in (200, 201):
            body = resp.json()
            assert body["data"]["name"] == "'; DROP TABLE customers; --"

    def test_search_customer_with_sql(self):
        resp = client.get(
            "/api/v1/customers",
            params={"keyword": "' UNION SELECT * FROM users --"},
            headers=_headers(),
        )
        assert resp.status_code == 200

    def test_customer_phone_with_sql(self):
        resp = client.post(
            "/api/v1/customers",
            json={"name": "正常客户", "phone": "'; DROP TABLE customers; --"},
            headers=_headers(),
        )
        assert resp.status_code in (200, 201, 400, 422)


class TestOrderSQLInjection:
    """订单端点 SQL 注入防护"""

    def test_search_order_with_sql_keyword(self):
        resp = client.get(
            "/api/v1/sales-orders",
            params={"keyword": "1 OR 1=1"},
            headers=_headers(),
        )
        assert resp.status_code == 200

    def test_order_uuid_path_with_sql(self):
        resp = client.get("/api/v1/sales-orders/1; DROP TABLE orders", headers=_headers())
        assert resp.status_code in (400, 404, 422)


class TestUserSQLInjection:
    """用户端点 SQL 注入防护"""

    def test_search_user_with_sql(self):
        resp = client.get(
            "/api/v1/users",
            params={"keyword": "' OR '1'='1"},
            headers=_headers(),
        )
        assert resp.status_code == 200

    def test_create_user_with_sql_username(self):
        """SQL 注入用户名不会破坏系统"""
        resp = client.post(
            "/api/v1/users",
            json={"username": "admin'--", "password": "TestPass123!"},
            headers=_headers(),
        )
        # 可能成功（名字被存储为字面值）或因验证规则拒绝
        assert resp.status_code in (200, 201, 400, 422)

    def test_update_user_display_name_with_sql(self):
        body = {"display_name": "Robert'); DROP TABLE users; --"}
        resp = client.put(f"/api/v1/users/{_admin_id}", json=body, headers=_headers())
        assert resp.status_code in (200, 400, 404)
        if resp.status_code == 200:
            assert resp.json()["success"] is True


class TestLoginSQLInjection:
    """登录端点 SQL 注入防护"""

    def test_login_with_sql_username(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin' OR '1'='1", "password": "anything"},
        )
        # 不应登录成功
        assert resp.status_code in (400, 401)

    def test_login_with_sql_password(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "sqli_admin", "password": "' OR '1'='1"},
        )
        assert resp.status_code in (400, 401)

    def test_login_with_classic_injection(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin'--", "password": "anything"},
        )
        assert resp.status_code in (400, 401)


class TestTableIntegrityAfterInjection:
    """SQL 注入尝试后表结构完整"""

    def test_products_table_still_exists(self):
        """注入尝试后商品表仍可用"""
        resp = client.get("/api/v1/products", headers=_headers())
        assert resp.status_code == 200

    def test_customers_table_still_exists(self):
        resp = client.get("/api/v1/customers", headers=_headers())
        assert resp.status_code == 200

    def test_orders_table_still_exists(self):
        resp = client.get("/api/v1/sales-orders", headers=_headers())
        assert resp.status_code == 200

    def test_users_table_still_exists(self):
        resp = client.get("/api/v1/users", headers=_headers())
        assert resp.status_code == 200
