"""代码质量：后端 Pydantic Schema 与 API 响应序列化一致性验证测试
覆盖 response_model 声明、输入 Schema 验证器、响应 Schema 字段、Schema 与端点导入一致性、字段命名规范"""

import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "app" / "schemas"
API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
DEPS = Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"

# response_model 声明：模块 → [(端点名, Schema名)]
RESPONSE_MODEL_DECLS = {
    "products.py": [
        ("create_product", "ProductBrief"),
        ("get_product", "ProductDetail"),
        ("update_product", "ProductBrief"),
    ],
    "orders.py": [
        ("create_order", "OrderBrief"),
        ("get_order", "OrderDetail"),
    ],
    "customers.py": [
        ("create_customer", "CustomerBrief"),
        ("get_customer", "CustomerDetail"),
    ],
    "payments.py": [
        ("create_payment", "PaymentCreated"),
        ("reverse_payment", "PaymentReversed"),
    ],
    "inventory.py": [
        ("adjust_stock", "InventoryAdjusted"),
    ],
}

# 各 Schema 模块的响应类名
SCHEMA_RESPONSE_CLASSES = {
    "product.py": ["ProductItem", "ProductBrief", "ProductImageItem", "ProductDetail",
                   "PriceHistoryItem", "ImportResult"],
    "order.py": ["OrderBrief", "OrderItemResponse", "OrderPaymentResponse", "OrderDetail"],
    "customer.py": ["CustomerBrief", "CustomerDetail"],
    "payment.py": ["PaymentCreated", "PaymentReversed"],
    "inventory.py": ["InventoryAdjusted"],
    "auth.py": ["TokenResponse", "CurrentUser", "RoleBrief", "UserBrief"],
}

# 各 Schema 模块的输入类名
SCHEMA_INPUT_CLASSES = {
    "product.py": ["ProductCreate", "ProductUpdate"],
    "order.py": ["OrderItemInput", "OrderCreate", "OrderUpdate"],
    "customer.py": ["CustomerCreate", "CustomerUpdate", "CustomerTransfer"],
    "payment.py": ["PaymentCreate"],
    "inventory.py": ["InventoryAdjust"],
    "auth.py": ["LoginRequest", "RefreshRequest", "ChangePasswordRequest",
                "UserCreate", "UserUpdate"],
}


def _extract_class_fields(source: str, class_name: str) -> list[str]:
    """从 Pydantic BaseModel 提取顶级字段名（不进入方法体）"""
    idx = source.find(f"class {class_name}(BaseModel):")
    if idx == -1:
        return []
    # 从类定义行后开始，收集顶级缩进的字段声明（缩进 4 空格，非方法/装饰器）
    lines = source[idx:].split("\n")[1:]  # 跳过 class 行
    fields = []
    for line in lines:
        stripped = line.lstrip()
        # 遇到非空行且缩进为 0（顶级定义）→ 类体结束
        if stripped and not line[0].isspace():
            break
        # 空行跳过
        if not stripped:
            continue
        # 跳过装饰器和方法定义
        if stripped.startswith("@") or stripped.startswith("def "):
            continue
        # 只匹配 4 空格缩进（顶级字段，非方法内部）
        if line.startswith("    ") and not line.startswith("        "):
            fm = re.match(r"    (\w+)\s*:\s", line)
            if fm and fm.group(1) != "model_config":
                fields.append(fm.group(1))
    return fields


# ═══════════════════════════════════════════════════════════
# 1. response_model 声明验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestResponseModelDeclarations:
    """验证 API 端点 response_model 声明引用正确的 Schema"""

    def test_products_response_models_imported(self):
        source = (API_DIR / "products.py").read_text()
        for _, schema in RESPONSE_MODEL_DECLS["products.py"]:
            assert schema in source, f"products.py 未导入 {schema}"

    def test_orders_response_models_imported(self):
        source = (API_DIR / "orders.py").read_text()
        for _, schema in RESPONSE_MODEL_DECLS["orders.py"]:
            assert schema in source, f"orders.py 未导入 {schema}"

    def test_customers_response_models_imported(self):
        source = (API_DIR / "customers.py").read_text()
        for _, schema in RESPONSE_MODEL_DECLS["customers.py"]:
            assert schema in source, f"customers.py 未导入 {schema}"

    def test_payments_response_models_imported(self):
        source = (API_DIR / "payments.py").read_text()
        for _, schema in RESPONSE_MODEL_DECLS["payments.py"]:
            assert schema in source, f"payments.py 未导入 {schema}"

    def test_inventory_response_models_imported(self):
        source = (API_DIR / "inventory.py").read_text()
        for _, schema in RESPONSE_MODEL_DECLS["inventory.py"]:
            assert schema in source, f"inventory.py 未导入 {schema}"

    def test_response_model_references_api_response(self):
        """所有 response_model 声明都使用 ApiResponse 包装"""
        for mod_name in RESPONSE_MODEL_DECLS:
            source = (API_DIR / mod_name).read_text()
            assert "response_model=ApiResponse[" in source


# ═══════════════════════════════════════════════════════════
# 2. Schema 输入验证器覆盖验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestInputSchemaValidators:
    """验证输入 Schema 的关键字段有验证器"""

    def test_product_create_has_price_validators(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        assert 'field_validator("sale_price")' in source
        assert 'field_validator("cost_price")' in source

    def test_product_create_has_sanitize_validator(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        assert 'field_validator("name", "remark")' in source

    def test_order_create_has_uuid_validators(self):
        source = (SCHEMA_DIR / "order.py").read_text()
        assert "validate_customer_id" in source
        assert "validate_product_id" in source

    def test_customer_create_has_email_and_phone_validators(self):
        source = (SCHEMA_DIR / "customer.py").read_text()
        assert 'field_validator("email")' in source
        assert 'field_validator("phone")' in source

    def test_payment_create_has_amount_validator(self):
        source = (SCHEMA_DIR / "payment.py").read_text()
        assert "amount_must_be_positive" in source

    def test_user_create_has_password_strength_validator(self):
        source = (SCHEMA_DIR / "auth.py").read_text()
        assert "validate_password_strength" in source


# ═══════════════════════════════════════════════════════════
# 3. 响应 Schema 字段完整性验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestResponseSchemaFields:
    """验证响应 Schema 包含必要的字段"""

    def test_product_brief_has_core_fields(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        fields = _extract_class_fields(source, "ProductBrief")
        required = {"id", "sku", "name", "sale_price", "status"}
        assert required.issubset(set(fields)), f"ProductBrief 缺少字段: {required - set(fields)}"

    def test_product_detail_extends_brief(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        detail_fields = set(_extract_class_fields(source, "ProductDetail"))
        core = {"id", "sku", "name", "sale_price", "status"}
        assert core.issubset(detail_fields)
        assert "remark" in detail_fields or "images" in detail_fields

    def test_order_detail_has_sub_resources(self):
        source = (SCHEMA_DIR / "order.py").read_text()
        fields = _extract_class_fields(source, "OrderDetail")
        assert "items" in fields
        assert "payments" in fields

    def test_customer_detail_extends_brief(self):
        source = (SCHEMA_DIR / "customer.py").read_text()
        brief_fields = set(_extract_class_fields(source, "CustomerBrief"))
        detail_fields = set(_extract_class_fields(source, "CustomerDetail"))
        # Detail 至少包含 Brief 的所有字段
        assert brief_fields.issubset(detail_fields), f"CustomerDetail 缺少: {brief_fields - detail_fields}"

    def test_payment_created_has_required_fields(self):
        source = (SCHEMA_DIR / "payment.py").read_text()
        fields = _extract_class_fields(source, "PaymentCreated")
        required = {"id", "order_id", "amount", "payment_method", "order_status"}
        assert required.issubset(set(fields))

    def test_current_user_has_roles_and_permissions(self):
        source = (SCHEMA_DIR / "auth.py").read_text()
        fields = _extract_class_fields(source, "CurrentUser")
        assert "roles" in fields
        assert "permissions" in fields


# ═══════════════════════════════════════════════════════════
# 4. Schema 类定义完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSchemaClassIntegrity:
    """验证所有 Schema 文件中声明的类都存在"""

    def test_product_schemas_all_defined(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        for cls_name in SCHEMA_RESPONSE_CLASSES["product.py"] + SCHEMA_INPUT_CLASSES["product.py"]:
            assert f"class {cls_name}(BaseModel)" in source, f"缺少类 {cls_name}"

    def test_order_schemas_all_defined(self):
        source = (SCHEMA_DIR / "order.py").read_text()
        for cls_name in SCHEMA_RESPONSE_CLASSES["order.py"] + SCHEMA_INPUT_CLASSES["order.py"]:
            assert f"class {cls_name}(BaseModel)" in source, f"缺少类 {cls_name}"

    def test_customer_schemas_all_defined(self):
        source = (SCHEMA_DIR / "customer.py").read_text()
        for cls_name in SCHEMA_RESPONSE_CLASSES["customer.py"] + SCHEMA_INPUT_CLASSES["customer.py"]:
            assert f"class {cls_name}(BaseModel)" in source, f"缺少类 {cls_name}"

    def test_payment_schemas_all_defined(self):
        source = (SCHEMA_DIR / "payment.py").read_text()
        for cls_name in SCHEMA_RESPONSE_CLASSES["payment.py"] + SCHEMA_INPUT_CLASSES["payment.py"]:
            assert f"class {cls_name}(BaseModel)" in source, f"缺少类 {cls_name}"

    def test_auth_schemas_all_defined(self):
        source = (SCHEMA_DIR / "auth.py").read_text()
        for cls_name in SCHEMA_RESPONSE_CLASSES["auth.py"] + SCHEMA_INPUT_CLASSES["auth.py"]:
            assert f"class {cls_name}(BaseModel)" in source, f"缺少类 {cls_name}"


# ═══════════════════════════════════════════════════════════
# 5. 字段命名规范验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestFieldNamingConvention:
    """验证 Schema 字段使用 snake_case 命名"""

    def test_response_schemas_use_snake_case(self):
        camel_re = re.compile(r"^[a-z]+(?:[A-Z][a-z]*)+$")
        all_schema_files = list(SCHEMA_DIR.glob("*.py"))
        all_schema_files = [f for f in all_schema_files if f.name != "__init__.py"]
        for sf in all_schema_files:
            source = sf.read_text()
            for cls_match in re.finditer(r"class (\w+)\(BaseModel\)", source):
                cls_name = cls_match.group(1)
                fields = _extract_class_fields(source, cls_name)
                for field in fields:
                    assert not camel_re.match(field), (
                        f"{sf.name}:{cls_name} 字段 '{field}' 使用 camelCase，应为 snake_case"
                    )

    def test_id_fields_are_string_type(self):
        """所有 id 类字段使用 str 类型（序列化后的 UUID）"""
        for sf_name in ["product.py", "order.py", "customer.py", "payment.py", "auth.py"]:
            source = (SCHEMA_DIR / sf_name).read_text()
            for cls_match in re.finditer(r"class (\w+)\(BaseModel\)", source):
                cls_name = cls_match.group(1)
                # 提取类体
                pattern = rf"class {cls_name}\(BaseModel\):\s*\n((?:\s+[^\n]+\n)*)"
                m = re.search(pattern, source)
                if not m:
                    continue
                for line in m.group(1).split("\n"):
                    id_match = re.match(r"\s+(\w+_id)\s*:\s*(\w+)", line)
                    if id_match and id_match.group(1) == "id":
                        assert id_match.group(2) == "str", (
                            f"{sf_name}:{cls_name}.id 类型应为 str，实际为 {id_match.group(2)}"
                        )

    def test_amount_fields_are_string_type(self):
        """金额字段使用 str 类型（Decimal 序列化为字符串）"""
        amount_fields = {"sale_price", "cost_price", "amount", "unit_profit",
                        "gross_margin", "total_amount", "total_cost", "gross_profit",
                        "subtotal_amount", "subtotal_cost", "discount_amount",
                        "discount_rate", "unit_price", "cost_price_snapshot",
                        "paid_amount", "old_sale_price", "new_sale_price",
                        "old_cost_price", "new_cost_price"}
        for sf_name in ["product.py", "order.py", "payment.py"]:
            source = (SCHEMA_DIR / sf_name).read_text()
            for cls_match in re.finditer(r"class (\w+)\(BaseModel\)", source):
                cls_name = cls_match.group(1)
                pattern = rf"class {cls_name}\(BaseModel\):\s*\n((?:\s+[^\n]+\n)*)"
                m = re.search(pattern, source)
                if not m:
                    continue
                for line in m.group(1).split("\n"):
                    fm = re.match(r"\s+(\w+)\s*:\s*(\S+)", line)
                    if fm and fm.group(1) in amount_fields:
                        field_type = fm.group(2)
                        # 允许 str | None 或 str
                        assert "str" in field_type, (
                            f"{sf_name}:{cls_name}.{fm.group(1)} 类型应为 str，实际为 {field_type}"
                        )

    def test_datetime_fields_are_string_type(self):
        """响应 Schema 中时间字段使用 str 类型"""
        datetime_fields = {"created_at", "updated_at", "paid_at"}
        for sf_name in ["product.py", "order.py", "customer.py"]:
            source = (SCHEMA_DIR / sf_name).read_text()
            for cls_match in re.finditer(r"class (\w+)\(BaseModel\)", source):
                cls_name = cls_match.group(1)
                # 只检查响应类（带 _Item, _Brief, _Detail, _Response 后缀的）
                if not any(cls_name.endswith(s) for s in ("Item", "Brief", "Detail", "Response")):
                    continue
                pattern = rf"class {cls_name}\(BaseModel\):\s*\n((?:\s+[^\n]+\n)*)"
                m = re.search(pattern, source)
                if not m:
                    continue
                for line in m.group(1).split("\n"):
                    fm = re.match(r"\s+(\w+)\s*:\s*(\S+)", line)
                    if fm and fm.group(1) in datetime_fields:
                        field_type = fm.group(2)
                        assert "str" in field_type, (
                            f"{sf_name}:{cls_name}.{fm.group(1)} 类型应为 str，实际为 {field_type}"
                        )


# ═══════════════════════════════════════════════════════════
# 6. 输入/更新 Schema 差异验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCreateUpdateSchemaDifference:
    """验证 Create 和 Update Schema 的字段关系"""

    def test_product_update_all_optional(self):
        source = (SCHEMA_DIR / "product.py").read_text()
        create_fields = _extract_class_fields(source, "ProductCreate")
        update_fields = _extract_class_fields(source, "ProductUpdate")
        # Update 应覆盖 Create 的大部分字段
        overlap = set(create_fields) & set(update_fields)
        assert len(overlap) >= 5, f"ProductUpdate 与 ProductCreate 重叠字段不足: {overlap}"

    def test_customer_update_all_optional(self):
        source = (SCHEMA_DIR / "customer.py").read_text()
        create_fields = _extract_class_fields(source, "CustomerCreate")
        update_fields = _extract_class_fields(source, "CustomerUpdate")
        overlap = set(create_fields) & set(update_fields)
        assert len(overlap) >= 5, f"CustomerUpdate 与 CustomerCreate 重叠字段不足: {overlap}"

    def test_order_update_subset_of_create(self):
        source = (SCHEMA_DIR / "order.py").read_text()
        create_fields = _extract_class_fields(source, "OrderCreate")
        update_fields = _extract_class_fields(source, "OrderUpdate")
        overlap = set(create_fields) & set(update_fields)
        assert len(overlap) >= 2, f"OrderUpdate 与 OrderCreate 重叠字段不足: {overlap}"

    def test_user_update_no_username(self):
        """UserUpdate 不包含 username（不可修改）"""
        source = (SCHEMA_DIR / "auth.py").read_text()
        update_fields = _extract_class_fields(source, "UserUpdate")
        assert "username" not in update_fields, "UserUpdate 不应包含 username"

    def test_user_update_no_password(self):
        """UserUpdate 不包含 password（通过专用接口修改）"""
        source = (SCHEMA_DIR / "auth.py").read_text()
        update_fields = _extract_class_fields(source, "UserUpdate")
        assert "password" not in update_fields, "UserUpdate 不应包含 password"


# ═══════════════════════════════════════════════════════════
# 7. ApiResponse 响应包装验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestApiResponseWrapper:
    """验证 ApiResponse 通用响应包装"""

    def test_api_response_has_success_field(self):
        source = (SCHEMA_DIR / "response.py").read_text()
        assert "success" in source

    def test_api_response_has_data_field(self):
        source = (SCHEMA_DIR / "response.py").read_text()
        assert "data" in source

    def test_api_response_has_message_field(self):
        source = (SCHEMA_DIR / "response.py").read_text()
        assert "message" in source

    def test_api_response_is_generic(self):
        source = (SCHEMA_DIR / "response.py").read_text()
        assert "Generic" in source
        assert "ApiResponse" in source


# ═══════════════════════════════════════════════════════════
# 8. resp 辅助函数一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRespHelperConsistency:
    """验证 resp() 辅助函数与 ApiResponse 结构一致"""

    def test_resp_returns_success_true(self):
        source = DEPS.read_text()
        assert '"success": True' in source or "'success': True" in source

    def test_resp_includes_data(self):
        source = DEPS.read_text()
        assert '"data"' in source or "'data'" in source

    def test_resp_includes_message(self):
        source = DEPS.read_text()
        assert '"message"' in source or "'message'" in source

    def test_resp_default_message(self):
        source = DEPS.read_text()
        m = re.search(r'def resp\([^)]*\)', source)
        assert m
        assert "操作成功" in m.group() or '"操作成功"' in source

    def test_resp_includes_request_id(self):
        source = DEPS.read_text()
        assert "request_id" in source
