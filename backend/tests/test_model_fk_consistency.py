"""代码质量：后端模型关系与外键约束一致性验证测试
覆盖外键引用完整性、back_populates 配对、级联删除、唯一约束、索引覆盖、关联表结构"""

import re
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "app" / "models"

MODEL_FILES = {
    "user.py": ["User", "Role", "Permission", "UserRole", "RolePermission"],
    "customer.py": ["Customer"],
    "product.py": ["ProductCategory", "Product", "File", "ProductImage", "ProductPriceHistory"],
    "order.py": ["SalesOrder", "SalesOrderItem", "InventoryMovement", "Payment"],
    "audit.py": ["AuditLog"],
}


def _read_model(name: str) -> str:
    for fname, classes in MODEL_FILES.items():
        if name in classes:
            return (MODELS_DIR / fname).read_text()
    return ""


def _extract_class_body(source: str, class_name: str) -> str:
    """提取类体（从 class 行到下一个同级 class 或文件结尾）"""
    idx = source.find(f"class {class_name}(")
    if idx == -1:
        return ""
    lines = source[idx:].split("\n")[1:]
    collected = []
    for line in lines:
        if line and not line[0].isspace() and line.strip() and not line.strip().startswith("#"):
            break
        collected.append(line)
    return "\n".join(collected)


def _extract_fks_from_body(body: str) -> list[tuple[str, str]]:
    """从类体提取 ForeignKey: [(column_name, ref)]"""
    results = []
    statements = _join_statements(body)
    for stmt in statements:
        m = re.match(r'(\w+)\s*:\s*Mapped.*?ForeignKey\([\'"](\w+\.\w+)[\'"]', stmt)
        if m:
            results.append((m.group(1), m.group(2)))
    return results


def _has_field_with_flag(body: str, field_name: str, flag: str) -> bool:
    """检查字段定义中包含某个标志（跨行）"""
    statements = _join_statements(body)
    for stmt in statements:
        if (stmt.startswith(f"{field_name}:") or stmt.startswith(f"{field_name} :")) and re.search(flag, stmt):
            return True
    return False


def _extract_relationships_from_body(body: str) -> list[dict]:
    """从类体提取 relationship() 声明"""
    results = []
    statements = _join_statements(body)
    for stmt in statements:
        m = re.search(r'(\w+)\s*:\s*Mapped.*?relationship\((.+)\)', stmt, re.DOTALL)
        if m:
            attr = m.group(1)
            args = m.group(2)
            info = {"attr": attr}
            bp = re.search(r'back_populates\s*=\s*"(\w+)"', args)
            if bp:
                info["back_populates"] = bp.group(1)
            if "secondary" in args:
                sec = re.search(r'secondary\s*=\s*"(\w+)"', args)
                if sec:
                    info["secondary"] = sec.group(1)
            if "cascade" in args:
                cas = re.search(r'cascade\s*=\s*"([^"]+)"', args)
                if cas:
                    info["cascade"] = cas.group(1)
            results.append(info)
    return results


def _join_statements(body: str) -> list[str]:
    """将多行的 mapped_column/relationship 调用合并为单条语句"""
    lines = body.split("\n")
    statements = []
    current = ""
    paren_depth = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current += " " + stripped
        paren_depth += stripped.count("(") - stripped.count(")")
        if paren_depth <= 0 and ": Mapped" in current:
            statements.append(current.strip())
            current = ""
            paren_depth = 0
    if current.strip():
        statements.append(current.strip())
    return statements


def _get_model_body(name: str) -> str:
    return _extract_class_body(_read_model(name), name)


def _get_model_rels(name: str) -> list[dict]:
    return _extract_relationships_from_body(_get_model_body(name))


# ═══════════════════════════════════════════════════════════
# 1. 外键引用完整性验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestForeignKeyIntegrity:
    """验证外键引用正确的表和列"""

    def test_customer_owner_references_users(self):
        body = _get_model_body("Customer")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("owner_user_id") == "users.id"

    def test_product_category_references_categories(self):
        body = _get_model_body("Product")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("category_id") == "product_categories.id"

    def test_order_customer_references_customers(self):
        body = _get_model_body("SalesOrder")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("customer_id") == "customers.id"

    def test_order_item_references_order_and_product(self):
        body = _get_model_body("SalesOrderItem")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("order_id") == "sales_orders.id"
        assert fks.get("product_id") == "products.id"

    def test_payment_references_order(self):
        body = _get_model_body("Payment")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("order_id") == "sales_orders.id"

    def test_audit_log_actor_references_users(self):
        body = _get_model_body("AuditLog")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("actor_id") == "users.id"


# ═══════════════════════════════════════════════════════════
# 2. back_populates 配对验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBackPopulates:
    """验证 relationship 的 back_populates 双向配对"""

    def test_product_images_bidirectional(self):
        product_rels = _get_model_rels("Product")
        pimage_rels = _get_model_rels("ProductImage")
        images_rel = next((r for r in product_rels if r["attr"] == "images"), None)
        assert images_rel and images_rel.get("back_populates") == "product"
        product_rel = next((r for r in pimage_rels if r["attr"] == "product"), None)
        assert product_rel and product_rel.get("back_populates") == "images"

    def test_order_items_bidirectional(self):
        order_rels = _get_model_rels("SalesOrder")
        item_rels = _get_model_rels("SalesOrderItem")
        items_rel = next((r for r in order_rels if r["attr"] == "items"), None)
        assert items_rel and items_rel.get("back_populates") == "order"
        order_rel = next((r for r in item_rels if r["attr"] == "order"), None)
        assert order_rel and order_rel.get("back_populates") == "items"

    def test_order_payments_bidirectional(self):
        order_rels = _get_model_rels("SalesOrder")
        payment_rels = _get_model_rels("Payment")
        payments_rel = next((r for r in order_rels if r["attr"] == "payments"), None)
        assert payments_rel and payments_rel.get("back_populates") == "order"
        order_rel = next((r for r in payment_rels if r["attr"] == "order"), None)
        assert order_rel and order_rel.get("back_populates") == "payments"

    def test_user_roles_many_to_many(self):
        user_rels = _get_model_rels("User")
        role_rels = _get_model_rels("Role")
        user_roles = next((r for r in user_rels if r["attr"] == "roles"), None)
        role_users = next((r for r in role_rels if r["attr"] == "users"), None)
        assert user_roles and user_roles.get("back_populates") == "users"
        assert role_users and role_users.get("back_populates") == "roles"
        assert user_roles.get("secondary") == "user_roles"

    def test_role_permissions_many_to_many(self):
        role_rels = _get_model_rels("Role")
        perm_rels = _get_model_rels("Permission")
        role_perms = next((r for r in role_rels if r["attr"] == "permissions"), None)
        perm_roles = next((r for r in perm_rels if r["attr"] == "roles"), None)
        assert role_perms and role_perms.get("back_populates") == "roles"
        assert perm_roles and perm_roles.get("back_populates") == "permissions"


# ═══════════════════════════════════════════════════════════
# 3. 级联删除验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCascadeDeletes:
    """验证级联删除配置"""

    def test_order_items_cascade_on_delete(self):
        rels = _get_model_rels("SalesOrder")
        items_rel = next((r for r in rels if r["attr"] == "items"), None)
        assert items_rel
        assert "delete-orphan" in items_rel.get("cascade", "")

    def test_order_item_fk_cascade(self):
        body = _get_model_body("SalesOrderItem")
        assert 'ondelete="CASCADE"' in body

    def test_product_image_fk_cascade(self):
        body = _get_model_body("ProductImage")
        assert 'ondelete="CASCADE"' in body

    def test_user_role_fk_cascade(self):
        body = _get_model_body("UserRole")
        assert body.count('ondelete="CASCADE"') >= 2

    def test_audit_log_actor_set_null(self):
        body = _get_model_body("AuditLog")
        assert 'ondelete="SET NULL"' in body


# ═══════════════════════════════════════════════════════════
# 4. 唯一约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestUniqueConstraints:
    """验证关键字段的唯一约束"""

    def test_user_username_unique(self):
        body = _get_model_body("User")
        assert _has_field_with_flag(body, "username", r"unique\s*=\s*True")

    def test_role_name_unique(self):
        body = _get_model_body("Role")
        assert _has_field_with_flag(body, "name", r"unique\s*=\s*True")

    def test_permission_code_unique(self):
        body = _get_model_body("Permission")
        assert _has_field_with_flag(body, "code", r"unique\s*=\s*True")

    def test_product_sku_unique(self):
        body = _get_model_body("Product")
        assert _has_field_with_flag(body, "sku", r"unique\s*=\s*True")

    def test_order_no_unique(self):
        body = _get_model_body("SalesOrder")
        assert _has_field_with_flag(body, "order_no", r"unique\s*=\s*True")


# ═══════════════════════════════════════════════════════════
# 5. 索引覆盖验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestIndexCoverage:
    """验证常用查询字段有索引"""

    def test_customer_query_fields_indexed(self):
        body = _get_model_body("Customer")
        assert _has_field_with_flag(body, "name", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "owner_user_id", r"index\s*=\s*True")

    def test_product_query_fields_indexed(self):
        body = _get_model_body("Product")
        assert _has_field_with_flag(body, "status", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "category_id", r"index\s*=\s*True")

    def test_order_query_fields_indexed(self):
        body = _get_model_body("SalesOrder")
        assert _has_field_with_flag(body, "customer_id", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "status", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "created_at", r"index\s*=\s*True")

    def test_payment_query_fields_indexed(self):
        body = _get_model_body("Payment")
        assert _has_field_with_flag(body, "order_id", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "status", r"index\s*=\s*True")

    def test_audit_log_query_fields_indexed(self):
        body = _get_model_body("AuditLog")
        assert _has_field_with_flag(body, "action", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "created_at", r"index\s*=\s*True")

    def test_inventory_movement_query_fields_indexed(self):
        body = _get_model_body("InventoryMovement")
        assert _has_field_with_flag(body, "product_id", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "created_at", r"index\s*=\s*True")


# ═══════════════════════════════════════════════════════════
# 6. 关联表结构验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestJunctionTables:
    """验证多对多关联表结构"""

    def test_user_role_has_user_and_role_fks(self):
        body = _get_model_body("UserRole")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("user_id") == "users.id"
        assert fks.get("role_id") == "roles.id"

    def test_role_permission_has_role_and_perm_fks(self):
        body = _get_model_body("RolePermission")
        fks = dict(_extract_fks_from_body(body))
        assert fks.get("role_id") == "roles.id"
        assert fks.get("permission_id") == "permissions.id"

    def test_user_role_fks_indexed(self):
        body = _get_model_body("UserRole")
        assert _has_field_with_flag(body, "user_id", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "role_id", r"index\s*=\s*True")

    def test_role_permission_fks_indexed(self):
        body = _get_model_body("RolePermission")
        assert _has_field_with_flag(body, "role_id", r"index\s*=\s*True")
        assert _has_field_with_flag(body, "permission_id", r"index\s*=\s*True")


# ═══════════════════════════════════════════════════════════
# 7. 模型注册验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModelRegistration:
    """验证所有模型在 __init__.py 中注册"""

    def test_all_models_in_init(self):
        source = (MODELS_DIR / "__init__.py").read_text()
        all_classes = [cls for classes in MODEL_FILES.values() for cls in classes]
        for cls in all_classes:
            assert cls in source, f"{cls} 未在 __init__.py 中注册"

    def test_user_model_importable(self):
        from app.models.user import User
        assert User is not None

    def test_product_model_importable(self):
        from app.models.product import Product
        assert Product is not None

    def test_order_model_importable(self):
        from app.models.order import SalesOrder
        assert SalesOrder is not None

    def test_audit_model_importable(self):
        from app.models.audit import AuditLog
        assert AuditLog is not None
