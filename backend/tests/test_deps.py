"""deps.py 辅助函数单元测试"""

import uuid

from app.api.deps import _get_user_permissions, has_permission
from app.models.user import User


def _make_user(*, superuser=False, perm_codes=None):
    """构造测试用户，直接绑定角色和权限"""
    from app.models.user import Role, Permission

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
    from app.models.user import Role, Permission

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
