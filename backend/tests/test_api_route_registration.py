"""代码质量：后端 API 路由注册与鉴权覆盖静态验证测试
验证路由模块注册完整性、前缀一致性、tag 对齐、端点总数"""

import ast
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
ROUTER_FILE = API_DIR / "router.py"
MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"


def _get_router_source(filename):
    return (API_DIR / filename).read_text()


def _parse(filename):
    return ast.parse(_get_router_source(filename))


class TestRouterRegistration:
    """所有路由模块在 router.py 中注册"""

    ROUTE_MODULES = [
        "health.py", "auth.py", "users.py", "roles.py", "files.py",
        "products.py", "customers.py", "orders.py", "payments.py",
        "inventory.py", "reports.py", "audit_logs.py", "exports.py",
    ]

    def test_all_13_modules_registered(self):
        source = ROUTER_FILE.read_text()
        for mod in self.ROUTE_MODULES:
            # health -> health_router, auth -> auth_router
            name = mod.replace(".py", "").replace("_", "_")
            assert f"from app.api.v1.{name} import router" in source, \
                f"router.py 未导入 {mod}"

    def test_all_imports_have_include_router(self):
        source = ROUTER_FILE.read_text()
        for mod in self.ROUTE_MODULES:
            name = mod.replace(".py", "")
            assert f"include_router({name}_router)" in source, \
                f"router.py 未 include_router {name}_router"

    def test_router_module_count_matches(self):
        source = ROUTER_FILE.read_text()
        count = source.count("include_router(")
        assert count == 13, f"注册路由模块数 {count} ≠ 13"


class TestModulePrefixes:
    """各模块路由前缀正确"""

    PREFIX_MAP = {
        "health.py": None,
        "auth.py": "/auth",
        "users.py": "/users",
        "roles.py": "/roles",
        "files.py": "/files",
        "products.py": "/products",
        "customers.py": "/customers",
        "orders.py": "/sales-orders",
        "payments.py": "/payments",
        "inventory.py": "/inventory",
        "reports.py": "/reports",
        "audit_logs.py": "/audit-logs",
        "exports.py": "/exports",
    }

    def test_all_prefixes_correct(self):
        for filename, expected in self.PREFIX_MAP.items():
            source = _get_router_source(filename)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == "APIRouter":
                        prefix_kw = next(
                            (kw for kw in node.keywords if kw.arg == "prefix"), None
                        )
                        if expected is None:
                            assert prefix_kw is None, \
                                f"{filename} 不应有 prefix 但有 {ast.dump(prefix_kw.value)}"
                        else:
                            assert prefix_kw is not None, f"{filename} 缺少 prefix"
                            assert isinstance(prefix_kw.value, ast.Constant), \
                                f"{filename} prefix 不是常量"
                            assert prefix_kw.value.value == expected, \
                                f"{filename} prefix={prefix_kw.value.value} ≠ {expected}"


class TestModuleTags:
    """各模块 tag 与 main.py OpenAPI_TAGS 对齐"""

    TAG_MAP = {
        "health.py": "健康检查",
        "auth.py": "认证",
        "users.py": "用户管理",
        "roles.py": "角色管理",
        "files.py": "文件管理",
        "products.py": "商品管理",
        "customers.py": "客户管理",
        "orders.py": "订单管理",
        "payments.py": "收款管理",
        "inventory.py": "库存管理",
        "reports.py": "报表",
        "audit_logs.py": "操作日志",
        "exports.py": "数据导出",
    }

    def test_all_tags_match_openapi_tags(self):
        for filename, expected_tag in self.TAG_MAP.items():
            source = _get_router_source(filename)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == "APIRouter":
                        tags_kw = next(
                            (kw for kw in node.keywords if kw.arg == "tags"), None
                        )
                        assert tags_kw is not None, f"{filename} 缺少 tags 参数"
                        assert isinstance(tags_kw.value, ast.List), \
                            f"{filename} tags 不是列表"
                        assert len(tags_kw.value.elts) > 0, f"{filename} tags 为空"
                        tag_val = tags_kw.value.elts[0]
                        assert isinstance(tag_val, ast.Constant), \
                            f"{filename} tag 不是常量"
                        assert tag_val.value == expected_tag, \
                            f"{filename} tag={tag_val.value} ≠ {expected_tag}"

    def test_all_module_tags_in_openapi_tags(self):
        """router tag 在 main.py OPENAPI_TAGS 中有定义"""
        main_src = MAIN_FILE.read_text()
        for tag in self.TAG_MAP.values():
            assert f'"{tag}"' in main_src, f"OpenAPI_TAGS 缺少 '{tag}'"


class TestEndpointMethods:
    """各模块端点 HTTP 方法统计"""

    def test_products_has_get_post_put_delete(self):
        tree = _parse("products.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods
        assert "delete" in methods

    def test_customers_has_get_post_put_delete(self):
        tree = _parse("customers.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods
        assert "delete" in methods

    def test_orders_has_get_post_put(self):
        tree = _parse("orders.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods

    def test_payments_has_get_post(self):
        tree = _parse("payments.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods

    def test_users_has_get_post_put(self):
        tree = _parse("users.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods

    def test_roles_has_get_post_put_delete(self):
        tree = _parse("roles.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods
        assert "delete" in methods

    def test_auth_has_get_post(self):
        tree = _parse("auth.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods

    def test_health_only_get(self):
        tree = _parse("health.py")
        methods = _extract_methods(tree)
        assert methods == {"get"}

    def test_reports_only_get(self):
        tree = _parse("reports.py")
        methods = _extract_methods(tree)
        assert methods == {"get"}

    def test_exports_only_get(self):
        tree = _parse("exports.py")
        methods = _extract_methods(tree)
        assert methods == {"get"}

    def test_inventory_has_get_post(self):
        tree = _parse("inventory.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods

    def test_files_has_get_post_delete(self):
        tree = _parse("files.py")
        methods = _extract_methods(tree)
        assert "get" in methods
        assert "post" in methods
        assert "delete" in methods


class TestEndpointPaths:
    """关键端点路径存在性验证"""

    def _get_paths(self, filename):
        tree = _parse(filename)
        paths = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("get", "post", "put", "delete", "patch"):
                    if node.args and isinstance(node.args[0], ast.Constant):
                        paths.append(node.args[0].value)
        return paths

    def test_health_has_health_and_version(self):
        paths = self._get_paths("health.py")
        assert "/health" in paths
        assert "/version" in paths

    def test_auth_has_login_refresh_logout_me(self):
        paths = self._get_paths("auth.py")
        assert "/login" in paths
        assert "/refresh" in paths
        assert "/logout" in paths
        assert "/me" in paths
        assert "/change-password" in paths

    def test_products_has_crud_paths(self):
        paths = self._get_paths("products.py")
        assert "" in paths
        assert "/{product_id}" in paths
        assert "/{product_id}/disable" in paths
        assert "/{product_id}/price-history" in paths
        assert "/import" in paths

    def test_customers_has_crud_paths(self):
        paths = self._get_paths("customers.py")
        assert "" in paths
        assert "/{customer_id}" in paths
        assert "/{customer_id}/transfer" in paths
        assert "/import" in paths

    def test_orders_has_crud_paths(self):
        paths = self._get_paths("orders.py")
        assert "" in paths
        assert "/{order_id}" in paths
        assert "/{order_id}/confirm" in paths
        assert "/{order_id}/cancel" in paths
        assert "/{order_id}/logs" in paths
        assert "/{order_id}/payments" in paths

    def test_payments_has_reverse_path(self):
        paths = self._get_paths("payments.py")
        assert "" in paths
        assert "/{payment_id}/reverse" in paths

    def test_users_has_roles_path(self):
        paths = self._get_paths("users.py")
        assert "" in paths
        assert "/{user_id}" in paths
        assert "/roles" in paths

    def test_roles_has_permissions_path(self):
        paths = self._get_paths("roles.py")
        assert "" in paths
        assert "/{role_id}" in paths
        assert "/permissions" in paths

    def test_files_has_images_paths(self):
        paths = self._get_paths("files.py")
        assert "/images" in paths
        assert "/images/{file_id}" in paths

    def test_inventory_has_movements_and_adjustments(self):
        paths = self._get_paths("inventory.py")
        assert "/movements" in paths
        assert "/adjustments" in paths

    def test_reports_has_all_ranking_paths(self):
        paths = self._get_paths("reports.py")
        assert "/sales-summary" in paths
        assert "/sales-trend" in paths
        assert "/product-ranking" in paths
        assert "/customer-ranking" in paths
        assert "/salesperson-ranking" in paths
        assert "/inventory-warning" in paths

    def test_exports_has_all_four(self):
        paths = self._get_paths("exports.py")
        assert "/products" in paths
        assert "/customers" in paths
        assert "/orders" in paths
        assert "/payments" in paths


class TestTotalEndpointCount:
    """端点总数统计"""

    def test_total_endpoints_at_least_55(self):
        """API 端点总数不少于 55"""
        count = 0
        for filename in API_DIR.glob("*.py"):
            if filename.name == "__init__.py" or filename.name == "router.py":
                continue
            tree = ast.parse(filename.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("get", "post", "put", "delete", "patch"):
                        count += 1
        assert count >= 55, f"端点总数 {count} 少于 55"

    def test_no_patch_endpoints(self):
        """系统不使用 PATCH 方法，保持 PUT 一致性"""
        for filename in API_DIR.glob("*.py"):
            source = filename.read_text()
            assert "@router.patch" not in source, f"{filename.name} 使用了 PATCH 方法"


class TestMainAppMount:
    """main.py 路由挂载验证"""

    def test_api_v1_prefix(self):
        source = MAIN_FILE.read_text()
        assert 'prefix="/api/v1"' in source

    def test_cors_middleware_configured(self):
        source = MAIN_FILE.read_text()
        assert "CORSMiddleware" in source

    def test_request_id_middleware_added(self):
        source = MAIN_FILE.read_text()
        assert "RequestIDMiddleware" in source

    def test_request_log_middleware_added(self):
        source = MAIN_FILE.read_text()
        assert "RequestLogMiddleware" in source

    def test_security_headers_middleware_added(self):
        source = MAIN_FILE.read_text()
        assert "SecurityHeadersMiddleware" in source

    def test_body_limit_middleware_added(self):
        source = MAIN_FILE.read_text()
        assert "BodyLimitMiddleware" in source

    def test_prometheus_instrumentator_configured(self):
        source = MAIN_FILE.read_text()
        assert "Instrumentator" in source

    def test_static_files_mounted(self):
        source = MAIN_FILE.read_text()
        assert "StaticFiles" in source
        assert "/uploads" in source


class TestRateLimitConfig:
    """速率限制配置验证"""

    def test_add_rate_limit_called(self):
        source = MAIN_FILE.read_text()
        assert "add_rate_limit" in source

    def test_rate_limit_registered_after_routes(self):
        """速率限制在路由注册之后调用"""
        source = MAIN_FILE.read_text()
        router_pos = source.index("include_router(api_router")
        rate_limit_pos = source.index("add_rate_limit(app)")
        assert rate_limit_pos > router_pos, "速率限制应在路由注册之后"


def _extract_methods(tree):
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("get", "post", "put", "delete", "patch"):
                methods.add(node.func.attr)
    return methods
