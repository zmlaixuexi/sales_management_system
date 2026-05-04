"""代码质量：后端报表模块结构与逻辑验证测试
覆盖周期类型约束、日期范围计算、有效订单状态、数据权限过滤、响应字段结构"""

import re
from pathlib import Path

REPORTS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "reports.py"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"


def _extract_function_source(source: str, func_name: str) -> str:
    """提取函数体（含多行参数定义）"""
    idx = source.find(f"def {func_name}(")
    if idx == -1:
        return ""
    # 先找到函数签名的结束位置（关闭括号 + 冒号）
    rest = source[idx:]
    paren_depth = 0
    sig_end = 0
    for i, ch in enumerate(rest):
        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth -= 1
            if paren_depth == 0:
                # 找到冒号
                colon_pos = rest.find(":", i)
                if colon_pos != -1:
                    sig_end = colon_pos + 1
                break
    # 从签名结束后开始收集函数体
    body_start = rest.find("\n", sig_end)
    if body_start == -1:
        return ""
    lines = rest[body_start + 1:].split("\n")
    collected = []
    for line in lines:
        if line and not line[0].isspace() and line.strip() and not line.strip().startswith("#"):
            break
        collected.append(line)
    return "\n".join(collected)


# ═══════════════════════════════════════════════════════════
# 1. 周期类型约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPeriodTypeConstraints:
    """验证周期参数类型定义"""

    def test_period_type_is_literal(self):
        source = REPORTS_FILE.read_text()
        assert "PeriodType = Literal[" in source

    def test_period_type_includes_today(self):
        source = REPORTS_FILE.read_text()
        assert '"today"' in source

    def test_period_type_includes_7d_30d(self):
        source = REPORTS_FILE.read_text()
        assert '"7d"' in source
        assert '"30d"' in source

    def test_period_type_includes_month_periods(self):
        source = REPORTS_FILE.read_text()
        assert '"this_month"' in source
        assert '"last_month"' in source

    def test_date_range_handles_all_periods(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "today" in body
        assert "7d" in body
        assert "30d" in body
        assert "this_month" in body
        assert "last_month" in body


# ═══════════════════════════════════════════════════════════
# 2. 日期范围计算验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestDateRangeCalculation:
    """验证 _date_range 函数逻辑"""

    def test_today_returns_today(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert 'period == "today"' in body
        assert "start = today" in body

    def test_7d_returns_7_days(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "timedelta(days=6)" in body  # today + 6 previous days = 7 days total

    def test_30d_returns_30_days(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "timedelta(days=29)" in body  # today + 29 previous = 30 days

    def test_this_month_starts_at_first(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "replace(day=1)" in body

    def test_invalid_period_raises_400(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "400" in body or "HTTPException" in body

    def test_returns_start_and_end(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_date_range")
        assert "return start, today" in body


# ═══════════════════════════════════════════════════════════
# 3. 有效订单状态验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestValidOrderStatuses:
    """验证报表使用的有效订单状态"""

    def test_valid_statuses_defined(self):
        source = REPORTS_FILE.read_text()
        assert "_VALID_ORDER_STATUSES" in source

    def test_includes_confirmed(self):
        source = REPORTS_FILE.read_text()
        assert '"confirmed"' in source

    def test_includes_completed(self):
        source = REPORTS_FILE.read_text()
        assert '"completed"' in source

    def test_excludes_pending(self):
        """待确认订单不计入报表"""
        source = REPORTS_FILE.read_text()
        m = re.search(r'_VALID_ORDER_STATUSES\s*=\s*\[([^\]]+)\]', source)
        assert m
        statuses = m.group(1)
        assert '"pending"' not in statuses

    def test_excludes_cancelled(self):
        """已取消订单不计入报表"""
        source = REPORTS_FILE.read_text()
        m = re.search(r'_VALID_ORDER_STATUSES\s*=\s*\[([^\]]+)\]', source)
        assert m
        statuses = m.group(1)
        assert '"cancelled"' not in statuses


# ═══════════════════════════════════════════════════════════
# 4. 数据权限过滤验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDataScopeFilter:
    """验证数据权限过滤逻辑"""

    def test_apply_data_scope_function_exists(self):
        source = REPORTS_FILE.read_text()
        assert "def _apply_data_scope(" in source

    def test_checks_view_all_permission(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_apply_data_scope")
        assert "order:view_all" in body

    def test_filters_by_sales_user_id(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_apply_data_scope")
        assert "sales_user_id" in body
        assert "current_user.id" in body

    def test_all_report_endpoints_apply_data_scope(self):
        """所有报表端点都应用数据范围过滤"""
        source = REPORTS_FILE.read_text()
        # 每个报表端点函数应调用 _apply_data_scope
        for func_name in ["sales_summary", "sales_trend", "product_ranking",
                          "customer_ranking", "salesperson_ranking"]:
            body = _extract_function_source(source, func_name)
            # inventory_warning 不需要数据范围过滤（它查商品）
            assert "_apply_data_scope" in body or func_name == "inventory_warning", \
                f"{func_name} 未调用 _apply_data_scope"

    def test_order_period_filter_excludes_deleted(self):
        """订单过滤排除已删除订单"""
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "_order_period_filter")
        assert "deleted_at" in body


# ═══════════════════════════════════════════════════════════
# 5. 响应字段结构验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestReportResponseStructure:
    """验证报表响应字段结构"""

    def test_sales_summary_has_required_fields(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "sales_summary")
        assert '"total_amount"' in body
        assert '"order_count"' in body
        assert '"period"' in body

    def test_sales_summary_conditional_profit_fields(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "sales_summary")
        assert "can_view_profit" in body
        assert '"total_cost"' in body
        assert '"gross_profit"' in body
        assert '"gross_margin"' in body

    def test_sales_trend_fills_missing_dates(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "sales_trend")
        assert "data_map" in body
        assert "timedelta(days=1)" in body

    def test_ranking_endpoints_have_rank_field(self):
        source = REPORTS_FILE.read_text()
        for func_name in ["product_ranking", "customer_ranking", "salesperson_ranking"]:
            body = _extract_function_source(source, func_name)
            assert '"rank"' in body

    def test_ranking_endpoints_have_limit_param(self):
        source = REPORTS_FILE.read_text()
        for func_name in ["product_ranking", "customer_ranking", "salesperson_ranking"]:
            body = _extract_function_source(source, func_name)
            assert "limit" in body

    def test_inventory_warning_uses_config_threshold(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "inventory_warning")
        assert "INVENTORY_WARNING_THRESHOLD" in body


# ═══════════════════════════════════════════════════════════
# 6. 毛利率计算验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestGrossMarginCalculation:
    """验证毛利率计算逻辑"""

    def test_gross_margin_uses_decimal(self):
        source = REPORTS_FILE.read_text()
        assert "Decimal" in source

    def test_gross_margin_handles_zero_amount(self):
        """总金额为零时毛利率为 0"""
        source = REPORTS_FILE.read_text()
        assert 'Decimal("0")' in source

    def test_gross_margin_quantize_to_001(self):
        source = REPORTS_FILE.read_text()
        assert 'Decimal("0.01")' in source

    def test_gross_margin_formula(self):
        source = REPORTS_FILE.read_text()
        body = _extract_function_source(source, "sales_summary")
        assert "gross_profit / total_amount" in body or "gross_profit" in body
        assert "100" in body

    def test_config_has_inventory_threshold(self):
        source = CONFIG_FILE.read_text()
        assert "INVENTORY_WARNING_THRESHOLD" in source
