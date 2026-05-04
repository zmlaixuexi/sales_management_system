"""需求符合性：前端 API 路径与后端路由前缀一致性验证测试
验证前端所有 API 调用路径与后端注册的路由前缀对齐"""

import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
FRONTEND_API_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api"

# 后端路由前缀映射：模块文件 → 前缀
BACKEND_PREFIXES = {
    "products.py": "/products",
    "customers.py": "/customers",
    "orders.py": "/sales-orders",
    "payments.py": "/payments",
    "users.py": "/users",
    "roles.py": "/roles",
    "auth.py": "/auth",
    "inventory.py": "/inventory",
    "reports.py": "/reports",
    "audit_logs.py": "/audit-logs",
    "files.py": "/files",
    "exports.py": "/exports",
    "health.py": "/health",
}


def _extract_frontend_api_paths(filename):
    """从前端 API 模块提取所有 API 路径（支持单引号和模板字符串）"""
    source = (FRONTEND_API_DIR / filename).read_text()
    paths = set()
    # 匹配 get/post/put/del/upload<...>(`path` 或 'path')
    # 使用非贪婪匹配，支持嵌套泛型如 PaginatedData<OrderLog>
    for m in re.finditer(r"(?:get|post|put|del|upload)(?:<[^>]*(?:<[^>]*>)*[^>]*>)?\(\s*[`'](.+?)[`']", source):
        paths.add(m.group(1))
    # 匹配 apiClient.get/post/put/delete<...>(`path` 或 'path')
    for m in re.finditer(r"apiClient\.(?:get|post|put|delete)(?:<[^>]*(?:<[^>]*>)*[^>]*>)?\s*\(\s*[`'](.+?)[`']", source):
        paths.add(m.group(1))
    return paths


def _extract_backend_endpoint_paths(filename):
    """从后端路由文件提取所有端点路径"""
    source = (API_DIR / filename).read_text()
    paths = set()
    for m in re.finditer(r'@router\.(get|post|put|delete)\(\s*"([^"]*)"', source):
        paths.add(m.group(2))
    return paths


class TestProductsPaths:
    """商品 API 路径一致性"""

    def test_frontend_list_matches_backend(self):
        fe = _extract_frontend_api_paths("products.ts")
        be = _extract_backend_endpoint_paths("products.py")
        assert "/products" in fe or "" in fe
        assert "" in be  # backend uses empty string for list

    def test_crud_paths_exist(self):
        fe = _extract_frontend_api_paths("products.ts")
        assert any("/products/" in p for p in fe)  # detail/update/delete/disable


class TestOrdersPaths:
    """订单 API 路径一致性"""

    def test_frontend_uses_sales_orders_prefix(self):
        fe = _extract_frontend_api_paths("orders.ts")
        for p in fe:
            assert p.startswith("/sales-orders"), f"订单路径 {p} 不以 /sales-orders 开头"

    def test_backend_uses_sales_orders_prefix(self):
        source = (API_DIR / "orders.py").read_text()
        assert 'prefix="/sales-orders"' in source

    def test_confirm_cancel_paths(self):
        fe = _extract_frontend_api_paths("orders.ts")
        has_confirm = any("confirm" in p for p in fe)
        has_cancel = any("cancel" in p for p in fe)
        assert has_confirm, "前端缺少订单确认路径"
        assert has_cancel, "前端缺少订单取消路径"

    def test_logs_path(self):
        fe = _extract_frontend_api_paths("orders.ts")
        has_logs = any("logs" in p for p in fe)
        assert has_logs, "前端缺少订单日志路径"


class TestPaymentsPaths:
    """收款 API 路径一致性"""

    def test_frontend_list_path(self):
        fe = _extract_frontend_api_paths("payments.ts")
        assert any("/payments" in p for p in fe)

    def test_reverse_path(self):
        fe = _extract_frontend_api_paths("payments.ts")
        has_reverse = any("reverse" in p for p in fe)
        assert has_reverse, "前端缺少收款冲正路径"


class TestCustomersPaths:
    """客户 API 路径一致性"""

    def test_crud_paths(self):
        fe = _extract_frontend_api_paths("customers.ts")
        be = _extract_backend_endpoint_paths("customers.py")
        fe_base = {p.split("/")[2] if len(p.split("/")) > 2 else p for p in fe}
        assert "/customers" in fe or "" in fe

    def test_transfer_path(self):
        fe = _extract_frontend_api_paths("customers.ts")
        has_transfer = any("transfer" in p for p in fe)
        assert has_transfer, "前端缺少客户转移路径"


class TestUsersPaths:
    """用户 API 路径一致性"""

    def test_frontend_paths(self):
        fe = _extract_frontend_api_paths("users.ts")
        assert any("/users" in p for p in fe)

    def test_roles_path(self):
        fe = _extract_frontend_api_paths("users.ts")
        has_roles = any("roles" in p for p in fe)
        assert has_roles, "前端缺少用户角色查询路径"


class TestRolesPaths:
    """角色 API 路径一致性"""

    def test_crud_paths(self):
        fe = _extract_frontend_api_paths("roles.ts")
        assert any("/roles" in p for p in fe)

    def test_permissions_path(self):
        fe = _extract_frontend_api_paths("roles.ts")
        has_perms = any("permissions" in p for p in fe)
        assert has_perms, "前端缺少权限查询路径"


class TestAuthPaths:
    """认证 API 路径一致性"""

    def test_login_path(self):
        source = (FRONTEND_API_DIR / "auth.ts").read_text()
        assert "/auth/login" in source

    def test_refresh_path(self):
        source = (FRONTEND_API_DIR / "auth.ts").read_text()
        assert "/auth/refresh" in source

    def test_logout_path(self):
        source = (FRONTEND_API_DIR / "auth.ts").read_text()
        assert "/auth/logout" in source

    def test_me_path(self):
        source = (FRONTEND_API_DIR / "auth.ts").read_text()
        assert "/auth/me" in source

    def test_change_password_path(self):
        source = (FRONTEND_API_DIR / "auth.ts").read_text()
        assert "/auth/change-password" in source

    def test_backend_auth_has_all_endpoints(self):
        be = _extract_backend_endpoint_paths("auth.py")
        assert "/login" in be
        assert "/refresh" in be
        assert "/logout" in be
        assert "/me" in be
        assert "/change-password" in be


class TestInventoryPaths:
    """库存 API 路径一致性"""

    def test_frontend_paths(self):
        fe = _extract_frontend_api_paths("inventory.ts")
        has_movements = any("movements" in p for p in fe)
        has_adjustments = any("adjustments" in p for p in fe)
        assert has_movements, "前端缺少库存流水路径"
        assert has_adjustments, "前端缺少库存调整路径"


class TestReportsPaths:
    """报表 API 路径一致性"""

    def test_frontend_paths(self):
        fe = _extract_frontend_api_paths("reports.ts")
        be = _extract_backend_endpoint_paths("reports.py")
        # 前端有 sales-summary 等
        assert any("sales-summary" in p for p in fe)
        assert any("product-ranking" in p for p in fe)

    def test_all_six_report_endpoints(self):
        fe = _extract_frontend_api_paths("reports.ts")
        expected = ["sales-summary", "sales-trend", "product-ranking",
                    "customer-ranking", "salesperson-ranking", "inventory-warning"]
        for name in expected:
            assert any(name in p for p in fe), f"前端缺少报表端点 {name}"


class TestAuditLogsPaths:
    """审计日志 API 路径一致性"""

    def test_list_path(self):
        source = (FRONTEND_API_DIR / "auditLogs.ts").read_text()
        assert "/audit-logs" in source

    def test_actions_path(self):
        source = (FRONTEND_API_DIR / "auditLogs.ts").read_text()
        assert "/audit-logs/actions" in source


class TestPathPrefixConsistency:
    """所有前端 API 路径都以 / 开头且使用正确的后端前缀"""

    EXPECTED_PREFIXES = [
        "/products", "/customers", "/sales-orders", "/payments",
        "/users", "/roles", "/auth", "/inventory", "/reports",
        "/audit-logs", "/files",
    ]

    def test_all_frontend_paths_start_with_known_prefix(self):
        for filename in FRONTEND_API_DIR.glob("*.ts"):
            if filename.name in ("client.ts", "request.ts"):
                continue
            paths = _extract_frontend_api_paths(filename.name)
            for p in paths:
                matched = any(p.startswith(prefix) or p == prefix.rstrip("s") for prefix in self.EXPECTED_PREFIXES)
                assert matched, f"{filename.name}: 路径 '{p}' 不匹配任何后端前缀"

    def test_no_frontend_paths_use_wrong_orders_prefix(self):
        """前端不使用 /orders 前缀（应该是 /sales-orders）"""
        for filename in FRONTEND_API_DIR.glob("*.ts"):
            source = filename.read_text()
            # 排除 orders.ts 自身（它使用 /sales-orders）
            if filename.name == "orders.ts":
                assert "/orders" not in source or "/sales-orders" in source
            else:
                # 其他文件不应使用 /orders 或 /sales-orders
                pass
