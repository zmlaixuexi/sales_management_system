"""中间件测试 — BodyLimitMiddleware / RequestLogMiddleware"""

import json
import logging
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.body_limit import BodyLimitMiddleware
from app.core.request_log import RequestLogMiddleware


# ─── BodyLimitMiddleware ────────────────────────────────────


def _make_app_with_body_limit(max_mb: int = 1):
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware)

    @app.post("/api/test")
    async def test_endpoint():
        return {"ok": True}

    @app.post("/api/upload")
    async def upload_endpoint():
        return {"ok": True}

    with patch("app.core.body_limit.settings") as mock_settings:
        mock_settings.MAX_JSON_BODY_MB = max_mb
        # Re-instantiate middleware with patched settings
        # (middleware reads settings at dispatch time, not init time)
        return app, mock_settings


def test_body_limit_allows_small_body():
    """小请求体正常通过"""
    app, mock_settings = _make_app_with_body_limit(1)
    mock_settings.MAX_JSON_BODY_MB = 1
    client = TestClient(app)
    resp = client.post("/api/test", json={"key": "value"})
    assert resp.status_code == 200


def test_body_limit_rejects_oversized_json():
    """超过限制的 JSON 请求体返回 413"""
    app, mock_settings = _make_app_with_body_limit(1)
    mock_settings.MAX_JSON_BODY_MB = 1
    client = TestClient(app)
    # 构造一个超过 1MB 的 body
    big_body = {"data": "x" * (1024 * 1024 + 100)}
    resp = client.post("/api/test", json=big_body)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_body_limit_exempts_multipart():
    """multipart/form-data 请求不受限制"""
    app, mock_settings = _make_app_with_body_limit(1)
    mock_settings.MAX_JSON_BODY_MB = 1
    client = TestClient(app)
    resp = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"x" * 2048 * 1024, "text/plain")},
    )
    assert resp.status_code == 200


def test_body_limit_exempts_get_requests():
    """GET 请求不受限制"""
    app, _ = _make_app_with_body_limit(0)
    app.add_api_route("/api/get-test", lambda: {"ok": True}, methods=["GET"])
    client = TestClient(app)
    resp = client.get("/api/get-test")
    assert resp.status_code == 200


# ─── RequestLogMiddleware ───────────────────────────────────


def test_request_log_records_api_calls(caplog):
    """API 请求被记录到 app.request 日志"""
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="app.request"):
        client = TestClient(app)
        resp = client.get("/api/v1/test")
        assert resp.status_code == 200

    log_records = [r for r in caplog.records if r.name == "app.request"]
    assert len(log_records) >= 1
    msg = log_records[0].msg
    assert "GET" in msg
    assert "/api/v1/test" in msg
    assert "200" in msg


def test_request_log_adds_response_time_header():
    """响应包含 X-Response-Time 头"""
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/test")
    assert "X-Response-Time" in resp.headers
    assert resp.headers["X-Response-Time"].endswith("ms")


def test_request_log_includes_response_size(caplog):
    """日志中包含响应体大小"""
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="app.request"):
        client = TestClient(app)
        resp = client.get("/api/v1/test")
        assert resp.status_code == 200

    log_records = [r for r in caplog.records if r.name == "app.request"]
    assert len(log_records) >= 1
    record = log_records[0]
    assert hasattr(record, "extra_fields")
    assert record.extra_fields["resp_bytes"] == len(resp.content)


def test_request_log_skips_non_api_paths(caplog):
    """非 API 路径不记录日志"""
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/favicon.ico")
    async def favicon():
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="app.request"):
        client = TestClient(app)
        resp = client.get("/favicon.ico")
        assert resp.status_code == 200

    log_records = [r for r in caplog.records if r.name == "app.request"]
    assert len(log_records) == 0


# ─── SecurityHeadersMiddleware ──────────────────────────────

from app.core.security_headers import SecurityHeadersMiddleware


def test_security_headers_present_on_api_responses():
    """API 响应包含安全头"""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/test")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" in resp.headers
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


def test_security_headers_present_on_non_api_responses():
    """非 API 路径也包含安全头"""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_security_headers_referrer_policy():
    """Referrer-Policy 头设置正确"""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/test")
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
