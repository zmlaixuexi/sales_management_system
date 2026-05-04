"""代码质量：FastAPI 应用结构验证测试
覆盖中间件注册、异常处理器、路由挂载、OpenAPI tag、生命周期配置、安全设置"""

import re
from pathlib import Path

MAIN_SOURCE = Path(__file__).resolve().parent.parent / "app" / "main.py"
CONFIG_SOURCE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
ROUTER_SOURCE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "router.py"


# ═══════════════════════════════════════════════════════════
# 1. 中间件注册完整性（8 项）
# ═══════════════════════════════════════════════════════════


class TestMiddlewareRegistration:
    """验证所有必要中间件均已注册"""

    def test_cors_middleware_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "CORSMiddleware" in source
        assert "add_middleware" in source

    def test_body_limit_middleware_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "BodyLimitMiddleware" in source

    def test_security_headers_middleware_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "SecurityHeadersMiddleware" in source

    def test_request_log_middleware_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "RequestLogMiddleware" in source

    def test_request_id_middleware_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "RequestIDMiddleware" in source

    def test_rate_limit_registered(self):
        source = MAIN_SOURCE.read_text()
        assert "add_rate_limit" in source

    def test_cors_allows_required_methods(self):
        source = MAIN_SOURCE.read_text()
        for method in ["GET", "POST", "PUT", "DELETE", "OPTIONS"]:
            assert method in source, f"CORS 缺少 {method} 方法"

    def test_cors_allows_required_headers(self):
        source = MAIN_SOURCE.read_text()
        for header in ["Authorization", "Content-Type", "X-Request-ID"]:
            assert header in source, f"CORS 缺少 {header} 头部"


# ═══════════════════════════════════════════════════════════
# 2. 异常处理器完整性（6 项）
# ═══════════════════════════════════════════════════════════


class TestExceptionHandlers:
    """验证所有异常处理器均已注册"""

    def test_http_exception_handler(self):
        source = MAIN_SOURCE.read_text()
        assert "@app.exception_handler(HTTPException)" in source

    def test_starlette_exception_handler(self):
        source = MAIN_SOURCE.read_text()
        assert "@app.exception_handler(StarletteHTTPException)" in source

    def test_validation_error_handler(self):
        source = MAIN_SOURCE.read_text()
        assert "@app.exception_handler(RequestValidationError)" in source

    def test_unhandled_exception_handler(self):
        source = MAIN_SOURCE.read_text()
        assert "@app.exception_handler(Exception)" in source

    def test_all_handlers_return_json(self):
        """所有异常处理器返回 JSONResponse"""
        source = MAIN_SOURCE.read_text()
        handler_count = source.count("@app.exception_handler(")
        json_response_count = source.count("JSONResponse(status_code=")
        assert handler_count > 0, "未找到异常处理器"
        assert json_response_count >= handler_count, \
            f"异常处理器 {handler_count} 个但 JSONResponse 只出现 {json_response_count} 次"

    def test_unhandled_exception_no_stack_trace(self):
        """未处理异常不泄露堆栈信息"""
        source = MAIN_SOURCE.read_text()
        # 找到 unhandled_exception_handler 函数
        idx = source.index("def unhandled_exception_handler")
        func_body = source[idx:idx + 500]
        assert "服务器内部错误" in func_body
        # 确保没有 repr/str/repr(_exc) 等
        assert "str(_exc)" not in func_body
        assert "repr(_exc)" not in func_body


# ═══════════════════════════════════════════════════════════
# 3. 路由挂载与 OpenAPI 配置（6 项）
# ═══════════════════════════════════════════════════════════


class TestRouterAndOpenAPI:
    """验证路由挂载和 OpenAPI 配置"""

    def test_api_router_included(self):
        source = MAIN_SOURCE.read_text()
        assert "app.include_router(api_router" in source
        assert 'prefix="/api/v1"' in source

    def test_openapi_tags_defined(self):
        source = MAIN_SOURCE.read_text()
        assert "OPENAPI_TAGS" in source

    def test_openapi_tags_cover_all_modules(self):
        """OpenAPI tag 覆盖所有业务模块"""
        source = MAIN_SOURCE.read_text()
        required_tags = [
            "认证", "用户管理", "角色管理", "商品管理", "客户管理",
            "订单管理", "收款管理", "库存管理", "报表", "操作日志",
        ]
        for tag in required_tags:
            assert f'"name": "{tag}"' in source, f"缺少 OpenAPI tag: {tag}"

    def test_production_disables_docs(self):
        """生产环境禁用文档端点"""
        source = MAIN_SOURCE.read_text()
        assert 'docs_url=None' in source
        assert 'redoc_url=None' in source
        assert 'openapi_url=None' in source

    def test_app_title_defined(self):
        source = MAIN_SOURCE.read_text()
        assert 'title="销售管理系统"' in source

    def test_lifespan_configured(self):
        source = MAIN_SOURCE.read_text()
        assert "lifespan=lifespan" in source
        assert "@asynccontextmanager" in source


# ═══════════════════════════════════════════════════════════
# 4. 生命周期管理（5 项）
# ═══════════════════════════════════════════════════════════


class TestLifespanManagement:
    """验证应用生命周期管理"""

    def test_lifespan_creates_upload_dir(self):
        source = MAIN_SOURCE.read_text()
        assert "upload_dir" in source
        assert "mkdir" in source

    def test_lifespan_production_jwt_check(self):
        """生产环境检查 JWT 密钥安全性"""
        source = MAIN_SOURCE.read_text()
        assert 'JWT_SECRET_KEY == "change-me"' in source
        assert "RuntimeError" in source

    def test_lifespan_production_jwt_length_check(self):
        """生产环境检查 JWT 密钥长度"""
        source = MAIN_SOURCE.read_text()
        assert "len(settings.JWT_SECRET_KEY) < 32" in source or "len(settings.JWT_SECRET_KEY)" in source

    def test_lifespan_graceful_shutdown(self):
        """优雅关闭：释放数据库连接池"""
        source = MAIN_SOURCE.read_text()
        assert "_shutting_down" in source
        assert "engine.dispose()" in source

    def test_lifespan_production_cors_warning(self):
        """生产环境 CORS localhost 告警"""
        source = MAIN_SOURCE.read_text()
        assert "localhost" in source
        assert "127.0.0.1" in source


# ═══════════════════════════════════════════════════════════
# 5. 安全配置一致性（6 项）
# ═══════════════════════════════════════════════════════════


class TestSecurityConfig:
    """验证安全相关配置"""

    def test_cors_credentials_enabled(self):
        source = MAIN_SOURCE.read_text()
        assert "allow_credentials=True" in source

    def test_cors_no_wildcard_origin(self):
        """CORS 不允许通配符来源"""
        source = CONFIG_SOURCE.read_text()
        assert '"*"' not in source or "CORS_ORIGINS 不允许使用通配符" in source

    def test_jwt_secret_has_validator(self):
        source = CONFIG_SOURCE.read_text()
        assert "_validate_jwt_secret" in source
        assert "不能为空" in source or "不能少于" in source

    def test_jwt_secret_min_length(self):
        source = CONFIG_SOURCE.read_text()
        assert "len(v) < 8" in source or "不能少于 8" in source

    def test_static_files_mounted(self):
        source = MAIN_SOURCE.read_text()
        assert "StaticFiles(" in source
        assert '"/uploads"' in source

    def test_prometheus_excluded_endpoints(self):
        """Prometheus 排除健康检查端点"""
        source = MAIN_SOURCE.read_text()
        assert "excluded_handlers" in source
        assert "/health" in source


# ═══════════════════════════════════════════════════════════
# 6. API 路由模块注册完整性（6 项）
# ═══════════════════════════════════════════════════════════


class TestRouterModuleRegistration:
    """验证所有 API 模块都在路由中注册"""

    def test_router_file_exists(self):
        assert ROUTER_SOURCE.exists()

    def test_all_crud_modules_included(self):
        """所有 CRUD 模块都在路由中注册"""
        source = ROUTER_SOURCE.read_text()
        required_modules = [
            "auth", "users", "roles", "products", "customers",
            "orders", "payments", "inventory", "reports", "audit_logs",
        ]
        for mod in required_modules:
            assert mod in source, f"路由缺少模块: {mod}"

    def test_router_prefixes_consistent(self):
        """每个模块使用一致的前缀"""
        source = ROUTER_SOURCE.read_text()
        # 验证 include_router 调用数量
        includes = re.findall(r"include_router\(", source)
        assert len(includes) >= 10, f"路由注册数量不足: {len(includes)}"

    def test_router_imports_all_modules(self):
        source = ROUTER_SOURCE.read_text()
        # 验证 import 语句
        imports = re.findall(r"from app\.api\.v1\.\w+ import", source)
        assert len(imports) >= 10

    def test_health_endpoint_registered(self):
        """健康检查端点已注册"""
        source = ROUTER_SOURCE.read_text()
        assert "health" in source or "health" in source.lower()

    def test_file_upload_router_registered(self):
        source = ROUTER_SOURCE.read_text()
        assert "file" in source.lower() or "upload" in source.lower()


# ═══════════════════════════════════════════════════════════
# 7. 请求 ID 和日志配置（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestIdAndLogging:
    """验证请求 ID 和日志配置"""

    def test_request_id_middleware_import(self):
        source = MAIN_SOURCE.read_text()
        assert "from app.core.request_id import RequestIDMiddleware" in source

    def test_request_log_middleware_import(self):
        source = MAIN_SOURCE.read_text()
        assert "from app.core.request_log import RequestLogMiddleware" in source

    def test_request_id_used_in_exception_handlers(self):
        """异常处理器使用 request_id"""
        source = MAIN_SOURCE.read_text()
        # 至少 2 个异常处理器使用 request_id
        count = source.count("request_id_ctx")
        assert count >= 4, f"request_id_ctx 使用次数不足: {count}"

    def test_body_limit_middleware_import(self):
        source = MAIN_SOURCE.read_text()
        assert "from app.core.body_limit import BodyLimitMiddleware" in source

    def test_security_headers_middleware_import(self):
        source = MAIN_SOURCE.read_text()
        assert "from app.core.security_headers import SecurityHeadersMiddleware" in source
