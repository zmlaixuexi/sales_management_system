"""安全响应头中间件单元测试"""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.security_headers import SecurityHeadersMiddleware


@pytest.fixture()
def client():
    async def homepage(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware)
    return TestClient(app)


def test_x_content_type_options(client):
    assert client.get("/").headers["X-Content-Type-Options"] == "nosniff"


def test_x_frame_options(client):
    assert client.get("/").headers["X-Frame-Options"] == "DENY"


def test_x_xss_protection(client):
    assert client.get("/").headers["X-XSS-Protection"] == "1; mode=block"


def test_referrer_policy(client):
    assert client.get("/").headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy(client):
    assert client.get("/").headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_content_security_policy(client):
    assert client.get("/").headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_cache_control(client):
    assert client.get("/").headers["Cache-Control"] == "no-store"


def test_cross_origin_opener_policy(client):
    assert client.get("/").headers["Cross-Origin-Opener-Policy"] == "same-origin"


def test_cross_origin_resource_policy(client):
    assert client.get("/").headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_hsts_not_set_on_http(client):
    """HTTP 请求不添加 HSTS"""
    resp = client.get("/")
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_set_on_https():
    """HTTPS 请求添加 HSTS"""
    async def homepage(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware)
    with TestClient(app, base_url="https://testserver") as c:
        resp = c.get("/")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]


def test_all_headers_present(client):
    """所有安全头都存在"""
    resp = client.get("/")
    expected = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Referrer-Policy",
        "Permissions-Policy",
        "Content-Security-Policy",
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
        "Cache-Control",
    ]
    for h in expected:
        assert h in resp.headers, f"Missing header: {h}"
