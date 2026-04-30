"""deps.py 辅助函数单元测试"""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import _get_user_permissions, check_owner_or_forbid, has_permission
from app.models.user import User


def _make_user(*, superuser=False, perm_codes=None):
    """构造测试用户，直接绑定角色和权限"""
    from app.models.user import Permission, Role

    perms = [Permission(id=uuid.uuid4(), code=c, name=c) for c in (perm_codes or [])]
    role = Role(id=uuid.uuid4(), name="test_role", display_name="测试", permissions=perms)
    user = User(
        id=uuid.uuid4(),
        username="test",
        hashed_password="x",
        is_superuser=superuser,
        roles=[role],
    )
    return user


def test_get_user_permissions_collects_from_roles():
    """应收集所有角色的所有权限码"""
    user = _make_user(perm_codes=["product:view", "order:create", "customer:view"])
    perms = _get_user_permissions(user)
    assert perms == {"product:view", "order:create", "customer:view"}


def test_get_user_permissions_empty_roles():
    """无角色时返回空集"""
    user = _make_user(perm_codes=[])
    perms = _get_user_permissions(user)
    assert perms == set()


def test_get_user_permissions_dedup():
    """不同角色的相同权限码应去重"""
    from app.models.user import Permission, Role

    perm = Permission(id=uuid.uuid4(), code="product:view", name="查看商品")
    role1 = Role(id=uuid.uuid4(), name="r1", display_name="R1", permissions=[perm])
    role2 = Role(id=uuid.uuid4(), name="r2", display_name="R2", permissions=[perm])
    user = User(
        id=uuid.uuid4(),
        username="test",
        hashed_password="x",
        is_superuser=False,
        roles=[role1, role2],
    )
    perms = _get_user_permissions(user)
    assert perms == {"product:view"}


def test_has_permission_superuser():
    """超级用户自动拥有所有权限"""
    user = _make_user(superuser=True, perm_codes=[])
    assert has_permission(user, "anything") is True


def test_has_permission_granted():
    """拥有权限码时返回 True"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "product:view") is True


def test_has_permission_denied():
    """无权限码时返回 False"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "product:delete") is False


def test_check_owner_or_forbid_superuser():
    """超级用户直接通过"""
    user = _make_user(superuser=True)
    other_id = uuid.uuid4()
    check_owner_or_forbid(user, other_id, "order:view_all", "订单")


def test_check_owner_or_forbid_view_all():
    """有 view_all 权限的用户通过"""
    user = _make_user(perm_codes=["order:view_all"])
    check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")


def test_check_owner_or_forbid_owner():
    """资源所有者通过"""
    user = _make_user(perm_codes=[])
    check_owner_or_forbid(user, user.id, "order:view_all", "订单")


def test_check_owner_or_forbid_forbidden():
    """非所有者且无 view_all 权限 → 403"""
    user = _make_user(perm_codes=[])
    other_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, other_id, "order:view_all", "订单")
    assert exc_info.value.status_code == 403
    assert "无权访问此订单" in exc_info.value.detail["message"]
