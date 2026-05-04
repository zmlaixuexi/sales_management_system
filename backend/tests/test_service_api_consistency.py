"""代码质量：后端服务层函数签名与 API 层调用一致性验证测试
覆盖服务模块公共 API、服务函数参数对齐、导出服务调用完整性、
审计服务使用覆盖、API 层直接 DB 操作审计"""

import re
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parent.parent / "app" / "services"
API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"


def _extract_public_functions(source: str) -> list[tuple[str, list[str]]]:
    """提取模块级公开函数: [(name, [param_names])]"""
    results = []
    for m in re.finditer(
        r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", source, re.MULTILINE
    ):
        name = m.group(1)
        if name.startswith("_"):
            continue
        params_raw = m.group(2)
        params = []
        for p in params_raw.split(","):
            p = p.strip()
            if not p or p == "/":
                continue
            param_name = p.split(":")[0].split("=")[0].strip()
            if param_name.startswith("*"):
                continue
            params.append(param_name)
        results.append((name, params))
    return results


def _extract_imports_from_services(source: str) -> list[tuple[str, str]]:
    """提取从 app.services 导入的: [(module, symbol)]"""
    results = []
    for m in re.finditer(
        r"from\s+app\.services\.(\w+)\s+import\s+(.+)", source
    ):
        module = m.group(1)
        symbols = [s.strip().rstrip(",") for s in m.group(2).split(",")]
        for s in symbols:
            # 处理多行 import 块中的括号
            s = s.strip("() ")
            if s:
                results.append((module, s))
    return results


def _extract_function_calls(source: str, func_name: str) -> list[str]:
    """提取源码中所有 func_name(...) 调用的完整文本"""
    calls = []
    pattern = re.escape(func_name) + r"\s*\("
    for m in re.finditer(pattern, source):
        start = m.end() - 1  # 指向 (
        depth = 0
        end = start
        for i in range(start, len(source)):
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        calls.append(source[start + 1 : end])
    return calls


def _count_positional_args(call_text: str) -> int:
    """统计函数调用中的位置参数数量"""
    depth = 0
    count = 0
    for ch in call_text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
        elif ch == "=" and depth == 0:
            pass  # keyword argument boundary
    if call_text.strip():
        count += 1
    return count


# ═══════════════════════════════════════════════════════════
# 1. 服务模块公共 API 验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestServiceModuleAPI:
    """验证服务模块公共函数定义"""

    def test_5_service_modules_exist(self):
        modules = ["payment_service", "audit_service", "file_service",
                    "export_service", "csv_import"]
        for mod in modules:
            path = SERVICES_DIR / f"{mod}.py"
            assert path.exists(), f"服务模块 {mod} 不存在"

    def test_payment_service_has_register_payment(self):
        source = (SERVICES_DIR / "payment_service.py").read_text()
        funcs = _extract_public_functions(source)
        names = [f[0] for f in funcs]
        assert "register_payment" in names
        assert "reset_payment_debounce" in names

    def test_register_payment_signature(self):
        source = (SERVICES_DIR / "payment_service.py").read_text()
        funcs = dict(_extract_public_functions(source))
        assert "db" in funcs["register_payment"]
        assert "order_id" in funcs["register_payment"]
        assert "data" in funcs["register_payment"]
        assert "current_user" in funcs["register_payment"]

    def test_file_service_has_upload_and_delete(self):
        source = (SERVICES_DIR / "file_service.py").read_text()
        funcs = _extract_public_functions(source)
        names = [f[0] for f in funcs]
        assert "upload_image" in names
        assert "delete_file" in names
        assert "cleanup_orphan_files" in names

    def test_audit_service_has_log_functions(self):
        source = (SERVICES_DIR / "audit_service.py").read_text()
        funcs = _extract_public_functions(source)
        names = [f[0] for f in funcs]
        assert "log_action" in names
        assert "log_user_action" in names
        assert "get_request_meta" in names
        assert "model_to_dict" in names


# ═══════════════════════════════════════════════════════════
# 2. 服务函数调用参数对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestServiceCallAlignment:
    """验证 API 层调用服务函数时参数正确"""

    def test_payments_api_calls_register_payment(self):
        source = (API_DIR / "payments.py").read_text()
        calls = _extract_function_calls(source, "register_payment")
        assert len(calls) == 1, f"payments.py 应调用 register_payment 1 次，实际 {len(calls)}"
        call = calls[0]
        assert "db" in call
        assert "str(order_id)" in call or "order_id" in call
        assert "data" in call
        assert "current_user" in call

    def test_orders_api_calls_register_payment(self):
        source = (API_DIR / "orders.py").read_text()
        calls = _extract_function_calls(source, "register_payment")
        assert len(calls) == 1, f"orders.py 应调用 register_payment 1 次，实际 {len(calls)}"
        call = calls[0]
        assert "db" in call
        assert "current_user" in call

    def test_files_api_calls_upload_image(self):
        source = (API_DIR / "files.py").read_text()
        calls = _extract_function_calls(source, "upload_image")
        assert len(calls) == 1, "files.py 应调用 upload_image 1 次"
        call = calls[0]
        assert "db" in call
        assert "file" in call

    def test_files_api_calls_delete_file(self):
        source = (API_DIR / "files.py").read_text()
        calls = _extract_function_calls(source, "delete_file")
        assert len(calls) == 1, "files.py 应调用 delete_file 1 次"
        call = calls[0]
        assert "db" in call
        assert "file_id" in call

    def test_log_user_action_called_with_4_positional_args(self):
        """log_user_action(db, request, user, action=..., ...) 前三个位置参数"""
        source = (API_DIR / "exports.py").read_text()
        calls = _extract_function_calls(source, "log_user_action")
        assert len(calls) == 4, "exports.py 应调用 log_user_action 4 次"
        for call in calls:
            positional = _count_positional_args(call)
            assert positional >= 3, f"log_user_action 至少需要 3 个位置参数: {call[:60]}"


# ═══════════════════════════════════════════════════════════
# 3. 导出服务调用完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExportServiceCalls:
    """验证导出端点正确调用导出服务"""

    def test_exports_api_imports_all_4_functions(self):
        source = (API_DIR / "exports.py").read_text()
        for func in ["export_products", "export_customers",
                     "export_orders", "export_payments"]:
            assert func in source, f"exports.py 未导入 {func}"

    def test_export_products_called_with_can_view_cost(self):
        source = (API_DIR / "exports.py").read_text()
        calls = _extract_function_calls(source, "export_products")
        assert len(calls) == 1
        assert "can_view_cost" in calls[0]

    def test_export_orders_called_with_can_view_cost(self):
        source = (API_DIR / "exports.py").read_text()
        calls = _extract_function_calls(source, "export_orders")
        assert len(calls) == 1
        assert "can_view_cost" in calls[0]

    def test_export_customers_called_with_owner_filter(self):
        source = (API_DIR / "exports.py").read_text()
        calls = _extract_function_calls(source, "export_customers")
        assert len(calls) == 1
        assert "owner_user_id" in calls[0]

    def test_export_payments_called_with_sales_filter(self):
        source = (API_DIR / "exports.py").read_text()
        calls = _extract_function_calls(source, "export_payments")
        assert len(calls) == 1
        assert "sales_user_id" in calls[0]


# ═══════════════════════════════════════════════════════════
# 4. 审计服务使用覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuditServiceUsage:
    """验证写操作端点使用审计服务"""

    def test_all_mutation_modules_import_audit(self):
        """所有有写操作的 API 模块都导入审计服务"""
        mutation_modules = [
            "products.py", "customers.py", "orders.py",
            "payments.py", "users.py", "roles.py",
            "files.py", "inventory.py", "exports.py",
        ]
        for mod in mutation_modules:
            source = (API_DIR / mod).read_text()
            assert "audit_service" in source or "log_action" in source or "log_user_action" in source, \
                f"{mod} 有写操作但未导入审计服务"

    def test_auth_module_uses_log_action(self):
        source = (API_DIR / "auth.py").read_text()
        assert "log_action" in source
        assert "get_request_meta" in source

    def test_products_api_log_user_action_calls(self):
        source = (API_DIR / "products.py").read_text()
        calls = _extract_function_calls(source, "log_user_action")
        # 创建、更新、删除、图片绑定、CSV 导入
        assert len(calls) >= 4, f"products.py 至少 4 次 log_user_action，实际 {len(calls)}"

    def test_orders_api_log_user_action_calls(self):
        source = (API_DIR / "orders.py").read_text()
        calls = _extract_function_calls(source, "log_user_action")
        # 创建、确认、取消、编辑、收款
        assert len(calls) >= 4, f"orders.py 至少 4 次 log_user_action，实际 {len(calls)}"

    def test_customers_api_log_user_action_calls(self):
        source = (API_DIR / "customers.py").read_text()
        calls = _extract_function_calls(source, "log_user_action")
        # 创建、更新、删除、转移、CSV 导入
        assert len(calls) >= 4, f"customers.py 至少 4 次 log_user_action，实际 {len(calls)}"


# ═══════════════════════════════════════════════════════════
# 5. API 层直接 DB 操作审计验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDirectDBOperations:
    """审计 API 层中的直接数据库操作"""

    def test_payments_list_uses_direct_query(self):
        """list_payments 是读取端点，直接查询可接受"""
        source = (API_DIR / "payments.py").read_text()
        assert "db.query(Payment)" in source or "select(Payment)" in source

    def test_reverse_payment_uses_with_for_update(self):
        """reverse_payment 在 API 层直接做行锁"""
        source = (API_DIR / "payments.py").read_text()
        assert "with_for_update" in source

    def test_audit_logs_uses_direct_query(self):
        """审计日志查询端点直接查询（无服务层抽象）"""
        source = (API_DIR / "audit_logs.py").read_text()
        assert "db.query(AuditLog)" in source or "select(AuditLog)" in source

    def test_exports_api_no_direct_db_operations(self):
        """导出端点不直接操作数据库，全部通过 export_service"""
        source = (API_DIR / "exports.py").read_text()
        assert "db.query(" not in source
        assert "db.add(" not in source
        assert "db.delete(" not in source

    def test_csv_import_used_in_products_and_customers(self):
        """CSV 导入校验在商品和客户模块使用"""
        products = (API_DIR / "products.py").read_text()
        customers = (API_DIR / "customers.py").read_text()
        assert "validate_csv_upload" in products
        assert "validate_csv_upload" in customers
