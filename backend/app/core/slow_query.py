"""SQL 慢查询日志 — 通过 SQLAlchemy 事件监听记录超过阈值的 SQL 语句"""

import logging
import time
from contextvars import ContextVar

from sqlalchemy import event

from app.core.config import settings

logger = logging.getLogger("app.slow_query")

_query_start_ctx: ContextVar[float] = ContextVar("sql_query_start", default=0.0)


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    _query_start_ctx.set(time.monotonic())


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    elapsed_ms = round((time.monotonic() - _query_start_ctx.get()) * 1000, 2)
    threshold = settings.SLOW_SQL_THRESHOLD_MS
    if elapsed_ms >= threshold:
        from app.core.request_id import request_id_ctx

        sql_short = statement[:200] + "..." if len(statement) > 200 else statement
        logger.warning(
            "SLOW SQL %.2fms (threshold=%dms) request_id=%s: %s",
            elapsed_ms,
            threshold,
            request_id_ctx.get(""),
            sql_short,
        )


def register_slow_query_listener(engine):  # type: ignore[no-untyped-def]
    if settings.SLOW_SQL_THRESHOLD_MS > 0:
        event.listen(engine, "before_cursor_execute", _before_cursor_execute)
        event.listen(engine, "after_cursor_execute", _after_cursor_execute)
