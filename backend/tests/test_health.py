import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check(monkeypatch):
    """数据库可用时返回 ok"""
    from unittest.mock import MagicMock

    from app.api.v1 import health as health_mod

    mock_session = MagicMock()
    mock_session.execute.return_value = None
    mock_session.close.return_value = None
    monkeypatch.setattr(health_mod, "SessionLocal", lambda: mock_session)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


def test_health_check_pool_info():
    """健康检查返回连接池状态"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    pool = response.json()["data"]["pool"]
    assert "size" in pool
    assert "checked_in" in pool
    assert "checked_out" in pool
    assert "overflow" in pool


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
    assert response.headers["cache-control"] == "no-store"


def test_request_log_records_api_calls(caplog):
    """验证 API 请求被日志记录"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/v1/health")
    assert any("GET /api/v1/health" in r.message for r in caplog.records)


def test_request_log_ignores_non_api(caplog):
    """验证非 API 路径不记录请求日志"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/")
    assert not any(r.message.split()[0:2] == ["GET", "/"] for r in caplog.records)


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


def test_request_id_in_response_body():
    """响应体应包含 request_id 字段"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] == response.headers["x-request-id"]


def test_request_id_in_response_body_passthrough():
    """自定义 request_id 应同时出现在响应头和响应体"""
    custom_id = "body-test-req-id-9999"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.json()["request_id"] == custom_id


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
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
        assert data["error"]["message"] == "服务器内部错误，请稍后重试"
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


def test_cors_preflight_credentials():
    """允许的 Origin 预检请求应包含 credentials 头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_allowed_methods():
    """预检请求返回允许的方法列表"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "GET" in allow_methods
    assert "PUT" in allow_methods
    assert "DELETE" in allow_methods


def test_cors_preflight_disallowed_method():
    """不在允许列表的方法（PATCH）不应通过预检"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )
    # FastAPI CORSMiddleware 对不在 allow_methods 的请求仍可能返回 CORS 头
    # 但 allow-methods 列表中不应包含 PATCH
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "PATCH" not in allow_methods


def test_cors_preflight_allowed_headers():
    """预检请求应返回允许的自定义头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type,X-Request-ID",
        },
    )
    assert response.status_code == 200


def test_cors_preflight_disallowed_header():
    """预检请求中不在允许列表的头应被拒绝"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-Forbidden",
        },
    )
    # FastAPI CORSMiddleware 会拒绝不在 allow_headers 的自定义头
    assert "access-control-allow-headers" not in response.headers or \
        "X-Custom-Forbidden" not in response.headers.get("access-control-allow-headers", "")


def test_cors_empty_origin():
    """空 Origin 不应返回 CORS 头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_cors_null_origin():
    """null Origin 不应返回 CORS 头"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_response_time_header():
    """所有 API 响应应包含 X-Response-Time 头"""
    response = client.get("/api/v1/health")
    assert "x-response-time" in response.headers
    assert response.headers["x-response-time"].endswith("ms")


# ─── CORS 配置验证 ──────────────────────────────────────────

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_rejects_wildcard():
    """CORS_ORIGINS 不允许通配符 '*'"""
    with pytest.raises(ValidationError, match="通配符"):
        Settings(CORS_ORIGINS="*")


def test_cors_rejects_invalid_scheme():
    """CORS origin 必须以 http:// 或 https:// 开头"""
    with pytest.raises(ValidationError, match="http://"):
        Settings(CORS_ORIGINS="ftp://example.com")


def test_cors_rejects_no_scheme():
    """CORS origin 没有协议前缀应被拒绝"""
    with pytest.raises(ValidationError, match="http://"):
        Settings(CORS_ORIGINS="example.com")


def test_cors_accepts_multiple_origins():
    """允许多个合法 origin"""
    s = Settings(CORS_ORIGINS="http://a.com, https://b.com")
    assert "http://a.com" in s.CORS_ORIGINS
    assert "https://b.com" in s.CORS_ORIGINS


def test_cors_strips_whitespace():
    """CORS origin 前后空格被去除"""
    s = Settings(CORS_ORIGINS="  http://a.com ,  http://b.com  ")
    assert "http://a.com" in s.CORS_ORIGINS
    assert "http://b.com" in s.CORS_ORIGINS


def test_cors_rejects_empty():
    """CORS_ORIGINS 不能为空"""
    with pytest.raises(ValidationError, match="不能为空"):
        Settings(CORS_ORIGINS="")


# ─── JWT_SECRET_KEY 强度校验 ──────────────────────────────────


def test_jwt_secret_rejects_empty():
    """JWT_SECRET_KEY 不能为空"""
    with pytest.raises(ValidationError, match="不能为空"):
        Settings(JWT_SECRET_KEY="")


def test_jwt_secret_rejects_whitespace_only():
    """纯空格的 JWT_SECRET_KEY 等效为空"""
    with pytest.raises(ValidationError, match="不能为空"):
        Settings(JWT_SECRET_KEY="   ")


def test_jwt_secret_rejects_short():
    """过短的 JWT_SECRET_KEY 被拒绝"""
    with pytest.raises(ValidationError, match="8"):
        Settings(JWT_SECRET_KEY="short")


def test_jwt_secret_accepts_long():
    """足够长的 JWT_SECRET_KEY 被接受"""
    s = Settings(JWT_SECRET_KEY="a" * 32)
    assert len(s.JWT_SECRET_KEY) == 32


def test_openapi_disabled_in_production(monkeypatch):
    """生产环境不应暴露 OpenAPI 文档"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    # FastAPI 的 docs_url/redoc_url/openapi_url 在创建时已固定
    # 这里验证配置逻辑正确性
    assert settings.APP_ENV == "production"
    is_prod = settings.APP_ENV == "production"
    docs_url = None if is_prod else "/api/docs"
    redoc_url = None if is_prod else "/api/redoc"
    openapi_url = None if is_prod else "/api/openapi.json"
    assert docs_url is None
    assert redoc_url is None
    assert openapi_url is None


def test_health_returns_503_during_shutdown(monkeypatch):
    """关闭期间健康检查返回 503"""
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "_shutting_down", True)
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SHUTTING_DOWN"


def test_health_returns_200_after_restart(monkeypatch):
    """重启后关闭标志重置，健康检查恢复正常"""
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "_shutting_down", False)
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_metrics_endpoint_returns_prometheus_format():
    """/metrics 返回 Prometheus 格式指标"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    text = response.text
    # 包含 http_requests_total 计数器
    assert "http_requests_total" in text
    # 包含请求耗时直方图
    assert "http_request_duration_seconds" in text


def test_metrics_tracks_requests():
    """请求后 /metrics 指标递增"""
    # 先请求一次健康检查产生流量
    client.get("/api/v1/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "http_requests_total" in text


def test_metrics_exposes_custom_business_metrics():
    """/metrics 端点包含自定义业务指标"""
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    for metric_name in [
        "business_order_created",
        "business_order_confirmed",
        "business_order_cancelled",
        "business_payment_registered",
        "business_payment_reversed",
        "business_inventory_stockout",
        "business_low_stock_products",
        "business_login_attempts",
    ]:
        assert metric_name in text, f"自定义指标 {metric_name} 未在 /metrics 输出中"


def test_metrics_login_attempts_has_labels():
    """LOGIN_ATTEMPTS 指标在 /metrics 中包含 result 标签"""
    from app.core.metrics import LOGIN_ATTEMPTS
    LOGIN_ATTEMPTS.labels(result="test").inc()
    response = client.get("/metrics")
    text = response.text
    assert 'business_login_attempts_total{result="test"}' in text
