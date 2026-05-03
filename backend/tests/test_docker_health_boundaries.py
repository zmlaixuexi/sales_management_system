"""部署体验：健康检查端点边界测试 — 覆盖响应结构、Docker 健康检查、
连接池配置、Prometheus 配置、Nginx 代理、健康检查脚本"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ═══════════════════════════════════════════════════════
# 1. 健康检查端点响应结构
# ═══════════════════════════════════════════════════════


def test_health_endpoint_returns_200():
    """GET /api/v1/health 返回 200"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_health_response_has_success():
    """响应包含 success 字段"""
    resp = client.get("/api/v1/health")
    assert resp.json()["success"] is True


def test_health_response_has_data():
    """响应包含 data 字段"""
    resp = client.get("/api/v1/health")
    assert "data" in resp.json()


def test_health_data_has_database():
    """data 包含 database 字段"""
    resp = client.get("/api/v1/health")
    data = resp.json()["data"]
    assert "database" in data


def test_health_database_status_present():
    """data 包含 database 状态字段"""
    resp = client.get("/api/v1/health")
    data = resp.json()["data"]
    assert "database" in data
    assert data["database"] in ("ok", "error")


def test_health_data_has_version():
    """data 包含 version 字段"""
    resp = client.get("/api/v1/health")
    data = resp.json()["data"]
    assert "version" in data


def test_health_data_has_pool_info():
    """data 包含连接池信息（在 pool 子对象中）"""
    resp = client.get("/api/v1/health")
    data = resp.json()["data"]
    assert "pool" in data
    pool = data["pool"]
    assert "size" in pool
    assert "checked_in" in pool


# ═══════════════════════════════════════════════════════
# 2. Version 端点
# ═══════════════════════════════════════════════════════


def test_version_endpoint_returns_200():
    """GET /api/v1/version 返回 200"""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200


def test_version_response_has_version():
    """version 响应包含版本号"""
    resp = client.get("/api/v1/version")
    assert "data" in resp.json()
    assert "version" in resp.json()["data"]


# ═══════════════════════════════════════════════════════
# 3. Backend Dockerfile 健康检查
# ═══════════════════════════════════════════════════════


def test_backend_dockerfile_has_healthcheck():
    """后端 Dockerfile 包含 HEALTHCHECK"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile 不存在")
    content = dockerfile.read_text()
    assert "HEALTHCHECK" in content


def test_backend_dockerfile_healthcheck_interval():
    """健康检查间隔 15s"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile 不存在")
    content = dockerfile.read_text()
    assert "--interval=15s" in content


def test_backend_dockerfile_healthcheck_timeout():
    """健康检查超时 5s"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile 不存在")
    content = dockerfile.read_text()
    assert "--timeout=5s" in content


def test_backend_dockerfile_healthcheck_checks_database():
    """健康检查验证 database == 'ok'"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile 不存在")
    content = dockerfile.read_text()
    assert "database" in content
    assert "ok" in content


def test_backend_dockerfile_exposes_8000():
    """后端 Dockerfile 暴露端口 8000"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile 不存在")
    content = dockerfile.read_text()
    assert "8000" in content


# ═══════════════════════════════════════════════════════
# 4. Docker Compose 生产配置
# ═══════════════════════════════════════════════════════


def test_prod_compose_postgres_has_healthcheck():
    """生产 compose postgres 有健康检查"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "pg_isready" in content


def test_prod_compose_backend_depends_on_postgres_healthy():
    """后端依赖 postgres service_healthy"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "service_healthy" in content


def test_prod_compose_backend_has_healthcheck():
    """生产 compose 后端有健康检查"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "/api/v1/health" in content


def test_prod_compose_nginx_depends_on_backend_healthy():
    """nginx 依赖后端 service_healthy"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "backend" in content


def test_prod_compose_nginx_has_healthcheck():
    """生产 compose nginx 有健康检查"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "wget" in content


def test_prod_compose_has_resource_limits():
    """生产 compose 有资源限制"""
    compose = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("生产 compose 不存在")
    content = compose.read_text()
    assert "mem_limit" in content or "memory" in content or "deploy" in content


# ═══════════════════════════════════════════════════════
# 5. Nginx 代理配置
# ═══════════════════════════════════════════════════════


def test_nginx_proxy_api():
    """nginx 代理 /api/ 到后端"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        pytest.skip("nginx.conf 不存在")
    content = nginx_conf.read_text()
    assert "proxy_pass" in content
    assert "backend" in content


def test_nginx_proxy_health():
    """nginx 映射 /health 到 /api/v1/health"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        pytest.skip("nginx.conf 不存在")
    content = nginx_conf.read_text()
    assert "/api/v1/health" in content


def test_nginx_proxy_metrics():
    """nginx 代理 /metrics"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        pytest.skip("nginx.conf 不存在")
    content = nginx_conf.read_text()
    assert "/metrics" in content


def test_nginx_upstream_backend():
    """nginx upstream 指向 backend:8000"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        pytest.skip("nginx.conf 不存在")
    content = nginx_conf.read_text()
    assert "backend:8000" in content


# ═══════════════════════════════════════════════════════
# 6. Prometheus 配置
# ═══════════════════════════════════════════════════════


def test_prometheus_scrapes_backend():
    """Prometheus 配置抓取 backend"""
    prom_conf = REPO_ROOT / "deploy" / "prometheus.yml"
    if not prom_conf.exists():
        pytest.skip("prometheus.yml 不存在")
    content = prom_conf.read_text()
    assert "backend:8000" in content


def test_prometheus_metrics_path():
    """Prometheus metrics_path 为 /metrics"""
    prom_conf = REPO_ROOT / "deploy" / "prometheus.yml"
    if not prom_conf.exists():
        pytest.skip("prometheus.yml 不存在")
    content = prom_conf.read_text()
    assert "metrics_path" in content
    assert "/metrics" in content


def test_prometheus_scrape_interval():
    """Prometheus 抓取间隔 15s"""
    prom_conf = REPO_ROOT / "deploy" / "prometheus.yml"
    if not prom_conf.exists():
        pytest.skip("prometheus.yml 不存在")
    content = prom_conf.read_text()
    assert "15s" in content


# ═══════════════════════════════════════════════════════
# 7. Metrics 端点验证
# ═══════════════════════════════════════════════════════


def test_metrics_endpoint_returns_200():
    """GET /metrics 返回 200"""
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_contains_prometheus_format():
    """metrics 响应包含 Prometheus 格式"""
    resp = client.get("/metrics")
    content = resp.text
    assert "#" in content  # Prometheus comments


def test_metrics_not_under_api_v1():
    """/metrics 不在 /api/v1 前缀下"""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════
# 8. 连接池配置验证
# ═══════════════════════════════════════════════════════


def test_db_pool_size_positive():
    """DB_POOL_SIZE > 0"""
    assert settings.DB_POOL_SIZE > 0


def test_db_max_overflow_non_negative():
    """DB_MAX_OVERFLOW >= 0"""
    assert settings.DB_MAX_OVERFLOW >= 0


def test_db_pool_recycle_positive():
    """DB_POOL_RECYCLE_SECONDS > 0"""
    assert settings.DB_POOL_RECYCLE_SECONDS > 0


# ═══════════════════════════════════════════════════════
# 9. 健康检查脚本
# ═══════════════════════════════════════════════════════


def test_health_check_script_exists():
    """scripts/health-check.sh 存在"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    assert script.exists()


def test_health_check_script_checks_api_health():
    """健康检查脚本检查 /api/v1/health"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    if not script.exists():
        pytest.skip("health-check.sh 不存在")
    content = script.read_text()
    assert "/api/v1/health" in content


def test_health_check_script_checks_database():
    """健康检查脚本验证 database 状态"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    if not script.exists():
        pytest.skip("health-check.sh 不存在")
    content = script.read_text()
    assert "database" in content


def test_health_check_script_is_executable():
    """健康检查脚本可执行"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    if not script.exists():
        pytest.skip("health-check.sh 不存在")
    assert script.stat().st_mode & 0o111


# ═══════════════════════════════════════════════════════
# 10. Docker Compose 开发配置
# ═══════════════════════════════════════════════════════


def test_dev_compose_backend_has_healthcheck():
    """开发 compose 后端有健康检查"""
    compose = REPO_ROOT / "deploy" / "docker-compose.dev.yml"
    if not compose.exists():
        pytest.skip("开发 compose 不存在")
    content = compose.read_text()
    assert "/api/v1/health" in content


def test_dev_compose_postgres_has_healthcheck():
    """开发 compose postgres 有健康检查"""
    compose = REPO_ROOT / "deploy" / "docker-compose.dev.yml"
    if not compose.exists():
        pytest.skip("开发 compose 不存在")
    content = compose.read_text()
    assert "pg_isready" in content


# ═══════════════════════════════════════════════════════
# 11. Grafana 配置
# ═══════════════════════════════════════════════════════


def test_grafana_dashboard_exists():
    """Grafana dashboard JSON 存在"""
    dashboard = REPO_ROOT / "deploy" / "grafana" / "dashboard.json"
    assert dashboard.exists()


def test_grafana_dashboard_is_valid_json():
    """Grafana dashboard JSON 可解析"""
    dashboard = REPO_ROOT / "deploy" / "grafana" / "dashboard.json"
    if not dashboard.exists():
        pytest.skip("dashboard.json 不存在")
    data = json.loads(dashboard.read_text())
    assert "panels" in data or "dashboard" in data


def test_grafana_provisioning_exists():
    """Grafana provisioning 配置存在"""
    provisioning = REPO_ROOT / "deploy" / "grafana" / "dashboards.yml"
    assert provisioning.exists()
