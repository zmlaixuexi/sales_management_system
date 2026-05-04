"""安全加固：后端 logout token 失效机制验证测试
覆盖 token 类型区分验证、密码修改后旧 token 失效、
logout 端点行为、token 结构安全字段、refresh token 安全"""

import re
from pathlib import Path

AUTH_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "auth.py"
DEPS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"
SECURITY_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "security.py"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
USER_MODEL = Path(__file__).resolve().parent.parent / "app" / "models" / "user.py"


def _read(path: Path) -> str:
    return path.read_text()


def _find_function_body(source: str, func_name: str) -> str:
    pattern = re.compile(rf"def {func_name}\b")
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
            if stripped.startswith(("def ", "class ", "@")):
                break
        body_lines.append(line)
    return "\n".join(body_lines)


# ═══════════════════════════════════════════════════════════
# 1. token 类型区分验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenTypeEnforcement:
    """验证 access/refresh token 类型严格区分"""

    def test_get_current_user_requires_access_type(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "get_current_user")
        assert 'token_type != "access"' in body

    def test_refresh_endpoint_requires_refresh_type(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "refresh_token")
        assert 'token_type != "refresh"' in body

    def test_create_access_token_sets_type(self):
        source = _read(SECURITY_FILE)
        body = _find_function_body(source, "create_access_token")
        assert '"type": "access"' in body

    def test_create_refresh_token_sets_type(self):
        source = _read(SECURITY_FILE)
        body = _find_function_body(source, "create_refresh_token")
        assert '"type": "refresh"' in body

    def test_both_tokens_include_iss_and_aud(self):
        source = _read(SECURITY_FILE)
        assert source.count("JWT_ISSUER") >= 2
        assert source.count("JWT_AUDIENCE") >= 2


# ═══════════════════════════════════════════════════════════
# 2. 密码修改后旧 token 失效验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordChangeInvalidation:
    """验证密码修改后旧 token 自动失效"""

    def test_get_current_user_checks_password_changed_at(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "get_current_user")
        assert "password_changed_at" in body

    def test_refresh_endpoint_checks_password_changed_at(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "refresh_token")
        assert "password_changed_at" in body

    def test_compares_token_iat_with_password_change_time(self):
        source = _read(DEPS_FILE)
        assert "token_issued < changed_at" in source

    def test_handles_timezone_aware_comparison(self):
        source = _read(DEPS_FILE)
        assert "replace(tzinfo=UTC)" in source or "tzinfo" in source

    def test_truncates_to_second_precision(self):
        source = _read(DEPS_FILE)
        assert "microsecond=0" in source


# ═══════════════════════════════════════════════════════════
# 3. logout 端点行为验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestLogoutBehavior:
    """验证 logout 端点行为"""

    def test_logout_endpoint_exists(self):
        source = _read(AUTH_FILE)
        assert '@router.post("/logout")' in source

    def test_logout_returns_success_message(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "logout")
        assert "已退出登录" in body
        assert "resp(" in body

    def test_logout_does_not_require_auth(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "logout")
        assert "current_user" not in body
        assert "Depends" not in body

    def test_login_generates_new_token_pair(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "login")
        assert "create_access_token" in body
        assert "create_refresh_token" in body

    def test_refresh_generates_new_token_pair(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "refresh_token")
        assert "create_access_token" in body
        assert "create_refresh_token" in body


# ═══════════════════════════════════════════════════════════
# 4. token 结构安全字段验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenStructureSecurity:
    """验证 JWT token 包含安全相关字段"""

    def test_tokens_include_jti_unique_id(self):
        source = _read(SECURITY_FILE)
        assert source.count('"jti"') >= 2
        assert "uuid.uuid4()" in source

    def test_tokens_include_iat_issued_at(self):
        source = _read(SECURITY_FILE)
        assert source.count('"iat"') >= 2

    def test_tokens_include_exp_expiration(self):
        source = _read(SECURITY_FILE)
        assert source.count('"exp"') >= 2

    def test_access_token_has_configurable_expiry(self):
        source = _read(SECURITY_FILE)
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in source
        source_cfg = _read(CONFIG_FILE)
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in source_cfg

    def test_refresh_token_has_longer_expiry(self):
        source = _read(SECURITY_FILE)
        assert "JWT_REFRESH_TOKEN_EXPIRE_DAYS" in source
        source_cfg = _read(CONFIG_FILE)
        assert "JWT_REFRESH_TOKEN_EXPIRE_DAYS" in source_cfg


# ═══════════════════════════════════════════════════════════
# 5. 用户状态检查验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestUserStatusCheck:
    """验证 token 验证时检查用户状态"""

    def test_get_current_user_checks_is_active(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "get_current_user")
        assert "is_active" in body

    def test_get_current_user_checks_deleted_at(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "get_current_user")
        assert "deleted_at" in body

    def test_refresh_endpoint_checks_is_active(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "refresh_token")
        assert "is_active" in body

    def test_login_checks_is_active(self):
        source = _read(AUTH_FILE)
        body = _find_function_body(source, "login")
        assert "is_active" in body

    def test_user_model_has_password_changed_at(self):
        source = _read(USER_MODEL)
        assert "password_changed_at" in source
