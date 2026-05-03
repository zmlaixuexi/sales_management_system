"""API 路由与文档一致性校验 — 确保每个后端路由都有对应的 API 文档"""

import re
from pathlib import Path

from app.main import app

# 从 docs/api.md 提取的已文档化端点（METHOD /path 格式）
_DOC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "api.md"

# 这些路由不需要文档（内部/基础设施端点）
_SKIP_ROUTES = {
    ("/metrics", "GET"),  # Prometheus 采集端点，非业务 API
    ("/openapi.json", "GET"),  # FastAPI 自动生成
    ("/docs", "GET"),  # Swagger UI
    ("/redoc", "GET"),  # ReDoc
}

# 路径参数归一化模式：将 {param_name} 统一
_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalize_path(path: str) -> str:
    """将路径参数统一格式：/users/{user_id} → /users/{id}"""
    return _PARAM_RE.sub("{id}", path)


def _load_documented_endpoints() -> set[tuple[str, str]]:
    """从 docs/api.md 解析所有已文档化的 METHOD /path"""
    documented = set()
    try:
        with _DOC_PATH.open() as f:
            content = f.read()
    except FileNotFoundError:
        return documented

    # 匹配 ### METHOD /path 格式
    for match in re.finditer(r"^### (GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", content, re.MULTILINE):
        method = match.group(1)
        path = match.group(2).strip()
        # 去掉 /api/v1 前缀（文档中省略了基础路径）
        documented.add((_normalize_path(path), method))

    return documented


def _get_app_routes() -> set[tuple[str, str]]:
    """提取所有注册的业务路由"""
    routes = set()
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        path = route.path
        # 只检查 /api/v1/ 下的路由
        if not path.startswith("/api/v1/"):
            continue
        # 去掉 /api/v1 前缀
        short_path = path[len("/api/v1"):]
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            routes.add((_normalize_path(short_path), method))
    return routes


def test_all_routes_are_documented():
    """验证所有后端路由都在 API 文档中有记录"""
    documented = _load_documented_endpoints()
    routes = _get_app_routes()

    undoc = []
    for path, method in sorted(routes):
        if (path, method) in _SKIP_ROUTES:
            continue
        # 检查原始路径和归一化路径
        if (path, method) not in documented:
            undoc.append(f"{method} {path}")

    assert not undoc, (
        f"以下 {len(undoc)} 个路由缺少 API 文档，请在 docs/api.md 中补充：\n"
        + "\n".join(f"  - {r}" for r in undoc)
    )


def test_no_documented_ghost_routes():
    """验证文档中没有不存在的路由（幽灵路由）"""
    documented = _load_documented_endpoints()
    routes = _get_app_routes()

    ghost = []
    for path, method in sorted(documented):
        if (path, method) not in routes:
            ghost.append(f"{method} {path}")

    assert not ghost, (
        f"以下 {len(ghost)} 个文档路由在后端不存在（幽灵路由）：\n"
        + "\n".join(f"  - {r}" for r in ghost)
    )


def test_route_count_reasonable():
    """路由总数应在合理范围内（防止意外大量新增）"""
    routes = _get_app_routes()
    assert 40 <= len(routes) <= 80, f"路由总数 {len(routes)} 异常，预期 40-80"


def test_all_crud_resources_have_delete():
    """核心 CRUD 资源（products、customers、roles）应有 DELETE 端点"""
    routes = _get_app_routes()
    paths = {p for p, m in routes}

    for resource in ["/products/{id}", "/customers/{id}", "/roles/{id}"]:
        assert f"DELETE {resource}" in {f"{m} {p}" for p, m in routes}, (
            f"资源 {resource} 缺少 DELETE 端点"
        )


def test_auth_endpoints_complete():
    """认证端点齐全：login、refresh、logout、me、change-password"""
    routes = {(p, m) for p, m in _get_app_routes()}

    required = [
        ("/auth/login", "POST"),
        ("/auth/refresh", "POST"),
        ("/auth/logout", "POST"),
        ("/auth/me", "GET"),
        ("/auth/change-password", "POST"),
    ]
    missing = [f"{m} {p}" for p, m in required if (p, m) not in routes]
    assert not missing, f"缺少认证端点: {missing}"


def test_export_endpoints_complete():
    """4 种导出端点齐全"""
    routes = _get_app_routes()

    for resource in ["products", "customers", "orders", "payments"]:
        assert (f"/exports/{resource}", "GET") in routes, (
            f"缺少导出端点 GET /exports/{resource}"
        )
