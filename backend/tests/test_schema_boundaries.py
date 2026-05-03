"""Pydantic schema 字段边界测试 — 覆盖字符串长度、数值范围、UUID/枚举/正则校验、Decimal 解析"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    UserCreate,
    UserUpdate,
)
from app.schemas.customer import CustomerCreate, CustomerTransfer, CustomerUpdate
from app.schemas.inventory import InventoryAdjust
from app.schemas.order import OrderCreate, OrderItemInput, OrderUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.product import ProductCreate, ProductUpdate

# ═══════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════

_UUID = "00000000-0000-0000-0000-000000000001"


# ═══════════════════════════════════════════════════════
# 1. CustomerCreate 边界
# ═══════════════════════════════════════════════════════


class TestCustomerCreate:
    def test_name_min_length_1(self):
        """name 最短 1 字符"""
        c = CustomerCreate(name="张")
        assert c.name == "张"

    def test_name_max_length_100(self):
        """name 最长 100 字符"""
        c = CustomerCreate(name="张" * 100)
        assert len(c.name) == 100

    def test_name_exceeds_max_length(self):
        """name 超过 100 字符被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="张" * 101)

    def test_name_empty_rejected(self):
        """name 为空被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="")

    def test_name_whitespace_only(self):
        """name 纯空格通过 sanitize 后的行为（sanitize 可能保留）"""
        c = CustomerCreate(name="   ")
        # sanitize 不拒绝纯空格，但 name 字段 min_length=1 仍通过
        assert c.name is not None

    def test_phone_valid(self):
        """合法中国手机号通过"""
        c = CustomerCreate(name="客户", phone="13800138000")
        assert c.phone == "13800138000"

    def test_phone_invalid_format(self):
        """非法手机号被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="客户", phone="12345678901")

    def test_email_valid(self):
        """合法邮箱通过"""
        c = CustomerCreate(name="客户", email="test@example.com")
        assert c.email == "test@example.com"

    def test_email_invalid_format(self):
        """非法邮箱被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="客户", email="not-an-email")

    def test_source_enum_valid(self):
        """source 枚举值通过"""
        for src in ("referral", "online", "offline", "ad", "other"):
            c = CustomerCreate(name="客户", source=src)
            assert c.source == src

    def test_source_enum_invalid(self):
        """非法 source 被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="客户", source="invalid")

    def test_level_enum_valid(self):
        """level 枚举值通过"""
        for lvl in ("vip", "important", "normal", "potential"):
            c = CustomerCreate(name="客户", level=lvl)
            assert c.level == lvl

    def test_owner_user_id_valid_uuid(self):
        """owner_user_id 合法 UUID 通过"""
        c = CustomerCreate(name="客户", owner_user_id=_UUID)
        assert c.owner_user_id == _UUID

    def test_owner_user_id_invalid_uuid(self):
        """owner_user_id 非法 UUID 被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="客户", owner_user_id="not-a-uuid")

    def test_remark_max_length_500(self):
        """remark 最长 500 字符"""
        c = CustomerCreate(name="客户", remark="备注" * 250)
        assert len(c.remark) == 500

    def test_remark_exceeds_max_length(self):
        """remark 超过 500 字符被拒绝"""
        with pytest.raises(ValidationError):
            CustomerCreate(name="客户", remark="x" * 501)

    def test_defaults(self):
        """可选字段默认值"""
        c = CustomerCreate(name="客户")
        assert c.source is None
        assert c.level == "normal"
        assert c.follow_status == "new"
        assert c.phone is None
        assert c.email is None
        assert c.owner_user_id is None
        assert c.remark is None


# ═══════════════════════════════════════════════════════
# 2. CustomerUpdate 边界
# ═══════════════════════════════════════════════════════


class TestCustomerUpdate:
    def test_all_none(self):
        """所有字段可选"""
        u = CustomerUpdate()
        assert u.name is None
        assert u.phone is None

    def test_name_min_length_1(self):
        """name 不能为空字符串"""
        with pytest.raises(ValidationError):
            CustomerUpdate(name="")

    def test_phone_invalid(self):
        """非法手机号被拒绝"""
        with pytest.raises(ValidationError):
            CustomerUpdate(phone="999")


class TestCustomerTransfer:
    def test_valid_uuid(self):
        """合法 UUID 通过"""
        t = CustomerTransfer(owner_user_id=_UUID)
        assert t.owner_user_id == _UUID

    def test_invalid_uuid(self):
        """非法 UUID 被拒绝"""
        with pytest.raises(ValidationError):
            CustomerTransfer(owner_user_id="abc")


# ═══════════════════════════════════════════════════════
# 3. ProductCreate 边界
# ═══════════════════════════════════════════════════════


class TestProductCreate:
    def test_name_min_length(self):
        c = ProductCreate(name="商", sale_price="10.00", cost_price="5.00")
        assert c.name == "商"

    def test_name_max_length_100(self):
        c = ProductCreate(name="商" * 100, sale_price="10.00", cost_price="5.00")
        assert len(c.name) == 100

    def test_name_exceeds_max(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商" * 101, sale_price="10.00", cost_price="5.00")

    def test_name_empty(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="", sale_price="10.00", cost_price="5.00")

    def test_sale_price_zero(self):
        """售价 0 通过"""
        c = ProductCreate(name="商品", sale_price="0", cost_price="0")
        assert c.sale_price == "0"

    def test_sale_price_negative(self):
        """负售价被拒绝"""
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="-1.00", cost_price="0")

    def test_sale_price_max(self):
        """售价上限 9999999999.99 通过"""
        c = ProductCreate(name="商品", sale_price="9999999999.99", cost_price="0")
        assert c.sale_price == "9999999999.99"

    def test_sale_price_exceeds_max(self):
        """售价超过上限被拒绝"""
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10000000000.00", cost_price="0")

    def test_sale_price_invalid_format(self):
        """非数字售价被拒绝"""
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="abc", cost_price="0")

    def test_stock_quantity_zero(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5", stock_quantity=0)
        assert c.stock_quantity == 0

    def test_stock_quantity_max(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5", stock_quantity=9999999)
        assert c.stock_quantity == 9999999

    def test_stock_quantity_exceeds_max(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", stock_quantity=10000000)

    def test_stock_quantity_negative(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", stock_quantity=-1)

    def test_category_id_valid(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5", category_id=_UUID)
        assert c.category_id == _UUID

    def test_category_id_invalid(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", category_id="xyz")

    def test_status_enum(self):
        for s in ("active", "inactive", "disabled"):
            c = ProductCreate(name="商品", sale_price="10", cost_price="5", status=s)
            assert c.status == s

    def test_status_invalid(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", status="deleted")

    def test_sort_weight_range(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5", sort_weight=99999)
        assert c.sort_weight == 99999
        c2 = ProductCreate(name="商品", sale_price="10", cost_price="5", sort_weight=-99999)
        assert c2.sort_weight == -99999

    def test_sort_weight_exceeds(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", sort_weight=100000)

    def test_sku_max_length(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5", sku="S" * 50)
        assert len(c.sku) == 50

    def test_sku_exceeds(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="商品", sale_price="10", cost_price="5", sku="S" * 51)

    def test_defaults(self):
        c = ProductCreate(name="商品", sale_price="10", cost_price="5")
        assert c.stock_quantity == 0
        assert c.status == "active"
        assert c.sort_weight == 0
        assert c.sku is None
        assert c.category_id is None


# ═══════════════════════════════════════════════════════
# 4. ProductUpdate 边界
# ═══════════════════════════════════════════════════════


class TestProductUpdate:
    def test_all_none(self):
        u = ProductUpdate()
        assert u.name is None
        assert u.sale_price is None

    def test_name_empty_rejected(self):
        with pytest.raises(ValidationError):
            ProductUpdate(name="")

    def test_sale_price_negative(self):
        with pytest.raises(ValidationError):
            ProductUpdate(sale_price="-5.00")

    def test_stock_quantity_negative(self):
        with pytest.raises(ValidationError):
            ProductUpdate(stock_quantity=-1)


# ═══════════════════════════════════════════════════════
# 5. OrderCreate / OrderItemInput 边界
# ═══════════════════════════════════════════════════════


class TestOrderItemInput:
    def test_quantity_min_1(self):
        item = OrderItemInput(product_id=_UUID, quantity=1)
        assert item.quantity == 1

    def test_quantity_max_99999(self):
        item = OrderItemInput(product_id=_UUID, quantity=99999)
        assert item.quantity == 99999

    def test_quantity_zero_rejected(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=_UUID, quantity=0)

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=_UUID, quantity=-1)

    def test_quantity_exceeds_max(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=_UUID, quantity=100000)

    def test_unit_price_zero(self):
        item = OrderItemInput(product_id=_UUID, quantity=1, unit_price="0")
        assert item.unit_price == "0"

    def test_unit_price_negative(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=_UUID, quantity=1, unit_price="-1.00")

    def test_unit_price_invalid(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id=_UUID, quantity=1, unit_price="abc")

    def test_product_id_invalid(self):
        with pytest.raises(ValidationError):
            OrderItemInput(product_id="not-uuid", quantity=1)


class TestOrderCreate:
    def test_items_min_1(self):
        o = OrderCreate(customer_id=_UUID, items=[
            OrderItemInput(product_id=_UUID, quantity=1),
        ])
        assert len(o.items) == 1

    def test_items_empty_rejected(self):
        with pytest.raises(ValidationError):
            OrderCreate(customer_id=_UUID, items=[])

    def test_items_max_500(self):
        items = [OrderItemInput(product_id=_UUID, quantity=1) for _ in range(500)]
        o = OrderCreate(customer_id=_UUID, items=items)
        assert len(o.items) == 500

    def test_items_exceeds_500(self):
        items = [OrderItemInput(product_id=_UUID, quantity=1) for _ in range(501)]
        with pytest.raises(ValidationError):
            OrderCreate(customer_id=_UUID, items=items)

    def test_customer_id_invalid(self):
        with pytest.raises(ValidationError):
            OrderCreate(customer_id="bad", items=[
                OrderItemInput(product_id=_UUID, quantity=1),
            ])

    def test_remark_max_length(self):
        o = OrderCreate(customer_id=_UUID, items=[
            OrderItemInput(product_id=_UUID, quantity=1),
        ], remark="r" * 500)
        assert len(o.remark) == 500

    def test_remark_exceeds(self):
        with pytest.raises(ValidationError):
            OrderCreate(customer_id=_UUID, items=[
                OrderItemInput(product_id=_UUID, quantity=1),
            ], remark="r" * 501)


class TestOrderUpdate:
    def test_all_none(self):
        u = OrderUpdate()
        assert u.customer_id is None
        assert u.items is None
        assert u.remark is None

    def test_items_empty_rejected(self):
        with pytest.raises(ValidationError):
            OrderUpdate(items=[])

    def test_customer_id_invalid(self):
        with pytest.raises(ValidationError):
            OrderUpdate(customer_id="bad")


# ═══════════════════════════════════════════════════════
# 6. PaymentCreate 边界
# ═══════════════════════════════════════════════════════


class TestPaymentCreate:
    def test_amount_positive(self):
        p = PaymentCreate(amount="100.50", payment_method="cash")
        assert p.amount == "100.50"

    def test_amount_zero_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="0", payment_method="cash")

    def test_amount_negative_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="-1.00", payment_method="cash")

    def test_amount_max(self):
        p = PaymentCreate(amount="9999999999.99", payment_method="cash")
        assert p.amount == "9999999999.99"

    def test_amount_exceeds_max(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="10000000000.00", payment_method="cash")

    def test_amount_invalid(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="abc", payment_method="cash")

    def test_payment_method_enum(self):
        for m in ("cash", "transfer", "wechat", "alipay", "other"):
            p = PaymentCreate(amount="10.00", payment_method=m)
            assert p.payment_method == m

    def test_payment_method_invalid(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="10.00", payment_method="crypto")

    def test_remark_max_500(self):
        p = PaymentCreate(amount="10.00", payment_method="cash", remark="r" * 500)
        assert len(p.remark) == 500

    def test_remark_exceeds(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount="10.00", payment_method="cash", remark="r" * 501)

    def test_remark_none_default(self):
        p = PaymentCreate(amount="10.00", payment_method="cash")
        assert p.remark is None


# ═══════════════════════════════════════════════════════
# 7. InventoryAdjust 边界
# ═══════════════════════════════════════════════════════


class TestInventoryAdjust:
    def test_quantity_positive(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=100)
        assert a.quantity_change == 100

    def test_quantity_negative(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=-100)
        assert a.quantity_change == -100

    def test_quantity_zero(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=0)
        assert a.quantity_change == 0

    def test_quantity_max(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=9999999)
        assert a.quantity_change == 9999999

    def test_quantity_min(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=-9999999)
        assert a.quantity_change == -9999999

    def test_quantity_exceeds_max(self):
        with pytest.raises(ValidationError):
            InventoryAdjust(product_id=_UUID, quantity_change=10000000)

    def test_quantity_exceeds_min(self):
        with pytest.raises(ValidationError):
            InventoryAdjust(product_id=_UUID, quantity_change=-10000000)

    def test_product_id_invalid(self):
        with pytest.raises(ValidationError):
            InventoryAdjust(product_id="bad", quantity_change=1)

    def test_remark_max_500(self):
        a = InventoryAdjust(product_id=_UUID, quantity_change=1, remark="r" * 500)
        assert len(a.remark) == 500

    def test_remark_exceeds(self):
        with pytest.raises(ValidationError):
            InventoryAdjust(product_id=_UUID, quantity_change=1, remark="r" * 501)


# ═══════════════════════════════════════════════════════
# 8. Auth schema 边界
# ═══════════════════════════════════════════════════════


class TestLoginRequest:
    def test_username_min_1(self):
        r = LoginRequest(username="a", password="TestPass123!")
        assert r.username == "a"

    def test_username_empty_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="TestPass123!")

    def test_username_max_50(self):
        r = LoginRequest(username="a" * 50, password="TestPass123!")
        assert len(r.username) == 50

    def test_username_exceeds_50(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="a" * 51, password="TestPass123!")

    def test_password_empty_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="user", password="")


class TestUserCreate:
    def test_username_min_2(self):
        u = UserCreate(username="ab", password="TestPass123!")
        assert u.username == "ab"

    def test_username_min_1_rejected(self):
        """UserCreate username 最短 2 字符"""
        with pytest.raises(ValidationError):
            UserCreate(username="a", password="TestPass123!")

    def test_username_max_50(self):
        u = UserCreate(username="a" * 50, password="TestPass123!")
        assert len(u.username) == 50

    def test_username_exceeds_50(self):
        with pytest.raises(ValidationError):
            UserCreate(username="a" * 51, password="TestPass123!")

    def test_password_min_6(self):
        u = UserCreate(username="user1", password="Abc1!x")
        assert u.password == "Abc1!x"

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(username="user1", password="Ab1!")

    def test_password_max_100(self):
        pwd = "A" * 40 + "a" * 40 + "1!xx"
        u = UserCreate(username="user1", password=pwd)
        assert len(u.password) == 84

    def test_password_exceeds_100(self):
        with pytest.raises(ValidationError):
            UserCreate(username="user1", password="A" * 50 + "a" * 50 + "1!")

    def test_role_ids_valid(self):
        u = UserCreate(username="user1", password="TestPass123!", role_ids=[_UUID])
        assert u.role_ids == [_UUID]

    def test_role_ids_invalid_uuid(self):
        with pytest.raises(ValidationError):
            UserCreate(username="user1", password="TestPass123!", role_ids=["bad"])

    def test_role_ids_max_50(self):
        ids = [f"00000000-0000-0000-0000-{i:012d}" for i in range(50)]
        u = UserCreate(username="user1", password="TestPass123!", role_ids=ids)
        assert len(u.role_ids) == 50

    def test_role_ids_exceeds_50(self):
        ids = [f"00000000-0000-0000-0000-{i:012d}" for i in range(51)]
        with pytest.raises(ValidationError):
            UserCreate(username="user1", password="TestPass123!", role_ids=ids)

    def test_display_name_max_100(self):
        u = UserCreate(username="user1", password="TestPass123!", display_name="名" * 100)
        assert len(u.display_name) == 100

    def test_display_name_exceeds_100(self):
        with pytest.raises(ValidationError):
            UserCreate(username="user1", password="TestPass123!", display_name="名" * 101)

    def test_defaults(self):
        u = UserCreate(username="user1", password="TestPass123!")
        assert u.display_name is None
        assert u.phone is None
        assert u.email is None
        assert u.role_ids == []


class TestUserUpdate:
    def test_all_none(self):
        u = UserUpdate()
        assert u.display_name is None
        assert u.is_active is None
        assert u.role_ids is None

    def test_role_ids_invalid(self):
        with pytest.raises(ValidationError):
            UserUpdate(role_ids=["bad"])

    def test_display_name_exceeds_100(self):
        with pytest.raises(ValidationError):
            UserUpdate(display_name="名" * 101)


class TestChangePasswordRequest:
    def test_valid(self):
        r = ChangePasswordRequest(old_password="OldPass123!", new_password="NewPass123!")
        assert r.new_password == "NewPass123!"

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(old_password="OldPass123!", new_password="Ab1!")

    def test_old_password_empty(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(old_password="", new_password="NewPass123!")


class TestRefreshRequest:
    def test_valid(self):
        r = RefreshRequest(refresh_token="some-token")
        assert r.refresh_token == "some-token"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="")

    def test_max_length_2048(self):
        r = RefreshRequest(refresh_token="t" * 2048)
        assert len(r.refresh_token) == 2048

    def test_exceeds_2048(self):
        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="t" * 2049)
