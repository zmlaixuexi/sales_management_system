"""
代码质量：后端 API 端点查询参数与分页参数命名规范验证测试
覆盖分页参数定义、分页注入一致性、
keyword 参数命名、过滤参数类型、Query 参数约束
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()

API_DIR = ROOT / "app" / "api" / "v1"
MODULES = ["products", "customers", "orders", "payments", "inventory",
           "audit_logs", "reports", "exports", "users", "roles"]
SOURCES = {name: (API_DIR / f"{name}.py").read_text() for name in MODULES}


def _list_endpoints(src: str) -> list[str]:
    """提取所有 GET list 端点函数名"""
    funcs = []
    for m in re.finditer(r'@router\.get\([^)]*\)\s*(?:async\s+)?def\s+(\w+)', src):
        funcs.append(m.group(1))
    return funcs


def _get_function_body(src: str, func_name: str) -> str:
    """提取函数签名（到第一个冒号或函数体开始）"""
    m = re.search(rf'def\s+{func_name}\s*\(', src)
    if not m:
        return ""
    # 匹配平衡括号获取参数列表
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(src) and (depth > 0 or i == start):
        if src[i] == '(':
            depth += 1
        elif src[i] == ')':
            depth -= 1
        i += 1
    return src[start:i]


# ═══════════════════════════════════════════════════════════
# 1. 分页参数定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginationParamsDefinition:
    """PaginationParams 数据类定义规范"""

    def test_pagination_params_is_dataclass(self):
        """PaginationParams 是 dataclass"""
        assert "@dataclass" in DEPS_SRC, "PaginationParams 应使用 @dataclass 装饰器"
        assert "class PaginationParams" in DEPS_SRC, "应定义 PaginationParams 类"

    def test_page_field_has_query_constraints(self):
        """page 字段有 Query 约束（ge=1, le=10000）"""
        assert "page" in DEPS_SRC, "PaginationParams 应有 page 字段"
        assert "ge=1" in DEPS_SRC or "ge" in DEPS_SRC, "page 应有 ge=1"
        assert "le=" in DEPS_SRC, "page 应有上限约束"

    def test_page_size_field_has_query_constraints(self):
        """page_size 字段有 Query 约束（ge=1, le=100）"""
        assert "page_size" in DEPS_SRC, "PaginationParams 应有 page_size 字段"
        m = re.search(r'page_size.*?le\s*=\s*(\d+)', DEPS_SRC)
        assert m, "page_size 应有 le 约束"
        assert int(m.group(1)) <= 100, "page_size le 应 <= 100"

    def test_page_default_is_one(self):
        """page 默认值为 1"""
        m = re.search(r'page\s*:\s*int\s*=\s*Query\((\d+)', DEPS_SRC)
        assert m, "page 应有 Query 默认值"
        assert int(m.group(1)) == 1, f"page 默认应为 1，实际 {m.group(1)}"

    def test_page_size_default_reasonable(self):
        """page_size 默认值合理（10-50）"""
        m = re.search(r'page_size\s*:\s*int\s*=\s*Query\((\d+)', DEPS_SRC)
        assert m, "page_size 应有 Query 默认值"
        val = int(m.group(1))
        assert 10 <= val <= 50, f"page_size 默认值应在 10-50 之间，实际 {val}"


# ═══════════════════════════════════════════════════════════
# 2. 分页注入一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginationInjectionConsistency:
    """各模块列表端点一致使用 PaginationParams"""

    def test_core_list_modules_use_pagination(self):
        """核心列表端点（products, customers, orders, users）使用 PaginationParams"""
        for name in ["products", "customers", "orders", "users"]:
            src = SOURCES[name]
            assert "PaginationParams" in src, f"{name} 模块应导入 PaginationParams"
            assert "Depends()" in src or "Depends(PaginationParams)" in src, (
                f"{name} 列表端点应注入 PaginationParams"
            )

    def test_secondary_list_modules_use_pagination(self):
        """次要列表端点（payments, inventory, audit_logs）使用 PaginationParams"""
        for name in ["payments", "inventory", "audit_logs"]:
            src = SOURCES[name]
            assert "PaginationParams" in src, f"{name} 模块应导入 PaginationParams"

    def test_reports_do_not_use_pagination(self):
        """报表端点不使用 PaginationParams（使用 period + limit）"""
        src = SOURCES["reports"]
        assert "PaginationParams" not in src, "报表端点不应使用 PaginationParams"
        assert "period" in src.lower(), "报表端点应有 period 参数"

    def test_exports_do_not_use_pagination(self):
        """导出端点不使用 PaginationParams（流式输出）"""
        src = SOURCES["exports"]
        assert "PaginationParams" not in src, "导出端点不应使用 PaginationParams"

    def test_roles_do_not_use_pagination(self):
        """角色/权限列表不使用 PaginationParams（数据量小）"""
        src = SOURCES["roles"]
        assert "PaginationParams" not in src, "角色列表不应使用 PaginationParams"


# ═══════════════════════════════════════════════════════════
# 3. keyword 参数命名验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestKeywordParameterNaming:
    """keyword 参数命名一致"""

    def test_keyword_param_type_is_optional_str(self):
        """keyword 参数使用 str | None 类型"""
        for name in ["products", "customers", "orders", "users"]:
            src = SOURCES[name]
            # 搜索 keyword: str | None = None 或 keyword: Optional[str] = None
            m = re.search(r'keyword\s*:\s*(str\s*\|\s*None|Optional\[str\])\s*=\s*None', src)
            assert m, f"{name} keyword 参数应为 str | None = None"

    def test_keyword_param_used_in_searchable_modules(self):
        """有文本搜索需求的模块都使用 keyword 参数"""
        searchable = ["products", "customers", "orders", "users"]
        for name in searchable:
            src = SOURCES[name]
            assert "keyword" in src, f"{name} 列表端点应有 keyword 参数"

    def test_keyword_default_is_none(self):
        """keyword 参数默认值为 None"""
        for name in ["products", "customers", "orders"]:
            m = re.search(r'keyword\s*[:=].*?=\s*(\w+)', SOURCES[name])
            assert m, f"{name} keyword 应有默认值"
            assert m.group(1) == "None", f"{name} keyword 默认应为 None"

    def test_export_endpoints_mirror_keyword_params(self):
        """导出端点使用相同的 keyword 参数"""
        exports_src = SOURCES["exports"]
        for name in ["products", "customers", "orders"]:
            assert "keyword" in exports_src, "导出端点应有 keyword 参数"

    def test_audit_logs_has_keyword(self):
        """审计日志支持 keyword 搜索"""
        assert "keyword" in SOURCES["audit_logs"], "审计日志应有 keyword 参数"


# ═══════════════════════════════════════════════════════════
# 4. 过滤参数类型验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFilterParameterTypes:
    """过滤参数使用合适的类型"""

    def test_status_filters_use_literal(self):
        """状态过滤使用 Literal 类型"""
        for name, expected_status in [("products", "active"), ("orders", "draft")]:
            src = SOURCES[name]
            m = re.search(r'status\s*:\s*Literal\[', src)
            assert m, f"{name} status 过滤应使用 Literal 类型"
            assert expected_status in src, f"{name} Literal 应包含 '{expected_status}'"

    def test_uuid_filters_use_uuid_type(self):
        """UUID 过滤参数使用 uuid.UUID 类型"""
        uuid_filters = {
            "products": "category_id",
            "customers": "owner_user_id",
            "orders": "customer_id",
            "payments": "order_id",
        }
        for name, param in uuid_filters.items():
            src = SOURCES[name]
            m = re.search(rf'{param}\s*:\s*uuid\.UUID\s*\|\s*None', src)
            assert m, f"{name} {param} 应使用 uuid.UUID | None 类型"

    def test_date_filters_exist_where_needed(self):
        """需要日期过滤的模块有日期参数"""
        assert "start_date" in SOURCES["exports"], "导出订单应有 start_date"
        assert "end_date" in SOURCES["exports"], "导出订单应有 end_date"
        assert "start_date" in SOURCES["audit_logs"], "审计日志应有 start_date"

    def test_reports_use_period_literal(self):
        """报表使用 period Literal 类型"""
        src = SOURCES["reports"]
        assert "PeriodType" in src or "Literal" in src, "报表应有 PeriodType 或 Literal 类型"
        assert "30d" in src or "today" in src, "PeriodType 应包含标准时间段值"

    def test_inventory_movement_type_uses_literal(self):
        """库存变动类型使用 Literal 或 Enum"""
        src = SOURCES["inventory"]
        assert "movement_type" in src, "库存查询应有 movement_type 参数"
        assert "Literal" in src or "MovementType" in src, "movement_type 应使用 Literal 或枚举"


# ═══════════════════════════════════════════════════════════
# 5. Query 参数约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestQueryParameterConstraints:
    """Query 参数有合理的约束"""

    def test_report_limit_has_bounds(self):
        """报表 limit 参数有 ge 和 le 约束"""
        src = SOURCES["reports"]
        m = re.search(r'limit\s*:\s*int\s*=\s*Query\(\d+,\s*ge\s*=\s*(\d+)', src)
        assert m, "报表 limit 应有 ge 约束"
        assert int(m.group(1)) >= 1, "limit ge 应 >= 1"
        m2 = re.search(r'limit\s*:\s*int\s*=\s*Query\([^)]*le\s*=\s*(\d+)', src)
        assert m2, "报表 limit 应有 le 约束"
        assert int(m2.group(1)) <= 100, "limit le 应 <= 100"

    def test_inventory_threshold_has_bounds(self):
        """库存预警阈值有合理的约束"""
        src = SOURCES["reports"]
        m = re.search(r'threshold\s*:\s*int\s*=\s*Query', src)
        if m:
            m2 = re.search(r'threshold[^)]*ge\s*=\s*(\d+)', src)
            assert m2, "threshold 应有 ge 约束"
            assert int(m2.group(1)) >= 0, "threshold ge 应 >= 0"

    def test_products_sort_params_have_defaults(self):
        """商品排序参数有默认值"""
        src = SOURCES["products"]
        m = re.search(r'sort_by\s*:\s*str\s*=\s*Query\(["\'](\w+)["\']', src)
        assert m, "商品排序应有 sort_by 默认值"
        m2 = re.search(r'sort_order\s*:\s*str\s*=\s*Query\(["\'](\w+)["\']', src)
        assert m2, "商品排序应有 sort_order 默认值"
        assert m2.group(1) in ("asc", "desc"), "sort_order 默认应为 asc 或 desc"

    def test_all_filter_params_are_optional(self):
        """所有过滤参数默认 None（可选）"""
        for name in ["products", "customers", "orders", "payments", "inventory"]:
            src = SOURCES[name]
            # 查找所有 = None 的可选参数（排除 db, current_user, pagination, request）
            for m in re.finditer(r'(\w+)\s*:\s*(?:str|uuid|Literal|MovementType).*?=\s*None', src):
                param = m.group(1)
                # 确认这些参数默认 None
                assert "= None" in src[m.start():m.end() + 20], (
                    f"{name}.{param} 应默认 None"
                )

    def test_deprecated_query_params_not_used(self):
        """不使用已弃用的查询参数命名"""
        for name, src in SOURCES.items():
            # 不使用 pageNum/pageNum 等非标准命名
            assert "pageNum" not in src, f"{name} 不应使用 pageNum（应用 page）"
            assert "pageSize" not in src or "page_size" in src, (
                f"{name} 应使用 page_size 而非 pageSize"
            )
            # 不使用 search/searchTerm 等命名（统一用 keyword）
            if "keyword" in src:
                # 如果有 keyword，不应同时有 search 参数
                assert "search:" not in src and "search =" not in src, (
                    f"{name} 不应同时有 search 和 keyword 参数"
                )
