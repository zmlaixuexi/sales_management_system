"""需求符合性：后端 API 端点 HTTP 方法与路由模式验证测试
覆盖 CRUD 方法规范、动作端点方法、公开端点认证排除、导出端点方法、路由路径命名"""

import re
from pathlib import Path
from typing import ClassVar

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
ROUTER_FILE = API_DIR / "router.py"
MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"


def _get_routes(source: str) -> list[tuple[str, str, str]]:
    """提取路由: [(http_method, path, function_name)]"""
    results = []
    for m in re.finditer(
        r"@router\.(get|post|put|delete|patch)\(['\"]([^'\"]*)['\"]",
        source,
    ):
        method = m.group(1)
        path = m.group(2)
        rest = source[m.end():]
        fn = re.search(r"def\s+(\w+)\s*\(", rest)
        if fn:
            results.append((method, path, fn.group(1)))
    return results


# ═══════════════════════════════════════════════════════════
# 1. CRUD 方法规范验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestCrudMethodConventions:
    """验证 CRUD 端点使用正确的 HTTP 方法"""

    def test_products_list_is_get(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        list_route = next((r for r in routes if r[2] == "list_products"), None)
        assert list_route and list_route[0] == "get"

    def test_products_create_is_post(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        create = next((r for r in routes if r[2] == "create_product"), None)
        assert create and create[0] == "post"

    def test_products_update_is_put(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        update = next((r for r in routes if r[2] == "update_product"), None)
        assert update and update[0] == "put"

    def test_products_delete_is_delete(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        delete = next((r for r in routes if r[2] == "delete_product"), None)
        assert delete and delete[0] == "delete"

    def test_customers_list_is_get(self):
        source = (API_DIR / "customers.py").read_text()
        routes = _get_routes(source)
        list_route = next((r for r in routes if r[2] == "list_customers"), None)
        assert list_route and list_route[0] == "get"

    def test_orders_list_is_get(self):
        source = (API_DIR / "orders.py").read_text()
        routes = _get_routes(source)
        list_route = next((r for r in routes if r[2] == "list_orders"), None)
        assert list_route and list_route[0] == "get"

    def test_orders_create_is_post(self):
        source = (API_DIR / "orders.py").read_text()
        routes = _get_routes(source)
        create = next((r for r in routes if r[2] == "create_order"), None)
        assert create and create[0] == "post"

    def test_payments_list_is_get(self):
        source = (API_DIR / "payments.py").read_text()
        routes = _get_routes(source)
        list_route = next((r for r in routes if r[2] == "list_payments"), None)
        assert list_route and list_route[0] == "get"


# ═══════════════════════════════════════════════════════════
# 2. 动作端点方法验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestActionEndpointMethods:
    """验证动作类端点使用 POST 方法"""

    def test_order_confirm_is_post(self):
        source = (API_DIR / "orders.py").read_text()
        routes = _get_routes(source)
        confirm = next((r for r in routes if r[2] == "confirm_order"), None)
        assert confirm and confirm[0] == "post"

    def test_order_cancel_is_post(self):
        source = (API_DIR / "orders.py").read_text()
        routes = _get_routes(source)
        cancel = next((r for r in routes if r[2] == "cancel_order"), None)
        assert cancel and cancel[0] == "post"

    def test_product_disable_is_post(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        disable = next((r for r in routes if r[2] == "disable_product"), None)
        assert disable and disable[0] == "post"

    def test_customer_transfer_is_post(self):
        source = (API_DIR / "customers.py").read_text()
        routes = _get_routes(source)
        transfer = next((r for r in routes if r[2] == "transfer_customer"), None)
        assert transfer and transfer[0] == "post"

    def test_payment_reverse_is_post(self):
        source = (API_DIR / "payments.py").read_text()
        routes = _get_routes(source)
        reverse = next((r for r in routes if r[2] == "reverse_payment"), None)
        assert reverse and reverse[0] == "post"

    def test_inventory_adjust_is_post(self):
        source = (API_DIR / "inventory.py").read_text()
        routes = _get_routes(source)
        adjust = next((r for r in routes if r[2] == "adjust_inventory"), None)
        assert adjust and adjust[0] == "post"


# ═══════════════════════════════════════════════════════════
# 3. 公开端点认证排除验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPublicEndpointAuth:
    """验证公开端点不需要认证"""

    def test_health_no_auth(self):
        source = (API_DIR / "health.py").read_text()
        assert "Depends(" not in source or "get_current_user" not in source

    def test_login_no_auth(self):
        source = (API_DIR / "auth.py").read_text()
        routes = _get_routes(source)
        login = next((r for r in routes if r[2] == "login"), None)
        assert login
        # login 函数不应使用 require_permission 或 get_current_user 作为 Depends
        fn_body_start = source.index("def login(")
        fn_body_end = (
            source.index("\n@router", fn_body_start + 1)
            if "\n@router" in source[fn_body_start + 1:]
            else len(source)
        )
        fn_body = source[fn_body_start:fn_body_end]
        assert "require_permission" not in fn_body
        assert "get_current_user" not in fn_body

    def test_refresh_no_auth(self):
        source = (API_DIR / "auth.py").read_text()
        fn_body_start = source.index("def refresh_token(")
        fn_body_end = (
            source.index("\n@router", fn_body_start + 1)
            if "\n@router" in source[fn_body_start + 1:]
            else len(source)
        )
        fn_body = source[fn_body_start:fn_body_end]
        assert "require_permission" not in fn_body

    def test_auth_endpoints_count(self):
        """auth 模块有 5 个端点"""
        source = (API_DIR / "auth.py").read_text()
        routes = _get_routes(source)
        assert len(routes) == 5

    def test_health_endpoints_count(self):
        """health 模块有 2 个端点"""
        source = (API_DIR / "health.py").read_text()
        routes = _get_routes(source)
        assert len(routes) == 2


# ═══════════════════════════════════════════════════════════
# 4. 导出端点方法验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestExportEndpointMethods:
    """验证导出端点使用 GET 方法"""

    def test_export_products_is_get(self):
        source = (API_DIR / "exports.py").read_text()
        routes = _get_routes(source)
        export = next((r for r in routes if r[2] == "export_products_csv"), None)
        assert export and export[0] == "get"

    def test_export_customers_is_get(self):
        source = (API_DIR / "exports.py").read_text()
        routes = _get_routes(source)
        export = next((r for r in routes if r[2] == "export_customers_csv"), None)
        assert export and export[0] == "get"

    def test_export_orders_is_get(self):
        source = (API_DIR / "exports.py").read_text()
        routes = _get_routes(source)
        export = next((r for r in routes if r[2] == "export_orders_csv"), None)
        assert export and export[0] == "get"

    def test_export_payments_is_get(self):
        source = (API_DIR / "exports.py").read_text()
        routes = _get_routes(source)
        export = next((r for r in routes if r[2] == "export_payments_csv"), None)
        assert export and export[0] == "get"


# ═══════════════════════════════════════════════════════════
# 5. 路由路径命名验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestRoutePathNaming:
    """验证路由路径使用 kebab-case 和正确的模式"""

    def test_products_routes_use_product_id(self):
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        detail_routes = [r for r in routes if "product_id" in r[1]]
        assert len(detail_routes) >= 3  # get, update, delete

    def test_customers_routes_use_customer_id(self):
        source = (API_DIR / "customers.py").read_text()
        routes = _get_routes(source)
        detail_routes = [r for r in routes if "customer_id" in r[1]]
        assert len(detail_routes) >= 3

    def test_orders_routes_use_order_id(self):
        source = (API_DIR / "orders.py").read_text()
        routes = _get_routes(source)
        detail_routes = [r for r in routes if "order_id" in r[1]]
        assert len(detail_routes) >= 3

    def test_import_routes_are_sub_resources(self):
        """导入端点路径为 /import"""
        source = (API_DIR / "products.py").read_text()
        routes = _get_routes(source)
        import_route = next((r for r in routes if r[2] == "import_products_csv"), None)
        assert import_route and "/import" in import_route[1]

    def test_no_trailing_slashes(self):
        """路由路径不以 / 结尾"""
        for mod_file in API_DIR.glob("*.py"):
            if mod_file.name in ("__init__.py", "router.py"):
                continue
            source = mod_file.read_text()
            routes = _get_routes(source)
            for _method, path, fn in routes:
                assert not path.endswith("/"), f"{mod_file.name}:{fn} 路径 '{path}' 以 / 结尾"

    def test_detail_routes_use_uuid_pattern(self):
        """详情路由使用 {resource_id} 格式"""
        for mod_file in API_DIR.glob("*.py"):
            if mod_file.name in ("__init__.py", "router.py"):
                continue
            source = mod_file.read_text()
            routes = _get_routes(source)
            for _method, path, fn in routes:
                if "{" in path:
                    param = path.split("{")[1].split("}")[0]
                    assert re.match(r"\w+_id$", param), (
                        f"{mod_file.name}:{fn} 路径参数格式不正确: {param}"
                    )


# ═══════════════════════════════════════════════════════════
# 6. 路由注册完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRouterRegistration:
    """验证所有路由模块在 router.py 中注册"""

    EXPECTED_MODULES: ClassVar = [
        "health", "auth", "users", "roles", "files",
        "products", "customers", "orders", "payments",
        "inventory", "reports", "audit_logs", "exports",
    ]

    def test_all_modules_registered(self):
        source = ROUTER_FILE.read_text()
        for mod in self.EXPECTED_MODULES:
            assert mod in source, f"模块 {mod} 未在 router.py 中注册"

    def test_router_includes_all_modules(self):
        source = ROUTER_FILE.read_text()
        assert "include_router" in source
        count = source.count("include_router")
        assert count >= len(self.EXPECTED_MODULES)

    def test_api_prefix_in_main(self):
        source = MAIN_FILE.read_text()
        assert "/api/v1" in source

    def test_total_endpoint_count(self):
        """总端点数约 59 个"""
        total = 0
        for mod_file in API_DIR.glob("*.py"):
            if mod_file.name in ("__init__.py", "router.py"):
                continue
            source = mod_file.read_text()
            total += len(_get_routes(source))
        assert total >= 55

    def test_no_patch_methods(self):
        """项目不使用 PATCH 方法（全部用 PUT）"""
        for mod_file in API_DIR.glob("*.py"):
            if mod_file.name in ("__init__.py", "router.py"):
                continue
            source = mod_file.read_text()
            assert "@router.patch" not in source, f"{mod_file.name} 使用了 PATCH 方法"
