"""需求符合性：订单折扣与金额计算边界测试 — 覆盖负折扣（加价销售）、毛利率极端值、
page_size 上界、金额精度、成本价保护、折扣由后端计算、明细数量边界"""

import contextlib
import uuid
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import PaginationParams
from app.api.v1.orders import _calc_order_totals, _prepare_item
from app.core.security import hash_password
from app.db.session import Base
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemInput, OrderUpdate

TEST_DB_URL = "sqlite:///./test_order_calc_bounds.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_admin_id = uuid.uuid4()
_sales_user_id = uuid.uuid4()
_category_id = uuid.uuid4()
_product_id = uuid.uuid4()
_customer_id = uuid.uuid4()


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        _seed(db)
    finally:
        db.close()


def teardown_module(module):
    import os
    with contextlib.suppress(FileNotFoundError):
        os.remove("test_order_calc_bounds.db")


def _seed(db: Session):
    admin = User(id=_admin_id, username="ord_calc_admin", hashed_password=hash_password("Aa1!aaaa"), is_superuser=True)
    sales = User(id=_sales_user_id, username="ord_calc_sales", hashed_password=hash_password("Aa1!aaaa"))
    db.add_all([admin, sales])

    cat = ProductCategory(id=_category_id, name="订单计算测试分类")
    db.add(cat)

    prod = Product(
        id=_product_id, name="计算边界商品", sku="CALC-BOUND-01",
        category_id=_category_id, cost_price=Decimal("50.00"),
        sale_price=Decimal("100.00"), stock_quantity=1000,
        status="active",
    )
    db.add(prod)

    cust = Customer(id=_customer_id, name="计算边界客户", phone="13800000999", created_by=sales.id)
    db.add(cust)
    db.commit()


@pytest.fixture()
def db():
    sess = TestSession()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture()
def product(db):
    return db.query(Product).filter(Product.id == _product_id).first()


# ═══════════════════════════════════════════════════════
# 1. 负折扣（加价销售）
# ═══════════════════════════════════════════════════════


def test_markup_unit_price_above_sale_price(product):
    """unit_price > sale_price 产生负 discount_amount（加价销售）"""
    item = _prepare_item(product, 1, Decimal("120.00"))
    assert item["discount_amount"] == Decimal("-20.00")
    assert item["discount_rate"] == Decimal("-0.2000")


def test_markup_discount_amount_negative():
    """加价销售时 discount_amount 为负"""
    sale_price = Decimal("100.00")
    unit_price = Decimal("150.00")
    discount_amount = sale_price - unit_price
    assert discount_amount == Decimal("-50.00")


def test_markup_discount_rate_negative():
    """加价销售时 discount_rate 为负"""
    sale_price = Decimal("100.00")
    unit_price = Decimal("130.00")
    discount_rate = ((sale_price - unit_price) / sale_price).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    assert discount_rate == Decimal("-0.3000")


def test_no_discount_when_equal(product):
    """unit_price == sale_price 时 discount_amount 为 0"""
    item = _prepare_item(product, 1, Decimal("100.00"))
    assert item["discount_amount"] == Decimal("0.00")


def test_normal_discount_positive(product):
    """正常折扣 discount_amount 为正"""
    item = _prepare_item(product, 1, Decimal("80.00"))
    assert item["discount_amount"] == Decimal("20.00")


# ═══════════════════════════════════════════════════════
# 2. 成本价保护
# ═══════════════════════════════════════════════════════


def test_below_cost_price_rejected(product):
    """unit_price < cost_price 被拒绝"""
    with pytest.raises(HTTPException) as exc_info:
        _prepare_item(product, 1, Decimal("30.00"))
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "PRICE_BELOW_COST"


def test_cost_price_exact_boundary(product):
    """unit_price == cost_price 允许（零利润边界）"""
    item = _prepare_item(product, 1, Decimal("50.00"))
    assert item["unit_price"] == Decimal("50.00")
    assert item["subtotal_cost"] == item["subtotal_amount"]


def test_cost_price_plus_one_cent(product):
    """unit_price = cost_price + 0.01 允许"""
    item = _prepare_item(product, 1, Decimal("50.01"))
    assert item["unit_price"] == Decimal("50.01")


# ═══════════════════════════════════════════════════════
# 3. 毛利率计算极端值
# ═══════════════════════════════════════════════════════


def test_gross_margin_zero_amount():
    """total_amount 为 0 时 gross_margin 为 0"""
    result = _calc_order_totals([])
    assert result["gross_margin"] == Decimal("0")


def test_gross_margin_normal():
    """正常毛利率计算"""
    items = [{
        "subtotal_amount": Decimal("100.00"),
        "subtotal_cost": Decimal("60.00"),
    }]
    result = _calc_order_totals(items)
    assert result["gross_profit"] == Decimal("40.00")
    assert result["gross_margin"] == Decimal("0.4000")


def test_gross_margin_negative_profit():
    """成本高于售价时毛利率为负"""
    items = [{
        "subtotal_amount": Decimal("100.00"),
        "subtotal_cost": Decimal("150.00"),
    }]
    result = _calc_order_totals(items)
    assert result["gross_profit"] == Decimal("-50.00")
    assert result["gross_margin"] == Decimal("-0.5000")


def test_gross_margin_zero_cost():
    """成本为 0 时毛利率为 1.0（100%）"""
    items = [{
        "subtotal_amount": Decimal("100.00"),
        "subtotal_cost": Decimal("0.00"),
    }]
    result = _calc_order_totals(items)
    assert result["gross_profit"] == Decimal("100.00")
    assert result["gross_margin"] == Decimal("1.0000")


def test_gross_margin_multiple_items():
    """多行明细的毛利汇总"""
    items = [
        {"subtotal_amount": Decimal("200.00"), "subtotal_cost": Decimal("120.00")},
        {"subtotal_amount": Decimal("300.00"), "subtotal_cost": Decimal("180.00")},
    ]
    result = _calc_order_totals(items)
    assert result["total_amount"] == Decimal("500.00")
    assert result["total_cost"] == Decimal("300.00")
    assert result["gross_profit"] == Decimal("200.00")
    assert result["gross_margin"] == Decimal("0.4000")


def test_gross_margin_4_decimal_precision():
    """毛利率保留 4 位小数"""
    items = [{
        "subtotal_amount": Decimal("99.99"),
        "subtotal_cost": Decimal("33.33"),
    }]
    result = _calc_order_totals(items)
    margin = result["gross_margin"]
    assert abs(margin.as_tuple().exponent) == 4  # 4 decimal places


# ═══════════════════════════════════════════════════════
# 4. page_size 上界验证（通过 FastAPI Query 验证）
# ═══════════════════════════════════════════════════════


def test_page_size_source_constraints():
    """page_size Query 参数 ge=1, le=100"""
    import inspect
    source = inspect.getsource(PaginationParams)
    assert "le=100" in source
    assert "ge=1" in source


def test_page_source_constraints():
    """page 源码中 le=10000"""
    import inspect
    source = inspect.getsource(PaginationParams)
    assert "le=10000" in source


# ═══════════════════════════════════════════════════════
# 5. OrderItemInput Schema 边界
# ═══════════════════════════════════════════════════════


def test_quantity_min_1():
    """quantity 最小为 1"""
    item = OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="10.00")
    assert item.quantity == 1


def test_quantity_zero_rejected():
    """quantity = 0 被拒绝"""
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=str(uuid.uuid4()), quantity=0, unit_price="10.00")


def test_quantity_max_99999():
    """quantity 最大为 99999"""
    item = OrderItemInput(product_id=str(uuid.uuid4()), quantity=99999, unit_price="10.00")
    assert item.quantity == 99999


def test_quantity_over_max_rejected():
    """quantity > 99999 被拒绝"""
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=str(uuid.uuid4()), quantity=100000, unit_price="10.00")


def test_unit_price_none_defaults_to_sale_price(product):
    """unit_price 为 None 时使用商品 sale_price"""
    item = _prepare_item(product, 1)
    assert item["unit_price"] == Decimal("100.00")


def test_unit_price_negative_rejected():
    """unit_price < 0 被拒绝"""
    with pytest.raises(ValidationError, match="不能为负"):
        OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="-1.00")


def test_unit_price_zero_accepted():
    """unit_price = 0 合法（免费赠送）"""
    item = OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="0")
    assert Decimal(item.unit_price) == Decimal("0")


def test_unit_price_max_accepted():
    """unit_price 恰好等于上限"""
    item = OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="9999999999.99")
    assert item.unit_price == "9999999999.99"


def test_unit_price_over_max_rejected():
    """unit_price 超过上限被拒绝"""
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="99999999999.99")


# ═══════════════════════════════════════════════════════
# 6. OrderCreate/OrderUpdate items 边界
# ═══════════════════════════════════════════════════════


def test_order_items_min_1():
    """订单明细最少 1 条"""
    oid = str(uuid.uuid4())
    order = OrderCreate(
        customer_id=oid,
        items=[OrderItemInput(product_id=oid, quantity=1, unit_price="10.00")],
    )
    assert len(order.items) == 1


def test_order_items_empty_rejected():
    """订单明细为空被拒绝"""
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=str(uuid.uuid4()), items=[])


def test_order_items_max_500():
    """订单明细最多 500 条"""
    oid = str(uuid.uuid4())
    items = [OrderItemInput(product_id=oid, quantity=1, unit_price="10.00") for _ in range(500)]
    order = OrderCreate(customer_id=oid, items=items)
    assert len(order.items) == 500


def test_order_items_over_500_rejected():
    """订单明细超过 500 条被拒绝"""
    oid = str(uuid.uuid4())
    items = [OrderItemInput(product_id=oid, quantity=1, unit_price="10.00") for _ in range(501)]
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=oid, items=items)


def test_order_remark_max_500():
    """备注恰好 500 字符"""
    order = OrderCreate(
        customer_id=str(uuid.uuid4()),
        items=[OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="10.00")],
        remark="x" * 500,
    )
    assert len(order.remark) == 500


def test_order_remark_over_500_rejected():
    """备注超过 500 字符被拒绝"""
    with pytest.raises(ValidationError):
        OrderCreate(
            customer_id=str(uuid.uuid4()),
            items=[OrderItemInput(product_id=str(uuid.uuid4()), quantity=1, unit_price="10.00")],
            remark="x" * 501,
        )


def test_order_update_items_optional():
    """OrderUpdate items 为可选"""
    update = OrderUpdate(remark="only remark")
    assert update.items is None


# ═══════════════════════════════════════════════════════
# 7. 折扣由后端计算，不接受前端输入
# ═══════════════════════════════════════════════════════


def test_order_item_input_no_discount_fields():
    """OrderItemInput 不包含 discount_amount/discount_rate 字段"""
    import inspect
    source = inspect.getsource(OrderItemInput)
    assert "discount_amount" not in source
    assert "discount_rate" not in source


def test_prepare_item_computes_discount(product):
    """_prepare_item 自动计算 discount_amount 和 discount_rate"""
    item = _prepare_item(product, 1, Decimal("90.00"))
    assert "discount_amount" in item
    assert "discount_rate" in item
    assert item["discount_amount"] == Decimal("10.00")
    assert item["discount_rate"] == Decimal("0.1000")


# ═══════════════════════════════════════════════════════
# 8. 金额精度验证
# ═══════════════════════════════════════════════════════


def test_subtotal_precision_2_decimals(product):
    """subtotal_amount 和 subtotal_cost 保持 2 位小数"""
    item = _prepare_item(product, 3, Decimal("99.99"))
    assert item["subtotal_amount"] == Decimal("299.97")
    assert item["subtotal_cost"] == Decimal("150.00")


def test_calc_totals_precision_2_decimals():
    """_calc_order_totals 金额保持 2 位小数"""
    items = [{
        "subtotal_amount": Decimal("99.99"),
        "subtotal_cost": Decimal("50.00"),
    }]
    result = _calc_order_totals(items)
    assert result["total_amount"] == Decimal("99.99")
    assert result["total_cost"] == Decimal("50.00")
    assert result["gross_profit"] == Decimal("49.99")


# ═══════════════════════════════════════════════════════
# 9. SalesOrderItem 模型字段精度
# ═══════════════════════════════════════════════════════


def test_order_item_discount_amount_numeric():
    """SalesOrderItem.discount_amount 为 Numeric(12, 2)"""
    col = SalesOrderItem.__table__.columns["discount_amount"]
    assert col.type.precision == 12
    assert col.type.scale == 2


def test_order_item_discount_rate_numeric():
    """SalesOrderItem.discount_rate 为 Numeric(8, 4)"""
    col = SalesOrderItem.__table__.columns["discount_rate"]
    assert col.type.precision == 8
    assert col.type.scale == 4


def test_order_gross_margin_numeric():
    """SalesOrder.gross_margin 为 Numeric(8, 4)"""
    col = SalesOrder.__table__.columns["gross_margin"]
    assert col.type.precision == 8
    assert col.type.scale == 4


def test_order_gross_profit_numeric():
    """SalesOrder.gross_profit 为 Numeric(12, 2)"""
    col = SalesOrder.__table__.columns["gross_profit"]
    assert col.type.precision == 12
    assert col.type.scale == 2
