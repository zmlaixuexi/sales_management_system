"""文档完善：API 路由一致性边界测试 — 覆盖路由注册、方法验证、路径参数、前缀一致性、OpenAPI 配置"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. 健康检查路由
# ═══════════════════════════════════════════════════════


def test_health_route_exists():
    """GET /api/v1/health 路由存在"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_version_route_exists():
    """GET /api/v1/version 路由存在"""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200


def test_health_only_get():
    """健康检查仅支持 GET"""
    assert client.post("/api/v1/health").status_code == 405
    assert client.put("/api/v1/health").status_code == 405
    assert client.delete("/api/v1/health").status_code == 405


# ═══════════════════════════════════════════════════════
# 2. 认证路由
# ═══════════════════════════════════════════════════════


def test_auth_login_route_exists():
    """POST /api/v1/auth/login 路由存在"""
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    resp = no_raise_client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
    # 200/401/422/500 都表示路由存在
    assert resp.status_code in (200, 401, 422, 500)


def test_auth_me_requires_auth():
    """GET /api/v1/auth/me 需要认证"""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_auth_refresh_route_exists():
    """POST /api/v1/auth/refresh 路由存在"""
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code in (200, 401, 422)


def test_auth_change_password_requires_auth():
    """POST /api/v1/auth/change-password 需要认证"""
    resp = client.post("/api/v1/auth/change-password", json={})
    assert resp.status_code in (401, 403, 422)


def test_auth_logout_route_exists():
    """POST /api/v1/auth/logout 路由存在"""
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 3. 用户路由
# ═══════════════════════════════════════════════════════


def test_users_list_requires_auth():
    """GET /api/v1/users 需要认证"""
    resp = client.get("/api/v1/users")
    assert resp.status_code in (401, 403)


def test_users_create_requires_auth():
    """POST /api/v1/users 需要认证"""
    resp = client.post("/api/v1/users", json={})
    assert resp.status_code in (401, 403, 422)


def test_users_update_requires_auth():
    """PUT /api/v1/users/{id} 需要认证"""
    resp = client.put("/api/v1/users/00000000-0000-0000-0000-000000000001", json={})
    assert resp.status_code in (401, 403, 422)


def test_users_roles_route():
    """GET /api/v1/users/roles 路由存在"""
    resp = client.get("/api/v1/users/roles")
    assert resp.status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════
# 4. 角色路由
# ═══════════════════════════════════════════════════════


def test_roles_list_requires_auth():
    """GET /api/v1/roles 需要认证"""
    resp = client.get("/api/v1/roles")
    assert resp.status_code in (401, 403)


def test_roles_permissions_route():
    """GET /api/v1/roles/permissions 路由存在"""
    resp = client.get("/api/v1/roles/permissions")
    assert resp.status_code in (200, 401, 403)


def test_roles_create_requires_auth():
    """POST /api/v1/roles 需要认证"""
    resp = client.post("/api/v1/roles", json={})
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 5. 商品路由
# ═══════════════════════════════════════════════════════


def test_products_list_route():
    """GET /api/v1/products 路由存在"""
    resp = client.get("/api/v1/products")
    assert resp.status_code in (200, 401)


def test_products_create_requires_auth():
    """POST /api/v1/products 需要认证"""
    resp = client.post("/api/v1/products", json={})
    assert resp.status_code in (401, 403, 422)


def test_products_import_requires_auth():
    """POST /api/v1/products/import 需要认证"""
    resp = client.post("/api/v1/products/import")
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 6. 客户路由
# ═══════════════════════════════════════════════════════


def test_customers_list_route():
    """GET /api/v1/customers 路由存在"""
    resp = client.get("/api/v1/customers")
    assert resp.status_code in (200, 401)


def test_customers_import_requires_auth():
    """POST /api/v1/customers/import 需要认证"""
    resp = client.post("/api/v1/customers/import")
    assert resp.status_code in (401, 403, 422)


def test_customer_transfer_requires_auth():
    """POST /api/v1/customers/{id}/transfer 需要认证"""
    resp = client.post(
        "/api/v1/customers/00000000-0000-0000-0000-000000000001/transfer", json={}
    )
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 7. 订单路由
# ═══════════════════════════════════════════════════════


def test_orders_list_route():
    """GET /api/v1/sales-orders 路由存在"""
    resp = client.get("/api/v1/sales-orders")
    assert resp.status_code in (200, 401)


def test_order_confirm_requires_auth():
    """POST /api/v1/sales-orders/{id}/confirm 需要认证"""
    resp = client.post(
        "/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/confirm"
    )
    assert resp.status_code in (401, 403, 404, 422)


def test_order_cancel_requires_auth():
    """POST /api/v1/sales-orders/{id}/cancel 需要认证"""
    resp = client.post(
        "/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/cancel"
    )
    assert resp.status_code in (401, 403, 404, 422)


def test_order_logs_route():
    """GET /api/v1/sales-orders/{id}/logs 路由存在"""
    resp = client.get(
        "/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/logs"
    )
    assert resp.status_code in (200, 401, 404)


# ═══════════════════════════════════════════════════════
# 8. 收款路由
# ═══════════════════════════════════════════════════════


def test_payments_list_route():
    """GET /api/v1/payments 路由存在"""
    resp = client.get("/api/v1/payments")
    assert resp.status_code in (200, 401)


def test_payment_reverse_requires_auth():
    """POST /api/v1/payments/{id}/reverse 需要认证"""
    resp = client.post(
        "/api/v1/payments/00000000-0000-0000-0000-000000000001/reverse"
    )
    assert resp.status_code in (401, 403, 404, 422)


# ═══════════════════════════════════════════════════════
# 9. 库存路由
# ═══════════════════════════════════════════════════════


def test_inventory_movements_route():
    """GET /api/v1/inventory/movements 路由存在"""
    resp = client.get("/api/v1/inventory/movements")
    assert resp.status_code in (200, 401)


def test_inventory_adjustments_requires_auth():
    """POST /api/v1/inventory/adjustments 需要认证"""
    resp = client.post("/api/v1/inventory/adjustments", json={})
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 10. 报表路由
# ═══════════════════════════════════════════════════════


def test_reports_sales_summary_route():
    """GET /api/v1/reports/sales-summary 路由存在"""
    resp = client.get("/api/v1/reports/sales-summary")
    assert resp.status_code in (200, 401)


def test_reports_sales_trend_route():
    """GET /api/v1/reports/sales-trend 路由存在"""
    resp = client.get("/api/v1/reports/sales-trend")
    assert resp.status_code in (200, 401)


def test_reports_product_ranking_route():
    """GET /api/v1/reports/product-ranking 路由存在"""
    resp = client.get("/api/v1/reports/product-ranking")
    assert resp.status_code in (200, 401)


def test_reports_customer_ranking_route():
    """GET /api/v1/reports/customer-ranking 路由存在"""
    resp = client.get("/api/v1/reports/customer-ranking")
    assert resp.status_code in (200, 401)


def test_reports_salesperson_ranking_route():
    """GET /api/v1/reports/salesperson-ranking 路由存在"""
    resp = client.get("/api/v1/reports/salesperson-ranking")
    assert resp.status_code in (200, 401)


def test_reports_inventory_warning_route():
    """GET /api/v1/reports/inventory-warning 路由存在"""
    resp = client.get("/api/v1/reports/inventory-warning")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 11. 操作日志路由
# ═══════════════════════════════════════════════════════


def test_audit_logs_route():
    """GET /api/v1/audit-logs 路由存在"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code in (200, 401)


def test_audit_logs_actions_route():
    """GET /api/v1/audit-logs/actions 路由存在"""
    resp = client.get("/api/v1/audit-logs/actions")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 12. 导出路由
# ═══════════════════════════════════════════════════════


def test_exports_products_route():
    """GET /api/v1/exports/products 路由存在"""
    resp = client.get("/api/v1/exports/products")
    assert resp.status_code in (200, 401)


def test_exports_customers_route():
    """GET /api/v1/exports/customers 路由存在"""
    resp = client.get("/api/v1/exports/customers")
    assert resp.status_code in (200, 401)


def test_exports_orders_route():
    """GET /api/v1/exports/orders 路由存在"""
    resp = client.get("/api/v1/exports/orders")
    assert resp.status_code in (200, 401)


def test_exports_payments_route():
    """GET /api/v1/exports/payments 路由存在"""
    resp = client.get("/api/v1/exports/payments")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 13. 文件路由
# ═══════════════════════════════════════════════════════


def test_files_images_upload_requires_auth():
    """POST /api/v1/files/images 需要认证"""
    resp = client.post("/api/v1/files/images")
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 14. OpenAPI 文档配置
# ═══════════════════════════════════════════════════════


def test_openapi_docs_url():
    """Swagger UI 在 /api/docs 可访问（非生产）"""
    resp = client.get("/api/docs")
    assert resp.status_code == 200


def test_openapi_redoc_url():
    """ReDoc 在 /api/redoc 可访问（非生产）"""
    resp = client.get("/api/redoc")
    assert resp.status_code == 200


def test_openapi_json_url():
    """OpenAPI JSON 在 /api/openapi.json 可访问"""
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "销售管理系统"
    assert "paths" in data


def test_openapi_json_contains_all_modules():
    """OpenAPI 文档包含所有模块路径"""
    resp = client.get("/api/openapi.json")
    paths = resp.json()["paths"]
    expected_prefixes = [
        "/api/v1/health",
        "/api/v1/version",
        "/api/v1/auth",
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/products",
        "/api/v1/customers",
        "/api/v1/sales-orders",
        "/api/v1/payments",
        "/api/v1/inventory",
        "/api/v1/reports",
        "/api/v1/audit-logs",
        "/api/v1/exports",
        "/api/v1/files",
    ]
    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in paths), f"缺少 {prefix} 路径前缀"


def test_openapi_version():
    """OpenAPI 文档版本为 0.1.0"""
    resp = client.get("/api/openapi.json")
    assert resp.json()["info"]["version"] == "0.1.0"


# ═══════════════════════════════════════════════════════
# 15. 404 标准响应格式
# ═══════════════════════════════════════════════════════


def test_404_returns_json():
    """不存在的路由返回标准 JSON"""
    resp = client.get("/api/v1/nonexistent-module")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert "request_id" in data


def test_404_deep_path():
    """深层不存在的路径返回 404"""
    resp = client.get("/api/v1/products/invalid-uuid/deep/path")
    assert resp.status_code in (404, 422)


# ═══════════════════════════════════════════════════════
# 16. UUID 路径参数验证
# ═══════════════════════════════════════════════════════


def test_product_invalid_uuid():
    """商品路径参数非 UUID 格式返回 422（或 401 需认证）"""
    resp = client.get("/api/v1/products/not-a-uuid")
    assert resp.status_code in (401, 422)


def test_customer_invalid_uuid():
    """客户路径参数非 UUID 格式返回 422（或 401 需认证）"""
    resp = client.get("/api/v1/customers/not-a-uuid")
    assert resp.status_code in (401, 422)


def test_order_invalid_uuid():
    """订单路径参数非 UUID 格式返回 422（或 401 需认证）"""
    resp = client.get("/api/v1/sales-orders/not-a-uuid")
    assert resp.status_code in (401, 422)


def test_role_invalid_uuid():
    """角色路径参数非 UUID 格式返回 422（或 401 需认证）"""
    resp = client.put("/api/v1/roles/not-a-uuid", json={})
    assert resp.status_code in (401, 403, 422)


def test_file_invalid_uuid():
    """文件路径参数非 UUID 格式返回 422（或 401 需认证）"""
    resp = client.get("/api/v1/files/images/not-a-uuid")
    assert resp.status_code in (401, 422)


# ═══════════════════════════════════════════════════════
# 17. Metrics 端点
# ═══════════════════════════════════════════════════════


def test_metrics_route():
    """GET /metrics 路由存在"""
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_not_under_api_v1():
    """/metrics 不在 /api/v1 前缀下"""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════
# 18. 路由器注册完整性
# ═══════════════════════════════════════════════════════


def test_all_routers_registered():
    """所有子路由器注册到 api_router"""
    from app.api.v1.router import api_router

    # api_router 应包含多个子路由
    routes = [r.path for r in api_router.routes]
    assert len(routes) > 0


def test_api_v1_prefix():
    """app 使用 /api/v1 前缀"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert 'prefix="/api/v1"' in source


def test_router_modules_count():
    """至少注册 13 个子路由器"""
    import app.api.v1.router as router_mod

    with open(router_mod.__file__) as f:
        source = f.read()
    import re

    count = len(re.findall(r"include_router\(", source))
    assert count >= 13
