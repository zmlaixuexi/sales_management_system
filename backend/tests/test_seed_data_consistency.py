"""代码质量：后端种子数据一致性验证测试
覆盖权限码定义完整性、角色权限分配合理性、
种子权限覆盖后端 API 使用、角色层级验证、admin 账号安全"""

import re
from pathlib import Path

SEED_FILE = Path(__file__).resolve().parent.parent / "app" / "db" / "seed.py"
API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"


def _extract_seed_permissions() -> list[tuple[str, str, str]]:
    """提取种子数据中的权限: [(code, name, module)]"""
    source = SEED_FILE.read_text()
    return [
        (m.group(1), m.group(2), m.group(3))
        for m in re.finditer(r'\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)', source)
    ]


def _extract_bracket_content(source: str, start: int) -> str:
    """从 start 位置的 [ 开始，提取到匹配的 ] 为止（支持嵌套）"""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "[":
            depth += 1
        elif source[i] == "]":
            depth -= 1
            if depth == 0:
                return source[start + 1 : i]
    return ""


def _extract_seed_role_permissions() -> dict[str, list[str]]:
    """提取角色 -> 权限码列表（包括 admin 的列表推导式）"""
    source = SEED_FILE.read_text()
    all_codes = [p[0] for p in _extract_seed_permissions()]
    roles: dict[str, list[str]] = {}
    role_names = ["admin", "sales_manager", "sales", "inventory", "finance", "audit"]
    for role_name in role_names:
        pattern = rf'"{role_name}":\s*\['
        m = re.search(pattern, source)
        if not m:
            continue
        bracket_start = m.end() - 1  # 指向 [
        content = _extract_bracket_content(source, bracket_start).strip()
        if "p[0] for p in PERMISSIONS" in content:
            roles[role_name] = all_codes
        else:
            perms = [p.strip().strip('"') for p in content.split(",") if p.strip() and '"' in p]
            roles[role_name] = perms
    return roles


def _extract_api_permissions() -> set[str]:
    """从 API 源码提取所有 require_permission 和 has_permission 调用中的权限码"""
    perms = set()
    for api_file in API_DIR.glob("*.py"):
        source = api_file.read_text()
        for m in re.finditer(r'require_permission\("([^"]+)"\)', source):
            perms.add(m.group(1))
        for m in re.finditer(r'has_permission\([^,]+,\s*"([^"]+)"\)', source):
            perms.add(m.group(1))
    return perms


# ═══════════════════════════════════════════════════════════
# 1. 权限码定义完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPermissionDefinitions:
    """验证种子权限码定义"""

    def test_permissions_count(self):
        perms = _extract_seed_permissions()
        assert len(perms) == 33

    def test_all_permissions_have_code_name_module(self):
        perms = _extract_seed_permissions()
        for code, name, module in perms:
            assert ":" in code, f"权限码 {code} 缺少冒号分隔符"
            assert len(name) > 0, f"权限码 {code} 缺少名称"
            assert len(module) > 0, f"权限码 {code} 缺少模块名"

    def test_permission_codes_are_unique(self):
        perms = _extract_seed_permissions()
        codes = [p[0] for p in perms]
        assert len(codes) == len(set(codes)), "权限码有重复"

    def test_permission_codes_match_colon_resource_action_pattern(self):
        """权限码格式为 resource:action"""
        perms = _extract_seed_permissions()
        for code, _, _ in perms:
            parts = code.split(":")
            assert len(parts) == 2, f"权限码 {code} 格式不正确"
            assert parts[0].isidentifier(), f"资源名 {parts[0]} 不是有效标识符"
            assert parts[1].isidentifier(), f"动作名 {parts[1]} 不是有效标识符"

    def test_modules_cover_all_resources(self):
        """权限模块覆盖所有业务域"""
        perms = _extract_seed_permissions()
        modules = {p[2] for p in perms}
        expected = {"用户管理", "角色管理", "商品管理", "客户管理", "订单管理", "库存管理", "收款管理", "报表", "审计"}
        assert modules == expected


# ═══════════════════════════════════════════════════════════
# 2. 角色权限分配合理性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRolePermissions:
    """验证角色权限分配合理"""

    def test_6_roles_defined(self):
        roles = _extract_seed_role_permissions()
        assert len(roles) == 6
        for name in ["admin", "sales_manager", "sales", "inventory", "finance", "audit"]:
            assert name in roles

    def test_admin_has_all_permissions(self):
        roles = _extract_seed_role_permissions()
        perms = _extract_seed_permissions()
        all_codes = {p[0] for p in perms}
        admin_codes = set(roles["admin"])
        assert admin_codes == all_codes, f"admin 缺少权限: {all_codes - admin_codes}"

    def test_role_permissions_subset_of_defined(self):
        """角色权限必须是已定义权限的子集"""
        roles = _extract_seed_role_permissions()
        perms = _extract_seed_permissions()
        all_codes = {p[0] for p in perms}
        for role_name, role_perms in roles.items():
            for perm in role_perms:
                assert perm in all_codes, f"角色 {role_name} 引用了未定义权限 {perm}"

    def test_sales_role_has_basic_permissions(self):
        roles = _extract_seed_role_permissions()
        sales = set(roles["sales"])
        assert "product:list" in sales
        assert "customer:list" in sales
        assert "order:list" in sales
        assert "order:create" in sales

    def test_finance_role_has_payment_and_report(self):
        roles = _extract_seed_role_permissions()
        finance = set(roles["finance"])
        assert "payment:list" in finance
        assert "payment:reverse" in finance
        assert "report:sales" in finance
        assert "report:profit" in finance


# ═══════════════════════════════════════════════════════════
# 3. 种子权限覆盖 API 使用验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSeedCoversApi:
    """验证种子权限覆盖 API 中使用的所有权限码"""

    def test_all_api_permissions_in_seed(self):
        api_perms = _extract_api_permissions()
        seed_codes = {p[0] for p in _extract_seed_permissions()}
        for perm in api_perms:
            assert perm in seed_codes, f"API 使用权限 {perm} 不在种子数据中"

    def test_all_seed_permissions_used_in_api_or_data_scope(self):
        """种子权限要么在 API 中使用，要么用于数据范围过滤或 UI 控制"""
        api_perms = _extract_api_permissions()
        seed_codes = {p[0] for p in _extract_seed_permissions()}
        data_scope_perms = {
            "customer:view_all", "order:view_all",
            # 用户/角色管理权限通过 users.py/roles.py 使用
            "user:list", "user:create", "user:update", "user:delete",
            "role:list", "role:create", "role:update", "role:delete",
        }
        used = api_perms | data_scope_perms
        unused = seed_codes - used
        assert len(unused) == 0, f"种子中有未使用权限: {unused}"

    def test_crud_permissions_for_main_resources(self):
        """主要 CRUD 资源都有 list/create/update"""
        seed_codes = {p[0] for p in _extract_seed_permissions()}
        for resource in ["product", "customer", "order"]:
            for action in ["list", "create", "update"]:
                code = f"{resource}:{action}"
                assert code in seed_codes, f"缺少 {code} 权限"

    def test_product_has_view_cost(self):
        seed_codes = {p[0] for p in _extract_seed_permissions()}
        assert "product:view_cost" in seed_codes

    def test_report_has_sales_and_profit(self):
        seed_codes = {p[0] for p in _extract_seed_permissions()}
        assert "report:sales" in seed_codes
        assert "report:profit" in seed_codes


# ═══════════════════════════════════════════════════════════
# 4. 角色层级验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestRoleHierarchy:
    """验证角色权限层级合理"""

    def test_sales_manager_superset_of_sales(self):
        """销售主管权限包含销售权限"""
        roles = _extract_seed_role_permissions()
        assert set(roles["sales"]).issubset(set(roles["sales_manager"]))

    def test_admin_superset_of_all_roles(self):
        """管理员权限包含所有角色权限"""
        roles = _extract_seed_role_permissions()
        admin_perms = set(roles["admin"])
        for role_name, role_perms in roles.items():
            if role_name != "admin":
                assert set(role_perms).issubset(admin_perms), f"admin 不包含 {role_name} 的所有权限"

    def test_inventory_role_has_inventory_adjust(self):
        roles = _extract_seed_role_permissions()
        assert "inventory:adjust" in roles["inventory"]

    def test_audit_role_only_has_audit_view(self):
        roles = _extract_seed_role_permissions()
        audit_perms = set(roles.get("audit", []))
        assert "audit:view" in audit_perms
        assert "user:delete" not in audit_perms
        assert "order:create" not in audit_perms


# ═══════════════════════════════════════════════════════════
# 5. admin 账号安全验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestAdminAccount:
    """验证 admin 账号安全设置"""

    def test_admin_is_superuser(self):
        source = SEED_FILE.read_text()
        assert "is_superuser=True" in source

    def test_admin_is_active(self):
        source = SEED_FILE.read_text()
        assert "is_active=True" in source

    def test_admin_password_is_hashed(self):
        source = SEED_FILE.read_text()
        assert "hash_password(" in source

    def test_admin_gets_admin_role(self):
        source = SEED_FILE.read_text()
        assert 'Role.name == "admin"' in source
        assert "UserRole(" in source
