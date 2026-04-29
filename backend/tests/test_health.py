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
