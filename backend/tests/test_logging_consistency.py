"""结构化日志字段完整性校验 — 确保所有日志条目包含必要字段"""

import json
import logging

import pytest

from app.core.config import settings
from app.core.logging import _JsonFormatter, _TextFormatter


@pytest.fixture
def json_formatter():
    return _JsonFormatter()


@pytest.fixture
def text_formatter():
    return _TextFormatter()


def _make_record(msg="test message", level=logging.INFO, logger_name="app.test"):
    return logging.LogRecord(
        name=logger_name, level=level,
        pathname="", lineno=0, msg=msg, args=None, exc_info=None,
    )


# ─── JSON 格式器基础字段 ──────────────────────────────────────


def test_json_output_is_valid(json_formatter):
    """JSON 格式器输出合法 JSON"""
    record = _make_record("hello world")
    output = json_formatter.format(record)
    data = json.loads(output)
    assert isinstance(data, dict)


def test_json_has_required_fields(json_formatter):
    """每条 JSON 日志包含 5 个基础字段"""
    record = _make_record()
    data = json.loads(json_formatter.format(record))
    for field in ("timestamp", "level", "logger", "message", "app_env"):
        assert field in data, f"缺少必要字段: {field}"


def test_json_timestamp_iso_format(json_formatter):
    """timestamp 为 ISO 8601 格式"""
    record = _make_record()
    data = json.loads(json_formatter.format(record))
    ts = data["timestamp"]
    assert ts.endswith("+00:00") or "T" in ts
    assert len(ts) >= 20


def test_json_level_name(json_formatter):
    """level 字段为标准日志级别名"""
    for level, name in [(logging.INFO, "INFO"), (logging.WARNING, "WARNING"), (logging.ERROR, "ERROR")]:
        record = _make_record(level=level)
        data = json.loads(json_formatter.format(record))
        assert data["level"] == name


def test_json_logger_name(json_formatter):
    """logger 字段为记录器名称"""
    record = _make_record(logger_name="app.request")
    data = json.loads(json_formatter.format(record))
    assert data["logger"] == "app.request"


def test_json_message_content(json_formatter):
    """message 字段为日志消息内容"""
    record = _make_record("用户登录成功")
    data = json.loads(json_formatter.format(record))
    assert data["message"] == "用户登录成功"


def test_json_app_env(json_formatter):
    """app_env 字段反映当前环境"""
    record = _make_record()
    data = json.loads(json_formatter.format(record))
    assert data["app_env"] == settings.APP_ENV


def test_json_unicode_escaped_false(json_formatter):
    """中文字符不被 Unicode 转义"""
    record = _make_record("测试消息🎉")
    output = json_formatter.format(record)
    assert "测试消息🎉" in output
    assert "\\u" not in output.split('"message":')[1].split('"')[1]


# ─── extra_fields 扩展字段 ─────────────────────────────────────


def test_json_extra_fields_merged(json_formatter):
    """extra_fields 中的字段合并到日志条目"""
    record = _make_record("请求日志")
    record.extra_fields = {  # type: ignore[attr-defined]
        "method": "GET",
        "path": "/api/v1/products",
        "status": 200,
        "duration_ms": 12.5,
        "client_ip": "127.0.0.1",
    }
    data = json.loads(json_formatter.format(record))
    assert data["method"] == "GET"
    assert data["path"] == "/api/v1/products"
    assert data["status"] == 200
    assert data["duration_ms"] == 12.5
    assert data["client_ip"] == "127.0.0.1"


def test_json_request_log_has_all_required_extra_fields(json_formatter):
    """请求日志 extra_fields 包含 10 个必要字段"""
    record = _make_record("GET /api/v1/health 200 2.5ms")
    record.extra_fields = {  # type: ignore[attr-defined]
        "method": "GET",
        "path": "/api/v1/health",
        "query_string": None,
        "status": 200,
        "duration_ms": 2.5,
        "client_ip": "127.0.0.1",
        "user_agent": "test-client/1.0",
        "slow": False,
        "request_id": "req-123",
        "resp_bytes": 150,
    }
    data = json.loads(json_formatter.format(record))
    expected = {"method", "path", "query_string", "status", "duration_ms",
                "client_ip", "user_agent", "slow", "request_id", "resp_bytes"}
    for field in expected:
        assert field in data, f"请求日志缺少字段: {field}"


# ─── 异常格式化 ──────────────────────────────────────────────


def test_json_exception_included(json_formatter):
    """异常信息被包含在 exception 字段"""
    import sys
    try:
        raise ValueError("模拟异常")
    except ValueError:
        record = _make_record("发生错误", level=logging.ERROR)
        record.exc_info = sys.exc_info()

    data = json.loads(json_formatter.format(record))
    assert "exception" in data
    assert "ValueError" in data["exception"]
    assert "模拟异常" in data["exception"]


def test_json_no_exception_when_none(json_formatter):
    """无异常时不含 exception 字段"""
    record = _make_record()
    data = json.loads(json_formatter.format(record))
    assert "exception" not in data


# ─── 文本格式器 ──────────────────────────────────────────────


def test_text_formatter_output(text_formatter):
    """文本格式器输出可读字符串"""
    record = _make_record("hello")
    output = text_formatter.format(record)
    assert isinstance(output, str)
    assert "hello" in output
    assert "INFO" in output


def test_text_formatter_not_json(text_formatter):
    """文本格式器输出不是 JSON"""
    record = _make_record("test")
    output = text_formatter.format(record)
    with pytest.raises(json.JSONDecodeError):
        json.loads(output)
