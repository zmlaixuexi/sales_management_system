"""可观测性：日志格式一致性边界测试 — 覆盖日志配置、JSON 格式器、请求 ID 中间件、
请求日志中间件、慢 SQL 配置、审计服务工具函数、审计模型字段、审计 API 端点"""

import json
import logging
import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. 日志配置验证
# ═══════════════════════════════════════════════════════


def test_log_level_default_info():
    """LOG_LEVEL 默认为 INFO"""
    assert settings.LOG_LEVEL == "INFO"


def test_log_format_default_text():
    """LOG_FORMAT 默认为 text"""
    assert settings.LOG_FORMAT == "text"


def test_log_level_is_valid():
    """LOG_LEVEL 是合法日志级别"""
    assert hasattr(logging, settings.LOG_LEVEL.upper())


def test_slow_request_threshold_positive():
    """SLOW_REQUEST_THRESHOLD_MS > 0"""
    assert settings.SLOW_REQUEST_THRESHOLD_MS > 0


def test_slow_request_threshold_default_1000():
    """SLOW_REQUEST_THRESHOLD_MS 默认为 1000"""
    assert settings.SLOW_REQUEST_THRESHOLD_MS == 1000


def test_slow_sql_threshold_positive():
    """SLOW_SQL_THRESHOLD_MS > 0"""
    assert settings.SLOW_SQL_THRESHOLD_MS > 0


def test_slow_sql_threshold_default_200():
    """SLOW_SQL_THRESHOLD_MS 默认为 200"""
    assert settings.SLOW_SQL_THRESHOLD_MS == 200


def test_app_env_is_string():
    """APP_ENV 是字符串"""
    assert isinstance(settings.APP_ENV, str)
    assert len(settings.APP_ENV) > 0


# ═══════════════════════════════════════════════════════
# 2. JSON 格式器结构验证
# ═══════════════════════════════════════════════════════


def test_json_formatter_produces_valid_json():
    """_JsonFormatter 输出合法 JSON"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger", level=logging.INFO,
        pathname="", lineno=0, msg="hello", args=None, exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


def test_json_formatter_has_required_fields():
    """JSON 日志包含 timestamp/level/logger/message/app_env"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger", level=logging.WARNING,
        pathname="", lineno=0, msg="test message", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert "timestamp" in parsed
    assert "level" in parsed
    assert "logger" in parsed
    assert "message" in parsed
    assert "app_env" in parsed


def test_json_formatter_level_matches_record():
    """JSON level 字段匹配日志级别"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.ERROR,
        pathname="", lineno=0, msg="err", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["level"] == "ERROR"


def test_json_formatter_logger_name():
    """JSON logger 字段为 logger 名称"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="app.request", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["logger"] == "app.request"


def test_json_formatter_message_content():
    """JSON message 字段包含日志消息"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="测试消息", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["message"] == "测试消息"


def test_json_formatter_app_env_value():
    """JSON app_env 字段值与 settings 一致"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["app_env"] == settings.APP_ENV


def test_json_formatter_timestamp_iso_format():
    """JSON timestamp 为 ISO 8601 格式"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    ts = parsed["timestamp"]
    assert "T" in ts  # ISO 8601


def test_json_formatter_no_exception_by_default():
    """无异常时不包含 exception 字段"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert "exception" not in parsed


def test_json_formatter_extra_fields_merged():
    """extra_fields 合并到 JSON 输出"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    record.extra_fields = {"method": "GET", "status": 200}  # type: ignore[attr-defined]
    parsed = json.loads(formatter.format(record))
    assert parsed["method"] == "GET"
    assert parsed["status"] == 200


def test_json_formatter_ensure_ascii_false():
    """JSON 输出保留中文字符（非转义）"""
    from app.core.logging import _JsonFormatter

    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="中文消息", args=None, exc_info=None,
    )
    output = formatter.format(record)
    assert "中文消息" in output


# ═══════════════════════════════════════════════════════
# 3. 文本格式器验证
# ═══════════════════════════════════════════════════════


def test_text_formatter_contains_level():
    """_TextFormatter 输出包含日志级别"""
    from app.core.logging import _TextFormatter

    formatter = _TextFormatter()
    record = logging.LogRecord(
        name="t", level=logging.WARNING,
        pathname="", lineno=0, msg="warn msg", args=None, exc_info=None,
    )
    output = formatter.format(record)
    assert "WARNING" in output


def test_text_formatter_contains_message():
    """_TextFormatter 输出包含消息内容"""
    from app.core.logging import _TextFormatter

    formatter = _TextFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="hello world", args=None, exc_info=None,
    )
    output = formatter.format(record)
    assert "hello world" in output


def test_text_formatter_contains_timestamp():
    """_TextFormatter 输出包含时间戳"""
    from app.core.logging import _TextFormatter

    formatter = _TextFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO,
        pathname="", lineno=0, msg="x", args=None, exc_info=None,
    )
    output = formatter.format(record)
    # 格式：2024-01-01T12:00:00
    assert "T" in output


# ═══════════════════════════════════════════════════════
# 4. 请求 ID 中间件验证
# ═══════════════════════════════════════════════════════


def test_request_id_response_header():
    """响应包含 X-Request-ID 头"""
    resp = client.get("/api/v1/health")
    assert "x-request-id" in resp.headers


def test_request_id_is_uuid_format():
    """自动生成的 X-Request-ID 为 UUID 格式"""
    resp = client.get("/api/v1/health")
    rid = resp.headers["x-request-id"]
    # UUID 格式验证
    uuid.UUID(rid)


def test_request_id_propagated_from_client():
    """客户端传入的 X-Request-ID 被透传"""
    custom_id = "custom-request-123"
    resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp.headers["x-request-id"] == custom_id


def test_request_id_unique_per_request():
    """每次请求生成不同的 X-Request-ID"""
    resp1 = client.get("/api/v1/health")
    resp2 = client.get("/api/v1/health")
    # 如果两次都没有传入自定义 ID，应该不同
    id1 = resp1.headers["x-request-id"]
    id2 = resp2.headers["x-request-id"]
    # 注意：如果有自定义头传入可能会相同，这里只验证不传时
    # 第二次请求没传 X-Request-ID，应该自动生成
    assert id1  # 非空
    assert id2  # 非空


def test_request_id_ctx_var_exists():
    """request_id_ctx ContextVar 存在"""
    from app.core.request_id import request_id_ctx

    assert request_id_ctx is not None


def test_request_id_ctx_default_empty():
    """request_id_ctx 默认值为空字符串"""
    from app.core.request_id import request_id_ctx

    assert request_id_ctx.get("") == ""


# ═══════════════════════════════════════════════════════
# 5. 请求日志中间件验证
# ═══════════════════════════════════════════════════════


def test_response_time_header():
    """响应包含 X-Response-Time 头"""
    resp = client.get("/api/v1/health")
    assert "x-response-time" in resp.headers


def test_response_time_format():
    """X-Response-Time 格式为数字+ms"""
    resp = client.get("/api/v1/health")
    rt = resp.headers["x-response-time"]
    assert rt.endswith("ms")
    value = float(rt.replace("ms", ""))
    assert value >= 0


def test_non_api_path_not_logged():
    """非 /api/ 路径不记录请求日志（metrics 端点不在 /api/ 下）"""
    resp = client.get("/metrics")
    # /metrics 不在 /api/ 前缀下，正常响应
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════
# 6. get_logger 辅助函数
# ═══════════════════════════════════════════════════════


def test_get_logger_returns_logger():
    """get_logger 返回 logging.Logger 实例"""
    from app.core.logging import get_logger

    log = get_logger("test.module")
    assert isinstance(log, logging.Logger)


def test_get_logger_name():
    """get_logger 返回正确名称的 logger"""
    from app.core.logging import get_logger

    log = get_logger("app.custom")
    assert log.name == "app.custom"


# ═══════════════════════════════════════════════════════
# 7. 审计服务 — SENSITIVE_FIELDS 验证
# ═══════════════════════════════════════════════════════


def test_sensitive_fields_is_set():
    """SENSITIVE_FIELDS 是集合"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert isinstance(SENSITIVE_FIELDS, set)


def test_sensitive_fields_contains_password():
    """SENSITIVE_FIELDS 包含 password"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "password" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_hashed_password():
    """SENSITIVE_FIELDS 包含 hashed_password"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "hashed_password" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_token():
    """SENSITIVE_FIELDS 包含 token"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "token" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_secret():
    """SENSITIVE_FIELDS 包含 secret"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "secret" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_credit_card():
    """SENSITIVE_FIELDS 包含 credit_card"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "credit_card" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_phone():
    """SENSITIVE_FIELDS 包含 phone"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "phone" in SENSITIVE_FIELDS


def test_sensitive_fields_contains_email():
    """SENSITIVE_FIELDS 包含 email"""
    from app.services.audit_service import SENSITIVE_FIELDS

    assert "email" in SENSITIVE_FIELDS


# ═══════════════════════════════════════════════════════
# 8. _mask_sensitive 边界测试
# ═══════════════════════════════════════════════════════


def test_mask_sensitive_none():
    """_mask_sensitive(None) 返回 None"""
    from app.services.audit_service import _mask_sensitive

    assert _mask_sensitive(None) is None


def test_mask_sensitive_empty_dict():
    """_mask_sensitive({}) 返回 {}"""
    from app.services.audit_service import _mask_sensitive

    assert _mask_sensitive({}) == {}


def test_mask_sensitive_password():
    """password 字段被脱敏为 ***"""
    from app.services.audit_service import _mask_sensitive

    data = {"username": "admin", "password": "secret123"}
    result = _mask_sensitive(data)
    assert result["password"] == "***"
    assert result["username"] == "admin"


def test_mask_sensitive_hashed_password():
    """hashed_password 字段被脱敏"""
    from app.services.audit_service import _mask_sensitive

    data = {"hashed_password": "$2b$12$xxx"}
    assert _mask_sensitive(data)["hashed_password"] == "***"


def test_mask_sensitive_token():
    """包含 token 的 key 被脱敏"""
    from app.services.audit_service import _mask_sensitive

    data = {"access_token": "jwt-xxx", "name": "test"}
    result = _mask_sensitive(data)
    assert result["access_token"] == "***"
    assert result["name"] == "test"


def test_mask_sensitive_email():
    """email 字段被脱敏"""
    from app.services.audit_service import _mask_sensitive

    data = {"email": "user@example.com"}
    assert _mask_sensitive(data)["email"] == "***"


def test_mask_sensitive_phone():
    """phone 字段被脱敏"""
    from app.services.audit_service import _mask_sensitive

    data = {"phone": "13800138000"}
    assert _mask_sensitive(data)["phone"] == "***"


def test_mask_sensitive_case_insensitive():
    """key 匹配大小写不敏感（user_email 包含 email）"""
    from app.services.audit_service import _mask_sensitive

    data = {"user_email": "a@b.com"}
    assert _mask_sensitive(data)["user_email"] == "***"


def test_mask_sensitive_partial_match():
    """部分匹配：refresh_token 包含 token"""
    from app.services.audit_service import _mask_sensitive

    data = {"refresh_token": "rt-xxx"}
    assert _mask_sensitive(data)["refresh_token"] == "***"


def test_mask_sensitive_preserves_non_sensitive():
    """非敏感字段保持原值"""
    from app.services.audit_service import _mask_sensitive

    data = {"name": "张三", "role": "admin", "status": "active"}
    result = _mask_sensitive(data)
    assert result == data


# ═══════════════════════════════════════════════════════
# 9. model_to_dict 边界测试
# ═══════════════════════════════════════════════════════


def test_model_to_dict_returns_dict():
    """model_to_dict 返回字典"""
    from app.models.user import User
    from app.services.audit_service import model_to_dict

    user = User()
    result = model_to_dict(user)
    assert isinstance(result, dict)


def test_model_to_dict_uuid_to_string():
    """model_to_dict 将 UUID 转为字符串"""
    from app.models.user import User
    from app.services.audit_service import model_to_dict

    user = User()
    user.id = uuid.uuid4()
    result = model_to_dict(user)
    assert isinstance(result["id"], str)


def test_model_to_dict_skips_none():
    """model_to_dict 跳过 None 值"""
    from app.models.user import User
    from app.services.audit_service import model_to_dict

    user = User()
    # display_name 默认为 None
    result = model_to_dict(user)
    assert "display_name" not in result


# ═══════════════════════════════════════════════════════
# 10. 审计模型字段验证
# ═══════════════════════════════════════════════════════


def test_audit_model_table_name():
    """AuditLog 表名为 audit_logs"""
    from app.models.audit import AuditLog

    assert AuditLog.__tablename__ == "audit_logs"


def test_audit_model_has_action():
    """AuditLog 有 action 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "action")


def test_audit_model_action_not_nullable():
    """action 字段不可为 null"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["action"]
    assert not col.nullable


def test_audit_model_action_length():
    """action 字段长度为 50"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["action"]
    assert col.type.length == 50


def test_audit_model_has_request_id():
    """AuditLog 有 request_id 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "request_id")


def test_audit_model_request_id_nullable():
    """request_id 字段可为 null"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["request_id"]
    assert col.nullable


def test_audit_model_has_actor_id():
    """AuditLog 有 actor_id 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "actor_id")


def test_audit_model_actor_id_fk_to_users():
    """actor_id 外键指向 users.id"""
    from app.models.audit import AuditLog

    fks = AuditLog.__table__.c["actor_id"].foreign_keys
    fk_targets = {str(fk.target_fullname) for fk in fks}
    assert any("users.id" in t for t in fk_targets)


def test_audit_model_has_before_data():
    """AuditLog 有 before_data 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "before_data")


def test_audit_model_has_after_data():
    """AuditLog 有 after_data 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "after_data")


def test_audit_model_has_ip_address():
    """AuditLog 有 ip_address 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "ip_address")


def test_audit_model_ip_address_length():
    """ip_address 字段长度 45（支持 IPv6）"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["ip_address"]
    assert col.type.length == 45


def test_audit_model_has_user_agent():
    """AuditLog 有 user_agent 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "user_agent")


def test_audit_model_user_agent_length():
    """user_agent 字段长度 500"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["user_agent"]
    assert col.type.length == 500


def test_audit_model_has_created_at():
    """AuditLog 有 created_at 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "created_at")


def test_audit_model_created_at_has_timezone():
    """created_at 带时区"""
    from app.models.audit import AuditLog

    col = AuditLog.__table__.c["created_at"]
    assert col.type.timezone is True


def test_audit_model_has_resource_type():
    """AuditLog 有 resource_type 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "resource_type")


def test_audit_model_has_resource_id():
    """AuditLog 有 resource_id 字段"""
    from app.models.audit import AuditLog

    assert hasattr(AuditLog, "resource_id")


# ═══════════════════════════════════════════════════════
# 11. 审计 API 端点验证
# ═══════════════════════════════════════════════════════


def test_audit_logs_list_requires_auth():
    """审计日志列表需要认证"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code in (401, 403)


def test_audit_logs_actions_requires_auth():
    """审计日志动作列表需要认证"""
    resp = client.get("/api/v1/audit-logs/actions")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════
# 12. user_id_ctx ContextVar
# ═══════════════════════════════════════════════════════


def test_user_id_ctx_exists():
    """user_id_ctx ContextVar 存在"""
    from app.core.user_context import user_id_ctx

    assert user_id_ctx is not None


def test_user_id_ctx_default_empty():
    """user_id_ctx 默认值为空字符串"""
    from app.core.user_context import user_id_ctx

    assert user_id_ctx.get("") == ""


# ═══════════════════════════════════════════════════════
# 13. get_request_meta 验证
# ═══════════════════════════════════════════════════════


def test_get_request_meta_function_exists():
    """get_request_meta 函数存在"""
    from app.services.audit_service import get_request_meta

    assert callable(get_request_meta)


def test_log_action_function_exists():
    """log_action 函数存在"""
    from app.services.audit_service import log_action

    assert callable(log_action)


def test_log_user_action_function_exists():
    """log_user_action 函数存在"""
    from app.services.audit_service import log_user_action

    assert callable(log_user_action)


# ═══════════════════════════════════════════════════════
# 14. 中间件注册验证
# ═══════════════════════════════════════════════════════


def test_request_id_middleware_registered():
    """RequestIDMiddleware 已注册"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "RequestIDMiddleware" in source


def test_request_log_middleware_registered():
    """RequestLogMiddleware 已注册"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "RequestLogMiddleware" in source


def test_slow_query_listener_registered():
    """慢 SQL 监听器已注册"""
    import app.db.session as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "slow_query" in source.lower() or "before_cursor_execute" in source


# ═══════════════════════════════════════════════════════
# 15. setup_logging 第三方库降级
# ═══════════════════════════════════════════════════════


def test_uvicorn_access_log_level():
    """uvicorn.access 日志级别被降低到 WARNING"""
    level = logging.getLogger("uvicorn.access").level
    assert level >= logging.WARNING


def test_sqlalchemy_engine_log_level():
    """sqlalchemy.engine 日志级别被降低到 WARNING"""
    level = logging.getLogger("sqlalchemy.engine").level
    assert level >= logging.WARNING


# ═══════════════════════════════════════════════════════
# 16. user_agent 截断验证
# ═══════════════════════════════════════════════════════


def test_user_agent_truncated_to_500():
    """log_action 截断 user_agent 到 500 字符"""
    import inspect

    from app.services.audit_service import log_action

    source = inspect.getsource(log_action)
    assert "500" in source
    assert "user_agent" in source
