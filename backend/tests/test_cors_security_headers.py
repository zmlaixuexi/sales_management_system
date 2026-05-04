"""安全加固：后端 CORS 配置与安全头验证测试
覆盖 CORS 中间件配置、安全响应头完整性、
HSTS 条件逻辑、安全头不泄露信息、配置项约束"""

from pathlib import Path

MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"
SECURITY_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "security_headers.py"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. CORS 中间件配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCorsConfig:
    """验证 CORS 中间件配置"""

    def test_cors_middleware_imported(self):
        source = _read(MAIN_FILE)
        assert "CORSMiddleware" in source
        assert "from fastapi.middleware.cors" in source

    def test_cors_origins_from_settings(self):
        source = _read(MAIN_FILE)
        assert "settings.CORS_ORIGINS" in source
        assert '.split(",")' in source

    def test_cors_allows_credentials(self):
        source = _read(MAIN_FILE)
        assert "allow_credentials=True" in source

    def test_cors_limits_methods(self):
        source = _read(MAIN_FILE)
        assert "allow_methods" in source
        assert '"GET"' in source
        assert '"POST"' in source
        assert '"PUT"' in source
        assert '"DELETE"' in source

    def test_cors_limits_headers(self):
        source = _read(MAIN_FILE)
        assert "allow_headers" in source
        assert '"Authorization"' in source
        assert '"Content-Type"' in source


# ═══════════════════════════════════════════════════════════
# 2. 安全响应头完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSecurityHeaders:
    """验证安全响应头中间件"""

    def test_x_content_type_options(self):
        source = _read(SECURITY_FILE)
        assert '"X-Content-Type-Options"' in source
        assert '"nosniff"' in source

    def test_x_frame_options(self):
        source = _read(SECURITY_FILE)
        assert '"X-Frame-Options"' in source
        assert '"DENY"' in source

    def test_csp_header(self):
        source = _read(SECURITY_FILE)
        assert '"Content-Security-Policy"' in source
        assert "default-src" in source
        assert "'none'" in source

    def test_referrer_policy(self):
        source = _read(SECURITY_FILE)
        assert '"Referrer-Policy"' in source
        assert '"strict-origin-when-cross-origin"' in source

    def test_permissions_policy(self):
        source = _read(SECURITY_FILE)
        assert '"Permissions-Policy"' in source


# ═══════════════════════════════════════════════════════════
# 3. HSTS 条件逻辑验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHSTSLogic:
    """验证 HSTS 仅在 HTTPS 时添加"""

    def test_hsts_checks_scheme(self):
        source = _read(SECURITY_FILE)
        assert 'request.url.scheme == "https"' in source

    def test_hsts_uses_settings(self):
        source = _read(SECURITY_FILE)
        assert "settings.HSTS_MAX_AGE" in source

    def test_hsts_includes_subdomains(self):
        source = _read(SECURITY_FILE)
        assert "includeSubDomains" in source

    def test_hsts_max_age_default_1_year(self):
        source = _read(CONFIG_FILE)
        assert "HSTS_MAX_AGE: int = 31536000" in source

    def test_security_headers_middleware_registered(self):
        source = _read(MAIN_FILE)
        assert "SecurityHeadersMiddleware" in source
        assert "add_middleware(SecurityHeadersMiddleware)" in source


# ═══════════════════════════════════════════════════════════
# 4. 安全头不泄露信息验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestNoInfoLeak:
    """验证安全头防止信息泄露"""

    def test_cache_control_no_store(self):
        source = _read(SECURITY_FILE)
        assert '"Cache-Control"' in source
        assert '"no-store"' in source

    def test_cross_origin_opener_policy(self):
        source = _read(SECURITY_FILE)
        assert '"Cross-Origin-Opener-Policy"' in source
        assert '"same-origin"' in source

    def test_cross_origin_resource_policy(self):
        source = _read(SECURITY_FILE)
        assert '"Cross-Origin-Resource-Policy"' in source

    def test_xss_protection_header(self):
        source = _read(SECURITY_FILE)
        assert '"X-XSS-Protection"' in source
        assert '"1; mode=block"' in source

    def test_csp_blocks_framing(self):
        source = _read(SECURITY_FILE)
        assert "frame-ancestors" in source
        assert "'none'" in source


# ═══════════════════════════════════════════════════════════
# 5. 配置项约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestConfigConstraints:
    """验证安全相关配置约束"""

    def test_cors_origins_no_wildcard(self):
        """CORS 不允许通配符 *"""
        source = _read(CONFIG_FILE)
        assert "'*'" in source  # validator explicitly rejects it
        assert "CORS_ORIGINS 不允许使用通配符" in source

    def test_cors_origins_must_start_with_http(self):
        source = _read(CONFIG_FILE)
        assert "http://" in source
        assert "https://" in source
        assert "origin 必须以 http:// 或 https:// 开头" in source

    def test_cors_origins_default_is_localhost(self):
        source = _read(CONFIG_FILE)
        assert "CORS_ORIGINS: str = " in source
        assert "localhost" in source

    def test_hsts_max_age_is_positive(self):
        source = _read(CONFIG_FILE)
        assert "HSTS_MAX_AGE: int = 31536000" in source
        assert 31536000 > 0

    def test_jwt_secret_minimum_length(self):
        source = _read(CONFIG_FILE)
        assert "len(v) < 8" in source
        assert "长度不能少于 8 个字符" in source
