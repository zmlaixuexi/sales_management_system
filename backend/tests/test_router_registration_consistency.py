"""
代码质量：后端 API 路由模块注册与标签命名一致性验证测试
覆盖路由模块注册完整性、前缀与标签命名规范、
CRUD 端点覆盖、responses 声明一致性、路由装饰器规范
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_DIR = ROOT / "app" / "api" / "v1"
ROUTER_SRC = (API_DIR / "router.py").read_text()
MAIN_SRC = (ROOT / "app" / "main.py").read_text()

MODULE_NAMES = [
    "health", "auth", "users", "roles", "files", "products",
    "customers", "orders", "payments", "inventory", "reports",
    "audit_logs", "exports",
]

SOURCES = {}
for name in MODULE_NAMES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()


def _get_router_prefix(src: str) -> str:
    """提取 APIRouter 的 prefix"""
    m = re.search(r'prefix\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else ""


def _get_router_tags(src: str) -> list[str]:
    """提取 APIRouter 的 tags"""
    m = re.search(r'tags\s*=\s*\[([^\]]+)\]', src)
    if not m:
        return []
    return [t.strip().strip('"\'') for t in m.group(1).split(",")]


def _count_endpoints(src: str) -> int:
    """统计路由装饰器数量"""
    return len(re.findall(r'@router\.(get|post|put|delete|patch)\(', src))


def _has_method(src: str, method: str) -> bool:
    """检查是否有指定 HTTP 方法的端点"""
    return bool(re.search(rf'@router\.{method}\(', src))


# ═══════════════════════════════════════════════════════════
# 1. 路由模块注册完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRouterRegistrationCompleteness:
    """所有路由模块在 router.py 和 main.py 中正确注册"""

    def test_all_modules_imported_in_router(self):
        """所有模块在 router.py 中导入"""
        for name in MODULE_NAMES:
            assert f"from app.api.v1.{name} import" in ROUTER_SRC, (
                f"router.py 应导入 {name} 模块"
            )

    def test_all_modules_included_in_router(self):
        """所有模块通过 include_router 注册"""
        for name in MODULE_NAMES:
            # import 行的别名格式：xxx_router
            alias = name + "_router"
            assert f"include_router({alias})" in ROUTER_SRC, (
                f"router.py 应 include_router({alias})"
            )

    def test_api_router_mounted_in_main(self):
        """api_router 挂载到 main.py 的 /api/v1"""
        assert "include_router(api_router" in MAIN_SRC or "api_router" in MAIN_SRC, (
            "main.py 应挂载 api_router"
        )
        assert "/api/v1" in MAIN_SRC, "api_router 应挂载到 /api/v1 前缀"

    def test_all_module_files_exist(self):
        """所有路由模块文件存在"""
        for name in MODULE_NAMES:
            assert (API_DIR / f"{name}.py").exists(), f"路由模块 {name}.py 应存在"

    def test_router_count_matches_module_count(self):
        """include_router 调用数与模块数匹配"""
        count = len(re.findall(r'include_router\(', ROUTER_SRC))
        assert count == len(MODULE_NAMES), (
            f"include_router 调用数 {count} 应与模块数 {len(MODULE_NAMES)} 匹配"
        )


# ═══════════════════════════════════════════════════════════
# 2. 前缀与标签命名规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPrefixAndTagNaming:
    """前缀使用 kebab-case，标签使用中文"""

    def test_prefixes_use_kebab_case(self):
        """所有前缀使用小写 kebab-case"""
        for name, src in SOURCES.items():
            prefix = _get_router_prefix(src)
            if prefix:
                assert prefix == prefix.lower(), f"{name} 前缀应全小写: {prefix}"
                assert re.match(r'^/[a-z0-9-]+$', prefix), (
                    f"{name} 前缀应使用 kebab-case: {prefix}"
                )

    def test_tags_are_chinese(self):
        """所有标签使用中文"""
        for name, src in SOURCES.items():
            tags = _get_router_tags(src)
            for tag in tags:
                assert re.search(r'[一-鿿]', tag), (
                    f"{name} 标签应包含中文: {tag}"
                )

    def test_each_module_has_one_tag(self):
        """每个模块只有一个标签"""
        for name, src in SOURCES.items():
            tags = _get_router_tags(src)
            if tags:
                assert len(tags) == 1, f"{name} 应只有一个标签，实际 {tags}"

    def test_prefix_starts_with_slash(self):
        """所有前缀以 / 开头"""
        for name, src in SOURCES.items():
            prefix = _get_router_prefix(src)
            if prefix:
                assert prefix.startswith("/"), f"{name} 前缀应以 / 开头: {prefix}"

    def test_health_has_no_prefix(self):
        """健康检查无前缀（直接挂在 /api/v1 下）"""
        prefix = _get_router_prefix(SOURCES["health"])
        assert prefix == "", "health 模块不应有 prefix"


# ═══════════════════════════════════════════════════════════
# 3. CRUD 端点覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCRUDEndpointCoverage:
    """核心 CRUD 模块有完整的端点覆盖"""

    def test_products_has_list_create_detail_update_delete(self):
        """商品模块有完整 CRUD 端点"""
        src = SOURCES["products"]
        assert _has_method(src, "get"), "products 应有 GET 端点（列表）"
        assert _has_method(src, "post"), "products 应有 POST 端点（创建）"
        assert _has_method(src, "put"), "products 应有 PUT 端点（更新）"
        assert _has_method(src, "delete"), "products 应有 DELETE 端点（删除）"

    def test_customers_has_list_create_detail_update_delete(self):
        """客户模块有完整 CRUD 端点"""
        src = SOURCES["customers"]
        assert _has_method(src, "get"), "customers 应有 GET 端点"
        assert _has_method(src, "post"), "customers 应有 POST 端点"
        assert _has_method(src, "put"), "customers 应有 PUT 端点"
        assert _has_method(src, "delete"), "customers 应有 DELETE 端点"

    def test_orders_has_list_create_and_actions(self):
        """订单模块有列表、创建和动作端点"""
        src = SOURCES["orders"]
        assert _has_method(src, "get"), "orders 应有 GET 端点"
        assert _has_method(src, "post"), "orders 应有 POST 端点"
        assert _has_method(src, "put"), "orders 应有 PUT 端点"
        assert _count_endpoints(src) >= 6, f"orders 应至少 6 个端点，实际 {_count_endpoints(src)}"

    def test_auth_has_login_and_refresh(self):
        """认证模块有登录和刷新端点"""
        src = SOURCES["auth"]
        assert _has_method(src, "post"), "auth 应有 POST 端点（登录/刷新）"
        assert _has_method(src, "get"), "auth 应有 GET 端点（/me）"
        assert _count_endpoints(src) >= 3, f"auth 应至少 3 个端点"

    def test_core_modules_have_minimum_endpoints(self):
        """核心模块有最低端点数量"""
        min_endpoints = {
            "products": 5,
            "customers": 5,
            "orders": 5,
            "users": 3,
            "roles": 3,
            "payments": 2,
        }
        for name, minimum in min_endpoints.items():
            count = _count_endpoints(SOURCES[name])
            assert count >= minimum, (
                f"{name} 应至少 {minimum} 个端点，实际 {count}"
            )


# ═══════════════════════════════════════════════════════════
# 4. responses 声明一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestResponsesConsistency:
    """路由模块有统一的 responses 声明"""

    def test_core_modules_declare_401_response(self):
        """核心 CRUD 模块声明 401 响应"""
        core = ["products", "customers", "orders", "payments", "users", "roles"]
        for name in core:
            assert '"401"' in SOURCES[name] or "401" in SOURCES[name], (
                f"{name} 应声明 401 响应"
            )

    def test_modules_use_chinese_response_descriptions(self):
        """responses 描述使用中文"""
        for name, src in SOURCES.items():
            if "responses" in src:
                # 检查 description 字段是否含中文
                descs = re.findall(r'"description"\s*:\s*"([^"]*)"', src)
                for d in descs:
                    if d:
                        assert re.search(r'[一-鿿]', d), (
                            f"{name} response description 应含中文: {d}"
                        )

    def test_router_definitions_use_router_variable(self):
        """所有模块使用 `router` 变量名"""
        for name, src in SOURCES.items():
            assert "router = APIRouter" in src, f"{name} 应使用 router = APIRouter(...)"

    def test_business_modules_have_docstring(self):
        """业务核心路由模块有模块级文档字符串"""
        business_with_docs = ["products", "customers", "orders", "payments"]
        for name in business_with_docs:
            src = SOURCES[name]
            assert '"""' in src[:200] or "'''" in src[:200], (
                f"{name} 模块应有模块级文档字符串"
            )

    def test_no_hardcoded_api_v1_in_routes(self):
        """路由内部不硬编码 /api/v1 前缀"""
        for name, src in SOURCES.items():
            # 路由装饰器中不应包含 /api/v1
            routes_with_prefix = re.findall(r'@router\.\w+\(\s*["\'](/api/v1[^"\']*)', src)
            assert len(routes_with_prefix) == 0, (
                f"{name} 路由不应硬编码 /api/v1 前缀: {routes_with_prefix}"
            )


# ═══════════════════════════════════════════════════════════
# 5. 路由装饰器规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRouteDecoratorStyle:
    """路由装饰器使用统一风格"""

    def test_all_modules_import_api_router_from_fastapi(self):
        """所有模块从 fastapi 导入 APIRouter"""
        for name, src in SOURCES.items():
            assert "APIRouter" in src, f"{name} 应导入 APIRouter"

    def test_no_app_level_router_usage(self):
        """路由模块不直接使用 app 对象"""
        for name, src in SOURCES.items():
            # 不应有 from app.main import app
            assert "from app.main import app" not in src, (
                f"{name} 不应直接导入 app 对象"
            )
            assert "app = FastAPI" not in src, f"{name} 不应创建 FastAPI 实例"

    def test_path_params_use_curly_brace_format(self):
        """路径参数使用 {param} 格式（FastAPI 标准）"""
        for name, src in SOURCES.items():
            # 找路径中的参数
            for m in re.finditer(r'@router\.\w+\(\s*["\']([^"\']+)["\']', src):
                path = m.group(1)
                # 不应使用 :param 格式（Flask 风格）
                assert ":" not in path or path.startswith(":"), (
                    f"{name} 路径 {path} 不应使用 :param 格式"
                )

    def test_all_endpoints_have_path_params_format(self):
        """带路径参数的端点使用正确格式"""
        for name, src in SOURCES.items():
            for m in re.finditer(r'@router\.\w+\(\s*["\']([^"\']+\{[^}]+\})', src):
                path = m.group(1)
                # 路径参数应使用 {xxx_id} 或 {xxx} 格式
                params = re.findall(r'\{(\w+)\}', path)
                for param in params:
                    assert re.match(r'^[a-z_]+$', param), (
                        f"{name} 路径参数 {param} 应使用小写 snake_case"
                    )

    def test_no_duplicate_routes(self):
        """无重复路由定义（同方法+同路径）"""
        for name, src in SOURCES.items():
            routes = re.findall(r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)', src)
            seen = set()
            for method, path in routes:
                key = f"{method} {path}"
                assert key not in seen, f"{name} 有重复路由: {key}"
                seen.add(key)
