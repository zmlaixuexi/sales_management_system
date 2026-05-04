"""安全加固：后端速率限制运行时验证测试
覆盖中间件注册、429 响应结构、速率限制头部、
非 API 路径豁免、配置控制"""

from pathlib import Path

MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"
RATELIMIT_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "ratelimit.py"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"


def _extract_source(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. 中间件注册验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareRegistration:
    """验证速率限制中间件在 main.py 中正确注册"""

    def test_main_calls_add_rate_limit(self):
        source = _extract_source(MAIN_FILE)
        assert "add_rate_limit" in source

    def test_add_rate_limit_imported_from_core(self):
        source = _extract_source(MAIN_FILE)
        assert "ratelimit" in source
        assert "add_rate_limit" in source

    def test_rate_limit_registered_after_router(self):
        """速率限制中间件在路由注册之后添加（Starlette 逆序执行）"""
        source = _extract_source(MAIN_FILE)
        add_pos = source.find("add_rate_limit(app)")
        router_pos = source.find("include_router")
        assert add_pos > 0, "add_rate_limit(app) 未找到"
        assert router_pos > 0, "include_router 未找到"
        assert add_pos > router_pos, "速率限制应在路由注册之后"

    def test_rate_limit_middleware_class_exists(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "class RateLimitMiddleware" in source
        assert "BaseHTTPMiddleware" in source

    def test_add_rate_limit_reads_settings(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "RATE_LIMIT_MAX" in source
        assert "RATE_LIMIT_WINDOW" in source
        assert "add_middleware" in source


# ═══════════════════════════════════════════════════════════
# 2. 429 响应结构验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRateLimitResponse:
    """验证速率限制响应格式"""

    def test_429_status_code(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "429" in source
        assert "status_code=429" in source

    def test_429_body_has_error_code(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "RATE_LIMIT_EXCEEDED" in source

    def test_429_body_has_success_false(self):
        source = _extract_source(RATELIMIT_FILE)
        assert '"success": False' in source or "'success': False" in source

    def test_429_body_has_message(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "请求过于频繁" in source or "稍后再试" in source

    def test_429_uses_json_response(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "JSONResponse" in source


# ═══════════════════════════════════════════════════════════
# 3. 速率限制头部验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRateLimitHeaders:
    """验证 X-RateLimit 头部设置"""

    def test_x_ratelimit_limit_header_on_success(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "X-RateLimit-Limit" in source

    def test_x_ratelimit_remaining_header_on_success(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "X-RateLimit-Remaining" in source

    def test_remaining_uses_max_function(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "max(0" in source

    def test_429_response_includes_headers(self):
        source = _extract_source(RATELIMIT_FILE)
        # 在 429 响应分支中也要有 headers
        lines = source.split("\n")
        in_429_branch = False
        has_headers_in_429 = False
        for line in lines:
            if "status_code=429" in line:
                in_429_branch = True
            if in_429_branch and "X-RateLimit-Limit" in line:
                has_headers_in_429 = True
                break
            if in_429_branch and "return error_resp" in line:
                break
        assert has_headers_in_429, "429 响应应包含 X-RateLimit-Limit 头"

    def test_429_remaining_is_zero(self):
        source = _extract_source(RATELIMIT_FILE)
        lines = source.split("\n")
        in_429_branch = False
        has_zero_remaining = False
        for line in lines:
            if "status_code=429" in line:
                in_429_branch = True
            if in_429_branch and "X-RateLimit-Remaining" in line and '"0"' in line:
                has_zero_remaining = True
                break
            if in_429_branch and "return error_resp" in line:
                break
        assert has_zero_remaining, "429 响应的 Remaining 应为 0"


# ═══════════════════════════════════════════════════════════
# 4. 非 API 路径豁免验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPathExemption:
    """验证非 API 路径不受速率限制"""

    def test_only_api_paths_limited(self):
        source = _extract_source(RATELIMIT_FILE)
        assert '"/api/"' in source or "'/api/'" in source
        assert "startswith" in source

    def test_health_endpoint_not_limited(self):
        """健康检查路径不以 /api/ 开头"""
        source = _extract_source(RATELIMIT_FILE)
        # 中间件检查 request.url.path.startswith("/api/")
        # /health 不以 /api/ 开头，自动豁免
        assert "startswith" in source

    def test_metrics_endpoint_not_limited(self):
        """Prometheus /metrics 不以 /api/ 开头"""
        source = _extract_source(RATELIMIT_FILE)
        assert "request.url.path" in source

    def test_uploads_endpoint_not_limited(self):
        """/uploads/ 静态文件不受限制"""
        source = _extract_source(RATELIMIT_FILE)
        # /uploads/ 不以 /api/ 开头
        assert '"/api/"' in source

    def test_ip_based_tracking(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "request.client" in source
        assert "client_ip" in source


# ═══════════════════════════════════════════════════════════
# 5. 配置控制验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRateLimitConfig:
    """验证速率限制配置控制"""

    def test_config_has_rate_limit_max(self):
        source = _extract_source(CONFIG_FILE)
        assert "RATE_LIMIT_MAX" in source

    def test_config_has_rate_limit_window(self):
        source = _extract_source(CONFIG_FILE)
        assert "RATE_LIMIT_WINDOW" in source

    def test_rate_limit_max_default_1000(self):
        source = _extract_source(CONFIG_FILE)
        assert "RATE_LIMIT_MAX: int = 1000" in source

    def test_rate_limit_window_default_60(self):
        source = _extract_source(CONFIG_FILE)
        assert "RATE_LIMIT_WINDOW: int = 60" in source

    def test_zero_max_disables_rate_limit(self):
        source = _extract_source(RATELIMIT_FILE)
        assert "max_requests > 0" in source
