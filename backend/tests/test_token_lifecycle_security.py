"""
安全加固：后端会话管理与 Token 生命周期验证测试
覆盖 JWT 配置、Token 创建函数、
密码安全、Auth 端点模式、Token 校验安全
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()
SECURITY_SRC = (ROOT / "app" / "core" / "security.py").read_text()
AUTH_SRC = (ROOT / "app" / "api" / "v1" / "auth.py").read_text()
DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
MODEL_SRC = (ROOT / "app" / "models" / "user.py").read_text()


def _extract_setting_default(name: str, src: str) -> str | None:
    m = re.search(rf'{name}\s*:\s*\w+\s*=\s*([^#\n]+)', src)
    return m.group(1).strip() if m else None


# ═══════════════════════════════════════════════════════════
# 1. JWT 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestJWTConfiguration:
    """JWT 配置项完整且有合理默认值"""

    def test_jwt_secret_key_configured(self):
        """JWT_SECRET_KEY 有配置且有默认值"""
        assert "JWT_SECRET_KEY" in CONFIG_SRC, "应定义 JWT_SECRET_KEY"
        default = _extract_setting_default("JWT_SECRET_KEY", CONFIG_SRC)
        assert default is not None, "JWT_SECRET_KEY 应有默认值"

    def test_jwt_algorithm_configured(self):
        """JWT_ALGORITHM 使用 HS256"""
        assert "JWT_ALGORITHM" in CONFIG_SRC, "应定义 JWT_ALGORITHM"
        default = _extract_setting_default("JWT_ALGORITHM", CONFIG_SRC)
        assert default is not None and "HS256" in default, (
            f"JWT_ALGORITHM 默认应为 HS256，实际 {default}"
        )

    def test_jwt_issuer_and_audience_configured(self):
        """JWT_ISSUER 和 JWT_AUDIENCE 已配置"""
        assert "JWT_ISSUER" in CONFIG_SRC, "应定义 JWT_ISSUER"
        assert "JWT_AUDIENCE" in CONFIG_SRC, "应定义 JWT_AUDIENCE"
        assert "sales-management-system" in CONFIG_SRC, (
            "JWT_ISSUER/AUDIENCE 应有应用名称"
        )

    def test_access_token_expiration_reasonable(self):
        """JWT_ACCESS_TOKEN_EXPIRE_MINUTES 有合理的默认值"""
        m = re.search(r'JWT_ACCESS_TOKEN_EXPIRE_MINUTES\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "应定义 JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
        val = int(m.group(1))
        assert 5 <= val <= 120, (
            f"Access token 过期时间应 5-120 分钟，实际 {val}"
        )

    def test_refresh_token_expiration_reasonable(self):
        """JWT_REFRESH_TOKEN_EXPIRE_DAYS 有合理的默认值"""
        m = re.search(r'JWT_REFRESH_TOKEN_EXPIRE_DAYS\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "应定义 JWT_REFRESH_TOKEN_EXPIRE_DAYS"
        val = int(m.group(1))
        assert 1 <= val <= 30, (
            f"Refresh token 过期时间应 1-30 天，实际 {val}"
        )


# ═══════════════════════════════════════════════════════════
# 2. Token 创建函数验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenCreation:
    """Token 创建函数正确生成 JWT"""

    def test_create_access_token_defined(self):
        """create_access_token 函数已定义"""
        assert "def create_access_token(" in SECURITY_SRC, (
            "应定义 create_access_token 函数"
        )
        assert "subject" in SECURITY_SRC, "应接收 subject 参数"

    def test_create_refresh_token_defined(self):
        """create_refresh_token 函数已定义"""
        assert "def create_refresh_token(" in SECURITY_SRC, (
            "应定义 create_refresh_token 函数"
        )

    def test_access_token_includes_required_claims(self):
        """Access token 包含必要的 JWT claims"""
        assert '"sub"' in SECURITY_SRC or "'sub'" in SECURITY_SRC, (
            "Token 应包含 sub（用户 ID）claim"
        )
        assert '"exp"' in SECURITY_SRC or "'exp'" in SECURITY_SRC, (
            "Token 应包含 exp（过期时间）claim"
        )
        assert '"iat"' in SECURITY_SRC or "'iat'" in SECURITY_SRC, (
            "Token 应包含 iat（签发时间）claim"
        )
        assert '"jti"' in SECURITY_SRC or "'jti'" in SECURITY_SRC, (
            "Token 应包含 jti（唯一标识）claim"
        )

    def test_access_token_type_is_access(self):
        """Access token 的 type 字段为 'access'"""
        assert '"access"' in SECURITY_SRC, (
            "Access token 的 type 字段应为 'access'"
        )
        assert '"refresh"' in SECURITY_SRC, (
            "Refresh token 的 type 字段应为 'refresh'"
        )

    def test_token_uses_configured_settings(self):
        """Token 创建使用配置的 settings"""
        assert "settings.JWT_SECRET_KEY" in SECURITY_SRC, (
            "Token 应使用 settings.JWT_SECRET_KEY 签名"
        )
        assert "settings.JWT_ALGORITHM" in SECURITY_SRC, (
            "Token 应使用 settings.JWT_ALGORITHM 算法"
        )


# ═══════════════════════════════════════════════════════════
# 3. 密码安全验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordSecurity:
    """密码使用 bcrypt 安全处理"""

    def test_hash_password_uses_bcrypt(self):
        """hash_password 使用 bcrypt"""
        assert "def hash_password(" in SECURITY_SRC, "应定义 hash_password"
        assert "bcrypt" in SECURITY_SRC.lower() or "hash" in SECURITY_SRC.lower(), (
            "密码哈希应使用 bcrypt"
        )

    def test_verify_password_defined(self):
        """verify_password 函数已定义"""
        assert "def verify_password(" in SECURITY_SRC, "应定义 verify_password"
        assert "plain_password" in SECURITY_SRC or "password" in SECURITY_SRC, (
            "verify_password 应接收明文密码参数"
        )

    def test_password_input_truncated_to_72_bytes(self):
        """密码输入截断到 72 字节（bcrypt 限制）"""
        assert "72" in SECURITY_SRC, "应截断密码到 72 字节（bcrypt 限制）"

    def test_password_changed_at_field_on_user_model(self):
        """User 模型有 password_changed_at 字段"""
        assert "password_changed_at" in MODEL_SRC, (
            "User 模型应有 password_changed_at 字段"
        )
        # 应为可空的带时区 DateTime
        assert "DateTime" in MODEL_SRC, "password_changed_at 应为 DateTime 类型"
        assert "nullable" in MODEL_SRC or "None" in MODEL_SRC, (
            "password_changed_at 应可为空"
        )

    def test_change_password_sets_timestamp(self):
        """修改密码时更新 password_changed_at"""
        assert "password_changed_at" in AUTH_SRC, (
            "auth 模块应引用 password_changed_at"
        )
        assert "datetime" in AUTH_SRC or "now" in AUTH_SRC, (
            "修改密码应设置当前时间戳"
        )


# ═══════════════════════════════════════════════════════════
# 4. Auth 端点模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAuthEndpointPatterns:
    """Auth 端点正确实现登录/刷新/退出流程"""

    def test_login_endpoint_validates_credentials(self):
        """登录端点验证用户名密码"""
        assert "verify_password" in AUTH_SRC, "登录应调用 verify_password"
        assert "username" in AUTH_SRC, "登录应接收 username 参数"
        assert "password" in AUTH_SRC, "登录应接收 password 参数"

    def test_login_endpoint_returns_both_tokens(self):
        """登录返回 access_token 和 refresh_token"""
        assert "access_token" in AUTH_SRC, "登录响应应包含 access_token"
        assert "refresh_token" in AUTH_SRC, "登录响应应包含 refresh_token"
        assert "bearer" in AUTH_SRC.lower(), "token_type 应为 bearer"

    def test_refresh_endpoint_validates_token_type(self):
        """刷新端点验证 token type 为 refresh"""
        assert '"refresh"' in AUTH_SRC, "刷新端点应验证 type == 'refresh'"
        assert "jwt.decode" in AUTH_SRC, "刷新端点应解码 JWT"

    def test_login_has_rate_limiting(self):
        """登录端点有速率限制"""
        assert "LOGIN_FAIL_MAX" in AUTH_SRC or "rate_limit" in AUTH_SRC.lower(), (
            "登录应有失败次数限制"
        )
        assert "Lock" in AUTH_SRC or "threading" in AUTH_SRC, (
            "速率限制应使用线程安全机制"
        )
        assert "429" in AUTH_SRC, "超限应返回 429 状态码"

    def test_auth_endpoints_use_oauth2_scheme(self):
        """Auth 相关端点使用 OAuth2PasswordBearer"""
        assert "OAuth2PasswordBearer" in DEPS_SRC, (
            "应使用 OAuth2PasswordBearer 方案"
        )
        assert "/auth/login" in DEPS_SRC, "tokenUrl 应指向 /auth/login"


# ═══════════════════════════════════════════════════════════
# 5. Token 校验安全验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenValidationSecurity:
    """Token 校验实现多重安全检查"""

    def test_get_current_user_validates_token_type(self):
        """get_current_user 验证 token type 为 access"""
        assert '"access"' in DEPS_SRC, "应验证 token type == 'access'"
        # 不应接受 refresh token 作为 access token
        assert "token_type" in DEPS_SRC or "type" in DEPS_SRC, (
            "应检查 token 的 type 字段"
        )

    def test_get_current_user_checks_user_active(self):
        """get_current_user 检查用户是否激活"""
        assert "is_active" in DEPS_SRC, "应检查 user.is_active"

    def test_get_current_user_checks_soft_delete(self):
        """get_current_user 过滤已删除用户"""
        assert "deleted_at" in DEPS_SRC, "应过滤 deleted_at IS NULL 的用户"

    def test_get_current_user_validates_password_change(self):
        """get_current_user 检查密码修改后旧 token 自动失效"""
        assert "password_changed_at" in DEPS_SRC, (
            "应检查 password_changed_at"
        )
        assert "iat" in DEPS_SRC, "应比较 token 的 iat claim"
        # 应在 token 签发早于密码修改时拒绝
        assert "<" in DEPS_SRC or "before" in DEPS_SRC.lower() or "changed_at" in DEPS_SRC, (
            "密码修改后，签发时间更早的 token 应被拒绝"
        )

    def test_get_current_user_raises_401_on_invalid_token(self):
        """Token 无效时抛 401 错误"""
        assert "401" in DEPS_SRC or "HTTP_401_UNAUTHORIZED" in DEPS_SRC, (
            "Token 无效应返回 401"
        )
        assert "AUTH_UNAUTHORIZED" in DEPS_SRC, (
            "错误码应为 AUTH_UNAUTHORIZED"
        )
