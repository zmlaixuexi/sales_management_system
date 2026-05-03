"""请求 ID 中间件单元测试"""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.request_id import RequestIDMiddleware, request_id_ctx


@pytest.fixture()
def app():
    async def homepage(request):
        rid = request_id_ctx.get("")
        return PlainTextResponse(f"rid={rid}")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RequestIDMiddleware)
    return app


@pytest.fixture()
def client(app):
    return TestClient(app)


def test_generates_request_id_when_missing(client):
    """无 X-Request-ID 时自动生成"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


def test_passthrough_existing_request_id(client):
    """已有 X-Request-ID 时透传"""
    rid = "my-custom-id-12345"
    resp = client.get("/", headers={"X-Request-ID": rid})
    assert resp.headers["X-Request-ID"] == rid


def test_request_id_available_in_handler(client):
    """contextvars 中的 request_id 可在处理函数中读取"""
    rid = "test-rid-abc"
    resp = client.get("/", headers={"X-Request-ID": rid})
    assert f"rid={rid}" in resp.text


def test_different_requests_get_different_ids(client):
    """不同请求生成不同 ID"""
    resp1 = client.get("/")
    resp2 = client.get("/")
    assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]
