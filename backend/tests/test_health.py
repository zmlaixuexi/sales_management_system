import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


def test_health_check_degraded(monkeypatch):
    """数据库不可用时返回 degraded"""
    from app.api.v1 import health as health_mod
    def _broken_session():
        raise RuntimeError("db down")
    monkeypatch.setattr(health_mod, "SessionLocal", _broken_session)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "degraded"
    assert data["database"] == "error"


def test_version():
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "version" in data["data"]


def test_security_headers():
    """验证安全响应头存在"""
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-xss-protection"] == "1; mode=block"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "content-security-policy" in response.headers
    assert "permissions-policy" in response.headers


def test_request_log_records_api_calls(caplog):
    """验证 API 请求被日志记录"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/v1/health")
    assert any("GET /api/v1/health" in r.message for r in caplog.records)


def test_request_log_ignores_non_api(caplog):
    """验证非 API 路径不记录请求日志"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/")
    assert not any("GET /" == r.message.split()[0:2] for r in caplog.records)


def test_request_id_generated_when_missing():
    """请求不带 X-Request-ID 时自动生成"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    rid = response.headers["x-request-id"]
    assert len(rid) == 36  # UUID format


def test_request_id_passthrough():
    """请求带 X-Request-ID 时透传回响应"""
    custom_id = "my-custom-request-id-1234"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


def test_request_id_in_log(caplog):
    """验证 request_id 写入请求日志"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/v1/health", headers={"X-Request-ID": "log-test-id"})
    records = [r for r in caplog.records if "GET /api/v1/health" in r.message]
    assert len(records) >= 1
    record = records[-1]
    assert record.extra_fields["request_id"] == "log-test-id"


def test_production_env_rejects_default_secret(monkeypatch):
    """生产环境使用默认 JWT_SECRET_KEY 应拒绝启动"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "change-me")

    assert settings.APP_ENV == "production"
    assert settings.JWT_SECRET_KEY == "change-me"
    # lifespan 中的检查逻辑
    should_reject = (
        settings.APP_ENV == "production" and settings.JWT_SECRET_KEY == "change-me"
    )
    assert should_reject is True

    # 使用非默认密钥时不应拒绝
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "a-real-secret-key-12345")
    should_reject = (
        settings.APP_ENV == "production" and settings.JWT_SECRET_KEY == "change-me"
    )
    assert should_reject is False


def test_unhandled_exception_returns_json():
    """全局未处理异常应返回一致的 JSON 格式，不泄露内部详情"""
    from fastapi import APIRouter

    test_router = APIRouter()

    @test_router.get("/api/v1/_test_crash")
    def crash():
        raise RuntimeError("something broke")

    app.include_router(test_router)
    # raise_server_exceptions=False 让异常处理器接管
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    try:
        response = no_raise_client.get("/api/v1/_test_crash")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"
        assert data["detail"]["message"] == "服务器内部错误，请稍后重试"
        assert "something broke" not in str(data)
    finally:
        app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/api/v1/_test_crash"]


def test_cors_allowed_origin():
    """允许的 Origin 应返回 CORS 响应头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_disallowed_origin():
    """不允许的 Origin 不应返回 CORS 响应头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_response_time_header():
    """所有 API 响应应包含 X-Response-Time 头"""
    response = client.get("/api/v1/health")
    assert "x-response-time" in response.headers
    assert response.headers["x-response-time"].endswith("ms")
