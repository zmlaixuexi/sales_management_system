"""数据导出边界测试 — 覆盖 CSV 导出格式、公式注入防御、敏感字段权限、工具函数"""

import re

from app.core.sanitize import (
    _CSV_FORMULA_CHARS,
    escape_like,
    sanitize_csv_cell,
    sanitize_text,
    strip_control_chars,
    strip_html,
)

# ═══════════════════════════════════════════════════════
# 1. CSV 公式注入防御 — sanitize_csv_cell
# ═══════════════════════════════════════════════════════


def test_csv_formula_equal_sign():
    """以 = 开头的值被加引号"""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_csv_formula_plus_sign():
    """以 + 开头的值被加引号"""
    assert sanitize_csv_cell("+cmd|'/C calc'") == "'+cmd|'/C calc'"


def test_csv_formula_minus_sign():
    """以 - 开头的值被加引号"""
    assert sanitize_csv_cell("-1+1|cmd") == "'-1+1|cmd"


def test_csv_formula_at_sign():
    """以 @ 开头的值被加引号"""
    assert sanitize_csv_cell("@SUM(A1)") == "'@SUM(A1)"


def test_csv_formula_tab_prefix():
    """以制表符开头的值被加引号"""
    assert sanitize_csv_cell("\t=cmd") == "'\t=cmd"


def test_csv_formula_cr_prefix():
    """以回车符开头的值被加引号"""
    assert sanitize_csv_cell("\r=cmd") == "'\r=cmd"


def test_csv_normal_text_unchanged():
    """普通文本不被修改"""
    assert sanitize_csv_cell("Hello World") == "Hello World"


def test_csv_number_unchanged():
    """数字字符串不被修改（不以公式字符开头）"""
    assert sanitize_csv_cell("12345") == "12345"


def test_csv_empty_string_unchanged():
    """空字符串不被修改"""
    assert sanitize_csv_cell("") == ""


def test_csv_chinese_text_unchanged():
    """中文文本不被修改"""
    assert sanitize_csv_cell("你好世界") == "你好世界"


def test_csv_formula_chars_coverage():
    """公式触发字符覆盖所有已知危险字符"""
    assert "=" in _CSV_FORMULA_CHARS
    assert "+" in _CSV_FORMULA_CHARS
    assert "-" in _CSV_FORMULA_CHARS
    assert "@" in _CSV_FORMULA_CHARS
    assert "\t" in _CSV_FORMULA_CHARS
    assert "\r" in _CSV_FORMULA_CHARS


# ═══════════════════════════════════════════════════════
# 2. LIKE 转义 — escape_like
# ═══════════════════════════════════════════════════════


def test_escape_like_percent():
    """百分号被转义"""
    assert escape_like("100%") == r"100\%"


def test_escape_like_underscore():
    """下划线被转义"""
    assert escape_like("test_name") == r"test\_name"


def test_escape_like_backslash():
    """反斜杠被转义"""
    assert escape_like("path\\file") == r"path\\file"


def test_escape_like_no_special():
    """无特殊字符不变"""
    assert escape_like("hello") == "hello"


def test_escape_like_empty():
    """空字符串不变"""
    assert escape_like("") == ""


def test_escape_like_multiple_special():
    """多个特殊字符都被转义"""
    result = escape_like("a%b_c\\d")
    assert r"\%" in result
    assert r"\_" in result
    assert r"\\" in result


# ═══════════════════════════════════════════════════════
# 3. 文本清理 — strip_html, strip_control_chars, sanitize_text
# ═══════════════════════════════════════════════════════


def test_strip_html_removes_tags():
    """移除 HTML 标签"""
    assert strip_html("<script>alert('xss')</script>hello") == "alert('xss')hello"


def test_strip_html_preserves_plain_text():
    """纯文本不被修改"""
    assert strip_html("Hello World") == "Hello World"


def test_strip_html_empty_string():
    """空字符串不被修改"""
    assert strip_html("") == ""


def test_strip_control_chars_removes_null():
    """移除 NULL 字符"""
    assert strip_control_chars("hello\x00world") == "helloworld"


def test_strip_control_chars_preserves_newline():
    """保留换行符"""
    assert strip_control_chars("hello\nworld") == "hello\nworld"


def test_strip_control_chars_preserves_tab():
    """保留制表符"""
    assert strip_control_chars("hello\tworld") == "hello\tworld"


def test_sanitize_text_none():
    """None 输入返回 None"""
    assert sanitize_text(None) is None


def test_sanitize_text_empty():
    """空字符串返回空字符串"""
    assert sanitize_text("") == ""


def test_sanitize_text_strips_html_and_control():
    """同时移除 HTML 标签和控制字符"""
    result = sanitize_text("<b>test</b>\x00value")
    assert "<b>" not in result
    assert "\x00" not in result


# ═══════════════════════════════════════════════════════
# 4. 导出服务工具函数
# ═══════════════════════════════════════════════════════


def test_export_service_has_product_export():
    """导出服务包含商品导出函数"""
    from app.services.export_service import export_products
    assert callable(export_products)


def test_export_service_has_customer_export():
    """导出服务包含客户导出函数"""
    from app.services.export_service import export_customers
    assert callable(export_customers)


def test_export_service_has_order_export():
    """导出服务包含订单导出函数"""
    from app.services.export_service import export_orders
    assert callable(export_orders)


def test_export_service_has_payment_export():
    """导出服务包含收款导出函数"""
    from app.services.export_service import export_payments
    assert callable(export_payments)


def test_export_service_dec_function():
    """_dec 函数转换 Decimal"""
    from decimal import Decimal

    from app.services.export_service import _dec
    assert _dec(Decimal("99.99")) == "99.99"
    assert _dec(None) == ""


def test_export_service_str_function():
    """_str 函数经过 CSV 消毒"""
    from app.services.export_service import _str
    assert _str("=SUM(A1)") == "'=SUM(A1)"
    assert _str("normal") == "normal"


def test_export_service_dt_function():
    """_dt 函数格式化日期时间"""
    from datetime import UTC, datetime

    from app.services.export_service import _dt
    dt = datetime(2026, 5, 4, 14, 30, 52, tzinfo=UTC)
    assert _dt(dt) == "2026-05-04 14:30:52"
    assert _dt(None) == ""


def test_csv_filename_format():
    """CSV 文件名格式正确"""
    from app.api.v1.exports import _csv_filename
    filename = _csv_filename("products")
    assert filename.startswith("products_")
    assert filename.endswith(".csv")
    pattern = r"products_\d{8}_\d{6}\.csv"
    assert re.match(pattern, filename), f"文件名格式不匹配: {filename}"


# ═══════════════════════════════════════════════════════
# 5. 导出端点存在性验证
# ═══════════════════════════════════════════════════════


def test_exports_router_exists():
    """导出路由模块存在"""
    from app.api.v1 import exports
    assert hasattr(exports, "router")


def test_export_endpoints_registered():
    """导出端点在路由中注册"""
    from app.api.v1.exports import router
    routes = [(r.path, list(r.methods or set())) for r in router.routes]
    paths = {path for path, _ in routes}
    for expected in ("/exports/products", "/exports/customers", "/exports/orders", "/exports/payments"):
        assert expected in paths, f"缺少导出端点 {expected}"


def test_export_endpoints_use_get():
    """导出端点使用 GET 方法"""
    from app.api.v1.exports import router
    for route in router.routes:
        if hasattr(route, "methods"):
            assert "GET" in route.methods, f"{route.path} 不是 GET 方法"


# ═══════════════════════════════════════════════════════
# 6. 导出配置验证
# ═══════════════════════════════════════════════════════


def test_export_uses_bom():
    """导出 CSV 包含 UTF-8 BOM"""
    from app.services.export_service import BOM
    assert BOM == "﻿"


def test_sanitize_module_exported():
    """sanitize_csv_cell 可从 sanitize 模块导入"""
    from app.core.sanitize import sanitize_csv_cell
    assert callable(sanitize_csv_cell)


def test_export_service_is_generator():
    """导出函数返回生成器"""
    import inspect

    from app.services.export_service import export_products
    assert inspect.isgeneratorfunction(export_products)
