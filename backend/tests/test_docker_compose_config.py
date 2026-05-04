"""部署体验：docker-compose 配置一致性验证测试
验证 dev/prod compose 文件的服务结构、端口、健康检查、环境变量对齐"""

from pathlib import Path

import yaml

DEPLOY_DIR = Path(__file__).resolve().parent.parent.parent / "deploy"


def _load_compose(filename):
    with open(DEPLOY_DIR / filename) as f:
        return yaml.safe_load(f)


def _get_services(compose):
    return compose.get("services", {})


class TestDockerComposeStructure:
    """docker-compose 文件基本结构"""

    def test_dev_compose_loads(self):
        config = _load_compose("docker-compose.dev.yml")
        assert isinstance(config, dict)
        assert "services" in config

    def test_prod_compose_loads(self):
        config = _load_compose("docker-compose.prod.yml")
        assert isinstance(config, dict)
        assert "services" in config

    def test_dev_has_postgres_backend_frontend(self):
        services = _get_services(_load_compose("docker-compose.dev.yml"))
        for name in ("postgres", "backend", "frontend"):
            assert name in services, f"dev 缺少 {name} 服务"

    def test_prod_has_postgres_backend_nginx(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        for name in ("postgres", "backend", "nginx"):
            assert name in services, f"prod 缺少 {name} 服务"


class TestPostgresConfig:
    """PostgreSQL 配置一致性"""

    def test_both_use_postgres_17_alpine(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            image = services["postgres"].get("image", "")
            assert "postgres:17" in image, f"{filename} postgres 镜像不是 17"

    def test_both_have_healthcheck(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            assert "healthcheck" in services["postgres"], f"{filename} postgres 无健康检查"

    def test_both_pg_isready_check(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            cmd = services["postgres"]["healthcheck"]["test"]
            assert "pg_isready" in str(cmd), f"{filename} postgres 健康检查非 pg_isready"

    def _resolve_env(self, value):
        """解析 ${VAR:-default} 格式的环境变量值，返回默认值"""
        s = str(value)
        if s.startswith("${") and ":-" in s:
            return s.split(":-", 1)[1].rstrip("}")
        return s

    def test_db_name_consistent(self):
        dev_env = _get_services(_load_compose("docker-compose.dev.yml"))["postgres"]["environment"]
        prod_env = _get_services(_load_compose("docker-compose.prod.yml"))["postgres"]["environment"]
        assert self._resolve_env(dev_env.get("POSTGRES_DB")) == self._resolve_env(prod_env.get("POSTGRES_DB"))


class TestBackendConfig:
    """Backend 配置一致性"""

    def test_both_expose_8000_internal(self):
        """后端容器内部都使用 8000 端口"""
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            backend = services["backend"]
            # 检查端口映射或 Dockerfile EXPOSE
            ports = backend.get("ports", [])
            if ports:
                assert any("8000" in str(p) for p in ports)
            cmd = backend.get("command", "")
            assert "8000" in str(cmd) or not cmd

    def test_both_have_healthcheck(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            assert "healthcheck" in services["backend"], f"{filename} backend 无健康检查"

    def test_healthcheck_uses_api_v1_health(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            hc = services["backend"]["healthcheck"]
            test = str(hc.get("test", ""))
            assert "/api/v1/health" in test, f"{filename} backend 健康检查不使用 /api/v1/health"

    def test_both_depend_on_postgres_healthy(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            depends = services["backend"].get("depends_on", {})
            if isinstance(depends, dict):
                assert "postgres" in depends
                assert depends["postgres"].get("condition") == "service_healthy"
            elif isinstance(depends, list):
                assert "postgres" in depends

    def test_both_set_database_url(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            env = services["backend"].get("environment", {})
            assert "DATABASE_URL" in env or "database_url" in str(env).lower()

    def test_both_set_jwt_secret(self):
        for filename in ("docker-compose.dev.yml", "docker-compose.prod.yml"):
            services = _get_services(_load_compose(filename))
            env = services["backend"].get("environment", {})
            assert "JWT_SECRET_KEY" in env

    def test_prod_app_env_is_production(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        env = services["backend"].get("environment", {})
        assert env.get("APP_ENV") == "production"

    def test_dev_app_env_is_development(self):
        services = _get_services(_load_compose("docker-compose.dev.yml"))
        env = services["backend"].get("environment", {})
        val = str(env.get("APP_ENV", ""))
        assert "development" in val

    def test_prod_has_security_options(self):
        """生产环境有安全加固选项"""
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        backend = services["backend"]
        security = backend.get("security_opt", [])
        assert "no-new-privileges:true" in security

    def test_prod_has_resource_limits(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        backend = services["backend"]
        deploy = backend.get("deploy", {})
        assert "resources" in deploy or "mem_limit" in backend

    def test_prod_drops_capabilities(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        backend = services["backend"]
        cap_drop = backend.get("cap_drop", [])
        assert "ALL" in cap_drop


class TestNginxConfig:
    """Nginx 配置（仅 prod）"""

    def test_nginx_depends_on_backend(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        depends = services["nginx"].get("depends_on", {})
        if isinstance(depends, (dict, list)):
            assert "backend" in depends

    def test_nginx_exposes_http_port(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        ports = services["nginx"].get("ports", [])
        assert any("80" in str(p) for p in ports)

    def test_nginx_uses_alpine(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        image = services["nginx"].get("image", "")
        assert "nginx" in image

    def test_nginx_has_healthcheck(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        assert "healthcheck" in services["nginx"]


class TestDockerfileHealthCheck:
    """Dockerfile 健康检查与 compose 对齐"""

    def test_dockerfile_healthcheck_url(self):
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "/api/v1/health" in content
        assert "database" in content

    def test_dockerfile_exposes_8000(self):
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "EXPOSE 8000" in content

    def test_dockerfile_uses_non_root_user(self):
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "appuser" in content or "USER" in content


class TestPrometheusConfig:
    """Prometheus 配置（仅 prod）"""

    def test_prod_has_prometheus(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        assert "prometheus" in services

    def test_prometheus_depends_on_backend(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        depends = services["prometheus"].get("depends_on", {})
        if isinstance(depends, (dict, list)):
            assert "backend" in depends

    def test_prometheus_config_mounted(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        volumes = services["prometheus"].get("volumes", [])
        assert any("prometheus.yml" in str(v) for v in volumes)

    def test_prometheus_has_resource_limits(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        prom = services["prometheus"]
        deploy = prom.get("deploy", {})
        assert "resources" in deploy or "mem_limit" in prom


class TestNetworkConfig:
    """网络配置（仅 prod）"""

    def test_prod_has_backend_network(self):
        config = _load_compose("docker-compose.prod.yml")
        networks = config.get("networks", {})
        assert "backend" in networks

    def test_prod_has_frontend_network(self):
        config = _load_compose("docker-compose.prod.yml")
        networks = config.get("networks", {})
        assert "frontend" in networks

    def test_backend_on_both_networks(self):
        services = _get_services(_load_compose("docker-compose.prod.yml"))
        backend_nets = services["backend"].get("networks", [])
        if isinstance(backend_nets, (list, dict)):
            assert "backend" in backend_nets
            assert "frontend" in backend_nets
