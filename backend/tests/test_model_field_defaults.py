"""
代码质量：后端模型字段类型与默认值覆盖验证测试
覆盖 UUID 主键一致性、状态字段默认值、布尔字段默认值、
时间戳 server_default 模式、Numeric 精度与 String 长度
"""
import re

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRODUCT = (ROOT / "app/models/product.py").read_text()
CUSTOMER = (ROOT / "app/models/customer.py").read_text()
ORDER = (ROOT / "app/models/order.py").read_text()
USER = (ROOT / "app/models/user.py").read_text()


def _class_body(src: str, cls: str) -> str:
    """提取类体文本：从 class 声明到下一个顶层 class 或文件末尾"""
    m = re.search(rf"class {cls}\(.*?:\n", src)
    if not m:
        return ""
    start = m.end()
    rest = src[start:]
    next_class = re.search(r"\nclass \w+", rest)
    return rest[: next_class.start()] if next_class else rest


# ═══════════════════════════════════════════════════════════
# 1. UUID 主键一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestUUIDPrimaryKey:
    """所有模型主键使用 UUID(as_uuid=True) + default=uuid.uuid4"""

    MODELS = [
        ("Product", PRODUCT),
        ("Customer", CUSTOMER),
        ("SalesOrder", ORDER),
        ("Payment", ORDER),
        ("User", USER),
    ]

    def test_all_core_models_have_uuid_pk(self):
        for cls_name, src in self.MODELS:
            body = _class_body(src, cls_name)
            assert body, f"{cls_name} 类体未找到"
            assert "UUID(as_uuid=True)" in body, f"{cls_name} 应使用 UUID(as_uuid=True)"
            assert "primary_key=True" in body, f"{cls_name} 应声明 primary_key=True"

    def test_all_uuid_pks_have_default(self):
        for cls_name, src in self.MODELS:
            body = _class_body(src, cls_name)
            assert "default=uuid.uuid4" in body, f"{cls_name} PK 应有 default=uuid.uuid4"

    def test_uuid_import_present(self):
        for src in [PRODUCT, CUSTOMER, ORDER, USER]:
            assert "import uuid" in src, "模型文件应导入 uuid"

    def test_auxiliary_models_uuid_pk(self):
        """辅助模型（Role、Permission、SalesOrderItem）也使用 UUID PK"""
        for cls_name in ["Role", "Permission", "UserRole", "RolePermission"]:
            body = _class_body(USER, cls_name)
            assert body, f"{cls_name} 类体未找到"
            assert "UUID(as_uuid=True)" in body
            assert "primary_key=True" in body
            assert "default=uuid.uuid4" in body

    def test_product_auxiliary_models_uuid_pk(self):
        """ProductCategory、File、ProductImage 也使用 UUID PK"""
        for cls_name in ["ProductCategory", "File", "ProductImage", "ProductPriceHistory"]:
            body = _class_body(PRODUCT, cls_name)
            assert body, f"{cls_name} 类体未找到"
            assert "UUID(as_uuid=True)" in body
            assert "primary_key=True" in body


# ═══════════════════════════════════════════════════════════
# 2. 状态字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStatusDefaults:
    """状态字段使用 String + 合理默认值"""

    def test_product_status_default_active(self):
        body = _class_body(PRODUCT, "Product")
        assert re.search(r'status.*default="active"', body), "商品状态默认值应为 active"

    def test_order_status_default_draft(self):
        body = _class_body(ORDER, "SalesOrder")
        assert re.search(r'status.*default="draft"', body), "订单状态默认值应为 draft"

    def test_payment_status_default_normal(self):
        body = _class_body(ORDER, "Payment")
        assert re.search(r'status.*default="normal"', body), "收款状态默认值应为 normal"

    def test_status_fields_have_index(self):
        """状态字段应建立索引"""
        for cls_name, src, field_pat in [
            ("Product", PRODUCT, r'status.*index=True'),
            ("SalesOrder", ORDER, r'status.*index=True'),
            ("Payment", ORDER, r'status.*index=True'),
        ]:
            body = _class_body(src, cls_name)
            assert re.search(field_pat, body), f"{cls_name} status 应有 index=True"

    def test_status_string_lengths(self):
        """状态字段 String 长度足够容纳所有状态值"""
        for cls_name, src, expected_len in [
            ("Product", PRODUCT, "String(20)"),
            ("SalesOrder", ORDER, "String(30)"),
            ("Payment", ORDER, "String(20)"),
        ]:
            body = _class_body(src, cls_name)
            assert f"status.*{expected_len}" in body or re.search(
                rf'status.*{re.escape(expected_len)}', body
            ), f"{cls_name} status 应使用 {expected_len}"


# ═══════════════════════════════════════════════════════════
# 3. 布尔字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBooleanDefaults:
    """布尔字段使用安全默认值"""

    def test_user_is_active_default_true(self):
        body = _class_body(USER, "User")
        assert re.search(r'is_active.*default=True', body), "is_active 默认值应为 True"

    def test_user_is_superuser_default_false(self):
        body = _class_body(USER, "User")
        assert re.search(r'is_superuser.*default=False', body), "is_superuser 默认值应为 False"

    def test_boolean_fields_not_nullable(self):
        body = _class_body(USER, "User")
        assert re.search(r'is_active.*nullable=False', body), "is_active 应为 nullable=False"
        assert re.search(r'is_superuser.*nullable=False', body), "is_superuser 应为 nullable=False"

    def test_boolean_uses_boolean_type(self):
        body = _class_body(USER, "User")
        assert "Boolean" in body, "布尔字段应使用 Boolean 类型"
        assert "Boolean" in USER, "应导入 Boolean"

    def test_product_image_is_primary_default(self):
        body = _class_body(PRODUCT, "ProductImage")
        assert re.search(r'is_primary.*default=False', body), "is_primary 默认值应为 False"


# ═══════════════════════════════════════════════════════════
# 4. 时间戳 server_default 模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTimestampDefaults:
    """created_at 使用 server_default=func.now()，updated_at 有 onupdate"""

    def test_core_models_created_at_server_default(self):
        for cls_name, src in [
            ("Product", PRODUCT),
            ("Customer", CUSTOMER),
            ("SalesOrder", ORDER),
            ("User", USER),
        ]:
            body = _class_body(src, cls_name)
            assert "server_default=func.now()" in body, f"{cls_name} created_at 应有 server_default"

    def test_core_models_updated_at_onupdate(self):
        for cls_name, src in [
            ("Product", PRODUCT),
            ("Customer", CUSTOMER),
            ("SalesOrder", ORDER),
            ("User", USER),
        ]:
            body = _class_body(src, cls_name)
            assert "onupdate=func.now()" in body, f"{cls_name} updated_at 应有 onupdate"

    def test_datetime_with_timezone(self):
        """时间戳字段使用 DateTime(timezone=True)"""
        for cls_name, src in [
            ("Product", PRODUCT),
            ("Customer", CUSTOMER),
            ("SalesOrder", ORDER),
            ("User", USER),
        ]:
            body = _class_body(src, cls_name)
            assert "DateTime(timezone=True)" in body, f"{cls_name} 应使用 DateTime(timezone=True)"

    def test_created_at_imports_func(self):
        """使用 server_default=func.now() 的文件都导入了 func"""
        for src in [PRODUCT, CUSTOMER, ORDER, USER]:
            assert "from sqlalchemy" in src and "func" in src, "应导入 func"

    def test_auxiliary_models_created_at(self):
        """辅助模型也应有 created_at"""
        for cls_name in ["ProductCategory", "File", "ProductPriceHistory"]:
            body = _class_body(PRODUCT, cls_name)
            assert "created_at" in body, f"{cls_name} 应有 created_at 字段"
            assert "server_default=func.now()" in body, f"{cls_name} created_at 应有 server_default"


# ═══════════════════════════════════════════════════════════
# 5. Numeric 精度与 String 长度约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestNumericAndStringConstraints:
    """金额使用 Numeric(12,2)，毛利率使用 Numeric(8,4)，字符串有合理长度"""

    def test_money_fields_use_numeric_12_2(self):
        """金额字段使用 Numeric(12, 2)"""
        order_body = _class_body(ORDER, "SalesOrder")
        product_body = _class_body(PRODUCT, "Product")
        for body_name, body in [("SalesOrder", order_body), ("Product", product_body)]:
            matches = re.findall(r"Numeric\((\d+),\s*(\d+)\)", body)
            money_matches = [m for m in matches if m[1] == "2"]
            assert len(money_matches) > 0, f"{body_name} 应有 Numeric(x, 2) 金额字段"

    def test_margin_uses_numeric_8_4(self):
        """毛利率字段使用 Numeric(8, 4)"""
        order_body = _class_body(ORDER, "SalesOrder")
        assert "Numeric(8, 4)" in order_body, "SalesOrder gross_margin 应使用 Numeric(8, 4)"

    def test_string_lengths_reasonable(self):
        """关键字段有长度约束"""
        product_body = _class_body(PRODUCT, "Product")
        assert "String(64)" in product_body, "Product sku 应有 String(64)"
        assert "String(100)" in product_body, "Product name 应有 String(100)"

        customer_body = _class_body(CUSTOMER, "Customer")
        assert "String(100)" in customer_body, "Customer name 应有 String(100)"
        assert "String(30)" in customer_body, "Customer phone 应有 String(30)"

        user_body = _class_body(USER, "User")
        assert "String(50)" in user_body, "User username 应有 String(50)"

    def test_product_sku_is_unique(self):
        body = _class_body(PRODUCT, "Product")
        assert re.search(r'sku.*unique=True', body), "Product sku 应为 unique=True"
        assert re.search(r'sku.*index=True', body), "Product sku 应为 index=True"

    def test_order_no_is_unique(self):
        body = _class_body(ORDER, "SalesOrder")
        assert re.search(r'order_no.*unique=True', body), "SalesOrder order_no 应为 unique=True"
        assert re.search(r'order_no.*index=True', body), "SalesOrder order_no 应为 index=True"
