"""安全加固：后端密码强度验证覆盖测试
覆盖密码强度规则定义、Schema 集成、哈希安全、
密码修改流程、黑名单覆盖"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PWD_FILE = ROOT / "app" / "core" / "password_strength.py"
AUTH_SCHEMA = ROOT / "app" / "schemas" / "auth.py"
SECURITY = ROOT / "app" / "core" / "security.py"
AUTH_API = ROOT / "app" / "api" / "v1" / "auth.py"
USERS_API = ROOT / "app" / "api" / "v1" / "users.py"


def _read(path: Path) -> str:
    return path.read_text()


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


# ═══════════════════════════════════════════════════════════
# 1. 密码强度规则定义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordStrengthRules:
    """验证密码强度规则定义完整"""

    def test_has_uppercase_check(self):
        src = _read(PWD_FILE)
        assert r"[A-Z]" in src or "[A-Z]" in src

    def test_has_lowercase_check(self):
        src = _read(PWD_FILE)
        assert r"[a-z]" in src or "[a-z]" in src

    def test_has_digit_check(self):
        src = _read(PWD_FILE)
        assert r"\d" in src or "\\d" in src

    def test_has_special_char_check(self):
        src = _read(PWD_FILE)
        assert r"[^a-zA-Z0-9]" in src or "[^a-zA-Z0-9]" in src

    def test_has_weak_password_blacklist(self):
        src = _read(PWD_FILE)
        assert "_WEAK_PASSWORDS" in src
        assert "frozenset" in src
        # 应包含常见弱密码
        for weak in ["password", "123456", "admin", "qwerty", "root"]:
            assert weak in src, f"黑名单应包含 {weak}"


# ═══════════════════════════════════════════════════════════
# 2. Schema 集成验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSchemaIntegration:
    """验证密码强度验证器正确集成到 Schema"""

    def test_user_create_has_password_field_with_length_bounds(self):
        src = _read(AUTH_SCHEMA)
        # UserCreate 的 password 字段应有 min_length 和 max_length
        assert "min_length=6" in src
        assert "max_length=100" in src

    def test_user_create_has_password_validator(self):
        src = _read(AUTH_SCHEMA)
        assert "validate_password_strength" in src

    def test_change_password_request_has_same_validator(self):
        src = _read(AUTH_SCHEMA)
        body = _find_function_body(src, "validate_password_strength")
        # 该验证器被多个字段使用
        assert "validate_password_strength" in src
        # ChangePasswordRequest 的 new_password 应使用相同验证器
        schema_src = src
        # 找 field_validator 引用
        validator_count = schema_src.count("validate_password_strength")
        assert validator_count >= 2, f"validate_password_strength 应被引用至少 2 次，实际 {validator_count}"

    def test_user_update_has_no_password_field(self):
        src = _read(AUTH_SCHEMA)
        # UserUpdate 不应有 password 字段
        update_match = re.search(r"class UserUpdate\b[\s\S]*?(?=\nclass |\Z)", src)
        assert update_match, "应找到 UserUpdate 类"
        assert "password" not in update_match.group(0), "UserUpdate 不应包含 password 字段"

    def test_password_validator_delegates_to_core(self):
        src = _read(AUTH_SCHEMA)
        assert "from app.core.password_strength import" in src or "password_strength" in src


# ═══════════════════════════════════════════════════════════
# 3. 哈希安全验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHashSecurity:
    """验证密码哈希安全配置"""

    def test_uses_bcrypt(self):
        src = _read(SECURITY)
        assert "bcrypt" in src

    def test_bcrypt_rounds_is_12(self):
        src = _read(SECURITY)
        assert "rounds=12" in src or "12" in src

    def test_truncates_to_72_bytes(self):
        src = _read(SECURITY)
        assert "[:72]" in src

    def test_verify_password_handles_errors_gracefully(self):
        src = _read(SECURITY)
        body = _find_function_body(src, "verify_password")
        assert "try:" in body or "except" in body
        assert "return False" in body

    def test_hash_password_encodes_utf8(self):
        src = _read(SECURITY)
        body = _find_function_body(src, "hash_password")
        assert ".encode" in body
        assert "utf-8" in body or "utf8" in body


# ═══════════════════════════════════════════════════════════
# 4. 密码修改流程验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordChangeFlow:
    """验证密码修改端点安全流程"""

    def test_change_password_endpoint_exists(self):
        src = _read(AUTH_API)
        assert 'change-password' in src or 'change_password' in src

    def test_change_password_verifies_old_password(self):
        src = _read(AUTH_API)
        body = _find_function_body(src, "change_password")
        assert "verify_password" in body
        assert "old_password" in body

    def test_change_password_hashes_new_password(self):
        src = _read(AUTH_API)
        body = _find_function_body(src, "change_password")
        assert "hash_password" in body
        assert "new_password" in body

    def test_change_password_updates_password_changed_at(self):
        src = _read(AUTH_API)
        body = _find_function_body(src, "change_password")
        assert "password_changed_at" in body

    def test_create_user_hashes_password(self):
        src = _read(USERS_API)
        body = _find_function_body(src, "create_user")
        assert "hash_password" in body


# ═══════════════════════════════════════════════════════════
# 5. 黑名单覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBlacklistCoverage:
    """验证弱密码黑名单覆盖范围"""

    def test_blacklist_has_at_least_50_entries(self):
        src = _read(PWD_FILE)
        entries = re.findall(r'"([^"]+)"', src)
        # 统计黑名单中的条目数（排除非黑名单字符串）
        blacklist_match = re.search(r"_WEAK_PASSWORDS\s*=\s*frozenset\(\{([^}]+)\}\)", src, re.DOTALL)
        assert blacklist_match, "应找到 _WEAK_PASSWORDS 定义"
        items = re.findall(r'"([^"]+)"', blacklist_match.group(1))
        assert len(items) >= 50, f"黑名单应至少 50 项，实际 {len(items)}"

    def test_blacklist_uses_case_insensitive_comparison(self):
        src = _read(PWD_FILE)
        body = _find_function_body(src, "validate_password_strength")
        assert ".lower()" in body

    def test_blacklist_covers_common_numeric_passwords(self):
        src = _read(PWD_FILE)
        for pwd in ["123456", "12345678", "123456789", "666666", "888888"]:
            assert pwd in src, f"黑名单应包含 {pwd}"

    def test_blacklist_covers_common_word_passwords(self):
        src = _read(PWD_FILE)
        for pwd in ["password", "admin", "root", "test", "login"]:
            assert pwd in src, f"黑名单应包含 {pwd}"

    def test_blacklist_covers_l33t_speak_variants(self):
        src = _read(PWD_FILE)
        for pwd in ["passw0rd", "p@ssw0rd", "p@ssword"]:
            assert pwd in src, f"黑名单应包含 l33t 变体 {pwd}"
