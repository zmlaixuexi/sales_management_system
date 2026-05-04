"""需求符合性：OpenAPI tag 与路由模块覆盖验证
验证所有 API 路由模块的 tag 都在 OPENAPI_TAGS 中定义"""


from fastapi.testclient import TestClient

from app.main import OPENAPI_TAGS, app

client = TestClient(app)


def _get_openapi():
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    return resp.json()


class TestOpenAPITagCoverage:
    """每个路由模块的 tag 都在 OPENAPI_TAGS 中"""

    def test_all_router_tags_in_openapi_tags(self):
        """路由中使用的 tag 都在 OPENAPI_TAGS 中定义"""
        defined_tags = {t["name"] for t in OPENAPI_TAGS}
        schema = _get_openapi()
        used_tags = set()
        for path_info in schema["paths"].values():
            for method_info in path_info.values():
                if isinstance(method_info, dict):
                    for tag in method_info.get("tags", []):
                        used_tags.add(tag)
        for tag in used_tags:
            assert tag in defined_tags, f"tag '{tag}' 未在 OPENAPI_TAGS 中定义"

    def test_openapi_tags_all_used(self):
        """OPENAPI_TAGS 中定义的 tag 都被路由使用"""
        schema = _get_openapi()
        used_tags = set()
        for path_info in schema["paths"].values():
            for method_info in path_info.values():
                if isinstance(method_info, dict):
                    for tag in method_info.get("tags", []):
                        used_tags.add(tag)
        defined_tags = {t["name"] for t in OPENAPI_TAGS}
        for tag in defined_tags:
            assert tag in used_tags, f"OPENAPI_TAGS 中定义的 '{tag}' 未被任何路由使用"

    def test_all_tags_have_description(self):
        """所有 OPENAPI_TAGS 有描述"""
        for tag in OPENAPI_TAGS:
            assert "name" in tag
            assert "description" in tag
            assert len(tag["description"]) > 0

    def test_expected_modules_have_tags(self):
        """关键模块都有对应的 tag"""
        defined_tags = {t["name"] for t in OPENAPI_TAGS}
        expected = {"认证", "用户管理", "商品管理", "客户管理", "订单管理", "收款管理", "报表"}
        assert expected.issubset(defined_tags)


class TestOpenAPIRouteModuleCoverage:
    """路由模块覆盖完整性"""

    def test_auth_routes_exist(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/auth/login" in p for p in paths)

    def test_roles_routes_exist(self):
        """角色管理路由存在"""
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/roles" in p for p in paths)

    def test_inventory_routes_exist(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/inventory" in p for p in paths)

    def test_exports_routes_exist(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/exports" in p for p in paths)

    def test_files_routes_exist(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/files" in p for p in paths)

    def test_audit_logs_routes_exist(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/audit-logs" in p for p in paths)

    def test_health_route_exists(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/health" in p for p in paths)

    def test_version_route_exists(self):
        schema = _get_openapi()
        paths = schema["paths"]
        assert any("/version" in p for p in paths)


class TestOpenAPIStructure:
    """OpenAPI 结构验证"""

    def test_openapi_version_3(self):
        schema = _get_openapi()
        assert schema["openapi"].startswith("3.")

    def test_has_info(self):
        schema = _get_openapi()
        assert "info" in schema
        assert schema["info"]["title"] == "销售管理系统"

    def test_has_security_schemes(self):
        schema = _get_openapi()
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert len(schemes) > 0

    def test_all_paths_under_api_v1(self):
        schema = _get_openapi()
        for path in schema["paths"]:
            assert path.startswith("/api/v1/"), f"路径 {path} 不在 /api/v1/ 下"
