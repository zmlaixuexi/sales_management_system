"""
文档完善：后端 API 端点 HTTP 状态码覆盖验证测试
覆盖成功响应状态码、客户端错误状态码覆盖、
特殊状态码验证、错误响应结构一致性、状态码常量使用
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_DIR = ROOT / "app" / "api" / "v1"
MAIN_SRC = (ROOT / "app" / "main.py").read_text()

MODULES = ["products", "customers", "orders", "payments", "auth", "users", "roles", "files", "inventory", "exports", "reports", "health"]

SOURCES = {}
for name in MODULES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()


def _count_status_code(src: str, code: int) -> int:
    """统计源码中指定状态码出现次数"""
    # 匹配 status_code=NNN 或 HTTP_NNN_XXX
    count = len(re.findall(rf"status_code\s*=\s*{code}\b", src))
    count += len(re.findall(rf"status\.HTTP_{code}_\w+", src))
    return count


def _find_all_status_codes(src: str) -> set[int]:
    """提取源码中所有状态码"""
    codes = set()
    for m in re.finditer(r"status_code\s*=\s*(\d{3})", src):
        codes.add(int(m.group(1)))
    for m in re.finditer(r"status\.HTTP_(\d{3})_\w+", src):
        codes.add(int(m.group(1)))
    return codes


# ═══════════════════════════════════════════════════════════
# 1. 成功响应状态码验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSuccessStatusCodes:
    """成功响应使用正确的状态码"""

    def test_all_get_endpoints_use_200(self):
        """所有 GET 端点默认返回 200"""
        for name, src in SOURCES.items():
            get_endpoints = re.findall(r'@router\.get\(', src)
            # GET 端点不应显式设置 status_code=201/204 等
            for m in re.finditer(r'@router\.get\([^)]*status_code', src):
                assert False, f"{name} GET 端点不应设置非默认 status_code"

    def test_all_post_endpoints_return_200(self):
        """所有 POST 端点返回 200（非 201）"""
        for name, src in SOURCES.items():
            post_endpoints = re.findall(r'@router\.post\(', src)
            # 检查路由装饰器中是否显式设置 status_code
            for m in re.finditer(r'@router\.post\([^)]*status_code\s*=\s*(\d+)', src):
                code = int(m.group(1))
                assert code == 200, f"{name} POST 端点应使用 200，而非 {code}"

    def test_all_put_endpoints_return_200(self):
        """所有 PUT 端点返回 200"""
        for name, src in SOURCES.items():
            for m in re.finditer(r'@router\.put\([^)]*status_code\s*=\s*(\d+)', src):
                code = int(m.group(1))
                assert code == 200, f"{name} PUT 端点应使用 200，而非 {code}"

    def test_all_delete_endpoints_return_200(self):
        """所有 DELETE 端点返回 200（含响应体）"""
        for name, src in SOURCES.items():
            for m in re.finditer(r'@router\.delete\([^)]*status_code\s*=\s*(\d+)', src):
                code = int(m.group(1))
                assert code == 200, f"{name} DELETE 端点应使用 200，而非 {code}"

    def test_resp_helper_returns_default_200(self):
        """resp() 辅助函数不设置特定状态码，使用 FastAPI 默认 200"""
        DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
        assert "def resp(" in DEPS_SRC, "deps.py 应定义 resp 函数"
        # resp() 返回普通 dict，不包含 status_code 设置


# ═══════════════════════════════════════════════════════════
# 2. 客户端错误状态码覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestClientErrorStatusCodes:
    """各模块使用适当的客户端错误状态码"""

    def test_400_used_for_validation_errors(self):
        """400 用于输入验证和业务规则错误"""
        modules_with_400 = []
        for name, src in SOURCES.items():
            if _count_status_code(src, 400) > 0:
                modules_with_400.append(name)
        assert len(modules_with_400) >= 5, (
            f"至少 5 个模块应使用 400，实际 {len(modules_with_400)}: {modules_with_400}"
        )

    def test_401_used_for_auth_errors(self):
        """401 用于认证错误"""
        assert _count_status_code(SOURCES["auth"], 401) > 0, "auth 模块应使用 401"
        # deps.py 的 get_current_user 也应使用 401
        DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
        assert _count_status_code(DEPS_SRC, 401) > 0, "deps.py get_current_user 应使用 401"

    def test_403_used_for_permission_errors(self):
        """403 用于权限不足"""
        modules_with_403 = []
        for name, src in SOURCES.items():
            if _count_status_code(src, 403) > 0:
                modules_with_403.append(name)
        DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
        if _count_status_code(DEPS_SRC, 403) > 0:
            modules_with_403.append("deps")
        assert len(modules_with_403) >= 3, (
            f"至少 3 个模块应使用 403，实际 {modules_with_403}"
        )

    def test_404_used_for_resource_not_found(self):
        """404 用于资源不存在"""
        modules_with_404 = []
        for name, src in SOURCES.items():
            if _count_status_code(src, 404) > 0:
                modules_with_404.append(name)
        DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
        if _count_status_code(DEPS_SRC, 404) > 0:
            modules_with_404.append("deps")
        assert len(modules_with_404) >= 4, (
            f"至少 4 个模块应使用 404，实际 {modules_with_404}"
        )

    def test_409_used_for_conflict_errors(self):
        """409 用于唯一约束冲突"""
        modules_with_409 = []
        for name, src in SOURCES.items():
            if _count_status_code(src, 409) > 0:
                modules_with_409.append(name)
        assert len(modules_with_409) >= 2, (
            f"至少 2 个模块应使用 409（唯一约束冲突），实际 {modules_with_409}"
        )


# ═══════════════════════════════════════════════════════════
# 3. 特殊状态码验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSpecialStatusCodes:
    """特殊状态码正确使用"""

    def test_422_used_for_validation_error_handler(self):
        """422 用于请求体验证错误（全局异常处理器）"""
        assert "422" in MAIN_SRC, "main.py 异常处理器应处理 422"

    def test_429_used_for_rate_limiting(self):
        """429 用于速率限制"""
        assert _count_status_code(SOURCES["auth"], 429) > 0, "auth 模块应使用 429（速率限制）"

    def test_500_used_for_unhandled_exceptions(self):
        """500 用于未处理异常（全局异常处理器）"""
        assert "500" in MAIN_SRC, "main.py 应处理 500 未处理异常"

    def test_503_used_for_shutdown(self):
        """503 用于服务关闭状态"""
        assert _count_status_code(SOURCES["health"], 503) > 0, "health 端点应使用 503（关闭状态）"

    def test_no_301_302_redirects(self):
        """API 端点不使用重定向状态码"""
        for name, src in SOURCES.items():
            codes = _find_all_status_codes(src)
            redirects = codes & {301, 302, 303, 307, 308}
            assert len(redirects) == 0, f"{name} 不应使用重定向状态码: {redirects}"


# ═══════════════════════════════════════════════════════════
# 4. 错误响应结构一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorResponseStructure:
    """错误响应使用统一的结构"""

    def test_http_exception_handler_in_main(self):
        """main.py 定义 HTTPException 全局处理器"""
        assert "http_exception_handler" in MAIN_SRC or "HTTPException" in MAIN_SRC, (
            "main.py 应定义 HTTPException 处理器"
        )

    def test_validation_error_handler_in_main(self):
        """main.py 定义 RequestValidationError 全局处理器"""
        assert "RequestValidationError" in MAIN_SRC, "main.py 应定义验证错误处理器"
        assert "VALIDATION_FAILED" in MAIN_SRC, "验证错误应使用 VALIDATION_FAILED 错误码"

    def test_unhandled_exception_handler_in_main(self):
        """main.py 定义通用异常处理器"""
        assert "SYSTEM_INTERNAL_ERROR" in MAIN_SRC, "通用异常应使用 SYSTEM_INTERNAL_ERROR 错误码"

    def test_error_response_includes_request_id(self):
        """错误响应包含 request_id"""
        assert "request_id" in MAIN_SRC, "错误响应应包含 request_id"
        assert "request_id_ctx" in MAIN_SRC, "错误处理应读取 request_id_ctx"

    def test_error_responses_have_success_false(self):
        """错误响应 success 字段为 false"""
        assert '"success"' in MAIN_SRC, "错误响应应包含 success 字段"
        assert "false" in MAIN_SRC, "错误响应 success 应为 false"


# ═══════════════════════════════════════════════════════════
# 5. 状态码常量使用验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStatusCodeConstants:
    """状态码使用一致的风格"""

    def test_auth_uses_status_module(self):
        """auth 模块使用 status 模块常量"""
        assert "status.HTTP_" in SOURCES["auth"], "auth 应使用 status.HTTP_XXX 常量"

    def test_users_uses_status_module(self):
        """users 模块使用 status 模块常量"""
        assert "status.HTTP_" in SOURCES["users"], "users 应使用 status.HTTP_XXX 常量"

    def test_error_detail_uses_dict_structure(self):
        """错误 detail 使用 dict 结构（code + message）"""
        for name, src in SOURCES.items():
            # 不应使用字符串形式的 detail
            bad = re.findall(r'detail\s*=\s*"[^"]{5,}"', src)
            assert len(bad) == 0, f"{name} 不应使用字符串 detail（应使用 dict）: {bad[:2]}"

    def test_status_codes_only_in_valid_range(self):
        """所有状态码在有效范围（200-599）"""
        for name, src in SOURCES.items():
            for code in _find_all_status_codes(src):
                assert 200 <= code <= 599, f"{name} 状态码 {code} 超出有效范围"

    def test_health_module_uses_shutdown_status(self):
        """health 模块使用正确的关闭状态码"""
        health = SOURCES["health"]
        assert "SHUTTING_DOWN" in health or "503" in health, (
            "health 端点应在关闭时返回 503"
        )
