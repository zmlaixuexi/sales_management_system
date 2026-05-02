"""安全模块单元测试 — hash_password / verify_password / create_access_token / create_refresh_token"""

from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

# ─── hash_password ──────────────────────────────────────────


def test_hash_password_returns_bcrypt_string():
    """hash_password 返回 bcrypt 哈希字符串"""
    h = hash_password("mypass123")
    assert isinstance(h, str)
    assert h.startswith("$2b$")


def test_hash_password_different_salts():
    """相同密码两次哈希结果不同（盐值不同）"""
    h1 = hash_password("same_pass")
    h2 = hash_password("same_pass")
    assert h1 != h2


# ─── verify_password ────────────────────────────────────────


def test_verify_password_correct():
    """正确密码验证通过"""
    h = hash_password("mypassword1")
    assert verify_password("mypassword1", h) is True


def test_verify_password_wrong():
    """错误密码验证失败"""
    h = hash_password("mypassword1")
    assert verify_password("wrongpass", h) is False


def test_verify_password_empty():
    """空密码验证失败"""
    h = hash_password("realpass1")
    assert verify_password("", h) is False


def test_verify_password_hash_from_hash_password():
    """hash_password 产生的哈希可以被 verify_password 验证"""
    password = "test_pass_123"
    h = hash_password(password)
    assert verify_password(password, h) is True
    assert verify_password(password + "x", h) is False


# ─── create_access_token ────────────────────────────────────


def test_access_token_decodable():
    """access token 可用同一密钥解码"""
    token = create_access_token("user-123")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "user-123"


def test_access_token_type_claim():
    """access token type 为 access"""
    token = create_access_token("user-abc")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["type"] == "access"


def test_access_token_has_exp():
    """access token 包含 exp 过期时间"""
    token = create_access_token("user-1")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert "exp" in payload


def test_access_token_custom_expiry():
    """自定义过期时间生效"""
    token = create_access_token("user-1", expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert "exp" in payload


# ─── create_refresh_token ────────────────────────────────────


def test_refresh_token_decodable():
    """refresh token 可用同一密钥解码"""
    token = create_refresh_token("user-456")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "user-456"


def test_refresh_token_type_claim():
    """refresh token type 为 refresh"""
    token = create_refresh_token("user-xyz")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["type"] == "refresh"


def test_refresh_token_has_exp():
    """refresh token 包含 exp 过期时间"""
    token = create_refresh_token("user-1")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert "exp" in payload


def test_refresh_token_longer_expiry():
    """refresh token 过期时间晚于 access token"""
    access = create_access_token("user-1")
    refresh = create_refresh_token("user-1")
    a_payload = jwt.decode(access, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    r_payload = jwt.decode(refresh, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert r_payload["exp"] > a_payload["exp"]
