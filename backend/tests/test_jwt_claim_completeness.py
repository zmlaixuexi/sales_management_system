"""
安全加固：后端 JWT Token Claim 完整性静态验证测试
覆盖 Token 创建 Claim 一致性、验证端点 Claim 校验、
签发者与受众配置、过期时间配置、Token 安全字段
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECURITY = (ROOT / "app" / "core" / "security.py").read_text()
CONFIG = (ROOT / "app" / "core" / "config.py").read_text()
AUTH = (ROOT / "app" / "api" / "v1" / "auth.py").read_text()
DEPS = (ROOT / "app" / "api" / "deps.py").read_text()

REQUIRED_CLAIMS = {"sub", "exp", "iat", "jti", "type", "iss", "aud"}


def _token_encode_block(src: str, func_name: str) -> str:
    """提取 token 创建函数体"""
    m = re.search(rf"^def {func_name}\b", src, re.MULTILINE)
    if not m:
        return ""
    rest = src[m.start():]
    next_def = re.search(r"\ndef \w", rest[1:])
    return rest[1:1 + next_def.start()] if next_def else rest[1:]


# ═══════════════════════════════════════════════════════════
# 1. Token 创建 Claim 一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenCreationClaims:
    """access 和 refresh token 包含相同的 claim 结构"""

    def test_access_token_has_all_required_claims(self):
        body = _token_encode_block(SECURITY, "create_access_token")
        for claim in REQUIRED_CLAIMS:
            assert f'"{claim}"' in body, f"access token 应包含 {claim} claim"

    def test_refresh_token_has_all_required_claims(self):
        body = _token_encode_block(SECURITY, "create_refresh_token")
        for claim in REQUIRED_CLAIMS:
            assert f'"{claim}"' in body, f"refresh token 应包含 {claim} claim"

    def test_both_tokens_use_same_claims_structure(self):
        """两种 token 的 claim 键完全一致"""
        access_body = _token_encode_block(SECURITY, "create_access_token")
        refresh_body = _token_encode_block(SECURITY, "create_refresh_token")
        access_claims = set(re.findall(r'"(\w+)":', access_body))
        refresh_claims = set(re.findall(r'"(\w+)":', refresh_body))
        assert access_claims == refresh_claims, (
            f"access/refresh claim 不一致: {access_claims} vs {refresh_claims}"
        )

    def test_access_type_is_access(self):
        body = _token_encode_block(SECURITY, "create_access_token")
        assert '"type": "access"' in body, "access token type 应为 'access'"

    def test_refresh_type_is_refresh(self):
        body = _token_encode_block(SECURITY, "create_refresh_token")
        assert '"type": "refresh"' in body, "refresh token type 应为 'refresh'"


# ═══════════════════════════════════════════════════════════
# 2. Token 验证端点 Claim 校验验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenVerificationClaims:
    """验证端点检查 token claim 完整性"""

    def test_deps_validates_subject_claim(self):
        assert '"sub"' in DEPS, "get_current_user 应验证 sub claim"

    def test_deps_validates_type_claim(self):
        assert '"type"' in DEPS, "get_current_user 应验证 type claim"
        assert "access" in DEPS, "get_current_user 应检查 type == access"

    def test_deps_validates_issuer_and_audience(self):
        assert "audience" in DEPS, "get_current_user 应验证 audience"
        assert "issuer" in DEPS, "get_current_user 应验证 issuer"

    def test_auth_refresh_validates_type(self):
        assert "refresh" in AUTH, "refresh 端点应检查 type == refresh"

    def test_both_verification_use_same_algorithm(self):
        """验证和创建使用相同算法"""
        assert "algorithms=" in DEPS, "验证应指定算法"
        assert "JWT_ALGORITHM" in DEPS, "验证应使用配置的算法"
        assert "JWT_ALGORITHM" in SECURITY, "创建应使用配置的算法"


# ═══════════════════════════════════════════════════════════
# 3. 签发者与受众配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestIssuerAudienceConfig:
    """JWT 签发者和受众配置一致"""

    def test_issuer_config_defined(self):
        assert "JWT_ISSUER" in CONFIG, "应定义 JWT_ISSUER 配置"
        assert "sales-management-system" in CONFIG, "JWT_ISSUER 应有默认值"

    def test_audience_config_defined(self):
        assert "JWT_AUDIENCE" in CONFIG, "应定义 JWT_AUDIENCE 配置"
        assert "sales-management-system" in CONFIG, "JWT_AUDIENCE 应有默认值"

    def test_token_creation_uses_config_issuer(self):
        assert "settings.JWT_ISSUER" in SECURITY, "token 创建应使用配置的 issuer"

    def test_token_creation_uses_config_audience(self):
        assert "settings.JWT_AUDIENCE" in SECURITY, "token 创建应使用配置的 audience"

    def test_verification_uses_config_issuer_and_audience(self):
        assert "settings.JWT_ISSUER" in DEPS, "验证应使用配置的 issuer"
        assert "settings.JWT_AUDIENCE" in DEPS, "验证应使用配置的 audience"


# ═══════════════════════════════════════════════════════════
# 4. 过期时间配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExpiryConfig:
    """Token 过期时间配置合理"""

    def test_access_token_expiry_config(self):
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in CONFIG
        assert "30" in CONFIG, "access token 默认过期时间应为 30 分钟"

    def test_refresh_token_expiry_config(self):
        assert "JWT_REFRESH_TOKEN_EXPIRE_DAYS" in CONFIG
        assert "7" in CONFIG, "refresh token 默认过期时间应为 7 天"

    def test_access_uses_minutes(self):
        body = _token_encode_block(SECURITY, "create_access_token")
        assert "minutes" in body, "access token 应使用分钟为单位"

    def test_refresh_uses_days(self):
        body = _token_encode_block(SECURITY, "create_refresh_token")
        assert "days" in body, "refresh token 应使用天为单位"

    def test_expiry_has_validator(self):
        """过期时间有值域校验"""
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in CONFIG
        assert "JWT_REFRESH_TOKEN_EXPIRE_DAYS" in CONFIG
        # 检查有 field_validator
        assert "field_validator" in CONFIG, "过期时间应有字段验证器"


# ═══════════════════════════════════════════════════════════
# 5. Token 安全字段验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTokenSecurityFields:
    """Token 包含安全相关字段"""

    def test_jti_uses_uuid4(self):
        """JTI 使用 UUID4 确保唯一性"""
        assert "uuid.uuid4()" in SECURITY, "jti 应使用 uuid4"

    def test_both_tokens_have_unique_jti(self):
        """两种 token 各自生成独立 jti"""
        access_body = _token_encode_block(SECURITY, "create_access_token")
        refresh_body = _token_encode_block(SECURITY, "create_refresh_token")
        assert "uuid.uuid4()" in access_body, "access token 应生成独立 jti"
        assert "uuid.uuid4()" in refresh_body, "refresh token 应生成独立 jti"

    def test_iat_uses_utc(self):
        """iat 使用 UTC 时间"""
        assert "UTC" in SECURITY, "token 时间应使用 UTC"

    def test_secret_key_validated(self):
        """JWT 密钥有安全验证"""
        assert "JWT_SECRET_KEY" in CONFIG
        assert "不能为空" in CONFIG or "不能少于" in CONFIG, "密钥应有安全校验"

    def test_algorithm_is_hs256(self):
        """算法为 HS256"""
        assert "HS256" in CONFIG, "默认算法应为 HS256"
        assert "JWT_ALGORITHM" in SECURITY, "创建 token 应使用配置的算法"
