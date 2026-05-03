"""CORS 配置验证测试 — 覆盖预检请求、响应头、配置校验"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. CORS 预检请求 (OPTIONS)
# ═══════════════════════════════════════════════════════


class TestPreflight:
    def test_options_returns_200(self):
        """OPTIONS 预检请求返回 200"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.status_code == 200

    def test_options_has_cors_headers(self):
        """OPTIONS 响应包含 CORS 头"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in resp.headers

    def test_options_allows_get(self):
        """预检允许 GET 方法"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods

    def test_options_allows_post(self):
        """预检允许 POST 方法"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        })
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods

    def test_options_allows_put(self):
        """预检允许 PUT 方法"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
        })
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "PUT" in allow_methods

    def test_options_allows_delete(self):
        """预检允许 DELETE 方法"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        })
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "DELETE" in allow_methods

    def test_options_allows_authorization_header(self):
        """预检允许 Authorization 头"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        })
        allow_headers = resp.headers.get("access-control-allow-headers", "")
        assert "Authorization" in allow_headers

    def test_options_allows_content_type_header(self):
        """预检允许 Content-Type 头"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        allow_headers = resp.headers.get("access-control-allow-headers", "")
        assert "Content-Type" in allow_headers

    def test_options_allows_x_request_id(self):
        """预检允许 X-Request-ID 头"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        })
        allow_headers = resp.headers.get("access-control-allow-headers", "")
        assert "X-Request-ID" in allow_headers


# ═══════════════════════════════════════════════════════
# 2. CORS 实际请求响应头
# ═══════════════════════════════════════════════════════


class TestActualRequest:
    def test_allowed_origin_gets_cors_header(self):
        """允许的 Origin 获得 CORS 头"""
        resp = client.get("/api/v1/health", headers={
            "Origin": "http://localhost:5173",
        })
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_credentials_allowed(self):
        """allow-credentials 为 true"""
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.headers.get("access-control-allow-credentials") == "true"


# ═══════════════════════════════════════════════════════
# 3. CORS_ORIGINS 配置验证
# ═══════════════════════════════════════════════════════


class TestCorsConfig:
    def test_wildcard_rejected(self):
        """通配符 * 被拒绝"""
        with pytest.raises(ValidationError):
            Settings(CORS_ORIGINS="*")

    def test_empty_rejected(self):
        """空字符串被拒绝"""
        with pytest.raises(ValidationError):
            Settings(CORS_ORIGINS="")

    def test_no_protocol_rejected(self):
        """缺少协议前缀被拒绝"""
        with pytest.raises(ValidationError):
            Settings(CORS_ORIGINS="example.com")

    def test_single_origin_valid(self):
        """单个合法 origin 通过"""
        s = Settings(CORS_ORIGINS="http://localhost:3000")
        assert s.CORS_ORIGINS == "http://localhost:3000"

    def test_multiple_origins_valid(self):
        """多个合法 origin 通过"""
        s = Settings(CORS_ORIGINS="http://localhost:3000,https://example.com")
        assert "http://localhost:3000" in s.CORS_ORIGINS
        assert "https://example.com" in s.CORS_ORIGINS

    def test_https_origin_valid(self):
        """HTTPS origin 通过"""
        s = Settings(CORS_ORIGINS="https://prod.example.com")
        assert s.CORS_ORIGINS == "https://prod.example.com"
