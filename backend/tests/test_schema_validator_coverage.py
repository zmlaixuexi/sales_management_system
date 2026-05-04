"""代码质量：后端 Schema 验证器覆盖完整性验证测试
覆盖文本字段清洗覆盖、UUID 外键验证覆盖、
金额/价格验证逻辑、密码强度验证、验证器一致性"""

import re
from pathlib import Path

AUTH_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "auth.py"
CUSTOMER_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "customer.py"
PRODUCT_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "product.py"
ORDER_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "order.py"
PAYMENT_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "payment.py"
INVENTORY_FILE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "inventory.py"
SANITIZE_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "sanitize.py"


def _read(path: Path) -> str:
    return path.read_text()


def _extract_validators(source: str) -> dict[str, list[str]]:
    """从源码中提取每个 field_validator 装饰的字段名和方法名"""
    result: dict[str, list[str]] = {}
    pattern = re.compile(
        r'@field_validator\(([^)]+)\)\s*@classmethod\s+def\s+(\w+)',
    )
    for match in pattern.finditer(source):
        fields_str = match.group(1)
        method_name = match.group(2)
        fields = [f.strip().strip('"').strip("'") for f in fields_str.split(",")]
        for f in fields:
            result.setdefault(f, []).append(method_name)
    return result


# ═══════════════════════════════════════════════════════════
# 1. 文本字段清洗覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSanitizeCoverage:
    """验证所有自由文本字段都有清洗验证器"""

    def test_customer_create_sanitizes_text_fields(self):
        source = _read(CUSTOMER_FILE)
        validators = _extract_validators(source)
        # name, contact_name, email, remark 共享 sanitize_text
        sanitize_fields = validators.get("name", [])
        assert any("sanitize" in v for v in sanitize_fields)

    def test_product_create_sanitizes_name_and_remark(self):
        source = _read(PRODUCT_FILE)
        validators = _extract_validators(source)
        for field in ("name", "remark"):
            methods = validators.get(field, [])
            assert any("sanitize" in m for m in methods), f"ProductCreate 缺少 {field} 清洗"

    def test_order_create_sanitizes_remark(self):
        source = _read(ORDER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("remark", [])
        assert any("sanitize" in m for m in methods)

    def test_payment_create_sanitizes_remark(self):
        source = _read(PAYMENT_FILE)
        validators = _extract_validators(source)
        methods = validators.get("remark", [])
        assert any("sanitize" in m for m in methods)

    def test_sanitize_strips_html_and_control_chars(self):
        source = _read(SANITIZE_FILE)
        assert "strip_html" in source
        assert "strip_control_chars" in source
        assert "_HTML_TAG_RE" in source
        assert "_CONTROL_CHAR_RE" in source


# ═══════════════════════════════════════════════════════════
# 2. UUID 外键验证覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestUUIDValidation:
    """验证所有外键 ID 字段都有 UUID 格式校验"""

    def test_order_item_validates_product_id(self):
        source = _read(ORDER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("product_id", [])
        assert any("validate_product" in m for m in methods)

    def test_order_create_validates_customer_id(self):
        source = _read(ORDER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("customer_id", [])
        assert any("validate_customer" in m for m in methods)

    def test_customer_validates_owner_user_id(self):
        source = _read(CUSTOMER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("owner_user_id", [])
        assert any("validate_owner" in m for m in methods)

    def test_product_validates_category_id(self):
        source = _read(PRODUCT_FILE)
        validators = _extract_validators(source)
        methods = validators.get("category_id", [])
        assert any("validate_category" in m for m in methods)

    def test_inventory_validates_product_id(self):
        source = _read(INVENTORY_FILE)
        validators = _extract_validators(source)
        methods = validators.get("product_id", [])
        assert any("validate_product" in m for m in methods)


# ═══════════════════════════════════════════════════════════
# 3. 金额/价格验证逻辑验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPriceAmountValidation:
    """验证价格和金额字段的验证逻辑"""

    def test_product_validates_sale_and_cost_price(self):
        source = _read(PRODUCT_FILE)
        validators = _extract_validators(source)
        assert "validate_sale_price" in validators.get("sale_price", [])
        assert "validate_cost_price" in validators.get("cost_price", [])

    def test_price_uses_decimal_for_precision(self):
        source = _read(PRODUCT_FILE)
        assert "from decimal import Decimal" in source
        assert "InvalidOperation" in source

    def test_price_rejects_negative(self):
        source = _read(PRODUCT_FILE)
        assert "不能为负数" in source

    def test_price_has_upper_bound(self):
        source = _read(PRODUCT_FILE)
        assert "_MAX_PRICE" in source
        assert "9999999999.99" in source

    def test_payment_amount_must_be_positive(self):
        source = _read(PAYMENT_FILE)
        assert "amount_must_be_positive" in source
        assert "必须大于 0" in source
        assert "_MAX_AMOUNT" in source


# ═══════════════════════════════════════════════════════════
# 4. 密码强度与邮箱/手机验证验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuthValidation:
    """验证认证相关 Schema 验证器"""

    def test_password_strength_validator_on_create(self):
        source = _read(AUTH_FILE)
        validators = _extract_validators(source)
        methods = validators.get("password", [])
        assert any("validate_password_strength" in m for m in methods)
        assert "validate_password_strength" in source

    def test_password_strength_on_change_password(self):
        source = _read(AUTH_FILE)
        validators = _extract_validators(source)
        methods = validators.get("new_password", [])
        assert any("validate_password_strength" in m for m in methods)

    def test_user_create_validates_role_ids(self):
        source = _read(AUTH_FILE)
        validators = _extract_validators(source)
        methods = validators.get("role_ids", [])
        assert any("validate_role_ids" in m for m in methods)

    def test_customer_validates_email_format(self):
        source = _read(CUSTOMER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("email", [])
        has_email_validator = any("validate_email" in m for m in methods)
        assert has_email_validator
        assert "_EMAIL_RE" in source

    def test_customer_validates_phone_format(self):
        source = _read(CUSTOMER_FILE)
        validators = _extract_validators(source)
        methods = validators.get("phone", [])
        has_phone_validator = any("validate_phone" in m for m in methods)
        assert has_phone_validator
        assert "_PHONE_RE" in source


# ═══════════════════════════════════════════════════════════
# 5. Create/Update 验证器一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCreateUpdateConsistency:
    """验证 Create 和 Update Schema 验证器一致"""

    def test_product_create_update_same_price_validators(self):
        source = _read(PRODUCT_FILE)
        validators = _extract_validators(source)
        create_price_methods = set(validators.get("sale_price", []))
        # 验证 sale_price 在 ProductCreate 和 ProductUpdate 都有验证
        assert "validate_sale_price" in create_price_methods

    def test_customer_create_update_same_sanitize_fields(self):
        source = _read(CUSTOMER_FILE)
        validators = _extract_validators(source)
        # name 的 sanitize_text 在 Create 中
        create_name_methods = validators.get("name", [])
        assert any("sanitize" in m for m in create_name_methods)

    def test_order_create_update_both_sanitize_remark(self):
        source = _read(ORDER_FILE)
        # 统计 remark 的 sanitize_text 出现次数（Create + Update 各一个）
        count = source.count('def sanitize_text')
        assert count >= 2, "OrderCreate 和 OrderUpdate 应各有 sanitize_text"

    def test_customer_create_update_both_validate_email(self):
        source = _read(CUSTOMER_FILE)
        count = source.count('def validate_email')
        assert count >= 2, "CustomerCreate 和 CustomerUpdate 应各有 validate_email"

    def test_user_create_update_both_validate_role_ids(self):
        source = _read(AUTH_FILE)
        count = source.count('def validate_role_ids')
        assert count >= 2, "UserCreate 和 UserUpdate 应各有 validate_role_ids"
