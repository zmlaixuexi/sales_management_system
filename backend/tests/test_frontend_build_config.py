"""部署体验：前端构建与环境变量配置验证测试
覆盖 Vite 构建配置、环境变量声明、
TypeScript 配置、package.json 脚本、前端 Dockerfile 配置"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND = ROOT / "frontend"
VITE_CONFIG = FRONTEND / "vite.config.ts"
TSCONFIG = FRONTEND / "tsconfig.json"
TSCONFIG_APP = FRONTEND / "tsconfig.app.json"
TSCONFIG_NODE = FRONTEND / "tsconfig.node.json"
PACKAGE_JSON = FRONTEND / "package.json"
ENV_EXAMPLE = FRONTEND / ".env.example"
FRONTEND_DOCKERFILE = FRONTEND / "Dockerfile"


def _read(path: Path) -> str:
    return path.read_text()


def _read_json(path: Path) -> dict:
    """读取 JSONC 文件（支持 /* */ 注释和尾随逗号）"""
    src = _read(path)
    cleaned = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
    # 移除尾随逗号（}, ] 前的逗号）
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    return json.loads(cleaned)


# ═══════════════════════════════════════════════════════════
# 1. Vite 构建配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestViteBuildConfig:
    """验证 Vite 构建配置完整性"""

    def test_vite_config_exists(self):
        assert VITE_CONFIG.exists(), "vite.config.ts 不存在"

    def test_uses_react_plugin(self):
        src = _read(VITE_CONFIG)
        assert "react()" in src or "@vitejs/plugin-react" in src

    def test_has_path_alias_at_sign(self):
        src = _read(VITE_CONFIG)
        assert "'@'" in src or '"@"' in src
        assert "resolve(__dirname" in src or "resolve(" in src

    def test_has_manual_chunks_splitting(self):
        src = _read(VITE_CONFIG)
        assert "manualChunks" in src
        assert "vendor-react" in src
        assert "vendor-antd" in src

    def test_has_dev_proxy_for_api(self):
        src = _read(VITE_CONFIG)
        assert "proxy" in src
        assert "'/api'" in src or '"/api"' in src
        assert "VITE_PROXY_TARGET" in src


# ═══════════════════════════════════════════════════════════
# 2. 环境变量声明验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEnvironmentVariables:
    """验证环境变量声明与使用一致"""

    def test_env_example_exists(self):
        assert ENV_EXAMPLE.exists(), ".env.example 不存在"

    def test_env_example_declares_vite_api_base_url(self):
        src = _read(ENV_EXAMPLE)
        assert "VITE_API_BASE_URL" in src

    def test_env_example_declares_vite_proxy_target(self):
        src = _read(ENV_EXAMPLE)
        assert "VITE_PROXY_TARGET" in src

    def test_vite_config_uses_env_variables(self):
        src = _read(VITE_CONFIG)
        assert "VITE_PROXY_TARGET" in src
        assert "loadEnv" in src

    def test_client_uses_vite_api_base_url(self):
        client = FRONTEND / "src" / "api" / "client.ts"
        src = _read(client)
        assert "VITE_API_BASE_URL" in src


# ═══════════════════════════════════════════════════════════
# 3. TypeScript 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTypeScriptConfig:
    """验证 TypeScript 配置严格性和完整性"""

    def test_tsconfig_uses_project_references(self):
        src = _read(TSCONFIG)
        assert '"references"' in src
        assert "./tsconfig.app.json" in src
        assert "./tsconfig.node.json" in src

    def test_tsconfig_app_has_strict_mode(self):
        src = _read(TSCONFIG_APP)
        assert '"strict": true' in src

    def test_tsconfig_app_has_no_unchecked_indexed_access(self):
        src = _read(TSCONFIG_APP)
        assert '"noUncheckedIndexedAccess": true' in src

    def test_tsconfig_app_path_alias_matches_vite(self):
        src = _read(TSCONFIG_APP)
        assert '"@/*"' in src or "'@/*'" in src
        assert '"src/*"' in src or "'src/*'" in src

    def test_tsconfig_app_excludes_test_dirs(self):
        src = _read(TSCONFIG_APP)
        assert "src/__tests__" in src
        assert "src/test" in src


# ═══════════════════════════════════════════════════════════
# 4. package.json 脚本验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPackageJsonScripts:
    """验证 package.json 构建脚本完整性"""

    def test_has_build_script(self):
        data = _read_json(PACKAGE_JSON)
        scripts = data.get("scripts", {})
        assert "build" in scripts
        assert "tsc" in scripts["build"]
        assert "vite build" in scripts["build"]

    def test_has_dev_script(self):
        data = _read_json(PACKAGE_JSON)
        assert "dev" in data.get("scripts", {})

    def test_has_test_script(self):
        data = _read_json(PACKAGE_JSON)
        scripts = data.get("scripts", {})
        assert "test" in scripts
        assert "vitest" in scripts["test"]

    def test_has_lint_script(self):
        data = _read_json(PACKAGE_JSON)
        assert "lint" in data.get("scripts", {})

    def test_has_test_coverage_script(self):
        data = _read_json(PACKAGE_JSON)
        scripts = data.get("scripts", {})
        assert "test:coverage" in scripts or "test:watch" in scripts


# ═══════════════════════════════════════════════════════════
# 5. 前端 Dockerfile 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFrontendDockerfile:
    """验证前端 Dockerfile 构建配置"""

    def test_dockerfile_exists(self):
        assert FRONTEND_DOCKERFILE.exists(), "deploy/frontend/Dockerfile 不存在"

    def test_uses_multi_stage_build(self):
        src = _read(FRONTEND_DOCKERFILE)
        from_count = len(re.findall(r"^FROM\s+", src, re.MULTILINE))
        assert from_count >= 2, f"应至少 2 个 FROM 阶段，实际 {from_count}"

    def test_build_stage_runs_npm_build(self):
        src = _read(FRONTEND_DOCKERFILE)
        assert "npm run build" in src

    def test_uses_nginx_for_serving(self):
        src = _read(FRONTEND_DOCKERFILE)
        assert "nginx" in src.lower()

    def test_copies_dist_to_nginx_serve_directory(self):
        src = _read(FRONTEND_DOCKERFILE)
        assert "/usr/share/nginx/html" in src or "dist" in src
