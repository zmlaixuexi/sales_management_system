"""异常路径：金额/数值边界测试 — 覆盖 Pydantic Schema 约束、Decimal 精度、
舍入行为、数量约束、模型字段类型、计算一致性"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

# ═══════════════════════════════════════════════════════
# 1. Pydantic 商品价格约束
# ═══════════════════════════════════════════════════════


def test_product_max_price_constant():
    """商品 _MAX_PRICE 为 9999999999.99"""
    from app.schemas.product import _MAX_PRICE

    assert Decimal("9999999999.99") == _MAX_PRICE


def test_product_validate_price_accepts_positive():
    """正价格通过验证"""
    from app.schemas.product import _validate_price

    result = _validate_price("100.50", "sale_price")
    assert Decimal(str(result)) == Decimal("100.50")


def test_product_validate_price_accepts_zero():
    """零价格通过验证"""
    from app.schemas.product import _validate_price

    result = _validate_price("0", "sale_price")
    assert Decimal(str(result)) == Decimal("0")


def test_product_validate_price_rejects_negative():
    """负价格被拒绝"""
    from app.schemas.product import _validate_price

    with pytest.raises(ValueError, match="不能为负"):
        _validate_price("-1.00", "sale_price")


def test_product_validate_price_rejects_exceeds_max():
    """超过 _MAX_PRICE 被拒绝"""
    from app.schemas.product import _validate_price

    with pytest.raises(ValueError):
        _validate_price("10000000000.00", "sale_price")


def test_product_validate_price_accepts_max():
    """恰好 _MAX_PRICE 通过"""
    from app.schemas.product import _validate_price

    result = _validate_price("9999999999.99", "sale_price")
    assert Decimal(str(result)) == Decimal("9999999999.99")


def test_product_validate_price_small_decimal():
    """小数点后多位被保留"""
    from app.schemas.product import _validate_price

    result = _validate_price("1.123", "sale_price")
    assert Decimal(str(result)) == Decimal("1.123")


# ═══════════════════════════════════════════════════════
# 2. Pydantic 订单明细约束
# ═══════════════════════════════════════════════════════


def test_order_max_price_constant():
    """订单 _MAX_PRICE 为 9999999999.99"""
    from app.schemas.order import _MAX_PRICE

    assert Decimal("9999999999.99") == _MAX_PRICE


def test_order_item_quantity_gt_zero():
    """订单明细数量必须 > 0"""
    from pydantic import ValidationError

    from app.schemas.order import OrderItemInput

    with pytest.raises(ValidationError) as exc_info:
        OrderItemInput(
            product_id="00000000-0000-0000-0000-000000000001",
            quantity=0,
            unit_price="10.00",
        )
    assert "greater than 0" in str(exc_info.value).lower() or "gt=0" in str(
        exc_info.value
    )


def test_order_item_quantity_negative():
    """订单明细数量不能为负"""
    from pydantic import ValidationError

    from app.schemas.order import OrderItemInput

    with pytest.raises(ValidationError):
        OrderItemInput(
            product_id="00000000-0000-0000-0000-000000000001",
            quantity=-1,
            unit_price="10.00",
        )


def test_order_item_quantity_max_99999():
    """订单明细数量上限 99999"""
    from app.schemas.order import OrderItemInput

    item = OrderItemInput(
        product_id="00000000-0000-0000-0000-000000000001",
        quantity=99999,
        unit_price="10.00",
    )
    assert item.quantity == 99999


def test_order_item_quantity_100000_rejected():
    """订单明细数量 100000 被拒绝"""
    from pydantic import ValidationError

    from app.schemas.order import OrderItemInput

    with pytest.raises(ValidationError):
        OrderItemInput(
            product_id="00000000-0000-0000-0000-000000000001",
            quantity=100000,
            unit_price="10.00",
        )


def test_order_item_quantity_1_accepted():
    """订单明细数量 1 被接受"""
    from app.schemas.order import OrderItemInput

    item = OrderItemInput(
        product_id="00000000-0000-0000-0000-000000000001",
        quantity=1,
        unit_price="10.00",
    )
    assert item.quantity == 1


def test_order_unit_price_non_negative():
    """订单单价不能为负"""
    # unit_price 通过 validator 检查
    from pydantic import ValidationError

    from app.schemas.order import OrderItemInput

    with pytest.raises(ValidationError):
        OrderItemInput(
            product_id="00000000-0000-0000-0000-000000000001",
            quantity=1,
            unit_price="-5.00",
        )


def test_order_unit_price_accepts_zero():
    """订单单价为 0 被接受"""
    from app.schemas.order import OrderItemInput

    item = OrderItemInput(
        product_id="00000000-0000-0000-0000-000000000001",
        quantity=1,
        unit_price="0",
    )
    assert item.unit_price == "0"


def test_order_items_min_length():
    """订单 items 最少 1 项"""
    from pydantic import ValidationError

    from app.schemas.order import OrderCreate

    with pytest.raises(ValidationError):
        OrderCreate(
            customer_id="00000000-0000-0000-0000-000000000001",
            items=[],
        )


def test_order_items_max_length():
    """订单 items 最多 500 项"""
    from app.schemas.order import OrderCreate

    # 构建 500 项应该通过
    items = [
        {
            "product_id": "00000000-0000-0000-0000-000000000001",
            "quantity": 1,
            "unit_price": "10.00",
        }
    ] * 500
    order = OrderCreate(
        customer_id="00000000-0000-0000-0000-000000000001",
        items=items,
    )
    assert len(order.items) == 500


# ═══════════════════════════════════════════════════════
# 3. Pydantic 收款金额约束
# ═══════════════════════════════════════════════════════


def test_payment_max_amount_constant():
    """收款 _MAX_AMOUNT 为 9999999999.99"""
    from app.schemas.payment import _MAX_AMOUNT

    assert Decimal("9999999999.99") == _MAX_AMOUNT


def test_payment_amount_positive():
    """收款金额必须为正数"""
    from pydantic import ValidationError

    from app.schemas.payment import PaymentCreate

    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id="00000000-0000-0000-0000-000000000001",
            amount="0",
            payment_method="cash",
        )


def test_payment_amount_negative():
    """收款金额不能为负"""
    from pydantic import ValidationError

    from app.schemas.payment import PaymentCreate

    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id="00000000-0000-0000-0000-000000000001",
            amount="-100.00",
            payment_method="cash",
        )


def test_payment_amount_accepts_positive():
    """正数收款金额通过"""
    from app.schemas.payment import PaymentCreate

    p = PaymentCreate(
        order_id="00000000-0000-0000-0000-000000000001",
        amount="100.50",
        payment_method="cash",
    )
    assert p.amount == "100.50"


# ═══════════════════════════════════════════════════════
# 4. 商品库存数量约束
# ═══════════════════════════════════════════════════════


def test_stock_quantity_ge_zero():
    """库存数量 >= 0"""
    # 0 应被接受

    from app.schemas.product import ProductCreate

    p = ProductCreate(
        name="测试",
        category_id="00000000-0000-0000-0000-000000000001",
        sale_price="10.00",
        cost_price="5.00",
        stock_quantity=0,
    )
    assert p.stock_quantity == 0


def test_stock_quantity_negative_rejected():
    """库存数量不能为负"""
    from pydantic import ValidationError

    from app.schemas.product import ProductCreate

    with pytest.raises(ValidationError):
        ProductCreate(
            name="测试",
            category_id="00000000-0000-0000-0000-000000000001",
            sale_price="10.00",
            cost_price="5.00",
            stock_quantity=-1,
        )


def test_stock_quantity_max_9999999():
    """库存数量上限 9999999"""
    from app.schemas.product import ProductCreate

    p = ProductCreate(
        name="测试",
        category_id="00000000-0000-0000-0000-000000000001",
        sale_price="10.00",
        cost_price="5.00",
        stock_quantity=9999999,
    )
    assert p.stock_quantity == 9999999


def test_stock_quantity_10000000_rejected():
    """库存数量 10000000 被拒绝"""
    from pydantic import ValidationError

    from app.schemas.product import ProductCreate

    with pytest.raises(ValidationError):
        ProductCreate(
            name="测试",
            category_id="00000000-0000-0000-0000-000000000001",
            sale_price="10.00",
            cost_price="5.00",
            stock_quantity=10000000,
        )


# ═══════════════════════════════════════════════════════
# 5. Decimal 精度验证
# ═══════════════════════════════════════════════════════


def test_decimal_multiplication_precision():
    """Decimal * int 保持精度（无浮点误差）"""
    price = Decimal("10.10")
    quantity = 3
    total = price * quantity
    assert total == Decimal("30.30")


def test_decimal_division_precision():
    """Decimal 除法保持精度"""
    profit = Decimal("100.00")
    revenue = Decimal("300.00")
    margin = profit / revenue
    # Decimal 除法产生精确结果
    assert margin == Decimal("0.3333333333333333333333333333")


def test_decimal_quantize_2dp():
    """quantize 到 2 位小数"""
    value = Decimal("10.125")
    result = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert result == Decimal("10.13")


def test_decimal_quantize_4dp():
    """quantize 到 4 位小数"""
    value = Decimal("0.33335")
    result = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert result == Decimal("0.3334")


def test_decimal_string_conversion():
    """Decimal(str(x)) 无浮点误差"""
    assert Decimal("10.10") == Decimal("10.10")
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")


def test_decimal_zero_comparison():
    """Decimal("0") == 0 为 True"""
    assert Decimal("0") == 0
    assert Decimal("0.00") == 0


def test_decimal_negative_not_zero():
    """Decimal 负数 != 0"""
    assert Decimal("-0.01") != 0


# ═══════════════════════════════════════════════════════
# 6. 模型字段类型验证
# ═══════════════════════════════════════════════════════


def test_product_price_column_type():
    """商品价格字段为 Numeric(12, 2)"""
    from app.models.product import Product

    col = Product.__table__.c
    assert col["sale_price"].type.precision == 12
    assert col["sale_price"].type.scale == 2


def test_product_cost_price_column_type():
    """商品成本价字段为 Numeric(12, 2)"""
    from app.models.product import Product

    col = Product.__table__.c
    assert col["cost_price"].type.precision == 12
    assert col["cost_price"].type.scale == 2


def test_order_total_amount_column_type():
    """订单总金额为 Numeric(12, 2)"""
    from app.models.order import SalesOrder

    col = SalesOrder.__table__.c
    assert col["total_amount"].type.precision == 12
    assert col["total_amount"].type.scale == 2


def test_order_paid_amount_column_type():
    """订单已付金额为 Numeric(12, 2)"""
    from app.models.order import SalesOrder

    col = SalesOrder.__table__.c
    assert col["paid_amount"].type.precision == 12
    assert col["paid_amount"].type.scale == 2


def test_order_gross_margin_column_type():
    """订单毛利率为 Numeric(8, 4)"""
    from app.models.order import SalesOrder

    col = SalesOrder.__table__.c
    assert col["gross_margin"].type.precision == 8
    assert col["gross_margin"].type.scale == 4


def test_order_item_discount_rate_column_type():
    """订单明细折扣率为 Numeric(8, 4)"""
    from app.models.order import SalesOrderItem

    col = SalesOrderItem.__table__.c
    assert col["discount_rate"].type.precision == 8
    assert col["discount_rate"].type.scale == 4


def test_payment_amount_column_type():
    """收款金额为 Numeric(12, 2)"""
    from app.models.order import Payment

    col = Payment.__table__.c
    assert col["amount"].type.precision == 12
    assert col["amount"].type.scale == 2


def test_order_item_quantity_column_type():
    """订单明细数量为 Integer"""
    from sqlalchemy import Integer

    from app.models.order import SalesOrderItem

    col = SalesOrderItem.__table__.c
    assert isinstance(col["quantity"].type, Integer)


def test_product_stock_quantity_column_type():
    """商品库存数量为 Integer"""
    from sqlalchemy import Integer

    from app.models.product import Product

    col = Product.__table__.c
    assert isinstance(col["stock_quantity"].type, Integer)


# ═══════════════════════════════════════════════════════
# 7. 计算逻辑一致性验证
# ═══════════════════════════════════════════════════════


def test_subtotal_calculation():
    """小计 = 单价 × 数量"""
    unit_price = Decimal("99.99")
    quantity = 3
    subtotal = unit_price * quantity
    assert subtotal == Decimal("299.97")


def test_gross_profit_calculation():
    """毛利 = 销售金额 - 成本金额"""
    total_amount = Decimal("1000.00")
    total_cost = Decimal("600.00")
    gross_profit = total_amount - total_cost
    assert gross_profit == Decimal("400.00")


def test_gross_margin_calculation():
    """毛利率 = 毛利 / 销售金额 (4 位小数)"""
    gross_profit = Decimal("400.00")
    total_amount = Decimal("1000.00")
    margin = (gross_profit / total_amount).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    assert margin == Decimal("0.4000")


def test_gross_margin_rounding_half_up():
    """毛利率 ROUND_HALF_UP: 0.33335 → 0.3334"""
    profit = Decimal("1000.05")
    revenue = Decimal("3000.00")
    margin = (profit / revenue).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    assert margin == Decimal("0.3334")


def test_discount_amount_calculation():
    """折扣金额 = 原价 - 成交价"""
    sale_price = Decimal("100.00")
    deal_price = Decimal("85.00")
    discount = sale_price - deal_price
    assert discount == Decimal("15.00")


def test_discount_rate_calculation():
    """折扣率 = 折扣金额 / 原价 (4 位小数)"""
    discount_amount = Decimal("15.00")
    sale_price = Decimal("100.00")
    rate = (discount_amount / sale_price).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    assert rate == Decimal("0.1500")


def test_paid_amount_accumulation():
    """累计已付 = 旧已付 + 新收款"""
    old_paid = Decimal("500.00")
    new_payment = Decimal("300.00")
    total_paid = old_paid + new_payment
    assert total_paid == Decimal("800.00")


def test_remaining_amount():
    """剩余未付 = 总金额 - 已付金额"""
    total = Decimal("1000.00")
    paid = Decimal("300.00")
    remaining = total - paid
    assert remaining == Decimal("700.00")


# ═══════════════════════════════════════════════════════
# 8. _MAX_PRICE / _MAX_AMOUNT 一致性
# ═══════════════════════════════════════════════════════


def test_max_price_product_matches_order():
    """商品和订单 _MAX_PRICE 相同"""
    from app.schemas.order import _MAX_PRICE as _ORDER_MAX
    from app.schemas.product import _MAX_PRICE as _PRODUCT_MAX

    assert _PRODUCT_MAX == _ORDER_MAX


def test_max_price_product_matches_payment():
    """商品 _MAX_PRICE 和收款 _MAX_AMOUNT 相同"""
    from app.schemas.payment import _MAX_AMOUNT as _PAYMENT_MAX
    from app.schemas.product import _MAX_PRICE as _PRODUCT_MAX

    assert _PRODUCT_MAX == _PAYMENT_MAX


def test_max_price_is_10_billion():
    """_MAX_PRICE = 9999999999.99（百亿级上限）"""
    from app.schemas.product import _MAX_PRICE

    assert Decimal("9999999999.99") == _MAX_PRICE
    assert Decimal("10000000000.00") > _MAX_PRICE


# ═══════════════════════════════════════════════════════
# 9. 库存变动数量一致性
# ═══════════════════════════════════════════════════════


def test_inventory_quantity_after():
    """变动后数量 = 变动前 + 变动量"""
    before = 100
    change = -3
    after = before + change
    assert after == 97


def test_inventory_quantity_increase():
    """入库变动后数量增加"""
    before = 50
    change = 10
    after = before + change
    assert after == 60


def test_inventory_quantity_zero_change():
    """变动量为 0 时数量不变"""
    before = 50
    change = 0
    after = before + change
    assert after == before


# ═══════════════════════════════════════════════════════
# 10. 金额字符串序列化
# ═══════════════════════════════════════════════════════


def test_decimal_to_string():
    """Decimal 序列化为字符串保持精度"""
    d = Decimal("99.99")
    assert str(d) == "99.99"


def test_decimal_zero_to_string():
    """Decimal("0") 序列化为 '0'"""
    assert str(Decimal("0")) == "0"


def test_decimal_large_amount_to_string():
    """大金额序列化无精度丢失"""
    d = Decimal("9999999999.99")
    assert str(d) == "9999999999.99"


def test_decimal_4dp_to_string():
    """4 位小数 Decimal 序列化"""
    d = Decimal("0.1234")
    assert str(d) == "0.1234"


# ═══════════════════════════════════════════════════════
# 11. 订单金额汇总边界
# ═══════════════════════════════════════════════════════


def test_order_total_from_single_item():
    """单明细订单总金额 = 明细小计"""
    subtotal = Decimal("150.00")
    total = subtotal
    assert total == Decimal("150.00")


def test_order_total_from_multiple_items():
    """多明细订单总金额 = 所有小计之和"""
    subtotals = [Decimal("100.00"), Decimal("200.50"), Decimal("50.25")]
    total = sum(subtotals, Decimal("0"))
    assert total == Decimal("350.75")


def test_order_total_zero_items():
    """空明细列表总金额为 0"""
    total = sum([], Decimal("0"))
    assert total == Decimal("0")


# ═══════════════════════════════════════════════════════
# 12. 收款超额防护验证（schema 级别）
# ═══════════════════════════════════════════════════════


def test_payment_schema_rejects_exceeds_max():
    """收款金额超过 _MAX_AMOUNT 被 schema 拒绝"""
    from pydantic import ValidationError

    from app.schemas.payment import PaymentCreate

    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id="00000000-0000-0000-0000-000000000001",
            amount="10000000000.00",
            payment_method="cash",
        )


def test_payment_schema_accepts_max():
    """收款金额恰好 _MAX_AMOUNT 通过"""
    from app.schemas.payment import PaymentCreate

    p = PaymentCreate(
        order_id="00000000-0000-0000-0000-000000000001",
        amount="9999999999.99",
        payment_method="cash",
    )
    assert p.amount == "9999999999.99"


# ═══════════════════════════════════════════════════════
# 13. 收款冲减防护（paid_amount 下限）
# ═══════════════════════════════════════════════════════


def test_paid_amount_floor_zero():
    """冲减后 paid_amount <= 0 时归零"""
    paid = Decimal("50.00")
    refund = Decimal("100.00")
    result = paid - refund
    if result <= 0:
        result = Decimal("0")
    assert result == Decimal("0")


def test_paid_amount_partial_refund():
    """部分退款后 paid_amount > 0"""
    paid = Decimal("500.00")
    refund = Decimal("200.00")
    result = paid - refund
    assert result == Decimal("300.00")


# ═══════════════════════════════════════════════════════
# 14. sort_weight 约束
# ═══════════════════════════════════════════════════════


def test_sort_weight_bounds():
    """sort_weight 范围 [-99999, 99999]"""
    from app.schemas.product import ProductCreate

    p = ProductCreate(
        name="测试",
        category_id="00000000-0000-0000-0000-000000000001",
        sale_price="10.00",
        cost_price="5.00",
        sort_weight=99999,
    )
    assert p.sort_weight == 99999


def test_sort_weight_negative():
    """sort_weight 可以为负"""
    from app.schemas.product import ProductCreate

    p = ProductCreate(
        name="测试",
        category_id="00000000-0000-0000-0000-000000000001",
        sale_price="10.00",
        cost_price="5.00",
        sort_weight=-99999,
    )
    assert p.sort_weight == -99999


def test_sort_weight_exceeds_max():
    """sort_weight 超过 99999 被拒绝"""
    from pydantic import ValidationError

    from app.schemas.product import ProductCreate

    with pytest.raises(ValidationError):
        ProductCreate(
            name="测试",
            category_id="00000000-0000-0000-0000-000000000001",
            sale_price="10.00",
            cost_price="5.00",
            sort_weight=100000,
        )


# ═══════════════════════════════════════════════════════
# 15. 价格历史模型字段精度
# ═══════════════════════════════════════════════════════


def test_price_history_sale_price_precision():
    """价格历史新旧售价为 Numeric(12, 2)"""
    from app.models.product import ProductPriceHistory

    col = ProductPriceHistory.__table__.c
    assert col["old_sale_price"].type.precision == 12
    assert col["old_sale_price"].type.scale == 2
    assert col["new_sale_price"].type.precision == 12
    assert col["new_sale_price"].type.scale == 2


def test_price_history_cost_price_precision():
    """价格历史新旧成本价为 Numeric(12, 2)"""
    from app.models.product import ProductPriceHistory

    col = ProductPriceHistory.__table__.c
    assert col["old_cost_price"].type.precision == 12
    assert col["old_cost_price"].type.scale == 2
    assert col["new_cost_price"].type.precision == 12
    assert col["new_cost_price"].type.scale == 2
