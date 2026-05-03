"""Pydantic Schema 边界验证测试 — 价格上界、数量上界、列表长度"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RefreshRequest, UserCreate, UserUpdate
from app.schemas.inventory import InventoryAdjust
from app.schemas.order import OrderItemInput
from app.schemas.payment import PaymentCreate
from app.schemas.product import ProductCreate, ProductUpdate

# ─── ProductCreate 价格上界 ────────────────────────────────────


def test_product_sale_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        ProductCreate(name="测试", sale_price="99999999999.99", cost_price="0")


def test_product_cost_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        ProductCreate(name="测试", sale_price="0", cost_price="99999999999.99")


def test_product_stock_quantity_above_max_422():
    with pytest.raises(ValidationError):
        ProductCreate(name="测试", sale_price="0", cost_price="0", stock_quantity=10000000)


def test_product_sort_weight_above_max_422():
    with pytest.raises(ValidationError):
        ProductCreate(name="测试", sale_price="0", cost_price="0", sort_weight=100000)


def test_product_sort_weight_below_min_422():
    with pytest.raises(ValidationError):
        ProductCreate(name="测试", sale_price="0", cost_price="0", sort_weight=-100000)


def test_product_price_at_max_ok():
    p = ProductCreate(name="测试", sale_price="9999999999.99", cost_price="9999999999.99")
    assert p.sale_price == "9999999999.99"


# ─── ProductUpdate 价格上界 ────────────────────────────────────


def test_product_update_sale_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        ProductUpdate(sale_price="99999999999.99")


def test_product_update_cost_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        ProductUpdate(cost_price="99999999999.99")


def test_product_update_stock_above_max_422():
    with pytest.raises(ValidationError):
        ProductUpdate(stock_quantity=10000000)


def test_product_update_sort_weight_above_max_422():
    with pytest.raises(ValidationError):
        ProductUpdate(sort_weight=100000)


# ─── OrderItemInput 数量上界 + 单价上界 ─────────────────────────


def test_order_item_quantity_above_max_422():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id="x", quantity=100000)


def test_order_item_unit_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        OrderItemInput(product_id="x", quantity=1, unit_price="99999999999.99")


def test_order_item_quantity_at_max_ok():
    item = OrderItemInput(product_id="x", quantity=99999)
    assert item.quantity == 99999


def test_order_item_unit_price_at_max_ok():
    item = OrderItemInput(product_id="x", quantity=1, unit_price="9999999999.99")
    assert item.unit_price == "9999999999.99"


# ─── PaymentCreate 金额上界 ────────────────────────────────────


def test_payment_amount_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        PaymentCreate(amount="99999999999.99", payment_method="cash")


def test_payment_amount_at_max_ok():
    p = PaymentCreate(amount="9999999999.99", payment_method="cash")
    assert p.amount == "9999999999.99"


# ─── InventoryAdjust 数量边界 ──────────────────────────────────


def test_inventory_adjust_above_max_422():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id="x", quantity_change=10000000)


def test_inventory_adjust_below_min_422():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id="x", quantity_change=-10000000)


def test_inventory_adjust_at_max_ok():
    adj = InventoryAdjust(product_id="x", quantity_change=9999999)
    assert adj.quantity_change == 9999999


def test_inventory_adjust_at_min_ok():
    adj = InventoryAdjust(product_id="x", quantity_change=-9999999)
    assert adj.quantity_change == -9999999


# ─── RefreshRequest token 长度 ─────────────────────────────────


def test_refresh_request_empty_token_422():
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="")


def test_refresh_request_too_long_422():
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="x" * 2049)


def test_refresh_request_valid_token_ok():
    req = RefreshRequest(refresh_token="valid.jwt.token")
    assert req.refresh_token == "valid.jwt.token"


# ─── UserCreate role_ids 列表长度 ──────────────────────────────


def test_user_create_role_ids_too_many_422():
    with pytest.raises(ValidationError):
        UserCreate(
            username="testuser",
            password="pass123abc",
            role_ids=[str(i) for i in range(51)],
        )


def test_user_create_role_ids_at_max_ok():
    u = UserCreate(
        username="testuser",
        password="pass123abc",
        role_ids=[str(i) for i in range(50)],
    )
    assert len(u.role_ids) == 50


# ─── UserUpdate role_ids 列表长度 ──────────────────────────────


def test_user_update_role_ids_too_many_422():
    with pytest.raises(ValidationError):
        UserUpdate(role_ids=[str(i) for i in range(51)])


def test_user_update_role_ids_at_max_ok():
    u = UserUpdate(role_ids=[str(i) for i in range(50)])
    assert len(u.role_ids) == 50
