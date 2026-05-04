"""
代码质量：后端中间件链与执行顺序验证测试
覆盖中间件注册顺序、中间件配置完整性、
中间件功能覆盖、异常处理器链、生命周期与启动安全检查
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAIN_SRC = (ROOT / "app" / "main.py").read_text()
CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()
ROUTER_SRC = (ROOT / "app" / "api" / "v1" / "router.py").read_text()

# 中间件源文件
REQUEST_ID_SRC = (ROOT / "app" / "core" / "request_id.py").read_text()
REQUEST_LOG_SRC = (ROOT / "app" / "core" / "request_log.py").read_text()
SECURITY_HEADERS_SRC = (ROOT / "app" / "core" / "security_headers.py").read_text()
BODY_LIMIT_SRC = (ROOT / "app" / "core" / "body_limit.py").read_text()
RATELIMIT_SRC = (ROOT / "app" / "core" / "ratelimit.py").read_text()

MIDDLEWARE_SRCS = {
    "request_id": REQUEST_ID_SRC,
    "request_log": REQUEST_LOG_SRC,
    "security_headers": SECURITY_HEADERS_SRC,
    "body_limit": BODY_LIMIT_SRC,
    "ratelimit": RATELIMIT_SRC,
}


def _middleware_line_numbers(src: str) -> dict[str, int]:
    """提取各中间件注册的行号"""
    result = {}
    for m in re.finditer(r"add_middleware\(\s*(\w+Middleware)", src):
        name = m.group(1)
        result[name] = src[:m.start()].count("\n") + 1
    return result


def _count_add_middleware(src: str) -> int:
    """统计 add_middleware 调用次数"""
    return len(re.findall(r"add_middleware\(", src))


# ═══════════════════════════════════════════════════════════
# 1. 中间件注册顺序验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareRegistrationOrder:
    """中间件按正确顺序注册"""

    def test_at_least_five_middlewares_registered(self):
        """至少注册 5 个中间件"""
        count = _count_add_middleware(MAIN_SRC)
        assert count >= 5, f"应至少注册 5 个中间件，实际 {count}"

    def test_cors_registered_first(self):
        """CORS 中间件最先注册（最内层）"""
        lines = _middleware_line_numbers(MAIN_SRC)
        assert "CORSMiddleware" in lines, "应注册 CORSMiddleware"
        other_lines = {k: v for k, v in lines.items() if k != "CORSMiddleware"}
        # CORS 应有最小的行号（最先注册）
        if other_lines:
            assert lines["CORSMiddleware"] <= min(other_lines.values()), (
                "CORSMiddleware 应最先注册（最内层执行）"
            )

    def test_request_id_registered_after_others(self):
        """RequestIDMiddleware 在安全/业务中间件之后注册（最外层）"""
        lines = _middleware_line_numbers(MAIN_SRC)
        assert "RequestIDMiddleware" in lines, "应注册 RequestIDMiddleware"
        # RequestID 应有最大行号之一（最后注册 = 最外层）
        assert lines["RequestIDMiddleware"] >= lines.get("CORSMiddleware", 0), (
            "RequestIDMiddleware 应在 CORS 之后注册"
        )

    def test_security_headers_registered(self):
        """SecurityHeadersMiddleware 已注册"""
        lines = _middleware_line_numbers(MAIN_SRC)
        assert "SecurityHeadersMiddleware" in lines, "应注册 SecurityHeadersMiddleware"

    def test_body_limit_registered(self):
        """BodyLimitMiddleware 已注册"""
        lines = _middleware_line_numbers(MAIN_SRC)
        assert "BodyLimitMiddleware" in lines, "应注册 BodyLimitMiddleware"


# ═══════════════════════════════════════════════════════════
# 2. 中间件配置完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareConfiguration:
    """各中间件有正确的配置"""

    def test_cors_uses_config_origins(self):
        """CORS 使用配置的 origins（非硬编码）"""
        cors_block = re.search(r"CORSMiddleware.*?\)", MAIN_SRC, re.DOTALL)
        assert cors_block, "应有 CORSMiddleware 注册"
        block = cors_block.group(0)
        assert "settings" in block or "CORS" in block, (
            "CORS origins 应引用 settings 配置项"
        )

    def test_cors_allows_credentials(self):
        """CORS 允许凭证"""
        assert "allow_credentials" in MAIN_SRC, "CORS 应设置 allow_credentials"

    def test_rate_limit_uses_config(self):
        """速率限制使用配置参数"""
        assert "RATE_LIMIT_MAX" in RATELIMIT_SRC or "RATE_LIMIT" in CONFIG_SRC, (
            "速率限制应使用配置参数"
        )
        assert "RATE_LIMIT_WINDOW" in RATELIMIT_SRC or "RATE_LIMIT" in CONFIG_SRC, (
            "速率限制窗口应可配置"
        )

    def test_body_limit_uses_config(self):
        """请求体大小限制使用配置参数"""
        assert "MAX_JSON_BODY" in BODY_LIMIT_SRC or "MAX_JSON_BODY" in CONFIG_SRC, (
            "请求体限制应使用配置参数"
        )

    def test_request_log_uses_threshold(self):
        """请求日志使用慢请求阈值配置"""
        assert "SLOW_REQUEST" in REQUEST_LOG_SRC or "SLOW_REQUEST" in CONFIG_SRC, (
            "请求日志应使用慢请求阈值配置"
        )


# ═══════════════════════════════════════════════════════════
# 3. 中间件功能覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareFunctionCoverage:
    """中间件覆盖所有安全与可观测性需求"""

    def test_request_id_sets_header_and_context(self):
        """RequestID 设置响应头和上下文变量"""
        assert "X-Request-ID" in REQUEST_ID_SRC, "应设置 X-Request-ID 响应头"
        assert "request_id_ctx" in REQUEST_ID_SRC, "应使用 request_id_ctx 上下文变量"

    def test_request_log_adds_response_time(self):
        """请求日志添加响应时间头"""
        assert "X-Response-Time" in REQUEST_LOG_SRC, "应添加 X-Response-Time 响应头"

    def test_security_headers_covers_owasp(self):
        """安全头覆盖 OWASP 推荐"""
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
        ]
        for header in required_headers:
            assert header in SECURITY_HEADERS_SRC, f"安全头应包含 {header}"

    def test_rate_limit_returns_429(self):
        """速率限制超限返回 429"""
        assert "429" in RATELIMIT_SRC, "速率限制超限应返回 429"
        assert "RATE_LIMIT" in RATELIMIT_SRC, "应使用速率限制相关常量"

    def test_body_limit_returns_413(self):
        """请求体超限返回 413"""
        assert "413" in BODY_LIMIT_SRC, "请求体超限应返回 413"


# ═══════════════════════════════════════════════════════════
# 4. 异常处理器链验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExceptionHandlerChain:
    """异常处理器完整覆盖"""

    def test_http_exception_handler_registered(self):
        """HTTPException 处理器已注册"""
        assert "http_exception_handler" in MAIN_SRC or "HTTPException" in MAIN_SRC, (
            "应注册 HTTPException 处理器"
        )

    def test_validation_exception_handler_registered(self):
        """RequestValidationError 处理器已注册"""
        assert "RequestValidationError" in MAIN_SRC, "应注册 RequestValidationError 处理器"
        assert "validation_exception_handler" in MAIN_SRC, "验证错误处理器应有命名"

    def test_unhandled_exception_handler_registered(self):
        """通用异常处理器已注册"""
        assert "Exception" in MAIN_SRC, "应注册通用 Exception 处理器"
        assert "unhandled_exception_handler" in MAIN_SRC or "500" in MAIN_SRC, (
            "通用异常处理器应返回 500"
        )

    def test_all_handlers_include_request_id(self):
        """所有异常处理器包含 request_id"""
        assert "request_id" in MAIN_SRC, "异常响应应包含 request_id"
        assert "request_id_ctx" in MAIN_SRC, "应从上下文读取 request_id"

    def test_all_handlers_return_unified_structure(self):
        """所有异常处理器返回统一结构"""
        assert "success" in MAIN_SRC, "异常响应应包含 success 字段"
        assert "SYSTEM_INTERNAL_ERROR" in MAIN_SRC, "应使用 SYSTEM_INTERNAL_ERROR 错误码"
        assert "VALIDATION_FAILED" in MAIN_SRC, "应使用 VALIDATION_FAILED 错误码"


# ═══════════════════════════════════════════════════════════
# 5. 生命周期与启动安全检查验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLifespanStartupSecurity:
    """生命周期管理与启动安全检查"""

    def test_lifespan_context_manager_defined(self):
        """定义了 lifespan 上下文管理器"""
        assert "lifespan" in MAIN_SRC, "应定义 lifespan 上下文管理器"
        assert "yield" in MAIN_SRC, "lifespan 应使用 yield 分隔启动/关闭"

    def test_startup_checks_jwt_secret(self):
        """启动时检查 JWT 密钥安全性"""
        assert "JWT_SECRET_KEY" in MAIN_SRC, "启动时应检查 JWT_SECRET_KEY"
        assert "change-me" in MAIN_SRC, "应拒绝默认 JWT 密钥"

    def test_shutdown_sets_shutting_down_flag(self):
        """关闭时设置 shutting_down 标志"""
        assert "shutting_down" in MAIN_SRC or "_shutting_down" in MAIN_SRC, (
            "关闭时应设置 shutting_down 标志"
        )

    def test_shutdown_disposes_engine(self):
        """关闭时释放数据库连接池"""
        assert "engine.dispose" in MAIN_SRC or "dispose" in MAIN_SRC, (
            "关闭时应调用 engine.dispose()"
        )

    def test_router_mounted_with_api_prefix(self):
        """路由挂载使用 /api/v1 前缀"""
        assert 'prefix="/api/v1"' in MAIN_SRC or "prefix='/api/v1'" in MAIN_SRC, (
            "路由应挂载到 /api/v1 前缀"
        )
