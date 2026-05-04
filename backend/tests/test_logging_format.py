"""
可观测性：后端日志格式与结构化输出验证测试
覆盖日志格式配置、请求 ID 中间件、结构化日志字段、
日志级别与阈值、异常处理器日志集成
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LOGGING_SRC = (ROOT / "app" / "core" / "logging.py").read_text()
REQUEST_ID_SRC = (ROOT / "app" / "core" / "request_id.py").read_text()
REQUEST_LOG_SRC = (ROOT / "app" / "core" / "request_log.py").read_text()
SLOW_QUERY_SRC = (ROOT / "app" / "core" / "slow_query.py").read_text()
USER_CTX_SRC = (ROOT / "app" / "core" / "user_context.py").read_text()
CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()
MAIN_SRC = (ROOT / "app" / "main.py").read_text()


# ═══════════════════════════════════════════════════════════
# 1. 日志格式配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLogFormatConfig:
    """日志格式和输出配置正确"""

    def test_json_formatter_includes_required_fields(self):
        """JSON 格式器包含必要字段"""
        required = ["timestamp", "level", "logger", "message", "app_env"]
        for field in required:
            assert f'"{field}"' in LOGGING_SRC, f"JSON 格式器应包含 {field} 字段"

    def test_json_formatter_uses_iso_timestamp(self):
        """JSON 格式器使用 ISO 8601 时间戳"""
        assert "isoformat()" in LOGGING_SRC, "时间戳应使用 .isoformat() 格式"

    def test_text_formatter_format_string(self):
        """文本格式器使用标准格式字符串"""
        assert "%(asctime)s" in LOGGING_SRC, "文本格式应包含时间"
        assert "%(levelname)s" in LOGGING_SRC, "文本格式应包含级别"
        assert "%(name)s" in LOGGING_SRC, "文本格式应包含 logger 名称"
        assert "%(message)s" in LOGGING_SRC, "文本格式应包含消息"

    def test_setup_logging_selects_format_by_config(self):
        """setup_logging 根据 LOG_FORMAT 配置选择格式器"""
        assert "LOG_FORMAT" in LOGGING_SRC, "应读取 LOG_FORMAT 配置"
        assert "_JsonFormatter" in LOGGING_SRC, "应支持 JSON 格式器"
        assert "_TextFormatter" in LOGGING_SRC, "应支持文本格式器"

    def test_log_output_to_stdout(self):
        """日志输出到 stdout（非 stderr）"""
        assert "sys.stdout" in LOGGING_SRC, "日志应输出到 sys.stdout"


# ═══════════════════════════════════════════════════════════
# 2. 请求 ID 中间件验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestIdMiddleware:
    """请求 ID 中间件配置正确"""

    def test_request_id_context_var_defined(self):
        """request_id_ctx ContextVar 已定义"""
        assert "request_id_ctx" in REQUEST_ID_SRC, "应定义 request_id_ctx"
        assert "ContextVar" in REQUEST_ID_SRC, "应使用 ContextVar"

    def test_middleware_reads_x_request_id_header(self):
        """中间件读取 X-Request-ID 请求头"""
        assert "x-request-id" in REQUEST_ID_SRC.lower(), "应读取 X-Request-ID 头"

    def test_middleware_generates_uuid_if_missing(self):
        """缺少 X-Request-ID 时生成 UUID"""
        assert "uuid.uuid4()" in REQUEST_ID_SRC, "应使用 uuid.uuid4() 生成 ID"

    def test_middleware_sets_response_header(self):
        """中间件在响应中设置 X-Request-ID 头"""
        assert "X-Request-ID" in REQUEST_ID_SRC, "响应应设置 X-Request-ID 头"

    def test_request_id_middleware_registered_in_main(self):
        """RequestIDMiddleware 在 main.py 中注册"""
        assert "RequestIDMiddleware" in MAIN_SRC, "main.py 应注册 RequestIDMiddleware"


# ═══════════════════════════════════════════════════════════
# 3. 结构化日志字段验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStructuredLogFields:
    """请求日志和慢查询日志包含结构化字段"""

    def test_request_log_includes_method_path_status(self):
        """请求日志包含 method、path、status 字段"""
        for field in ['"method"', '"path"', '"status"']:
            assert field in REQUEST_LOG_SRC, f"请求日志应包含 {field} 字段"

    def test_request_log_includes_duration(self):
        """请求日志包含 duration_ms 字段"""
        assert '"duration_ms"' in REQUEST_LOG_SRC, "请求日志应包含 duration_ms"

    def test_request_log_includes_client_ip(self):
        """请求日志包含 client_ip 字段"""
        assert '"client_ip"' in REQUEST_LOG_SRC, "请求日志应包含 client_ip"

    def test_slow_query_includes_sql_and_duration(self):
        """慢查询日志包含 sql 和 duration_ms 字段"""
        assert '"sql"' in SLOW_QUERY_SRC, "慢查询日志应包含 sql 字段"
        assert '"duration_ms"' in SLOW_QUERY_SRC, "慢查询日志应包含 duration_ms"

    def test_json_formatter_includes_user_id(self):
        """JSON 格式器包含 user_id 字段（用于日志关联用户）"""
        assert "user_id" in LOGGING_SRC, "JSON 格式器应包含 user_id 字段"
        assert "user_id_ctx" in LOGGING_SRC, "应从 user_id_ctx ContextVar 读取"


# ═══════════════════════════════════════════════════════════
# 4. 日志级别与阈值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLogLevelAndThreshold:
    """日志级别和慢请求/慢查询阈值配置正确"""

    def test_log_level_configurable(self):
        """LOG_LEVEL 可通过配置调整"""
        assert "LOG_LEVEL" in CONFIG_SRC, "应定义 LOG_LEVEL 配置项"

    def test_slow_request_threshold_configured(self):
        """SLOW_REQUEST_THRESHOLD_MS 已配置"""
        m = re.search(r"SLOW_REQUEST_THRESHOLD_MS\s*[:=]\s*(?:int\s*=\s*)?(\d+)", CONFIG_SRC)
        assert m, "应定义 SLOW_REQUEST_THRESHOLD_MS"
        val = int(m.group(1))
        assert val >= 100, f"SLOW_REQUEST_THRESHOLD_MS 应 >= 100ms，当前 {val}"

    def test_slow_sql_threshold_configured(self):
        """SLOW_SQL_THRESHOLD_MS 已配置"""
        m = re.search(r"SLOW_SQL_THRESHOLD_MS\s*[:=]\s*(?:int\s*=\s*)?(\d+)", CONFIG_SRC)
        assert m, "应定义 SLOW_SQL_THRESHOLD_MS"
        val = int(m.group(1))
        assert val >= 50, f"SLOW_SQL_THRESHOLD_MS 应 >= 50ms，当前 {val}"

    def test_slow_request_logged_at_warning_level(self):
        """慢请求使用 WARNING 级别"""
        assert "logging.WARNING" in REQUEST_LOG_SRC, "慢请求应使用 WARNING 级别"

    def test_third_party_loggers_suppressed(self):
        """第三方库日志级别设为 WARNING"""
        assert "uvicorn.access" in LOGGING_SRC, "应抑制 uvicorn.access 日志"
        assert "sqlalchemy.engine" in LOGGING_SRC, "应抑制 sqlalchemy.engine 日志"
        assert "logging.WARNING" in LOGGING_SRC, "第三方库应设为 WARNING 级别"


# ═══════════════════════════════════════════════════════════
# 5. 异常处理器日志集成验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExceptionLoggingIntegration:
    """异常处理器集成 request_id 和日志"""

    def test_error_responses_include_request_id(self):
        """错误响应包含 request_id"""
        assert "request_id_ctx" in MAIN_SRC, "异常处理器应读取 request_id_ctx"
        assert "request_id" in MAIN_SRC, "错误响应应包含 request_id 字段"

    def test_request_log_middleware_registered(self):
        """RequestLogMiddleware 在 main.py 中注册"""
        assert "RequestLogMiddleware" in MAIN_SRC, "main.py 应注册 RequestLogMiddleware"

    def test_slow_query_listener_registered(self):
        """慢查询监听器在数据库引擎创建时注册"""
        SESSION_SRC = (ROOT / "app" / "db" / "session.py").read_text()
        assert "register_slow_query_listener" in SESSION_SRC, "session.py 应注册慢查询监听器"

    def test_request_log_only_logs_api_paths(self):
        """请求日志只记录 /api/ 路径"""
        assert '"/api/"' in REQUEST_LOG_SRC or "'/api/'" in REQUEST_LOG_SRC or "startswith" in REQUEST_LOG_SRC, (
            "请求日志应只记录 /api/ 路径"
        )

    def test_request_log_includes_response_time_header(self):
        """请求日志中间件设置 X-Response-Time 响应头"""
        assert "X-Response-Time" in REQUEST_LOG_SRC, "响应应包含 X-Response-Time 头"
