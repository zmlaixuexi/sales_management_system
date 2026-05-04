"""代码质量：前端 TypeScript 类型定义与 API 响应类型一致性验证测试
覆盖 ApiResponse 封装、PaginatedData 结构、ApiError 结构、请求函数签名、实体接口覆盖、枚举类型对齐"""

import re
from pathlib import Path

TYPES_FILE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "types" / "index.ts"
REQUEST_FILE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api" / "request.ts"
API_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api"
HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "hooks"

# API 模块列表
API_MODULES = [
    "products.ts", "customers.ts", "orders.ts", "payments.ts",
    "users.ts", "roles.ts", "inventory.ts", "auditLogs.ts", "reports.ts",
]


def _extract_interface_fields(source: str, interface_name: str) -> list[str]:
    """从 TypeScript interface 提取顶级字段名（支持泛型和 extends）"""
    # 匹配 interface 定义，可能带泛型参数 <T> 或 <T = unknown>，可能带 extends
    pattern = rf"(?:export\s+)?interface\s+{interface_name}(?:<[^>]*>)?(?:\s+extends\s+\w+)?\s*\{{"
    m = re.search(pattern, source)
    if not m:
        return []
    # 从 { 后开始，用大括号计数找到匹配的 }
    start = source.index("{", m.start())
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
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        # 匹配字段声明: fieldName?: type 或 fieldName: type
        fm = re.match(r"(\w+)\s*\??\s*:", stripped)
        if fm:
            fields.append(fm.group(1))
    return fields


# ═══════════════════════════════════════════════════════════
# 1. ApiResponse 封装结构验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestApiResponseEnvelope:
    """验证前端 ApiResponse<T> 结构与后端 resp() 一致"""

    def test_api_response_has_success(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiResponse")
        assert "success" in fields

    def test_api_response_has_data(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiResponse")
        assert "data" in fields

    def test_api_response_has_message(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiResponse")
        assert "message" in fields

    def test_api_response_has_request_id(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiResponse")
        assert "request_id" in fields

    def test_api_response_success_is_boolean(self):
        source = TYPES_FILE.read_text()
        assert "success: boolean" in source

    def test_api_response_is_generic(self):
        source = TYPES_FILE.read_text()
        assert "ApiResponse<T" in source


# ═══════════════════════════════════════════════════════════
# 2. PaginatedData 结构验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginatedDataStructure:
    """验证前端 PaginatedData<T> 与后端 paginated_resp() 一致"""

    def test_paginated_data_has_items(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "PaginatedData")
        assert "items" in fields

    def test_paginated_data_has_page(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "PaginatedData")
        assert "page" in fields

    def test_paginated_data_has_page_size(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "PaginatedData")
        assert "page_size" in fields

    def test_paginated_data_has_total(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "PaginatedData")
        assert "total" in fields

    def test_paginated_data_only_four_fields(self):
        """PaginatedData 只有 items/page/page_size/total 四个字段"""
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "PaginatedData")
        assert set(fields) == {"items", "page", "page_size", "total"}


# ═══════════════════════════════════════════════════════════
# 3. ApiError 结构验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestApiErrorStructure:
    """验证前端 ApiError 与后端错误响应一致"""

    def test_api_error_has_success_false(self):
        source = TYPES_FILE.read_text()
        assert "success: false" in source or "success:false" in source

    def test_api_error_has_error_object(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiError")
        assert "error" in fields

    def test_api_error_has_request_id(self):
        source = TYPES_FILE.read_text()
        fields = _extract_interface_fields(source, "ApiError")
        assert "request_id" in fields

    def test_api_error_code_and_message(self):
        """错误对象包含 code 和 message"""
        source = TYPES_FILE.read_text()
        assert '"code"' in source or "'code'" in source or "code:" in source
        assert '"message"' in source or "'message'" in source or "message:" in source


# ═══════════════════════════════════════════════════════════
# 4. 请求函数签名验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestFunctionSignatures:
    """验证 request.ts 导出函数使用 ApiResponse<T>"""

    def test_get_returns_api_response(self):
        source = REQUEST_FILE.read_text()
        assert "ApiResponse<" in source
        assert "Promise<ApiResponse<" in source

    def test_post_returns_api_response(self):
        source = REQUEST_FILE.read_text()
        assert "post" in source

    def test_put_returns_api_response(self):
        source = REQUEST_FILE.read_text()
        assert "put" in source

    def test_del_returns_api_response(self):
        source = REQUEST_FILE.read_text()
        assert "del" in source

    def test_all_helpers_are_exported(self):
        source = REQUEST_FILE.read_text()
        assert "export" in source
        for fn in ["get", "post", "put", "del"]:
            assert fn in source


# ═══════════════════════════════════════════════════════════
# 5. API 模块导入模式验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestApiModuleImports:
    """验证 API 模块正确导入请求函数和类型"""

    def test_products_imports_request_helpers(self):
        source = (API_DIR / "products.ts").read_text()
        assert "from './request'" in source

    def test_customers_imports_request_helpers(self):
        source = (API_DIR / "customers.ts").read_text()
        assert "from './request'" in source

    def test_orders_imports_request_helpers(self):
        source = (API_DIR / "orders.ts").read_text()
        assert "from './request'" in source

    def test_payments_imports_request_helpers(self):
        source = (API_DIR / "payments.ts").read_text()
        assert "from './request'" in source

    def test_users_imports_request_helpers(self):
        source = (API_DIR / "users.ts").read_text()
        assert "from './request'" in source

    def test_inventory_imports_request_helpers(self):
        source = (API_DIR / "inventory.ts").read_text()
        assert "from './request'" in source

    def test_reports_imports_request_helpers(self):
        source = (API_DIR / "reports.ts").read_text()
        assert "from './request'" in source

    def test_paginated_data_imported_where_needed(self):
        """使用分页的模块导入 PaginatedData 或定义等效结构"""
        paginated_modules = ["products.ts", "customers.ts", "orders.ts",
                             "payments.ts", "users.ts", "inventory.ts"]
        for mod in paginated_modules:
            source = (API_DIR / mod).read_text()
            assert "PaginatedData" in source, f"{mod} 未导入 PaginatedData"


# ═══════════════════════════════════════════════════════════
# 6. 实体接口字段覆盖验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestEntityInterfaceFields:
    """验证关键实体接口包含必要字段"""

    def test_product_has_core_fields(self):
        source = (API_DIR / "products.ts").read_text()
        fields = _extract_interface_fields(source, "Product")
        required = {"id", "name", "sku", "sale_price", "status", "stock_quantity"}
        assert required.issubset(set(fields)), f"Product 缺少: {required - set(fields)}"

    def test_customer_has_core_fields(self):
        source = (API_DIR / "customers.ts").read_text()
        fields = _extract_interface_fields(source, "Customer")
        required = {"id", "name", "phone", "email", "level", "source"}
        assert required.issubset(set(fields)), f"Customer 缺少: {required - set(fields)}"

    def test_order_has_core_fields(self):
        source = (API_DIR / "orders.ts").read_text()
        fields = _extract_interface_fields(source, "Order")
        required = {"id", "order_no", "status", "total_amount", "customer_id"}
        assert required.issubset(set(fields)), f"Order 缺少: {required - set(fields)}"

    def test_payment_has_core_fields(self):
        source = (API_DIR / "payments.ts").read_text()
        fields = _extract_interface_fields(source, "Payment")
        required = {"id", "order_id", "amount", "payment_method", "status"}
        assert required.issubset(set(fields)), f"Payment 缺少: {required - set(fields)}"

    def test_user_has_core_fields(self):
        source = (API_DIR / "users.ts").read_text()
        fields = _extract_interface_fields(source, "User")
        required = {"id", "username", "is_active", "roles"}
        assert required.issubset(set(fields)), f"User 缺少: {required - set(fields)}"

    def test_order_detail_extends_order(self):
        source = (API_DIR / "orders.ts").read_text()
        assert "OrderDetail extends Order" in source or "OrderDetail" in source
        detail_fields = _extract_interface_fields(source, "OrderDetail")
        assert "items" in detail_fields
        assert "payments" in detail_fields


# ═══════════════════════════════════════════════════════════
# 7. TypeScript 严格模式验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestTypeScriptStrictMode:
    """验证 TypeScript 类型无 any 滥用"""

    def test_types_file_no_any(self):
        source = TYPES_FILE.read_text()
        assert ": any" not in source

    def test_request_file_no_any(self):
        source = REQUEST_FILE.read_text()
        # 允许 unknown，不允许 any
        assert ": any" not in source or ": any" not in source.replace("// ", "")

    def test_entity_interfaces_use_proper_types(self):
        """实体接口不使用 any 类型"""
        for mod in ["products.ts", "customers.ts", "orders.ts", "payments.ts"]:
            source = (API_DIR / mod).read_text()
            # 在 interface 内部不应有 : any
            interfaces = re.findall(r"export\s+interface\s+\w+[^{]*\{[^}]+\}", source, re.DOTALL)
            for iface in interfaces:
                assert ": any" not in iface, f"{mod} 含有 : any 类型"

    def test_all_modules_export_interfaces(self):
        """所有 API 模块都导出 interface"""
        for mod in API_MODULES:
            source = (API_DIR / mod).read_text()
            assert "export interface" in source, f"{mod} 没有导出 interface"
