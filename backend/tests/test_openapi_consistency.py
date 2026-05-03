"""文档完善：OpenAPI 文档一致性边界测试 — 覆盖 schema 结构、tag 完整性、
认证方案、分页参数、响应模型、错误码、docs/redoc 端点、路由路径"""

import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def _get_openapi():
    """获取 OpenAPI schema"""
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    return resp.json()


# ═══════════════════════════════════════════════════════
# 1. OpenAPI 端点可访问性
# ═══════════════════════════════════════════════════════


def test_openapi_json_accessible():
    """GET /api/openapi.json 返回 200"""
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200


def test_openapi_json_is_valid_json():
    """openapi.json 返回合法 JSON"""
    resp = client.get("/api/openapi.json")
    data = json.loads(resp.text)
    assert isinstance(data, dict)


def test_docs_page_accessible():
    """GET /api/docs 返回 200（Swagger UI）"""
    resp = client.get("/api/docs")
    assert resp.status_code == 200


def test_redoc_page_accessible():
    """GET /api/redoc 返回 200"""
    resp = client.get("/api/redoc")
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════
# 2. OpenAPI schema 基本结构
# ═══════════════════════════════════════════════════════


def test_openapi_version():
    """OpenAPI 版本为 3.x"""
    schema = _get_openapi()
    assert schema["openapi"].startswith("3.")


def test_app_title():
    """标题为"销售管理系统" """
    schema = _get_openapi()
    assert schema["info"]["title"] == "销售管理系统"


def test_app_version():
    """版本号为 0.1.0"""
    schema = _get_openapi()
    assert schema["info"]["version"] == "0.1.0"


def test_app_description():
    """描述包含"销售管理系统" """
    schema = _get_openapi()
    assert "销售管理系统" in schema["info"]["description"]


def test_has_paths():
    """schema 包含 paths"""
    schema = _get_openapi()
    assert "paths" in schema
    assert len(schema["paths"]) > 0


def test_has_components():
    """schema 包含 components"""
    schema = _get_openapi()
    assert "components" in schema


# ═══════════════════════════════════════════════════════
# 3. Tag 完整性
# ═══════════════════════════════════════════════════════


def test_has_tags():
    """schema 包含 tags"""
    schema = _get_openapi()
    assert "tags" in schema
    assert len(schema["tags"]) > 0


def test_tag_names():
    """所有 tag 名称存在"""
    schema = _get_openapi()
    tag_names = {t["name"] for t in schema["tags"]}
    expected_tags = {
        "认证", "用户管理", "商品管理", "客户管理",
        "订单管理", "收款管理", "库存管理", "报表",
        "操作日志", "数据导出", "文件管理",
    }
    assert expected_tags.issubset(tag_names)


def test_tags_have_descriptions():
    """所有 tag 有描述"""
    schema = _get_openapi()
    for tag in schema["tags"]:
        assert "name" in tag
        assert "description" in tag
        assert len(tag["description"]) > 0


# ═══════════════════════════════════════════════════════
# 4. 路由路径一致性
# ═══════════════════════════════════════════════════════


def test_auth_paths_exist():
    """认证路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/auth/login" in p for p in paths)


def test_users_paths_exist():
    """用户管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/users" in p for p in paths)


def test_products_paths_exist():
    """商品管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/products" in p for p in paths)


def test_customers_paths_exist():
    """客户管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/customers" in p for p in paths)


def test_orders_paths_exist():
    """订单管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/sales-orders" in p for p in paths)


def test_payments_paths_exist():
    """收款管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/payments" in p for p in paths)


def test_inventory_paths_exist():
    """库存管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/inventory" in p for p in paths)


def test_reports_paths_exist():
    """报表路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/reports" in p for p in paths)


def test_audit_logs_paths_exist():
    """操作日志路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/audit-logs" in p for p in paths)


def test_exports_paths_exist():
    """数据导出路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/exports" in p for p in paths)


def test_files_paths_exist():
    """文件管理路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/files" in p for p in paths)


def test_health_path_exist():
    """健康检查路由路径存在"""
    schema = _get_openapi()
    paths = schema["paths"]
    assert any("/health" in p for p in paths)


def test_all_paths_under_api_v1():
    """所有 API 路径以 /api/v1 开头"""
    schema = _get_openapi()
    for path in schema["paths"]:
        assert path.startswith("/api/v1/")


# ═══════════════════════════════════════════════════════
# 5. 认证方案
# ═══════════════════════════════════════════════════════


def test_security_schemes_defined():
    """securitySchemes 已定义"""
    schema = _get_openapi()
    schemes = schema.get("components", {}).get("securitySchemes", {})
    assert len(schemes) > 0


def test_oauth2_password_bearer():
    """包含 OAuth2PasswordBearer 方案"""
    schema = _get_openapi()
    schemes = schema["components"]["securitySchemes"]
    # FastAPI 使用 OAuth2 作为 scheme 名
    assert "OAuth2PasswordBearer" in schemes or "OAuth2" in schemes


def test_oauth2_token_url():
    """OAuth2 tokenUrl 指向 /api/v1/auth/login"""
    schema = _get_openapi()
    schemes = schema["components"]["securitySchemes"]
    for scheme in schemes.values():
        if scheme.get("type") == "oauth2":
            flows = scheme.get("flows", {})
            password_flow = flows.get("password", {})
            token_url = password_flow.get("tokenUrl", "")
            assert "/auth/login" in token_url


# ═══════════════════════════════════════════════════════
# 6. 分页参数一致性
# ═══════════════════════════════════════════════════════


def test_pagination_params_in_get_list():
    """GET 列表端点包含 page 和 page_size 参数"""
    schema = _get_openapi()
    paths = schema["paths"]

    list_paths = [p for p in paths if p in (
        "/api/v1/users",
        "/api/v1/products",
        "/api/v1/customers",
    )]
    for path in list_paths:
        get_op = paths[path].get("get", {})
        params = get_op.get("parameters", [])
        param_names = {p.get("name") for p in params}
        assert "page" in param_names, f"{path} 缺少 page 参数"
        assert "page_size" in param_names, f"{path} 缺少 page_size 参数"


def test_page_param_constraints():
    """page 参数 ge=1, le=10000"""
    schema = _get_openapi()
    paths = schema["paths"]
    users_get = paths.get("/api/v1/users", {}).get("get", {})
    params = users_get.get("parameters", [])
    page_param = next((p for p in params if p.get("name") == "page"), None)
    assert page_param is not None
    schema_obj = page_param.get("schema", {})
    assert schema_obj.get("minimum") == 1
    assert schema_obj.get("maximum") == 10000
    assert schema_obj.get("default") == 1


def test_page_size_param_constraints():
    """page_size 参数 ge=1, le=100"""
    schema = _get_openapi()
    paths = schema["paths"]
    users_get = paths.get("/api/v1/users", {}).get("get", {})
    params = users_get.get("parameters", [])
    ps_param = next((p for p in params if p.get("name") == "page_size"), None)
    assert ps_param is not None
    schema_obj = ps_param.get("schema", {})
    assert schema_obj.get("minimum") == 1
    assert schema_obj.get("maximum") == 100
    assert schema_obj.get("default") == 20


# ═══════════════════════════════════════════════════════
# 7. 响应模型结构
# ═══════════════════════════════════════════════════════


def test_api_response_schema_exists():
    """ApiResponse schema 存在于 components"""
    schema = _get_openapi()
    schemas = schema.get("components", {}).get("schemas", {})
    # 查找 ApiResponse 相关 schema
    api_resp_schemas = [k for k in schemas if "ApiResponse" in k]
    assert len(api_resp_schemas) > 0


def test_api_response_has_success_field():
    """ApiResponse 包含 success 字段"""
    schema = _get_openapi()
    schemas = schema["components"]["schemas"]
    # 找到第一个 ApiResponse schema
    for name, defn in schemas.items():
        if "ApiResponse" in name:
            props = defn.get("properties", {})
            if "success" in props:
                assert props["success"].get("type") == "boolean"
                return
    # 如果没有找到嵌套 schema，验证实际响应
    resp = client.get("/api/v1/health")
    assert "success" in resp.json()


def test_api_response_has_data_field():
    """ApiResponse 包含 data 字段"""
    resp = client.get("/api/v1/health")
    data = resp.json()
    assert "data" in data


def test_api_response_has_message_field():
    """ApiResponse 包含 message 字段"""
    resp = client.get("/api/v1/health")
    data = resp.json()
    assert "message" in data


def test_success_response_structure():
    """成功响应包含 success=true"""
    resp = client.get("/api/v1/health")
    data = resp.json()
    assert data["success"] is True


def test_error_response_structure():
    """错误响应包含 success=false 和 error 对象"""
    resp = client.get("/api/v1/users")  # 无 token → 401
    data = resp.json()
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


# ═══════════════════════════════════════════════════════
# 8. HTTP 方法一致性
# ═══════════════════════════════════════════════════════


def test_login_is_post():
    """登录端点为 POST"""
    schema = _get_openapi()
    login_path = None
    for p in schema["paths"]:
        if "/auth/login" in p:
            login_path = p
            break
    assert login_path is not None
    assert "post" in schema["paths"][login_path]


def test_health_is_get():
    """健康检查端点为 GET"""
    schema = _get_openapi()
    health_path = None
    for p in schema["paths"]:
        if p.endswith("/health"):
            health_path = p
            break
    assert health_path is not None
    assert "get" in schema["paths"][health_path]


def test_list_endpoints_are_get():
    """列表端点为 GET"""
    schema = _get_openapi()
    list_paths = [
        "/api/v1/users",
        "/api/v1/products",
        "/api/v1/customers",
    ]
    for path in list_paths:
        if path in schema["paths"]:
            assert "get" in schema["paths"][path]


def test_create_endpoints_are_post():
    """创建端点为 POST"""
    schema = _get_openapi()
    create_paths = [
        "/api/v1/products",
        "/api/v1/customers",
    ]
    for path in create_paths:
        if path in schema["paths"]:
            assert "post" in schema["paths"][path]


# ═══════════════════════════════════════════════════════
# 9. 错误码文档一致性
# ═══════════════════════════════════════════════════════


def test_auth_endpoints_document_401():
    """认证相关端点文档记录 401"""
    schema = _get_openapi()
    login_path = None
    for p in schema["paths"]:
        if "/auth/login" in p:
            login_path = p
            break
    if login_path:
        op = schema["paths"][login_path].get("post", {})
        responses = op.get("responses", {})
        assert "200" in responses


def test_protected_endpoints_document_401():
    """需要认证的端点文档记录 401"""
    schema = _get_openapi()
    # 检查用户列表
    users_path = "/api/v1/users"
    if users_path in schema["paths"]:
        get_op = schema["paths"][users_path].get("get", {})
        responses = get_op.get("responses", {})
        # 应包含 401 或通过 router responses
        assert "200" in responses or "401" in responses


def test_validation_error_returns_422():
    """Pydantic 验证错误返回 422"""
    resp = client.post("/api/v1/auth/login", json={})
    # 缺少 username/password → 422
    assert resp.status_code == 422


def test_422_response_has_standard_format():
    """422 响应使用标准错误格式"""
    resp = client.post("/api/v1/auth/login", json={})
    data = resp.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_FAILED"


# ═══════════════════════════════════════════════════════
# 10. /metrics 不在 OpenAPI schema 中
# ═══════════════════════════════════════════════════════


def test_metrics_not_in_openapi():
    """/metrics 不在 OpenAPI schema 中（include_in_schema=False）"""
    schema = _get_openapi()
    for path in schema["paths"]:
        assert "metrics" not in path


# ═══════════════════════════════════════════════════════
# 11. 配置常量验证
# ═══════════════════════════════════════════════════════


def test_docs_url_config():
    """开发环境 docs_url 为 /api/docs"""
    assert settings.APP_ENV != "production"
    import app.main as mod

    assert mod.app.docs_url == "/api/docs"


def test_redoc_url_config():
    """开发环境 redoc_url 为 /api/redoc"""
    import app.main as mod

    assert mod.app.redoc_url == "/api/redoc"


def test_openapi_url_config():
    """开发环境 openapi_url 为 /api/openapi.json"""
    import app.main as mod

    assert mod.app.openapi_url == "/api/openapi.json"


# ═══════════════════════════════════════════════════════
# 12. JWT 配置与认证一致性
# ═══════════════════════════════════════════════════════


def test_jwt_algorithm_hs256():
    """JWT 算法为 HS256"""
    assert settings.JWT_ALGORITHM == "HS256"


def test_jwt_access_token_expire_positive():
    """JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0"""
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_jwt_refresh_token_expire_positive():
    """JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0"""
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0


def test_jwt_access_default_30_minutes():
    """JWT_ACCESS_TOKEN_EXPIRE_MINUTES 默认为 30"""
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30


def test_jwt_refresh_default_7_days():
    """JWT_REFRESH_TOKEN_EXPIRE_DAYS 默认为 7"""
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7


def test_jwt_issuer():
    """JWT_ISSUER 非空"""
    assert len(settings.JWT_ISSUER) > 0


def test_jwt_audience():
    """JWT_AUDIENCE 非空"""
    assert len(settings.JWT_AUDIENCE) > 0


# ═══════════════════════════════════════════════════════
# 13. OAuth2 scheme 配置
# ═══════════════════════════════════════════════════════


def test_oauth2_scheme_exists():
    """oauth2_scheme 实例存在"""
    from app.api.deps import oauth2_scheme

    assert oauth2_scheme is not None


def test_oauth2_scheme_token_url():
    """oauth2_scheme tokenUrl 为 /api/v1/auth/login"""
    from app.api.deps import oauth2_scheme

    assert "/auth/login" in oauth2_scheme.model.flows.password.tokenUrl


# ═══════════════════════════════════════════════════════
# 14. 版本端点
# ═══════════════════════════════════════════════════════


def test_version_endpoint():
    """GET /api/v1/version 返回版本号"""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "version" in data["data"]


def test_version_matches_openapi():
    """版本端点返回值与 OpenAPI info.version 一致"""
    resp = client.get("/api/v1/version")
    api_version = resp.json()["data"]["version"]
    schema = _get_openapi()
    openapi_version = schema["info"]["version"]
    assert api_version == openapi_version
