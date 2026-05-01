import json
import logging
import sys
import traceback
from datetime import UTC, datetime

from app.core.config import settings


class _JsonFormatter(logging.Formatter):
    """结构化 JSON 日志格式器"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        # 所有日志条目关联 request_id 和 user_id，便于日志检索
        from app.core.request_id import request_id_ctx
        from app.core.user_context import user_id_ctx
        rid = request_id_ctx.get("")
        if rid:
            log_entry["request_id"] = rid
        uid = user_id_ctx.get("")
        if uid:
            log_entry["user_id"] = uid
        return json.dumps(log_entry, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    """人类可读的文本格式"""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )


def get_logger(name: str) -> logging.Logger:
    """获取带结构化能力的 logger"""
    return logging.getLogger(name)


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    use_json = getattr(settings, "LOG_FORMAT", "text") == "json"
    formatter = _JsonFormatter() if use_json else _TextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # 降低第三方库日志级别
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


setup_logging()
