"""请求日志中间件单元测试"""

import logging

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.request_log import RequestLogMiddleware


@pytest.fixture()
def app():
    async def api_endpoint(request):
        return PlainTextResponse("ok", headers={"Content-Length": "2"})

    async def static_endpoint(request):
        return PlainTextResponse("static")

    return Starlette(routes=[
        Route("/api/v1/test", api_endpoint),
        Route("/static/file.txt", static_endpoint),
    ])


@pytest.fixture()
def client(app):
    app.add_middleware(RequestLogMiddleware)
    return TestClient(app)


def test_response_time_header_on_api(client):
    """API 请求响应包含 X-Response-Time"""
    resp = client.get("/api/v1/test")
    assert "X-Response-Time" in resp.headers
    assert resp.headers["X-Response-Time"].endswith("ms")


def test_response_time_header_on_static(client):
    """非 API 请求也包含 X-Response-Time"""
    resp = client.get("/static/file.txt")
    assert "X-Response-Time" in resp.headers


def test_api_request_logged(client, caplog):
    """API 请求写入 app.request 日志"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/v1/test")
    assert len(caplog.records) >= 1
    record = caplog.records[0]
    assert "GET" in record.msg
    assert "/api/v1/test" in record.msg
    assert "200" in record.msg


def test_static_path_not_logged(client, caplog):
    """非 API 路径不写入日志"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/static/file.txt")
    # 确保没有 /static/ 路径的日志（可能有其他测试的残留）
    static_records = [r for r in caplog.records if "/static/" in r.msg]
    assert len(static_records) == 0


def test_extra_fields_populated(client, caplog):
    """日志记录包含结构化 extra_fields"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/v1/test")
    assert len(caplog.records) >= 1
    record = caplog.records[0]
    fields = getattr(record, "extra_fields", None)
    assert fields is not None
    assert fields["method"] == "GET"
    assert fields["path"] == "/api/v1/test"
    assert fields["status"] == 200
    assert "duration_ms" in fields
    assert fields["slow"] is False
    assert fields["resp_bytes"] == 2


def test_response_time_is_numeric(client):
    """X-Response-Time 值为数字+ms 格式"""
    resp = client.get("/api/v1/test")
    value = resp.headers["X-Response-Time"]
    num_part = value.replace("ms", "")
    assert float(num_part) >= 0
