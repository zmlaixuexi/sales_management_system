"""部署体验：前端生产环境 Docker 镜像优化验证测试
覆盖 Dockerfile 多阶段构建、dev Dockerfile 配置、
docker-compose prod 前端服务、nginx 集成、构建脚本一致性"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DOCKERFILE = ROOT / "frontend" / "Dockerfile"
FRONTEND_DOCKERFILE_DEV = ROOT / "frontend" / "Dockerfile.dev"
PROD_COMPOSE = ROOT / "deploy" / "docker-compose.prod.yml"
DEV_COMPOSE = ROOT / "deploy" / "docker-compose.dev.yml"
NGINX_CONF = ROOT / "deploy" / "nginx.conf"
PACKAGE_JSON = ROOT / "frontend" / "package.json"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. Dockerfile 多阶段构建验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFrontendDockerfileBuild:
    """验证前端生产 Dockerfile 多阶段构建"""

    def test_uses_multi_stage_build(self):
        source = _read(FRONTEND_DOCKERFILE)
        stages = source.count("FROM ")
        assert stages >= 2, "应有至少 2 个构建阶段"

    def test_build_stage_uses_node_alpine(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "node:" in source
        assert "alpine" in source

    def test_uses_npm_ci_for_deterministic_build(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "npm ci" in source

    def test_build_uses_npm_run_build(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "npm run build" in source

    def test_output_stage_is_minimal_alpine(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "alpine" in source
        assert "COPY --from=build" in source
        assert "/app/dist" in source


# ═══════════════════════════════════════════════════════════
# 2. Dockerfile 构建参数验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFrontendBuildArgs:
    """验证前端 Dockerfile 构建参数"""

    def test_accepts_vite_api_base_url_arg(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "ARG VITE_API_BASE_URL" in source

    def test_sets_vite_env_from_arg(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "ENV VITE_API_BASE_URL=$VITE_API_BASE_URL" in source

    def test_copies_package_files_first(self):
        source = _read(FRONTEND_DOCKERFILE)
        lines = source.split("\n")
        copy_pkg = next(
            (i for i, line in enumerate(lines) if "package.json package-lock.json" in line),
            -1,
        )
        npm_ci = next((i for i, line in enumerate(lines) if "npm ci" in line), -1)
        assert copy_pkg >= 0 and npm_ci >= 0
        assert copy_pkg < npm_ci, "应先 COPY package 文件再 npm ci"

    def test_output_copies_dist_to_nginx_path(self):
        source = _read(FRONTEND_DOCKERFILE)
        assert "/usr/share/nginx/html/" in source

    def test_output_stage_has_no_dev_dependencies(self):
        source = _read(FRONTEND_DOCKERFILE)
        # 找最后一个 FROM 行作为输出阶段
        lines = source.split("\n")
        last_from = max(i for i, line in enumerate(lines) if line.startswith("FROM"))
        stage2 = "\n".join(lines[last_from:])
        assert "npm install" not in stage2
        assert "npm ci" not in stage2


# ═══════════════════════════════════════════════════════════
# 3. dev Dockerfile 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFrontendDevDockerfile:
    """验证前端开发 Dockerfile"""

    def test_uses_node_alpine(self):
        source = _read(FRONTEND_DOCKERFILE_DEV)
        assert "node:" in source
        assert "alpine" in source

    def test_uses_npm_install_not_ci(self):
        source = _read(FRONTEND_DOCKERFILE_DEV)
        assert "npm install" in source

    def test_exposes_dev_port(self):
        source = _read(FRONTEND_DOCKERFILE_DEV)
        assert "EXPOSE" in source
        assert "5173" in source

    def test_runs_dev_server(self):
        source = _read(FRONTEND_DOCKERFILE_DEV)
        assert '"npm"' in source
        assert '"run"' in source
        assert '"dev"' in source
        assert '"--host"' in source

    def test_is_single_stage(self):
        source = _read(FRONTEND_DOCKERFILE_DEV)
        from_count = source.count("FROM ")
        assert from_count == 1, "开发 Dockerfile 应为单阶段"


# ═══════════════════════════════════════════════════════════
# 4. docker-compose prod 前端服务验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestProdComposeFrontend:
    """验证 docker-compose.prod.yml 前端服务配置"""

    def test_has_frontend_build_service(self):
        source = _read(PROD_COMPOSE)
        assert "frontend-build:" in source

    def test_frontend_build_uses_dockerfile(self):
        source = _read(PROD_COMPOSE)
        assert "dockerfile: Dockerfile" in source
        assert "context: ../frontend" in source

    def test_frontend_build_passes_vite_arg(self):
        source = _read(PROD_COMPOSE)
        assert "VITE_API_BASE_URL: /api/v1" in source or "VITE_API_BASE_URL" in source

    def test_has_nginx_service(self):
        source = _read(PROD_COMPOSE)
        assert "nginx:" in source
        assert "nginx:" in source

    def test_nginx_uses_frontend_dist_volume(self):
        source = _read(PROD_COMPOSE)
        assert "frontend_dist:" in source
        assert "/usr/share/nginx/html" in source


# ═══════════════════════════════════════════════════════════
# 5. 构建脚本一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBuildScriptConsistency:
    """验证构建脚本与 Dockerfile 一致"""

    def test_package_json_build_command(self):
        source = _read(PACKAGE_JSON)
        assert '"build":' in source
        assert "tsc" in source
        assert "vite build" in source

    def test_package_json_has_dev_script(self):
        source = _read(PACKAGE_JSON)
        assert '"dev":' in source
        assert "vite" in source

    def test_package_json_has_test_script(self):
        source = _read(PACKAGE_JSON)
        assert '"test":' in source
        assert "vitest" in source

    def test_package_json_has_lint_script(self):
        source = _read(PACKAGE_JSON)
        assert '"lint":' in source
        assert "eslint" in source

    def test_dockerfile_build_matches_package_build(self):
        dockerfile = _read(FRONTEND_DOCKERFILE)
        package = _read(PACKAGE_JSON)
        assert "npm run build" in dockerfile
        assert '"build":' in package
