"""audit_service 内部函数单元测试 — _mask_sensitive / model_to_dict"""

import uuid

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models.audit import AuditLog
from app.services.audit_service import _mask_sensitive, model_to_dict

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
    data = {"name": "test", "email": "a@b.com"}
    assert _mask_sensitive(data) == data


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
