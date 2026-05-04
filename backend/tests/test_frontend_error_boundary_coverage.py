"""
代码质量：前端错误边界与全局异常捕获验证测试
覆盖 ErrorBoundary 组件实现、ErrorBoundary 集成使用、
API 客户端错误处理、Hook 错误处理模式、错误工具函数
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # 项目根目录

FRONTEND_DIR = ROOT / "frontend" / "src"

ERROR_BOUNDARY_SRC = (FRONTEND_DIR / "components" / "ErrorBoundary.tsx").read_text()
MAIN_SRC = (FRONTEND_DIR / "main.tsx").read_text()
ROUTES_SRC = (FRONTEND_DIR / "routes" / "index.tsx").read_text()
CLIENT_SRC = (FRONTEND_DIR / "api" / "client.ts").read_text()
REQUEST_SRC = (FRONTEND_DIR / "api" / "request.ts").read_text()
HOOKS_PAGINATED_SRC = (FRONTEND_DIR / "hooks" / "usePaginatedList.ts").read_text()
HOOKS_SUBMIT_SRC = (FRONTEND_DIR / "hooks" / "useSubmit.ts").read_text()
UTILS_SRC = (FRONTEND_DIR / "utils" / "index.ts").read_text()
PROTECTED_ROUTE_SRC = (FRONTEND_DIR / "routes" / "ProtectedRoute.tsx").read_text()


# ═══════════════════════════════════════════════════════════
# 1. ErrorBoundary 组件实现验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorBoundaryComponent:
    """ErrorBoundary 组件实现正确"""

    def test_error_boundary_has_class_component(self):
        """使用 class 组件实现 getDerivedStateFromError"""
        assert "getDerivedStateFromError" in ERROR_BOUNDARY_SRC, (
            "ErrorBoundary 应实现 getDerivedStateFromError"
        )
        assert "hasError" in ERROR_BOUNDARY_SRC, "应有 hasError 状态"

    def test_error_boundary_renders_result_component(self):
        """错误时渲染 Ant Design Result 组件"""
        assert 'Result' in ERROR_BOUNDARY_SRC, "应使用 Ant Design Result 组件"
        assert 'status="error"' in ERROR_BOUNDARY_SRC or "status='error'" in ERROR_BOUNDARY_SRC, (
            "Result 应设置 status=error"
        )

    def test_error_boundary_has_retry_button(self):
        """有重试按钮重置错误状态"""
        assert "重试" in ERROR_BOUNDARY_SRC, "应有重试按钮"
        assert "setState" in ERROR_BOUNDARY_SRC or "resetState" in ERROR_BOUNDARY_SRC, (
            "重试应重置错误状态"
        )

    def test_error_boundary_has_home_navigation(self):
        """有返回首页导航"""
        assert "返回首页" in ERROR_BOUNDARY_SRC or "Return Home" in ERROR_BOUNDARY_SRC, (
            "应有返回首页按钮"
        )
        assert "/" in ERROR_BOUNDARY_SRC, "应导航到首页路径"

    def test_error_boundary_resets_on_route_change(self):
        """路由变化时自动重置（通过 resetKey 或 location）"""
        assert "componentDidUpdate" in ERROR_BOUNDARY_SRC, (
            "应通过 componentDidUpdate 监听 resetKey 变化"
        )
        assert "resetKey" in ERROR_BOUNDARY_SRC, "应接收 resetKey 属性"
        assert "location.pathname" in ERROR_BOUNDARY_SRC or "pathname" in ERROR_BOUNDARY_SRC, (
            "resetKey 应使用 location.pathname"
        )


# ═══════════════════════════════════════════════════════════
# 2. ErrorBoundary 集成使用验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorBoundaryIntegration:
    """ErrorBoundary 在应用中正确集成"""

    def test_error_boundary_used_in_main(self):
        """ErrorBoundary 在 main.tsx 中包裹应用"""
        assert "ErrorBoundary" in MAIN_SRC, "main.tsx 应导入 ErrorBoundary"
        assert "<ErrorBoundary>" in MAIN_SRC, "应使用 ErrorBoundary 组件"

    def test_error_boundary_wraps_outlet(self):
        """ErrorBoundary 包裹 Outlet"""
        assert "Outlet" in MAIN_SRC, "应使用 Outlet 渲染路由"
        # ErrorBoundary 应在 Outlet 外层
        eb_pos = MAIN_SRC.find("<ErrorBoundary>")
        outlet_pos = MAIN_SRC.find("<Outlet />")
        assert outlet_pos > eb_pos > 0, "ErrorBoundary 应包裹 Outlet"

    def test_routes_use_suspense_for_lazy_loading(self):
        """路由使用 Suspense 包裹懒加载组件"""
        assert "Suspense" in ROUTES_SRC, "应使用 Suspense"
        assert "fallback" in ROUTES_SRC, "Suspense 应有 fallback"

    def test_loading_fallback_uses_spin(self):
        """Suspense fallback 使用 Ant Design Spin"""
        assert "Spin" in ROUTES_SRC, "Loading fallback 应使用 Spin"
        assert "lazyPage" in ROUTES_SRC, "应使用 lazyPage 辅助函数"

    def test_main_uses_create_browser_router(self):
        """main.tsx 使用 createBrowserRouter"""
        assert "createBrowserRouter" in MAIN_SRC, "应使用 createBrowserRouter"
        assert "RouterProvider" in MAIN_SRC, "应使用 RouterProvider 渲染"


# ═══════════════════════════════════════════════════════════
# 3. API 客户端错误处理验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestApiClientErrorHandling:
    """API 客户端正确处理各类错误"""

    def test_client_handles_401_with_refresh(self):
        """401 错误触发 token 刷新"""
        assert "401" in CLIENT_SRC, "应处理 401 状态码"
        assert "refresh" in CLIENT_SRC.lower(), "应尝试刷新 token"
        assert "access_token" in CLIENT_SRC, "应存储 access_token"

    def test_client_handles_429_with_retry(self):
        """429 错误自动重试"""
        assert "429" in CLIENT_SRC, "应处理 429 状态码"
        assert "Retry-After" in CLIENT_SRC or "retry" in CLIENT_SRC.lower(), (
            "应使用 Retry-After 头或重试机制"
        )
        assert "_retry429" in CLIENT_SRC or "_retry" in CLIENT_SRC, (
            "应有重试标记防止无限重试"
        )

    def test_client_shows_error_toast(self):
        """错误响应显示 Ant Design message 提示"""
        assert "message.error" in CLIENT_SRC, "应使用 message.error 显示错误"
        assert "请求过于频繁" in CLIENT_SRC, "429 应有中文提示"
        assert "没有操作权限" in CLIENT_SRC, "403 应有中文提示"
        assert "服务器错误" in CLIENT_SRC, "500 应有中文提示"

    def test_client_marks_toast_displayed(self):
        """已显示 toast 的错误设置标记防止重复"""
        assert "_toastDisplayed" in CLIENT_SRC, "应设置 _toastDisplayed 标记"
        assert "true" in CLIENT_SRC, "_toastDisplayed 应设为 true"

    def test_client_handles_network_error(self):
        """网络错误有友好提示"""
        assert "网络" in CLIENT_SRC, "网络错误应有中文提示"
        # 检查 request interceptor 添加请求 ID
        assert "X-Request-ID" in CLIENT_SRC, "请求应添加 X-Request-ID 头"


# ═══════════════════════════════════════════════════════════
# 4. Hook 错误处理模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHookErrorHandling:
    """自定义 Hook 正确处理错误和加载状态"""

    def test_use_paginated_list_has_error_state(self):
        """usePaginatedList 维护 error 状态"""
        assert "error" in HOOKS_PAGINATED_SRC, "应有 error 状态"
        assert "loading" in HOOKS_PAGINATED_SRC, "应有 loading 状态"
        assert "setError" in HOOKS_PAGINATED_SRC, "应有 setError 函数"

    def test_use_paginated_list_checks_toast_displayed(self):
        """usePaginatedList 检查 toast 是否已显示"""
        assert "isToastDisplayed" in HOOKS_PAGINATED_SRC, (
            "应检查 isToastDisplayed 防止重复提示"
        )
        assert "message.error" in HOOKS_PAGINATED_SRC, "错误时应显示 message.error"

    def test_use_submit_prevents_double_submission(self):
        """useSubmit 防止重复提交"""
        assert "locked" in HOOKS_SUBMIT_SRC or "submitting" in HOOKS_SUBMIT_SRC, (
            "应有锁定/提交中状态防止重复提交"
        )
        assert "useRef" in HOOKS_SUBMIT_SRC or "useState" in HOOKS_SUBMIT_SRC, (
            "应使用 ref 或 state 管理提交状态"
        )

    def test_use_submit_checks_toast_displayed(self):
        """useSubmit 检查 toast 是否已显示"""
        assert "isToastDisplayed" in HOOKS_SUBMIT_SRC, (
            "应检查 isToastDisplayed 防止重复提示"
        )
        assert "getApiErrorMessage" in HOOKS_SUBMIT_SRC, (
            "应使用 getApiErrorMessage 提取错误信息"
        )

    def test_use_paginated_list_auto_refetches(self):
        """usePaginatedList 在参数变化时自动重新获取"""
        assert "useEffect" in HOOKS_PAGINATED_SRC, "应使用 useEffect 监听参数变化"
        assert "page" in HOOKS_PAGINATED_SRC, "应监听 page 变化"
        assert "pageSize" in HOOKS_PAGINATED_SRC, "应监听 pageSize 变化"


# ═══════════════════════════════════════════════════════════
# 5. 错误工具函数与 ProtectedRoute 验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorUtilitiesAndProtectedRoute:
    """错误工具函数和 ProtectedRoute 正确实现"""

    def test_is_toast_displayed_function_exists(self):
        """isToastDisplayed 工具函数已定义"""
        assert "isToastDisplayed" in UTILS_SRC, "应定义 isToastDisplayed 函数"
        assert "_toastDisplayed" in UTILS_SRC, "应检查 _toastDisplayed 属性"

    def test_get_api_error_message_function_exists(self):
        """getApiErrorMessage 工具函数已定义"""
        assert "getApiErrorMessage" in UTILS_SRC, "应定义 getApiErrorMessage 函数"
        assert "response" in UTILS_SRC, "应从 response 中提取错误信息"
        assert "fallback" in UTILS_SRC, "应有 fallback 参数"

    def test_request_helpers_handle_csv_download_error(self):
        """CSV 下载请求处理错误响应"""
        assert "downloadCsv" in REQUEST_SRC, "应有 downloadCsv 函数"
        assert "application/json" in REQUEST_SRC, "应检查 blob 是否为 JSON 错误响应"

    def test_protected_route_has_loading_state(self):
        """ProtectedRoute 有加载中状态"""
        assert "Spin" in PROTECTED_ROUTE_SRC, "加载中应显示 Spin"
        assert "token" in PROTECTED_ROUTE_SRC, "应检查 token"
        assert "/login" in PROTECTED_ROUTE_SRC, "无 token 应跳转 /login"

    def test_protected_route_fetches_user_info(self):
        """ProtectedRoute 在有 token 时获取用户信息"""
        assert "user" in PROTECTED_ROUTE_SRC or "auth" in PROTECTED_ROUTE_SRC.lower(), (
            "应获取用户信息"
        )
        assert "children" in PROTECTED_ROUTE_SRC, "认证通过后渲染 children"
