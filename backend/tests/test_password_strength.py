"""密码强度验证模块单元测试"""

import pytest
from pydantic import ValidationError

from app.core.password_strength import validate_password_strength
from app.schemas.auth import ChangePasswordRequest, UserCreate

# ─── validate_password_strength 直接调用 ────────────────────────


def test_strong_password_passes():
    """符合所有规则的密码通过"""
    assert validate_password_strength("MyPass123!") == "MyPass123!"


def test_no_uppercase_rejected():
    """无大写字母被拒绝"""
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("mypass123!")


def test_no_lowercase_rejected():
    """无小写字母被拒绝"""
    with pytest.raises(ValueError, match="小写字母"):
        validate_password_strength("MYPASS123!")


def test_no_digit_rejected():
    """无数字被拒绝"""
    with pytest.raises(ValueError, match="数字"):
        validate_password_strength("MyPassword!")


def test_no_special_char_rejected():
    """无特殊字符被拒绝"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("MyPassword123")


def test_weak_password_password_rejected():
    """常见弱密码 'password' 被拒绝"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd!")


def test_weak_password_p_ssw0rd_rejected():
    """常见弱密码 'p@ssw0rd' 变体被拒绝"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd!")


def test_weak_password_in_list_exact_match():
    """弱密码列表中精确匹配的密码被拒绝"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd!")


def test_normal_password_not_in_weak_list():
    """不在弱密码列表中的正常密码通过"""
    result = validate_password_strength("Xk9#mP2$vL")
    assert result == "Xk9#mP2$vL"


def test_unicode_special_chars_accepted():
    """Unicode 特殊字符也算特殊字符"""
    result = validate_password_strength("MyPass123中文")
    assert result == "MyPass123中文"


def test_various_special_chars():
    """各种特殊字符都通过"""
    for ch in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`":
        pwd = f"MyPass123{ch}"
        assert validate_password_strength(pwd) == pwd


# ─── Schema 集成测试 ────────────────────────────────────────────


def test_user_create_rejects_no_uppercase():
    """UserCreate 拒绝无大写字母密码"""
    with pytest.raises(ValidationError, match="大写字母"):
        UserCreate(username="test", password="mypass123!")


def test_user_create_rejects_no_special():
    """UserCreate 拒绝无特殊字符密码"""
    with pytest.raises(ValidationError, match="特殊字符"):
        UserCreate(username="test", password="MyPassword123")


def test_change_password_rejects_weak():
    """ChangePasswordRequest 拒绝弱密码"""
    with pytest.raises(ValidationError, match="常见"):
        ChangePasswordRequest(old_password="old", new_password="P@ssw0rd!")


def test_change_password_accepts_strong():
    """ChangePasswordRequest 接受强密码"""
    r = ChangePasswordRequest(old_password="oldpass", new_password="MyNewPass1!")
    assert r.new_password == "MyNewPass1!"
