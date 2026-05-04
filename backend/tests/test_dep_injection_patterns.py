"""代码质量：后端依赖注入模式一致性验证测试
覆盖 deps 公共 API、分页参数、鉴权依赖、CRUD 辅助函数、响应构建器使用一致性"""

import re
from pathlib import Path

DEPS_SOURCE = Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"
API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
ROUTER_SOURCE = API_DIR / "router.py"


def _all_api_sources():
    """返回所有 API 模块源码"""
    return {f.stem: f.read_text() for f in API_DIR.glob("*.py") if f.name != "__init__.py" and f.name != "router.py"}


def _module_uses_dep(module_name: str, dep_pattern: str, sources: dict | None = None) -> bool:
    if sources is None:
        sources = _all_api_sources()
    return dep_pattern in sources.get(module_name, "")


# ═══════════════════════════════════════════════════════════
# 1. deps 公共 API 结构验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestDepsPublicAPI:
    """验证 deps.py 导出所有必要的公共函数和类"""

    def test_has_pagination_params(self):
        source = DEPS_SOURCE.read_text()
        assert "class PaginationParams" in source

    def test_has_get_db(self):
        source = DEPS_SOURCE.read_text()
        assert "def get_db(" in source

    def test_has_get_current_user(self):
        source = DEPS_SOURCE.read_text()
        assert "def get_current_user(" in source

    def test_has_require_permission(self):
        source = DEPS_SOURCE.read_text()
        assert "def require_permission(" in source

    def test_has_get_or_404(self):
        source = DEPS_SOURCE.read_text()
        assert "def get_or_404(" in source

    def test_has_safe_commit(self):
        source = DEPS_SOURCE.read_text()
        assert "def safe_commit(" in source

    def test_has_resp(self):
        source = DEPS_SOURCE.read_text()
        assert "def resp(" in source

    def test_has_paginated_resp(self):
        source = DEPS_SOURCE.read_text()
        assert "def paginated_resp(" in source


# ═══════════════════════════════════════════════════════════
# 2. 分页参数默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaginationParams:
    """验证分页参数默认值和约束"""

    def test_default_page_is_1(self):
        source = DEPS_SOURCE.read_text()
        assert "page: int = Query(1" in source

    def test_default_page_size_is_20(self):
        source = DEPS_SOURCE.read_text()
        assert "page_size: int = Query(20" in source

    def test_page_ge_1(self):
        source = DEPS_SOURCE.read_text()
        assert "ge=1" in source

    def test_page_size_ge_1(self):
        source = DEPS_SOURCE.read_text()
        # page_size also has ge=1
        matches = re.findall(r"page_size.*?ge=(\d+)", source)
        assert any(m == "1" for m in matches)

    def test_page_size_le_100(self):
        source = DEPS_SOURCE.read_text()
        assert "le=100" in source


# ═══════════════════════════════════════════════════════════
# 3. 鉴权依赖配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuthDependency:
    """验证鉴权依赖配置"""

    def test_oauth2_token_url(self):
        source = DEPS_SOURCE.read_text()
        assert 'tokenUrl="/api/v1/auth/login"' in source

    def test_get_current_user_returns_user(self):
        source = DEPS_SOURCE.read_text()
        assert "-> User" in source

    def test_get_current_user_checks_token_type(self):
        source = DEPS_SOURCE.read_text()
        assert 'token_type != "access"' in source

    def test_get_current_user_checks_password_changed(self):
        source = DEPS_SOURCE.read_text()
        assert "password_changed_at" in source

    def test_require_permission_superuser_bypass(self):
        source = DEPS_SOURCE.read_text()
        assert "is_superuser" in source
        assert "permission_code not in perms" in source


# ═══════════════════════════════════════════════════════════
# 4. get_db 使用完整性（6 项）
# ═══════════════════════════════════════════════════════════


class TestGetDbUsage:
    """验证所有需要数据库的模块都使用 get_db"""

    def test_all_crud_modules_use_get_db(self):
        """所有 CRUD 模块都注入 get_db"""
        sources = _all_api_sources()
        crud_modules = ["products", "customers", "orders", "payments", "users", "roles"]
        for mod in crud_modules:
            assert _module_uses_dep(mod, "Depends(get_db)", sources), \
                f"{mod} 未使用 Depends(get_db)"

    def test_inventory_uses_get_db(self):
        sources = _all_api_sources()
        assert _module_uses_dep("inventory", "Depends(get_db)", sources)

    def test_reports_uses_get_db(self):
        sources = _all_api_sources()
        assert _module_uses_dep("reports", "Depends(get_db)", sources)

    def test_files_uses_get_db(self):
        sources = _all_api_sources()
        assert _module_uses_dep("files", "Depends(get_db)", sources)

    def test_exports_uses_get_db(self):
        sources = _all_api_sources()
        assert _module_uses_dep("exports", "Depends(get_db)", sources)

    def test_audit_logs_uses_get_db(self):
        sources = _all_api_sources()
        assert _module_uses_dep("audit_logs", "Depends(get_db)", sources)


# ═══════════════════════════════════════════════════════════
# 5. 鉴权覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuthCoverage:
    """验证鉴权依赖覆盖所有需要认证的模块"""

    def test_products_uses_current_user(self):
        sources = _all_api_sources()
        assert _module_uses_dep("products", "get_current_user", sources) or \
            _module_uses_dep("products", "require_permission", sources)

    def test_customers_uses_current_user(self):
        sources = _all_api_sources()
        assert _module_uses_dep("customers", "get_current_user", sources) or \
            _module_uses_dep("customers", "require_permission", sources)

    def test_orders_uses_current_user(self):
        sources = _all_api_sources()
        assert _module_uses_dep("orders", "get_current_user", sources) or \
            _module_uses_dep("orders", "require_permission", sources)

    def test_payments_uses_current_user(self):
        sources = _all_api_sources()
        assert _module_uses_dep("payments", "get_current_user", sources) or \
            _module_uses_dep("payments", "require_permission", sources)

    def test_users_uses_current_user(self):
        sources = _all_api_sources()
        assert _module_uses_dep("users", "get_current_user", sources)


# ═══════════════════════════════════════════════════════════
# 6. safe_commit 使用完整性（5 项）
# ═══════════════════════════════════════════════════════════


class TestSafeCommitUsage:
    """验证写操作模块都使用 safe_commit"""

    def test_all_write_modules_use_safe_commit(self):
        """所有有写操作的模块都使用 safe_commit"""
        sources = _all_api_sources()
        write_modules = ["products", "customers", "orders", "users", "roles"]
        for mod in write_modules:
            assert _module_uses_dep(mod, "safe_commit", sources), \
                f"{mod} 未使用 safe_commit"

    def test_payments_uses_safe_commit(self):
        sources = _all_api_sources()
        assert _module_uses_dep("payments", "safe_commit", sources)

    def test_auth_uses_safe_commit(self):
        sources = _all_api_sources()
        assert _module_uses_dep("auth", "safe_commit", sources)

    def test_files_uses_safe_commit(self):
        sources = _all_api_sources()
        assert _module_uses_dep("files", "safe_commit", sources)

    def test_health_no_safe_commit(self):
        """健康检查模块无需 safe_commit"""
        sources = _all_api_sources()
        assert not _module_uses_dep("health", "safe_commit", sources)


# ═══════════════════════════════════════════════════════════
# 7. 辅助函数使用一致性（5 项）
# ═══════════════════════════════════════════════════════════


class TestHelperFunctionUsage:
    """验证辅助函数使用一致性"""

    def test_get_or_404_used_in_crud_modules(self):
        sources = _all_api_sources()
        crud_with_get_or = ["products", "customers", "orders"]
        for mod in crud_with_get_or:
            assert _module_uses_dep(mod, "get_or_404", sources), \
                f"{mod} 未使用 get_or_404"

    def test_active_query_used_in_modules(self):
        sources = _all_api_sources()
        # active_query 应在至少 3 个模块中使用
        users_count = sum(1 for s in sources.values() if "active_query" in s)
        assert users_count >= 3, f"active_query 仅在 {users_count} 个模块中使用"

    def test_resp_used_in_all_modules(self):
        sources = _all_api_sources()
        for mod_name, source in sources.items():
            if mod_name in ("health", "exports"):
                continue
            if "return" in source:
                assert "resp(" in source or "paginated_resp(" in source, \
                    f"{mod_name} 未使用 resp() 或 paginated_resp()"

    def test_paginated_resp_used_in_list_endpoints(self):
        sources = _all_api_sources()
        list_modules = ["products", "customers", "orders", "payments", "users"]
        for mod in list_modules:
            assert _module_uses_dep(mod, "paginated_resp", sources) or _module_uses_dep(mod, "paginate(", sources), \
                f"{mod} 未使用 paginated_resp 或 paginate"

    def test_fmt_dt_used_for_datetime_formatting(self):
        sources = _all_api_sources()
        users_count = sum(1 for s in sources.values() if "fmt_dt" in s)
        assert users_count >= 2, f"fmt_dt 仅在 {users_count} 个模块中使用"


# ═══════════════════════════════════════════════════════════
# 8. 响应格式一致性（6 项）
# ═══════════════════════════════════════════════════════════


class TestResponseFormat:
    """验证响应构建模式一致性"""

    def test_resp_includes_request_id(self):
        source = DEPS_SOURCE.read_text()
        assert "request_id_ctx" in source
        assert "request_id" in source

    def test_resp_default_message(self):
        source = DEPS_SOURCE.read_text()
        assert '操作成功' in source

    def test_paginated_resp_structure(self):
        source = DEPS_SOURCE.read_text()
        assert '"items"' in source
        assert '"page"' in source
        assert '"page_size"' in source
        assert '"total"' in source

    def test_resp_success_true(self):
        source = DEPS_SOURCE.read_text()
        assert '"success": True' in source or "'success': True" in source

    def test_get_or_404_error_code(self):
        source = DEPS_SOURCE.read_text()
        assert "RESOURCE_NOT_FOUND" in source

    def test_require_permission_error_code(self):
        source = DEPS_SOURCE.read_text()
        assert "AUTH_FORBIDDEN" in source
