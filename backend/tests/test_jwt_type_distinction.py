"""安全加固：JWT token type 区分验证测试
覆盖 access/refresh token 类型不可混用、type claim 正确性、iss/aud 一致性"""

import uuid

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token


def _decode(token: str) -> dict:
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
    )


class TestTokenTypeDistinction:
    """access token 与 refresh token 类型不可混用"""

    def test_access_token_type_is_access(self):
        payload = _decode(create_access_token("user-1"))
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        payload = _decode(create_refresh_token("user-1"))
        assert payload["type"] == "refresh"

    def test_access_and_refresh_have_different_types(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert access["type"] != refresh["type"]

    def test_access_token_cannot_be_used_as_refresh(self):
        """access token 的 type 不是 'refresh'，不能通过 refresh 端点验证"""
        token = create_access_token("user-1")
        payload = _decode(token)
        assert payload["type"] != "refresh"
        # 模拟 refresh 端点检查: if token_type != "refresh" → reject
        assert payload["type"] == "access"

    def test_refresh_token_not_access(self):
        """refresh token 的 type 不是 'access'"""
        token = create_refresh_token("user-1")
        payload = _decode(token)
        assert payload["type"] != "access"


class TestTokenClaimsConsistency:
    """两个 token 的共有 claim 一致性"""

    def test_both_have_same_iss(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert access["iss"] == refresh["iss"] == settings.JWT_ISSUER

    def test_both_have_same_aud(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert access["aud"] == refresh["aud"] == settings.JWT_AUDIENCE

    def test_both_have_same_sub(self):
        subject = str(uuid.uuid4())
        access = _decode(create_access_token(subject))
        refresh = _decode(create_refresh_token(subject))
        assert access["sub"] == refresh["sub"] == subject

    def test_both_have_jti(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert "jti" in access
        assert "jti" in refresh

    def test_jtis_are_different(self):
        """access 和 refresh token 的 jti 不同"""
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert access["jti"] != refresh["jti"]

    def test_both_have_iat(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert "iat" in access
        assert "iat" in refresh

    def test_refresh_expires_after_access(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert refresh["exp"] > access["exp"]

    def test_both_have_exp(self):
        access = _decode(create_access_token("user-1"))
        refresh = _decode(create_refresh_token("user-1"))
        assert "exp" in access
        assert "exp" in refresh


class TestTokenFormat:
    """token 格式验证"""

    def test_access_token_is_string(self):
        token = create_access_token("user-1")
        assert isinstance(token, str)

    def test_refresh_token_is_string(self):
        token = create_refresh_token("user-1")
        assert isinstance(token, str)

    def test_access_token_has_three_parts(self):
        """JWT 格式: header.payload.signature"""
        token = create_access_token("user-1")
        assert len(token.split(".")) == 3

    def test_refresh_token_has_three_parts(self):
        token = create_refresh_token("user-1")
        assert len(token.split(".")) == 3

    def test_multiple_access_tokens_have_unique_jti(self):
        tokens = [_decode(create_access_token("user-1")) for _ in range(5)]
        jtis = [t["jti"] for t in tokens]
        assert len(set(jtis)) == 5

    def test_multiple_refresh_tokens_have_unique_jti(self):
        tokens = [_decode(create_refresh_token("user-1")) for _ in range(5)]
        jtis = [t["jti"] for t in tokens]
        assert len(set(jtis)) == 5
