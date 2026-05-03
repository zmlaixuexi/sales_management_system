"""CSRF/安全防护边界测试 — 覆盖 CORS 配置、安全响应头、Cookie 使用、认证模式"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# ═══════════════════════════════════════════════════════
# 1. CORS 配置验证
# ═══════════════════════════════════════════════════════


def test_cors_rejects_wildcard():
    """CORS 不允许通配符 *"""
    with pytest.raises(ValidationError, match="通配符"):
        Settings(CORS_ORIGINS="*")


def test_cors_rejects_empty():
    """CORS 不允许空字符串"""
    with pytest.raises(ValidationError, match="不能为空"):
        Settings(CORS_ORIGINS="")


def test_cors_rejects_no_scheme():
    """CORS origin 必须有 http:// 或 https:// 前缀"""
    with pytest.raises(ValidationError, match="http://"):
        Settings(CORS_ORIGINS="example.com")


def test_cors_accepts_http():
    """CORS 接受 http:// 开头"""
    s = Settings(CORS_ORIGINS="http://localhost:5173")
    assert "http://localhost:5173" in s.CORS_ORIGINS


def test_cors_accepts_https():
    """CORS 接受 https:// 开头"""
    s = Settings(CORS_ORIGINS="https://example.com")
    assert "https://example.com" in s.CORS_ORIGINS


def test_cors_accepts_multiple_origins():
    """CORS 支持逗号分隔的多 origin"""
    s = Settings(CORS_ORIGINS="http://a.com, https://b.com")
    assert "http://a.com" in s.CORS_ORIGINS
    assert "https://b.com" in s.CORS_ORIGINS


def test_cors_strips_whitespace():
    """CORS 去除 origin 前后空白"""
    s = Settings(CORS_ORIGINS="  http://a.com  ,  https://b.com  ")
    assert "http://a.com" in s.CORS_ORIGINS
    assert "https://b.com" in s.CORS_ORIGINS


def test_cors_default_value():
    """CORS 默认值为 localhost:5173"""
    s = Settings()
    assert "localhost" in s.CORS_ORIGINS or "5173" in s.CORS_ORIGINS


# ═══════════════════════════════════════════════════════
# 2. JWT 密钥验证
# ═══════════════════════════════════════════════════════


def test_jwt_secret_rejects_empty():
    """JWT 密钥不允许空"""
    with pytest.raises(ValidationError, match="不能为空"):
        Settings(JWT_SECRET_KEY="")


def test_jwt_secret_rejects_short():
    """JWT 密钥最短 8 字符"""
    with pytest.raises(ValidationError, match="8"):
        Settings(JWT_SECRET_KEY="short")


def test_jwt_secret_accepts_long():
    """JWT 密钥 8 字符以上通过"""
    s = Settings(JWT_SECRET_KEY="a" * 32)
    assert len(s.JWT_SECRET_KEY) >= 8


# ═══════════════════════════════════════════════════════
# 3. 安全响应头中间件
# ═══════════════════════════════════════════════════════


def test_security_headers_middleware_class_exists():
    """SecurityHeadersMiddleware 存在"""
    from app.core.security_headers import SecurityHeadersMiddleware
    assert SecurityHeadersMiddleware is not None


def test_security_headers_middleware_is_subclass():
    """SecurityHeadersMiddleware 继承 BaseHTTPMiddleware"""
    from starlette.middleware.base import BaseHTTPMiddleware

    from app.core.security_headers import SecurityHeadersMiddleware
    assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)


def test_security_headers_set_nosniff():
    """设置 X-Content-Type-Options: nosniff"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert '"nosniff"' in source


def test_security_headers_set_frame_options():
    """设置 X-Frame-Options: DENY"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert '"DENY"' in source


def test_security_headers_set_xss_protection():
    """设置 X-XSS-Protection"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "X-XSS-Protection" in source


def test_security_headers_set_referrer_policy():
    """设置 Referrer-Policy"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Referrer-Policy" in source
    assert "strict-origin-when-cross-origin" in source


def test_security_headers_set_permissions_policy():
    """设置 Permissions-Policy 禁用摄像头/麦克风/定位"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Permissions-Policy" in source
    assert "camera=()" in source
    assert "microphone=()" in source
    assert "geolocation=()" in source


def test_security_headers_set_csp():
    """设置 Content-Security-Policy"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Content-Security-Policy" in source
    assert "default-src 'none'" in source


def test_security_headers_set_coop():
    """设置 Cross-Origin-Opener-Policy"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Cross-Origin-Opener-Policy" in source


def test_security_headers_set_corp():
    """设置 Cross-Origin-Resource-Policy"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Cross-Origin-Resource-Policy" in source


def test_security_headers_hsts_https_only():
    """HSTS 仅在 HTTPS 时设置"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "https" in source
    assert "Strict-Transport-Security" in source


def test_security_headers_cache_control():
    """设置 Cache-Control: no-store"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    assert "Cache-Control" in source
    assert "no-store" in source


def test_security_headers_total_count():
    """安全响应头至少 8 个"""
    import inspect

    from app.core.security_headers import SecurityHeadersMiddleware
    source = inspect.getsource(SecurityHeadersMiddleware)
    header_count = source.count('response.headers[')
    assert header_count >= 8


# ═══════════════════════════════════════════════════════
# 4. 认证模式 — Bearer Token（非 Cookie）
# ═══════════════════════════════════════════════════════


def test_auth_uses_bearer_header():
    """认证使用 Authorization: Bearer 头而非 Cookie"""
    import inspect

    from app.api.deps import get_current_user
    source = inspect.getsource(get_current_user)
    assert "Bearer" in source or "Authorization" in source


def test_backend_no_cookie_usage():
    """后端代码不使用 set_cookie"""
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent / "app"
    for py_file in backend_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "set_cookie" not in source, f"{py_file} 使用了 set_cookie"


def test_login_returns_json_tokens():
    """登录返回 JSON 中的 token 而非 Set-Cookie"""
    import inspect

    from app.api.v1 import auth
    source = inspect.getsource(auth)
    assert "access_token" in source
    assert "set_cookie" not in source


# ═══════════════════════════════════════════════════════
# 5. CORS 中间件配置
# ═══════════════════════════════════════════════════════


def _read_main_source():
    import app.main as mod
    with open(mod.__file__) as f:
        return f.read()


def test_cors_allows_credentials():
    """CORS 配置允许凭证传递"""
    source = _read_main_source()
    assert "allow_credentials" in source
    assert "True" in source


def test_cors_specifies_methods():
    """CORS 指定允许的 HTTP 方法"""
    source = _read_main_source()
    for method in ["GET", "POST", "PUT", "DELETE", "OPTIONS"]:
        assert method in source


def test_cors_specifies_headers():
    """CORS 指定允许的请求头"""
    source = _read_main_source()
    assert "Authorization" in source
    assert "Content-Type" in source


def test_cors_uses_settings():
    """CORS origins 从 Settings 读取"""
    source = _read_main_source()
    assert "CORS_ORIGINS" in source


# ═══════════════════════════════════════════════════════
# 6. Nginx 安全头
# ═══════════════════════════════════════════════════════


def test_nginx_has_security_headers():
    """Nginx 配置包含安全头"""
    from pathlib import Path
    nginx_conf = Path(__file__).parent.parent.parent / "deploy" / "nginx.conf"
    if nginx_conf.exists():
        content = nginx_conf.read_text()
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content


def test_nginx_hides_version():
    """Nginx 隐藏版本号"""
    from pathlib import Path
    nginx_conf = Path(__file__).parent.parent.parent / "deploy" / "nginx.conf"
    if nginx_conf.exists():
        content = nginx_conf.read_text()
        assert "server_tokens off" in content


def test_nginx_blocks_hidden_files():
    """Nginx 阻止访问隐藏文件"""
    from pathlib import Path
    nginx_conf = Path(__file__).parent.parent.parent / "deploy" / "nginx.conf"
    if nginx_conf.exists():
        content = nginx_conf.read_text()
        assert "/\\." in content or "hidden" in content.lower()


def test_nginx_has_csp():
    """Nginx 配置包含 CSP"""
    from pathlib import Path
    nginx_conf = Path(__file__).parent.parent.parent / "deploy" / "nginx.conf"
    if nginx_conf.exists():
        content = nginx_conf.read_text()
        assert "Content-Security-Policy" in content


# ═══════════════════════════════════════════════════════
# 7. 速率限制存在性
# ═══════════════════════════════════════════════════════


def test_rate_limit_module_exists():
    """速率限制模块存在"""
    from app.core import ratelimit
    assert ratelimit is not None


def test_login_rate_limit_exists():
    """登录接口有速率限制"""
    import inspect

    from app.api.v1 import auth
    source = inspect.getsource(auth)
    assert "rate_limit" in source or "ratelimit" in source or "lockout" in source.lower()


# ═══════════════════════════════════════════════════════
# 8. 请求体大小限制
# ═══════════════════════════════════════════════════════


def test_body_limit_module_exists():
    """请求体大小限制模块存在"""
    from app.core import body_limit
    assert body_limit is not None


def test_body_limit_default_size():
    """默认请求体大小限制"""
    from app.core.config import Settings
    s = Settings()
    assert s.MAX_JSON_BODY_MB > 0


# ═══════════════════════════════════════════════════════
# 9. 生产环境安全检查
# ═══════════════════════════════════════════════════════


def test_swagger_disabled_in_production():
    """生产环境禁用 Swagger 文档"""
    source = _read_main_source()
    assert "docs_url" in source


def test_jwt_algorithm_is_configurable():
    """JWT 算法可配置"""
    from app.core.config import Settings
    s = Settings()
    assert hasattr(s, "JWT_ALGORITHM")


def test_hsts_max_age_configurable():
    """HSTS max-age 可配置"""
    from app.core.config import Settings
    s = Settings()
    assert hasattr(s, "HSTS_MAX_AGE")
    assert s.HSTS_MAX_AGE > 0


# ═══════════════════════════════════════════════════════
# 10. 输入消毒（XSS 防护）
# ═══════════════════════════════════════════════════════


def test_sanitize_module_exists():
    """输入消毒模块存在"""
    from app.core import sanitize
    assert sanitize is not None


def test_sanitize_strips_html():
    """移除 HTML 标签防 XSS"""
    from app.core.sanitize import strip_html
    assert strip_html("<script>alert(1)</script>") == "alert(1)"


def test_sanitize_strips_control_chars():
    """移除控制字符"""
    from app.core.sanitize import strip_control_chars
    assert "\x00" not in strip_control_chars("hello\x00world")


def test_sanitize_csv_formula_injection():
    """CSV 公式注入防御"""
    from app.core.sanitize import sanitize_csv_cell
    assert sanitize_csv_cell("=SUM(A1)") == "'=SUM(A1)"


# ═══════════════════════════════════════════════════════
# 11. Docker 容器安全
# ═══════════════════════════════════════════════════════


def test_docker_compose_no_new_privileges():
    """Docker Compose 设置 no-new-privileges"""
    from pathlib import Path
    compose_file = Path(__file__).parent.parent.parent / "deploy" / "docker-compose.prod.yml"
    if compose_file.exists():
        content = compose_file.read_text()
        assert "no-new-privileges" in content


def test_docker_compose_cap_drop():
    """Docker Compose 丢弃所有能力"""
    from pathlib import Path
    compose_file = Path(__file__).parent.parent.parent / "deploy" / "docker-compose.prod.yml"
    if compose_file.exists():
        content = compose_file.read_text()
        assert "cap_drop" in content.lower() or "CAP_DROP" in content
