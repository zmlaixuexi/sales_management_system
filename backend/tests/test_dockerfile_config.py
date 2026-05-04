"""部署体验：后端 Dockerfile 多阶段构建配置验证测试
覆盖多阶段构建结构、安全配置、健康检查、
应用文件复制、pyproject.toml 配置"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = Path(__file__).resolve().parent.parent
DOCKERFILE = BACKEND / "Dockerfile"
PYPROJECT = BACKEND / "pyproject.toml"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. 多阶段构建结构验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMultiStageBuild:
    """验证多阶段构建结构"""

    def test_dockerfile_exists(self):
        assert DOCKERFILE.exists()

    def test_two_build_stages(self):
        source = _read(DOCKERFILE)
        from_lines = [line for line in source.split("\n") if line.strip().startswith("FROM ")]
        assert len(from_lines) == 2, f"期望 2 个 FROM 指令，实际 {len(from_lines)}"
        assert "AS builder" in from_lines[0]

    def test_builder_stage_uses_python_slim(self):
        source = _read(DOCKERFILE)
        assert "python:3.13-slim" in source

    def test_builder_installs_dependencies(self):
        source = _read(DOCKERFILE)
        assert "pip install" in source
        assert "pyproject.toml" in source

    def test_runtime_copies_from_builder(self):
        source = _read(DOCKERFILE)
        assert "COPY --from=builder" in source


# ═══════════════════════════════════════════════════════════
# 2. 安全配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSecurityConfig:
    """验证 Docker 安全配置"""

    def test_uses_non_root_user(self):
        source = _read(DOCKERFILE)
        assert "USER appuser" in source

    def test_creates_dedicated_user(self):
        source = _read(DOCKERFILE)
        assert "groupadd" in source
        assert "useradd" in source
        assert "appuser" in source

    def test_user_has_no_login_shell(self):
        source = _read(DOCKERFILE)
        assert "/sbin/nologin" in source

    def test_apt_get_cleanup(self):
        source = _read(DOCKERFILE)
        assert "rm -rf /var/lib/apt/lists/" in source

    def test_runtime_only_has_libpq(self):
        """运行时镜像仅安装 libpq5（无 gcc）"""
        source = _read(DOCKERFILE)
        # 找到阶段 2 之后的内容
        lines = source.split("\n")
        runtime_start = -1
        for i, line in enumerate(lines):
            if "阶段 2" in line or "运行时" in line:
                runtime_start = i
                break
        assert runtime_start > 0, "未找到阶段 2 注释"
        runtime_section = "\n".join(lines[runtime_start:])
        assert "libpq" in runtime_section
        assert "gcc" not in runtime_section


# ═══════════════════════════════════════════════════════════
# 3. 健康检查验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHealthCheck:
    """验证 HEALTHCHECK 指令"""

    def test_healthcheck_exists(self):
        source = _read(DOCKERFILE)
        assert "HEALTHCHECK" in source

    def test_healthcheck_checks_health_endpoint(self):
        source = _read(DOCKERFILE)
        assert "/health" in source or "/api/v1/health" in source

    def test_healthcheck_has_interval(self):
        source = _read(DOCKERFILE)
        assert "--interval=" in source

    def test_healthcheck_has_timeout(self):
        source = _read(DOCKERFILE)
        assert "--timeout=" in source

    def test_healthcheck_verifies_database_ok(self):
        source = _read(DOCKERFILE)
        assert "database" in source
        assert "ok" in source


# ═══════════════════════════════════════════════════════════
# 4. 应用文件复制验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAppCopy:
    """验证应用文件复制"""

    def test_copies_app_directory(self):
        source = _read(DOCKERFILE)
        assert "COPY app/ app/" in source

    def test_copies_alembic_directory(self):
        source = _read(DOCKERFILE)
        assert "COPY alembic/ alembic/" in source

    def test_copies_alembic_ini(self):
        source = _read(DOCKERFILE)
        assert "COPY alembic.ini" in source

    def test_creates_uploads_directory(self):
        source = _read(DOCKERFILE)
        assert "uploads" in source
        assert "mkdir" in source

    def test_uploads_owned_by_appuser(self):
        source = _read(DOCKERFILE)
        assert "chown" in source
        assert "appuser" in source


# ═══════════════════════════════════════════════════════════
# 5. pyproject.toml 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPyprojectConfig:
    """验证 pyproject.toml 构建配置"""

    def test_project_name_and_version(self):
        source = _read(PYPROJECT)
        assert 'name = "sales-management-backend"' in source
        assert "version" in source

    def test_python_version_requirement(self):
        source = _read(PYPROJECT)
        assert "requires-python" in source
        assert ">=3.11" in source

    def test_key_dependencies_listed(self):
        source = _read(PYPROJECT)
        for dep in ["fastapi", "uvicorn", "sqlalchemy", "alembic", "pydantic", "python-jose"]:
            assert dep in source, f"缺少依赖: {dep}"

    def test_ruff_config_present(self):
        source = _read(PYPROJECT)
        assert "[tool.ruff]" in source
        assert "target-version" in source
        assert "line-length" in source

    def test_pytest_config_present(self):
        source = _read(PYPROJECT)
        assert "[tool.pytest.ini_options]" in source
        assert "testpaths" in source
