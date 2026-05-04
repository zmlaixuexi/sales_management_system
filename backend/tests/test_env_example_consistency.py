"""文档完善：后端环境变量文档与 .env.example 一致性验证测试
覆盖变量名对齐、默认值一致性、验证器覆盖、
格式规范、敏感配置安全约束"""

import re
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.example"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"


def _read(path: Path) -> str:
    return path.read_text()


def _parse_env_vars(source: str) -> dict[str, str]:
    """从 .env.example 内容解析 KEY=VALUE 对"""
    result = {}
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key.strip()] = value.strip()
    return result


def _parse_settings_fields(source: str) -> dict[str, str]:
    """从 config.py 提取 Settings 类字段名和默认值的原始字符串"""
    result = {}
    in_class = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("class Settings"):
            in_class = True
            continue
        if in_class and stripped.startswith(("def ", "@", "model_config", "class ")):
            if stripped.startswith("model_config") or stripped.startswith("@") or stripped.startswith("def "):
                continue
            if stripped.startswith("class "):
                break
        if not in_class:
            continue
        if stripped.startswith("model_config"):
            continue
        # 匹配字段定义：FIELD_NAME: type = default
        m = re.match(r"(\w+)\s*:\s*\w+\s*=\s*(.+)", stripped)
        if m:
            raw = m.group(2).rstrip().rstrip(",").strip()
            # 剥离行内注释（# 后内容，但 URL 中的 # 除外）
            if "://" not in raw:
                raw = raw.split("#")[0].strip()
            result[m.group(1)] = raw
    return result


# ═══════════════════════════════════════════════════════════
# 1. 变量名对齐验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestVariableNameAlignment:
    """验证 .env.example 与 config.py Settings 字段名完全对齐"""

    def test_env_keys_exist_in_settings(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        for key in env_vars:
            assert key in settings, f".env.example 有 {key}，但 config.py Settings 中不存在"

    def test_settings_fields_exist_in_env(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        for key in settings:
            assert key in env_vars, f"config.py Settings 有 {key}，但 .env.example 中不存在"

    def test_env_file_has_no_duplicate_keys(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        lines = env_src.splitlines()
        keys = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                keys.append(key)
        assert len(keys) == len(set(keys)), f"存在重复键: {[k for k in keys if keys.count(k) > 1]}"

    def test_total_variable_count_matches(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        assert len(env_vars) == len(settings), (
            f".env.example 有 {len(env_vars)} 个变量，config.py 有 {len(settings)} 个字段"
        )

    def test_env_file_is_not_empty(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        assert len(env_vars) >= 20, f".env.example 至少应有 20 个变量，实际 {len(env_vars)}"


# ═══════════════════════════════════════════════════════════
# 2. 默认值一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDefaultValueConsistency:
    """验证 .env.example 默认值与 config.py 一致"""

    def test_integer_defaults_match(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        int_fields = [
            "BACKEND_PORT", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
            "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_SIZE_MB", "MAX_CSV_IMPORT_ROWS",
            "INVENTORY_WARNING_THRESHOLD", "RATE_LIMIT_MAX", "RATE_LIMIT_WINDOW",
            "LOGIN_FAIL_MAX", "LOGIN_FAIL_WINDOW_SECONDS",
            "ACCOUNT_LOCK_MAX_FAILURES", "ACCOUNT_LOCK_WINDOW_SECONDS",
            "SLOW_REQUEST_THRESHOLD_MS", "SLOW_SQL_THRESHOLD_MS",
            "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_RECYCLE_SECONDS",
            "MAX_JSON_BODY_MB", "HSTS_MAX_AGE",
        ]
        for field in int_fields:
            env_val = env_vars.get(field, "")
            cfg_val = settings.get(field, "")
            assert env_val == cfg_val, (
                f"{field}: .env.example={env_val!r}, config.py={cfg_val!r}"
            )

    def test_string_defaults_match(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        str_fields = [
            ("APP_ENV", "development"),
            ("JWT_ALGORITHM", "HS256"),
            ("JWT_ISSUER", "sales-management-system"),
            ("JWT_AUDIENCE", "sales-management-system"),
            ("CORS_ORIGINS", "http://localhost:5173"),
            ("LOG_LEVEL", "INFO"),
            ("LOG_FORMAT", "text"),
            ("UPLOAD_STORAGE_TYPE", "local"),
            ("UPLOAD_PUBLIC_BASE_URL", "/uploads"),
        ]
        for field, expected_env in str_fields:
            env_val = env_vars.get(field, "")
            assert env_val == expected_env, (
                f"{field}: .env.example={env_val!r}, 期望={expected_env!r}"
            )
            # config.py 中的值应包含该默认值
            cfg_val = settings.get(field, "")
            assert expected_env in cfg_val or cfg_val == f'"{expected_env}"', (
                f"{field}: config.py 默认值 {cfg_val!r} 不匹配 {expected_env!r}"
            )

    def test_database_url_defaults_match(self):
        env_src = _read(ENV_FILE)
        cfg_src = _read(CONFIG_FILE)
        env_vars = _parse_env_vars(env_src)
        settings = _parse_settings_fields(cfg_src)
        for field in ["DATABASE_URL", "DATABASE_ASYNC_URL"]:
            env_val = env_vars.get(field, "")
            cfg_val = settings.get(field, "")
            assert env_val in cfg_val or cfg_val.endswith(env_val + '"'), (
                f"{field}: .env.example={env_val!r}, config.py={cfg_val!r}"
            )

    def test_jwt_secret_key_default_is_placeholder(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        assert env_vars.get("JWT_SECRET_KEY") == "change-me"

    def test_upload_dir_has_entry(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        cfg_src = _read(CONFIG_FILE)
        settings = _parse_settings_fields(cfg_src)
        assert "UPLOAD_DIR" in env_vars
        assert "UPLOAD_DIR" in settings
        # config.py 使用动态路径，env 使用相对路径
        assert "uploads" in settings["UPLOAD_DIR"]


# ═══════════════════════════════════════════════════════════
# 3. 验证器覆盖完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestValidatorCoverage:
    """验证 config.py 中关键字段有验证器保护"""

    def test_jwt_expiry_has_positive_validator(self):
        src = _read(CONFIG_FILE)
        body = _find_decorator_field_list(src, "_positive_int")
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in body
        assert "JWT_REFRESH_TOKEN_EXPIRE_DAYS" in body

    def test_pool_size_and_limits_have_strictly_positive_validator(self):
        src = _read(CONFIG_FILE)
        body = _find_decorator_field_list(src, "_strictly_positive")
        assert "DB_POOL_SIZE" in body
        assert "MAX_IMAGE_SIZE_MB" in body
        assert "MAX_CSV_IMPORT_ROWS" in body

    def test_rate_limit_has_non_negative_validator(self):
        src = _read(CONFIG_FILE)
        body = _find_decorator_field_list(src, "_non_negative")
        assert "RATE_LIMIT_MAX" in body

    def test_cors_origins_has_format_validator(self):
        src = _read(CONFIG_FILE)
        body = _find_function_body(src, "_validate_cors_origins")
        assert "http://" in body or "https://" in body
        assert "*" in body

    def test_jwt_secret_has_length_validator(self):
        src = _read(CONFIG_FILE)
        body = _find_function_body(src, "_validate_jwt_secret")
        assert "len(v)" in body or "len(v) <" in body
        assert "不能为空" in body or "不能少于" in body


# ═══════════════════════════════════════════════════════════
# 4. .env.example 格式规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEnvFileFormat:
    """验证 .env.example 格式规范"""

    def test_has_header_comment(self):
        src = _read(ENV_FILE)
        assert src.startswith("#"), ".env.example 应以注释开头说明用途"

    def test_has_section_comments(self):
        src = _read(ENV_FILE)
        sections = re.findall(r"#\s*─{3,}", src)
        assert len(sections) >= 8, f"应有至少 8 个分段注释，实际 {len(sections)}"

    def test_no_empty_values(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        for key, value in env_vars.items():
            assert value.strip(), f"{key} 的值不应为空"

    def test_no_inline_comments_after_values(self):
        src = _read(ENV_FILE)
        for line in src.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                value_part = stripped.split("=", 1)[1].strip()
                # 值部分不应包含 # 注释（URL 中的 # 除外）
                if "#" in value_part and "://" not in value_part:
                    assert False, f"值中有行内注释: {stripped}"

    def test_all_keys_are_uppercase_snake_case(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")
        for key in env_vars:
            assert pattern.match(key), f"键名 {key} 不符合大写下划线命名"


# ═══════════════════════════════════════════════════════════
# 5. 敏感配置安全约束验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSensitiveConfigSecurity:
    """验证敏感配置项有安全提示和安全默认值"""

    def test_jwt_secret_has_production_warning(self):
        src = _read(ENV_FILE)
        # JWT_SECRET_KEY 上方应有生产环境警告
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("JWT_SECRET_KEY="):
                # 检查上方注释是否提到生产环境
                comments_above = []
                for j in range(i - 1, max(i - 5, -1), -1):
                    if lines[j].strip().startswith("#"):
                        comments_above.append(lines[j])
                    else:
                        break
                comment_text = " ".join(comments_above)
                assert "生产" in comment_text, "JWT_SECRET_KEY 上方应有生产环境警告注释"

    def test_hsts_has_https_context_comment(self):
        src = _read(ENV_FILE)
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("HSTS_MAX_AGE="):
                comments = []
                for j in range(i - 1, max(i - 3, -1), -1):
                    if lines[j].strip().startswith("#"):
                        comments.append(lines[j])
                    else:
                        break
                comment_text = " ".join(comments)
                assert "HTTPS" in comment_text, "HSTS_MAX_AGE 应注明仅在 HTTPS 下生效"

    def test_cors_origins_not_wildcard_default(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        cors = env_vars.get("CORS_ORIGINS", "")
        assert cors != "*", "CORS_ORIGINS 默认值不应为通配符 *"
        assert "localhost" in cors, "CORS_ORIGINS 默认值应限制为 localhost"

    def test_jwt_secret_default_is_not_production_safe(self):
        env_src = _read(ENV_FILE)
        env_vars = _parse_env_vars(env_src)
        secret = env_vars.get("JWT_SECRET_KEY", "")
        assert secret == "change-me", "默认密钥应为明显占位值 change-me"
        assert len(secret) >= 8, "默认密钥长度应满足验证器最低要求"

    def test_config_allows_extra_env_vars(self):
        src = _read(CONFIG_FILE)
        assert '"extra": "ignore"' in src, "Settings 应配置 extra=ignore 允许额外环境变量"


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════


def _find_function_body(source: str, func_name: str) -> str:
    pattern = re.compile(rf"(?:async )?def {func_name}\b")
    match = pattern.search(source)
    if not match:
        return ""
    start = match.start()
    lines = source[start:].split("\n")
    body_lines = [lines[0]]
    indent = len(lines[0]) - len(lines[0].lstrip())
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped and (len(line) - len(stripped)) <= indent:
            if stripped.startswith(("def ", "async def ", "class ", "@")):
                break
        body_lines.append(line)
    return "\n".join(body_lines)


def _find_decorator_field_list(source: str, func_name: str) -> str:
    """查找 @field_validator(...) 装饰器中的字段列表"""
    # 找到 _positive_int / _strictly_positive 等函数名前一行的装饰器
    pattern = re.compile(rf'@field_validator\(([^)]+)\)\s*\n\s*@classmethod\s*\n\s*def {func_name}')
    match = pattern.search(source)
    if not match:
        return ""
    return match.group(1)
