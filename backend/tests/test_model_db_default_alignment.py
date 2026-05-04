"""
代码质量：后端模型默认值与数据库列默认对齐验证测试
覆盖状态字段默认值、布尔字段默认值、时间戳字段默认值、
数值字段默认值、主键与 ID 默认值
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODELS_DIR = ROOT / "app" / "models"

PRODUCT_SRC = (MODELS_DIR / "product.py").read_text()
CUSTOMER_SRC = (MODELS_DIR / "customer.py").read_text()
ORDER_SRC = (MODELS_DIR / "order.py").read_text()
USER_SRC = (MODELS_DIR / "user.py").read_text()
AUDIT_SRC = (MODELS_DIR / "audit.py").read_text()

ALL_MODELS = {
    "product": PRODUCT_SRC,
    "customer": CUSTOMER_SRC,
    "order": ORDER_SRC,
    "user": USER_SRC,
    "audit": AUDIT_SRC,
}


def _get_column_def(src: str, field_name: str) -> str:
    """提取字段完整的 mapped_column(...) 或 Column(...) 定义（跨行）"""
    m = re.search(rf"{field_name}\s*[:=]", src)
    if not m:
        return ""
    rest = src[m.end():]
    # 找到 mapped_column( 或 Column( 的开始
    mc = re.search(r"(?:mapped_column|Column)\(", rest)
    if not mc:
        return ""
    # 从 ( 开始，匹配到平衡的 )
    start = mc.end()
    depth = 1
    i = start
    while i < len(rest) and depth > 0:
        if rest[i] == '(':
            depth += 1
        elif rest[i] == ')':
            depth -= 1
        i += 1
    return rest[start:i - 1]


def _find_column_default(src: str, field_name: str) -> str | None:
    """提取字段的 default= 值"""
    col_def = _get_column_def(src, field_name)
    if not col_def:
        return None
    m = re.search(r"default\s*=\s*([^,\)]+)", col_def)
    return m.group(1).strip() if m else None


def _find_server_default(src: str, field_name: str) -> str | None:
    """提取字段的 server_default= 值"""
    col_def = _get_column_def(src, field_name)
    if not col_def:
        return None
    # server_default=func.now() 中的 func.now() 含括号，需要特殊处理
    m = re.search(r"server_default\s*=\s*(func\.now\(\)|[^,\)]+)", col_def)
    return m.group(1).strip() if m else None


def _has_field(src: str, field_name: str) -> bool:
    """检查模型是否定义了指定字段"""
    return bool(_get_column_def(src, field_name))


# ═══════════════════════════════════════════════════════════
# 1. 状态字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStatusFieldDefaults:
    """状态字段使用合理的默认值"""

    def test_product_status_defaults_to_active(self):
        """Product.status 默认 'active'"""
        val = _find_column_default(PRODUCT_SRC, "status")
        assert val is not None, "Product 应定义 status 字段并设 default"
        assert '"active"' in val, f"Product.status 默认值应为 'active'，实际 {val}"

    def test_order_status_defaults_to_draft(self):
        """SalesOrder.status 默认 'draft'"""
        val = _find_column_default(ORDER_SRC, "status")
        assert val is not None, "SalesOrder 应定义 status 字段并设 default"
        assert '"draft"' in val, f"SalesOrder.status 默认值应为 'draft'，实际 {val}"

    def test_payment_status_defaults_to_normal(self):
        """Payment.status 默认 'normal'"""
        val = _find_column_default(ORDER_SRC, "status")
        # Payment 在 order.py 中，需确认 Payment 类
        assert "normal" in ORDER_SRC, "Payment.status 应有 'normal' 值"
        # 验证 Payment 类中有 status 字段
        m = re.search(r"class Payment\(", ORDER_SRC)
        assert m, "应定义 Payment 类"
        body = ORDER_SRC[m.end():]
        next_class = re.search(r"\nclass \w", body)
        payment_body = body[:next_class.start()] if next_class else body
        assert re.search(r'status.*default.*"normal"', payment_body), (
            "Payment.status 默认值应为 'normal'"
        )

    def test_status_fields_use_string_type(self):
        """状态字段使用 String 类型"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "status")
            if col_def:
                assert "String" in col_def, f"{name} status 字段应使用 String 类型"

    def test_status_fields_have_length_constraint(self):
        """状态字段有长度约束"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "status")
            if col_def:
                assert re.search(r"String\(\d+\)", col_def), (
                    f"{name} status 字段应有 String(N) 长度约束"
                )


# ═══════════════════════════════════════════════════════════
# 2. 布尔字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBooleanFieldDefaults:
    """布尔字段使用合理的默认值"""

    def test_user_is_active_defaults_to_true(self):
        """User.is_active 默认 True"""
        val = _find_column_default(USER_SRC, "is_active")
        assert val is not None, "User 应定义 is_active 并设 default"
        assert "True" in val, f"User.is_active 默认应为 True，实际 {val}"

    def test_user_is_superuser_defaults_to_false(self):
        """User.is_superuser 默认 False"""
        val = _find_column_default(USER_SRC, "is_superuser")
        assert val is not None, "User 应定义 is_superuser 并设 default"
        assert "False" in val, f"User.is_superuser 默认应为 False，实际 {val}"

    def test_product_image_is_primary_defaults_to_false(self):
        """ProductImage.is_primary 默认 False"""
        val = _find_column_default(PRODUCT_SRC, "is_primary")
        assert val is not None, "ProductImage 应定义 is_primary 并设 default"
        assert "False" in val, f"ProductImage.is_primary 默认应为 False，实际 {val}"

    def test_boolean_fields_use_boolean_type(self):
        """布尔字段使用 Boolean 或 Mapped[bool] 类型"""
        for name, src in ALL_MODELS.items():
            for m in re.finditer(r"(is_\w+)\s*[:=]", src):
                field = m.group(1)
                col_def = _get_column_def(src, field)
                if col_def:
                    # mapped_column(Boolean, ...) 或 Mapped[bool] = mapped_column(...)
                    line_start = src[:src.find(field)].rfind("\n") + 1
                    line = src[line_start:src.find("mapped_column", line_start) + 50] if "mapped_column" in src[line_start:] else ""
                    assert "Boolean" in col_def or "Mapped[bool]" in line or "bool" in col_def, (
                        f"{name}.{field} 应使用 Boolean 类型或 Mapped[bool]"
                    )

    def test_boolean_fields_have_explicit_default(self):
        """布尔字段有明确的 default 值（不允许隐式 None）"""
        for name, src in ALL_MODELS.items():
            for m in re.finditer(r"(is_\w+)\s*[:=]", src):
                field = m.group(1)
                col_def = _get_column_def(src, field)
                if col_def:
                    assert "default=" in col_def, f"{name}.{field} 应设置显式 default 值"


# ═══════════════════════════════════════════════════════════
# 3. 时间戳字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTimestampFieldDefaults:
    """时间戳字段使用 server_default=func.now()"""

    def test_created_at_uses_server_default(self):
        """created_at 使用 server_default=func.now()"""
        for name, src in ALL_MODELS.items():
            if _has_field(src, "created_at"):
                sd = _find_server_default(src, "created_at")
                assert sd is not None, f"{name}.created_at 应设置 server_default"
                assert "func.now()" in sd, f"{name}.created_at 应使用 func.now()"

    def test_updated_at_uses_server_default_with_onupdate(self):
        """updated_at 使用 server_default + onupdate"""
        for name, src in ALL_MODELS.items():
            if _has_field(src, "updated_at"):
                col_def = _get_column_def(src, "updated_at")
                assert col_def, f"{name}.updated_at 列定义未找到"
                assert "server_default" in col_def, f"{name}.updated_at 应设置 server_default"
                assert "func.now()" in col_def, f"{name}.updated_at 应使用 func.now()"
                assert "onupdate" in col_def, f"{name}.updated_at 应设置 onupdate"

    def test_deleted_at_is_nullable(self):
        """deleted_at 是可空字段（软删除标记）"""
        for name, src in ALL_MODELS.items():
            if _has_field(src, "deleted_at"):
                col_def = _get_column_def(src, "deleted_at")
                assert col_def, f"{name} deleted_at 列定义未找到"
                # mapped_column(DateTime(timezone=True), index=True) 没有 nullable=False 即为可空
                assert "nullable=False" not in col_def, (
                    f"{name}.deleted_at 不应设为 nullable=False"
                )

    def test_deleted_at_has_no_server_default(self):
        """deleted_at 没有默认值（由软删除操作显式设置）"""
        for name, src in ALL_MODELS.items():
            if _has_field(src, "deleted_at"):
                sd = _find_server_default(src, "deleted_at")
                assert sd is None, f"{name}.deleted_at 不应有 server_default"

    def test_timestamp_fields_use_datetime_type(self):
        """时间戳字段使用 DateTime 类型"""
        for name, src in ALL_MODELS.items():
            for field in ["created_at", "updated_at", "deleted_at"]:
                if _has_field(src, field):
                    col_def = _get_column_def(src, field)
                    assert "DateTime" in col_def, f"{name}.{field} 应使用 DateTime 类型"


# ═══════════════════════════════════════════════════════════
# 4. 数值字段默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestNumericFieldDefaults:
    """数值字段使用合理的默认值"""

    def test_product_prices_default_to_zero(self):
        """Product 的 sale_price 和 cost_price 默认 0"""
        for field in ["sale_price", "cost_price"]:
            val = _find_column_default(PRODUCT_SRC, field)
            assert val is not None, f"Product.{field} 应设置 default"
            assert '"0"' in val or "0" in val, f"Product.{field} 默认应为 0，实际 {val}"

    def test_order_amounts_default_to_zero(self):
        """SalesOrder 的金额字段默认 0"""
        for field in ["total_amount", "paid_amount"]:
            val = _find_column_default(ORDER_SRC, field)
            assert val is not None, f"SalesOrder.{field} 应设置 default"
            assert '"0"' in val or "0" in val, f"SalesOrder.{field} 默认应为 0"

    def test_product_stock_defaults_to_zero(self):
        """Product.stock_quantity 默认 0"""
        val = _find_column_default(PRODUCT_SRC, "stock_quantity")
        assert val is not None, "Product.stock_quantity 应设置 default"
        assert val == "0", f"Product.stock_quantity 默认应为 0，实际 {val}"

    def test_numeric_fields_use_numeric_type(self):
        """金额字段使用 Numeric 类型（非 Float）"""
        for name, src in ALL_MODELS.items():
            for field_name in ["total_amount", "paid_amount", "sale_price", "cost_price", "gross_profit", "amount"]:
                if _has_field(src, field_name):
                    col_def = _get_column_def(src, field_name)
                    if col_def:
                        assert "Numeric" in col_def, f"{name}.{field_name} 应使用 Numeric 类型"
                        assert "Float" not in col_def, f"{name}.{field_name} 不应使用 Float 类型"

    def test_discount_fields_default_to_zero(self):
        """折扣字段默认 0"""
        val = _find_column_default(ORDER_SRC, "discount_amount")
        assert val is not None, "SalesOrderItem.discount_amount 应设置 default"
        assert '"0"' in val or "0" in val, "discount_amount 默认应为 0"


# ═══════════════════════════════════════════════════════════
# 5. 主键与 ID 默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPrimaryKeyDefaults:
    """主键字段使用 uuid.uuid4 默认值"""

    def test_all_models_use_uuid_primary_key(self):
        """所有模型使用 UUID 类型主键"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "id")
            if col_def:
                assert "UUID" in col_def or "uuid" in col_def.lower(), (
                    f"{name}.id 应使用 UUID 类型"
                )

    def test_id_fields_use_uuid4_default(self):
        """ID 字段使用 uuid.uuid4 作为默认值"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "id")
            if col_def:
                assert "uuid.uuid4" in col_def or "uuid4" in col_def, (
                    f"{name}.id 应使用 uuid.uuid4 默认值"
                )

    def test_id_fields_are_primary_key(self):
        """ID 字段声明为 primary_key"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "id")
            if col_def:
                assert "primary_key" in col_def, f"{name}.id 应为 primary_key"

    def test_no_server_default_for_uuid_ids(self):
        """UUID ID 字段不设置 server_default（由 Python 端生成）"""
        for name, src in ALL_MODELS.items():
            col_def = _get_column_def(src, "id")
            if col_def:
                assert "server_default" not in col_def, (
                    f"{name}.id 不应设置 server_default"
                )

    def test_sort_order_fields_default_to_zero(self):
        """排序字段默认 0"""
        for name, src in ALL_MODELS.items():
            for m in re.finditer(r"(sort_order|sort_weight)\s*=\s*Column\([^)]*?default\s*=\s*([^,\)]+)", src):
                field = m.group(1)
                val = m.group(2).strip()
                assert val == "0", f"{name}.{field} 默认应为 0，实际 {val}"
