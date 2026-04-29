import logging
from unittest.mock import patch

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
