"""API 错误响应结构一致性测试 — 确保 4 种异常处理器输出格式统一"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_error_resp.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}


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
            username="err_test_user",
            hashed_password=hash_password("TestPass123!"),
            display_name="错误测试",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_error_resp.db"):
        os.remove("./test_error_resp.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def _assert_error_structure(body: dict, expected_code: str | None = None):
    """验证错误响应的统一结构"""
    assert body["success"] is False, f"success 应为 False，实际: {body.get('success')}"
    assert "error" in body, f"缺少 error 字段: {body}"
    error = body["error"]
    assert isinstance(error, dict), f"error 应为 dict，实际: {type(error)}"
    assert "code" in error, f"error 缺少 code 字段: {error}"
    assert "message" in error, f"error 缺少 message 字段: {error}"
    assert isinstance(error["code"], str), f"error.code 应为 str: {error['code']}"
    assert isinstance(error["message"], str), f"error.message 应为 str: {error['message']}"
    if expected_code:
        assert error["code"] == expected_code, f"error.code 应为 {expected_code}，实际: {error['code']}"


# ═══════════════════════════════════════════════════════
# 0. 登录
# ═══════════════════════════════════════════════════════


def test_01_login():
    resp = client.post("/api/v1/auth/login", json={
        "username": "err_test_user", "password": "TestPass123!",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


# ═══════════════════════════════════════════════════════
# 1. HTTPException — dict detail（业务错误）
# ═══════════════════════════════════════════════════════


def test_02_404_resource_not_found():
    """GET 不存在的资源返回 404 + RESOURCE_NOT_FOUND"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/products/{fake_id}", headers=_auth())
    assert resp.status_code == 404
    _assert_error_structure(resp.json(), "RESOURCE_NOT_FOUND")


def test_03_404_customer_not_found():
    """GET 不存在的客户返回 404 + RESOURCE_NOT_FOUND"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/customers/{fake_id}", headers=_auth())
    assert resp.status_code == 404
    _assert_error_structure(resp.json(), "RESOURCE_NOT_FOUND")


def test_04_404_order_not_found():
    """GET 不存在的订单返回 404 + RESOURCE_NOT_FOUND"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/orders/{fake_id}", headers=_auth())
    assert resp.status_code == 404
    _assert_error_structure(resp.json(), "RESOURCE_NOT_FOUND")


def test_05_401_unauthorized():
    """无 token 访问受保护端点返回 401"""
    resp = client.get("/api/v1/products")
    assert resp.status_code == 401
    _assert_error_structure(resp.json())


def test_06_401_invalid_token():
    """无效 token 返回 401 + AUTH_UNAUTHORIZED"""
    resp = client.get("/api/v1/products", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
    _assert_error_structure(resp.json(), "AUTH_UNAUTHORIZED")


def test_07_400_validation_business():
    """业务层校验错误返回 400 — 创建商品时不存在的分类"""
    fake_category = str(uuid.uuid4())
    resp = client.post("/api/v1/products", json={
        "name": "测试商品",
        "sale_price": "10",
        "cost_price": "5",
        "category_id": fake_category,
    }, headers=_auth())
    assert resp.status_code == 400
    _assert_error_structure(resp.json(), "VALIDATION_FAILED")


# ═══════════════════════════════════════════════════════
# 2. RequestValidationError — 422 Pydantic 校验错误
# ═══════════════════════════════════════════════════════


def test_08_422_missing_required_field():
    """缺少必填字段返回 422 + VALIDATION_FAILED"""
    resp = client.post("/api/v1/products", json={}, headers=_auth())
    assert resp.status_code == 422
    _assert_error_structure(resp.json(), "VALIDATION_FAILED")


def test_09_422_invalid_type():
    """字段类型错误返回 422 + VALIDATION_FAILED"""
    resp = client.post("/api/v1/products", json={
        "name": "商品",
        "sale_price": "10",
        "cost_price": "5",
        "stock_quantity": "not_a_number",
    }, headers=_auth())
    assert resp.status_code == 422
    _assert_error_structure(resp.json(), "VALIDATION_FAILED")


def test_10_422_invalid_json():
    """无效 JSON body 返回 422"""
    resp = client.post(
        "/api/v1/products",
        content=b"{invalid json",
        headers={**_auth(), "Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    body = resp.json()
    _assert_error_structure(body)


def test_11_422_extra_fields_not_rejected():
    """多余字段不导致错误（Pydantic 默认忽略）"""
    resp = client.post("/api/v1/products", json={
        "name": "商品",
        "sale_price": "10",
        "cost_price": "5",
        "extra_field": "ignored",
    }, headers=_auth())
    # Pydantic 默认不拒绝额外字段，创建成功
    assert resp.status_code in (200, 201)


# ═══════════════════════════════════════════════════════
# 3. Starlette 路由异常 — 404/405
# ═══════════════════════════════════════════════════════


def test_12_404_unknown_route():
    """不存在的路由返回 404 + RESOURCE_NOT_FOUND"""
    resp = client.get("/api/v1/this-route-does-not-exist", headers=_auth())
    assert resp.status_code == 404
    _assert_error_structure(resp.json(), "RESOURCE_NOT_FOUND")


def test_13_405_method_not_allowed():
    """不支持的方法返回 405 + METHOD_NOT_ALLOWED"""
    resp = client.patch("/api/v1/products", headers=_auth())
    assert resp.status_code == 405
    _assert_error_structure(resp.json(), "METHOD_NOT_ALLOWED")


# ═══════════════════════════════════════════════════════
# 4. 跨模块一致性 — 所有 CRUD 端点 404 格式相同
# ═══════════════════════════════════════════════════════


def test_14_crud_404_consistent():
    """所有 CRUD 资源的 404 响应结构一致"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    endpoints = [
        f"/api/v1/products/{fake_id}",
        f"/api/v1/customers/{fake_id}",
        f"/api/v1/orders/{fake_id}",
    ]
    for url in endpoints:
        resp = client.get(url, headers=_auth())
        assert resp.status_code == 404, f"{url} 应返回 404"
        body = resp.json()
        _assert_error_structure(body, "RESOURCE_NOT_FOUND")


# ═══════════════════════════════════════════════════════
# 5. 成功响应包含 success=True
# ═══════════════════════════════════════════════════════


def test_15_success_response_has_success_true():
    """成功响应包含 success: true"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_16_success_response_has_data():
    """成功响应包含 data 字段"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


# ═══════════════════════════════════════════════════════
# 6. 错误响应不含 data 字段
# ═══════════════════════════════════════════════════════


def test_17_error_response_no_data_field():
    """错误响应不应包含 data 字段"""
    resp = client.get("/api/v1/products/00000000-0000-0000-0000-000000000000", headers=_auth())
    body = resp.json()
    assert "data" not in body or body["data"] is None


def test_18_401_error_no_data():
    """401 错误响应不含 data"""
    resp = client.get("/api/v1/products")
    body = resp.json()
    assert "data" not in body or body["data"] is None


# ═══════════════════════════════════════════════════════
# 7. 422 校验错误消息包含字段位置
# ═══════════════════════════════════════════════════════


def test_19_422_message_includes_field_location():
    """422 错误消息包含字段路径"""
    resp = client.post("/api/v1/products", json={"name": 123}, headers=_auth())
    assert resp.status_code == 422
    body = resp.json()
    msg = body["error"]["message"]
    assert "name" in msg.lower() or "body" in msg.lower()


# ═══════════════════════════════════════════════════════
# 8. 认证错误 403 — 权限不足
# ═══════════════════════════════════════════════════════


def test_20_forbidden_without_permission():
    """非 superuser 访问管理端点返回 403"""
    # 创建普通用户
    db = TestSession()
    try:
        normal = User(
            id=uuid.uuid4(),
            username="err_normal_user",
            hashed_password=hash_password("TestPass123!"),
            display_name="普通用户",
            is_active=True,
            is_superuser=False,
        )
        db.add(normal)
        db.commit()

        # 登录普通用户
        resp = client.post("/api/v1/auth/login", json={
            "username": "err_normal_user", "password": "TestPass123!",
        })
        normal_token = resp.json()["data"]["access_token"]

        # 访问用户管理端点
        resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {normal_token}"})
        assert resp.status_code == 403
        _assert_error_structure(resp.json())
    finally:
        db.close()
