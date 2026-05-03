"""Pydantic Schema 验证边界测试 — 覆盖字段约束、类型校验、自定义验证器、文本消毒"""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, UserCreate
from app.schemas.customer import CustomerCreate, CustomerTransfer, CustomerUpdate
from app.schemas.inventory import InventoryAdjust
from app.schemas.order import OrderCreate, OrderItemInput, OrderUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.product import ProductCreate, ProductUpdate

UID = str(uuid.uuid4())


# ═══════════════════════════════════════════════════════
# 1. LoginRequest 边界
# ═══════════════════════════════════════════════════════


def test_login_valid():
    LoginRequest(username="admin", password="secret")


def test_login_username_min_1():
    LoginRequest(username="a", password="p")


def test_login_username_empty_rejected():
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="p")


def test_login_username_max_50():
    LoginRequest(username="a" * 50, password="p")


def test_login_username_51_rejected():
    with pytest.raises(ValidationError):
        LoginRequest(username="a" * 51, password="p")


def test_login_password_max_100():
    LoginRequest(username="u", password="a" * 100)


def test_login_password_101_rejected():
    with pytest.raises(ValidationError):
        LoginRequest(username="u", password="a" * 101)


# ═══════════════════════════════════════════════════════
# 2. RefreshRequest 边界
# ═══════════════════════════════════════════════════════


def test_refresh_token_max_2048():
    RefreshRequest(refresh_token="a" * 2048)


def test_refresh_token_2049_rejected():
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="a" * 2049)


# ═══════════════════════════════════════════════════════
# 3. ChangePasswordRequest 边界
# ═══════════════════════════════════════════════════════


def test_change_pwd_new_min_6():
    ChangePasswordRequest(old_password="old", new_password="Aa1!aa")


def test_change_pwd_new_5_rejected():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="Aa1!a")


def test_change_pwd_no_uppercase_rejected():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="aa1!abcdef")


def test_change_pwd_no_lowercase_rejected():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="AA1!ABCDEF")


def test_change_pwd_no_digit_rejected():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="Aa!abcdef")


def test_change_pwd_no_special_rejected():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="Aa1abcdef")


# ═══════════════════════════════════════════════════════
# 4. UserCreate 边界
# ═══════════════════════════════════════════════════════


def test_user_create_valid():
    UserCreate(username="test", password="Aa1!password")


def test_user_create_username_min_2():
    UserCreate(username="ab", password="Aa1!password")


def test_user_create_username_1_rejected():
    with pytest.raises(ValidationError):
        UserCreate(username="a", password="Aa1!password")


def test_user_create_username_max_50():
    UserCreate(username="a" * 50, password="Aa1!password")


def test_user_create_username_51_rejected():
    with pytest.raises(ValidationError):
        UserCreate(username="a" * 51, password="Aa1!password")


def test_user_create_role_ids_invalid_uuid():
    with pytest.raises(ValidationError, match="角色 ID"):
        UserCreate(username="test", password="Aa1!password", role_ids=["not-uuid"])


def test_user_create_role_ids_max_50():
    UserCreate(username="test", password="Aa1!password", role_ids=[UID] * 50)


def test_user_create_role_ids_51_rejected():
    with pytest.raises(ValidationError):
        UserCreate(username="test", password="Aa1!password", role_ids=[UID] * 51)


def test_user_create_sanitize_display_name():
    """display_name 经过 sanitize_text 移除 HTML 标签"""
    u = UserCreate(username="test", password="Aa1!password", display_name="<b>hi</b>")
    assert "<b>" not in u.display_name


# ═══════════════════════════════════════════════════════
# 5. CustomerCreate 边界
# ═══════════════════════════════════════════════════════


def test_customer_create_valid():
    CustomerCreate(name="测试客户")


def test_customer_create_name_empty_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="")


def test_customer_create_name_max_100():
    CustomerCreate(name="客" * 100)


def test_customer_create_name_101_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="客" * 101)


def test_customer_phone_valid():
    CustomerCreate(name="c", phone="13812345678")


def test_customer_phone_invalid_second_digit():
    with pytest.raises(ValidationError, match="手机号"):
        CustomerCreate(name="c", phone="12345678901")


def test_customer_phone_too_short():
    with pytest.raises(ValidationError, match="手机号"):
        CustomerCreate(name="c", phone="1381234567")


def test_customer_phone_too_long():
    with pytest.raises(ValidationError, match="手机号"):
        CustomerCreate(name="c", phone="138123456789")


def test_customer_email_valid():
    CustomerCreate(name="c", email="a@b.com")


def test_customer_email_no_at():
    with pytest.raises(ValidationError, match="邮箱"):
        CustomerCreate(name="c", email="plain-text")


def test_customer_email_spaces():
    with pytest.raises(ValidationError, match="邮箱"):
        CustomerCreate(name="c", email="a @b.com")


def test_customer_source_valid():
    CustomerCreate(name="c", source="referral")


def test_customer_source_invalid():
    with pytest.raises(ValidationError):
        CustomerCreate(name="c", source="invalid")


def test_customer_level_valid():
    CustomerCreate(name="c", level="vip")


def test_customer_level_invalid():
    with pytest.raises(ValidationError):
        CustomerCreate(name="c", level="platinum")


def test_customer_follow_status_valid():
    CustomerCreate(name="c", follow_status="following")


def test_customer_follow_status_invalid():
    with pytest.raises(ValidationError):
        CustomerCreate(name="c", follow_status="unknown")


def test_customer_owner_invalid_uuid():
    with pytest.raises(ValidationError, match="归属销售"):
        CustomerCreate(name="c", owner_user_id="not-uuid")


def test_customer_remark_max_500():
    CustomerCreate(name="c", remark="x" * 500)


def test_customer_remark_501_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="c", remark="x" * 501)


def test_customer_sanitize_name():
    """name 经过 sanitize_text"""
    c = CustomerCreate(name="<script>alert(1)</script>test")
    assert "<script>" not in c.name


# ═══════════════════════════════════════════════════════
# 6. CustomerUpdate 边界
# ═══════════════════════════════════════════════════════


def test_customer_update_all_none():
    CustomerUpdate()


def test_customer_update_name_empty_rejected():
    with pytest.raises(ValidationError):
        CustomerUpdate(name="")


def test_customer_update_name_none_ok():
    CustomerUpdate(name=None)


# ═══════════════════════════════════════════════════════
# 7. CustomerTransfer 边界
# ═══════════════════════════════════════════════════════


def test_customer_transfer_valid():
    CustomerTransfer(owner_user_id=UID)


def test_customer_transfer_invalid_uuid():
    with pytest.raises(ValidationError, match="归属销售"):
        CustomerTransfer(owner_user_id="bad")


# ═══════════════════════════════════════════════════════
# 8. ProductCreate 边界
# ═══════════════════════════════════════════════════════


def test_product_create_valid():
    ProductCreate(name="商品A")


def test_product_create_name_empty_rejected():
    with pytest.raises(ValidationError):
        ProductCreate(name="")


def test_product_create_name_max_100():
    ProductCreate(name="商" * 100)


def test_product_create_name_101_rejected():
    with pytest.raises(ValidationError):
        ProductCreate(name="商" * 101)


def test_product_sale_price_zero():
    ProductCreate(name="p", sale_price="0")


def test_product_sale_price_max():
    ProductCreate(name="p", sale_price="9999999999.99")


def test_product_sale_price_exceeds_max():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sale_price="9999999999.999")


def test_product_sale_price_negative():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sale_price="-0.01")


def test_product_sale_price_invalid_decimal():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sale_price="abc")


def test_product_cost_price_negative():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", cost_price="-1")


def test_product_stock_quantity_zero():
    ProductCreate(name="p", stock_quantity=0)


def test_product_stock_quantity_max():
    ProductCreate(name="p", stock_quantity=9999999)


def test_product_stock_quantity_exceeds():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", stock_quantity=10000000)


def test_product_stock_quantity_negative():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", stock_quantity=-1)


def test_product_sort_weight_bounds():
    ProductCreate(name="p", sort_weight=-99999)
    ProductCreate(name="p", sort_weight=99999)


def test_product_sort_weight_exceeds():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sort_weight=100000)
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sort_weight=-100000)


def test_product_status_valid():
    ProductCreate(name="p", status="active")
    ProductCreate(name="p", status="inactive")
    ProductCreate(name="p", status="disabled")


def test_product_status_invalid():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", status="pending")


def test_product_category_id_invalid_uuid():
    with pytest.raises(ValidationError, match="分类"):
        ProductCreate(name="p", category_id="not-uuid")


def test_product_sku_max_50():
    ProductCreate(name="p", sku="s" * 50)


def test_product_sku_51_rejected():
    with pytest.raises(ValidationError):
        ProductCreate(name="p", sku="s" * 51)


# ═══════════════════════════════════════════════════════
# 9. ProductUpdate 边界
# ═══════════════════════════════════════════════════════


def test_product_update_all_none():
    ProductUpdate()


def test_product_update_name_empty_rejected():
    with pytest.raises(ValidationError):
        ProductUpdate(name="")


def test_product_update_sale_price_none_ok():
    ProductUpdate(sale_price=None)


def test_product_update_sale_price_negative_rejected():
    with pytest.raises(ValidationError):
        ProductUpdate(sale_price="-1")


# ═══════════════════════════════════════════════════════
# 10. OrderItemInput 边界
# ═══════════════════════════════════════════════════════


def test_order_item_quantity_min_1():
    OrderItemInput(product_id=UID, quantity=1)


def test_order_item_quantity_zero_rejected():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=UID, quantity=0)


def test_order_item_quantity_max_99999():
    OrderItemInput(product_id=UID, quantity=99999)


def test_order_item_quantity_100000_rejected():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=UID, quantity=100000)


def test_order_item_quantity_negative_rejected():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=UID, quantity=-1)


def test_order_item_unit_price_zero():
    OrderItemInput(product_id=UID, quantity=1, unit_price="0")


def test_order_item_unit_price_negative_rejected():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=UID, quantity=1, unit_price="-0.01")


def test_order_item_unit_price_invalid_decimal():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id=UID, quantity=1, unit_price="abc")


def test_order_item_product_id_invalid():
    with pytest.raises(ValidationError):
        OrderItemInput(product_id="bad", quantity=1)


# ═══════════════════════════════════════════════════════
# 11. OrderCreate 边界
# ═══════════════════════════════════════════════════════


def test_order_create_valid():
    OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}])


def test_order_create_items_empty_rejected():
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=UID, items=[])


def test_order_create_items_max_500():
    OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}] * 500)


def test_order_create_items_501_rejected():
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}] * 501)


def test_order_create_customer_id_invalid():
    with pytest.raises(ValidationError):
        OrderCreate(customer_id="bad", items=[{"product_id": UID, "quantity": 1}])


def test_order_create_remark_max_500():
    OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}], remark="r" * 500)


def test_order_create_remark_501_rejected():
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}], remark="r" * 501)


# ═══════════════════════════════════════════════════════
# 12. OrderUpdate 边界
# ═══════════════════════════════════════════════════════


def test_order_update_all_none():
    OrderUpdate()


def test_order_update_items_empty_rejected():
    with pytest.raises(ValidationError):
        OrderUpdate(items=[])


def test_order_update_items_none_ok():
    OrderUpdate(items=None)


# ═══════════════════════════════════════════════════════
# 13. PaymentCreate 边界
# ═══════════════════════════════════════════════════════


def test_payment_create_valid():
    PaymentCreate(amount="100.00", payment_method="cash")


def test_payment_amount_zero_rejected():
    """收款金额必须大于 0，与商品价格（允许 0）不同"""
    with pytest.raises(ValidationError, match="大于 0"):
        PaymentCreate(amount="0", payment_method="cash")


def test_payment_amount_positive():
    PaymentCreate(amount="0.01", payment_method="cash")


def test_payment_amount_negative_rejected():
    with pytest.raises(ValidationError):
        PaymentCreate(amount="-1", payment_method="cash")


def test_payment_amount_max():
    PaymentCreate(amount="9999999999.99", payment_method="cash")


def test_payment_amount_exceeds_max():
    with pytest.raises(ValidationError):
        PaymentCreate(amount="9999999999.999", payment_method="cash")


def test_payment_amount_invalid_decimal():
    with pytest.raises(ValidationError, match="金额格式"):
        PaymentCreate(amount="abc", payment_method="cash")


def test_payment_method_valid():
    for m in ("cash", "transfer", "wechat", "alipay", "other"):
        PaymentCreate(amount="10", payment_method=m)


def test_payment_method_invalid():
    with pytest.raises(ValidationError):
        PaymentCreate(amount="10", payment_method="credit_card")


def test_payment_remark_max_500():
    PaymentCreate(amount="10", payment_method="cash", remark="r" * 500)


def test_payment_remark_501_rejected():
    with pytest.raises(ValidationError):
        PaymentCreate(amount="10", payment_method="cash", remark="r" * 501)


# ═══════════════════════════════════════════════════════
# 14. InventoryAdjust 边界
# ═══════════════════════════════════════════════════════


def test_inventory_adjust_positive():
    InventoryAdjust(product_id=UID, quantity_change=100)


def test_inventory_adjust_negative():
    InventoryAdjust(product_id=UID, quantity_change=-100)


def test_inventory_adjust_zero():
    InventoryAdjust(product_id=UID, quantity_change=0)


def test_inventory_adjust_max():
    InventoryAdjust(product_id=UID, quantity_change=9999999)


def test_inventory_adjust_min():
    InventoryAdjust(product_id=UID, quantity_change=-9999999)


def test_inventory_adjust_exceeds_positive():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id=UID, quantity_change=10000000)


def test_inventory_adjust_exceeds_negative():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id=UID, quantity_change=-10000000)


def test_inventory_adjust_product_id_invalid():
    with pytest.raises(ValidationError):
        InventoryAdjust(product_id="bad", quantity_change=1)


# ═══════════════════════════════════════════════════════
# 15. 文本消毒交叉验证
# ═══════════════════════════════════════════════════════


def test_sanitize_strips_html_in_customer_name():
    c = CustomerCreate(name="<script>alert(1)</script>")
    assert "<" not in c.name


def test_sanitize_strips_control_chars_in_product_remark():
    p = ProductCreate(name="p", remark="hello\x00world")
    assert "\x00" not in p.remark


def test_sanitize_strips_html_in_order_remark():
    o = OrderCreate(customer_id=UID, items=[{"product_id": UID, "quantity": 1}], remark="<b>bold</b>")
    assert "<b>" not in o.remark


def test_sanitize_strips_html_in_payment_remark():
    p = PaymentCreate(amount="10", payment_method="cash", remark="<img src=x>")
    assert "<img" not in p.remark


# ═══════════════════════════════════════════════════════
# 16. 缺少必填字段
# ═══════════════════════════════════════════════════════


def test_login_missing_username():
    with pytest.raises(ValidationError):
        LoginRequest(password="p")


def test_user_create_missing_username():
    with pytest.raises(ValidationError):
        UserCreate(password="Aa1!password")


def test_customer_create_missing_name():
    with pytest.raises(ValidationError):
        CustomerCreate()


def test_order_create_missing_items():
    with pytest.raises(ValidationError):
        OrderCreate(customer_id=UID)


def test_payment_create_missing_amount():
    with pytest.raises(ValidationError):
        PaymentCreate(payment_method="cash")
