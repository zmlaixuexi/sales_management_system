"""需求符合性：后端 API 响应分页元数据一致性验证测试
覆盖分页参数定义、响应字段一致性、所有分页端点覆盖、参数传递正确性、边界约束"""

import re
from pathlib import Path

DEPS = Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"
API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"

# 已知使用分页的模块及端点
PAGINATED_MODULES = {
    "products.py": ["list_products"],
    "customers.py": ["list_customers"],
    "orders.py": ["list_orders", "order_logs"],
    "payments.py": ["list_payments"],
    "users.py": ["list_users"],
    "inventory.py": ["list_movements"],
    "audit_logs.py": ["list_audit_logs"],
}

# 已知不使用分页的模块
NON_PAGINATED_MODULES = [
    "auth.py", "files.py", "exports.py",
    "health.py", "reports.py", "roles.py",
]


# ═══════════════════════════════════════════════════════════
# 1. 分页参数定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginationParamsDefinition:
    """验证 PaginationParams 数据类定义"""

    def test_pagination_params_is_dataclass(self):
        source = DEPS.read_text()
        assert "@dataclass" in source
        assert "class PaginationParams" in source

    def test_page_default_and_constraints(self):
        source = DEPS.read_text()
        # page 默认 1, ge=1, le=10000
        assert "page:" in source
        assert "Query(1" in source
        assert "ge=1" in source
        assert "le=10000" in source

    def test_page_size_default_and_constraints(self):
        source = DEPS.read_text()
        # page_size 默认 20, ge=1, le=100
        assert "page_size:" in source
        assert "Query(20" in source
        assert "le=100" in source

    def test_page_and_page_size_are_int(self):
        source = DEPS.read_text()
        pattern = r"class PaginationParams.*?(?=\n(?:class |def |$))"
        m = re.search(pattern, source, re.DOTALL)
        assert m
        body = m.group()
        assert "page: int" in body
        assert "page_size: int" in body

    def test_pagination_params_used_as_depends(self):
        """PaginationParams 通过 Depends() 注入"""
        source = DEPS.read_text()
        assert "PaginationParams" in source
        # 验证在 API 模块中被使用
        for mod_name in PAGINATED_MODULES:
            mod_source = (API_DIR / mod_name).read_text()
            assert "PaginationParams" in mod_source, f"{mod_name} 未导入 PaginationParams"


# ═══════════════════════════════════════════════════════════
# 2. paginate 函数验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginateFunction:
    """验证 paginate() 函数实现"""

    def test_paginate_returns_tuple(self):
        source = DEPS.read_text()
        assert "def paginate(" in source
        assert "return items, total" in source

    def test_paginate_uses_count(self):
        source = DEPS.read_text()
        assert "query.count()" in source

    def test_paginate_uses_offset_and_limit(self):
        source = DEPS.read_text()
        assert ".offset(" in source
        assert ".limit(" in source

    def test_paginate_offset_formula(self):
        """offset 计算 = (page - 1) * page_size"""
        source = DEPS.read_text()
        assert "(page - 1) * page_size" in source

    def test_paginate_signature(self):
        source = DEPS.read_text()
        # 签名: paginate(query, page, page_size)
        m = re.search(r"def paginate\(([^)]+)\)", source)
        assert m
        params = m.group(1)
        assert "query" in params
        assert "page" in params
        assert "page_size" in params


# ═══════════════════════════════════════════════════════════
# 3. paginated_resp 函数验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestPaginatedRespFunction:
    """验证 paginated_resp() 响应结构"""

    def test_paginated_resp_returns_dict_with_items(self):
        source = DEPS.read_text()
        assert '"items"' in source
        assert "paginated_resp" in source

    def test_paginated_resp_includes_page(self):
        source = DEPS.read_text()
        # 验证 data dict 包含 "page"
        m = re.search(r'def paginated_resp.*?return\s+resp\((.+?)\)', source, re.DOTALL)
        assert m
        body = m.group(1)
        assert '"page"' in body
        assert '"page_size"' in body
        assert '"total"' in body
        assert '"items"' in body

    def test_paginated_resp_only_four_fields(self):
        """分页响应数据只有 items/page/page_size/total 四个字段"""
        source = DEPS.read_text()
        m = re.search(r'resp\(data=\{([^}]+)\}', source)
        assert m
        fields_str = m.group(1)
        fields = re.findall(r'"(\w+)"', fields_str)
        assert set(fields) == {"items", "page", "page_size", "total"}

    def test_paginated_resp_wraps_through_resp(self):
        """paginated_resp 通过 resp() 构建响应"""
        source = DEPS.read_text()
        m = re.search(r'def paginated_resp.*?return\s+(\w+)\(', source, re.DOTALL)
        assert m
        assert m.group(1) == "resp"

    def test_paginated_resp_default_message(self):
        source = DEPS.read_text()
        m = re.search(r'def paginated_resp\([^)]*\)', source)
        assert m
        sig = m.group()
        assert 'message="查询成功"' in sig or 'message: str = "查询成功"' in sig

    def test_paginated_resp_signature_params(self):
        source = DEPS.read_text()
        m = re.search(r'def paginated_resp\(([^)]+)\)', source)
        assert m
        params = m.group(1)
        assert "items" in params
        assert "page" in params
        assert "page_size" in params
        assert "total" in params


# ═══════════════════════════════════════════════════════════
# 4. 各模块分页端点覆盖验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestPaginatedEndpointCoverage:
    """验证所有应分页的端点都使用了分页"""

    def test_products_uses_pagination(self):
        source = (API_DIR / "products.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_products(" in source

    def test_customers_uses_pagination(self):
        source = (API_DIR / "customers.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_customers(" in source

    def test_orders_list_uses_pagination(self):
        source = (API_DIR / "orders.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_orders(" in source

    def test_orders_logs_uses_pagination(self):
        source = (API_DIR / "orders.py").read_text()
        assert "def order_logs(" in source
        # order_logs 也使用 paginated_resp
        logs_idx = source.index("def order_logs(")
        assert "paginated_resp" in source[logs_idx:]

    def test_payments_uses_pagination(self):
        source = (API_DIR / "payments.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_payments(" in source

    def test_users_uses_pagination(self):
        source = (API_DIR / "users.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_users(" in source

    def test_inventory_uses_pagination(self):
        source = (API_DIR / "inventory.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_movements(" in source

    def test_audit_logs_uses_pagination(self):
        source = (API_DIR / "audit_logs.py").read_text()
        assert "PaginationParams" in source
        assert "paginated_resp" in source
        assert "def list_audit_logs(" in source


# ═══════════════════════════════════════════════════════════
# 5. 参数传递一致性验证（7 项）
# ═══════════════════════════════════════════════════════════


class TestPaginationParamPassing:
    """验证各端点正确传递 pagination.page 和 pagination.page_size"""

    def _get_function_body(self, source: str, func_name: str) -> str:
        """提取函数体"""
        idx = source.index(f"def {func_name}(")
        # 找到下一个同级别 def 或文件结尾
        depth = 0
        end = idx
        for i in range(idx, len(source)):
            if source[i] == '(':
                depth += 1
            elif source[i] == ')':
                depth -= 1
            elif depth == 0 and source[i] == '\n':
                # 检查下一行是否为顶级 def/class 或装饰器
                rest = source[i+1:]
                if rest and (rest.startswith('def ') or rest.startswith('class ') or rest.startswith('@')):
                    # 回溯找到上一个非空行
                    end = i
                    break
        else:
            end = len(source)
        return source[idx:end]

    def test_products_passes_pagination_correctly(self):
        source = (API_DIR / "products.py").read_text()
        body = self._get_function_body(source, "list_products")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_customers_passes_pagination_correctly(self):
        source = (API_DIR / "customers.py").read_text()
        body = self._get_function_body(source, "list_customers")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_orders_passes_pagination_correctly(self):
        source = (API_DIR / "orders.py").read_text()
        body = self._get_function_body(source, "list_orders")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_order_logs_passes_pagination_correctly(self):
        source = (API_DIR / "orders.py").read_text()
        body = self._get_function_body(source, "order_logs")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_payments_passes_pagination_correctly(self):
        source = (API_DIR / "payments.py").read_text()
        body = self._get_function_body(source, "list_payments")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_users_passes_pagination_correctly(self):
        source = (API_DIR / "users.py").read_text()
        body = self._get_function_body(source, "list_users")
        assert "pagination.page" in body
        assert "pagination.page_size" in body

    def test_inventory_passes_pagination_correctly(self):
        source = (API_DIR / "inventory.py").read_text()
        body = self._get_function_body(source, "list_movements")
        assert "pagination.page" in body
        assert "pagination.page_size" in body


# ═══════════════════════════════════════════════════════════
# 6. 非分页模块验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestNonPaginatedModules:
    """验证不应分页的模块未使用 paginated_resp"""

    def test_auth_no_pagination(self):
        source = (API_DIR / "auth.py").read_text()
        assert "paginated_resp" not in source
        assert "PaginationParams" not in source

    def test_files_no_pagination(self):
        source = (API_DIR / "files.py").read_text()
        assert "paginated_resp" not in source
        assert "PaginationParams" not in source

    def test_exports_no_pagination(self):
        source = (API_DIR / "exports.py").read_text()
        assert "paginated_resp" not in source
        assert "PaginationParams" not in source

    def test_health_no_pagination(self):
        source = (API_DIR / "health.py").read_text()
        assert "paginated_resp" not in source
        assert "PaginationParams" not in source

    def test_reports_no_pagination(self):
        source = (API_DIR / "reports.py").read_text()
        assert "paginated_resp" not in source
        assert "PaginationParams" not in source


# ═══════════════════════════════════════════════════════════
# 7. paginate 调用一致性验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestPaginateCallConsistency:
    """验证各端点调用 paginate() 时传入的参数一致"""

    def test_all_modules_import_paginate(self):
        """所有分页模块导入 paginate"""
        for mod_name in PAGINATED_MODULES:
            source = (API_DIR / mod_name).read_text()
            assert "paginate" in source, f"{mod_name} 未导入 paginate"

    def test_all_modules_import_paginated_resp(self):
        """所有分页模块导入 paginated_resp"""
        for mod_name in PAGINATED_MODULES:
            source = (API_DIR / mod_name).read_text()
            assert "paginated_resp" in source, f"{mod_name} 未导入 paginated_resp"

    def test_products_calls_paginate(self):
        source = (API_DIR / "products.py").read_text()
        assert "paginate(" in source

    def test_customers_calls_paginate(self):
        source = (API_DIR / "customers.py").read_text()
        assert "paginate(" in source

    def test_orders_calls_paginate(self):
        source = (API_DIR / "orders.py").read_text()
        assert "paginate(" in source

    def test_payments_calls_paginate(self):
        source = (API_DIR / "payments.py").read_text()
        assert "paginate(" in source

    def test_users_calls_paginate(self):
        source = (API_DIR / "users.py").read_text()
        assert "paginate(" in source

    def test_inventory_calls_paginate(self):
        source = (API_DIR / "inventory.py").read_text()
        assert "paginate(" in source

    def test_audit_logs_calls_paginate(self):
        source = (API_DIR / "audit_logs.py").read_text()
        assert "paginate(" in source


# ═══════════════════════════════════════════════════════════
# 8. audit_logs 分页传递验证（1 项）
# ═══════════════════════════════════════════════════════════


class TestAuditLogsPagination:
    """验证 audit_logs 端点分页参数传递"""

    def test_audit_logs_passes_pagination_correctly(self):
        source = (API_DIR / "audit_logs.py").read_text()
        body = source[source.index("def list_audit_logs("):]
        assert "pagination.page" in body
        assert "pagination.page_size" in body
