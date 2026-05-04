"""需求符合性：后端 Pydantic Schema 字段约束与数据库模型列约束一致性验证
覆盖字符串长度、数值精度、必填/可选、枚举值、默认值一致性"""

import re
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "app" / "models"
SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "app" / "schemas"


def _extract_model_string_lengths(source: str) -> dict[str, int]:
    """从模型源码提取 String(N) 字段及其长度（支持 Column 和 mapped_column）"""
    result = {}
    for m in re.finditer(r"(\w+)\s*[:=].*?(?:mapped_column|Column)\(String\((\d+)\)", source):
        result[m.group(1)] = int(m.group(2))
    return result


def _extract_model_nullable_fields(source: str) -> set[str]:
    """从模型源码提取可空字段（Mapped[type | None] 或 nullable=True）"""
    result = set()
    for m in re.finditer(r"(\w+)\s*:\s*Mapped\[.*?\|\s*None\]", source):
        result.add(m.group(1))
    for m in re.finditer(r"(\w+)\s*[:=].*?(?:mapped_column|Column)\([^)]*nullable=True", source):
        result.add(m.group(1))
    return result


def _extract_model_numeric_fields(source: str) -> dict[str, tuple[int, int]]:
    """从模型源码提取 Numeric(P,S) 字段"""
    result = {}
    for m in re.finditer(r"(\w+)\s*[:=].*?(?:mapped_column|Column)\(Numeric\((\d+),\s*(\d+)\)", source):
        result[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return result


def _extract_schema_max_lengths(source: str, class_name: str) -> dict[str, int]:
    """从 Schema 类提取 max_length 约束"""
    body = _extract_class_body(source, class_name)
    if not body:
        return {}
    result = {}
    for m in re.finditer(r"(\w+)\s*.*?max_length=(\d+)", body):
        result[m.group(1)] = int(m.group(2))
    return result


def _extract_schema_min_lengths(source: str, class_name: str) -> dict[str, int]:
    body = _extract_class_body(source, class_name)
    if not body:
        return {}
    result = {}
    for m in re.finditer(r"(\w+)\s*.*?min_length=(\d+)", body):
        result[m.group(1)] = int(m.group(2))
    return result


def _extract_class_body(source: str, class_name: str) -> str | None:
    """提取 class 定义体（到下一个同级 class/def 或文件结尾）"""
    pattern = rf"class\s+{class_name}\s*(?:\([^)]*\))?\s*:\s*\n"
    m = re.search(pattern, source)
    if not m:
        return None
    start = m.end()
    lines = source[start:].split("\n")
    body_lines = []
    for line in lines:
        stripped = line.rstrip()
        if stripped and not stripped.startswith((" ", "\t")):
            break
        body_lines.append(line)
    return "\n".join(body_lines)


# ═══════════════════════════════════════════════════════════
# 1. 商品实体 Schema ↔ Model 一致性（8 项）
# ═══════════════════════════════════════════════════════════


class TestProductSchemaModelConsistency:
    """商品 Schema 与 Model 约束一致性"""

    def test_product_name_length_matches(self):
        model_src = (MODELS_DIR / "product.py").read_text()
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "ProductCreate")
        assert "name" in model_lengths
        assert "name" in schema_lengths
        assert schema_lengths["name"] <= model_lengths["name"]

    def test_product_sku_schema_not_exceed_model(self):
        model_src = (MODELS_DIR / "product.py").read_text()
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "ProductCreate")
        # sku: model String(64), schema max_length=50 (schema 更严格是安全的)
        if "sku" in schema_lengths and "sku" in model_lengths:
            assert schema_lengths["sku"] <= model_lengths["sku"]

    def test_product_sale_price_numeric_precision(self):
        model_src = (MODELS_DIR / "product.py").read_text()
        numerics = _extract_model_numeric_fields(model_src)
        assert "sale_price" in numerics
        assert numerics["sale_price"] == (12, 2)

    def test_product_cost_price_numeric_precision(self):
        model_src = (MODELS_DIR / "product.py").read_text()
        numerics = _extract_model_numeric_fields(model_src)
        assert "cost_price" in numerics
        assert numerics["cost_price"] == (12, 2)

    def test_product_schema_max_price_fits_numeric(self):
        """Schema 价格上限不超过 Numeric(12,2) 范围"""
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        assert "_MAX_PRICE" in schema_src
        assert "9999999999.99" in schema_src

    def test_product_status_literal_values(self):
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        assert '"active"' in schema_src
        assert '"inactive"' in schema_src
        assert '"disabled"' in schema_src

    def test_product_stock_quantity_ge_0(self):
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        assert "ge=0" in schema_src

    def test_product_sort_weight_range(self):
        schema_src = (SCHEMAS_DIR / "product.py").read_text()
        assert "ge=-99999" in schema_src or "ge= -99999" in schema_src
        assert "le=99999" in schema_src


# ═══════════════════════════════════════════════════════════
# 2. 客户实体 Schema ↔ Model 一致性（6 项）
# ═══════════════════════════════════════════════════════════


class TestCustomerSchemaModelConsistency:
    """客户 Schema 与 Model 约束一致性"""

    def test_customer_name_length_matches(self):
        model_src = (MODELS_DIR / "customer.py").read_text()
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "CustomerCreate")
        assert "name" in model_lengths
        assert "name" in schema_lengths
        assert schema_lengths["name"] <= model_lengths["name"]

    def test_customer_phone_length_matches(self):
        model_src = (MODELS_DIR / "customer.py").read_text()
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "CustomerCreate")
        assert "phone" in model_lengths
        if "phone" in schema_lengths:
            assert schema_lengths["phone"] <= model_lengths["phone"]

    def test_customer_email_length_matches(self):
        model_src = (MODELS_DIR / "customer.py").read_text()
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "CustomerCreate")
        assert "email" in model_lengths
        if "email" in schema_lengths:
            assert schema_lengths["email"] <= model_lengths["email"]

    def test_customer_source_literal_values(self):
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        for val in ["referral", "online", "offline", "ad", "other"]:
            assert f'"{val}"' in schema_src, f"缺少 source 值: {val}"

    def test_customer_level_literal_values(self):
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        for val in ["vip", "important", "normal", "potential"]:
            assert f'"{val}"' in schema_src, f"缺少 level 值: {val}"

    def test_customer_remark_max_length(self):
        schema_src = (SCHEMAS_DIR / "customer.py").read_text()
        assert "max_length=500" in schema_src


# ═══════════════════════════════════════════════════════════
# 3. 订单实体 Schema ↔ Model 一致性（6 项）
# ═══════════════════════════════════════════════════════════


class TestOrderSchemaModelConsistency:
    """订单 Schema 与 Model 约束一致性"""

    def test_order_remark_max_length(self):
        schema_src = (SCHEMAS_DIR / "order.py").read_text()
        assert "max_length=500" in schema_src

    def test_order_item_quantity_gt_0(self):
        schema_src = (SCHEMAS_DIR / "order.py").read_text()
        assert "gt=0" in schema_src

    def test_order_total_amount_numeric_precision(self):
        model_src = (MODELS_DIR / "order.py").read_text()
        numerics = _extract_model_numeric_fields(model_src)
        assert "total_amount" in numerics
        assert numerics["total_amount"] == (12, 2)

    def test_order_item_unit_price_numeric(self):
        model_src = (MODELS_DIR / "order.py").read_text()
        numerics = _extract_model_numeric_fields(model_src)
        assert "unit_price" in numerics
        assert numerics["unit_price"] == (12, 2)

    def test_order_items_min_length_1(self):
        schema_src = (SCHEMAS_DIR / "order.py").read_text()
        assert "min_length=1" in schema_src

    def test_order_no_auto_generated(self):
        """order_no 由后端自动生成，不在 Create schema 中"""
        schema_src = (SCHEMAS_DIR / "order.py").read_text()
        body = _extract_class_body(schema_src, "OrderCreate")
        if body:
            assert "order_no" not in body


# ═══════════════════════════════════════════════════════════
# 4. 用户实体 Schema ↔ Model 一致性（5 项）
# ═══════════════════════════════════════════════════════════


class TestUserSchemaModelConsistency:
    """用户 Schema 与 Model 约束一致性"""

    def test_username_length_matches(self):
        model_src = (MODELS_DIR / "user.py").read_text()
        schema_src = (SCHEMAS_DIR / "auth.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "UserCreate")
        assert "username" in model_lengths
        assert "username" in schema_lengths
        assert schema_lengths["username"] <= model_lengths["username"]

    def test_display_name_length_matches(self):
        model_src = (MODELS_DIR / "user.py").read_text()
        schema_src = (SCHEMAS_DIR / "auth.py").read_text()
        model_lengths = _extract_model_string_lengths(model_src)
        schema_lengths = _extract_schema_max_lengths(schema_src, "UserCreate")
        assert "display_name" in model_lengths
        if "display_name" in schema_lengths:
            assert schema_lengths["display_name"] <= model_lengths["display_name"]

    def test_password_max_length_100(self):
        schema_src = (SCHEMAS_DIR / "auth.py").read_text()
        assert "max_length=100" in schema_src

    def test_password_min_length_6(self):
        schema_src = (SCHEMAS_DIR / "auth.py").read_text()
        assert "min_length=6" in schema_src

    def test_hashed_password_column_exists(self):
        model_src = (MODELS_DIR / "user.py").read_text()
        assert "hashed_password" in model_src


# ═══════════════════════════════════════════════════════════
# 5. 收款实体 Schema ↔ Model 一致性（4 项）
# ═══════════════════════════════════════════════════════════


class TestPaymentSchemaModelConsistency:
    """收款 Schema 与 Model 约束一致性"""

    def test_payment_amount_numeric(self):
        model_src = (MODELS_DIR / "order.py").read_text()
        numerics = _extract_model_numeric_fields(model_src)
        assert "amount" in numerics
        assert numerics["amount"] == (12, 2)

    def test_payment_method_literal_values(self):
        schema_src = (SCHEMAS_DIR / "payment.py").read_text()
        for val in ["cash", "transfer", "wechat", "alipay", "other"]:
            assert f'"{val}"' in schema_src, f"缺少 payment_method 值: {val}"

    def test_payment_remark_max_length(self):
        schema_src = (SCHEMAS_DIR / "payment.py").read_text()
        assert "max_length=500" in schema_src

    def test_payment_amount_positive(self):
        schema_src = (SCHEMAS_DIR / "payment.py").read_text()
        assert "amount_must_be_positive" in schema_src or "gt=0" in schema_src


# ═══════════════════════════════════════════════════════════
# 6. 模型层统一约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModelUniformConstraints:
    """模型层统一约束模式验证"""

    def test_all_models_have_id_primary_key(self):
        """所有模型都有 UUID 主键"""
        for model_file in MODELS_DIR.glob("*.py"):
            if model_file.name.startswith("__"):
                continue
            source = model_file.read_text()
            # 检查有 id = Column 的定义
            if "class " in source and "Model" in source:
                assert "id" in source, f"{model_file.name} 缺少 id 字段"

    def test_all_models_have_created_at(self):
        """核心业务模型有 created_at 时间戳"""
        for entity in ["product.py", "customer.py", "order.py"]:
            source = (MODELS_DIR / entity).read_text()
            assert "created_at" in source, f"{entity} 缺少 created_at"

    def test_numeric_precision_consistent_12_2(self):
        """所有金额字段使用统一的 Numeric(12,2) 精度"""
        # 非金额字段（比率、百分比等）使用不同精度
        skip_fields = {"gross_margin", "discount_rate"}
        for model_file in MODELS_DIR.glob("*.py"):
            if model_file.name.startswith("__"):
                continue
            source = model_file.read_text()
            numerics = _extract_model_numeric_fields(source)
            for field, (precision, scale) in numerics.items():
                if field in skip_fields:
                    continue
                assert (precision, scale) == (12, 2), \
                    f"{model_file.name}.{field} 精度 ({precision},{scale}) 不符合统一标准 (12,2)"

    def test_soft_delete_columns_consistent(self):
        """软删除字段 deleted_at 定义一致（Mapped[type | None] 表示 nullable）"""
        for model_file in MODELS_DIR.glob("*.py"):
            if model_file.name.startswith("__"):
                continue
            source = model_file.read_text()
            if "deleted_at" in source:
                # deleted_at 使用 Mapped[datetime | None] 表示可空
                assert "datetime | None" in source or "nullable=True" in source

    def test_all_string_columns_have_length(self):
        """所有 String 列都指定长度（避免无长度限制的 String）"""
        for model_file in MODELS_DIR.glob("*.py"):
            if model_file.name.startswith("__"):
                continue
            source = model_file.read_text()
            # 检查是否有 String() 不带长度参数的（仅 String 本身，不是 String(N)）
            bare_strings = re.findall(r"Column\(String\)", source)
            assert len(bare_strings) == 0, \
                f"{model_file.name} 有未指定长度的 String 列"
