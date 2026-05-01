"""SQL 慢查询日志测试"""

import logging
from unittest.mock import patch

from sqlalchemy import create_engine, text

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
