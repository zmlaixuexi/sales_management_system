"""Docker Compose 配置验证测试 — 静态分析部署配置文件"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy"


def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"文件不存在: {path}"
    with open(path) as f:
        return yaml.safe_load(f)


# ═══════════════════════════════════════════════════════
# 1. 文件完整性
# ═══════════════════════════════════════════════════════


def test_deploy_directory_exists():
    """deploy 目录存在"""
    assert DEPLOY_DIR.is_dir()


def test_prod_compose_file_exists():
    """docker-compose.prod.yml 存在"""
    assert (DEPLOY_DIR / "docker-compose.prod.yml").is_file()


def test_dev_compose_file_exists():
    """docker-compose.dev.yml 存在"""
    assert (DEPLOY_DIR / "docker-compose.dev.yml").is_file()


def test_nginx_conf_exists():
    """nginx.conf 存在"""
    assert (DEPLOY_DIR / "nginx.conf").is_file()


def test_backend_dockerfile_exists():
    """后端 Dockerfile 存在"""
    assert (REPO_ROOT / "backend" / "Dockerfile").is_file()


def test_frontend_dockerfile_exists():
    """前端 Dockerfile 存在"""
    assert (REPO_ROOT / "frontend" / "Dockerfile").is_file()


def test_frontend_dockerfile_dev_exists():
    """前端 Dockerfile.dev 存在"""
    assert (REPO_ROOT / "frontend" / "Dockerfile.dev").is_file()


def test_backend_dockerignore_exists():
    """后端 .dockerignore 存在"""
    assert (REPO_ROOT / "backend" / ".dockerignore").is_file()


def test_frontend_dockerignore_exists():
    """前端 .dockerignore 存在"""
    assert (REPO_ROOT / "frontend" / ".dockerignore").is_file()


# ═══════════════════════════════════════════════════════
# 2. docker-compose.prod.yml 结构
# ═══════════════════════════════════════════════════════


def test_prod_compose_valid_yaml():
    """docker-compose.prod.yml 是有效 YAML"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    assert "services" in data


def test_prod_has_required_services():
    """生产 Compose 包含必要服务"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    for service in ("postgres", "backend", "nginx", "frontend-build"):
        assert service in data["services"], f"缺少 {service} 服务"


def test_prod_has_monitoring_services():
    """生产 Compose 包含监控服务"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    assert "prometheus" in data["services"]
    assert "grafana" in data["services"]


def test_prod_postgres_has_healthcheck():
    """PostgreSQL 服务有健康检查"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    pg = data["services"]["postgres"]
    assert "healthcheck" in pg


def test_prod_backend_depends_on_postgres():
    """后端依赖 PostgreSQL"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    assert "depends_on" in backend
    assert "postgres" in backend["depends_on"]


def test_prod_backend_runs_alembic():
    """后端启动命令包含 alembic upgrade head"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    command = backend.get("command", "")
    assert "alembic upgrade head" in command


def test_prod_backend_has_security_options():
    """后端容器有安全加固选项"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    assert "security_opt" in backend
    assert "no-new-privileges:true" in backend["security_opt"]
    assert "cap_drop" in backend
    assert "ALL" in backend["cap_drop"]


def test_prod_backend_has_resource_limits():
    """后端容器有资源限制"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    limits = backend.get("deploy", {}).get("resources", {}).get("limits", {})
    assert "memory" in limits
    assert "cpus" in limits


def test_prod_backend_has_logging_config():
    """后端容器有日志配置"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    assert "logging" in backend
    assert backend["logging"]["driver"] == "json-file"
    assert "max-size" in backend["logging"]["options"]


def test_prod_backend_requires_jwt_secret():
    """后端环境变量要求设置 JWT_SECRET_KEY"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    env = backend.get("environment", {})
    jwt_key = env.get("JWT_SECRET_KEY", "")
    assert "?请设置" in jwt_key or ":-" in jwt_key


def test_prod_backend_has_app_env_production():
    """后端 APP_ENV 设置为 production"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    backend = data["services"]["backend"]
    env = backend.get("environment", {})
    assert env.get("APP_ENV") == "production"


def test_prod_nginx_depends_on_backend():
    """Nginx 依赖后端"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    nginx = data["services"]["nginx"]
    assert "depends_on" in nginx
    assert "backend" in nginx["depends_on"]


def test_prod_nginx_has_security_options():
    """Nginx 容器有安全加固选项"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    nginx = data["services"]["nginx"]
    assert "security_opt" in nginx
    assert "cap_drop" in nginx


def test_prod_has_networks():
    """生产 Compose 定义了网络"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    assert "networks" in data
    for net in ("backend", "frontend", "monitoring"):
        assert net in data["networks"], f"缺少 {net} 网络"


def test_prod_has_volumes():
    """生产 Compose 定义了数据卷"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    assert "volumes" in data
    for vol in ("postgres_data", "uploads_data", "frontend_dist"):
        assert vol in data["volumes"], f"缺少 {vol} 数据卷"


def test_prod_postgres_no_exposed_ports():
    """PostgreSQL 不对外暴露端口"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    pg = data["services"]["postgres"]
    assert "ports" not in pg


def test_prod_grafana_in_monitoring_profile():
    """Grafana 在 monitoring profile 中"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.prod.yml")
    grafana = data["services"]["grafana"]
    assert "profiles" in grafana
    assert "monitoring" in grafana["profiles"]


# ═══════════════════════════════════════════════════════
# 3. docker-compose.dev.yml 结构
# ═══════════════════════════════════════════════════════


def test_dev_compose_valid_yaml():
    """docker-compose.dev.yml 是有效 YAML"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    assert "services" in data


def test_dev_has_required_services():
    """开发 Compose 包含必要服务"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    for service in ("postgres", "backend", "frontend"):
        assert service in data["services"], f"缺少 {service} 服务"


def test_dev_postgres_has_healthcheck():
    """开发 PostgreSQL 有健康检查"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    pg = data["services"]["postgres"]
    assert "healthcheck" in pg


def test_dev_backend_depends_on_postgres():
    """开发后端依赖 PostgreSQL"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    backend = data["services"]["backend"]
    assert "depends_on" in backend
    assert "postgres" in backend["depends_on"]


def test_dev_backend_mounts_source():
    """开发后端挂载源代码（热重载）"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    backend = data["services"]["backend"]
    volumes = backend.get("volumes", [])
    has_source_mount = any("../backend/app" in str(v) or "/app/app" in str(v) for v in volumes)
    assert has_source_mount, "开发模式应挂载源代码"


def test_dev_postgres_exposes_port():
    """开发 PostgreSQL 暴露端口"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    pg = data["services"]["postgres"]
    assert "ports" in pg


def test_dev_backend_env_is_development():
    """开发后端 APP_ENV 为 development"""
    data = _load_yaml(DEPLOY_DIR / "docker-compose.dev.yml")
    backend = data["services"]["backend"]
    env = backend.get("environment", {})
    assert "development" in str(env.get("APP_ENV", ""))


# ═══════════════════════════════════════════════════════
# 4. Nginx 配置
# ═══════════════════════════════════════════════════════


def test_nginx_conf_readable():
    """nginx.conf 可读取"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert len(content) > 0


def test_nginx_has_upstream_backend():
    """nginx.conf 定义 backend upstream"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "upstream backend" in content


def test_nginx_has_api_proxy():
    """nginx.conf 代理 /api/ 路径"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "location /api/" in content
    assert "proxy_pass http://backend" in content


def test_nginx_has_uploads_proxy():
    """nginx.conf 代理 /uploads/ 路径"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "location /uploads/" in content


def test_nginx_has_health_endpoint():
    """nginx.conf 有 /health 代理"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "location /health" in content


def test_nginx_has_metrics_endpoint():
    """nginx.conf 有 /metrics 代理"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "location /metrics" in content


def test_nginx_has_security_headers():
    """nginx.conf 包含安全响应头"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    for header in ("X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"):
        assert header in content, f"缺少安全头 {header}"


def test_nginx_server_tokens_off():
    """nginx.conf 隐藏版本号"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "server_tokens off" in content


def test_nginx_has_gzip():
    """nginx.conf 启用 gzip 压缩"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "gzip on" in content


def test_nginx_spa_fallback():
    """nginx.conf 前端 SPA 回退"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "try_files $uri $uri/ /index.html" in content


def test_nginx_hides_hidden_files():
    """nginx.conf 禁止访问隐藏文件"""
    content = (DEPLOY_DIR / "nginx.conf").read_text()
    assert "location ~ /\\." in content
    assert "deny all" in content


# ═══════════════════════════════════════════════════════
# 5. Dockerfile 验证
# ═══════════════════════════════════════════════════════


def test_backend_dockerfile_multi_stage():
    """后端 Dockerfile 使用多阶段构建"""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    stages = content.count("FROM ")
    assert stages >= 2, "应使用多阶段构建"


def test_backend_dockerfile_non_root_user():
    """后端 Dockerfile 使用非 root 用户"""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "USER appuser" in content or "USER " in content


def test_backend_dockerfile_has_healthcheck():
    """后端 Dockerfile 有健康检查"""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "HEALTHCHECK" in content


def test_backend_dockerfile_exposes_port():
    """后端 Dockerfile 暴露端口"""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "EXPOSE" in content


def test_backend_dockerfile_uses_slim_image():
    """后端 Dockerfile 使用 slim 镜像"""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "slim" in content.lower() or "alpine" in content.lower()


def test_frontend_dockerfile_multi_stage():
    """前端 Dockerfile 使用多阶段构建"""
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    stages = content.count("FROM ")
    assert stages >= 2


def test_frontend_dockerfile_has_build_arg():
    """前端 Dockerfile 有 VITE_API_BASE_URL 构建参数"""
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "VITE_API_BASE_URL" in content


def test_frontend_dockerfile_uses_alpine():
    """前端 Dockerfile 最终阶段使用轻量镜像"""
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    lines = content.strip().split("\n")
    from_lines = [line for line in lines if line.strip().startswith("FROM")]
    assert len(from_lines) >= 2
    last_from = from_lines[-1].lower()
    assert "alpine" in last_from
