"""Pydantic Schema 边界验证测试 — 价格上界、数量上界、列表长度、UUID 格式"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RefreshRequest, UserCreate, UserUpdate
from app.schemas.customer import CustomerCreate, CustomerTransfer, CustomerUpdate
from app.schemas.inventory import InventoryAdjust
from app.schemas.order import OrderCreate, OrderItemInput, OrderUpdate
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
        OrderItemInput(product_id="00000000-0000-0000-0000-000000000001", quantity=100000)


def test_order_item_unit_price_above_max_422():
    with pytest.raises(ValidationError, match="不能超过"):
        OrderItemInput(product_id="00000000-0000-0000-0000-000000000001", quantity=1, unit_price="99999999999.99")


def test_order_item_quantity_at_max_ok():
    item = OrderItemInput(product_id="00000000-0000-0000-0000-000000000001", quantity=99999)
    assert item.quantity == 99999


def test_order_item_unit_price_at_max_ok():
    item = OrderItemInput(product_id="00000000-0000-0000-0000-000000000001", quantity=1, unit_price="9999999999.99")
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
        InventoryAdjust(product_id="00000000-0000-0000-0000-000000000001", quantity_change=10000000)


def test_inventory_adjust_below_min_422():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id="00000000-0000-0000-0000-000000000001", quantity_change=-10000000)


def test_inventory_adjust_at_max_ok():
    adj = InventoryAdjust(product_id="00000000-0000-0000-0000-000000000001", quantity_change=9999999)
    assert adj.quantity_change == 9999999


def test_inventory_adjust_at_min_ok():
    adj = InventoryAdjust(product_id="00000000-0000-0000-0000-000000000001", quantity_change=-9999999)
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
            role_ids=[f"00000000-0000-0000-0000-{i:012d}" for i in range(51)],
        )


def test_user_create_role_ids_at_max_ok():
    u = UserCreate(
        username="testuser",
        password="pass123abc",
        role_ids=[f"00000000-0000-0000-0000-{i:012d}" for i in range(50)],
    )
    assert len(u.role_ids) == 50


# ─── UserUpdate role_ids 列表长度 ──────────────────────────────


def test_user_update_role_ids_too_many_422():
    with pytest.raises(ValidationError):
        UserUpdate(role_ids=[f"00000000-0000-0000-0000-{i:012d}" for i in range(51)])


def test_user_update_role_ids_at_max_ok():
    u = UserUpdate(role_ids=[f"00000000-0000-0000-0000-{i:012d}" for i in range(50)])
    assert len(u.role_ids) == 50


# ─── CustomerCreate owner_user_id UUID 格式 ──────────────────


def test_customer_create_owner_user_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="归属销售 ID"):
        CustomerCreate(name="测试", owner_user_id="not-a-uuid")


def test_customer_create_owner_user_id_valid_uuid_ok():
    c = CustomerCreate(name="测试", owner_user_id="12345678-1234-1234-1234-123456789abc")
    assert c.owner_user_id == "12345678-1234-1234-1234-123456789abc"


def test_customer_create_owner_user_id_none_ok():
    c = CustomerCreate(name="测试", owner_user_id=None)
    assert c.owner_user_id is None


# ─── CustomerUpdate owner_user_id UUID 格式 ──────────────────


def test_customer_update_owner_user_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="归属销售 ID"):
        CustomerUpdate(owner_user_id="bad-uuid")


def test_customer_update_owner_user_id_valid_uuid_ok():
    u = CustomerUpdate(owner_user_id="12345678-1234-1234-1234-123456789abc")
    assert u.owner_user_id == "12345678-1234-1234-1234-123456789abc"


def test_customer_update_owner_user_id_none_ok():
    u = CustomerUpdate(owner_user_id=None)
    assert u.owner_user_id is None


# ─── CustomerTransfer owner_user_id UUID 格式 ────────────────


def test_customer_transfer_owner_user_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="归属销售 ID"):
        CustomerTransfer(owner_user_id="not-a-uuid")


def test_customer_transfer_owner_user_id_valid_uuid_ok():
    t = CustomerTransfer(owner_user_id="12345678-1234-1234-1234-123456789abc")
    assert t.owner_user_id == "12345678-1234-1234-1234-123456789abc"


# ─── OrderItemInput product_id UUID 格式 ──────────────────────


def test_order_item_product_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="商品 ID"):
        OrderItemInput(product_id="not-a-uuid", quantity=1)


def test_order_item_product_id_valid_uuid_ok():
    item = OrderItemInput(product_id="12345678-1234-1234-1234-123456789abc", quantity=1)
    assert item.product_id == "12345678-1234-1234-1234-123456789abc"


# ─── OrderCreate customer_id UUID 格式 ────────────────────────


def test_order_create_customer_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="客户 ID"):
        OrderCreate(
            customer_id="bad-uuid",
            items=[{"product_id": "12345678-1234-1234-1234-123456789abc", "quantity": 1}],
        )


def test_order_create_customer_id_valid_uuid_ok():
    o = OrderCreate(
        customer_id="12345678-1234-1234-1234-123456789abc",
        items=[{"product_id": "12345678-1234-1234-1234-123456789abc", "quantity": 1}],
    )
    assert o.customer_id == "12345678-1234-1234-1234-123456789abc"


# ─── OrderUpdate customer_id UUID 格式 ────────────────────────


def test_order_update_customer_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="客户 ID"):
        OrderUpdate(customer_id="bad-uuid")


def test_order_update_customer_id_valid_uuid_ok():
    u = OrderUpdate(customer_id="12345678-1234-1234-1234-123456789abc")
    assert u.customer_id == "12345678-1234-1234-1234-123456789abc"


def test_order_update_customer_id_none_ok():
    u = OrderUpdate(customer_id=None)
    assert u.customer_id is None


# ─── ProductCreate category_id UUID 格式 ──────────────────────


def test_product_create_category_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="分类 ID"):
        ProductCreate(name="测试", sale_price="0", cost_price="0", category_id="bad-uuid")


def test_product_create_category_id_valid_uuid_ok():
    p = ProductCreate(name="测试", sale_price="0", cost_price="0", category_id="12345678-1234-1234-1234-123456789abc")
    assert p.category_id == "12345678-1234-1234-1234-123456789abc"


def test_product_create_category_id_none_ok():
    p = ProductCreate(name="测试", sale_price="0", cost_price="0", category_id=None)
    assert p.category_id is None


# ─── ProductUpdate category_id UUID 格式 ──────────────────────


def test_product_update_category_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="分类 ID"):
        ProductUpdate(category_id="bad-uuid")


def test_product_update_category_id_valid_uuid_ok():
    u = ProductUpdate(category_id="12345678-1234-1234-1234-123456789abc")
    assert u.category_id == "12345678-1234-1234-1234-123456789abc"


def test_product_update_category_id_none_ok():
    u = ProductUpdate(category_id=None)
    assert u.category_id is None


# ─── InventoryAdjust product_id UUID 格式 ─────────────────────


def test_inventory_adjust_product_id_invalid_uuid_422():
    with pytest.raises(ValidationError, match="商品 ID"):
        InventoryAdjust(product_id="bad-uuid", quantity_change=10)


def test_inventory_adjust_product_id_valid_uuid_ok():
    adj = InventoryAdjust(product_id="12345678-1234-1234-1234-123456789abc", quantity_change=10)
    assert adj.product_id == "12345678-1234-1234-1234-123456789abc"


# ─── UserCreate role_ids UUID 格式 ────────────────────────────


def test_user_create_role_ids_invalid_uuid_422():
    with pytest.raises(ValidationError, match="角色 ID"):
        UserCreate(username="testuser", password="pass123abc", role_ids=["not-a-uuid"])


def test_user_create_role_ids_valid_uuid_ok():
    u = UserCreate(username="testuser", password="pass123abc", role_ids=["12345678-1234-1234-1234-123456789abc"])
    assert len(u.role_ids) == 1


def test_user_create_role_ids_empty_ok():
    u = UserCreate(username="testuser", password="pass123abc", role_ids=[])
    assert u.role_ids == []


# ─── UserUpdate role_ids UUID 格式 ────────────────────────────


def test_user_update_role_ids_invalid_uuid_422():
    with pytest.raises(ValidationError, match="角色 ID"):
        UserUpdate(role_ids=["not-a-uuid"])


def test_user_update_role_ids_valid_uuid_ok():
    u = UserUpdate(role_ids=["12345678-1234-1234-1234-123456789abc"])
    assert len(u.role_ids) == 1


def test_user_update_role_ids_none_ok():
    u = UserUpdate(role_ids=None)
    assert u.role_ids is None
