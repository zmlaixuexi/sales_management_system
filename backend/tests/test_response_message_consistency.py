"""文档完善：后端端点响应 message 一致性测试
验证所有 JSON 响应端点返回一致的 {success, data, message} 或 {success, error} 结构"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_response_msg.db"
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
        id=_admin_id, username="msg_admin", display_name="管理员",
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
        os.remove("test_response_msg.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


def _check_success_body(body):
    """验证成功响应结构"""
    assert "success" in body
    assert body["success"] is True
    assert "data" in body
    assert "message" in body
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 0


def _check_error_body(body):
    """验证错误响应结构"""
    assert "success" in body
    assert body["success"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


class TestAuthResponseMessage:
    """认证端点响应结构"""

    def test_login_success_structure(self):
        body = {"username": "msg_admin", "password": "TestPass123!"}
        resp = client.post("/api/v1/auth/login", json=body)
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_login_wrong_password_structure(self):
        body = {"username": "msg_admin", "password": "wrong"}
        resp = client.post("/api/v1/auth/login", json=body)
        assert resp.status_code in (400, 401)
        _check_error_body(resp.json())

    def test_me_success_structure(self):
        resp = client.get("/api/v1/auth/me", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_me_no_token_structure(self):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        _check_error_body(resp.json())

    def test_refresh_invalid_structure(self):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code in (400, 401)
        _check_error_body(resp.json())


class TestUserResponseMessage:
    """用户端点响应结构"""

    def test_list_users_structure(self):
        resp = client.get("/api/v1/users", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]

    def test_create_user_duplicate_structure(self):
        """创建已存在用户名返回错误结构"""
        body = {"username": "msg_admin", "password": "TestPass123!"}
        resp = client.post("/api/v1/users", json=body, headers=_headers())
        assert resp.status_code in (400, 409)
        _check_error_body(resp.json())

    def test_update_user_structure(self):
        body = {"display_name": "更新名"}
        resp = client.put(f"/api/v1/users/{_admin_id}", json=body, headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_update_user_not_found_structure(self):
        body = {"display_name": "更新名"}
        uid = str(uuid.uuid4())
        resp = client.put(f"/api/v1/users/{uid}", json=body, headers=_headers())
        assert resp.status_code in (400, 404)
        _check_error_body(resp.json())


class TestProductResponseMessage:
    """商品端点响应结构"""

    def test_list_products_structure(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]

    def test_create_product_structure(self):
        body = {"name": f"测试商品_{uuid.uuid4().hex[:8]}"}
        resp = client.post("/api/v1/products", json=body, headers=_headers())
        assert resp.status_code in (200, 201)
        _check_success_body(resp.json())

    def test_get_product_not_found_structure(self):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/products/{uid}", headers=_headers())
        assert resp.status_code == 404
        _check_error_body(resp.json())

    def test_create_product_validation_structure(self):
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        assert resp.status_code == 422
        _check_error_body(resp.json())


class TestCustomerResponseMessage:
    """客户端点响应结构"""

    def test_list_customers_structure(self):
        resp = client.get("/api/v1/customers", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]

    def test_create_customer_structure(self):
        body = {"name": f"测试客户_{uuid.uuid4().hex[:8]}"}
        resp = client.post("/api/v1/customers", json=body, headers=_headers())
        assert resp.status_code in (200, 201)
        _check_success_body(resp.json())

    def test_get_customer_not_found_structure(self):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/customers/{uid}", headers=_headers())
        assert resp.status_code == 404
        _check_error_body(resp.json())


class TestOrderResponseMessage:
    """订单端点响应结构"""

    def test_list_orders_structure(self):
        resp = client.get("/api/v1/sales-orders", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]

    def test_get_order_not_found_structure(self):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/sales-orders/{uid}", headers=_headers())
        assert resp.status_code == 404
        _check_error_body(resp.json())

    def test_create_order_validation_structure(self):
        resp = client.post("/api/v1/sales-orders", json={}, headers=_headers())
        assert resp.status_code == 422
        _check_error_body(resp.json())


class TestPaymentResponseMessage:
    """收款端点响应结构"""

    def test_list_payments_structure(self):
        resp = client.get("/api/v1/payments", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]


class TestRoleResponseMessage:
    """角色端点响应结构"""

    def test_list_roles_structure(self):
        resp = client.get("/api/v1/roles", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_permissions_structure(self):
        resp = client.get("/api/v1/roles/permissions", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())


class TestInventoryResponseMessage:
    """库存端点响应结构"""

    def test_list_movements_structure(self):
        resp = client.get("/api/v1/inventory/movements", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]


class TestAuditLogResponseMessage:
    """审计日志端点响应结构"""

    def test_list_audit_logs_structure(self):
        resp = client.get("/api/v1/audit-logs", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        _check_success_body(body)
        assert "items" in body["data"]

    def test_audit_actions_structure(self):
        resp = client.get("/api/v1/audit-logs/actions", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())


class TestReportResponseMessage:
    """报表端点响应结构"""

    def test_sales_summary_structure(self):
        resp = client.get("/api/v1/reports/sales-summary", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_sales_trend_structure(self):
        resp = client.get("/api/v1/reports/sales-trend", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_product_ranking_structure(self):
        resp = client.get("/api/v1/reports/product-ranking", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_customer_ranking_structure(self):
        resp = client.get("/api/v1/reports/customer-ranking", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_salesperson_ranking_structure(self):
        resp = client.get("/api/v1/reports/salesperson-ranking", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_inventory_warning_structure(self):
        resp = client.get("/api/v1/reports/inventory-warning", headers=_headers())
        assert resp.status_code == 200
        _check_success_body(resp.json())


class TestHealthVersionResponseMessage:
    """健康检查/版本端点响应结构"""

    def test_health_structure(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        _check_success_body(resp.json())

    def test_version_structure(self):
        resp = client.get("/api/v1/version")
        assert resp.status_code == 200
        _check_success_body(resp.json())


class TestExportNonJsonResponse:
    """导出端点返回 CSV（非 JSON）"""

    def test_export_products_is_csv(self):
        resp = client.get("/api/v1/exports/products", headers=_headers())
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_customers_is_csv(self):
        resp = client.get("/api/v1/exports/customers", headers=_headers())
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_orders_is_csv(self):
        resp = client.get("/api/v1/exports/orders", headers=_headers())
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_payments_is_csv(self):
        resp = client.get("/api/v1/exports/payments", headers=_headers())
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")


class TestRequestIdInResponses:
    """响应包含 request_id"""

    def test_success_has_request_id(self):
        resp = client.get("/api/v1/products", headers=_headers())
        body = resp.json()
        assert "request_id" in body
        assert len(body["request_id"]) > 0

    def test_error_has_request_id(self):
        uid = str(uuid.uuid4())
        resp = client.get(f"/api/v1/products/{uid}", headers=_headers())
        body = resp.json()
        assert "request_id" in body

    def test_422_has_request_id(self):
        resp = client.post("/api/v1/products", json={}, headers=_headers())
        body = resp.json()
        assert "request_id" in body


class TestMessageNonEmpty:
    """成功响应 message 不为空且使用语义化文案"""

    def test_product_list_message(self):
        """分页列表使用 '查询成功'"""
        resp = client.get("/api/v1/products", headers=_headers())
        assert resp.json()["message"] == "查询成功"

    def test_customer_list_message(self):
        resp = client.get("/api/v1/customers", headers=_headers())
        assert resp.json()["message"] == "查询成功"

    def test_order_list_message(self):
        resp = client.get("/api/v1/sales-orders", headers=_headers())
        assert resp.json()["message"] == "查询成功"

    def test_user_list_message(self):
        resp = client.get("/api/v1/users", headers=_headers())
        assert resp.json()["message"] == "查询成功"

    def test_payment_list_message(self):
        resp = client.get("/api/v1/payments", headers=_headers())
        assert resp.json()["message"] == "查询成功"

    def test_role_list_message(self):
        """非分页列表使用默认 '操作成功'"""
        resp = client.get("/api/v1/roles", headers=_headers())
        assert resp.json()["message"] == "操作成功"

    def test_login_success_message(self):
        body = {"username": "msg_admin", "password": "TestPass123!"}
        resp = client.post("/api/v1/auth/login", json=body)
        msg = resp.json()["message"]
        assert isinstance(msg, str) and len(msg) > 0
