"""安全模块单元测试 — hash_password / verify_password / create_access_token / create_refresh_token"""

from datetime import timedelta

import pytest
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import ValidationError

from app.core.config import settings


def _decode(token: str) -> dict:
    """解码 JWT 并验证 iss/aud 声明"""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER,
    )
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import ChangePasswordRequest, UserCreate

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
    payload = _decode(token)
    assert payload["sub"] == "user-123"


def test_access_token_type_claim():
    """access token type 为 access"""
    token = create_access_token("user-abc")
    payload = _decode(token)
    assert payload["type"] == "access"


def test_access_token_has_exp():
    """access token 包含 exp 过期时间"""
    token = create_access_token("user-1")
    payload = _decode(token)
    assert "exp" in payload


def test_access_token_custom_expiry():
    """自定义过期时间生效"""
    token = create_access_token("user-1", expires_delta=timedelta(minutes=5))
    payload = _decode(token)
    assert "exp" in payload


# ─── create_refresh_token ────────────────────────────────────


def test_refresh_token_decodable():
    """refresh token 可用同一密钥解码"""
    token = create_refresh_token("user-456")
    payload = _decode(token)
    assert payload["sub"] == "user-456"


def test_refresh_token_type_claim():
    """refresh token type 为 refresh"""
    token = create_refresh_token("user-xyz")
    payload = _decode(token)
    assert payload["type"] == "refresh"


def test_refresh_token_has_exp():
    """refresh token 包含 exp 过期时间"""
    token = create_refresh_token("user-1")
    payload = _decode(token)
    assert "exp" in payload


def test_refresh_token_longer_expiry():
    """refresh token 过期时间晚于 access token"""
    access = create_access_token("user-1")
    refresh = create_refresh_token("user-1")
    a_payload = _decode(access)
    r_payload = _decode(refresh)
    assert r_payload["exp"] > a_payload["exp"]


# ─── verify_password 异常防御 ────────────────────────────────


def test_verify_password_invalid_hash_returns_false():
    """无效哈希格式不抛异常，返回 False"""
    assert verify_password("anypass", "not-a-bcrypt-hash") is False


def test_verify_password_empty_hash_returns_false():
    """空哈希不抛异常，返回 False"""
    assert verify_password("anypass", "") is False


def test_verify_password_none_hash_returns_false():
    """None 哈希不抛异常，返回 False"""
    assert verify_password("anypass", None) is False


# ─── JWT iat / jti 字段 ─────────────────────────────────────


def test_access_token_has_iat():
    """access token 包含 iat 签发时间"""
    token = create_access_token("user-1")
    payload = _decode(token)
    assert "iat" in payload
    assert isinstance(payload["iat"], (int, float))


def test_refresh_token_has_iat():
    """refresh token 包含 iat 签发时间"""
    token = create_refresh_token("user-1")
    payload = _decode(token)
    assert "iat" in payload


def test_access_token_has_jti():
    """access token 包含 jti 唯一标识"""
    token = create_access_token("user-1")
    payload = _decode(token)
    assert "jti" in payload
    assert len(payload["jti"]) == 36  # UUID 格式


def test_refresh_token_has_jti():
    """refresh token 包含 jti 唯一标识"""
    token = create_refresh_token("user-1")
    payload = _decode(token)
    assert "jti" in payload


def test_tokens_have_unique_jti():
    """每次生成的 token jti 不同"""
    t1 = create_access_token("user-1")
    t2 = create_access_token("user-1")
    p1 = _decode(t1)
    p2 = _decode(t2)
    assert p1["jti"] != p2["jti"]


# ─── Token 篡改检测 ──────────────────────────────────────────


def test_tampered_token_rejected():
    """被篡改的 token 解码失败"""
    token = create_access_token("user-1")
    # 修改 token 最后一个字符
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    try:
        jwt.decode(tampered, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        pytest.fail("篡改的 token 不应解码成功")
    except JWTError:
        pass


def test_token_wrong_secret_rejected():
    """用错误密钥解码 token 失败"""
    token = create_access_token("user-1")
    try:
        jwt.decode(token, "wrong-secret-key", algorithms=[settings.JWT_ALGORITHM])
        pytest.fail("错误密钥不应解码成功")
    except JWTError:
        pass


def test_expired_token_rejected():
    """已过期的 token 解码失败"""
    token = create_access_token("user-1", expires_delta=timedelta(seconds=-1))
    try:
        jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        pytest.fail("过期 token 不应解码成功")
    except ExpiredSignatureError:
        pass


# ─── bcrypt 安全参数 ────────────────────────────────────────


def test_bcrypt_rounds_12():
    """bcrypt 使用 12 轮加密"""
    h = hash_password("test1234")
    # bcrypt 哈希格式: $2b$12$...
    parts = h.split("$")
    assert parts[1] == "2b"
    assert parts[2] == "12"


# ─── 密码特殊字符 ────────────────────────────────────────────


def test_unicode_password():
    """Unicode 密码可以正确哈希和验证"""
    pwd = "密码测试🔐abc"
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("密码测试🔓abc", h) is False


def test_long_password():
    """长密码（72 字节内）可以正确验证"""
    pwd = "a" * 72
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True


def test_password_beyond_72_bytes():
    """超过 72 字节的密码被截断（bcrypt 特性）"""
    pwd72 = "a" * 72
    pwd73 = "a" * 73
    h = hash_password(pwd73)
    # bcrypt 截断到 72 字节，所以 73 字节和 72 字节密码验证结果相同
    assert verify_password(pwd72, h) is True


# ─── 密码强度校验（Schema 层） ───────────────────────────────


@pytest.mark.parametrize("pwd,error_keyword", [
    ("123456", "字母"),
    ("abcdef", "数字"),
])
def test_user_create_rejects_weak_passwords(pwd, error_keyword):
    """创建用户时拒绝弱密码"""
    with pytest.raises(ValidationError, match=error_keyword):
        UserCreate(username="test", password=pwd)


def test_user_create_rejects_short_password():
    """创建用户时拒绝短于 6 位的密码"""
    with pytest.raises(ValidationError, match="at least 6"):
        UserCreate(username="test", password="ab1")


def test_user_create_accepts_strong_password():
    """创建用户时接受符合要求的密码"""
    u = UserCreate(username="test", password="test12")
    assert u.password == "test12"


@pytest.mark.parametrize("pwd,error_keyword", [
    ("123456", "字母"),
    ("abcdef", "数字"),
])
def test_change_password_rejects_weak_new_password(pwd, error_keyword):
    """修改密码时拒绝弱新密码"""
    with pytest.raises(ValidationError, match=error_keyword):
        ChangePasswordRequest(old_password="oldpass1", new_password=pwd)
