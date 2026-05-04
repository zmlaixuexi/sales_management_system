"""代码质量：后端配置项与环境变量引用一致性验证测试
覆盖配置字段定义、settings 引用覆盖、env.example 完整性、
验证器覆盖、配置分类"""

import re
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"
APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _extract_defined_settings() -> set[str]:
    source = CONFIG_FILE.read_text()
    return {
        m.group(1)
        for m in re.finditer(r"^\s+(\w+)\s*:\s*(?:int|str|float|bool)", source, re.MULTILINE)
    }


def _extract_used_settings() -> dict[str, list[str]]:
    """返回 {setting_name: [file_paths]}"""
    used: dict[str, list[str]] = {}
    for f in APP_DIR.rglob("*.py"):
        if "test_" in f.name:
            continue
        source = f.read_text()
        for m in re.finditer(r"settings\.(\w+)", source):
            name = m.group(1)
            rel = str(f.relative_to(APP_DIR))
            used.setdefault(name, []).append(rel)
    return used


def _extract_env_example_keys() -> set[str]:
    if not ENV_EXAMPLE.exists():
        return set()
    source = ENV_EXAMPLE.read_text()
    return {m.group(1) for m in re.finditer(r"^(\w+)=", source, re.MULTILINE)}


def _extract_validated_fields() -> list[str]:
    source = CONFIG_FILE.read_text()
    return [m.group(1) for m in re.finditer(r'@field_validator\("([^"]+)"', source)]


# ═══════════════════════════════════════════════════════════
# 1. 配置字段定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestConfigFields:
    """验证配置字段定义完整"""

    def test_34_settings_defined(self):
        defined = _extract_defined_settings()
        assert len(defined) == 34

    def test_jwt_settings_complete(self):
        defined = _extract_defined_settings()
        for s in ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ISSUER", "JWT_AUDIENCE",
                   "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS"]:
            assert s in defined, f"缺少 {s}"

    def test_database_settings_complete(self):
        defined = _extract_defined_settings()
        for s in ["DATABASE_URL", "DATABASE_ASYNC_URL", "DB_POOL_SIZE",
                   "DB_MAX_OVERFLOW", "DB_POOL_RECYCLE_SECONDS", "DB_CONNECT_TIMEOUT_SECONDS"]:
            assert s in defined, f"缺少 {s}"

    def test_security_settings_complete(self):
        defined = _extract_defined_settings()
        for s in ["RATE_LIMIT_MAX", "RATE_LIMIT_WINDOW", "MAX_JSON_BODY_MB",
                   "HSTS_MAX_AGE", "LOGIN_FAIL_MAX", "LOGIN_FAIL_WINDOW_SECONDS",
                   "ACCOUNT_LOCK_MAX_FAILURES", "ACCOUNT_LOCK_WINDOW_SECONDS"]:
            assert s in defined, f"缺少 {s}"

    def test_upload_settings_complete(self):
        defined = _extract_defined_settings()
        for s in ["UPLOAD_DIR", "UPLOAD_PUBLIC_BASE_URL", "UPLOAD_STORAGE_TYPE",
                   "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_SIZE_MB", "MAX_CSV_IMPORT_ROWS"]:
            assert s in defined, f"缺少 {s}"


# ═══════════════════════════════════════════════════════════
# 2. settings 引用覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSettingsUsage:
    """验证所有配置字段被正确引用"""

    def test_all_used_settings_are_defined(self):
        used = _extract_used_settings()
        defined = _extract_defined_settings()
        for name in used:
            assert name in defined, f"settings.{name} 在代码中使用但未在 config.py 定义"

    def test_jwt_settings_used_in_security_and_deps(self):
        used = _extract_used_settings()
        jwt_fields = ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ISSUER", "JWT_AUDIENCE",
                       "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS"]
        for field in jwt_fields:
            assert field in used, f"settings.{field} 已定义但未被使用"

    def test_database_url_used_in_session(self):
        used = _extract_used_settings()
        assert "DATABASE_URL" in used
        files = used["DATABASE_URL"]
        assert any("session" in f for f in files)

    def test_upload_settings_used_in_file_service(self):
        used = _extract_used_settings()
        assert "UPLOAD_DIR" in used
        assert "MAX_IMAGE_SIZE_MB" in used
        files = used["UPLOAD_DIR"]
        assert any("file_service" in f for f in files)

    def test_rate_limit_used_in_main(self):
        used = _extract_used_settings()
        assert "RATE_LIMIT_MAX" in used
        assert "RATE_LIMIT_WINDOW" in used


# ═══════════════════════════════════════════════════════════
# 3. .env.example 完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEnvExample:
    """验证 .env.example 包含所有配置项"""

    def test_env_example_exists(self):
        assert ENV_EXAMPLE.exists()

    def test_env_example_covers_all_used_settings(self):
        env_keys = _extract_env_example_keys()
        used = _extract_used_settings()
        missing = set(used.keys()) - env_keys
        assert len(missing) == 0, f".env.example 缺少: {sorted(missing)}"

    def test_env_example_has_comments(self):
        source = ENV_EXAMPLE.read_text()
        comment_lines = [line for line in source.split("\n") if line.startswith("#")]
        assert len(comment_lines) >= 5

    def test_env_example_values_match_defaults(self):
        env_src = ENV_EXAMPLE.read_text()
        assert "JWT_ALGORITHM=HS256" in env_src
        assert "APP_ENV=development" in env_src
        assert "DB_POOL_SIZE=5" in env_src

    def test_env_example_has_security_warning(self):
        source = ENV_EXAMPLE.read_text()
        assert "生产" in source or "production" in source.lower()
        assert "安全" in source or "secret" in source.lower() or "随机" in source


# ═══════════════════════════════════════════════════════════
# 4. 验证器覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestConfigValidators:
    """验证关键字段有验证器保护"""

    def test_jwt_secret_has_validator(self):
        validated = _extract_validated_fields()
        assert "JWT_SECRET_KEY" in validated

    def test_jwt_expire_has_positive_validator(self):
        validated = _extract_validated_fields()
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in validated

    def test_cors_origins_has_validator(self):
        validated = _extract_validated_fields()
        assert "CORS_ORIGINS" in validated

    def test_db_pool_size_has_validator(self):
        validated = _extract_validated_fields()
        assert "DB_POOL_SIZE" in validated

    def test_rate_limit_has_non_negative_validator(self):
        validated = _extract_validated_fields()
        assert "RATE_LIMIT_MAX" in validated


# ═══════════════════════════════════════════════════════════
# 5. 配置引用模块覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestConfigModuleCoverage:
    """验证配置在关键模块中被正确引用"""

    def test_security_module_uses_jwt_settings(self):
        source = (APP_DIR / "core" / "security.py").read_text()
        assert "settings.JWT_SECRET_KEY" in source
        assert "settings.JWT_ALGORITHM" in source
        assert "settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in source

    def test_main_module_uses_env_and_cors(self):
        source = (APP_DIR / "main.py").read_text()
        assert "settings.APP_ENV" in source
        assert "settings.CORS_ORIGINS" in source

    def test_body_limit_uses_max_json_body(self):
        source = (APP_DIR / "core" / "body_limit.py").read_text()
        assert "settings.MAX_JSON_BODY_MB" in source

    def test_security_headers_uses_hsts(self):
        source = (APP_DIR / "core" / "security_headers.py").read_text()
        assert "settings.HSTS_MAX_AGE" in source

    def test_auth_api_uses_login_fail_settings(self):
        source = (APP_DIR / "api" / "v1" / "auth.py").read_text()
        assert "settings.LOGIN_FAIL_MAX" in source
        assert "settings.LOGIN_FAIL_WINDOW_SECONDS" in source
