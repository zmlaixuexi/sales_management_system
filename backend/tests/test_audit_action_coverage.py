"""需求符合性：后端审计日志 action 覆盖率与命名规范验证测试
验证所有 API 端点的审计日志调用符合 action 命名规范、无遗漏"""

import ast
import re
from pathlib import Path

from app.services.audit_service import SENSITIVE_FIELDS

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"


def _parse_file(filename):
    return ast.parse((API_DIR / filename).read_text())


def _find_action_strings(tree):
    """从 AST 中提取所有 action="xxx" 字符串值"""
    actions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "action":
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                actions.append(node.value.value)
    return actions


class TestActionNamingConvention:
    """action 命名格式规范"""

    def test_product_actions_use_prefix(self):
        tree = _parse_file("products.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("product_"), f"商品 action '{a}' 不以 product_ 开头"

    def test_customer_actions_use_prefix(self):
        tree = _parse_file("customers.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("customer_"), f"客户 action '{a}' 不以 customer_ 开头"

    def test_order_actions_use_prefix(self):
        tree = _parse_file("orders.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("order_") or a.startswith("payment_"), \
                f"订单 action '{a}' 不以 order_ 或 payment_ 开头"

    def test_payment_actions_use_prefix(self):
        tree = _parse_file("payments.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("payment_"), f"收款 action '{a}' 不以 payment_ 开头"

    def test_user_actions_use_prefix(self):
        tree = _parse_file("users.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("user_"), f"用户 action '{a}' 不以 user_ 开头"

    def test_role_actions_use_prefix(self):
        tree = _parse_file("roles.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("role_"), f"角色 action '{a}' 不以 role_ 开头"

    def test_auth_actions_use_known_names(self):
        tree = _parse_file("auth.py")
        actions = _find_action_strings(tree)
        valid = {"login_success", "login_failed", "password_change"}
        for a in actions:
            assert a in valid, f"认证 action '{a}' 不在已知集合中"

    def test_inventory_actions_use_prefix(self):
        tree = _parse_file("inventory.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("inventory_"), f"库存 action '{a}' 不以 inventory_ 开头"

    def test_file_actions_use_prefix(self):
        tree = _parse_file("files.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("file_"), f"文件 action '{a}' 不以 file_ 开头"

    def test_export_actions_use_prefix(self):
        tree = _parse_file("exports.py")
        actions = _find_action_strings(tree)
        for a in actions:
            assert a.startswith("export_"), f"导出 action '{a}' 不以 export_ 开头"

    def test_actions_use_snake_case(self):
        """所有 action 使用 snake_case 格式"""
        for filename in API_DIR.glob("*.py"):
            tree = ast.parse(filename.read_text())
            for a in _find_action_strings(tree):
                assert re.match(r"^[a-z][a-z0-9_]*$", a), \
                    f"action '{a}' 在 {filename.name} 不符合 snake_case"

    def test_actions_no_double_underscore(self):
        """action 不包含连续下划线"""
        for filename in API_DIR.glob("*.py"):
            tree = ast.parse(filename.read_text())
            for a in _find_action_strings(tree):
                assert "__" not in a, f"action '{a}' 包含连续下划线"

    def test_actions_length_within_50(self):
        """action 长度不超过模型定义的 String(50)"""
        for filename in API_DIR.glob("*.py"):
            tree = ast.parse(filename.read_text())
            for a in _find_action_strings(tree):
                assert len(a) <= 50, f"action '{a}' 超过 50 字符限制"


class TestResourceTypeConsistency:
    """resource_type 与模块对应关系"""

    def test_product_resource_type(self):
        tree = _parse_file("products.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "product", \
                        f"商品 resource_type 不是 product: {node.value.value}"

    def test_customer_resource_type(self):
        tree = _parse_file("customers.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "customer", \
                        f"客户 resource_type 不是 customer: {node.value.value}"

    def test_order_resource_type(self):
        tree = _parse_file("orders.py")
        types = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    types.add(node.value.value)
        assert "order" in types, "订单模块缺少 resource_type=order"
        assert "payment" in types, "订单模块缺少 resource_type=payment"

    def test_payment_resource_type(self):
        tree = _parse_file("payments.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "payment", \
                        f"收款 resource_type 不是 payment: {node.value.value}"

    def test_user_resource_type(self):
        tree = _parse_file("users.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "user", \
                        f"用户 resource_type 不是 user: {node.value.value}"

    def test_role_resource_type(self):
        tree = _parse_file("roles.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "role", \
                        f"角色 resource_type 不是 role: {node.value.value}"

    def test_auth_resource_type_is_user(self):
        tree = _parse_file("auth.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "user", \
                        f"认证 resource_type 不是 user: {node.value.value}"

    def test_inventory_resource_type(self):
        tree = _parse_file("inventory.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "product", \
                        f"库存 resource_type 不是 product: {node.value.value}"

    def test_file_resource_type(self):
        tree = _parse_file("files.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "file", \
                        f"文件 resource_type 不是 file: {node.value.value}"

    def test_export_resource_types(self):
        tree = _parse_file("exports.py")
        types = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "resource_type":
                if isinstance(node.value, ast.Constant):
                    types.add(node.value.value)
        assert types == {"product", "customer", "order", "payment"}, \
            f"导出 resource_type 集合不匹配: {types}"


class TestAuditLogImport:
    """所有修改类 API 都导入了审计服务"""

    MUTATION_MODULES = [
        "products.py", "customers.py", "orders.py", "payments.py",
        "users.py", "roles.py", "auth.py", "inventory.py", "files.py", "exports.py",
    ]

    def test_all_mutation_modules_import_audit(self):
        for filename in self.MUTATION_MODULES:
            tree = _parse_file(filename)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "audit_service" in node.module:
                        for alias in node.names:
                            imports.add(alias.name)
            assert "log_user_action" in imports or "log_action" in imports, \
                f"{filename} 未导入 log_user_action 或 log_action"


class TestSensitiveFieldMasking:
    """敏感字段脱敏配置完整性"""

    def test_sensitive_fields_includes_password(self):
        assert "password" in SENSITIVE_FIELDS

    def test_sensitive_fields_includes_hashed_password(self):
        assert "hashed_password" in SENSITIVE_FIELDS

    def test_sensitive_fields_includes_token(self):
        assert "token" in SENSITIVE_FIELDS

    def test_sensitive_fields_includes_secret(self):
        assert "secret" in SENSITIVE_FIELDS

    def test_sensitive_fields_includes_email(self):
        assert "email" in SENSITIVE_FIELDS

    def test_sensitive_fields_includes_phone(self):
        assert "phone" in SENSITIVE_FIELDS

    def test_masking_function_exists(self):
        from app.services.audit_service import _mask_sensitive
        result = _mask_sensitive({"password": "secret123", "name": "test"})
        assert result["password"] == "***"
        assert result["name"] == "test"

    def test_masking_handles_none(self):
        from app.services.audit_service import _mask_sensitive
        assert _mask_sensitive(None) is None

    def test_masking_handles_empty(self):
        from app.services.audit_service import _mask_sensitive
        assert _mask_sensitive({}) == {}

    def test_masking_handles_nested_key_match(self):
        from app.services.audit_service import _mask_sensitive
        result = _mask_sensitive({"user_token": "abc"})
        assert result["user_token"] == "***"


class TestAuditModelConstraints:
    """AuditLog 模型约束验证"""

    def test_action_column_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.action
        assert col.type.length == 50

    def test_resource_type_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.resource_type
        assert col.type.length == 50

    def test_actor_name_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.actor_name
        assert col.type.length == 100

    def test_resource_id_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.resource_id
        assert col.type.length == 64

    def test_ip_address_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.ip_address
        assert col.type.length == 45

    def test_user_agent_max_length(self):
        from app.models.audit import AuditLog
        col = AuditLog.__table__.c.user_agent
        assert col.type.length == 500

    def test_action_not_nullable(self):
        from app.models.audit import AuditLog
        assert not AuditLog.__table__.c.action.nullable

    def test_created_at_not_nullable(self):
        from app.models.audit import AuditLog
        assert not AuditLog.__table__.c.created_at.nullable

    def test_actor_id_nullable_with_set_null(self):
        """actor_id 允许为空（用户删除时 SET NULL）"""
        from app.models.audit import AuditLog
        fk = AuditLog.__table__.c.actor_id.foreign_keys
        assert len(fk) == 1
        fk_val = next(iter(fk))
        assert fk_val.ondelete == "SET NULL"

    def test_composite_index_exists(self):
        from app.models.audit import AuditLog
        index_names = [idx.name for idx in AuditLog.__table__.indexes]
        assert "ix_audit_logs_action_resource" in index_names


class TestCRUDActionsComplete:
    """关键模块的 CRUD 审计 action 完整性"""

    def test_product_has_create_update_delete(self):
        tree = _parse_file("products.py")
        actions = _find_action_strings(tree)
        assert "product_create" in actions
        assert "product_update" in actions
        assert "product_delete" in actions

    def test_customer_has_create_update_delete(self):
        tree = _parse_file("customers.py")
        actions = _find_action_strings(tree)
        assert "customer_create" in actions
        assert "customer_update" in actions
        assert "customer_delete" in actions

    def test_order_has_create_update(self):
        tree = _parse_file("orders.py")
        actions = _find_action_strings(tree)
        assert "order_create" in actions
        assert "order_update" in actions

    def test_order_has_confirm_cancel(self):
        tree = _parse_file("orders.py")
        actions = _find_action_strings(tree)
        assert "order_confirm" in actions
        assert "order_cancel" in actions

    def test_payment_has_create_and_reverse(self):
        actions = set()
        for filename in ("payments.py", "orders.py"):
            tree = _parse_file(filename)
            actions.update(_find_action_strings(tree))
        assert "payment_create" in actions
        assert "payment_reverse" in actions

    def test_user_has_create_update(self):
        tree = _parse_file("users.py")
        actions = _find_action_strings(tree)
        assert "user_create" in actions
        assert "user_update" in actions

    def test_role_has_create_update_delete(self):
        tree = _parse_file("roles.py")
        actions = _find_action_strings(tree)
        assert "role_create" in actions
        assert "role_update" in actions
        assert "role_delete" in actions

    def test_auth_has_login_success_and_failure(self):
        tree = _parse_file("auth.py")
        actions = _find_action_strings(tree)
        assert "login_success" in actions
        assert "login_failed" in actions

    def test_auth_has_password_change(self):
        tree = _parse_file("auth.py")
        actions = _find_action_strings(tree)
        assert "password_change" in actions

    def test_product_has_disable(self):
        tree = _parse_file("products.py")
        actions = _find_action_strings(tree)
        assert "product_disable" in actions

    def test_customer_has_transfer(self):
        tree = _parse_file("customers.py")
        actions = _find_action_strings(tree)
        assert "customer_transfer" in actions

    def test_product_has_import(self):
        tree = _parse_file("products.py")
        actions = _find_action_strings(tree)
        assert "product_import" in actions

    def test_customer_has_import(self):
        tree = _parse_file("customers.py")
        actions = _find_action_strings(tree)
        assert "customer_import" in actions

    def test_inventory_has_adjust(self):
        tree = _parse_file("inventory.py")
        actions = _find_action_strings(tree)
        assert "inventory_adjust" in actions

    def test_file_has_upload_and_delete(self):
        tree = _parse_file("files.py")
        actions = _find_action_strings(tree)
        assert "file_upload" in actions
        assert "file_delete" in actions

    def test_export_has_all_four_types(self):
        tree = _parse_file("exports.py")
        actions = _find_action_strings(tree)
        assert "export_products" in actions
        assert "export_customers" in actions
        assert "export_orders" in actions
        assert "export_payments" in actions


class TestTotalActionCount:
    """审计 action 总数统计"""

    def test_at_least_26_distinct_actions(self):
        """系统应至少有 26 种不同的审计 action"""
        all_actions = set()
        for filename in API_DIR.glob("*.py"):
            tree = ast.parse(filename.read_text())
            all_actions.update(_find_action_strings(tree))
        assert len(all_actions) >= 26, f"审计 action 总数 {len(all_actions)} 少于 26"

    def test_no_duplicate_actions_across_modules(self):
        """不同模块间 action 不重复"""
        module_actions = {}
        for filename in sorted(API_DIR.glob("*.py")):
            tree = ast.parse(filename.read_text())
            actions = _find_action_strings(tree)
            if actions:
                module_actions[filename.name] = set(actions)

        seen = {}
        for module, actions in module_actions.items():
            for a in actions:
                if a in seen:
                    # payment_create 允许在 orders.py 和 payments.py 中出现
                    if a == "payment_create" and {module, seen[a]} == {"orders.py", "payments.py"}:
                        continue
                    assert False, f"action '{a}' 在 {module} 和 {seen[a]} 中重复定义"
                seen[a] = module
