"""audit_service 内部函数单元测试 — _mask_sensitive / model_to_dict / get_request_meta / 模型字段 / 动作类型"""

import uuid
from unittest.mock import MagicMock

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models.audit import AuditLog
from app.services.audit_service import (
    SENSITIVE_FIELDS,
    _mask_sensitive,
    get_request_meta,
    model_to_dict,
)

# ─── _mask_sensitive ────────────────────────────────────────


def test_mask_sensitive_none():
    """None 输入直接返回 None"""
    assert _mask_sensitive(None) is None


def test_mask_sensitive_empty():
    """空字典直接返回空字典"""
    assert _mask_sensitive({}) == {}


def test_mask_sensitive_password():
    """password 字段脱敏"""
    result = _mask_sensitive({"password": "secret123", "name": "test"})
    assert result["password"] == "***"
    assert result["name"] == "test"


def test_mask_sensitive_token():
    """包含 token 子串的字段脱敏"""
    result = _mask_sensitive({"access_token": "abc", "refresh_token": "def", "username": "admin"})
    assert result["access_token"] == "***"
    assert result["refresh_token"] == "***"
    assert result["username"] == "admin"


def test_mask_sensitive_no_match():
    """无敏感字段时原样返回"""
    data = {"name": "test", "address": "beijing"}
    assert _mask_sensitive(data) == data


def test_mask_sensitive_phone_email():
    """手机号和邮箱脱敏"""
    result = _mask_sensitive({"phone": "13800138000", "email": "a@b.com", "name": "test"})
    assert result["phone"] == "***"
    assert result["email"] == "***"
    assert result["name"] == "test"


def test_mask_sensitive_case_insensitive():
    """字段名匹配不区分大小写"""
    assert _mask_sensitive({"Password": "x"})["Password"] == "***"
    assert _mask_sensitive({"EMAIL": "x"})["EMAIL"] == "***"
    assert _mask_sensitive({"Phone_Number": "x"})["Phone_Number"] == "***"


def test_mask_sensitive_all_keywords():
    """所有敏感关键词均被脱敏"""
    for keyword in SENSITIVE_FIELDS:
        result = _mask_sensitive({keyword: "sensitive_value"})
        assert result[keyword] == "***", f"{keyword} 未被脱敏"


def test_mask_sensitive_nested_not_touched():
    """嵌套 dict 值不被递归脱敏"""
    data = {"meta": {"phone": "13800138000"}}
    result = _mask_sensitive(data)
    assert result["meta"]["phone"] == "13800138000"


def test_mask_sensitive_partial_key_match():
    """key 包含敏感词即匹配"""
    assert _mask_sensitive({"user_email_address": "a@b.com"})["user_email_address"] == "***"
    assert _mask_sensitive({"secret_key": "xyz"})["secret_key"] == "***"


# ─── model_to_dict ──────────────────────────────────────────


class _Base(DeclarativeBase):
    pass


class _SampleModel(_Base):
    __tablename__ = "_test_sample_model"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))


_test_engine = create_engine("sqlite://")
_Base.metadata.create_all(bind=_test_engine)
_TestSession = sessionmaker(bind=_test_engine)


def test_model_to_dict_with_uuid():
    """UUID 字段转为字符串"""
    uid = uuid.uuid4()
    log = AuditLog(
        id=uid,
        actor_id=uuid.uuid4(),
        actor_name="tester",
        action="test_action",
        resource_type="order",
    )
    result = model_to_dict(log)
    assert result["id"] == str(uid)
    assert result["actor_name"] == "tester"
    assert result["action"] == "test_action"


def test_model_to_dict_skips_none():
    """None 值字段被跳过"""
    obj = _SampleModel(id="abc", name=None, status="active")
    result = model_to_dict(obj)
    assert "name" not in result
    assert result["id"] == "abc"
    assert result["status"] == "active"


def test_model_to_dict_returns_dict():
    """返回 dict 类型"""
    log = AuditLog(id=uuid.uuid4(), action="test")
    assert isinstance(model_to_dict(log), dict)


# ─── get_request_meta ────────────────────────────────────────


def _mock_request(*, host="127.0.0.1", user_agent="TestAgent", request_id=""):
    req = MagicMock()
    req.client = MagicMock() if host else None
    if host:
        req.client.host = host
    req.headers = {"user-agent": user_agent}
    if request_id:
        req.headers["x-request-id"] = request_id
    return req


def test_get_request_meta_basic():
    """基本请求元信息提取"""
    req = _mock_request()
    meta = get_request_meta(req)
    assert meta["ip_address"] == "127.0.0.1"
    assert meta["user_agent"] == "TestAgent"


def test_get_request_meta_no_client():
    """无客户端信息时 IP 为 None"""
    req = _mock_request(host=None)
    meta = get_request_meta(req)
    assert meta["ip_address"] is None


def test_get_request_meta_with_request_id():
    """透传 x-request-id"""
    req = _mock_request(request_id="req-123")
    meta = get_request_meta(req)
    assert meta["request_id"] == "req-123"


# ─── log_action user_agent 截断 ──────────────────────────────


def _make_db():
    from app.models.audit import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_log_action_truncates_long_user_agent():
    """超长 user_agent 被截断到 500 字符"""
    from app.services.audit_service import log_action

    db = _make_db()
    long_ua = "A" * 600
    log_action(
        db, action="test", resource_type="user",
        actor_name="tester", user_agent=long_ua,
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert len(log.user_agent) == 500
    assert log.user_agent == "A" * 500


def test_log_action_short_user_agent_unchanged():
    """短 user_agent 不被截断"""
    from app.services.audit_service import log_action

    db = _make_db()
    log_action(
        db, action="test", resource_type="user",
        actor_name="tester", user_agent="ShortAgent/1.0",
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert log.user_agent == "ShortAgent/1.0"


def test_log_action_before_data_masked():
    """before_data 中的敏感字段被脱敏"""
    import json

    from app.services.audit_service import log_action

    db = _make_db()
    log_action(
        db, action="customer_update", resource_type="customer",
        actor_name="tester",
        before_data={"name": "张三", "phone": "13800138000", "email": "a@b.com"},
    )
    db.flush()
    log = db.query(AuditLog).first()
    data = json.loads(log.before_data)
    assert data["name"] == "张三"
    assert data["phone"] == "***"
    assert data["email"] == "***"


def test_log_action_after_data_masked():
    """after_data 中的敏感字段被脱敏"""
    import json

    from app.services.audit_service import log_action

    db = _make_db()
    log_action(
        db, action="user_create", resource_type="user",
        actor_name="tester",
        after_data={"username": "newuser", "password": "TestPass123!", "email": "x@y.com"},
    )
    db.flush()
    log = db.query(AuditLog).first()
    data = json.loads(log.after_data)
    assert data["username"] == "newuser"
    assert data["password"] == "***"
    assert data["email"] == "***"


def test_log_action_none_data_stored_as_none():
    """before_data 和 after_data 为 None 时不存储"""
    from app.services.audit_service import log_action

    db = _make_db()
    log_action(
        db, action="login_success", resource_type="user",
        actor_name="tester",
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert log.before_data is None
    assert log.after_data is None


def test_log_action_unicode_preserved():
    """脱敏后 JSON 保持中文不被 Unicode 转义"""
    from app.services.audit_service import log_action

    db = _make_db()
    log_action(
        db, action="customer_create", resource_type="customer",
        actor_name="tester",
        after_data={"name": "中文用户名🎉", "level": "vip"},
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert "中文用户名🎉" in log.after_data
    assert "\\u" not in log.after_data


# ─── AuditLog 模型字段完整性 ─────────────────────────────────


class TestAuditLogModel:
    def test_model_has_expected_columns(self):
        """AuditLog 模型包含所有预期列"""
        col_names = {c.key for c in AuditLog.__table__.columns}
        expected = {
            "id", "actor_id", "actor_name", "action", "resource_type",
            "resource_id", "before_data", "after_data", "ip_address",
            "user_agent", "request_id", "created_at",
        }
        assert expected == col_names

    def test_action_max_length_50(self):
        assert AuditLog.__table__.columns["action"].type.length == 50

    def test_resource_type_max_length_50(self):
        assert AuditLog.__table__.columns["resource_type"].type.length == 50

    def test_resource_id_max_length_64(self):
        assert AuditLog.__table__.columns["resource_id"].type.length == 64

    def test_ip_address_max_length_45(self):
        assert AuditLog.__table__.columns["ip_address"].type.length == 45

    def test_user_agent_max_length_500(self):
        assert AuditLog.__table__.columns["user_agent"].type.length == 500

    def test_request_id_max_length_64(self):
        assert AuditLog.__table__.columns["request_id"].type.length == 64

    def test_actor_name_max_length_100(self):
        assert AuditLog.__table__.columns["actor_name"].type.length == 100


# ─── 审计动作类型完整性 ──────────────────────────────────────


KNOWN_ACTIONS = {
    "login_success", "login_failed", "password_change",
    "user_create", "user_update",
    "role_create", "role_update", "role_delete",
    "customer_create", "customer_update", "customer_delete",
    "customer_transfer", "customer_import",
    "product_create", "product_update", "product_delete",
    "product_disable", "product_import",
    "order_create", "order_update", "order_confirm", "order_cancel",
    "payment_create", "payment_reverse",
    "inventory_adjust",
    "file_upload", "file_delete",
    "export_products", "export_customers", "export_orders", "export_payments",
}

KNOWN_RESOURCE_TYPES = {
    "user", "role", "customer", "product", "order", "payment", "file",
}


def test_all_actions_within_50_chars():
    """所有 action 值长度在 50 以内"""
    for action in KNOWN_ACTIONS:
        assert len(action) <= 50, f"action '{action}' 超过 50 字符"


def test_all_resource_types_within_50_chars():
    """所有 resource_type 值长度在 50 以内"""
    for rt in KNOWN_RESOURCE_TYPES:
        assert len(rt) <= 50, f"resource_type '{rt}' 超过 50 字符"


def test_known_action_count():
    """已知 action 数量为 31"""
    assert len(KNOWN_ACTIONS) == 31


def test_known_resource_type_count():
    """已知 resource_type 数量为 7"""
    assert len(KNOWN_RESOURCE_TYPES) == 7
