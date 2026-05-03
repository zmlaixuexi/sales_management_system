"""Schema field_validator 单元测试 — 覆盖所有 Pydantic 校验器"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, UserCreate, UserUpdate
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.inventory import InventoryAdjust
from app.schemas.order import OrderCreate, OrderItemInput, OrderUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.product import ProductCreate, ProductUpdate

# ─── OrderItemInput.unit_price ──────────────────────────────


def test_order_item_unit_price_none_ok():
    """unit_price 为 None 时通过"""
    item = OrderItemInput(product_id="p1", quantity=1, unit_price=None)
    assert item.unit_price is None


def test_order_item_unit_price_zero_ok():
    """unit_price 为 0 时通过"""
    item = OrderItemInput(product_id="p1", quantity=1, unit_price="0")
    assert item.unit_price == "0"


def test_order_item_unit_price_negative_rejected():
    """unit_price 为负数被拒绝"""
    with pytest.raises(ValidationError) as exc_info:
        OrderItemInput(product_id="p1", quantity=1, unit_price="-5")
    assert "不能为负" in str(exc_info.value)


# ─── OrderCreate/OrderUpdate remark strip_html ──────────────


def test_order_create_remark_strips_html():
    """订单备注去除 HTML"""
    order = OrderCreate(customer_id="c1", items=[{"product_id": "p1", "quantity": 1}], remark="<b>测试</b>")
    assert order.remark == "测试"


def test_order_update_remark_strips_html():
    """订单更新备注去除 HTML"""
    order = OrderUpdate(remark="<script>alert(1)</script>备注")
    assert order.remark == "alert(1)备注"


# ─── PaymentCreate.amount ───────────────────────────────────


def test_payment_amount_positive_ok():
    """金额大于 0 通过"""
    p = PaymentCreate(amount="100.00", payment_method="cash")
    assert p.amount == "100.00"


def test_payment_amount_zero_rejected():
    """金额为 0 被拒绝"""
    with pytest.raises(ValidationError) as exc_info:
        PaymentCreate(amount="0", payment_method="cash")
    assert "必须大于 0" in str(exc_info.value)


def test_payment_amount_negative_rejected():
    """金额为负被拒绝"""
    with pytest.raises(ValidationError) as exc_info:
        PaymentCreate(amount="-10", payment_method="cash")
    assert "必须大于 0" in str(exc_info.value)


# ─── PaymentCreate.remark strip_html ────────────────────────


def test_payment_remark_strips_html():
    """收款备注去除 HTML"""
    p = PaymentCreate(amount="100", payment_method="cash", remark="<i>急</i>")
    assert p.remark == "急"


# ─── InventoryAdjust.remark strip_html ──────────────────────


def test_inventory_adjust_remark_strips_html():
    """库存调整备注去除 HTML"""
    adj = InventoryAdjust(product_id="p1", quantity_change=5, remark="<b>盘盈</b>")
    assert adj.remark == "盘盈"


# ─── ProductCreate/Update strip_html ────────────────────────


def test_product_create_name_strips_html():
    """商品名去除 HTML"""
    p = ProductCreate(name="<b>XSS</b>商品", sale_price="10", cost_price="5")
    assert p.name == "XSS商品"


def test_product_create_remark_strips_html():
    """商品备注去除 HTML"""
    p = ProductCreate(name="正常", sale_price="10", cost_price="5", remark="<script>x</script>")
    assert p.remark == "x"


def test_product_update_strips_html():
    """商品更新去除 HTML"""
    p = ProductUpdate(name="<b>新名</b>", remark="<b>备注</b>")
    assert p.name == "新名"
    assert p.remark == "备注"


# ─── CustomerCreate/Update strip_html ───────────────────────


def test_customer_create_name_strips_html():
    """客户名去除 HTML"""
    c = CustomerCreate(name="<script>alert(1)</script>客户")
    assert c.name == "alert(1)客户"


def test_customer_create_email_strips_html():
    """客户邮箱去除 HTML"""
    c = CustomerCreate(name="测试", email="<b>xss</b>@test.com")
    assert c.email == "xss@test.com"


def test_customer_update_strips_html():
    """客户更新去除 HTML"""
    c = CustomerUpdate(name="<i>新名</i>", contact_name="<b>张三</b>")
    assert c.name == "新名"
    assert c.contact_name == "张三"


# ─── UserCreate password strength ───────────────────────────


def test_user_create_password_valid():
    """合法密码通过"""
    u = UserCreate(username="test", password="pass123")
    assert u.password == "pass123"


def test_user_create_password_no_digits_rejected():
    """密码无数字被拒绝"""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="test", password="abcdef")
    assert "数字" in str(exc_info.value)


def test_user_create_password_no_letters_rejected():
    """密码无字母被拒绝"""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="test", password="123456")
    assert "字母" in str(exc_info.value)


# ─── UserCreate/Update sanitize ─────────────────────────────


def test_user_create_email_strips_html():
    """用户邮箱去除 HTML"""
    u = UserCreate(username="test", password="pass123", email="<script>x</script>@evil.com")
    assert u.email == "x@evil.com"


def test_user_update_display_name_strips_html():
    """用户显示名去除 HTML"""
    u = UserUpdate(display_name="<b>管理员</b>")
    assert u.display_name == "管理员"


# ─── ChangePasswordRequest password strength ────────────────


def test_change_password_valid():
    """合法新密码通过"""
    r = ChangePasswordRequest(old_password="old123", new_password="new456")
    assert r.new_password == "new456"


def test_change_password_short_rejected():
    """新密码太短被拒绝"""
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old123", new_password="ab1")


# ─── ProductCreate sale_price / cost_price 验证 ──────────────


def test_product_create_negative_sale_price_rejected():
    """负销售价被拒绝"""
    with pytest.raises(ValidationError, match="销售价不能为负数"):
        ProductCreate(name="测试", sale_price="-10", cost_price="5")


def test_product_create_negative_cost_price_rejected():
    """负成本价被拒绝"""
    with pytest.raises(ValidationError, match="成本价不能为负数"):
        ProductCreate(name="测试", sale_price="10", cost_price="-5")


def test_product_create_invalid_sale_price_rejected():
    """非数字销售价被拒绝"""
    with pytest.raises(ValidationError, match="销售价格式不正确"):
        ProductCreate(name="测试", sale_price="abc", cost_price="5")


def test_product_create_invalid_cost_price_rejected():
    """非数字成本价被拒绝"""
    with pytest.raises(ValidationError, match="成本价格式不正确"):
        ProductCreate(name="测试", sale_price="10", cost_price="xyz")


def test_product_create_zero_prices_ok():
    """零价格通过"""
    p = ProductCreate(name="测试", sale_price="0", cost_price="0")
    assert p.sale_price == "0"
    assert p.cost_price == "0"


def test_product_update_negative_sale_price_rejected():
    """编辑时负销售价被拒绝"""
    with pytest.raises(ValidationError, match="销售价不能为负数"):
        ProductUpdate(sale_price="-10")


def test_product_update_invalid_cost_price_rejected():
    """编辑时非数字成本价被拒绝"""
    with pytest.raises(ValidationError, match="成本价格式不正确"):
        ProductUpdate(cost_price="bad")


# ─── PaymentCreate.amount Decimal 解析保护 ──────────────────


def test_payment_create_invalid_amount_rejected():
    """非数字金额被拒绝"""
    with pytest.raises(ValidationError, match="金额格式不正确"):
        PaymentCreate(amount="hello", payment_method="cash")


# ─── OrderItemInput.unit_price Decimal 解析保护 ─────────────


def test_order_item_invalid_unit_price_rejected():
    """非数字成交单价被拒绝"""
    with pytest.raises(ValidationError, match="成交单价格式不正确"):
        OrderItemInput(product_id="p1", quantity=1, unit_price="abc")
