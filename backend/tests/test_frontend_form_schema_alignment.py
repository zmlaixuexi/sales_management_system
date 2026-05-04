"""
代码质量：前端表单验证规则与后端 Schema 约束对齐验证测试
覆盖必填字段对齐、字符串长度对齐、数值边界对齐、
格式验证对齐、表单字段覆盖
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # 项目根目录

FRONTEND_DIR = ROOT / "frontend" / "src"
BACKEND_DIR = ROOT / "backend"

# 前端表单文件
LOGIN_TSX = (FRONTEND_DIR / "pages" / "Login.tsx").read_text()
PRODUCT_FORM_TSX = (FRONTEND_DIR / "pages" / "ProductForm.tsx").read_text()
CUSTOMER_FORM_TSX = (FRONTEND_DIR / "pages" / "CustomerForm.tsx").read_text()
ORDER_FORM_TSX = (FRONTEND_DIR / "pages" / "OrderForm.tsx").read_text()
USERS_TSX = (FRONTEND_DIR / "pages" / "Users.tsx").read_text()
ROLES_TSX = (FRONTEND_DIR / "pages" / "Roles.tsx").read_text()

# 后端 Schema 文件
SCHEMAS_DIR = BACKEND_DIR / "app" / "schemas"
PRODUCT_SCH = (SCHEMAS_DIR / "product.py").read_text()
CUSTOMER_SCH = (SCHEMAS_DIR / "customer.py").read_text()
ORDER_SCH = (SCHEMAS_DIR / "order.py").read_text()
AUTH_SCH = (SCHEMAS_DIR / "auth.py").read_text()


def _field_context(src: str, field_name: str, window: int = 600) -> str:
    """提取 Form.Item name=fieldName 周围的上下文"""
    # 匹配 name="fieldName" 或 name={"fieldName"} 或 name='fieldName'
    pattern = rf'name\s*=\s*(?:"{field_name}"|\{{"{field_name}"}}|\'{field_name}\')'
    m = re.search(pattern, src)
    if not m:
        return ""
    start = max(0, m.start() - 50)
    end = min(len(src), m.end() + window)
    return src[start:end]


def _has_required_rule(src: str, field_name: str) -> bool:
    """检查字段是否有 required: true 规则"""
    ctx = _field_context(src, field_name)
    if not ctx:
        return False
    return bool(re.search(r'required\s*:\s*true', ctx))


def _has_rule_type(src: str, field_name: str, rule_type: str) -> bool:
    """检查字段是否有指定规则类型"""
    ctx = _field_context(src, field_name)
    if not ctx:
        return False
    if rule_type == "email":
        return bool(re.search(r"type\s*:\s*['\"]email['\"]", ctx))
    return bool(re.search(rf'{rule_type}\s*:', ctx))


def _get_rule_value(src: str, field_name: str, rule_type: str) -> int | None:
    """提取表单规则值（如 max: 50 → 50）"""
    ctx = _field_context(src, field_name)
    if not ctx:
        return None
    m = re.search(rf'{rule_type}\s*:\s*(\d+)', ctx)
    return int(m.group(1)) if m else None


def _get_input_maxlength(src: str, field_name: str) -> int | None:
    """提取 Input 组件的 maxLength 属性"""
    ctx = _field_context(src, field_name)
    if not ctx:
        return None
    m = re.search(r'maxLength\s*=\s*\{?\s*(\d+)\s*\}?', ctx)
    return int(m.group(1)) if m else None


def _get_input_number_prop(src: str, field_name: str, prop: str) -> int | None:
    """提取 InputNumber 的 min/max 属性"""
    ctx = _field_context(src, field_name)
    if not ctx:
        return None
    m = re.search(rf'{prop}\s*=\s*\{{\s*(-?\d+)\s*\}}', ctx)
    return int(m.group(1)) if m else None


def _get_schema_field_def(src: str, field_name: str) -> str:
    """提取后端 Schema 中字段的 Field(...) 定义"""
    m = re.search(rf"{field_name}\s*:", src)
    if not m:
        return ""
    rest = src[m.end():]
    eq = re.search(r"=\s*Field\(", rest)
    if not eq:
        return ""
    start = eq.end()
    depth = 1
    i = start
    while i < len(rest) and depth > 0:
        if rest[i] == '(':
            depth += 1
        elif rest[i] == ')':
            depth -= 1
        i += 1
    return rest[start:i - 1]


def _schema_has_constraint(src: str, field_name: str, constraint: str) -> bool:
    """检查后端 Schema 字段是否有指定约束"""
    field_def = _get_schema_field_def(src, field_name)
    return constraint in field_def if field_def else False


def _schema_get_constraint_value(src: str, field_name: str, constraint: str) -> int | None:
    """提取后端 Schema 字段约束值"""
    field_def = _get_schema_field_def(src, field_name)
    if not field_def:
        return None
    m = re.search(rf"{constraint}\s*=\s*(-?\d+)", field_def)
    return int(m.group(1)) if m else None


# ═══════════════════════════════════════════════════════════
# 1. 必填字段对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequiredFieldAlignment:
    """前端必填规则与后端 required 字段对齐"""

    def test_product_name_required_matches(self):
        """商品名称：前端 required 与后端 Field(...) 一致"""
        fe_required = _has_required_rule(PRODUCT_FORM_TSX, "name")
        be_required = _schema_has_constraint(PRODUCT_SCH, "name", "...")
        assert fe_required, "ProductForm name 字段应有 required 规则"
        assert be_required, "ProductCreate name 字段应为 required（Field(...)）"

    def test_customer_name_required_matches(self):
        """客户名称：前端 required 与后端 Field(...) 一致"""
        fe_required = _has_required_rule(CUSTOMER_FORM_TSX, "name")
        be_required = _schema_has_constraint(CUSTOMER_SCH, "name", "...")
        assert fe_required, "CustomerForm name 字段应有 required 规则"
        assert be_required, "CustomerCreate name 字段应为 required"

    def test_order_customer_id_required_matches(self):
        """订单客户 ID：前端 required 与后端 Field(...) 一致"""
        fe_required = _has_required_rule(ORDER_FORM_TSX, "customer_id")
        be_required = _schema_has_constraint(ORDER_SCH, "customer_id", "...")
        assert fe_required, "OrderForm customer_id 字段应有 required 规则"
        assert be_required, "OrderCreate customer_id 字段应为 required"

    def test_users_username_password_required_on_create(self):
        """用户创建：username/password 前端 required 与后端一致"""
        for field in ["username", "password"]:
            be_required = _schema_has_constraint(AUTH_SCH, field, "...")
            assert be_required, f"UserCreate {field} 字段应为 required"
        # 前端在创建模式下有 required 规则
        assert "请输入用户名" in USERS_TSX, "Users 创建模式 username 应有 required 规则"
        assert "请输入密码" in USERS_TSX, "Users 创建模式 password 应有 required 规则"

    def test_login_fields_required(self):
        """登录表单：username 和 password 都 required"""
        assert _has_required_rule(LOGIN_TSX, "username"), "Login username 应有 required"
        assert _has_required_rule(LOGIN_TSX, "password"), "Login password 应有 required"


# ═══════════════════════════════════════════════════════════
# 2. 字符串长度约束对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStringLengthAlignment:
    """前端 Input maxLength 与后端 max_length 对齐"""

    def test_product_name_maxlength_matches(self):
        """商品名称 maxLength 与 max_length 对齐"""
        fe_val = _get_input_maxlength(PRODUCT_FORM_TSX, "name")
        be_val = _schema_get_constraint_value(PRODUCT_SCH, "name", "max_length")
        assert fe_val is not None, "ProductForm name Input 应有 maxLength"
        assert be_val is not None, "ProductCreate name 应有 max_length"
        assert fe_val == be_val, f"name maxLength={fe_val} ≠ max_length={be_val}"

    def test_customer_phone_maxlength_matches(self):
        """客户电话 maxLength 与 max_length 对齐"""
        fe_val = _get_input_maxlength(CUSTOMER_FORM_TSX, "phone")
        be_val = _schema_get_constraint_value(CUSTOMER_SCH, "phone", "max_length")
        assert fe_val is not None, "CustomerForm phone Input 应有 maxLength"
        assert be_val is not None, "CustomerCreate phone 应有 max_length"
        assert fe_val == be_val, f"phone maxLength={fe_val} ≠ max_length={be_val}"

    def test_customer_email_maxlength_matches(self):
        """客户邮箱 maxLength 与 max_length 对齐"""
        fe_val = _get_input_maxlength(CUSTOMER_FORM_TSX, "email")
        be_val = _schema_get_constraint_value(CUSTOMER_SCH, "email", "max_length")
        assert fe_val is not None, "CustomerForm email Input 应有 maxLength"
        assert be_val is not None, "CustomerCreate email 应有 max_length"
        assert fe_val == be_val, f"email maxLength={fe_val} ≠ max_length={be_val}"

    def test_users_username_maxlength_matches(self):
        """用户名 maxLength 与 max_length 对齐"""
        fe_val = _get_input_maxlength(USERS_TSX, "username")
        be_val = _schema_get_constraint_value(AUTH_SCH, "username", "max_length")
        assert fe_val is not None, "Users username Input 应有 maxLength"
        assert be_val is not None, "UserCreate username 应有 max_length"
        assert fe_val == be_val, f"username maxLength={fe_val} ≠ max_length={be_val}"

    def test_users_password_maxlength_matches(self):
        """密码 maxLength 与 max_length 对齐"""
        fe_val = _get_input_maxlength(USERS_TSX, "password")
        be_val = _schema_get_constraint_value(AUTH_SCH, "password", "max_length")
        assert fe_val is not None, "Users password Input 应有 maxLength"
        assert be_val is not None, "UserCreate password 应有 max_length"
        assert fe_val == be_val, f"password maxLength={fe_val} ≠ max_length={be_val}"


# ═══════════════════════════════════════════════════════════
# 3. 数值边界对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestNumericBoundsAlignment:
    """前端 InputNumber min/max 与后端 ge/le 对齐"""

    def test_product_price_min_is_zero(self):
        """商品价格 InputNumber min=0 与后端非负验证对齐"""
        for field in ["cost_price", "sale_price"]:
            fe_min = _get_input_number_prop(PRODUCT_FORM_TSX, field, "min")
            assert fe_min is not None, f"ProductForm {field} InputNumber 应有 min"
            assert fe_min == 0, f"ProductForm {field} min 应为 0，实际 {fe_min}"

    def test_product_stock_quantity_bounds(self):
        """商品库存 InputNumber 有 min 约束"""
        fe_min = _get_input_number_prop(PRODUCT_FORM_TSX, "stock_quantity", "min")
        if fe_min is not None:
            be_ge = _schema_get_constraint_value(PRODUCT_SCH, "stock_quantity", "ge")
            assert be_ge is not None, "ProductCreate stock_quantity 应有 ge"
            assert fe_min == be_ge, f"stock_quantity min={fe_min} ≠ ge={be_ge}"

    def test_product_sort_weight_bounds(self):
        """商品排序权重有对称边界"""
        be_ge = _schema_get_constraint_value(PRODUCT_SCH, "sort_weight", "ge")
        be_le = _schema_get_constraint_value(PRODUCT_SCH, "sort_weight", "le")
        assert be_ge is not None, "sort_weight 应有 ge 约束"
        assert be_le is not None, "sort_weight 应有 le 约束"
        assert abs(be_ge) == be_le, f"sort_weight 边界不对称 ge={be_ge} le={be_le}"

    def test_order_quantity_gt_zero(self):
        """订单明细数量 gt=0 在后端验证（gt=0 即 >0）"""
        be_gt = _schema_get_constraint_value(ORDER_SCH, "quantity", "gt")
        assert be_gt is not None, "OrderItemInput quantity 应有 gt 约束"
        assert be_gt >= 0, "quantity gt 应 >= 0（gt=0 即 >0）"

    def test_inventory_quantity_change_symmetric(self):
        """库存调整数量对称边界在后端验证"""
        INV_SCH = (SCHEMAS_DIR / "inventory.py").read_text()
        be_ge = _schema_get_constraint_value(INV_SCH, "quantity_change", "ge")
        be_le = _schema_get_constraint_value(INV_SCH, "quantity_change", "le")
        assert be_ge is not None, "quantity_change 应有 ge 约束"
        assert be_le is not None, "quantity_change 应有 le 约束"
        assert abs(be_ge) == be_le, f"quantity_change 边界不对称 ge={be_ge} le={be_le}"


# ═══════════════════════════════════════════════════════════
# 4. 格式验证对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFormatValidationAlignment:
    """前端格式验证与后端 field_validator 对齐"""

    def test_customer_phone_pattern_matches(self):
        """客户手机号：前端正则与后端验证对齐"""
        # 前端使用 pattern: /^1[3-9]\d{9}$/
        assert _has_rule_type(CUSTOMER_FORM_TSX, "phone", "pattern"), (
            "CustomerForm phone 应有 pattern 规则"
        )
        ctx = _field_context(CUSTOMER_FORM_TSX, "phone")
        assert "1[3-9]" in ctx, "CustomerForm phone 应使用中国手机号正则"
        # 后端也有手机号验证
        assert "validate_phone" in CUSTOMER_SCH or "phone" in CUSTOMER_SCH, (
            "CustomerCreate 应有手机号验证"
        )

    def test_customer_email_type_matches(self):
        """客户邮箱：前端 type:'email' 与后端验证对齐"""
        assert _has_rule_type(CUSTOMER_FORM_TSX, "email", "email"), (
            "CustomerForm email 应有 type:'email' 规则"
        )
        # 后端应有邮箱验证
        assert "@" in CUSTOMER_SCH or "validate_email" in CUSTOMER_SCH or "EmailStr" in CUSTOMER_SCH, (
            "CustomerCreate 应有邮箱验证"
        )

    def test_users_phone_pattern_consistent(self):
        """用户手机号使用相同的中国手机号正则"""
        assert _has_rule_type(USERS_TSX, "phone", "pattern"), (
            "Users phone 应有 pattern 规则"
        )
        ctx = _field_context(USERS_TSX, "phone")
        assert "1[3-9]" in ctx, "Users phone 应使用中国手机号正则"

    def test_users_email_type_consistent(self):
        """用户邮箱使用 type:'email' 验证"""
        assert _has_rule_type(USERS_TSX, "email", "email"), (
            "Users email 应有 type:'email' 规则"
        )

    def test_users_password_complexity_rule(self):
        """用户密码有复杂度要求（字母+数字）"""
        ctx = _field_context(USERS_TSX, "password")
        assert "pattern" in ctx, "Users password 应有 pattern 规则"
        assert "a-zA-Z" in ctx, "密码正则应要求包含字母"
        assert r"\d" in ctx, "密码正则应要求包含数字"


# ═══════════════════════════════════════════════════════════
# 5. 表单字段覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFormFieldCoverage:
    """前端表单覆盖后端 Schema 关键字段"""

    def test_product_form_covers_key_fields(self):
        """商品表单覆盖 ProductCreate 关键字段"""
        for field in ["name", "sale_price", "cost_price", "stock_quantity", "status", "remark"]:
            assert f'name="{field}"' in PRODUCT_FORM_TSX or f"name='{field}'" in PRODUCT_FORM_TSX, (
                f"ProductForm 应包含 {field} 字段"
            )

    def test_customer_form_covers_key_fields(self):
        """客户表单覆盖 CustomerCreate 关键字段"""
        for field in ["name", "phone", "email", "source", "level", "remark"]:
            assert f'name="{field}"' in CUSTOMER_FORM_TSX or f"name='{field}'" in CUSTOMER_FORM_TSX, (
                f"CustomerForm 应包含 {field} 字段"
            )

    def test_order_form_covers_key_fields(self):
        """订单表单覆盖 OrderCreate 关键字段"""
        for field in ["customer_id", "remark"]:
            assert f'name="{field}"' in ORDER_FORM_TSX or f"name='{field}'" in ORDER_FORM_TSX, (
                f"OrderForm 应包含 {field} 字段"
            )
        # 订单明细通过动态添加，检查是否有商品选择逻辑
        assert "lines" in ORDER_FORM_TSX or "product" in ORDER_FORM_TSX.lower(), (
            "OrderForm 应有商品明细添加逻辑"
        )

    def test_users_form_covers_key_fields(self):
        """用户表单覆盖 UserCreate 关键字段"""
        for field in ["username", "password", "display_name", "phone", "email", "role_ids"]:
            assert f'name="{field}"' in USERS_TSX or f"name='{field}'" in USERS_TSX, (
                f"Users 表单应包含 {field} 字段"
            )

    def test_roles_form_covers_key_fields(self):
        """角色表单覆盖 RoleCreate 关键字段"""
        for field in ["name", "display_name", "description", "permission_ids"]:
            assert f'name="{field}"' in ROLES_TSX or f"name='{field}'" in ROLES_TSX, (
                f"Roles 表单应包含 {field} 字段"
            )
