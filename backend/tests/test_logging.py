"""日志模块单元测试 — _JsonFormatter / log_action 异常处理"""

import json
import logging

from app.core.logging import _JsonFormatter, get_logger
from app.services.audit_service import log_action

# ─── _JsonFormatter ─────────────────────────────────────────


def test_json_formatter_basic():
    """基本日志格式化为 JSON"""
    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    output = fmt.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "test"
    assert data["message"] == "hello"
    assert "timestamp" in data


def test_json_formatter_with_exception():
    """包含异常信息时输出 exception 字段"""
    fmt = _JsonFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error occurred", args=(), exc_info=exc_info,
    )
    output = fmt.format(record)
    data = json.loads(output)
    assert data["level"] == "ERROR"
    assert "exception" in data
    assert "ValueError" in data["exception"]
    assert "test error" in data["exception"]


def test_json_formatter_with_extra_fields():
    """extra_fields 被合并到 JSON 输出"""
    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="msg", args=(), exc_info=None,
    )
    record.extra_fields = {"request_id": "abc123", "duration_ms": 42}
    output = fmt.format(record)
    data = json.loads(output)
    assert data["request_id"] == "abc123"
    assert data["duration_ms"] == 42


def test_json_formatter_no_exception_without_exc_info():
    """无异常信息时不包含 exception 字段"""
    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="ok", args=(), exc_info=None,
    )
    output = fmt.format(record)
    data = json.loads(output)
    assert "exception" not in data


# ─── log_action 异常处理 ──────────────────────────────────────


def test_log_action_db_failure_returns_none():
    """数据库写入失败时返回 None 而不抛出异常"""
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_db.flush.side_effect = Exception("DB connection lost")
    result = log_action(
        mock_db,
        action="test_action",
        resource_type="order",
        actor_id=None,
        actor_name="tester",
    )
    assert result is None


def test_get_logger_returns_named_logger():
    """get_logger 返回指定名称的 logger"""
    logger = get_logger("test_module")
    assert logger.name == "test_module"
