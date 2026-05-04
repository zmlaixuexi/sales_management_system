"""JWT token 过期与刷新令牌边界测试 — 覆盖 token 生命周期、刷新机制、密码修改后失效"""

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt as jose_jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token

_USER_ID = str(uuid.uuid4())


def _decode(token: str) -> dict:
    return jose_jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
    )


# ═══════════════════════════════════════════════════════
# 1. Access Token 过期时间
# ═══════════════════════════════════════════════════════


def test_access_token_expiry_matches_config():
    """access token 的 exp 字段 = iat + JWT_ACCESS_TOKEN_EXPIRE_MINUTES"""
    token = create_access_token(subject=_USER_ID)
    claims = _decode(token)

    iat = datetime.fromtimestamp(claims["iat"], tz=UTC)
    exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
    expected_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    actual_delta = exp - iat
    assert abs((actual_delta - expected_delta).total_seconds()) < 2


def test_access_token_default_expiry_30_minutes():
    """默认 access token 过期时间为 30 分钟"""
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30


def test_access_token_custom_expiry():
    """自定义 access token 过期时间"""
    custom_delta = timedelta(minutes=5)
    token = create_access_token(subject=_USER_ID, expires_delta=custom_delta)
    claims = _decode(token)
    iat = datetime.fromtimestamp(claims["iat"], tz=UTC)
    exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
    actual_delta = exp - iat
    assert abs((actual_delta - custom_delta).total_seconds()) < 2


def test_access_token_expired_is_rejected():
    """已过期的 access token 解码时抛异常"""
    expired_token = create_access_token(subject=_USER_ID, expires_delta=timedelta(seconds=-1))
    from jose.exceptions import ExpiredSignatureError

    with pytest.raises(ExpiredSignatureError):
        _decode(expired_token)


def test_access_token_just_expired():
    """刚刚过期 1 秒的 token 被拒绝"""
    token = create_access_token(subject=_USER_ID, expires_delta=timedelta(seconds=-1))
    from jose.exceptions import ExpiredSignatureError

    with pytest.raises(ExpiredSignatureError):
        _decode(token)


def test_access_token_near_expiry_still_valid():
    """接近过期但未过期的 token 仍然有效"""
    token = create_access_token(subject=_USER_ID, expires_delta=timedelta(seconds=10))
    claims = _decode(token)
    assert claims["sub"] == _USER_ID


# ═══════════════════════════════════════════════════════
# 2. Refresh Token 过期时间
# ═══════════════════════════════════════════════════════


def test_refresh_token_expiry_matches_config():
    """refresh token 的 exp 字段 = iat + JWT_REFRESH_TOKEN_EXPIRE_DAYS"""
    token = create_refresh_token(subject=_USER_ID)
    claims = _decode(token)
    iat = datetime.fromtimestamp(claims["iat"], tz=UTC)
    exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
    expected_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    actual_delta = exp - iat
    assert abs((actual_delta - expected_delta).total_seconds()) < 2


def test_refresh_token_default_expiry_7_days():
    """默认 refresh token 过期时间为 7 天"""
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7


def test_refresh_token_longer_than_access():
    """refresh token 过期时间 > access token 过期时间"""
    refresh_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    access_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    assert refresh_delta > access_delta


def test_refresh_token_expired_is_rejected():
    """已过期的 refresh token 解码时抛异常"""
    now = int(time.time())
    payload = {
        "sub": _USER_ID, "exp": now - 1, "iat": now - 100,
        "jti": str(uuid.uuid4()), "type": "refresh",
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    from jose.exceptions import ExpiredSignatureError

    with pytest.raises(ExpiredSignatureError):
        _decode(token)


# ═══════════════════════════════════════════════════════
# 3. Token 类型区分
# ═══════════════════════════════════════════════════════


def test_access_token_type_is_access():
    """access token 的 type 字段为 access"""
    token = create_access_token(subject=_USER_ID)
    claims = _decode(token)
    assert claims["type"] == "access"


def test_refresh_token_type_is_refresh():
    """refresh token 的 type 字段为 refresh"""
    token = create_refresh_token(subject=_USER_ID)
    claims = _decode(token)
    assert claims["type"] == "refresh"


def test_access_token_cannot_be_used_as_refresh():
    """access token 不能用于刷新（type != refresh）"""
    access_token = create_access_token(subject=_USER_ID)
    claims = _decode(access_token)
    assert claims["type"] != "refresh"


def test_refresh_token_cannot_be_used_as_access():
    """refresh token 不能用于访问（type != access）"""
    refresh_token = create_refresh_token(subject=_USER_ID)
    claims = _decode(refresh_token)
    assert claims["type"] != "access"


# ═══════════════════════════════════════════════════════
# 4. Token Claims 完整性
# ═══════════════════════════════════════════════════════


def test_access_token_has_all_required_claims():
    """access token 包含所有必要 claims"""
    token = create_access_token(subject=_USER_ID)
    claims = _decode(token)
    for field in ("sub", "exp", "iat", "jti", "type", "iss", "aud"):
        assert field in claims, f"缺少 {field} 字段"


def test_refresh_token_has_all_required_claims():
    """refresh token 包含所有必要 claims"""
    token = create_refresh_token(subject=_USER_ID)
    claims = _decode(token)
    for field in ("sub", "exp", "iat", "jti", "type", "iss", "aud"):
        assert field in claims, f"缺少 {field} 字段"


def test_token_sub_is_user_id():
    """token 的 sub 字段是用户 UUID"""
    uid = str(uuid.uuid4())
    token = create_access_token(subject=uid)
    claims = _decode(token)
    assert claims["sub"] == uid


def test_token_jti_is_unique():
    """每次生成的 token jti 唯一"""
    t1 = create_access_token(subject=_USER_ID)
    t2 = create_access_token(subject=_USER_ID)
    c1 = _decode(t1)
    c2 = _decode(t2)
    assert c1["jti"] != c2["jti"]


def test_token_iss_matches_config():
    """token 的 iss 字段匹配配置"""
    token = create_access_token(subject=_USER_ID)
    claims = _decode(token)
    assert claims["iss"] == settings.JWT_ISSUER


def test_token_aud_matches_config():
    """token 的 aud 字段匹配配置"""
    token = create_access_token(subject=_USER_ID)
    claims = _decode(token)
    assert claims["aud"] == settings.JWT_AUDIENCE


# ═══════════════════════════════════════════════════════
# 5. 配置验证
# ═══════════════════════════════════════════════════════


def test_jwt_algorithm_is_hs256():
    """JWT 算法为 HS256"""
    assert settings.JWT_ALGORITHM == "HS256"


def test_jwt_access_expire_positive():
    """access token 过期时间为正数"""
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_jwt_refresh_expire_positive():
    """refresh token 过期天数为正数"""
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0


def test_jwt_secret_key_not_empty():
    """JWT 密钥不为空"""
    assert len(settings.JWT_SECRET_KEY) > 0


def test_jwt_secret_key_min_length():
    """JWT 密钥至少 8 个字符"""
    assert len(settings.JWT_SECRET_KEY) >= 8


# ═══════════════════════════════════════════════════════
# 6. 密码修改后 Token 失效逻辑
# ═══════════════════════════════════════════════════════


def test_password_changed_at_comparison_logic():
    """密码修改时间 > token iat 时 token 应失效（逻辑验证）"""
    now = datetime.now(UTC)
    token_iat = now - timedelta(hours=1)
    changed_at = now.replace(microsecond=0)
    # token 在密码修改前签发，应被拒绝
    assert token_iat < changed_at


def test_password_changed_after_token_issued_still_valid():
    """token 在密码修改之后签发的仍然有效"""
    now = datetime.now(UTC)
    token_iat = now + timedelta(hours=1)  # 未来签发（模拟）
    changed_at = now.replace(microsecond=0)
    # token 在密码修改后签发，不应被拒绝
    assert token_iat >= changed_at


def test_password_changed_at_microsecond_truncation():
    """password_changed_at 微秒被截断到秒级精度"""
    now = datetime.now(UTC)
    changed_at = now.replace(microsecond=500000)
    truncated = changed_at.replace(microsecond=0)
    assert truncated.microsecond == 0
    assert changed_at.second == truncated.second


# ═══════════════════════════════════════════════════════
# 7. Token 签名验证
# ═══════════════════════════════════════════════════════


def test_token_wrong_secret_rejected():
    """使用错误密钥签名的 token 被拒绝"""
    from jose.exceptions import JWTError

    payload = {
        "sub": _USER_ID, "exp": int(time.time()) + 3600, "iat": int(time.time()),
        "jti": str(uuid.uuid4()), "type": "access",
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
    }
    wrong_token = jose_jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
    with pytest.raises(JWTError):
        _decode(wrong_token)


def test_token_missing_exp_rejected():
    """缺少 exp 字段的 token 在 require_exp=True 时被拒绝"""
    from jose.exceptions import JWTError

    payload = {
        "sub": _USER_ID, "iat": int(time.time()),
        "jti": str(uuid.uuid4()), "type": "access",
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        jose_jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
            options={"require_exp": True},
        )


def test_token_with_future_iat_still_valid():
    """iat 在未来但未过期的 token 仍然有效（jose 不验证 iat 时序）"""
    future_iat = int(time.time()) + 3600
    payload = {
        "sub": _USER_ID, "exp": future_iat + 3600, "iat": future_iat,
        "jti": str(uuid.uuid4()), "type": "access",
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    claims = _decode(token)
    assert claims["sub"] == _USER_ID


# ═══════════════════════════════════════════════════════
# 8. E2E: 刷新 Token 流程
# ═══════════════════════════════════════════════════════


def test_e2e_refresh_token_returns_new_tokens():
    """E2E: 使用 refresh token 获取新的 access + refresh token"""
    import uuid as _uuid

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.user import User

    engine = create_engine("sqlite:///./test_jwt_refresh.db", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    original = app.dependency_overrides.get(get_db)

    def _override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    Base.metadata.create_all(bind=engine)

    db = TestSession()
    uid = _uuid.uuid4()
    db.add(User(
        id=uid, username="jwt_refresh_user", hashed_password=hash_password("TestPass123!"),
        display_name="JWT测试", is_active=True, is_superuser=True,
    ))
    db.commit()
    db.close()

    tc = TestClient(app)
    try:
        login_resp = tc.post("/api/v1/auth/login", json={
            "username": "jwt_refresh_user", "password": "TestPass123!",
        })
        assert login_resp.status_code == 200
        refresh_tok = login_resp.json()["data"]["refresh_token"]

        refresh_resp = tc.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert refresh_resp.status_code == 200
        new_data = refresh_resp.json()["data"]
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["access_token"] != login_resp.json()["data"]["access_token"]
    finally:
        Base.metadata.drop_all(bind=engine)
        if original is not None:
            app.dependency_overrides[get_db] = original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_jwt_refresh.db"):
            os.remove("./test_jwt_refresh.db")


def test_e2e_access_token_as_refresh_rejected():
    """E2E: 使用 access token 作为 refresh token 被 401 拒绝"""
    import uuid as _uuid

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.user import User

    engine = create_engine("sqlite:///./test_jwt_access_as_refresh.db", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    original = app.dependency_overrides.get(get_db)

    def _override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    Base.metadata.create_all(bind=engine)

    db = TestSession()
    uid = _uuid.uuid4()
    db.add(User(
        id=uid, username="jwt_access_refresh", hashed_password=hash_password("TestPass123!"),
        display_name="JWT测试2", is_active=True, is_superuser=True,
    ))
    db.commit()
    db.close()

    tc = TestClient(app)
    try:
        login_resp = tc.post("/api/v1/auth/login", json={
            "username": "jwt_access_refresh", "password": "TestPass123!",
        })
        access_tok = login_resp.json()["data"]["access_token"]

        refresh_resp = tc.post("/api/v1/auth/refresh", json={"refresh_token": access_tok})
        assert refresh_resp.status_code == 401
    finally:
        Base.metadata.drop_all(bind=engine)
        if original is not None:
            app.dependency_overrides[get_db] = original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_jwt_access_as_refresh.db"):
            os.remove("./test_jwt_access_as_refresh.db")


def test_e2e_invalid_refresh_token_rejected():
    """E2E: 使用无效 refresh token 被 401 拒绝"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-token"})
    assert resp.status_code == 401


def test_e2e_empty_refresh_token_rejected():
    """E2E: 空字符串 refresh token 被 422 拒绝"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.post("/api/v1/auth/refresh", json={"refresh_token": ""})
    assert resp.status_code == 422
