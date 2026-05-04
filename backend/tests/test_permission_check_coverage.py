"""
代码质量：后端权限检查函数实现与 API 端点覆盖验证测试
覆盖权限辅助函数定义、权限码使用对齐、
模块级权限覆盖、数据范围权限模式、超级管理员专用模块
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
SEED_SRC = (ROOT / "app" / "db" / "seed.py").read_text()
MODEL_SRC = (ROOT / "app" / "models" / "user.py").read_text()

API_DIR = ROOT / "app" / "api" / "v1"
MODULES = ["products", "customers", "orders", "payments", "users", "roles",
           "files", "inventory", "reports", "exports", "audit_logs"]

SOURCES = {}
for name in MODULES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()

# 提取种子数据中所有权限码
SEED_CODES = re.findall(r'\("([a-z_]+:[a-z_]+)"', SEED_SRC)

# 提取所有 require_permission 调用中的权限码
REQUIRE_CODES = set()
for name, src in SOURCES.items():
    for m in re.finditer(r'require_permission\("([a-z_]+:[a-z_]+)"\)', src):
        REQUIRE_CODES.add(m.group(1))

# 提取所有 has_permission 调用中的权限码
HAS_CODES = set()
for name, src in SOURCES.items():
    for m in re.finditer(r'has_permission\(\w+,\s*"([a-z_]+:[a-z_]+)"\)', src):
        HAS_CODES.add(m.group(1))


# ═══════════════════════════════════════════════════════════
# 1. 权限辅助函数定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPermissionHelperDefinitions:
    """权限辅助函数在 deps.py 中正确定义"""

    def test_require_permission_function_defined(self):
        """require_permission 函数已定义，接收权限码参数"""
        assert re.search(r'def\s+require_permission\(\s*permission_code\s*:\s*str\s*\)', DEPS_SRC), (
            "deps.py 应定义 require_permission(permission_code: str)"
        )

    def test_require_permission_returns_closure(self):
        """require_permission 返回闭包函数作为 Depends"""
        assert "def _check(current_user: User = Depends(get_current_user))" in DEPS_SRC, (
            "require_permission 应返回使用 Depends(get_current_user) 的闭包"
        )

    def test_has_permission_function_defined(self):
        """has_permission 函数已定义，不抛异常"""
        assert re.search(r'def\s+has_permission\(\s*user\s*:\s*User\s*,\s*permission_code\s*:\s*str\s*\)\s*->\s*bool', DEPS_SRC), (
            "deps.py 应定义 has_permission(user, permission_code) -> bool"
        )

    def test_check_owner_or_forbid_defined(self):
        """check_owner_or_forbid 函数已定义"""
        assert re.search(r'def\s+check_owner_or_forbid\(', DEPS_SRC), (
            "deps.py 应定义 check_owner_or_forbid"
        )
        assert "view_all_code" in DEPS_SRC, "check_owner_or_forbid 应接收 view_all_code 参数"
        assert "label" in DEPS_SRC, "check_owner_or_forbid 应接收 label 参数"

    def test_get_user_permissions_private_helper(self):
        """_get_user_permissions 私有辅助函数已定义"""
        assert re.search(r'def\s+_get_user_permissions\(\s*user\s*:\s*User\s*\)\s*->\s*set\[str\]', DEPS_SRC), (
            "deps.py 应定义 _get_user_permissions(user) -> set[str]"
        )


# ═══════════════════════════════════════════════════════════
# 2. 权限码使用与种子数据对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPermissionCodeAlignment:
    """API 使用的权限码与种子数据定义对齐"""

    def test_all_require_codes_exist_in_seed(self):
        """所有 require_permission 使用的权限码都在种子数据中定义"""
        for code in REQUIRE_CODES:
            assert code in SEED_CODES, (
                f"权限码 {code} 在 API 中使用但未在种子数据 PERMISSIONS 中定义"
            )

    def test_all_has_codes_exist_in_seed(self):
        """所有 has_permission 使用的权限码都在种子数据中定义"""
        for code in HAS_CODES:
            assert code in SEED_CODES, (
                f"权限码 {code} 在 has_permission 中使用但未在种子数据中定义"
            )

    def test_seed_permissions_count(self):
        """种子数据定义了足够的权限码"""
        assert len(SEED_CODES) >= 25, (
            f"种子数据应定义 >= 25 个权限码，实际 {len(SEED_CODES)}"
        )

    def test_permission_codes_follow_module_action_pattern(self):
        """所有权限码遵循 module:action 命名规范"""
        all_codes = SEED_CODES
        for code in all_codes:
            parts = code.split(":")
            assert len(parts) == 2, f"权限码 {code} 应为 module:action 格式"
            module, action = parts
            assert re.match(r'^[a-z_]+$', module), f"权限码模块名 {module} 应使用小写"
            assert re.match(r'^[a-z_]+$', action), f"权限码动作名 {action} 应使用小写"

    def test_crud_modules_have_standard_actions(self):
        """核心 CRUD 模块有 list/create/update/delete 标准动作"""
        for module in ["product", "customer", "user", "role"]:
            for action in ["list", "create", "update", "delete"]:
                code = f"{module}:{action}"
                assert code in SEED_CODES, f"核心模块应有权限码 {code}"


# ═══════════════════════════════════════════════════════════
# 3. 模块级权限覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModulePermissionCoverage:
    """各业务模块正确使用 require_permission"""

    def test_products_module_uses_product_permissions(self):
        """商品模块使用 product: 权限码"""
        src = SOURCES["products"]
        for code in ["product:list", "product:create", "product:update", "product:delete"]:
            assert f'require_permission("{code}")' in src, (
                f"products 模块应使用 {code} 权限"
            )

    def test_customers_module_uses_customer_permissions(self):
        """客户模块使用 customer: 权限码"""
        src = SOURCES["customers"]
        for code in ["customer:list", "customer:create", "customer:update", "customer:delete"]:
            assert f'require_permission("{code}")' in src, (
                f"customers 模块应使用 {code} 权限"
            )

    def test_orders_module_uses_order_permissions(self):
        """订单模块使用 order: 权限码"""
        src = SOURCES["orders"]
        for code in ["order:list", "order:create", "order:update", "order:confirm", "order:cancel"]:
            assert f'require_permission("{code}")' in src, (
                f"orders 模块应使用 {code} 权限"
            )

    def test_payments_inventory_audit_use_correct_permissions(self):
        """收款/库存/审计模块使用各自权限码"""
        assert 'require_permission("payment:list")' in SOURCES["payments"]
        assert 'require_permission("payment:create")' in SOURCES["payments"]
        assert 'require_permission("inventory:list")' in SOURCES["inventory"]
        assert 'require_permission("inventory:adjust")' in SOURCES["inventory"]
        assert 'require_permission("audit:view")' in SOURCES["audit_logs"]

    def test_exports_module_uses_list_permissions(self):
        """导出模块使用各资源的 list 权限"""
        src = SOURCES["exports"]
        for code in ["product:list", "customer:list", "order:list", "payment:list"]:
            assert f'require_permission("{code}")' in src, (
                f"exports 模块应使用 {code} 权限"
            )


# ═══════════════════════════════════════════════════════════
# 4. 数据范围权限模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDataScopePermissionPatterns:
    """has_permission 和 check_owner_or_forbid 使用正确"""

    def test_view_cost_permission_used_for_cost_fields(self):
        """product:view_cost 用于控制成本价可见性"""
        products_src = SOURCES["products"]
        assert 'has_permission(current_user, "product:view_cost")' in products_src, (
            "products 模块应使用 product:view_cost 控制成本价可见"
        )

    def test_view_all_permissions_used_for_data_scoping(self):
        """view_all 权限用于数据范围过滤"""
        orders_src = SOURCES["orders"]
        customers_src = SOURCES["customers"]
        assert 'has_permission(current_user, "order:view_all")' in orders_src, (
            "orders 模块应使用 order:view_all 过滤数据"
        )
        assert 'has_permission(current_user, "customer:view_all")' in customers_src, (
            "customers 模块应使用 customer:view_all 过滤数据"
        )

    def test_check_owner_or_forbid_used_in_detail_endpoints(self):
        """check_owner_or_forbid 用于对象级权限检查"""
        customers_src = SOURCES["customers"]
        orders_src = SOURCES["orders"]
        assert 'check_owner_or_forbid(current_user, customer.owner_user_id' in customers_src, (
            "customers 详情端点应使用 check_owner_or_forbid"
        )
        assert 'check_owner_or_forbid(current_user, order.sales_user_id' in orders_src, (
            "orders 详情端点应使用 check_owner_or_forbid"
        )

    def test_reports_profit_permission_gates_profit_data(self):
        """report:profit 权限控制利润数据可见性"""
        reports_src = SOURCES["reports"]
        assert 'has_permission(current_user, "report:profit")' in reports_src, (
            "reports 模块应使用 report:profit 控制利润数据可见"
        )

    def test_payment_list_scopes_by_order_view_all(self):
        """收款列表使用 order:view_all 进行数据过滤"""
        payments_src = SOURCES["payments"]
        assert 'has_permission(current_user, "order:view_all")' in payments_src, (
            "payments 模块应使用 order:view_all 过滤数据"
        )


# ═══════════════════════════════════════════════════════════
# 5. 超级管理员专用模块与角色定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSuperuserModulesAndRoles:
    """用户/角色管理模块使用超级管理员检查"""

    def test_users_module_uses_is_superuser_check(self):
        """用户管理模块使用 is_superuser 检查"""
        users_src = SOURCES["users"]
        assert "is_superuser" in users_src, "users 模块应使用 is_superuser 检查"
        assert "require_permission" not in users_src, (
            "users 模块不应使用 require_permission（使用 is_superuser 直接检查）"
        )

    def test_roles_module_uses_is_superuser_check(self):
        """角色管理模块使用 is_superuser 检查"""
        roles_src = SOURCES["roles"]
        assert "is_superuser" in roles_src, "roles 模块应使用 is_superuser 检查"
        assert "require_permission" not in roles_src, (
            "roles 模块不应使用 require_permission（使用 is_superuser 直接检查）"
        )

    def test_admin_role_has_all_permissions(self):
        """admin 角色拥有所有权限（通过列表推导引用 PERMISSIONS）"""
        assert '"admin": [p[0] for p in PERMISSIONS]' in SEED_SRC, (
            "admin 角色应通过 [p[0] for p in PERMISSIONS] 拥有所有权限"
        )

    def test_seed_roles_cover_all_permission_modules(self):
        """种子角色的权限覆盖所有模块"""
        # 提取非 admin 角色的字面权限码
        role_sections = re.findall(r'"(\w+)":\s*\[(.*?)\]', SEED_SRC, re.DOTALL)
        modules = set()
        for code in SEED_CODES:
            modules.add(code.split(":")[0])
        # admin 角色使用 PERMISSIONS 推导，自动覆盖所有模块
        # 只检查非 admin 角色的业务模块覆盖
        business_modules = modules - {"user", "role"}
        for module in business_modules:
            found = False
            for role_name, perm_codes_str in role_sections:
                if role_name == "admin":
                    continue
                codes = re.findall(r'"([a-z_]+:[a-z_]+)"', perm_codes_str)
                if any(c.startswith(f"{module}:") for c in codes):
                    found = True
                    break
            assert found, f"模块 {module} 应至少被一个种子角色覆盖"

    def test_seed_data_is_idempotent(self):
        """种子数据函数是幂等的（检查已存在记录）"""
        assert "if not existing" in SEED_SRC or "if existing" in SEED_SRC, (
            "种子数据应检查已存在记录以保证幂等性"
        )
        assert "_seed_permissions" in SEED_SRC, "应定义 _seed_permissions 函数"
        assert "_seed_roles" in SEED_SRC, "应定义 _seed_roles 函数"
        assert "_seed_admin_user" in SEED_SRC, "应定义 _seed_admin_user 函数"
