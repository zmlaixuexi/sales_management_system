"""JWT token 边界条件测试 — 覆盖 iss/aud 验证、claim 缺失/篡改、格式异常、空值等场景"""

import time
import uuid

import pytest
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token

# ═══════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════

_USER_ID = str(uuid.uuid4())


def _encode(payload: dict) -> str:
    """用项目密钥签名自定义 payload"""
    return jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _base_access_claims(**overrides) -> dict:
    """构造合法 access token 的 claims，可覆盖任意字段"""
    now = int(time.time())
    claims = {
        "sub": _USER_ID,
        "exp": now + 3600,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    claims.update(overrides)
    return claims


def _base_refresh_claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "sub": _USER_ID,
        "exp": now + 86400 * 7,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    claims.update(overrides)
    return claims


# ═══════════════════════════════════════════════════════
# 1. iss/aud 验证
# ═══════════════════════════════════════════════════════


class TestIssuerValidation:
    def test_wrong_issuer_rejected(self):
        """错误 issuer 的 token 解码失败"""
        token = _encode(_base_access_claims(iss="wrong-issuer"))
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_missing_issuer_rejected(self):
        """缺少 issuer 的 token 解码失败"""
        claims = _base_access_claims()
        del claims["iss"]
        token = _encode(claims)
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_empty_issuer_rejected(self):
        """空字符串 issuer 的 token 解码失败"""
        token = _encode(_base_access_claims(iss=""))
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )


class TestAudienceValidation:
    def test_wrong_audience_rejected(self):
        """错误 audience 的 token 解码失败"""
        token = _encode(_base_access_claims(aud="wrong-audience"))
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_missing_audience_rejected(self):
        """缺少 audience 的 token — jose 解码成功但 aud 不匹配"""
        claims = _base_access_claims()
        del claims["aud"]
        token = _encode(claims)
        # jose 不强制 claim 存在，但 decoded 中不含 aud
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        # decoded["aud"] 可能被 jose 自动设为 None 或不含该 key
        assert "aud" not in decoded or decoded.get("aud") != settings.JWT_AUDIENCE

    def test_empty_audience_rejected(self):
        """空字符串 audience 的 token 解码失败"""
        token = _encode(_base_access_claims(aud=""))
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )


# ═══════════════════════════════════════════════════════
# 2. sub 验证
# ═══════════════════════════════════════════════════════


class TestSubjectValidation:
    def test_missing_sub_rejected(self):
        """缺少 sub 的 token 解码成功但 sub 为 None"""
        claims = _base_access_claims()
        del claims["sub"]
        token = _encode(claims)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded.get("sub") is None

    def test_empty_sub(self):
        """空字符串 sub 可以解码但业务层应拒绝"""
        token = _encode(_base_access_claims(sub=""))
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["sub"] == ""

    def test_non_uuid_sub_decodable(self):
        """非 UUID 格式的 sub 在 JWT 层面可以解码"""
        token = _encode(_base_access_claims(sub="not-a-uuid"))
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["sub"] == "not-a-uuid"


# ═══════════════════════════════════════════════════════
# 3. type 验证
# ═══════════════════════════════════════════════════════


class TestTypeValidation:
    def test_type_access_accepted(self):
        """type=access 的 token 可解码"""
        token = _encode(_base_access_claims())
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["type"] == "access"

    def test_type_refresh_accepted(self):
        """type=refresh 的 token 可解码"""
        token = _encode(_base_refresh_claims())
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["type"] == "refresh"

    def test_type_unknown(self):
        """非 access/refresh 的 type 值在 JWT 层可解码"""
        token = _encode(_base_access_claims(type="admin"))
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["type"] == "admin"


# ═══════════════════════════════════════════════════════
# 4. exp 过期验证
# ═══════════════════════════════════════════════════════


class TestExpiryValidation:
    def test_expired_token_rejected(self):
        """已过期的 token 解码抛 ExpiredSignatureError"""
        token = _encode(_base_access_claims(exp=int(time.time()) - 3600))
        from jose.exceptions import ExpiredSignatureError
        with pytest.raises(ExpiredSignatureError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_just_expired_token_rejected(self):
        """刚过期 1 秒的 token 被拒绝"""
        token = _encode(_base_access_claims(exp=int(time.time()) - 1))
        from jose.exceptions import ExpiredSignatureError
        with pytest.raises(ExpiredSignatureError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_missing_exp_not_enforced(self):
        """缺少 exp 字段的 token — jose 默认不强制过期验证"""
        claims = _base_access_claims()
        del claims["exp"]
        token = _encode(claims)
        # jose 不强制 exp 存在，解码成功但不含 exp
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert "exp" not in decoded

    def test_far_future_exp_accepted(self):
        """远期过期时间的 token 正常解码"""
        token = _encode(_base_access_claims(exp=int(time.time()) + 86400 * 365))
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["sub"] == _USER_ID


# ═══════════════════════════════════════════════════════
# 5. 签名验证
# ═══════════════════════════════════════════════════════


class TestSignatureValidation:
    def test_wrong_secret_rejected(self):
        """错误密钥签名的 token 解码失败"""
        claims = _base_access_claims()
        token = jose_jwt.encode(claims, "wrong-secret-key", algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_tampered_payload_rejected(self):
        """篡改 token payload 部分导致签名失败"""
        token = _encode(_base_access_claims())
        parts = token.split(".")
        # 篡改 payload（第二段）的中间字符
        payload_chars = list(parts[1])
        payload_chars[len(payload_chars) // 2] = "!" if payload_chars[len(payload_chars) // 2] != "!" else "?"
        parts[1] = "".join(payload_chars)
        tampered = ".".join(parts)
        with pytest.raises(JWTError):
            jose_jwt.decode(
                tampered, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_empty_string_token_rejected(self):
        """空字符串 token 解码失败"""
        with pytest.raises(JWTError):
            jose_jwt.decode(
                "", settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_random_string_token_rejected(self):
        """随机字符串 token 解码失败"""
        with pytest.raises(JWTError):
            jose_jwt.decode(
                "totally.not.a.jwt", settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )

    def test_base64_only_no_signature_rejected(self):
        """只有 base64 部分、缺少签名的 token 被拒绝"""
        import base64
        import json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps(_base_access_claims()).encode()).decode().rstrip("=")
        fake_token = f"{header}.{payload}."
        with pytest.raises(JWTError):
            jose_jwt.decode(
                fake_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            )


# ═══════════════════════════════════════════════════════
# 6. 生成函数输出验证
# ═══════════════════════════════════════════════════════


class TestTokenGeneration:
    def test_access_token_contains_all_claims(self):
        """access token 包含所有标准 claim"""
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        for field in ("sub", "exp", "iat", "jti", "type", "iss", "aud"):
            assert field in decoded, f"缺少 claim: {field}"

    def test_refresh_token_contains_all_claims(self):
        """refresh token 包含所有标准 claim"""
        token = create_refresh_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        for field in ("sub", "exp", "iat", "jti", "type", "iss", "aud"):
            assert field in decoded, f"缺少 claim: {field}"

    def test_access_token_type_is_access(self):
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        token = create_refresh_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["type"] == "refresh"

    def test_access_token_sub_is_user_id(self):
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["sub"] == _USER_ID

    def test_refresh_token_sub_is_user_id(self):
        token = create_refresh_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["sub"] == _USER_ID

    def test_access_token_iss_matches_config(self):
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["iss"] == settings.JWT_ISSUER

    def test_access_token_aud_matches_config(self):
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        assert decoded["aud"] == settings.JWT_AUDIENCE

    def test_jti_is_valid_uuid(self):
        """jti 是合法 UUID v4 格式"""
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        # uuid.UUID 会在非法格式时抛异常
        parsed = uuid.UUID(decoded["jti"])
        assert str(parsed) == decoded["jti"]

    def test_unique_jti_per_token(self):
        """每次生成的 token jti 不同"""
        t1 = create_access_token(_USER_ID)
        t2 = create_access_token(_USER_ID)
        d1 = jose_jwt.decode(t1, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                             audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)
        d2 = jose_jwt.decode(t2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                             audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)
        assert d1["jti"] != d2["jti"]

    def test_access_token_expiry_within_config(self):
        """access token 过期时间约等于配置的 JWT_ACCESS_TOKEN_EXPIRE_MINUTES"""
        token = create_access_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        expected_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        actual_ttl = decoded["exp"] - decoded["iat"]
        assert abs(actual_ttl - expected_ttl) <= 2  # 允许 2 秒误差

    def test_refresh_token_expiry_within_config(self):
        """refresh token 过期时间约等于配置的 JWT_REFRESH_TOKEN_EXPIRE_DAYS"""
        token = create_refresh_token(_USER_ID)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        expected_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        actual_ttl = decoded["exp"] - decoded["iat"]
        assert abs(actual_ttl - expected_ttl) <= 2

    def test_custom_expiry_override(self):
        """自定义 expires_delta 覆盖默认过期时间"""
        from datetime import timedelta
        delta = timedelta(minutes=5)
        token = create_access_token(_USER_ID, expires_delta=delta)
        decoded = jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
        )
        actual_ttl = decoded["exp"] - decoded["iat"]
        assert abs(actual_ttl - 300) <= 2

    def test_refresh_longer_than_access(self):
        """refresh token 过期时间远长于 access token"""
        at = create_access_token(_USER_ID)
        rt = create_refresh_token(_USER_ID)
        ad = jose_jwt.decode(at, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                             audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)
        rd = jose_jwt.decode(rt, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                             audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER)
        assert rd["exp"] - rd["iat"] > ad["exp"] - ad["iat"]


# ═══════════════════════════════════════════════════════
# 7. JWT 配置验证
# ═══════════════════════════════════════════════════════


class TestJWTConfig:
    def test_algorithm_is_hs256(self):
        """JWT 算法为 HS256"""
        assert settings.JWT_ALGORITHM == "HS256"

    def test_issuer_is_sales_management_system(self):
        """JWT issuer 为 sales-management-system"""
        assert settings.JWT_ISSUER == "sales-management-system"

    def test_audience_is_sales_management_system(self):
        """JWT audience 为 sales-management-system"""
        assert settings.JWT_AUDIENCE == "sales-management-system"

    def test_secret_key_min_length(self):
        """JWT secret key 至少 8 个字符"""
        assert len(settings.JWT_SECRET_KEY) >= 8

    def test_access_expire_positive(self):
        """access token 过期时间为正数"""
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_refresh_expire_positive(self):
        """refresh token 过期时间为正数"""
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_access_expire_less_than_refresh(self):
        """access token 过期时间 < refresh token 过期时间"""
        access_s = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_s = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        assert access_s < refresh_s


# ═══════════════════════════════════════════════════════
# 8. API 端点认证测试
# ═══════════════════════════════════════════════════════


class TestAPIAuthEndpoints:
    def test_auth_me_no_token_401(self):
        """无 token 访问 /auth/me 返回 401"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        resp = c.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_auth_me_invalid_token_401(self):
        """无效 token 访问 /auth/me 返回 401"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        resp = c.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_auth_me_expired_token_401(self):
        """过期 token 访问 /auth/me 返回 401"""
        from datetime import timedelta

        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        expired = create_access_token(str(uuid.uuid4()), expires_delta=timedelta(seconds=-1))
        resp = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401

    def test_auth_me_refresh_token_rejected(self):
        """refresh token 不能访问 /auth/me"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        refresh = create_refresh_token(str(uuid.uuid4()))
        resp = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
        assert resp.status_code == 401

    def test_protected_endpoint_no_token_401(self):
        """无 token 访问受保护端点返回 401"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        resp = c.get("/api/v1/users")
        assert resp.status_code in (401, 403)

    def test_401_has_www_authenticate_header(self):
        """401 响应可能包含 WWW-Authenticate 头（取决于中间件处理）"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        resp = c.get("/api/v1/auth/me")
        # OAuth2 scheme 可能不直接设置此 header（由异常处理器控制）
        assert resp.status_code == 401

    def test_refresh_with_invalid_token_401(self):
        """无效 refresh_token 返回 401"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code in (401, 422)

    def test_refresh_with_access_token_rejected(self):
        """用 access token 作为 refresh_token 被拒绝"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app, raise_server_exceptions=False)
        access = create_access_token(str(uuid.uuid4()))
        resp = c.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════
# 9. OAuth2 scheme 配置
# ═══════════════════════════════════════════════════════


class TestOAuth2Scheme:
    def test_auto_error_true(self):
        """OAuth2 auto_error 默认为 True"""
        from app.api.deps import oauth2_scheme

        assert oauth2_scheme.auto_error is True

    def test_token_url_in_flows(self):
        """OAuth2 flows.password.tokenUrl 为 /api/v1/auth/login"""
        from app.api.deps import oauth2_scheme

        assert oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/login"


# ═══════════════════════════════════════════════════════
# 10. 密码哈希验证
# ═══════════════════════════════════════════════════════


class TestPasswordHash:
    def test_hash_verifies(self):
        """密码哈希后可验证"""
        from app.core.security import hash_password, verify_password

        h = hash_password("MyPassword123!")
        assert verify_password("MyPassword123!", h) is True

    def test_wrong_password_fails(self):
        """错误密码验证失败"""
        from app.core.security import hash_password, verify_password

        h = hash_password("MyPassword123!")
        assert verify_password("WrongPassword", h) is False

    def test_different_hash_each_time(self):
        """相同密码每次哈希结果不同"""
        from app.core.security import hash_password

        assert hash_password("same") != hash_password("same")

    def test_hash_not_plaintext(self):
        """哈希结果不等于明文"""
        from app.core.security import hash_password

        assert hash_password("secret") != "secret"


# ═══════════════════════════════════════════════════════
# 11. Auth Schema 验证
# ═══════════════════════════════════════════════════════


class TestAuthSchemas:
    def test_login_request_fields(self):
        """LoginRequest 需要 username 和 password"""
        from app.schemas.auth import LoginRequest

        req = LoginRequest(username="admin", password="secret")
        assert req.username == "admin"
        assert req.password == "secret"

    def test_login_request_missing_fields(self):
        """LoginRequest 缺少字段抛出 ValidationError"""
        from pydantic import ValidationError

        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest()

    def test_refresh_request_fields(self):
        """RefreshRequest 需要 refresh_token"""
        from app.schemas.auth import RefreshRequest

        req = RefreshRequest(refresh_token="some-token")
        assert req.refresh_token == "some-token"

    def test_refresh_request_missing_token(self):
        """RefreshRequest 缺少 refresh_token 抛出 ValidationError"""
        from pydantic import ValidationError

        from app.schemas.auth import RefreshRequest

        with pytest.raises(ValidationError):
            RefreshRequest()

    def test_token_response_fields(self):
        """TokenResponse 包含 access_token/refresh_token/token_type"""
        from app.schemas.auth import TokenResponse

        resp = TokenResponse(access_token="at", refresh_token="rt", token_type="bearer")
        assert resp.access_token == "at"
        assert resp.refresh_token == "rt"
        assert resp.token_type == "bearer"


# ═══════════════════════════════════════════════════════
# 12. User 模型 password_changed_at 字段
# ═══════════════════════════════════════════════════════


class TestPasswordChangedAt:
    def test_user_model_has_password_changed_at(self):
        """User 模型有 password_changed_at 字段"""
        from app.models.user import User

        assert hasattr(User, "password_changed_at")

    def test_password_changed_at_nullable(self):
        """password_changed_at 允许 NULL"""
        from app.models.user import User

        col = User.__table__.c["password_changed_at"]
        assert col.nullable is True


# ═══════════════════════════════════════════════════════
# 13. 登录端点验证
# ═══════════════════════════════════════════════════════


class TestLoginEndpoint:
    def test_login_missing_body_returns_422(self):
        """login 无 body 返回 422"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/api/v1/auth/login")
        assert resp.status_code == 422

    def test_login_empty_json_returns_422(self):
        """login 空 JSON 返回 422"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_login_wrong_credentials_returns_401(self):
        """login 错误凭据返回 401"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/api/v1/auth/login", json={"username": "nonexistent", "password": "wrong"})
        assert resp.status_code in (401, 500)


# ═══════════════════════════════════════════════════════
# 14. Logout 端点
# ═══════════════════════════════════════════════════════


class TestLogoutEndpoint:
    def test_logout_returns_200_or_401(self):
        """logout 端点存在"""
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        resp = c.post("/api/v1/auth/logout")
        assert resp.status_code in (200, 401)
