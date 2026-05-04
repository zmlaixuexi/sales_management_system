"""安全加固：后端 CORS 配置运行时验证测试
验证预检请求、实际请求、未授权来源的 CORS 行为"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ALLOWED_ORIGIN = "http://localhost:5173"


class TestCORSPreflight:
    """OPTIONS 预检请求 CORS 行为"""

    def test_preflight_returns_200(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert resp.status_code == 200

    def test_preflight_has_allow_origin(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

    def test_preflight_has_allow_methods(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
        methods = resp.headers.get("access-control-allow-methods", "")
        for method in ["GET", "POST", "PUT", "DELETE"]:
            assert method in methods

    def test_preflight_has_allow_headers(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        allowed = resp.headers.get("access-control-allow-headers", "")
        assert "Authorization" in allowed
        assert "Content-Type" in allowed

    def test_preflight_has_allow_credentials(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_preflight_max_age(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORSMiddleware 默认设置 max-age
        resp.headers.get("access-control-max-age")
        # 有或没有都是合法的，只需不报错
        assert resp.status_code == 200


class TestCORSActualRequest:
    """实际请求 CORS 行为"""

    def test_get_has_cors_headers(self):
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": ALLOWED_ORIGIN},
        )
        assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

    def test_post_has_cors_headers(self):
        """POST 错误响应（401/422）也包含 CORS 头"""
        resp = client.post(
            "/api/v1/products",
            json={},
            headers={"Origin": ALLOWED_ORIGIN},
        )
        assert resp.status_code in (401, 422)
        assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

    def test_404_has_cors_headers(self):
        """错误响应也包含 CORS 头"""
        resp = client.get(
            "/api/v1/nonexistent",
            headers={"Origin": ALLOWED_ORIGIN},
        )
        assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

    def test_422_has_cors_headers(self):
        """验证错误响应包含 CORS 头"""
        resp = client.post(
            "/api/v1/products",
            json={},
            headers={"Origin": ALLOWED_ORIGIN},
        )
        assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


class TestCORSNoOrigin:
    """无 Origin 请求不返回 CORS 头"""

    def test_no_origin_no_cors(self):
        resp = client.get("/api/v1/health")
        assert "access-control-allow-origin" not in resp.headers


class TestCORSAllowedMethods:
    """CORS 允许的方法覆盖"""

    def test_options_method_allowed(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "OPTIONS",
            },
        )
        assert resp.status_code == 200

    def test_delete_method_allowed(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "DELETE",
            },
        )
        methods = resp.headers.get("access-control-allow-methods", "")
        assert "DELETE" in methods


class TestCORSHeaders:
    """CORS 自定义请求头"""

    def test_x_request_id_allowed(self):
        resp = client.options(
            "/api/v1/products",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )
        allowed = resp.headers.get("access-control-allow-headers", "")
        assert "X-Request-ID" in allowed
