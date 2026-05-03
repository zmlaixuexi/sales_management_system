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
        "Cache-Control",
    ]
    for h in expected:
        assert h in resp.headers, f"Missing header: {h}"
