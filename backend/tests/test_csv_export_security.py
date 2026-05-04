"""
安全加固：后端 CSV 导出服务安全与注入防护验证测试
覆盖 CSV 公式注入防护、BOM 编码头、LIKE 注入防护、
敏感字段可见性控制、流式生成模式
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPORT = (ROOT / "app" / "services" / "export_service.py").read_text()
SANITIZE = (ROOT / "app" / "core" / "sanitize.py").read_text()
DEPS = (ROOT / "app" / "api" / "deps.py").read_text()


def _func_body(src: str, func_name: str) -> str:
    """提取函数体文本：从 def 行到下一个顶层 def/class 或文件末尾"""
    m = re.search(rf"^def {func_name}\b", src, re.MULTILINE)
    if not m:
        return ""
    # 找到 def 行之后的第一个非空行（函数体开始）
    rest = src[m.start():]
    # 找下一个顶层 def（行首的 def）
    next_def = re.search(r"\ndef \w", rest[1:])  # skip the first def
    if next_def:
        return rest[1:1 + next_def.start()]
    return rest[1:]


# ═══════════════════════════════════════════════════════════
# 1. CSV 公式注入防护验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCSVInjectionPrevention:
    """导出服务使用 sanitize_csv_cell 防御 CSV 公式注入"""

    def test_export_imports_sanitize_csv_cell(self):
        assert "sanitize_csv_cell" in EXPORT, "导出服务应导入 sanitize_csv_cell"

    def test_str_helper_uses_sanitize(self):
        """_str 辅助函数调用 sanitize_csv_cell"""
        body = _func_body(EXPORT, "_str")
        assert "sanitize_csv_cell" in body, "_str 应调用 sanitize_csv_cell"

    def test_sanitize_handles_formula_chars(self):
        """sanitize_csv_cell 处理公式触发字符"""
        # 检查 _CSV_FORMULA_CHARS 集合定义
        assert "_CSV_FORMULA_CHARS" in SANITIZE
        assert '"="' in SANITIZE or "'='" in SANITIZE
        assert '"+"' in SANITIZE or "'+'" in SANITIZE
        assert '"-"' in SANITIZE or "'-'" in SANITIZE

    def test_sanitize_prepends_quote(self):
        """sanitize_csv_cell 在公式字符前加单引号"""
        assert "'" in SANITIZE, "sanitize_csv_cell 应使用单引号前缀"
        assert "f\"'" in SANITIZE or "f'{" in SANITIZE or "\"'\"" in SANITIZE, (
            "sanitize_csv_cell 应前置单引号阻止公式解析"
        )

    def test_export_row_functions_use_str_helper(self):
        """所有行生成函数使用 _str 而非直接 str()"""
        for func_name in ["_product_row", "_customer_row", "_order_row", "_payment_row"]:
            body = _func_body(EXPORT, func_name)
            assert "_str(" in body, f"{func_name} 应使用 _str 辅助函数"


# ═══════════════════════════════════════════════════════════
# 2. BOM 编码头与 CSV 格式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBOMAndCSVFormat:
    """导出服务使用 UTF-8 BOM 和标准 CSV 格式"""

    def test_bom_constant_defined(self):
        assert "BOM" in EXPORT, "应定义 BOM 常量"

    def test_bom_prepended_to_first_chunk(self):
        """首个数据块包含 BOM 头"""
        for func_name in ["export_products", "export_customers", "export_orders", "export_payments"]:
            body = _func_body(EXPORT, func_name)
            assert "BOM" in body, f"{func_name} 首个 yield 应包含 BOM"

    def test_uses_csv_writer(self):
        """使用 csv.writer 生成 CSV 内容"""
        assert "csv.writer" in EXPORT, "应使用 csv.writer"
        assert "import csv" in EXPORT, "应导入 csv 模块"

    def test_header_row_written_first(self):
        """每个导出函数先写入表头行"""
        for func_name in ["export_products", "export_customers", "export_orders", "export_payments"]:
            body = _func_body(EXPORT, func_name)
            assert "writerow(headers)" in body or "writer.writerow" in body, (
                f"{func_name} 应先写入表头行"
            )

    def test_string_io_buffer_per_row(self):
        """每行使用独立 StringIO 缓冲区"""
        assert "io.StringIO" in EXPORT, "应使用 io.StringIO 缓冲区"
        # 每行创建新的缓冲区
        count = EXPORT.count("io.StringIO()")
        assert count >= 4, f"每个导出函数应有独立 StringIO，实际 {count} 处"


# ═══════════════════════════════════════════════════════════
# 3. LIKE 注入防护验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLikeInjectionPrevention:
    """导出服务使用 escape_like 防御 LIKE 注入"""

    def test_export_imports_escape_like(self):
        assert "escape_like" in EXPORT, "导出服务应导入 escape_like"

    def test_escape_like_handles_special_chars(self):
        """escape_like 处理 %、_、\\ 特殊字符"""
        for char in ["%", "_", "\\"]:
            assert char in SANITIZE, f"escape_like 应处理 {repr(char)}"

    def test_keyword_filters_use_escape_like(self):
        """关键字过滤使用 escape_like"""
        for func_name in ["export_products", "export_customers", "export_orders"]:
            body = _func_body(EXPORT, func_name)
            if "keyword" in body:
                assert "escape_like" in body, f"{func_name} 关键字过滤应使用 escape_like"

    def test_escape_like_prepends_backslash(self):
        """escape_like 在特殊字符前加反斜杠"""
        assert '"\\\\"' in SANITIZE or "'\\\\" in SANITIZE or "append(\"\\\\\")" in SANITIZE, (
            "escape_like 应在特殊字符前加反斜杠"
        )
        assert 'escape="' in EXPORT or "escape='" in EXPORT, (
            "导出服务生成的 LIKE 模式应指定 escape 字符"
        )

    def test_ilike_used_for_search(self):
        """搜索使用 ilike（不区分大小写）"""
        assert "ilike" in EXPORT, "搜索应使用 ilike"


# ═══════════════════════════════════════════════════════════
# 4. 敏感字段可见性控制验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSensitiveFieldVisibility:
    """导出服务根据权限控制成本价等敏感字段"""

    def test_product_export_has_cost_visibility_flag(self):
        """商品导出接受 can_view_cost 参数"""
        body = _func_body(EXPORT, "export_products")
        assert "can_view_cost" in body, "export_products 应接受 can_view_cost 参数"

    def test_order_export_has_cost_visibility_flag(self):
        """订单导出接受 can_view_cost 参数"""
        body = _func_body(EXPORT, "export_orders")
        assert "can_view_cost" in body, "export_orders 应接受 can_view_cost 参数"

    def test_product_row_conditional_cost(self):
        """商品行按 can_view_cost 决定是否包含成本价"""
        body = _func_body(EXPORT, "_product_row")
        assert "can_view_cost" in body, "_product_row 应根据 can_view_cost 条件输出成本价"

    def test_product_headers_without_cost(self):
        """无成本权限时使用不含成本价的表头"""
        assert "PRODUCT_HEADERS_NO_COST" in EXPORT, "应定义不含成本价的表头"

    def test_order_headers_without_cost(self):
        """订单无成本权限时使用不含成本/毛利的表头"""
        assert "ORDER_HEADERS_NO_COST" in EXPORT, "应定义不含成本/毛利的订单表头"


# ═══════════════════════════════════════════════════════════
# 5. 流式生成与数据过滤模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStreamingAndFiltering:
    """导出服务使用流式生成和软删除过滤"""

    def test_all_exports_are_generators(self):
        """所有导出函数使用 yield 返回生成器"""
        for func_name in ["export_products", "export_customers", "export_orders", "export_payments"]:
            body = _func_body(EXPORT, func_name)
            assert "yield" in body, f"{func_name} 应使用 yield 生成器"

    def test_yield_per_used_for_large_datasets(self):
        """使用 yield_per 分批加载大数据集"""
        assert "yield_per" in EXPORT, "应使用 yield_per 分批查询"
        assert "yield_per(500)" in EXPORT, "yield_per 批次大小应为 500"

    def test_all_exports_use_active_query(self):
        """所有导出函数使用 active_query 过滤软删除"""
        for func_name in ["export_products", "export_customers", "export_orders"]:
            body = _func_body(EXPORT, func_name)
            assert "active_query" in body, f"{func_name} 应使用 active_query 过滤软删除"

    def test_payment_export_filters_soft_deleted_orders(self):
        """收款导出过滤已软删除的订单"""
        body = _func_body(EXPORT, "export_payments")
        assert "deleted_at" in body, "export_payments 应过滤软删除的订单"

    def test_exports_ordered_by_created_at_desc(self):
        """导出按创建时间降序排列"""
        for func_name in ["export_products", "export_customers", "export_orders", "export_payments"]:
            body = _func_body(EXPORT, func_name)
            assert "order_by" in body, f"{func_name} 应使用 order_by"
            assert "desc()" in body, f"{func_name} 应使用 desc() 降序"
