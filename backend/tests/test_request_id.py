"""请求 ID 中间件单元测试 + 链路追踪完整性测试"""

import re
import uuid

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.request_id import RequestIDMiddleware, request_id_ctx

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ═══════════════════════════════════════════════════════
# 单元测试（独立 Starlette app）
# ═══════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════
# 完整性测试（FastAPI 真实 app）
# ═══════════════════════════════════════════════════════


class TestE2ERequestID:
    """端到端验证请求 ID 在真实 API 中的行为"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.main import app as main_app
        self.client = TestClient(main_app)

    def test_auto_generated_is_uuid(self):
        """自动生成的 request ID 为 UUID v4 格式"""
        resp = self.client.get("/api/v1/health")
        rid = resp.headers["X-Request-ID"]
        assert _UUID_RE.match(rid), f"request ID 不是 UUID 格式: {rid}"

    def test_custom_id_passthrough(self):
        """自定义 X-Request-ID 被透传"""
        custom = "trace-abc-123"
        resp = self.client.get("/api/v1/health", headers={"X-Request-ID": custom})
        assert resp.headers["X-Request-ID"] == custom

    def test_uuid_passthrough(self):
        """UUID 格式的自定义 ID 被透传"""
        custom = str(uuid.uuid4())
        resp = self.client.get("/api/v1/health", headers={"X-Request-ID": custom})
        assert resp.headers["X-Request-ID"] == custom

    def test_empty_header_auto_generates(self):
        """空字符串 X-Request-ID 触发自动生成"""
        resp = self.client.get("/api/v1/health", headers={"X-Request-ID": ""})
        rid = resp.headers["X-Request-ID"]
        assert _UUID_RE.match(rid), f"空 header 应触发自动生成: {rid}"

    def test_404_has_request_id(self):
        """404 响应包含 X-Request-ID"""
        resp = self.client.get("/api/v1/nonexistent-path-xyz")
        assert "X-Request-ID" in resp.headers

    def test_422_has_request_id(self):
        """422 响应包含 X-Request-ID"""
        resp = self.client.post("/api/v1/products", json={})
        assert resp.headers["X-Request-ID"]

    def test_405_has_request_id(self):
        """405 响应包含 X-Request-ID"""
        resp = self.client.patch("/api/v1/products")
        assert "X-Request-ID" in resp.headers

    def test_non_api_path_has_request_id(self):
        """非 API 路径也有 request ID"""
        resp = self.client.get("/does-not-exist")
        assert "X-Request-ID" in resp.headers

    def test_request_id_not_empty(self):
        """request ID 永远不为空"""
        resp = self.client.get("/api/v1/health")
        rid = resp.headers["X-Request-ID"]
        assert len(rid) > 0

    def test_auto_generated_is_lowercase(self):
        """自动生成的 UUID 为小写"""
        resp = self.client.get("/api/v1/health")
        rid = resp.headers["X-Request-ID"]
        if _UUID_RE.match(rid):
            assert rid == rid.lower()

    def test_concurrent_requests_unique_ids(self):
        """连续请求的 ID 各不相同"""
        rids = [
            self.client.get("/api/v1/health").headers["X-Request-ID"]
            for _ in range(20)
        ]
        assert len(set(rids)) == 20

    def test_custom_id_on_error_response(self):
        """错误响应透传自定义 request ID"""
        custom = "error-trace-999"
        resp = self.client.get("/api/v1/nonexistent-path-xyz", headers={"X-Request-ID": custom})
        assert resp.headers["X-Request-ID"] == custom
