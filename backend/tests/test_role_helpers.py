"""角色辅助函数单元测试 — _require_superuser / _serialize_role"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.roles import (
    _require_superuser,
    _serialize_role,
)

# ─── _require_superuser ────────────────────────────────────────


def test_require_superuser_passes():
    """超级管理员通过检查"""
    user = MagicMock()
    user.is_superuser = True
    _require_superuser(user)  # 不抛异常


def test_require_superuser_rejects_non_superuser():
    """非超级管理员抛 403"""
    user = MagicMock()
    user.is_superuser = False
    with pytest.raises(HTTPException) as exc_info:
        _require_superuser(user)
    assert exc_info.value.status_code == 403
    assert "仅超级管理员" in str(exc_info.value.detail)


def test_require_superuser_rejects_none_is_superuser():
    """is_superuser 为 None 时视为 False"""
    user = MagicMock()
    user.is_superuser = None
    with pytest.raises(HTTPException):
        _require_superuser(user)


# ─── _serialize_role ───────────────────────────────────────────


def _mock_permission(pid="p-1", code="order:view", name="查看订单", module="订单"):
    p = MagicMock()
    p.id = pid
    p.code = code
    p.name = name
    p.module = module
    return p


def _mock_role(**overrides):
    role = MagicMock()
    defaults = {
        "id": "r-1",
        "name": "admin",
        "display_name": "管理员",
        "description": "系统管理员",
        "permissions": [_mock_permission()],
        "users": [MagicMock()],  # 1 个用户
        "created_at": datetime(2026, 5, 1, 10, 0, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 2, 15, 30, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(role, k, v)
    return role


def test_serialize_role_basic():
    """基本序列化"""
    role = _mock_role()
    result = _serialize_role(role)
    assert result["id"] == "r-1"
    assert result["name"] == "admin"
    assert result["display_name"] == "管理员"
    assert result["description"] == "系统管理员"
    assert result["user_count"] == 1


def test_serialize_role_permissions():
    """权限列表序列化"""
    perms = [_mock_permission("p-1", "order:view", "查看订单", "订单"),
             _mock_permission("p-2", "order:create", "创建订单", "订单")]
    role = _mock_role(permissions=perms)
    result = _serialize_role(role)
    assert len(result["permissions"]) == 2
    assert result["permissions"][0]["code"] == "order:view"
    assert result["permissions"][1]["code"] == "order:create"


def test_serialize_role_empty_permissions():
    """无权限的角色"""
    role = _mock_role(permissions=[])
    result = _serialize_role(role)
    assert result["permissions"] == []
    assert result["user_count"] == 1


def test_serialize_role_no_users():
    """无用户的角色"""
    role = _mock_role(users=[])
    result = _serialize_role(role)
    assert result["user_count"] == 0


def test_serialize_role_none_timestamps():
    """created_at/updated_at 为 None 时返回 null"""
    role = _mock_role(created_at=None, updated_at=None)
    result = _serialize_role(role)
    assert result["created_at"] is None
    assert result["updated_at"] is None


def test_serialize_role_isoformat():
    """时间戳格式化为 ISO 8601"""
    dt = datetime(2026, 5, 3, 8, 30, 0, tzinfo=UTC)
    role = _mock_role(created_at=dt, updated_at=dt)
    result = _serialize_role(role)
    assert result["created_at"] == dt.isoformat()
    assert result["updated_at"] == dt.isoformat()
