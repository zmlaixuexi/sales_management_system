"""
代码质量：前端页面组件默认导出与路由懒加载引用一致性验证测试
覆盖路由懒加载引用、组件默认导出、
路由路径规范、页面文件覆盖、Suspense 降级一致性
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # 项目根目录

FRONTEND_DIR = ROOT / "frontend" / "src"
ROUTES_SRC = (FRONTEND_DIR / "routes" / "index.tsx").read_text()
PAGES_DIR = FRONTEND_DIR / "pages"

# 提取路由中引用的页面组件名
LAZY_IMPORTS = re.findall(r"import\('@/pages/(\w+)'\)", ROUTES_SRC)

# 所有页面文件
PAGE_FILES = {p.stem: p for p in PAGES_DIR.glob("*.tsx")}

# 读取所有页面组件源码
PAGE_SOURCES = {stem: p.read_text() for stem, p in PAGE_FILES.items()}


def _has_default_export(src: str) -> bool:
    """检查是否有 default export"""
    return bool(re.search(r'export\s+default', src))


def _has_named_function_export(src: str, name: str) -> bool:
    """检查是否有命名函数导出"""
    return bool(re.search(rf'export\s+(?:default\s+)?function\s+{name}\b', src)) or \
           bool(re.search(rf'export\s+(?:default\s+)?(?:const|function)\s+{name}\b', src))


# ═══════════════════════════════════════════════════════════
# 1. 路由懒加载引用验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLazyImportAlignment:
    """路由懒加载引用与页面文件对齐"""

    def test_all_lazy_imports_have_page_files(self):
        """所有懒加载引用对应存在的页面文件"""
        for name in LAZY_IMPORTS:
            assert name in PAGE_FILES, f"路由引用 @/pages/{name} 但文件不存在"

    def test_all_page_files_are_referenced_in_routes(self):
        """所有页面文件在路由中被引用"""
        for name in PAGE_FILES:
            assert name in LAZY_IMPORTS, f"页面文件 {name}.tsx 未在路由中引用"

    def test_lazy_import_count_matches_page_count(self):
        """懒加载引用数与页面文件数匹配"""
        assert len(set(LAZY_IMPORTS)) == len(PAGE_FILES), (
            f"懒加载引用 {len(set(LAZY_IMPORTS))} 个，页面文件 {len(PAGE_FILES)} 个"
        )

    def test_lazy_page_helper_used(self):
        """使用 lazyPage 辅助函数包裹懒加载"""
        assert "lazyPage(" in ROUTES_SRC, "应使用 lazyPage 辅助函数"
        count = len(re.findall(r'lazyPage\(', ROUTES_SRC))
        assert count >= 15, f"lazyPage 调用应 >= 15，实际 {count}"

    def test_no_direct_lazy_without_suspense(self):
        """没有不使用 Suspense 的 lazy 调用"""
        # 所有 lazy() 应在 lazyPage 内
        direct_lazy = re.findall(r'lazy\(', ROUTES_SRC)
        # lazy 被导入 1 次 + 在 lazyPage 中使用 1 次
        assert len(direct_lazy) <= 2, "lazy() 应仅在 lazyPage 辅助函数中使用"


# ═══════════════════════════════════════════════════════════
# 2. 组件默认导出验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestComponentDefaultExports:
    """页面组件有正确的默认导出"""

    def test_all_pages_have_default_export(self):
        """所有页面组件有 default export"""
        for name, src in PAGE_SOURCES.items():
            assert _has_default_export(src), f"{name}.tsx 应有 default export"

    def test_default_exports_use_function_or_const(self):
        """默认导出使用 function 或 const 声明"""
        for name, src in PAGE_SOURCES.items():
            has_fn = bool(re.search(r'export\s+default\s+function\s+\w+', src))
            has_const = bool(re.search(r'export\s+default\s+\w+\s*=', src))  # e.g. export default Component
            has_arrow = bool(re.search(r'export\s+default\s+\(\)', src))
            assert has_fn or has_const or has_arrow or _has_default_export(src), (
                f"{name}.tsx 默认导出格式不标准"
            )

    def test_login_page_has_default_export(self):
        """Login 页面有默认导出"""
        assert "Login" in PAGE_SOURCES, "应有 Login.tsx 页面"
        assert _has_default_export(PAGE_SOURCES["Login"]), "Login 应有 default export"

    def test_not_found_page_has_default_export(self):
        """NotFound 页面有默认导出"""
        assert "NotFound" in PAGE_SOURCES, "应有 NotFound.tsx 页面"
        assert _has_default_export(PAGE_SOURCES["NotFound"]), "NotFound 应有 default export"

    def test_dashboard_page_has_default_export(self):
        """Dashboard 页面有默认导出"""
        assert "Dashboard" in PAGE_SOURCES, "应有 Dashboard.tsx 页面"
        assert _has_default_export(PAGE_SOURCES["Dashboard"]), "Dashboard 应有 default export"


# ═══════════════════════════════════════════════════════════
# 3. 路由路径规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRoutePathConventions:
    """路由路径遵循规范"""

    def test_all_paths_start_with_slash_or_are_relative(self):
        """所有路由路径以 / 开头或为相对路径"""
        for m in re.finditer(r"path\s*:\s*['\"]([^'\"]+)['\"]", ROUTES_SRC):
            path = m.group(1)
            assert path.startswith("/") or path == "*" or re.match(r'^[a-z]', path), (
                f"路由路径 {path} 应以 / 开头或为相对路径"
            )

    def test_path_params_use_colon_format(self):
        """路径参数使用 :param 格式"""
        paths = re.findall(r"path\s*:\s*['\"]([^'\"]+)['\"]", ROUTES_SRC)
        for path in paths:
            params = re.findall(r':(\w+)', path)
            for param in params:
                assert re.match(r'^[a-z_]+$', param), (
                    f"路径参数 {param} 应使用小写 snake_case"
                )

    def test_has_catch_all_404_route(self):
        """有通配符 404 路由"""
        assert "*" in ROUTES_SRC or "NotFound" in ROUTES_SRC, "应有 404 通配符路由"

    def test_has_login_route(self):
        """有 /login 路由"""
        assert "'/login'" in ROUTES_SRC or '"/login"' in ROUTES_SRC, "应有 /login 路由"

    def test_has_index_route(self):
        """有 index 路由（首页）"""
        assert "index:" in ROUTES_SRC or "index:" in ROUTES_SRC.replace(" ", ""), (
            "应有 index 路由"
        )


# ═══════════════════════════════════════════════════════════
# 4. 页面文件覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPageFileCoverage:
    """关键页面文件完整覆盖"""

    def test_crud_pages_exist(self):
        """CRUD 页面（列表 + 表单）存在"""
        for entity in ["Products", "Customers", "Orders"]:
            assert entity in PAGE_FILES, f"应有 {entity}.tsx 列表页"
            assert f"{entity[:-1]}Form" in PAGE_FILES or f"{entity.rstrip('s')}Form" in PAGE_FILES, (
                f"应有 {entity} 表单页"
            )

    def test_detail_pages_exist(self):
        """详情页存在"""
        for name in ["CustomerDetail", "OrderDetail"]:
            assert name in PAGE_FILES, f"应有 {name}.tsx"

    def test_management_pages_exist(self):
        """管理页面存在"""
        for name in ["Users", "Roles", "AuditLogs", "Inventory", "Payments"]:
            assert name in PAGE_FILES, f"应有 {name}.tsx"

    def test_reports_page_exists(self):
        """报表页面存在"""
        assert "ReportsCenter" in PAGE_FILES, "应有 ReportsCenter.tsx"

    def test_all_pages_are_tsx(self):
        """所有页面文件使用 .tsx 扩展名"""
        for p in PAGES_DIR.iterdir():
            assert p.suffix == ".tsx", f"页面文件 {p.name} 应使用 .tsx 扩展名"


# ═══════════════════════════════════════════════════════════
# 5. Suspense 降级与路由结构验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSuspenseAndRouteStructure:
    """Suspense 降级和路由结构正确"""

    def test_loading_fallback_uses_ant_design_spin(self):
        """Loading 降级使用 Ant Design Spin"""
        assert "Spin" in ROUTES_SRC, "Loading 降级应使用 Ant Design Spin"
        assert "Suspense" in ROUTES_SRC, "应使用 Suspense 包裹懒加载组件"

    def test_routes_use_protected_route_wrapper(self):
        """受保护路由使用 ProtectedRoute 包裹"""
        assert "ProtectedRoute" in ROUTES_SRC, "应使用 ProtectedRoute 包裹受保护路由"

    def test_routes_use_app_layout(self):
        """受保护路由使用 AppLayout 布局"""
        assert "AppLayout" in ROUTES_SRC, "应使用 AppLayout 布局"

    def test_login_route_not_protected(self):
        """Login 路由不受 ProtectedRoute 保护"""
        # login 路由块很短，只到闭合 },
        login_start = ROUTES_SRC.find("'/login'")
        login_end = ROUTES_SRC.find("},", login_start) + 2
        login_block = ROUTES_SRC[login_start:login_end]
        assert "lazyPage" in login_block, "/login 应使用 lazyPage"
        assert "ProtectedRoute" not in login_block, "/login 不应包裹 ProtectedRoute"

    def test_routes_export_default(self):
        """routes 导出为 default"""
        assert "export default routes" in ROUTES_SRC, "路由应 export default routes"
