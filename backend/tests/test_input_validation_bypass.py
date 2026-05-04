"""安全加固：后端 API 输入校验绕过回归测试
验证 Pydantic Schema 在运行时拒绝非法输入：负值、越界、无效枚举、空必填、畸形 UUID、XSS 注入"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    UserCreate,
)
from app.schemas.customer import CustomerCreate
from app.schemas.order import OrderCreate, OrderItemInput
from app.schemas.payment import PaymentCreate
from app.schemas.product import ProductCreate

# ═══════════════════════════════════════════════════════════
# 1. 商品 Schema 输入校验（8 项）
# ═══════════════════════════════════════════════════════════


class TestProductInputValidation:
    """验证商品输入校验"""

    def test_product_create_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="", sale_price="10")

    def test_product_create_rejects_negative_price(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="-1")

    def test_product_create_rejects_negative_stock(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="10", stock_quantity=-1)

    def test_product_create_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="10", status="hacked")

    def test_product_create_rejects_oversized_name(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="A" * 101, sale_price="10")

    def test_product_create_rejects_oversized_remark(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="10", remark="B" * 501)

    def test_product_create_rejects_invalid_category_id(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="10", category_id="not-a-uuid")

    def test_product_create_accepts_valid_input(self):
        p = ProductCreate(name="测试商品", sale_price="99.9", cost_price="50")
        assert p.name == "测试商品"


# ═══════════════════════════════════════════════════════════
# 2. 客户 Schema 输入校验（6 项）
# ═══════════════════════════════════════════════════════════


class TestCustomerInputValidation:
    """验证客户输入校验"""

    def test_customer_create_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="")

    def test_customer_create_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="测试", email="not-an-email")

    def test_customer_create_rejects_invalid_phone(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="测试", phone="123")

    def test_customer_create_rejects_invalid_source(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="测试", source="invalid_source")

    def test_customer_create_rejects_invalid_level(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="测试", level="god")

    def test_customer_create_rejects_invalid_owner_id(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="测试", owner_user_id="xyz")


# ═══════════════════════════════════════════════════════════
# 3. 订单 Schema 输入校验（6 项）
# ═══════════════════════════════════════════════════════════


class TestOrderInputValidation:
    """验证订单输入校验"""

    def test_order_item_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="a" * 36, quantity=0)

    def test_order_item_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="a" * 36, quantity=-5)

    def test_order_item_rejects_negative_unit_price(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="a" * 36, quantity=1, unit_price="-10")

    def test_order_item_rejects_invalid_product_id(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="not-uuid", quantity=1)

    def test_order_create_rejects_empty_items(self):
        with pytest.raises(ValidationError):
            OrderCreate(customer_id="a" * 36, items=[])

    def test_order_create_rejects_invalid_customer_id(self):
        with pytest.raises(ValidationError):
            OrderCreate(customer_id="bad", items=[
                OrderItemInput(product_id="a" * 36, quantity=1),
            ])


# ═══════════════════════════════════════════════════════════
# 4. 收款 Schema 输入校验（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaymentInputValidation:
    """验证收款输入校验"""

    def test_payment_create_rejects_zero_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="0", payment_method="cash")

    def test_payment_create_rejects_negative_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="-5", payment_method="cash")

    def test_payment_create_rejects_invalid_method(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="100", payment_method="bitcoin")

    def test_payment_create_rejects_non_numeric_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="abc", payment_method="cash")

    def test_payment_create_accepts_valid_input(self):
        p = PaymentCreate(amount="100.50", payment_method="wechat")
        assert p.payment_method == "wechat"


# ═══════════════════════════════════════════════════════════
# 5. 用户 Schema 输入校验（5 项）
# ═══════════════════════════════════════════════════════════


class TestUserInputValidation:
    """验证用户输入校验"""

    def test_user_create_rejects_short_username(self):
        with pytest.raises(ValidationError):
            UserCreate(username="a", password="Test123456")

    def test_user_create_rejects_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", password="12345")

    def test_user_create_rejects_invalid_role_id(self):
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", password="Test123456", role_ids=["not-uuid"])

    def test_login_request_rejects_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="pass")

    def test_change_password_rejects_short_new_password(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(old_password="oldpass123", new_password="short")


# ═══════════════════════════════════════════════════════════
# 6. XSS/注入防护验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestXSSInjectionPrevention:
    """验证 Schema 的 sanitize 清理器阻止 XSS 注入"""

    def test_product_name_script_tag_sanitized(self):
        p = ProductCreate(name='<script>alert("xss")</script>', sale_price="10")
        assert "<script>" not in p.name

    def test_product_remark_html_sanitized(self):
        p = ProductCreate(name="测试", sale_price="10", remark='<img onerror="alert(1)">')
        assert "onerror" not in p.remark

    def test_customer_name_script_tag_sanitized(self):
        c = CustomerCreate(name='<script>alert("xss")</script>')
        assert "<script>" not in c.name

    def test_customer_remark_sanitized(self):
        c = CustomerCreate(name="测试", remark='"><script>alert(1)</script>')
        assert "<script>" not in c.remark

    def test_order_remark_sanitized(self):
        o = OrderCreate(
            customer_id="00000000-0000-0000-0000-000000000000",
            items=[OrderItemInput(product_id="00000000-0000-0000-0000-000000000000", quantity=1)],
            remark='<iframe src="evil">',
        )
        assert "<iframe" not in o.remark

    def test_payment_remark_sanitized(self):
        p = PaymentCreate(amount="100", payment_method="cash", remark='<svg onload="alert(1)">')
        assert "onload" not in p.remark


# ═══════════════════════════════════════════════════════════
# 7. 边界值验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestBoundaryValues:
    """验证边界值处理"""

    def test_product_create_accepts_max_name_length(self):
        p = ProductCreate(name="A" * 100, sale_price="10")
        assert len(p.name) <= 100

    def test_product_create_accepts_zero_price(self):
        p = ProductCreate(name="测试", sale_price="0", cost_price="0")
        assert p.sale_price == "0"

    def test_order_item_accepts_large_quantity(self):
        item = OrderItemInput(
            product_id="00000000-0000-0000-0000-000000000000",
            quantity=99999,
        )
        assert item.quantity == 99999

    def test_order_item_rejects_oversized_quantity(self):
        with pytest.raises(ValidationError):
            OrderItemInput(
                product_id="00000000-0000-0000-0000-000000000000",
                quantity=100000,
            )

    def test_product_create_rejects_oversized_sort_weight(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="测试", sale_price="10", sort_weight=100000)

    def test_customer_create_accepts_all_valid_sources(self):
        for src in ("referral", "online", "offline", "ad", "other"):
            c = CustomerCreate(name="测试", source=src)
            assert c.source == src
