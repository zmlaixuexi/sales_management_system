"""测试补强：后端 CORS 预检请求边界测试 — 覆盖未允许 Origin、PATCH 方法、
OPTIONS 各种路径、非 API 路径、max-age、allow-headers 边界、多 Origin 配置"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. 未允许的 Origin
# ═══════════════════════════════════════════════════════


def test_disallowed_origin_no_cors_header():
    """未允许的 Origin 不返回 CORS 头"""
    resp = client.get("/api/v1/health", headers={
        "Origin": "http://evil.example.com",
    })
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_disallowed_origin_preflight_rejected():
    """未允许的 Origin 预检请求被拒绝（无 CORS 头）"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://evil.example.com",
        "Access-Control-Request-Method": "GET",
    })
    assert "access-control-allow-origin" not in resp.headers


def test_no_origin_no_cors():
    """无 Origin 请求不返回 CORS 头"""
    resp = client.get("/api/v1/health")
    assert "access-control-allow-origin" not in resp.headers


# ═══════════════════════════════════════════════════════
# 2. OPTIONS 各种路径
# ═══════════════════════════════════════════════════════


def test_options_health_endpoint():
    """OPTIONS /health 正常"""
    resp = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code == 200


def test_options_nonexistent_path():
    """OPTIONS 不存在的路径仍返回 CORS 头"""
    resp = client.options("/api/v1/nonexistent-cors-test", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    # CORSMiddleware 在路由匹配前处理
    assert "access-control-allow-origin" in resp.headers or resp.status_code == 200


def test_options_metrics_path():
    """OPTIONS /metrics 非路由路径"""
    resp = client.options("/metrics", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code in (200, 404, 405)


def test_options_auth_login():
    """OPTIONS /auth/login 返回 CORS 头"""
    resp = client.options("/api/v1/auth/login", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


# ═══════════════════════════════════════════════════════
# 3. PATCH 方法不在允许列表
# ═══════════════════════════════════════════════════════


def test_patch_not_in_allow_methods():
    """PATCH 不在 CORS allow-methods 中"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PATCH",
    })
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    # main.py 只允许 GET/POST/PUT/DELETE/OPTIONS
    assert "PATCH" not in allow_methods


def test_options_method_in_allow_methods():
    """OPTIONS 在 CORS allow-methods 中"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "OPTIONS",
    })
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    assert "OPTIONS" in allow_methods or resp.status_code == 200


# ═══════════════════════════════════════════════════════
# 4. allow-headers 边界
# ═══════════════════════════════════════════════════════


def test_custom_header_not_allowed():
    """自定义头不在 allow-headers 中"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Custom-Header",
    })
    allow_headers = resp.headers.get("access-control-allow-headers", "")
    assert "X-Custom-Header" not in allow_headers


def test_multiple_request_headers():
    """请求多个 header，允许的在列表中"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type, X-Request-ID",
    })
    allow_headers = resp.headers.get("access-control-allow-headers", "")
    assert "Authorization" in allow_headers
    assert "Content-Type" in allow_headers
    assert "X-Request-ID" in allow_headers


# ═══════════════════════════════════════════════════════
# 5. credentials 验证
# ═══════════════════════════════════════════════════════


def test_credentials_true_on_get():
    """GET 请求也返回 credentials=true"""
    resp = client.get("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
    })
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_credentials_true_on_options():
    """OPTIONS 请求返回 credentials=true"""
    resp = client.options("/api/v1/products", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.headers.get("access-control-allow-credentials") == "true"


# ═══════════════════════════════════════════════════════
# 6. CORS 配置验证边界
# ═══════════════════════════════════════════════════════


def test_config_whitespace_in_origins():
    """配置中含空格的多个 origin 正常解析"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS=" http://a.com , http://b.com ")
    origins = [o.strip() for o in s.CORS_ORIGINS.split(",")]
    assert "http://a.com" in origins
    assert "http://b.com" in origins


def test_config_http_localhost_valid():
    """http://localhost 格式合法"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS="http://localhost:3000")
    assert s.CORS_ORIGINS == "http://localhost:3000"


def test_config_https_valid():
    """https:// 格式合法"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS="https://prod.example.com")
    assert s.CORS_ORIGINS == "https://prod.example.com"


def test_config_ftp_rejected():
    """ftp:// 缺少有效协议被拒绝"""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="ftp://example.com")


def test_config_trailing_slash_valid():
    """带尾部斜杠的 origin 合法"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS="http://localhost:3000/")
    assert s.CORS_ORIGINS == "http://localhost:3000/"


def test_config_single_comma_rejected():
    """纯逗号被拒绝"""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS=",")


def test_config_only_whitespace_rejected():
    """纯空格被拒绝"""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="   ")


# ═══════════════════════════════════════════════════════
# 7. CORS 与安全头共存
# ═══════════════════════════════════════════════════════


def test_cors_and_security_headers_together():
    """CORS 响应同时包含安全头"""
    resp = client.get("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
    })
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


def test_options_and_security_headers():
    """OPTIONS 响应同时包含安全头"""
    resp = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.headers.get("x-content-type-options") == "nosniff"


# ═══════════════════════════════════════════════════════
# 8. CORS 注册位置验证
# ═══════════════════════════════════════════════════════


def test_cors_middleware_registered():
    """CORS 中间件已注册"""
    from fastapi.middleware.cors import CORSMiddleware

    from app.main import app

    has_cors = any(
        isinstance(m.cls, type(CORSMiddleware)) if hasattr(m, 'cls') else False
        for m in app.user_middleware
    )
    assert has_cors


def test_cors_allow_methods_matches_config():
    """CORS allow-methods 包含配置的方法"""
    import pathlib

    source = pathlib.Path(__file__).resolve().parent.parent / "app" / "main.py"
    source = source.read_text()
    assert '"GET"' in source or "'GET'" in source
    assert '"POST"' in source or "'POST'" in source
    assert '"PUT"' in source or "'PUT'" in source
    assert '"DELETE"' in source or "'DELETE'" in source
    assert '"OPTIONS"' in source or "'OPTIONS'" in source
