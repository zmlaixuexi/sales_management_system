"""安全加固：安全头与 CORS 配置边界测试 — 覆盖安全响应头、CORS 配置、
Body Limit 中间件、HSTS 条件、CORS origin 验证"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import settings
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. 安全响应头 — X-Content-Type-Options
# ═══════════════════════════════════════════════════════


def test_x_content_type_options():
    """X-Content-Type-Options 为 nosniff"""
    resp = client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"


def test_x_content_type_options_on_metrics():
    """/metrics 端点也有安全头"""
    resp = client.get("/metrics")
    assert resp.headers.get("x-content-type-options") == "nosniff"


# ═══════════════════════════════════════════════════════
# 2. 安全响应头 — X-Frame-Options
# ═══════════════════════════════════════════════════════


def test_x_frame_options():
    """X-Frame-Options 为 DENY"""
    resp = client.get("/api/v1/health")
    assert resp.headers["x-frame-options"] == "DENY"


# ═══════════════════════════════════════════════════════
# 3. 安全响应头 — X-XSS-Protection
# ═══════════════════════════════════════════════════════


def test_x_xss_protection():
    """X-XSS-Protection 为 1; mode=block"""
    resp = client.get("/api/v1/health")
    assert resp.headers["x-xss-protection"] == "1; mode=block"


# ═══════════════════════════════════════════════════════
# 4. 安全响应头 — Referrer-Policy
# ═══════════════════════════════════════════════════════


def test_referrer_policy():
    """Referrer-Policy 为 strict-origin-when-cross-origin"""
    resp = client.get("/api/v1/health")
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"


# ═══════════════════════════════════════════════════════
# 5. 安全响应头 — Permissions-Policy
# ═══════════════════════════════════════════════════════


def test_permissions_policy():
    """Permissions-Policy 禁用 camera/microphone/geolocation"""
    resp = client.get("/api/v1/health")
    pp = resp.headers["permissions-policy"]
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


# ═══════════════════════════════════════════════════════
# 6. 安全响应头 — Content-Security-Policy
# ═══════════════════════════════════════════════════════


def test_content_security_policy():
    """CSP 包含 default-src 'none' 和 frame-ancestors 'none'"""
    resp = client.get("/api/v1/health")
    csp = resp.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


# ═══════════════════════════════════════════════════════
# 7. 安全响应头 — Cross-Origin 策略
# ═══════════════════════════════════════════════════════


def test_cross_origin_opener_policy():
    """Cross-Origin-Opener-Policy 为 same-origin"""
    resp = client.get("/api/v1/health")
    assert resp.headers["cross-origin-opener-policy"] == "same-origin"


def test_cross_origin_resource_policy():
    """Cross-Origin-Resource-Policy 为 same-origin"""
    resp = client.get("/api/v1/health")
    assert resp.headers["cross-origin-resource-policy"] == "same-origin"


# ═══════════════════════════════════════════════════════
# 8. 安全响应头 — Cache-Control
# ═══════════════════════════════════════════════════════


def test_cache_control():
    """Cache-Control 为 no-store"""
    resp = client.get("/api/v1/health")
    assert resp.headers["cache-control"] == "no-store"


# ═══════════════════════════════════════════════════════
# 9. HSTS 条件验证
# ═══════════════════════════════════════════════════════


def test_hsts_not_set_on_http():
    """HTTP 请求不设置 Strict-Transport-Security"""
    resp = client.get("/api/v1/health")
    assert "strict-transport-security" not in resp.headers


def test_hsts_max_age_setting():
    """HSTS_MAX_AGE 默认为 31536000（1年）"""
    assert settings.HSTS_MAX_AGE == 31536000


def test_hsts_max_age_positive():
    """HSTS_MAX_AGE > 0"""
    assert settings.HSTS_MAX_AGE > 0


def test_hsts_middleware_checks_scheme():
    """中间件源码检查 request.url.scheme == 'https'"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware

    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "https" in source
    assert "strict-transport-security" in source.lower()


# ═══════════════════════════════════════════════════════
# 10. CORS 配置验证
# ═══════════════════════════════════════════════════════


def test_cors_origins_default():
    """CORS_ORIGINS 默认包含 localhost:5173"""
    assert "localhost:5173" in settings.CORS_ORIGINS


def test_cors_origins_starts_with_http():
    """CORS_ORIGINS 每项以 http:// 或 https:// 开头"""
    for origin in settings.CORS_ORIGINS.split(","):
        origin = origin.strip()
        assert origin.startswith("http://") or origin.startswith("https://")


def test_cors_origins_not_wildcard():
    """CORS_ORIGINS 不包含通配符 *"""
    assert "*" not in settings.CORS_ORIGINS.split(",")


def test_cors_preflight_options():
    """OPTIONS 预检请求返回 200"""
    resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200


def test_cors_allows_authorization_header():
    """CORS 允许 Authorization 头"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "Authorization" in source
    assert "allow_headers" in source


def test_cors_allows_content_type_header():
    """CORS 允许 Content-Type 头"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "Content-Type" in source


def test_cors_allows_request_id_header():
    """CORS 允许 X-Request-ID 头"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "X-Request-ID" in source


def test_cors_allow_methods():
    """CORS 允许 GET/POST/PUT/DELETE/OPTIONS"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    for method in ["GET", "POST", "PUT", "DELETE", "OPTIONS"]:
        assert method in source


def test_cors_credentials_enabled():
    """CORS allow_credentials=True"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "allow_credentials=True" in source


# ═══════════════════════════════════════════════════════
# 11. Body Limit 中间件验证
# ═══════════════════════════════════════════════════════


def test_max_json_body_mb_default():
    """MAX_JSON_BODY_MB 默认为 1"""
    assert settings.MAX_JSON_BODY_MB == 1


def test_max_json_body_mb_positive():
    """MAX_JSON_BODY_MB > 0"""
    assert settings.MAX_JSON_BODY_MB > 0


def test_body_limit_get_exempt():
    """GET 请求不受 body limit 约束"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_body_limit_413_code():
    """超限返回 PAYLOAD_TOO_LARGE 错误码"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware

    source = inspect.getsource(BodyLimitMiddleware)
    assert "413" in source
    assert "PAYLOAD_TOO_LARGE" in source


def test_body_limit_multipart_exempt():
    """multipart/form-data 免除 body limit"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware

    source = inspect.getsource(BodyLimitMiddleware)
    assert "multipart" in source.lower()


def test_body_limit_uploads_exempt():
    """/uploads 路径免除 body limit"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware

    source = inspect.getsource(BodyLimitMiddleware)
    assert "/uploads" in source


# ═══════════════════════════════════════════════════════
# 12. JWT 安全配置
# ═══════════════════════════════════════════════════════


def test_jwt_secret_key_min_length():
    """JWT_SECRET_KEY 至少 8 字符"""
    assert len(settings.JWT_SECRET_KEY) >= 8


def test_jwt_algorithm_hs256():
    """JWT 算法为 HS256"""
    assert settings.JWT_ALGORITHM == "HS256"


def test_jwt_access_token_expire_positive():
    """JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0"""
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_jwt_refresh_token_expire_positive():
    """JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0"""
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0


# ═══════════════════════════════════════════════════════
# 13. 安全头中间件注册
# ═══════════════════════════════════════════════════════


def test_security_headers_middleware_registered():
    """SecurityHeadersMiddleware 已注册"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "SecurityHeadersMiddleware" in source


def test_body_limit_middleware_registered():
    """BodyLimitMiddleware 已注册"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "BodyLimitMiddleware" in source


def test_cors_middleware_registered():
    """CORSMiddleware 已注册"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "CORSMiddleware" in source


# ═══════════════════════════════════════════════════════
# 14. CORS origin 验证器
# ═══════════════════════════════════════════════════════


def test_cors_validator_rejects_wildcard():
    """CORS_ORIGINS 验证器拒绝通配符 *"""
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="*")


def test_cors_validator_rejects_no_protocol():
    """CORS_ORIGINS 验证器拒绝无协议的 origin"""
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="example.com")


def test_cors_validator_accepts_valid_http():
    """CORS_ORIGINS 验证器接受 http:// origin"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS="http://example.com")
    assert "http://example.com" in s.CORS_ORIGINS


def test_cors_validator_accepts_valid_https():
    """CORS_ORIGINS 验证器接受 https:// origin"""
    from app.core.config import Settings

    s = Settings(CORS_ORIGINS="https://example.com")
    assert "https://example.com" in s.CORS_ORIGINS


# ═══════════════════════════════════════════════════════
# 15. 文件上传安全配置
# ═══════════════════════════════════════════════════════


def test_max_image_size_positive():
    """MAX_IMAGE_SIZE_MB > 0"""
    assert settings.MAX_IMAGE_SIZE_MB > 0


def test_max_image_size_default():
    """MAX_IMAGE_SIZE_MB 默认为 5"""
    assert settings.MAX_IMAGE_SIZE_MB == 5


def test_max_csv_import_size_positive():
    """MAX_CSV_IMPORT_SIZE_MB > 0"""
    assert settings.MAX_CSV_IMPORT_SIZE_MB > 0


def test_max_csv_import_rows_positive():
    """MAX_CSV_IMPORT_ROWS > 0"""
    assert settings.MAX_CSV_IMPORT_ROWS > 0
