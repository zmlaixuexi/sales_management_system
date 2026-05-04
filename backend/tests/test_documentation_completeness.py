"""文档完善：README 与项目文档完整性验证测试
覆盖 README 核心章节、docs 文档覆盖、
.env.example 与文档一致性、API 文档模块覆盖、贡献指南完整性"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
README = ROOT / "README.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
ENV_EXAMPLE = ROOT / ".env.example"
DOCS_API = ROOT / "docs" / "api.md"
DOCS_ARCH = ROOT / "docs" / "architecture.md"
DOCS_DB = ROOT / "docs" / "database.md"
DOCS_DEPLOY = ROOT / "docs" / "deployment.md"
DOCS_TESTING = ROOT / "docs" / "testing.md"


def _read(path: Path) -> str:
    return path.read_text()


# ═══════════════════════════════════════════════════════════
# 1. README 核心章节验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestReadmeSections:
    """验证 README 包含核心章节"""

    def test_has_title_and_description(self):
        source = _read(README)
        assert source.startswith("# 销售管理系统")
        assert "技术栈" in source

    def test_has_quick_start_section(self):
        source = _read(README)
        assert "快速启动" in source
        assert "前置条件" in source
        assert "Docker Compose" in source

    def test_has_project_structure(self):
        source = _read(README)
        assert "项目结构" in source
        assert "backend/" in source
        assert "frontend/" in source
        assert "deploy/" in source

    def test_has_testing_section(self):
        source = _read(README)
        assert "## 测试" in source
        assert "后端测试" in source
        assert "前端测试" in source

    def test_has_api_overview_table(self):
        source = _read(README)
        assert "API 概览" in source
        assert "/api/v1/auth" in source
        assert "/api/v1/products" in source
        assert "/api/v1/sales-orders" in source


# ═══════════════════════════════════════════════════════════
# 2. docs 文档覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDocsCoverage:
    """验证 docs/ 目录文档覆盖"""

    def test_api_doc_exists_and_has_auth(self):
        source = _read(DOCS_API)
        assert "认证" in source
        assert "Bearer" in source

    def test_architecture_doc_has_tech_stack(self):
        source = _read(DOCS_ARCH)
        assert "技术栈" in source
        assert "FastAPI" in source
        assert "React" in source

    def test_database_doc_exists(self):
        assert DOCS_DB.exists()
        source = _read(DOCS_DB)
        assert len(source) > 100

    def test_deployment_doc_has_env_requirements(self):
        source = _read(DOCS_DEPLOY)
        assert "环境要求" in source
        assert "Docker" in source

    def test_testing_doc_exists(self):
        assert DOCS_TESTING.exists()
        source = _read(DOCS_TESTING)
        assert "测试" in source


# ═══════════════════════════════════════════════════════════
# 3. .env.example 与 README 一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEnvExampleConsistency:
    """验证 .env.example 与 README 环境变量表一致"""

    def test_env_example_exists(self):
        assert ENV_EXAMPLE.exists()

    def test_readme_env_table_covers_database_url(self):
        source = _read(README)
        assert "DATABASE_URL" in source

    def test_env_example_has_jwt_secret(self):
        source = _read(ENV_EXAMPLE)
        assert "JWT_SECRET_KEY" in source

    def test_readme_mentions_upload_dir(self):
        source = _read(README)
        assert "UPLOAD_DIR" in source or "MAX_IMAGE_SIZE" in source

    def test_env_example_has_rate_limit_vars(self):
        source = _read(ENV_EXAMPLE)
        assert "RATE_LIMIT" in source


# ═══════════════════════════════════════════════════════════
# 4. API 文档模块覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestApiDocCoverage:
    """验证 API 文档覆盖所有模块"""

    def test_api_doc_has_auth_endpoints(self):
        source = _read(DOCS_API)
        assert "/auth" in source or "登录" in source

    def test_api_doc_has_product_endpoints(self):
        source = _read(DOCS_API)
        assert "商品" in source or "/products" in source

    def test_api_doc_has_order_endpoints(self):
        source = _read(DOCS_API)
        assert "订单" in source or "/sales-orders" in source

    def test_api_doc_has_payment_endpoints(self):
        source = _read(DOCS_API)
        assert "收款" in source or "/payments" in source

    def test_api_doc_has_common_response_format(self):
        source = _read(DOCS_API)
        assert "通用响应" in source or "success" in source
        assert "request_id" in source


# ═══════════════════════════════════════════════════════════
# 5. 贡献指南完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestContributingGuide:
    """验证 CONTRIBUTING.md 贡献指南"""

    def test_contributing_exists(self):
        assert CONTRIBUTING.exists()

    def test_has_dev_environment_setup(self):
        source = _read(CONTRIBUTING)
        assert "开发环境" in source

    def test_mentions_env_example(self):
        source = _read(CONTRIBUTING)
        assert ".env.example" in source or ".env" in source

    def test_mentions_test_command(self):
        source = _read(CONTRIBUTING)
        assert "pytest" in source or "test" in source.lower()

    def test_has_backend_and_frontend_setup(self):
        source = _read(CONTRIBUTING)
        has_backend = "backend" in source.lower() or "pip" in source
        has_frontend = "frontend" in source.lower() or "npm" in source
        assert has_backend
        assert has_frontend
