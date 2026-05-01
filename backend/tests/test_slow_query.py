"""SQL 慢查询日志测试"""

import logging
from unittest.mock import patch

from sqlalchemy import create_engine, text

from app.core.slow_query import register_slow_query_listener


def test_slow_query_logged_when_exceeds_threshold(caplog):
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


def test_slow_query_not_logged_when_below_threshold(caplog):
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


def test_slow_query_listener_logs_when_slow():
    """直接测试 _after_cursor_execute 回调函数的日志逻辑"""
    import logging

    from app.core.slow_query import _after_cursor_execute

    logger = logging.getLogger("app.slow_query")
    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "warning") as mock_warn,
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = 100
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1100.0

        _after_cursor_execute(None, None, "SELECT * FROM products", None, None, None)

    mock_warn.assert_called_once()
    args = mock_warn.call_args[0]
    assert "SLOW SQL" in args[0]
