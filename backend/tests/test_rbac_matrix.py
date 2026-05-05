"""RBAC 权限矩阵边界测试 — 覆盖权限码完整性、角色分配、权限检查逻辑、数据范围"""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import _get_user_permissions, check_owner_or_forbid, has_permission
from app.db.seed import PERMISSIONS, ROLE_PERMISSIONS
from app.models.user import Permission, Role, User


def _make_user(*, is_superuser=False, perm_codes=None):
    """构建测试用户，可选附带权限"""
    user = User(
        id=uuid.uuid4(),
        username="test_user",
        hashed_password="x",
        is_superuser=is_superuser,
    )
    if perm_codes:
        role = Role(id=uuid.uuid4(), name="test_role")
        for code in perm_codes:
            p = Permission(id=uuid.uuid4(), code=code, name=code, module="test")
            role.permissions.append(p)
        user.roles.append(role)
    return user


# ═══════════════════════════════════════════════════════
# 1. 权限码定义完整性
# ═══════════════════════════════════════════════════════


def test_permission_count():
    """权限码数量"""
    assert len(PERMISSIONS) > 0


def test_all_permissions_have_code_name_module():
    """每个权限都有 code、name、module"""
    for code, name, module in PERMISSIONS:
        assert code, "权限缺少 code"
        assert name, f"{code} 缺少 name"
        assert module, f"{code} 缺少 module"


def test_permission_codes_unique():
    """权限码唯一"""
    codes = [p[0] for p in PERMISSIONS]
    assert len(codes) == len(set(codes))


def test_permission_codes_use_module_colon_action_format():
    """权限码格式为 module:action"""
    for code, _, _ in PERMISSIONS:
        assert ":" in code, f"{code} 缺少模块分隔符"
        parts = code.split(":")
        assert len(parts) == 2, f"{code} 格式不正确"


def test_permission_modules():
    """覆盖 9 个模块"""
    modules = {p[2] for p in PERMISSIONS}
    expected = {"用户管理", "角色管理", "商品管理", "客户管理", "订单管理", "库存管理", "收款管理", "报表", "审计"}
    assert modules == expected


def test_key_permissions_exist():
    """关键权限码存在"""
    codes = {p[0] for p in PERMISSIONS}
    for code in [
        "user:list", "user:create",
        "product:list", "product:view_cost",
        "customer:list", "customer:view_all",
        "order:list", "order:view_all",
        "inventory:list", "inventory:adjust",
        "payment:list", "payment:create",
        "report:sales", "report:profit",
        "audit:view",
    ]:
        assert code in codes, f"缺少权限码 {code}"


# ═══════════════════════════════════════════════════════
# 2. 角色定义完整性
# ═══════════════════════════════════════════════════════


def test_role_count():
    """共定义 6 个角色"""
    assert len(ROLE_PERMISSIONS) == 6


def test_roles_defined():
    """admin/sales_manager/sales/inventory/finance/audit 角色存在"""
    expected = {"admin", "sales_manager", "sales", "inventory", "finance", "audit"}
    assert set(ROLE_PERMISSIONS.keys()) == expected


def test_admin_has_all_permissions():
    """admin 角色拥有所有权限"""
    all_codes = {p[0] for p in PERMISSIONS}
    admin_codes = set(ROLE_PERMISSIONS["admin"])
    assert admin_codes == all_codes


def test_audit_role_minimal():
    """audit 角色只有 audit:view"""
    assert ROLE_PERMISSIONS["audit"] == ["audit:view"]


def test_sales_role_no_view_all():
    """sales 角色没有 customer:view_all 和 order:view_all"""
    sales_perms = set(ROLE_PERMISSIONS["sales"])
    assert "customer:view_all" not in sales_perms
    assert "order:view_all" not in sales_perms


def test_sales_manager_has_view_all():
    """sales_manager 角色有 customer:view_all 和 order:view_all"""
    sm_perms = set(ROLE_PERMISSIONS["sales_manager"])
    assert "customer:view_all" in sm_perms
    assert "order:view_all" in sm_perms


def test_finance_has_payment_reverse():
    """finance 角色有 payment:reverse"""
    fin_perms = set(ROLE_PERMISSIONS["finance"])
    assert "payment:reverse" in fin_perms


def test_inventory_has_adjust():
    """inventory 角色有 inventory:adjust"""
    inv_perms = set(ROLE_PERMISSIONS["inventory"])
    assert "inventory:adjust" in inv_perms


def test_no_role_has_all_permissions_except_admin():
    """除 admin 外其他角色不拥有所有权限"""
    all_codes = {p[0] for p in PERMISSIONS}
    for role_name, perms in ROLE_PERMISSIONS.items():
        if role_name == "admin":
            continue
        assert set(perms) != all_codes, f"{role_name} 拥有了所有权限"


def test_all_role_permissions_are_valid():
    """角色分配的权限都是已定义的"""
    all_codes = {p[0] for p in PERMISSIONS}
    for role_name, perms in ROLE_PERMISSIONS.items():
        for code in perms:
            assert code in all_codes, f"角色 {role_name} 引用了未定义的权限 {code}"


# ═══════════════════════════════════════════════════════
# 3. has_permission 逻辑
# ═══════════════════════════════════════════════════════


def test_superuser_has_all_permissions():
    """超级用户拥有所有权限"""
    user = _make_user(is_superuser=True)
    assert has_permission(user, "product:list") is True
    assert has_permission(user, "audit:view") is True
    assert has_permission(user, "nonexistent:perm") is True


def test_user_with_permission_returns_true():
    """有权限的用户返回 True"""
    user = _make_user(perm_codes=["product:list", "product:create"])
    assert has_permission(user, "product:list") is True
    assert has_permission(user, "product:create") is True


def test_user_without_permission_returns_false():
    """无权限的用户返回 False"""
    user = _make_user(perm_codes=["product:list"])
    assert has_permission(user, "product:delete") is False


def test_user_no_roles_returns_false():
    """无角色的用户返回 False"""
    user = _make_user()
    assert has_permission(user, "product:list") is False


def test_user_multiple_roles_permissions_merge():
    """多角色权限合并"""
    user = User(
        id=uuid.uuid4(), username="multi", hashed_password="x",
        is_superuser=False,
    )
    role1 = Role(id=uuid.uuid4(), name="r1")
    role1.permissions.append(Permission(id=uuid.uuid4(), code="product:list", name="", module=""))
    role2 = Role(id=uuid.uuid4(), name="r2")
    role2.permissions.append(Permission(id=uuid.uuid4(), code="order:list", name="", module=""))
    user.roles = [role1, role2]
    assert has_permission(user, "product:list") is True
    assert has_permission(user, "order:list") is True
    assert has_permission(user, "payment:list") is False


# ═══════════════════════════════════════════════════════
# 4. _get_user_permissions 逻辑
# ═══════════════════════════════════════════════════════


def test_get_user_permissions_returns_set():
    """返回权限码集合"""
    user = _make_user(perm_codes=["a:b", "c:d"])
    perms = _get_user_permissions(user)
    assert isinstance(perms, set)
    assert perms == {"a:b", "c:d"}


def test_get_user_permissions_empty():
    """无角色用户返回空集"""
    user = _make_user()
    assert _get_user_permissions(user) == set()


def test_get_user_permissions_deduplicates():
    """多角色中相同权限码去重"""
    user = User(id=uuid.uuid4(), username="dedup", hashed_password="x")
    code = "product:list"
    r1 = Role(id=uuid.uuid4(), name="r1")
    r1.permissions.append(Permission(id=uuid.uuid4(), code=code, name="", module=""))
    r2 = Role(id=uuid.uuid4(), name="r2")
    r2.permissions.append(Permission(id=uuid.uuid4(), code=code, name="", module=""))
    user.roles = [r1, r2]
    assert _get_user_permissions(user) == {code}


# ═══════════════════════════════════════════════════════
# 5. check_owner_or_forbid 逻辑
# ═══════════════════════════════════════════════════════


def test_check_owner_superuser_passes():
    """超级用户通过所有者检查"""
    user = _make_user(is_superuser=True)
    check_owner_or_forbid(user, uuid.uuid4(), "customer:view_all")


def test_check_owner_with_view_all_passes():
    """有 view_all 权限的用户通过"""
    user = _make_user(perm_codes=["customer:view_all"])
    check_owner_or_forbid(user, uuid.uuid4(), "customer:view_all")


def test_check_owner_own_data_passes():
    """所有者访问自己的数据通过"""
    user = _make_user(perm_codes=["customer:list"])
    check_owner_or_forbid(user, user.id, "customer:view_all")


def test_check_owner_other_data_forbidden():
    """非所有者且无 view_all 被拒绝"""
    user = _make_user(perm_codes=["customer:list"])
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, uuid.uuid4(), "customer:view_all", "客户")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "AUTH_FORBIDDEN"


def test_check_owner_error_includes_label():
    """403 错误消息包含资源标签"""
    user = _make_user(perm_codes=[])
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")
    assert "订单" in exc_info.value.detail["message"]


def test_check_owner_order_view_all():
    """order:view_all 权限检查"""
    user = _make_user(perm_codes=["order:view_all"])
    check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")


# ═══════════════════════════════════════════════════════
# 6. 权限分离原则
# ═══════════════════════════════════════════════════════


def test_view_cost_separate_from_list():
    """product:view_cost 与 product:list 分离"""
    codes = {p[0] for p in PERMISSIONS}
    assert "product:list" in codes
    assert "product:view_cost" in codes
    assert "product:list" != "product:view_cost"


def test_view_all_separate_from_list():
    """customer:view_all 和 order:view_all 独立定义"""
    codes = {p[0] for p in PERMISSIONS}
    assert "customer:view_all" in codes
    assert "order:view_all" in codes
    assert "customer:view_all" != "customer:list"


def test_sales_no_delete_permissions():
    """sales 角色没有产品和角色删除权限（客户删除已开放）"""
    sales_perms = set(ROLE_PERMISSIONS["sales"])
    for code in ["user:delete", "product:delete", "role:delete"]:
        assert code not in sales_perms
    # sales 可以删除自己创建的客户
    assert "customer:delete" in sales_perms


def test_inventory_no_customer_or_payment():
    """inventory 角色没有客户和收款权限"""
    inv_perms = set(ROLE_PERMISSIONS["inventory"])
    for code in ["customer:list", "customer:create", "payment:list", "payment:create"]:
        assert code not in inv_perms


def test_finance_no_create_update():
    """finance 角色没有创建和编辑商品/客户的权限"""
    fin_perms = set(ROLE_PERMISSIONS["finance"])
    for code in ["product:create", "product:update", "customer:create", "customer:update", "order:create"]:
        assert code not in fin_perms


def test_audit_no_data_access():
    """audit 角色没有数据访问权限"""
    audit_perms = set(ROLE_PERMISSIONS["audit"])
    for code in ["product:list", "customer:list", "order:list", "payment:list", "user:list"]:
        assert code not in audit_perms
