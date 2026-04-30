"""商品利润计算函数单元测试 — _calc_profit"""

from decimal import Decimal

from app.api.v1.products import _calc_profit


def test_calc_profit_basic():
    """基本利润计算"""
    profit, margin = _calc_profit(Decimal("100"), Decimal("60"))
    assert profit == Decimal("40")
    assert margin == Decimal("0.4000")


def test_calc_profit_zero_sale_price():
    """售价为零时毛利率为零（除零保护）"""
    profit, margin = _calc_profit(Decimal("0"), Decimal("60"))
    assert profit == Decimal("-60")
    assert margin == Decimal("0")


def test_calc_profit_loss():
    """成本高于售价时利润为负"""
    profit, margin = _calc_profit(Decimal("50"), Decimal("80"))
    assert profit == Decimal("-30")
    assert margin == Decimal("-0.6000")


def test_calc_profit_equal_prices():
    """售价等于成本时利润为零"""
    profit, margin = _calc_profit(Decimal("100"), Decimal("100"))
    assert profit == Decimal("0")
    assert margin == Decimal("0.0000")


def test_calc_profit_margin_precision():
    """毛利率精度为 4 位小数"""
    profit, margin = _calc_profit(Decimal("99.99"), Decimal("33.33"))
    assert profit == Decimal("66.66")
    assert margin == (Decimal("66.66") / Decimal("99.99")).quantize(Decimal("0.0001"))


def test_calc_profit_high_margin():
    """高毛利率场景"""
    profit, margin = _calc_profit(Decimal("1000"), Decimal("1"))
    assert profit == Decimal("999")
    assert margin == Decimal("0.9990")
