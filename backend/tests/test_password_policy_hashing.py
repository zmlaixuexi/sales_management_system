"""
安全加固：后端密码策略与哈希配置静态验证测试
覆盖哈希函数安全性、密码强度策略、账户锁定配置、
密码变更端点安全、哈希配置与参数约束
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECURITY_SRC = (ROOT / "app" / "core" / "security.py").read_text()
PASSWORD_SRC = (ROOT / "app" / "core" / "password_strength.py").read_text()
CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()
AUTH_SRC = (ROOT / "app" / "api" / "v1" / "auth.py").read_text()
SCHEMA_SRC = (ROOT / "app" / "schemas" / "auth.py").read_text()


# ═══════════════════════════════════════════════════════════
# 1. 哈希函数安全性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHashFunctionSecurity:
    """密码哈希使用 bcrypt，安全参数正确"""

    def test_hash_password_uses_bcrypt(self):
        """hash_password 使用 bcrypt 库"""
        assert "bcrypt" in SECURITY_SRC, "应使用 bcrypt 库进行密码哈希"
        assert "bcrypt.hashpw" in SECURITY_SRC, "hash_password 应调用 bcrypt.hashpw"

    def test_hash_password_uses_gensalt_with_rounds(self):
        """bcrypt.gensalt 指定 rounds 参数（cost factor >= 12）"""
        m = re.search(r"gensalt\(rounds=(\d+)\)", SECURITY_SRC)
        assert m, "bcrypt.gensalt 应指定 rounds 参数"
        rounds = int(m.group(1))
        assert rounds >= 12, f"bcrypt rounds 应 >= 12，当前 {rounds}"

    def test_hash_password_truncates_at_72_bytes(self):
        """密码在哈希前截断至 72 字节（bcrypt 限制）"""
        assert "[:72]" in SECURITY_SRC, "应在哈希前截断密码至 72 字节"

    def test_verify_password_catches_exceptions(self):
        """verify_password 捕获异常返回 False（防止时序攻击信息泄露）"""
        assert "bcrypt.checkpw" in SECURITY_SRC, "verify_password 应调用 bcrypt.checkpw"
        assert "except" in SECURITY_SRC, "verify_password 应捕获异常"
        # 应捕获 ValueError, TypeError 等异常
        assert "ValueError" in SECURITY_SRC or "Exception" in SECURITY_SRC, (
            "verify_password 应捕获 ValueError 等异常"
        )

    def test_hash_output_is_utf8_decoded_string(self):
        """hash_password 返回 UTF-8 解码的字符串（非 bytes）"""
        assert '.decode("utf-8")' in SECURITY_SRC, "哈希结果应 decode('utf-8') 返回字符串"


# ═══════════════════════════════════════════════════════════
# 2. 密码强度策略验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordStrengthPolicy:
    """密码强度验证规则完整"""

    def test_requires_uppercase(self):
        """密码必须包含大写字母"""
        assert r"[A-Z]" in PASSWORD_SRC, "密码策略应要求大写字母"

    def test_requires_lowercase(self):
        """密码必须包含小写字母"""
        assert r"[a-z]" in PASSWORD_SRC, "密码策略应要求小写字母"

    def test_requires_digit(self):
        """密码必须包含数字"""
        assert r"\d" in PASSWORD_SRC, "密码策略应要求数字"

    def test_requires_special_char(self):
        """密码必须包含特殊字符"""
        assert r"[^a-zA-Z0-9]" in PASSWORD_SRC, "密码策略应要求特殊字符"

    def test_weak_password_blacklist_exists(self):
        """存在弱密码黑名单"""
        assert "_WEAK_PASSWORDS" in PASSWORD_SRC, "应定义弱密码黑名单"
        assert "frozenset" in PASSWORD_SRC, "弱密码黑名单应为 frozenset"
        # 黑名单应包含常见弱密码
        assert '"password"' in PASSWORD_SRC, "黑名单应包含 'password'"
        assert '"123456"' in PASSWORD_SRC, "黑名单应包含 '123456'"
        assert '"admin"' in PASSWORD_SRC, "黑名单应包含 'admin'"


# ═══════════════════════════════════════════════════════════
# 3. 账户锁定配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAccountLockConfig:
    """账户锁定与 IP 限流配置正确"""

    def test_account_lock_max_failures_configured(self):
        """ACCOUNT_LOCK_MAX_FAILURES 配置存在且 <= 10"""
        m = re.search(r"ACCOUNT_LOCK_MAX_FAILURES\s*:\s*int\s*=\s*(\d+)", CONFIG_SRC)
        assert m, "应配置 ACCOUNT_LOCK_MAX_FAILURES"
        val = int(m.group(1))
        assert 3 <= val <= 10, f"ACCOUNT_LOCK_MAX_FAILURES 应在 3-10 之间，当前 {val}"

    def test_account_lock_window_configured(self):
        """ACCOUNT_LOCK_WINDOW_SECONDS 配置存在且 >= 300"""
        m = re.search(r"ACCOUNT_LOCK_WINDOW_SECONDS\s*:\s*int\s*=\s*(\d+)", CONFIG_SRC)
        assert m, "应配置 ACCOUNT_LOCK_WINDOW_SECONDS"
        val = int(m.group(1))
        assert val >= 300, f"ACCOUNT_LOCK_WINDOW_SECONDS 应 >= 300，当前 {val}"

    def test_ip_rate_limit_configured(self):
        """LOGIN_FAIL_MAX 和 LOGIN_FAIL_WINDOW_SECONDS 配置存在"""
        assert "LOGIN_FAIL_MAX" in CONFIG_SRC, "应配置 LOGIN_FAIL_MAX"
        assert "LOGIN_FAIL_WINDOW_SECONDS" in CONFIG_SRC, "应配置 LOGIN_FAIL_WINDOW_SECONDS"
        m_max = re.search(r"LOGIN_FAIL_MAX\s*:\s*int\s*=\s*(\d+)", CONFIG_SRC)
        assert m_max, "LOGIN_FAIL_MAX 应有默认值"
        val = int(m_max.group(1))
        assert val >= 3, f"LOGIN_FAIL_MAX 应 >= 3，当前 {val}"

    def test_lock_uses_thread_lock(self):
        """锁定机制使用线程锁保证并发安全"""
        assert "Lock" in AUTH_SRC, "应使用 threading.Lock"
        assert "_login_fail_lock" in AUTH_SRC, "应定义 IP 限流锁"
        assert "_account_fail_lock" in AUTH_SRC, "应定义账户锁定锁"
        assert "with _login_fail_lock" in AUTH_SRC, "IP 限流应使用 with Lock"
        assert "with _account_fail_lock" in AUTH_SRC, "账户锁定应使用 with Lock"

    def test_lock_returns_429_status(self):
        """锁定触发返回 429 状态码"""
        assert "429" in AUTH_SRC, "锁定触发应返回 429"
        assert "RATE_LIMIT_EXCEEDED" in AUTH_SRC, "IP 限流应使用 RATE_LIMIT_EXCEEDED 错误码"
        assert "ACCOUNT_LOCKED" in AUTH_SRC, "账户锁定应使用 ACCOUNT_LOCKED 错误码"


# ═══════════════════════════════════════════════════════════
# 4. 密码变更端点安全验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordChangeSecurity:
    """密码变更端点安全措施完整"""

    def test_change_password_verifies_old_password(self):
        """修改密码前验证旧密码"""
        assert "verify_password" in AUTH_SRC, "密码变更应验证旧密码"
        # 在 change-password 端点区域内
        m = re.search(r'@router\.post\("/change-password"\)', AUTH_SRC)
        assert m, "应有 change-password 端点"
        body = AUTH_SRC[m.end():]
        # 找下一个路由或文件结尾
        next_route = re.search(r"\n@router\.", body)
        func_body = body[:next_route.start()] if next_route else body
        assert "verify_password" in func_body, "密码变更应验证旧密码"
        assert "INVALID_PASSWORD" in func_body, "旧密码错误应返回 INVALID_PASSWORD"

    def test_change_password_requires_auth(self):
        """密码变更端点需要认证"""
        m = re.search(r'@router\.post\("/change-password"\)', AUTH_SRC)
        assert m, "应有 change-password 端点"
        body = AUTH_SRC[m.end():]
        assert "get_current_user" in body[:1000], "密码变更端点应依赖 get_current_user"

    def test_change_password_hashes_new_password(self):
        """新密码使用 hash_password 哈希存储"""
        m = re.search(r'@router\.post\("/change-password"\)', AUTH_SRC)
        assert m, "应有 change-password 端点"
        body = AUTH_SRC[m.end():]
        next_route = re.search(r"\n@router\.", body)
        func_body = body[:next_route.start()] if next_route else body
        assert "hash_password" in func_body, "新密码应使用 hash_password 哈希"

    def test_change_password_records_timestamp(self):
        """密码变更记录时间戳（用于 refresh token 失效判断）"""
        m = re.search(r'@router\.post\("/change-password"\)', AUTH_SRC)
        assert m, "应有 change-password 端点"
        body = AUTH_SRC[m.end():]
        next_route = re.search(r"\n@router\.", body)
        func_body = body[:next_route.start()] if next_route else body
        assert "password_changed_at" in func_body, "密码变更应记录 password_changed_at"

    def test_change_password_logs_audit(self):
        """密码变更记录审计日志"""
        m = re.search(r'@router\.post\("/change-password"\)', AUTH_SRC)
        assert m, "应有 change-password 端点"
        body = AUTH_SRC[m.end():]
        next_route = re.search(r"\n@router\.", body)
        func_body = body[:next_route.start()] if next_route else body
        assert "log_action" in func_body, "密码变更应记录审计日志"
        assert "password_change" in func_body, "审计 action 应为 password_change"


# ═══════════════════════════════════════════════════════════
# 5. Schema 密码验证集成验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSchemaPasswordIntegration:
    """Pydantic Schema 集成密码强度验证"""

    def test_user_create_validates_password_strength(self):
        """UserCreate Schema 调用密码强度验证"""
        assert "validate_password_strength" in SCHEMA_SRC, "Schema 应导入密码强度验证"
        # UserCreate 应有 password 字段的 field_validator
        m = re.search(r"class UserCreate", SCHEMA_SRC)
        assert m, "应定义 UserCreate"
        # 在 UserCreate 类体中查找 password validator
        rest = SCHEMA_SRC[m.end():]
        next_class = re.search(r"\nclass \w", rest)
        class_body = rest[:next_class.start()] if next_class else rest
        assert "password" in class_body, "UserCreate 应有 password 字段"
        assert "validate_password_strength" in class_body, "UserCreate 应验证密码强度"

    def test_change_password_validates_new_password_strength(self):
        """ChangePasswordRequest Schema 验证新密码强度"""
        m = re.search(r"class ChangePasswordRequest", SCHEMA_SRC)
        assert m, "应定义 ChangePasswordRequest"
        rest = SCHEMA_SRC[m.end():]
        next_class = re.search(r"\nclass \w", rest)
        class_body = rest[:next_class.start()] if next_class else rest
        assert "validate_password_strength" in class_body, "ChangePasswordRequest 应验证新密码强度"

    def test_password_min_length_at_least_6(self):
        """密码字段最小长度至少 6"""
        # UserCreate.password 和 ChangePasswordRequest.new_password
        m1 = re.search(r"class UserCreate.*?password.*?min_length=(\d+)", SCHEMA_SRC, re.DOTALL)
        assert m1, "UserCreate 应有 password 字段并设 min_length"
        assert int(m1.group(1)) >= 6, f"UserCreate password 最小长度应 >= 6，当前 {m1.group(1)}"
        m2 = re.search(r"class ChangePasswordRequest.*?new_password.*?min_length=(\d+)", SCHEMA_SRC, re.DOTALL)
        assert m2, "ChangePasswordRequest 应有 new_password 字段并设 min_length"
        assert int(m2.group(1)) >= 6, f"ChangePasswordRequest new_password 最小长度应 >= 6，当前 {m2.group(1)}"

    def test_password_max_length_defined(self):
        """密码字段有最大长度限制"""
        assert 'max_length=100' in SCHEMA_SRC, "密码字段应有最大长度限制"

    def test_login_request_does_not_validate_strength(self):
        """LoginRequest 不做密码强度验证（仅长度校验）"""
        m = re.search(r"class LoginRequest", SCHEMA_SRC)
        assert m, "应定义 LoginRequest"
        rest = SCHEMA_SRC[m.end():]
        next_class = re.search(r"\nclass \w", rest)
        class_body = rest[:next_class.start()] if next_class else rest
        assert "validate_password_strength" not in class_body, (
            "LoginRequest 不应验证密码强度（仅校验长度）"
        )
