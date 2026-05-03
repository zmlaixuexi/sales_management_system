"""导出服务辅助函数单元测试 — _dec / _str / _dt / 行构建函数"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.export_service import (
    ORDER_HEADERS,
    ORDER_HEADERS_NO_COST,
    PRODUCT_HEADERS,
    PRODUCT_HEADERS_NO_COST,
    _customer_row,
    _dec,
    _dt,
    _order_row,
    _payment_row,
    _product_row,
    _str,
)

# ─── _dec ──────────────────────────────────────────────────


def test_dec_none():
    assert _dec(None) == ""


def test_dec_value():
    assert _dec(Decimal("123.45")) == "123.45"


def test_dec_zero():
    assert _dec(Decimal("0")) == "0"


def test_dec_negative():
    assert _dec(Decimal("-10.50")) == "-10.50"


# ─── _str ──────────────────────────────────────────────────


def test_str_none():
    assert _str(None) == ""


def test_str_value():
    assert _str("hello") == "hello"


def test_str_number():
    assert _str(42) == "42"


def test_str_empty():
    assert _str("") == ""


# ─── _dt ───────────────────────────────────────────────────


def test_dt_none():
    assert _dt(None) == ""


def test_dt_iso_format():
    result = _dt("2026-04-30T12:34:56.789")
    assert result == "2026-04-30 12:34:56"


def test_dt_datetime_object():
    result = _dt(datetime(2026, 4, 30, 12, 34, 56))
    assert result == "2026-04-30 12:34:56"


def test_dt_already_formatted():
    result = _dt("2026-04-30 12:34:56")
    assert result == "2026-04-30 12:34:56"


def test_dt_short_string():
    result = _dt("2026-04-30")
    assert result == "2026-04-30"


# ─── _product_row ───────────────────────────────────────────


def _mock_product(**kwargs):
    p = MagicMock(spec=[])
    p.sku = kwargs.get("sku", "SKU-001")
    p.name = kwargs.get("name", "测试商品")
    p.sale_price = kwargs.get("sale_price", Decimal("100.00"))
    p.cost_price = kwargs.get("cost_price", Decimal("60.00"))
    p.stock_quantity = kwargs.get("stock_quantity", 10)
    p.status = kwargs.get("status", "active")
    p.category = kwargs.get("category")
    p.remark = kwargs.get("remark", "")
    p.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 10, 0, 0))
    return p


def test_product_row_with_cost():
    """有成本权限时包含成本价"""
    row = _product_row(_mock_product(), can_view_cost=True)
    assert row[3] == "60.00"  # 成本价
    assert len(row) == len(PRODUCT_HEADERS)


def test_product_row_without_cost():
    """无成本权限时不含成本价"""
    row = _product_row(_mock_product(), can_view_cost=False)
    assert len(row) == len(PRODUCT_HEADERS_NO_COST)
    # 确保成本价不在行中
    assert "60.00" not in row


def test_product_row_status_map():
    """状态映射为中文"""
    for status, label in [("active", "上架"), ("inactive", "下架"), ("disabled", "停用")]:
        row = _product_row(_mock_product(status=status))
        assert label in row


# ─── _order_row ──────────────────────────────────────────────


def _mock_order(**kwargs):
    o = MagicMock(spec=[])
    o.order_no = kwargs.get("order_no", "ORD20260501-0001")
    o.customer_id = kwargs.get("customer_id", "cust-1")
    o.status = kwargs.get("status", "confirmed")
    o.total_amount = kwargs.get("total_amount", Decimal("500.00"))
    o.total_cost = kwargs.get("total_cost", Decimal("300.00"))
    o.gross_profit = kwargs.get("gross_profit", Decimal("200.00"))
    o.gross_margin = kwargs.get("gross_margin", Decimal("0.4000"))
    o.paid_amount = kwargs.get("paid_amount", Decimal("0"))
    o.items = kwargs.get("items", [MagicMock()])
    o.remark = kwargs.get("remark", "")
    o.created_at = kwargs.get("created_at", datetime(2026, 5, 1, 10, 0, 0))
    return o


def test_order_row_with_cost():
    """有成本权限时包含成本/毛利/毛利率"""
    row = _order_row(_mock_order(), can_view_cost=True)
    assert row[4] == "300.00"  # 成本
    assert row[5] == "200.00"  # 毛利
    assert len(row) == len(ORDER_HEADERS)


def test_order_row_without_cost():
    """无成本权限时不含成本/毛利/毛利率"""
    row = _order_row(_mock_order(), can_view_cost=False)
    assert len(row) == len(ORDER_HEADERS_NO_COST)
    assert "300.00" not in row


def test_order_row_status_map():
    """订单状态映射"""
    for status, label in [("draft", "草稿"), ("confirmed", "已确认"), ("cancelled", "已取消"),
                          ("partially_paid", "部分收款"), ("completed", "已完成")]:
        row = _order_row(_mock_order(status=status))
        assert label in row


# ─── _customer_row ──────────────────────────────────────────


def test_customer_row_basic():
    """客户行包含所有字段"""
    c = MagicMock(spec=[])
    c.name = "测试客户"
    c.contact_name = "张三"
    c.phone = "13800138000"
    c.email = "test@example.com"
    c.source = "线上"
    c.level = "A"
    c.owner = None
    c.follow_status = "跟进中"
    c.remark = ""
    c.created_at = datetime(2026, 5, 1)
    row = _customer_row(c)
    assert row[0] == "测试客户"
    assert row[2] == "13800138000"
    assert row[6] == ""  # 无归属销售


# ─── _payment_row ────────────────────────────────────────────


def test_payment_row_normal_status():
    # 正常收款状态显示"正常"
    p = MagicMock(spec=[])
    p.id = "pay-1"
    p.order_id = "ord-1"
    p.amount = Decimal("100.00")
    p.payment_method = "微信"
    p.status = "normal"
    p.paid_at = None
    p.remark = ""
    p.created_at = datetime(2026, 5, 1)
    row = _payment_row(p)
    assert row[4] == "正常"


def test_payment_row_reversed_status():
    # 冲正状态显示"已冲正"
    p = MagicMock(spec=[])
    p.id = "pay-1"
    p.order_id = "ord-1"
    p.amount = Decimal("100.00")
    p.payment_method = "微信"
    p.status = "reversed"
    p.paid_at = None
    p.remark = ""
    p.created_at = datetime(2026, 5, 1)
    row = _payment_row(p)
    assert row[4] == "已冲正"


# ─── CSV 公式注入防护 ─────────────────────────────────────────


def test_str_sanitizes_formula_equals():
    """以 = 开头的值应被转义"""
    assert _str("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_str_sanitizes_formula_plus():
    """以 + 开头的值应被转义"""
    assert _str("+cmd|'/C calc'!A0") == "'+cmd|'/C calc'!A0"


def test_str_sanitizes_formula_minus():
    """以 - 开头的值应被转义"""
    assert _str("-1+1|cmd") == "'-1+1|cmd"


def test_str_sanitizes_formula_at():
    """以 @ 开头的值应被转义"""
    assert _str("@SUM(A1)") == "'@SUM(A1)"


def test_str_sanitizes_formula_tab():
    """以 \\t 开头的值应被转义"""
    assert _str("\t=cmd") == "'\t=cmd"


def test_str_sanitizes_formula_carriage_return():
    """以 \\r 开头的值应被转义"""
    assert _str("\rcmd") == "'\rcmd"


def test_str_normal_text_not_modified():
    """普通文本不应被转义"""
    assert _str("正常商品名称") == "正常商品名称"


def test_str_formula_midstring_not_modified():
    """公式字符在字符串中间不应被转义"""
    assert _str("价格=100") == "价格=100"


def test_product_row_formula_name_sanitized():
    """商品名称含公式注入时应被转义"""
    p = _mock_product(name="=CMD|'/C calc'!A0")
    row = _product_row(p, can_view_cost=False)
    assert row[1] == "'=CMD|'/C calc'!A0"


def test_customer_row_formula_phone_sanitized():
    """客户电话含公式注入时应被转义"""
    c = MagicMock(spec=[])
    c.name = "正常客户"
    c.contact_name = ""
    c.phone = "+1-555-0123"
    c.email = ""
    c.source = ""
    c.level = ""
    c.owner = None
    c.follow_status = ""
    c.remark = ""
    c.created_at = datetime(2026, 5, 1)
    row = _customer_row(c)
    assert row[2] == "'+1-555-0123"


def test_order_row_formula_remark_sanitized():
    """订单备注含公式注入时应被转义"""
    o = _mock_order(remark="=HYPERLINK(\"http://evil.com\",\"点击\")")
    row = _order_row(o, can_view_cost=False)
    # remark is the second-to-last field (before created_at)
    assert "'=HYPERLINK" in row[-2]


# ─── 边界条件测试 ──────────────────────────────────────────────


# _dec 边界


def test_dec_very_large_precision():
    """超高精度 Decimal 保留原始精度"""
    result = _dec(Decimal("123456789.123456789"))
    assert "123456789.123456789" in result


def test_dec_very_large_value():
    """超大金额值正确输出"""
    result = _dec(Decimal("999999999999.99"))
    assert result == "999999999999.99"


# _str 边界


def test_str_unicode_emoji():
    """emoji 和 Unicode 字符原样输出"""
    assert _str("🎉特价商品🚀") == "🎉特价商品🚀"


def test_str_very_long_value():
    """超长字符串原样输出"""
    long_val = "A" * 5000
    assert _str(long_val) == long_val
    assert len(_str(long_val)) == 5000


def test_str_whitespace_only():
    """纯空白字符串原样输出"""
    assert _str("   ") == "   "


def test_str_newline_in_value():
    """含换行的字符串原样输出（CSV writer 会加引号）"""
    assert _str("第一行\n第二行") == "第一行\n第二行"


def test_str_comma_in_value():
    """含逗号的字符串原样输出（CSV writer 会加引号）"""
    assert _str("含,逗号") == "含,逗号"


def test_str_quote_in_value():
    """含双引号的字符串原样输出"""
    assert _str('含"引号') == '含"引号'


# _dt 边界


def test_dt_timezone_aware():
    """时区感知 datetime 转为本地时间字符串"""
    dt = datetime(2026, 5, 1, 8, 30, 0, tzinfo=UTC)
    result = _dt(dt)
    assert "2026-05-01" in result
    assert "08:30:00" in result


def test_dt_microseconds_truncated():
    """微秒部分被截断"""
    result = _dt("2026-05-01T10:30:45.123456")
    assert result == "2026-05-01 10:30:45"


def test_dt_very_old_date():
    """很早的日期能正确输出"""
    result = _dt(datetime(2000, 1, 1, 0, 0, 0))
    assert result == "2000-01-01 00:00:00"


# _product_row 边界


def test_product_row_no_category():
    """无分类时显示'未分类'"""
    p = _mock_product(category=None)
    row = _product_row(p)
    assert "未分类" in row


def test_product_row_unknown_status():
    """未知状态使用原始值"""
    p = _mock_product(status="pending_review")
    row = _product_row(p)
    assert "pending_review" in row


def test_product_row_none_remark():
    """备注为 None 时输出空字符串"""
    p = _mock_product(remark=None)
    row = _product_row(p)
    remark_idx = PRODUCT_HEADERS.index("备注")
    assert row[remark_idx] == ""


def test_product_row_none_stock():
    """库存为 None 时输出 0"""
    p = _mock_product(stock_quantity=None)
    row = _product_row(p)
    stock_idx = PRODUCT_HEADERS.index("库存")
    assert row[stock_idx] == "0"


def test_product_row_zero_prices():
    """所有价格为零时正确输出"""
    p = _mock_product(sale_price=Decimal("0"), cost_price=Decimal("0"))
    row = _product_row(p)
    assert "0" in row


# _order_row 边界


def test_order_row_empty_items():
    """订单无明细时输出 0"""
    o = _mock_order(items=[])
    row = _order_row(o, can_view_cost=True)
    assert "0" in row


def test_order_row_many_items():
    """订单含多个明细时输出正确数量"""
    items = [MagicMock() for _ in range(10)]
    o = _mock_order(items=items)
    row = _order_row(o, can_view_cost=True)
    assert "10" in row


def test_order_row_unknown_status():
    """未知订单状态使用原始值"""
    o = _mock_order(status="pending")
    row = _order_row(o)
    assert "pending" in row


def test_order_row_none_remark():
    """订单备注为 None 时输出空字符串"""
    o = _mock_order(remark=None)
    row = _order_row(o, can_view_cost=False)
    remark_idx = ORDER_HEADERS_NO_COST.index("备注")
    assert row[remark_idx] == ""


# _customer_row 边界


def test_customer_row_all_empty_fields():
    """所有可选字段为空时行构建正常"""
    c = MagicMock(spec=[])
    c.name = "最小客户"
    c.contact_name = None
    c.phone = None
    c.email = None
    c.source = None
    c.level = None
    c.owner = None
    c.follow_status = None
    c.remark = None
    c.created_at = None
    row = _customer_row(c)
    assert row[0] == "最小客户"
    # 其余字段应为空字符串
    assert row[1] == ""  # contact_name
    assert row[2] == ""  # phone
    assert row[9] == ""  # created_at


# _payment_row 边界


def test_payment_row_unknown_status():
    """未知支付状态使用原始逻辑（非 normal 即显示'已冲正'）"""
    p = MagicMock(spec=[])
    p.id = "pay-x"
    p.order_id = "ord-x"
    p.amount = Decimal("50")
    p.payment_method = "现金"
    p.status = "pending"
    p.paid_at = None
    p.remark = ""
    p.created_at = datetime(2026, 5, 1)
    row = _payment_row(p)
    # 非 "normal" 都显示 "已冲正"
    assert row[4] == "已冲正"


def test_payment_row_none_paid_at():
    """收款时间为空时输出空字符串"""
    p = MagicMock(spec=[])
    p.id = "pay-1"
    p.order_id = "ord-1"
    p.amount = Decimal("100")
    p.payment_method = "微信"
    p.status = "normal"
    p.paid_at = None
    p.remark = None
    p.created_at = None
    row = _payment_row(p)
    assert row[5] == ""  # paid_at
    assert row[7] == ""  # created_at
