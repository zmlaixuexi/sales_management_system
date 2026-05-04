"""部署体验：nginx 配置与 Docker 镜像构建参数一致性验证测试
验证 nginx 反向代理配置、Dockerfile 多阶段构建、前端 Dockerfile 配置"""

from pathlib import Path

DEPLOY_DIR = Path(__file__).resolve().parent.parent.parent / "deploy"
BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


class TestNginxUpstreamConfig:
    """nginx upstream 配置与 docker-compose 对齐"""

    def _read_nginx(self):
        return (DEPLOY_DIR / "nginx.conf").read_text()

    def test_upstream_uses_backend_8000(self):
        content = self._read_nginx()
        assert "backend:8000" in content

    def test_upstream_block_defined(self):
        content = self._read_nginx()
        assert "upstream backend" in content


class TestNginxSecurityHeaders:
    """nginx 安全响应头"""

    def _read_nginx(self):
        return (DEPLOY_DIR / "nginx.conf").read_text()

    def test_x_content_type_options(self):
        content = self._read_nginx()
        assert 'X-Content-Type-Options "nosniff"' in content

    def test_x_frame_options(self):
        content = self._read_nginx()
        assert 'X-Frame-Options "DENY"' in content

    def test_x_xss_protection(self):
        content = self._read_nginx()
        assert 'X-XSS-Protection "1; mode=block"' in content

    def test_referrer_policy(self):
        content = self._read_nginx()
        assert "Referrer-Policy" in content

    def test_permissions_policy(self):
        content = self._read_nginx()
        assert "Permissions-Policy" in content

    def test_content_security_policy(self):
        content = self._read_nginx()
        assert "Content-Security-Policy" in content

    def test_server_tokens_off(self):
        content = self._read_nginx()
        assert "server_tokens off" in content


class TestNginxProxyConfig:
    """nginx 反向代理配置"""

    def _read_nginx(self):
        return (DEPLOY_DIR / "nginx.conf").read_text()

    def test_api_proxy_pass(self):
        content = self._read_nginx()
        assert "proxy_pass http://backend" in content

    def test_api_location_block(self):
        content = self._read_nginx()
        assert "location /api/" in content

    def test_uploads_proxy(self):
        content = self._read_nginx()
        assert "location /uploads/" in content

    def test_health_proxy(self):
        content = self._read_nginx()
        assert "location /health" in content
        assert "/api/v1/health" in content

    def test_metrics_proxy(self):
        content = self._read_nginx()
        assert "location /metrics" in content

    def test_proxy_set_header_host(self):
        content = self._read_nginx()
        assert "proxy_set_header Host" in content

    def test_proxy_set_header_real_ip(self):
        content = self._read_nginx()
        assert "proxy_set_header X-Real-IP" in content

    def test_proxy_set_header_forwarded_for(self):
        content = self._read_nginx()
        assert "proxy_set_header X-Forwarded-For" in content

    def test_proxy_set_header_forwarded_proto(self):
        content = self._read_nginx()
        assert "proxy_set_header X-Forwarded-Proto" in content

    def test_proxy_set_header_request_id(self):
        content = self._read_nginx()
        assert "proxy_set_header X-Request-ID" in content


class TestNginxFrontendConfig:
    """nginx 前端静态文件配置"""

    def _read_nginx(self):
        return (DEPLOY_DIR / "nginx.conf").read_text()

    def test_spa_fallback(self):
        content = self._read_nginx()
        assert "try_files $uri $uri/ /index.html" in content

    def test_root_directory(self):
        content = self._read_nginx()
        assert "/usr/share/nginx/html" in content

    def test_gzip_enabled(self):
        content = self._read_nginx()
        assert "gzip on" in content

    def test_gzip_types(self):
        content = self._read_nginx()
        assert "application/json" in content
        assert "application/javascript" in content

    def test_client_max_body_size(self):
        content = self._read_nginx()
        assert "client_max_body_size" in content

    def test_hidden_files_denied(self):
        content = self._read_nginx()
        assert "location ~ /\\." in content or r"location ~ /\." in content
        assert "deny all" in content

    def test_static_asset_cache(self):
        content = self._read_nginx()
        assert "expires 7d" in content


class TestNginxListenConfig:
    """nginx 监听配置"""

    def _read_nginx(self):
        return (DEPLOY_DIR / "nginx.conf").read_text()

    def test_listens_on_port_80(self):
        content = self._read_nginx()
        assert "listen 80" in content

    def test_https_template_exists(self):
        content = self._read_nginx()
        assert "listen 443 ssl" in content

    def test_tls_12_and_13(self):
        content = self._read_nginx()
        assert "TLSv1.2" in content
        assert "TLSv1.3" in content


class TestBackendDockerfile:
    """后端 Dockerfile 多阶段构建"""

    def _read_dockerfile(self):
        return (BACKEND_DIR / "Dockerfile").read_text()

    def test_has_builder_stage(self):
        content = self._read_dockerfile()
        assert "AS builder" in content

    def test_uses_python_313_slim(self):
        content = self._read_dockerfile()
        assert "python:3.13-slim" in content

    def test_builder_installs_gcc(self):
        content = self._read_dockerfile()
        assert "gcc" in content

    def test_builder_installs_libpq_dev(self):
        content = self._read_dockerfile()
        assert "libpq-dev" in content

    def test_runtime_installs_libpq5(self):
        content = self._read_dockerfile()
        assert "libpq5" in content

    def test_copy_from_builder(self):
        content = self._read_dockerfile()
        assert "COPY --from=builder" in content

    def test_copies_app_code(self):
        content = self._read_dockerfile()
        assert "COPY app/ app/" in content

    def test_copies_alembic(self):
        content = self._read_dockerfile()
        assert "COPY alembic/" in content
        assert "COPY alembic.ini" in content

    def test_creates_non_root_user(self):
        content = self._read_dockerfile()
        assert "groupadd -r appuser" in content
        assert "useradd -r -g appuser" in content

    def test_user_directive(self):
        content = self._read_dockerfile()
        assert "USER appuser" in content

    def test_exposes_8000(self):
        content = self._read_dockerfile()
        assert "EXPOSE 8000" in content

    def test_healthcheck_interval_15s(self):
        content = self._read_dockerfile()
        assert "--interval=15s" in content

    def test_healthcheck_timeout_5s(self):
        content = self._read_dockerfile()
        assert "--timeout=5s" in content

    def test_healthcheck_uses_health_endpoint(self):
        content = self._read_dockerfile()
        assert "/api/v1/health" in content

    def test_healthcheck_verifies_database(self):
        content = self._read_dockerfile()
        assert "database" in content
        assert "'ok'" in content

    def test_cmd_uses_uvicorn(self):
        content = self._read_dockerfile()
        assert "uvicorn" in content
        assert "app.main:app" in content

    def test_apt_get_cleanup(self):
        content = self._read_dockerfile()
        assert "rm -rf /var/lib/apt/lists/*" in content

    def test_creates_uploads_dir(self):
        content = self._read_dockerfile()
        assert "/app/uploads" in content

    def test_no_apt_cache_in_runtime(self):
        lines = self._read_dockerfile().splitlines()
        runtime_start = next(i for i, l in enumerate(lines) if "阶段 2" in l or "运行时" in l)
        runtime_section = "\n".join(lines[runtime_start:])
        assert "rm -rf /var/lib/apt/lists/*" in runtime_section


class TestFrontendDockerfile:
    """前端 Dockerfile 多阶段构建"""

    def _read_dockerfile(self):
        return (FRONTEND_DIR / "Dockerfile").read_text()

    def test_has_build_stage(self):
        content = self._read_dockerfile()
        assert "AS build" in content

    def test_uses_node_alpine(self):
        content = self._read_dockerfile()
        assert "node:" in content
        assert "alpine" in content

    def test_npm_ci_not_npm_install(self):
        content = self._read_dockerfile()
        assert "npm ci" in content

    def test_builds_with_npm_run_build(self):
        content = self._read_dockerfile()
        assert "npm run build" in content

    def test_has_vite_api_base_url_arg(self):
        content = self._read_dockerfile()
        assert "VITE_API_BASE_URL" in content

    def test_second_stage_is_alpine(self):
        content = self._read_dockerfile()
        lines = content.splitlines()
        stage2_lines = [l for l in lines if l.startswith("FROM") and "build" not in l.lower().split("from")[1].split()[0] if "FROM" in l]
        has_alpine = any("alpine" in l for l in stage2_lines)
        assert has_alpine

    def test_copies_dist_from_build(self):
        content = self._read_dockerfile()
        assert "COPY --from=build" in content
        assert "/app/dist" in content

    def test_second_stage_minimal(self):
        """第二阶段不包含 RUN/CMD 指令（最小化攻击面）"""
        content = self._read_dockerfile()
        lines = content.strip().splitlines()
        second_stage = False
        for line in lines:
            if line.startswith("FROM"):
                second_stage = "AS build" not in line and "as build" not in line.lower()
                continue
            if second_stage:
                assert not line.startswith("RUN npm"), \
                    f"第二阶段不应有 RUN npm 指令: {line}"


class TestFrontendDevDockerfile:
    """前端开发 Dockerfile"""

    def _read_dockerfile(self):
        return (FRONTEND_DIR / "Dockerfile.dev").read_text()

    def test_uses_node_alpine(self):
        content = self._read_dockerfile()
        assert "node:" in content

    def test_exposes_5173(self):
        content = self._read_dockerfile()
        assert "5173" in content

    def test_runs_dev_server(self):
        content = self._read_dockerfile()
        assert '"npm"' in content and '"run"' in content and '"dev"' in content

    def test_host_0_0_0_0(self):
        content = self._read_dockerfile()
        assert "0.0.0.0" in content


class TestPrometheusConfig:
    """Prometheus 配置验证"""

    def _read_prometheus(self):
        return (DEPLOY_DIR / "prometheus.yml").read_text()

    def test_scrape_interval_15s(self):
        content = self._read_prometheus()
        assert "scrape_interval: 15s" in content

    def test_scrape_backend_job(self):
        content = self._read_prometheus()
        assert 'job_name: "backend"' in content

    def test_metrics_path_correct(self):
        content = self._read_prometheus()
        assert 'metrics_path: "/metrics"' in content

    def test_target_backend_8000(self):
        content = self._read_prometheus()
        assert "backend:8000" in content

    def test_evaluation_interval(self):
        content = self._read_prometheus()
        assert "evaluation_interval" in content


class TestDeployScripts:
    """部署脚本存在性"""

    def test_manage_sh_exists(self):
        assert (DEPLOY_DIR / "manage.sh").exists()

    def test_pre_deploy_check_exists(self):
        assert (DEPLOY_DIR / "pre-deploy-check.sh").exists()

    def test_backup_sh_exists(self):
        assert (DEPLOY_DIR / "backup.sh").exists()

    def test_restore_sh_exists(self):
        assert (DEPLOY_DIR / "restore.sh").exists()

    def test_rollback_sh_exists(self):
        assert (DEPLOY_DIR / "rollback.sh").exists()
