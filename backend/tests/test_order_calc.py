"""订单金额计算函数单元测试 — _calc_order_totals / _prepare_item"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from app.api.v1.orders import _calc_order_totals, _prepare_item  # noqa: I001

# ─── _calc_order_totals ─────────────────────────────────────


def test_calc_totals_basic():
    """基本金额计算"""
    items = [
        {"subtotal_amount": "100.00", "subtotal_cost": "60.00"},
        {"subtotal_amount": "200.00", "subtotal_cost": "120.00"},
    ]
    result = _calc_order_totals(items)
    assert result["total_amount"] == Decimal("300.00")
    assert result["total_cost"] == Decimal("180.00")
    assert result["gross_profit"] == Decimal("120.00")
    assert result["gross_margin"] == Decimal("0.4000")


def test_calc_totals_zero_amount():
    """总金额为零时毛利率为零"""
    items = [
        {"subtotal_amount": "0", "subtotal_cost": "0"},
    ]
    result = _calc_order_totals(items)
    assert result["total_amount"] == Decimal("0")
    assert result["gross_profit"] == Decimal("0")
    assert result["gross_margin"] == Decimal("0")


def test_calc_totals_empty_items():
    """空明细列表"""
    result = _calc_order_totals([])
    assert result["total_amount"] == Decimal("0")
    assert result["total_cost"] == Decimal("0")
    assert result["gross_profit"] == Decimal("0")
    assert result["gross_margin"] == Decimal("0")


def test_calc_totals_margin_rounding():
    """毛利率精度为 4 位小数"""
    items = [
        {"subtotal_amount": "99.99", "subtotal_cost": "33.33"},
    ]
    result = _calc_order_totals(items)
    profit = Decimal("99.99") - Decimal("33.33")
    expected_margin = (profit / Decimal("99.99")).quantize(Decimal("0.0001"))
    assert result["gross_margin"] == expected_margin
    assert result["gross_profit"] == profit


def test_calc_totals_missing_fields_default_zero():
    """缺失字段默认为零"""
    items = [{}]
    result = _calc_order_totals(items)
    assert result["total_amount"] == Decimal("0")
    assert result["total_cost"] == Decimal("0")


# ─── _prepare_item ──────────────────────────────────────────


def _mock_product(*, sale_price="100.00", cost_price="60.00", sku="SKU-001", name="测试商品"):
    p = MagicMock(spec=[])
    p.id = uuid.uuid4()
    p.sku = sku
    p.name = name
    p.main_image_url = "https://example.com/img.jpg"
    p.sale_price = Decimal(sale_price)
    p.cost_price = Decimal(cost_price)
    return p


def test_prepare_item_default_price():
    """未指定单价时使用商品售价"""
    p = _mock_product()
    result = _prepare_item(p, 3)
    assert result["unit_price"] == Decimal("100.00")
    assert result["subtotal_amount"] == Decimal("300.00")
    assert result["subtotal_cost"] == Decimal("180.00")
    assert result["discount_amount"] == Decimal("0")
    assert result["discount_rate"] == Decimal("0")


def test_prepare_item_custom_price():
    """指定成交单价时计算折扣"""
    p = _mock_product(sale_price="100.00")
    result = _prepare_item(p, 2, unit_price=Decimal("80.00"))
    assert result["unit_price"] == Decimal("80.00")
    assert result["discount_amount"] == Decimal("20.00")
    assert result["subtotal_amount"] == Decimal("160.00")


def test_prepare_item_zero_sale_price():
    """售价为零时折扣率不为零且不除零"""
    p = _mock_product(sale_price="0")
    result = _prepare_item(p, 1)
    assert result["discount_rate"] == Decimal("0")
    assert result["subtotal_amount"] == Decimal("0")


def test_prepare_item_snapshots():
    """快照字段正确记录"""
    p = _mock_product()
    result = _prepare_item(p, 5)
    assert result["product_id"] == p.id
    assert result["product_sku_snapshot"] == "SKU-001"
    assert result["product_name_snapshot"] == "测试商品"
    assert result["product_image_url_snapshot"] == "https://example.com/img.jpg"
    assert result["cost_price_snapshot"] == Decimal("60.00")
    assert result["quantity"] == 5
