"""audit_service 内部函数单元测试 — _mask_sensitive / model_to_dict / get_request_meta"""

import uuid
from unittest.mock import MagicMock

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models.audit import AuditLog
from app.services.audit_service import _mask_sensitive, get_request_meta, model_to_dict

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
