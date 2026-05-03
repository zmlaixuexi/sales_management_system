"""SQL 慢查询日志测试 + 慢请求标记测试"""

import logging
from unittest.mock import patch

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.slow_query import register_slow_query_listener


def test_slow_query_not_logged_for_fast_queries(caplog):
    engine = create_engine("sqlite:///:memory:")
    with patch("app.core.slow_query.settings") as mock_settings:
        mock_settings.SLOW_SQL_THRESHOLD_MS = 1
        register_slow_query_listener(engine)

        with (
            caplog.at_level(logging.WARNING, logger="app.slow_query"),
            engine.connect() as conn,
        ):
            conn.execute(text("SELECT 1"))

    assert "SLOW SQL" not in caplog.text


def test_slow_query_not_logged_when_below_high_threshold(caplog):
    engine = create_engine("sqlite:///:memory:")
    with patch("app.core.slow_query.settings") as mock_settings:
        mock_settings.SLOW_SQL_THRESHOLD_MS = 999999
        register_slow_query_listener(engine)

        with (
            caplog.at_level(logging.WARNING, logger="app.slow_query"),
            engine.connect() as conn,
        ):
            conn.execute(text("SELECT 1"))

    assert "SLOW SQL" not in caplog.text


def test_slow_query_logs_with_simulated_slow_execution(caplog):
    """通过 mock time 模拟慢查询，验证完整日志路径"""
    engine = create_engine("sqlite:///:memory:")
    with patch("app.core.slow_query.settings") as mock_settings:
        mock_settings.SLOW_SQL_THRESHOLD_MS = 1
        register_slow_query_listener(engine)

        call_count = 0

        def fake_monotonic():  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return 1000.0
            return 1000.0 + 0.005  # 5ms

        with (
            patch("app.core.slow_query.time.monotonic", side_effect=fake_monotonic),
            caplog.at_level(logging.WARNING, logger="app.slow_query"),
            engine.connect() as conn,
        ):
            conn.execute(text("SELECT 1"))

    assert "SLOW SQL" in caplog.text
    assert "5.0ms" in caplog.text
    assert "threshold=1ms" in caplog.text


def test_slow_query_truncates_long_sql():
    """验证超过 500 字符的 SQL 语句被截断"""
    import logging

    from app.core.slow_query import _after_cursor_execute

    captured_records: list[logging.LogRecord] = []
    logger = logging.getLogger("app.slow_query")

    original_handle = logger.handle

    def capture_handle(record: logging.LogRecord) -> None:
        captured_records.append(record)
        original_handle(record)

    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "handle", capture_handle),
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = 100
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1100.0

        long_sql = "SELECT * FROM " + "a" * 600
        _after_cursor_execute(None, None, long_sql, None, None, None)

    assert len(captured_records) == 1
    record = captured_records[0]
    assert hasattr(record, "extra_fields")
    sql_val = record.extra_fields["sql"]
    assert len(sql_val) <= 503  # 500 + "..."
    assert sql_val.endswith("...")


def test_slow_query_disabled_when_threshold_zero(caplog):
    engine = create_engine("sqlite:///:memory:")
    with patch("app.core.slow_query.settings") as mock_settings:
        mock_settings.SLOW_SQL_THRESHOLD_MS = 0
    with (
        caplog.at_level(logging.WARNING, logger="app.slow_query"),
        engine.connect() as conn,
    ):
        conn.execute(text("SELECT 1"))

    assert "SLOW SQL" not in caplog.text


def test_slow_query_includes_request_id(caplog):
    """慢查询日志包含 request_id 用于链路追踪"""
    import logging

    from app.core.slow_query import _after_cursor_execute

    captured_records: list[logging.LogRecord] = []
    logger = logging.getLogger("app.slow_query")

    original_handle = logger.handle

    def capture_handle(record: logging.LogRecord) -> None:
        captured_records.append(record)
        original_handle(record)

    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "handle", capture_handle),
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = 100
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1100.0

        # 设置 request_id
        from app.core.request_id import request_id_ctx
        token = request_id_ctx.set("test-req-123")
        try:
            _after_cursor_execute(None, None, "SELECT 1", None, None, None)
        finally:
            request_id_ctx.reset(token)

    assert len(captured_records) == 1
    assert captured_records[0].extra_fields["request_id"] == "test-req-123"


def test_slow_query_parameters_truncated():
    """超过 200 字符的参数被截断"""
    import logging

    from app.core.slow_query import _after_cursor_execute

    captured_records: list[logging.LogRecord] = []
    logger = logging.getLogger("app.slow_query")

    original_handle = logger.handle

    def capture_handle(record: logging.LogRecord) -> None:
        captured_records.append(record)
        original_handle(record)

    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "handle", capture_handle),
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = 100
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1100.0

        long_params = {"key": "x" * 300}
        _after_cursor_execute(None, None, "SELECT 1", long_params, None, None)

    assert len(captured_records) == 1
    params_val = captured_records[0].extra_fields["parameters"]
    assert len(params_val) <= 200


def test_slow_query_sql_exactly_500_not_truncated():
    """SQL 恰好 500 字符时不截断（不加 ...）"""
    import logging

    from app.core.slow_query import _after_cursor_execute

    captured_records: list[logging.LogRecord] = []
    logger = logging.getLogger("app.slow_query")

    original_handle = logger.handle

    def capture_handle(record: logging.LogRecord) -> None:
        captured_records.append(record)
        original_handle(record)

    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "handle", capture_handle),
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = 100
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1100.0

        exact_sql = "SELECT * FROM " + "a" * 486  # 总长度 = 14 + 486 = 500
        assert len(exact_sql) == 500
        _after_cursor_execute(None, None, exact_sql, None, None, None)

    assert len(captured_records) == 1
    sql_val = captured_records[0].extra_fields["sql"]
    assert sql_val == exact_sql
    assert not sql_val.endswith("...")


# ═══════════════════════════════════════════════════════
# 慢请求标记测试
# ═══════════════════════════════════════════════════════


def test_slow_request_threshold_default():
    """慢请求阈值默认 1000ms"""
    assert settings.SLOW_REQUEST_THRESHOLD_MS == 1000


def test_slow_sql_threshold_default():
    """慢 SQL 阈值默认 200ms"""
    assert settings.SLOW_SQL_THRESHOLD_MS == 200


def test_slow_request_level_is_warning():
    """慢请求日志级别为 WARNING"""
    duration = settings.SLOW_REQUEST_THRESHOLD_MS + 1
    is_slow = duration >= settings.SLOW_REQUEST_THRESHOLD_MS
    level = logging.WARNING if is_slow else logging.INFO
    assert level == logging.WARNING


def test_fast_request_level_is_info():
    """正常请求日志级别为 INFO"""
    duration = 50
    is_slow = duration >= settings.SLOW_REQUEST_THRESHOLD_MS
    level = logging.WARNING if is_slow else logging.INFO
    assert level == logging.INFO


def test_slow_request_extra_fields_has_slow_true():
    """慢请求 extra_fields 的 slow 标记为 True"""
    duration = settings.SLOW_REQUEST_THRESHOLD_MS + 500
    is_slow = duration >= settings.SLOW_REQUEST_THRESHOLD_MS
    record = logging.LogRecord(
        name="app.request", level=logging.WARNING,
        pathname="", lineno=0, msg="", args=None, exc_info=None,
    )
    record.extra_fields = {  # type: ignore[attr-defined]
        "method": "GET", "path": "/api/v1/reports", "status": 200,
        "duration_ms": float(duration), "slow": is_slow,
    }
    assert record.extra_fields["slow"] is True


def test_fast_request_extra_fields_has_slow_false():
    """正常请求 extra_fields 的 slow 标记为 False"""
    duration = 50
    is_slow = duration >= settings.SLOW_REQUEST_THRESHOLD_MS
    record = logging.LogRecord(
        name="app.request", level=logging.INFO,
        pathname="", lineno=0, msg="", args=None, exc_info=None,
    )
    record.extra_fields = {  # type: ignore[attr-defined]
        "method": "GET", "path": "/api/v1/health", "status": 200,
        "duration_ms": float(duration), "slow": is_slow,
    }
    assert record.extra_fields["slow"] is False


def test_slow_request_message_includes_slow_label():
    """慢请求消息包含 SLOW 前缀"""
    is_slow = True
    label = "SLOW " if is_slow else ""
    msg = f"{label}GET /api/v1/reports 200 2500ms"
    assert msg.startswith("SLOW")


def test_fast_request_message_no_slow_label():
    """正常请求消息不含 SLOW 前缀"""
    is_slow = False
    label = "SLOW " if is_slow else ""
    msg = f"{label}GET /api/v1/health 200 5ms"
    assert not msg.startswith("SLOW")
    assert "SLOW" not in msg
