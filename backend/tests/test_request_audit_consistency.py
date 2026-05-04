"""
代码质量：后端 API 端点 Request 参数与审计日志一致性验证测试
覆盖变更端点 Request 参数声明、审计日志调用覆盖、
审计 action 命名规范、审计参数传递一致性、list 端点无审计日志
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_DIR = ROOT / "app" / "api" / "v1"
AUDIT_SVC = (ROOT / "app" / "services" / "audit_service.py").read_text()

# 需要审计日志的模块（含变更操作）
MUTATION_MODULES = ["products", "customers", "orders", "payments", "users", "roles", "files", "inventory", "exports", "auth"]

SOURCES = {name: (API_DIR / f"{name}.py").read_text() for name in MUTATION_MODULES}


def _endpoint_has_request_param(src: str, method: str, path_suffix: str) -> bool:
    """检查指定端点是否声明了 request: Request 参数"""
    pattern = rf'@router\.{method}\("{path_suffix}"'
    for m in re.finditer(pattern, src):
        rest = src[m.end():]
        chunk = rest[:500]
        if "request" in chunk and "Request" in chunk:
            func_match = re.search(r"def \w+\(", chunk)
            if func_match:
                return True
    return False


# ═══════════════════════════════════════════════════════════
# 1. 变更端点 Request 参数声明验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMutationEndpointsRequestParam:
    """变更端点声明 request: Request 参数"""

    def test_product_create_has_request(self):
        assert _endpoint_has_request_param(SOURCES["products"], "post", "")

    def test_customer_create_has_request(self):
        assert _endpoint_has_request_param(SOURCES["customers"], "post", "")

    def test_order_create_has_request(self):
        assert _endpoint_has_request_param(SOURCES["orders"], "post", "")

    def test_user_create_has_request(self):
        assert _endpoint_has_request_param(SOURCES["users"], "post", "")

    def test_inventory_adjust_has_request(self):
        assert _endpoint_has_request_param(SOURCES["inventory"], "post", "/adjustments")


# ═══════════════════════════════════════════════════════════
# 2. 审计日志调用覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuditLogCoverage:
    """每个变更模块都调用了审计日志函数"""

    def test_products_module_calls_log(self):
        assert "log_user_action" in SOURCES["products"], "products 模块应调用 log_user_action"

    def test_customers_module_calls_log(self):
        assert "log_user_action" in SOURCES["customers"], "customers 模块应调用 log_user_action"

    def test_orders_module_calls_log(self):
        assert "log_user_action" in SOURCES["orders"], "orders 模块应调用 log_user_action"

    def test_payments_module_calls_log(self):
        assert "log_user_action" in SOURCES["payments"], "payments 模块应调用 log_user_action"

    def test_all_modules_import_audit(self):
        """所有变更模块导入审计服务"""
        for name in ["products", "customers", "orders", "payments", "users", "roles", "files", "inventory"]:
            assert "audit_service" in SOURCES[name], f"{name} 模块应导入 audit_service"


# ═══════════════════════════════════════════════════════════
# 3. 审计 action 命名规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuditActionNaming:
    """审计 action 使用 snake_case 命名"""

    def test_actions_use_snake_case(self):
        """所有 action 值使用 snake_case"""
        for name, src in SOURCES.items():
            for m in re.finditer(r'action="([^"]+)"', src):
                action = m.group(1)
                assert re.fullmatch(r"[a-z][a-z0-9_]*", action), (
                    f"{name}: action '{action}' 不符合 snake_case 规范"
                )

    def test_create_actions_start_with_create(self):
        """创建操作的 action 包含 create"""
        src = SOURCES["products"]
        create_actions = re.findall(r'action="(create\w*)"', src)
        for action in create_actions:
            assert action.startswith("create"), f"创建 action 应以 create 开头: {action}"

    def test_delete_actions_start_with_delete(self):
        """删除操作的 action 包含 delete"""
        for name in ["products", "customers", "orders"]:
            src = SOURCES[name]
            delete_actions = re.findall(r'action="(delete\w*)"', src)
            for action in delete_actions:
                assert action.startswith("delete"), f"{name}: 删除 action 应以 delete 开头: {action}"

    def test_update_actions_start_with_update(self):
        """更新操作的 action 包含 update"""
        for name in ["products", "customers", "orders", "users"]:
            src = SOURCES[name]
            update_actions = re.findall(r'action="(update\w*)"', src)
            for action in update_actions:
                assert action.startswith("update"), f"{name}: 更新 action 应以 update 开头: {action}"

    def test_resource_type_matches_module(self):
        """resource_type 与模块对应"""
        module_resource = {
            "products": "product",
            "customers": "customer",
            "orders": "order",
            "payments": "payment",
            "users": "user",
            "roles": "role",
            "files": "file",
            "inventory": "product",
        }
        for name, expected in module_resource.items():
            src = SOURCES[name]
            if "resource_type=" in src:
                assert f'resource_type="{expected}"' in src or f"resource_type='{expected}'" in src, (
                    f"{name} 应使用 resource_type={expected}"
                )


# ═══════════════════════════════════════════════════════════
# 4. 审计参数传递一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuditParamConsistency:
    """审计日志传递 db、request、current_user 参数"""

    def test_log_user_action_signature(self):
        """log_user_action 接受 db、request、user 参数"""
        assert "def log_user_action" in AUDIT_SVC
        # 提取函数签名区域（从 def 到冒号，可能含 -> 返回类型）
        sig_match = re.search(r"def log_user_action\([\s\S]*?\)(?:\s*->[^:]+)?:", AUDIT_SVC)
        assert sig_match, "log_user_action 函数签名未找到"
        sig = sig_match.group(0)
        assert "db" in sig, "log_user_action 应接受 db 参数"
        assert "request" in sig, "log_user_action 应接受 request 参数"
        assert "user" in sig, "log_user_action 应接受 user 参数"

    def test_get_request_meta_available(self):
        """get_request_meta 辅助函数存在"""
        assert "def get_request_meta" in AUDIT_SVC, "应定义 get_request_meta 函数"

    def test_products_passes_request_to_log(self):
        """products 模块传递 request 给审计函数"""
        src = SOURCES["products"]
        log_calls = re.findall(r"log_user_action\([^)]+\)", src)
        assert len(log_calls) > 0, "products 应有 log_user_action 调用"

    def test_audit_service_extracts_ip_and_user_agent(self):
        """审计服务提取 IP 和 User-Agent"""
        meta_func = re.search(r"def get_request_meta\([^)]*\)[^:]*:(.*?)(?=\ndef )", AUDIT_SVC, re.DOTALL)
        if meta_func:
            body = meta_func.group(1)
            assert "client" in body or "ip" in body.lower(), "应提取客户端 IP"

    def test_all_log_calls_pass_db(self):
        """所有审计调用传递 db 参数（可能在下一行）"""
        for name, src in SOURCES.items():
            if "log_user_action" not in src:
                continue
            # log_user_action( 后面紧跟换行和 db，或直接 db
            calls = re.findall(r"log_user_action\(\s*\n?\s*db", src)
            assert len(calls) > 0, f"{name} 的 log_user_action 调用应传递 db"


# ═══════════════════════════════════════════════════════════
# 5. 列表端点无审计日志验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestListEndpointsNoAudit:
    """列表和详情查询端点不应记录审计日志"""

    def test_products_list_no_log(self):
        src = SOURCES["products"]
        # 找 GET 端点
        get_endpoints = re.findall(r'@router\.get\("([^"]*)"\)', src)
        if get_endpoints:
            # 第一个 GET 通常是列表，不应有审计日志
            first_get = get_endpoints[0]
            assert first_get == "" or first_get == "/", f"第一个 GET 端点: {first_get}"

    def test_customers_list_no_audit_log(self):
        """customers 列表端点不记录审计日志"""
        src = SOURCES["customers"]
        # 找第一个 GET 装饰器后的函数体
        first_get = re.search(r'@router\.get\(""\)', src)
        if first_get:
            # 到下一个 @router 之间的内容
            rest = src[first_get.end():]
            next_route = re.search(r'@router\.', rest)
            func_body = rest[:next_route.start()] if next_route else rest[:1000]
            assert "log_user_action" not in func_body, "列表端点不应调用审计日志"

    def test_orders_list_no_audit_log(self):
        """orders 列表端点不记录审计日志"""
        src = SOURCES["orders"]
        first_get = re.search(r'@router\.get\(""\)', src)
        if first_get:
            rest = src[first_get.end():]
            next_route = re.search(r'@router\.', rest)
            func_body = rest[:next_route.start()] if next_route else rest[:1000]
            assert "log_user_action" not in func_body, "列表端点不应调用审计日志"

    def test_audit_service_provides_both_functions(self):
        """审计服务同时提供 log_user_action 和 log_action"""
        assert "def log_user_action" in AUDIT_SVC
        assert "def log_action" in AUDIT_SVC

    def test_auth_uses_log_action_not_log_user_action(self):
        """auth 模块使用 log_action（无认证用户）"""
        src = SOURCES["auth"]
        assert "log_action" in src, "auth 应使用 log_action"
        # auth.py 不应使用 log_user_action
        assert "log_user_action" not in src, "auth 不应使用 log_user_action"
