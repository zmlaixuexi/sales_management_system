"""部署体验：后端 Dockerfile 多阶段构建配置验证测试
覆盖多阶段构建结构、安全配置、健康检查、
应用文件复制、pyproject.toml 配置"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
PYPROJECT = ROOT / "pyproject.toml"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. 多阶段构建结构验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMultiStageBuild:
    """验证 Dockerfile 使用多阶段构建"""

    def test_has_builder_stage(self):
        src = _read(DOCKERFILE)
        assert "AS builder" in src

    def test_builder_uses_python_slim(self):
        src = _read(DOCKERFILE)
        assert "python:3.13-slim" in src

    def test_has_two_from_stages(self):
        src = _read(DOCKERFILE)
        from_lines = re.findall(r"^FROM\s+", src, re.MULTILINE)
        assert len(from_lines) >= 2, f"应至少 2 个 FROM 阶段，实际 {len(from_lines)}"

    def test_runtime_copies_from_builder(self):
        src = _read(DOCKERFILE)
        assert "COPY --from=builder" in src

    def test_builder_installs_dependencies(self):
        src = _read(DOCKERFILE)
        assert "pip install" in src
        assert "pyproject.toml" in src


# ═══════════════════════════════════════════════════════════
# 2. 安全配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSecurityConfig:
    """验证 Dockerfile 安全配置"""

    def test_runs_as_non_root_user(self):
        src = _read(DOCKERFILE)
        assert "useradd" in src or "adduser" in src
        assert "USER appuser" in src

    def test_creates_dedicated_group(self):
        src = _read(DOCKERFILE)
        assert "groupadd" in src

    def test_uses_slim_base_image_not_full(self):
        src = _read(DOCKERFILE)
        # 不应使用 python:3.13（无 slim）
        full_image_matches = re.findall(r"FROM\s+python:\d+\.\d+\s", src)
        assert len(full_image_matches) == 0, "不应使用非 slim 基础镜像"

    def test_cleans_apt_cache(self):
        src = _read(DOCKERFILE)
        assert "rm -rf /var/lib/apt/lists/*" in src

    def test_user_has_no_login_shell(self):
        src = _read(DOCKERFILE)
        assert "/sbin/nologin" in src


# ═══════════════════════════════════════════════════════════
# 3. 健康检查验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHealthCheck:
    """验证 Dockerfile 健康检查配置"""

    def test_has_healthcheck_instruction(self):
        src = _read(DOCKERFILE)
        assert "HEALTHCHECK" in src

    def test_healthcheck_uses_health_endpoint(self):
        src = _read(DOCKERFILE)
        assert "/health" in src or "/api/v1/health" in src

    def test_healthcheck_has_interval(self):
        src = _read(DOCKERFILE)
        assert "--interval=" in src

    def test_healthcheck_has_timeout(self):
        src = _read(DOCKERFILE)
        assert "--timeout=" in src

    def test_healthcheck_has_retries(self):
        src = _read(DOCKERFILE)
        assert "--retries=" in src


# ═══════════════════════════════════════════════════════════
# 4. 应用文件复制验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestApplicationFiles:
    """验证 Dockerfile 正确复制应用文件"""

    def test_copies_app_directory(self):
        src = _read(DOCKERFILE)
        assert "COPY app/ app/" in src or "COPY app/" in src

    def test_copies_alembic_directory(self):
        src = _read(DOCKERFILE)
        assert "alembic/" in src

    def test_copies_alembic_ini(self):
        src = _read(DOCKERFILE)
        assert "alembic.ini" in src

    def test_creates_uploads_directory(self):
        src = _read(DOCKERFILE)
        assert "uploads" in src or "/app/uploads" in src

    def test_exposes_correct_port(self):
        src = _read(DOCKERFILE)
        assert "EXPOSE 8000" in src or "8000" in src


# ═══════════════════════════════════════════════════════════
# 5. pyproject.toml 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPyprojectConfig:
    """验证 pyproject.toml 构建配置"""

    def test_declares_python_version_requirement(self):
        src = _read(PYPROJECT)
        assert "requires-python" in src
        assert ">=3.11" in src

    def test_declares_core_dependencies(self):
        src = _read(PYPROJECT)
        for dep in ["fastapi", "uvicorn", "sqlalchemy", "alembic", "pydantic"]:
            assert dep in src, f"pyproject.toml 缺少 {dep} 依赖"

    def test_declares_dev_dependencies(self):
        src = _read(PYPROJECT)
        assert "dev" in src
        assert "pytest" in src
        assert "ruff" in src

    def test_configures_ruff_linting(self):
        src = _read(PYPROJECT)
        assert "[tool.ruff]" in src
        assert "line-length" in src

    def test_configures_pytest(self):
        src = _read(PYPROJECT)
        assert "[tool.pytest.ini_options]" in src
        assert "testpaths" in src
