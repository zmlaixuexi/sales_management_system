"""异常路径：后端外键关联删除级联行为验证测试
覆盖软删除防护、模型级联配置、
删除前关联检查、关联表级联清理、审计日志记录"""

import re
from pathlib import Path

PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "products.py"
CUSTOMERS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "customers.py"
ORDERS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "orders.py"
USERS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "users.py"
ROLES_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "roles.py"
PRODUCT_MODEL = Path(__file__).resolve().parent.parent / "app" / "models" / "product.py"
ORDER_MODEL = Path(__file__).resolve().parent.parent / "app" / "models" / "order.py"
USER_MODEL = Path(__file__).resolve().parent.parent / "app" / "models" / "user.py"


def _read(path: Path) -> str:
    return path.read_text()


def _find_function_body(source: str, func_name: str) -> str:
    pattern = re.compile(rf"def {func_name}\b")
    match = pattern.search(source)
    if not match:
        return ""
    start = match.start()
    lines = source[start:].split("\n")
    body_lines = [lines[0]]
    indent = len(lines[0]) - len(lines[0].lstrip())
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped and (len(line) - len(stripped)) <= indent:
            if stripped.startswith(("def ", "class ", "@")):
                break
        body_lines.append(line)
    return "\n".join(body_lines)


# ═══════════════════════════════════════════════════════════
# 1. 软删除防护验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSoftDeleteProtection:
    """验证删除操作有关联防护"""

    def test_product_delete_checks_order_references(self):
        source = _read(PRODUCTS_FILE)
        body = _find_function_body(source, "delete_product")
        assert "SalesOrderItem" in body
        assert "PRODUCT_IN_USE" in body

    def test_customer_delete_checks_order_references(self):
        source = _read(CUSTOMERS_FILE)
        body = _find_function_body(source, "delete_customer")
        assert "SalesOrder" in body
        assert "CUSTOMER_HAS_ORDERS" in body

    def test_product_delete_uses_soft_delete(self):
        source = _read(PRODUCTS_FILE)
        body = _find_function_body(source, "delete_product")
        assert "deleted_at" in body
        assert "datetime.now()" in body

    def test_customer_delete_uses_soft_delete(self):
        source = _read(CUSTOMERS_FILE)
        body = _find_function_body(source, "delete_customer")
        assert "deleted_at" in body
        assert "datetime.now()" in body

    def test_product_delete_checks_deleted_orders_only(self):
        source = _read(PRODUCTS_FILE)
        body = _find_function_body(source, "delete_product")
        assert "deleted_at.is_(None)" in body


# ═══════════════════════════════════════════════════════════
# 2. 模型级联配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModelCascadeConfig:
    """验证模型层级联删除配置"""

    def test_order_items_cascade_on_order_delete(self):
        source = _read(ORDER_MODEL)
        assert 'cascade="all, delete-orphan"' in source
        assert "back_populates" in source

    def test_product_images_fk_ondelete_cascade(self):
        source = _read(PRODUCT_MODEL)
        assert 'ondelete="CASCADE"' in source
        assert "products.id" in source

    def test_order_items_fk_ondelete_cascade(self):
        source = _read(ORDER_MODEL)
        assert 'ondelete="CASCADE"' in source
        assert "sales_orders.id" in source

    def test_user_roles_fk_ondelete_cascade(self):
        source = _read(USER_MODEL)
        assert 'ondelete="CASCADE"' in source
        assert "users.id" in source
        assert "roles.id" in source

    def test_audit_log_actor_fk_set_null(self):
        source = _read(Path(__file__).resolve().parent.parent / "app" / "models" / "audit.py")
        assert 'ondelete="SET NULL"' in source


# ═══════════════════════════════════════════════════════════
# 3. 删除前关联检查验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDeletePreCheck:
    """验证删除前关联检查逻辑"""

    def test_product_delete_returns_409_on_order_ref(self):
        source = _read(PRODUCTS_FILE)
        body = _find_function_body(source, "delete_product")
        assert "409" in body

    def test_customer_delete_returns_400_on_order_ref(self):
        source = _read(CUSTOMERS_FILE)
        body = _find_function_body(source, "delete_customer")
        assert "400" in body
        assert "无法删除" in body

    def test_role_delete_checks_user_association(self):
        source = _read(ROLES_FILE)
        body = _find_function_body(source, "delete_role")
        assert "users" in body.lower() or "用户" in body

    def test_product_delete_logs_audit_action(self):
        source = _read(PRODUCTS_FILE)
        body = _find_function_body(source, "delete_product")
        assert "log_user_action" in body
        assert "product_delete" in body

    def test_customer_delete_logs_audit_action(self):
        source = _read(CUSTOMERS_FILE)
        body = _find_function_body(source, "delete_customer")
        assert "log_user_action" in body
        assert "customer_delete" in body


# ═══════════════════════════════════════════════════════════
# 4. 关联表级联清理验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAssociationCleanup:
    """验证关联表在修改时的清理逻辑"""

    def test_user_update_clears_old_roles_before_new(self):
        source = _read(USERS_FILE)
        body = _find_function_body(source, "update_user")
        assert "UserRole" in body
        assert ".delete()" in body

    def test_role_update_clears_old_permissions_before_new(self):
        source = _read(ROLES_FILE)
        body = _find_function_body(source, "update_role")
        assert "RolePermission" in body
        assert ".delete()" in body

    def test_role_delete_clears_permissions_first(self):
        source = _read(ROLES_FILE)
        body = _find_function_body(source, "delete_role")
        assert "RolePermission" in body
        assert ".delete()" in body

    def test_order_update_deletes_old_items(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "update_order")
        assert "SalesOrderItem" in body
        assert ".delete()" in body

    def test_all_delete_endpoints_use_safe_commit(self):
        for file_path, func_name in [
            (PRODUCTS_FILE, "delete_product"),
            (CUSTOMERS_FILE, "delete_customer"),
        ]:
            source = _read(file_path)
            body = _find_function_body(source, func_name)
            assert "safe_commit" in body, f"{func_name} 应使用 safe_commit"


# ═══════════════════════════════════════════════════════════
# 5. deleted_at 过滤覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDeletedAtFilter:
    """验证已删除记录在查询时被过滤"""

    def test_product_list_excludes_deleted(self):
        source = _read(PRODUCTS_FILE)
        assert "deleted_at.is_(None)" in source

    def test_customer_list_excludes_deleted(self):
        source = _read(CUSTOMERS_FILE)
        assert "deleted_at" in source

    def test_payment_list_excludes_deleted_orders(self):
        source = _read(Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "payments.py")
        assert "deleted_at.is_(None)" in source

    def test_report_queries_exclude_deleted_orders(self):
        source = _read(Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "reports.py")
        assert "deleted_at.is_(None)" in source

    def test_product_model_has_deleted_at_column(self):
        source = _read(PRODUCT_MODEL)
        assert "deleted_at" in source
        assert "index=True" in source
