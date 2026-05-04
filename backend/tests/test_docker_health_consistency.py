"""部署体验：Docker 健康检查配置一致性测试
验证 Dockerfile HEALTHCHECK、docker-compose health check 与 /health 端点对齐"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
client = TestClient(app)

DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
DEV_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.dev.yml"
PROD_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.prod.yml"


class TestDockerfileHealthcheck:
    """Dockerfile HEALTHCHECK 配置"""

    def test_dockerfile_exists(self):
        assert DOCKERFILE.is_file()

    def test_dockerfile_has_healthcheck(self):
        content = DOCKERFILE.read_text()
        assert "HEALTHCHECK" in content

    def test_dockerfile_healthcheck_uses_health_endpoint(self):
        content = DOCKERFILE.read_text()
        assert "/api/v1/health" in content

    def test_dockerfile_healthcheck_checks_database(self):
        content = DOCKERFILE.read_text()
        assert "database" in content
        assert "ok" in content

    def test_dockerfile_healthcheck_params(self):
        content = DOCKERFILE.read_text()
        assert "interval=15s" in content
        assert "timeout=5s" in content
        assert "retries=3" in content

    def test_dockerfile_exposes_8000(self):
        content = DOCKERFILE.read_text()
        assert "8000" in content


class TestDevComposeHealthcheck:
    """docker-compose.dev.yml 健康检查"""

    def test_dev_compose_exists(self):
        assert DEV_COMPOSE.is_file()

    def test_dev_backend_healthcheck(self):
        content = DEV_COMPOSE.read_text()
        assert "/api/v1/health" in content
        assert "15s" in content  # interval

    def test_dev_postgres_healthcheck(self):
        content = DEV_COMPOSE.read_text()
        assert "pg_isready" in content


class TestProdComposeHealthcheck:
    """docker-compose.prod.yml 健康检查"""

    def test_prod_compose_exists(self):
        assert PROD_COMPOSE.is_file()

    def test_prod_backend_healthcheck(self):
        content = PROD_COMPOSE.read_text()
        assert "/api/v1/health" in content

    def test_prod_backend_checks_database(self):
        content = PROD_COMPOSE.read_text()
        # prod 版本检查 database == ok
        assert "database" in content

    def test_prod_postgres_healthcheck(self):
        content = PROD_COMPOSE.read_text()
        assert "pg_isready" in content

    def test_prod_nginx_healthcheck(self):
        content = PROD_COMPOSE.read_text()
        assert "wget" in content or "curl" in content

    def test_prod_backend_start_period_longer(self):
        """生产环境 start_period >= 30s"""
        content = PROD_COMPOSE.read_text()
        # 提取 start_period
        assert "30s" in content


class TestHealthEndpointMatchesDocker:
    """/health 端点与 Docker 配置对齐"""

    def test_health_endpoint_returns_200(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_has_database_field(self):
        """Dockerfile HEALTHCHECK 检查 data.database == ok"""
        resp = client.get("/api/v1/health")
        data = resp.json()["data"]
        assert "database" in data
        assert data["database"] in ("ok", "error")

    def test_health_response_parseable_by_docker_check(self):
        """Dockerfile 中的 python 代码能正确解析响应"""
        resp = client.get("/api/v1/health")
        body = resp.json()
        # 模拟 Dockerfile 中的检查逻辑
        d = body.get("data", {})
        # 当 database 不是 ok 时，Dockerfile 会报错（正确行为）
        assert "database" in d

    def test_health_endpoint_path_matches_dockerfile(self):
        """端点路径与 Dockerfile 一致"""
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 503)

    def test_dockerignore_excludes_tests(self):
        """dockerignore 排除测试文件"""
        dockerignore = REPO_ROOT / "backend" / ".dockerignore"
        if dockerignore.is_file():
            content = dockerignore.read_text()
            assert "test" in content or "tests" in content
