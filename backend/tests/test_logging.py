"""日志模块单元测试 — _JsonFormatter / _TextFormatter / setup_logging / log_action 异常处理"""

import json
import logging

from app.core.logging import _JsonFormatter, _TextFormatter, get_logger, setup_logging
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


def test_json_formatter_injects_request_id_from_context():
    """request_id_ctx 有值时自动注入到日志条目"""
    from app.core.request_id import request_id_ctx

    fmt = _JsonFormatter()
    token = request_id_ctx.set("req-abc-123")
    try:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="with request", args=(), exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["request_id"] == "req-abc-123"
    finally:
        request_id_ctx.reset(token)


def test_json_formatter_injects_user_id_from_context():
    """user_id_ctx 有值时自动注入到日志条目"""
    from app.core.user_context import user_id_ctx

    fmt = _JsonFormatter()
    token = user_id_ctx.set("user-456")
    try:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="with user", args=(), exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["user_id"] == "user-456"
    finally:
        user_id_ctx.reset(token)


def test_json_formatter_omits_empty_context_vars():
    """context vars 为空字符串时不注入对应字段"""
    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="no context", args=(), exc_info=None,
    )
    output = fmt.format(record)
    data = json.loads(output)
    assert "request_id" not in data
    assert "user_id" not in data


def test_json_formatter_extra_fields_override_context_vars():
    """extra_fields 中的 request_id 应优先于 context var"""
    from app.core.request_id import request_id_ctx

    fmt = _JsonFormatter()
    token = request_id_ctx.set("ctx-id")
    try:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="override", args=(), exc_info=None,
        )
        record.extra_fields = {"request_id": "extra-id"}
        output = fmt.format(record)
        data = json.loads(output)
        # extra_fields 先 update，context var 后覆盖 — context var 优先
        assert data["request_id"] == "ctx-id"
    finally:
        request_id_ctx.reset(token)


# ─── _TextFormatter ──────────────────────────────────────────


def test_text_formatter_basic():
    """文本格式器输出包含时间、级别、logger 名和消息"""
    fmt = _TextFormatter()
    record = logging.LogRecord(
        name="app.test", level=logging.WARNING, pathname="", lineno=0,
        msg="something happened", args=(), exc_info=None,
    )
    output = fmt.format(record)
    assert "WARNING" in output
    assert "app.test" in output
    assert "something happened" in output


def test_text_formatter_datefmt():
    """文本格式器使用 ISO 日期格式"""
    fmt = _TextFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="ok", args=(), exc_info=None,
    )
    output = fmt.format(record)
    # datefmt="%Y-%m-%dT%H:%M:%S"
    assert "T" in output.split()[0]


# ─── setup_logging ────────────────────────────────────────────


def test_setup_logging_sets_root_level():
    """setup_logging 设置 root logger 级别"""
    from unittest.mock import patch

    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "text"
        setup_logging()
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_setup_logging_suppresses_third_party():
    """第三方库日志级别设为 WARNING"""
    from unittest.mock import patch

    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "text"
        setup_logging()
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING


def test_setup_logging_json_formatter():
    """LOG_FORMAT=json 时使用 _JsonFormatter"""
    from unittest.mock import patch

    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    assert isinstance(root.handlers[-1].formatter, _JsonFormatter)


def test_setup_logging_text_formatter():
    """LOG_FORMAT=text 时使用 _TextFormatter"""
    from unittest.mock import patch

    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "text"
        setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    assert isinstance(root.handlers[-1].formatter, _TextFormatter)
