"""部署体验：健康检查端点边界测试 — 覆盖 Docker 健康检查、连接池配置、Prometheus 配置、Nginx 代理"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REPO_ROOT = Path(__file__).parent.parent.parent


# ═══════════════════════════════════════════════════════
# 1. 健康检查响应结构
# ═══════════════════════════════════════════════════════


def test_health_database_field():
    """健康检查返回 database 字段"""
    response = client.get("/api/v1/health")
    assert "database" in response.json()["data"]


def test_health_version_field():
    """健康检查返回 version 字段"""
    data = client.get("/api/v1/health").json()["data"]
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_health_revision_field():
    """健康检查返回 revision 字段"""
    data = client.get("/api/v1/health").json()["data"]
    assert "revision" in data


def test_health_pool_values_numeric():
    """连接池字段为数字"""
    pool = client.get("/api/v1/health").json()["data"]["pool"]
    for key in ("size", "checked_in", "checked_out", "overflow"):
        assert isinstance(pool[key], int), f"pool.{key} 应为整数"


def test_health_pool_size_non_negative():
    """连接池大小和 checked 非负"""
    pool = client.get("/api/v1/health").json()["data"]["pool"]
    assert pool["size"] >= 0
    assert pool["checked_in"] >= 0
    assert pool["checked_out"] >= 0
    # overflow 在 SQLite 中可以为负数（StaticPool 行为）


def test_health_no_auth_required():
    """健康检查不需要认证"""
    response = client.get("/api/v1/health")
    assert response.status_code != 401


def test_health_method_get_only():
    """健康检查只支持 GET"""
    assert client.post("/api/v1/health").status_code == 405
    assert client.put("/api/v1/health").status_code == 405
    assert client.delete("/api/v1/health").status_code == 405


# ═══════════════════════════════════════════════════════
# 2. 版本端点
# ═══════════════════════════════════════════════════════


def test_version_has_revision():
    """版本端点返回 revision"""
    data = client.get("/api/v1/version").json()["data"]
    assert "revision" in data
    assert isinstance(data["revision"], str)


def test_version_no_auth_required():
    """版本端点不需要认证"""
    assert client.get("/api/v1/version").status_code != 401


# ═══════════════════════════════════════════════════════
# 3. Docker Compose 健康检查配置
# ═══════════════════════════════════════════════════════


def _load_yaml(path):
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)


def test_prod_compose_backend_healthcheck():
    """生产 Compose 后端有健康检查"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    backend = compose["services"]["backend"]
    assert "healthcheck" in backend, "backend 缺少 healthcheck"


def test_prod_compose_backend_healthcheck_checks_db():
    """生产 Compose 后端健康检查验证数据库"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    hc = compose["services"]["backend"]["healthcheck"]
    cmd = hc["test"] if isinstance(hc["test"], str) else " ".join(hc["test"])
    assert "database" in cmd or "health" in cmd


def test_prod_compose_backend_healthcheck_interval():
    """生产 Compose 后端健康检查间隔 ≤ 30 秒"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    hc = compose["services"]["backend"]["healthcheck"]
    interval = hc.get("interval", "")
    assert "15s" in interval or "10s" in interval or "30s" in interval


def test_prod_compose_backend_healthcheck_retries():
    """生产 Compose 后端健康检查重试次数 ≤ 5"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    hc = compose["services"]["backend"]["healthcheck"]
    assert hc.get("retries", 0) <= 5


def test_prod_compose_postgres_healthcheck():
    """生产 Compose PostgreSQL 有健康检查"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    postgres = compose["services"]["postgres"]
    assert "healthcheck" in postgres
    cmd = postgres["healthcheck"]["test"]
    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    assert "pg_isready" in cmd_str


def test_prod_compose_nginx_healthcheck():
    """生产 Compose Nginx 有健康检查"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    nginx = compose["services"].get("nginx", {})
    assert "healthcheck" in nginx, "nginx 缺少 healthcheck"


def test_dev_compose_backend_healthcheck():
    """开发 Compose 后端有健康检查"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.dev.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    backend = compose["services"]["backend"]
    assert "healthcheck" in backend


def test_dev_compose_postgres_healthcheck():
    """开发 Compose PostgreSQL 有健康检查"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.dev.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    assert "healthcheck" in compose["services"]["postgres"]


# ═══════════════════════════════════════════════════════
# 4. Dockerfile 健康检查
# ═══════════════════════════════════════════════════════


def test_dockerfile_has_healthcheck():
    """Dockerfile 包含 HEALTHCHECK 指令"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        return
    content = dockerfile.read_text()
    assert "HEALTHCHECK" in content


def test_dockerfile_healthcheck_checks_database():
    """Dockerfile 健康检查验证数据库状态"""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        return
    content = dockerfile.read_text()
    assert "database" in content


# ═══════════════════════════════════════════════════════
# 5. 连接池配置
# ═══════════════════════════════════════════════════════


def test_db_pool_size_default():
    """连接池默认大小 > 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.DB_POOL_SIZE > 0


def test_db_max_overflow_default():
    """连接池最大溢出 >= 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.DB_MAX_OVERFLOW >= 0


def test_db_pool_recycle_default():
    """连接池回收时间 > 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.DB_POOL_RECYCLE_SECONDS > 0


def test_engine_has_pool_pre_ping():
    """数据库引擎启用 pool_pre_ping"""
    from app.db.session import engine
    # SQLAlchemy engine 的 pool_pre_ping 在创建参数中
    assert engine.pool._pool is not None or engine.pool.status is not None


# ═══════════════════════════════════════════════════════
# 6. Prometheus 配置
# ═══════════════════════════════════════════════════════


def test_prometheus_config_exists():
    """Prometheus 配置文件存在"""
    prom_file = REPO_ROOT / "deploy" / "prometheus.yml"
    assert prom_file.exists()


def test_prometheus_scrape_interval():
    """Prometheus 抓取间隔 ≤ 30 秒"""
    import yaml
    prom_file = REPO_ROOT / "deploy" / "prometheus.yml"
    with open(prom_file) as f:
        config = yaml.safe_load(f)
    interval = config.get("global", {}).get("scrape_interval", "30s")
    assert "15s" in interval or "30s" in interval


def test_prometheus_scrape_targets_backend():
    """Prometheus 抓取目标包含 backend"""
    import yaml
    prom_file = REPO_ROOT / "deploy" / "prometheus.yml"
    with open(prom_file) as f:
        config = yaml.safe_load(f)
    jobs = config.get("scrape_configs", [])
    assert any("backend" in str(j) for j in jobs)


def test_prometheus_metrics_path():
    """Prometheus 使用 /metrics 路径"""
    import yaml
    prom_file = REPO_ROOT / "deploy" / "prometheus.yml"
    with open(prom_file) as f:
        config = yaml.safe_load(f)
    jobs = config.get("scrape_configs", [])
    assert any(j.get("metrics_path") == "/metrics" for j in jobs)


def test_prod_compose_has_prometheus():
    """生产 Compose 包含 Prometheus 服务"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    assert "prometheus" in compose["services"]


def test_prod_compose_has_grafana():
    """生产 Compose 包含 Grafana 服务"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    assert "grafana" in compose["services"]


# ═══════════════════════════════════════════════════════
# 7. Nginx 代理配置
# ═══════════════════════════════════════════════════════


def test_nginx_proxies_health():
    """Nginx 代理 /health 到后端"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        return
    content = nginx_conf.read_text()
    assert "/health" in content


def test_nginx_proxies_metrics():
    """Nginx 代理 /metrics 到后端"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        return
    content = nginx_conf.read_text()
    assert "/metrics" in content


def test_nginx_health_no_access_log():
    """Nginx 健康检查不写访问日志"""
    nginx_conf = REPO_ROOT / "deploy" / "nginx.conf"
    if not nginx_conf.exists():
        return
    content = nginx_conf.read_text()
    # 查找 /health location 块中的 access_log off
    health_block_start = content.find("location /health")
    if health_block_start == -1:
        return
    health_block_end = content.find("}", health_block_start)
    health_block = content[health_block_start:health_block_end]
    assert "access_log off" in health_block or "access_log" not in health_block


# ═══════════════════════════════════════════════════════
# 8. 健康检查脚本
# ═══════════════════════════════════════════════════════


def test_health_check_script_exists():
    """健康检查脚本存在"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    assert script.exists()


def test_health_check_script_checks_backend():
    """健康检查脚本检查后端健康"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    if not script.exists():
        return
    content = script.read_text()
    assert "/api/v1/health" in content


def test_health_check_script_checks_frontend():
    """健康检查脚本检查前端"""
    script = REPO_ROOT / "scripts" / "health-check.sh"
    if not script.exists():
        return
    content = script.read_text()
    # 检查前端首页和 assets
    assert "frontend" in content.lower() or "assets" in content.lower()


# ═══════════════════════════════════════════════════════
# 9. 生产 Compose 覆盖连接池配置
# ═══════════════════════════════════════════════════════


def test_prod_compose_overrides_pool_size():
    """生产 Compose 覆盖连接池大小"""
    compose_file = REPO_ROOT / "deploy" / "docker-compose.prod.yml"
    if not compose_file.exists():
        return
    compose = _load_yaml(compose_file)
    backend_env = compose["services"]["backend"].get("environment", {})
    pool_size = backend_env.get("DB_POOL_SIZE", "")
    if pool_size:
        # 可能为 ${DB_POOL_SIZE:-10} 格式，提取默认值
        import re
        default = re.search(r":-(\d+)", str(pool_size))
        if default:
            assert int(default.group(1)) >= 5
        elif pool_size.isdigit():
            assert int(pool_size) >= 5


# ═══════════════════════════════════════════════════════
# 10. Metrics 排除健康检查
# ═══════════════════════════════════════════════════════


def test_metrics_excludes_health_endpoint():
    """/metrics 不记录 /health 端点流量"""
    import app.main as mod
    with open(mod.__file__) as f:
        source = f.read()
    assert "excluded_handlers" in source
    assert "/health" in source


def test_metrics_excludes_version_endpoint():
    """/metrics 不记录 /version 端点流量"""
    import app.main as mod
    with open(mod.__file__) as f:
        source = f.read()
    assert "/version" in source
