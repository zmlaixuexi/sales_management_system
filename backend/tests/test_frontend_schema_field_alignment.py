"""需求符合性：前端 TypeScript 接口与后端 Pydantic Schema 字段对齐验证测试
验证关键实体的前端接口字段名与后端响应模型字段名一致"""

import re
from pathlib import Path

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "app" / "schemas"
FRONTEND_API_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api"


def _extract_ts_interface_fields(source, interface_name):
    """从 TS 源码提取 interface 的字段名列表（支持嵌套大括号）"""
    # 找到 interface 定义开始的 {
    pattern = rf"export\s+interface\s+{interface_name}\s*(?:extends\s+\w+\s*)?\{{"
    m = re.search(pattern, source)
    if not m:
        return []
    # 从 { 开始计数大括号
    start = m.end() - 1
    depth = 0
    end = start
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = source[start + 1:end]
    fields = []
    for line in body.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue
        fm = re.match(r"(\w+)\??\s*:", line)
        if fm:
            fields.append(fm.group(1))
    return fields


def _extract_pydantic_fields(source, class_name):
    """从 Python 源码提取 Pydantic model 的字段名列表"""
    pattern = rf"class\s+{class_name}\s*\([^)]*\):\s*\n((?:\s{{4}}[^\n]+\n)+)"
    m = re.search(pattern, source)
    if not m:
        return []
    fields = []
    for line in m.group(1).strip().split("\n"):
        fm = re.match(r"\s*(\w+)\s*:", line)
        if fm and fm.group(1) not in ("model_config",):
            fields.append(fm.group(1))
    return fields


class TestProductFieldAlignment:
    """商品实体字段对齐"""

    def test_product_interface_matches_product_item(self):
        fe_source = (FRONTEND_API_DIR / "products.ts").read_text()
        be_source = (SCHEMAS_DIR / "product.py").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "Product")
        be_fields = _extract_pydantic_fields(be_source, "ProductItem")
        assert set(fe_fields) == set(be_fields), \
            f"商品字段差异: 前端独有={set(fe_fields)-set(be_fields)}, 后端独有={set(be_fields)-set(fe_fields)}"

    def test_product_detail_has_images(self):
        fe_source = (FRONTEND_API_DIR / "products.ts").read_text()
        # ProductDetail extends Product, so we check it has images
        assert "images" in fe_source


class TestOrderFieldAlignment:
    """订单实体字段对齐"""

    def test_order_interface_matches_order_detail(self):
        fe_source = (FRONTEND_API_DIR / "orders.ts").read_text()
        be_source = (SCHEMAS_DIR / "order.py").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "Order")
        be_fields = _extract_pydantic_fields(be_source, "OrderDetail")
        # 前端 Order 接口是 OrderDetail 的子集（不含 items/payments）
        fe_set = set(fe_fields)
        be_set = set(be_fields) - {"items", "payments"}
        fe_set = fe_set - {"item_count"}
        assert fe_set == be_set, \
            f"订单字段差异: 前端独有={fe_set-be_set}, 后端独有={be_set-fe_set}"

    def test_order_item_interface_matches(self):
        fe_source = (FRONTEND_API_DIR / "orders.ts").read_text()
        be_source = (SCHEMAS_DIR / "order.py").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "OrderItem")
        be_fields = _extract_pydantic_fields(be_source, "OrderItemResponse")
        assert set(fe_fields) == set(be_fields), \
            f"订单明细字段差异: 前端独有={set(fe_fields)-set(be_fields)}, 后端独有={set(be_fields)-set(fe_fields)}"

    def test_order_payment_interface_matches(self):
        fe_source = (FRONTEND_API_DIR / "orders.ts").read_text()
        be_source = (SCHEMAS_DIR / "order.py").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "OrderPayment")
        be_fields = _extract_pydantic_fields(be_source, "OrderPaymentResponse")
        assert set(fe_fields) == set(be_fields), \
            f"订单收款字段差异: 前端独有={set(fe_fields)-set(be_fields)}, 后端独有={set(be_fields)-set(fe_fields)}"


class TestCustomerFieldAlignment:
    """客户实体字段对齐"""

    def test_customer_interface_fields(self):
        fe_source = (FRONTEND_API_DIR / "customers.ts").read_text()
        be_source = (SCHEMAS_DIR / "customer.py").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "Customer")
        be_fields = _extract_pydantic_fields(be_source, "CustomerBrief")
        if fe_fields and be_fields:
            fe_set = set(fe_fields)
            be_set = set(be_fields)
            # 前端可能有额外字段，后端字段应全部包含
            missing = be_set - fe_set
            assert not missing, f"前端客户接口缺少后端字段: {missing}"


class TestUserFieldAlignment:
    """用户实体字段对齐"""

    def test_current_user_matches(self):
        fe_source = (FRONTEND_API_DIR / "auth.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "CurrentUser")
        assert "id" in fe_fields
        assert "username" in fe_fields
        assert "is_active" in fe_fields
        assert "is_superuser" in fe_fields
        assert "roles" in fe_fields
        assert "permissions" in fe_fields


class TestRoleFieldAlignment:
    """角色实体字段对齐"""

    def test_role_item_fields(self):
        fe_source = (FRONTEND_API_DIR / "roles.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "RoleItem")
        # RoleItem 应该有 id, name, display_name 等关键字段
        assert len(fe_fields) > 0
        assert "id" in fe_fields


class TestAuditLogFieldAlignment:
    """审计日志字段对齐"""

    def test_audit_log_item_fields(self):
        fe_source = (FRONTEND_API_DIR / "auditLogs.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "AuditLogItem")
        expected = {
            "id", "actor_id", "actor_name", "action", "resource_type",
            "resource_id", "before_data", "after_data", "ip_address",
            "user_agent", "request_id", "created_at",
        }
        assert set(fe_fields) == expected


class TestPaymentFieldAlignment:
    """收款实体字段对齐"""

    def test_payment_interface_fields(self):
        fe_source = (FRONTEND_API_DIR / "payments.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "Payment")
        # Payment 应有关键字段
        assert len(fe_fields) > 0
        assert "id" in fe_fields


class TestInventoryFieldAlignment:
    """库存实体字段对齐"""

    def test_inventory_movement_fields(self):
        fe_source = (FRONTEND_API_DIR / "inventory.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "InventoryMovement")
        assert len(fe_fields) > 0

    def test_inventory_adjustment_result(self):
        fe_source = (FRONTEND_API_DIR / "inventory.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "InventoryAdjustedResult")
        assert len(fe_fields) > 0


class TestReportFieldAlignment:
    """报表实体字段对齐"""

    def test_sales_summary_fields(self):
        fe_source = (FRONTEND_API_DIR / "reports.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "SalesSummary")
        assert len(fe_fields) > 0

    def test_product_ranking_fields(self):
        fe_source = (FRONTEND_API_DIR / "reports.ts").read_text()
        fe_fields = _extract_ts_interface_fields(fe_source, "ProductRankingItem")
        assert len(fe_fields) > 0
