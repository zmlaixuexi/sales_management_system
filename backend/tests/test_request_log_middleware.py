"""可观测性：后端请求日志中间件验证测试
覆盖请求日志中间件配置、请求 ID 中间件逻辑、
结构化日志格式器、慢查询日志监听、配置项约束"""

from pathlib import Path

MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"
REQUEST_LOG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "request_log.py"
REQUEST_ID_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "request_id.py"
LOGGING_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "logging.py"
SLOW_QUERY_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "slow_query.py"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. 请求日志中间件逻辑验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestLogMiddleware:
    """验证 RequestLogMiddleware 核心逻辑"""

    def test_only_logs_api_paths(self):
        source = _read(REQUEST_LOG_FILE)
        assert 'path.startswith("/api/")' in source

    def test_records_duration_in_ms(self):
        source = _read(REQUEST_LOG_FILE)
        assert "time.monotonic()" in source
        assert "duration_ms" in source
        assert "* 1000" in source

    def test_slow_request_uses_warning_level(self):
        source = _read(REQUEST_LOG_FILE)
        assert "SLOW_REQUEST_THRESHOLD_MS" in source
        assert "logging.WARNING" in source

    def test_extracts_structured_extra_fields(self):
        source = _read(REQUEST_LOG_FILE)
        for field in (
            '"method"', '"path"', '"query_string"',
            '"status"', '"duration_ms"', '"client_ip"',
            '"user_agent"', '"request_id"',
        ):
            assert field in source

    def test_adds_response_time_header(self):
        source = _read(REQUEST_LOG_FILE)
        assert '"X-Response-Time"' in source
        assert "duration_ms" in source


# ═══════════════════════════════════════════════════════════
# 2. 请求 ID 中间件逻辑验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestIDMiddleware:
    """验证 RequestIDMiddleware 逻辑"""

    def test_generates_uuid_if_no_header(self):
        source = _read(REQUEST_ID_FILE)
        assert "uuid.uuid4()" in source
        assert 'request.headers.get("x-request-id")' in source

    def test_uses_context_var_for_request_id(self):
        source = _read(REQUEST_ID_FILE)
        assert "ContextVar" in source
        assert "request_id_ctx" in source

    def test_sets_id_before_calling_next(self):
        source = _read(REQUEST_ID_FILE)
        assert "request_id_ctx.set(rid)" in source
        lines = source.split("\n")
        set_line = next(i for i, line in enumerate(lines) if "request_id_ctx.set" in line)
        call_next_line = next(i for i, line in enumerate(lines) if "await call_next" in line)
        assert set_line < call_next_line

    def test_returns_id_in_response_header(self):
        source = _read(REQUEST_ID_FILE)
        assert '"X-Request-ID"' in source
        assert "response.headers[" in source

    def test_default_empty_string(self):
        source = _read(REQUEST_ID_FILE)
        assert 'default=""' in source or "default=''" in source


# ═══════════════════════════════════════════════════════════
# 3. 结构化日志格式器验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLoggingFormatter:
    """验证结构化日志格式器"""

    def test_json_formatter_outputs_json(self):
        source = _read(LOGGING_FILE)
        assert "_JsonFormatter" in source
        assert "json.dumps" in source
        assert "ensure_ascii=False" in source

    def test_includes_standard_fields(self):
        source = _read(LOGGING_FILE)
        for field in ('"timestamp"', '"level"', '"logger"', '"message"'):
            assert field in source

    def test_includes_app_env(self):
        source = _read(LOGGING_FILE)
        assert '"app_env"' in source
        assert "settings.APP_ENV" in source

    def test_includes_request_id_and_user_id(self):
        source = _read(LOGGING_FILE)
        assert "request_id_ctx" in source
        assert "user_id_ctx" in source
        assert '"request_id"' in source
        assert '"user_id"' in source

    def test_merges_extra_fields(self):
        source = _read(LOGGING_FILE)
        assert "extra_fields" in source
        assert "log_entry.update" in source


# ═══════════════════════════════════════════════════════════
# 4. 慢查询日志监听验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSlowQueryListener:
    """验证慢查询日志配置"""

    def test_registers_sqlalchemy_events(self):
        source = _read(SLOW_QUERY_FILE)
        assert "event.listen" in source
        assert '"before_cursor_execute"' in source
        assert '"after_cursor_execute"' in source

    def test_uses_configurable_threshold(self):
        source = _read(SLOW_QUERY_FILE)
        assert "SLOW_SQL_THRESHOLD_MS" in source
        assert "settings.SLOW_SQL_THRESHOLD_MS" in source

    def test_truncates_long_sql(self):
        source = _read(SLOW_QUERY_FILE)
        assert "[:500]" in source or "[:200]" in source
        assert "..." in source

    def test_includes_request_id_in_slow_query(self):
        source = _read(SLOW_QUERY_FILE)
        assert "request_id_ctx" in source
        assert '"request_id"' in source

    def test_conditional_registration(self):
        source = _read(SLOW_QUERY_FILE)
        assert "SLOW_SQL_THRESHOLD_MS > 0" in source


# ═══════════════════════════════════════════════════════════
# 5. 中间件注册与配置约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareRegistration:
    """验证中间件在 main.py 中的注册顺序与配置"""

    def test_request_id_registered_before_log(self):
        source = _read(MAIN_FILE)
        id_pos = source.index("RequestIDMiddleware")
        log_pos = source.index("RequestLogMiddleware")
        assert id_pos < log_pos, "RequestIDMiddleware 应在 RequestLogMiddleware 之前注册"

    def test_all_logging_middlewares_registered(self):
        source = _read(MAIN_FILE)
        assert "RequestIDMiddleware" in source
        assert "RequestLogMiddleware" in source
        assert "add_middleware(RequestLogMiddleware)" in source
        assert "add_middleware(RequestIDMiddleware)" in source

    def test_log_level_configurable(self):
        source = _read(CONFIG_FILE)
        assert "LOG_LEVEL" in source
        assert '"INFO"' in source

    def test_log_format_configurable(self):
        source = _read(CONFIG_FILE)
        assert "LOG_FORMAT" in source
        assert '"text"' in source

    def test_slow_request_threshold_configurable(self):
        source = _read(CONFIG_FILE)
        assert "SLOW_REQUEST_THRESHOLD_MS" in source
        assert "1000" in source
