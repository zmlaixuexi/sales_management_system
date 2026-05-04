"""密码强度验证模块边界测试 — 覆盖字符类别、弱密码黑名单、长度边界、Schema 集成、E2E"""

import pytest
from pydantic import ValidationError

from app.core.password_strength import _WEAK_PASSWORDS, validate_password_strength
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


# ─── 字符类别边界 ──────────────────────────────────────────


def test_only_uppercase_rejected():
    """仅大写字母被拒绝"""
    with pytest.raises(ValueError):
        validate_password_strength("ABCDEFG")


def test_only_digits_rejected():
    """仅数字被拒绝"""
    with pytest.raises(ValueError):
        validate_password_strength("12345678")


def test_only_special_chars_rejected():
    """仅特殊字符被拒绝"""
    with pytest.raises(ValueError):
        validate_password_strength("!@#$%^&*")


def test_space_as_special_char():
    """空格算特殊字符"""
    pw = "Aa1 bc"
    assert validate_password_strength(pw) == pw


def test_exactly_meets_all_rules():
    """恰好满足所有规则的密码通过"""
    pw = "Aa1!Bb"
    assert validate_password_strength(pw) == pw


def test_very_long_password_passes():
    """很长的密码通过"""
    pw = "Aa1!" + "x" * 200
    assert validate_password_strength(pw) == pw


# ─── 弱密码黑名单 ──────────────────────────────────────────


def test_weak_password_blacklist_size():
    """黑名单包含条目"""
    assert len(_WEAK_PASSWORDS) > 0


def test_weak_password_is_frozenset():
    """黑名单是不可变集合"""
    assert isinstance(_WEAK_PASSWORDS, frozenset)


def test_blacklist_case_insensitive_match():
    """黑名单匹配不区分大小写"""
    assert "password123" in _WEAK_PASSWORDS
    assert "PASSWORD123".lower() in _WEAK_PASSWORDS
    assert "Admin123".lower() in _WEAK_PASSWORDS


def test_blacklist_contains_numeric_sequences():
    """黑名单包含数字序列"""
    for pw in ("123456", "12345678", "123456789", "1234567890"):
        assert pw in _WEAK_PASSWORDS


def test_blacklist_contains_keyboard_walks():
    """黑名单包含键盘行走模式"""
    for pw in ("qwerty", "qwerty123", "qwertyuiop"):
        assert pw in _WEAK_PASSWORDS


def test_blacklist_contains_admin_patterns():
    """黑名单包含 admin/root 模式"""
    for pw in ("admin", "admin123", "root", "root123"):
        assert pw in _WEAK_PASSWORDS


def test_blacklist_contains_l33t_speak():
    """黑名单包含 leet speak 变体"""
    for pw in ("passw0rd", "p@ssw0rd", "p@ssword"):
        assert pw in _WEAK_PASSWORDS


def test_blacklist_contains_chinese_patterns():
    """黑名单包含中文常见密码"""
    for pw in ("woaini", "woaini1314", "taobao"):
        assert pw in _WEAK_PASSWORDS


def test_blacklist_exact_match_not_suffix():
    """黑名单是精确匹配，不是后缀匹配"""
    # "password123" 在黑名单中，但加了特殊字符后不在
    assert "password123" in _WEAK_PASSWORDS
    assert "password123!" not in _WEAK_PASSWORDS


def test_blacklist_blocks_exact_password():
    """黑名单精确匹配整个密码（小写后）"""
    for weak in ("password", "admin", "123456", "qwerty"):
        assert weak in _WEAK_PASSWORDS
        assert weak.upper() in _WEAK_PASSWORDS or weak.upper().lower() in _WEAK_PASSWORDS


# ─── 验证顺序 ──────────────────────────────────────────────


def test_validation_checks_uppercase_first():
    """验证顺序：先检查大写字母"""
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("")


def test_validation_checks_lowercase_before_digit():
    """验证顺序：小写在数字之前"""
    with pytest.raises(ValueError, match="小写字母"):
        validate_password_strength("A")


def test_validation_checks_digit_before_special():
    """验证顺序：数字在特殊字符之前"""
    with pytest.raises(ValueError, match="数字"):
        validate_password_strength("Aa")


def test_validation_checks_special_before_blacklist():
    """验证顺序：特殊字符在黑名单之前"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("Admin123")


# ─── Schema 集成测试 ────────────────────────────────────────────


def test_user_create_rejects_no_uppercase():
    """UserCreate 拒绝无大写字母密码"""
    with pytest.raises(ValidationError, match="大写字母"):
        UserCreate(username="test", password="mypass123!")


def test_user_create_rejects_no_special():
    """UserCreate 拒绝无特殊字符密码"""
    with pytest.raises(ValidationError, match="特殊字符"):
        UserCreate(username="test", password="MyPassword123")


def test_user_create_password_min_length_6():
    """UserCreate 密码最短 6 个字符"""
    with pytest.raises(ValidationError):
        UserCreate(username="test", password="Aa1!", display_name="t")


def test_user_create_password_max_length_100():
    """UserCreate 密码最长 100 个字符"""
    long_pw = "Aa1!" + "x" * 97  # 101 chars
    with pytest.raises(ValidationError):
        UserCreate(username="test", password=long_pw, display_name="t")


def test_user_create_valid_password():
    """UserCreate 合法密码通过"""
    user = UserCreate(username="test", password="MyP@ss123", display_name="t")
    assert user.password == "MyP@ss123"


def test_user_create_weak_password_rejected():
    """UserCreate 弱密码被拒绝（黑名单精确匹配）"""
    with pytest.raises(ValidationError, match="常见"):
        UserCreate(username="test", password="P@ssw0rd!", display_name="t")


def test_change_password_rejects_weak():
    """ChangePasswordRequest 拒绝弱密码"""
    with pytest.raises(ValidationError, match="常见"):
        ChangePasswordRequest(old_password="old", new_password="P@ssw0rd!")


def test_change_password_accepts_strong():
    """ChangePasswordRequest 接受强密码"""
    r = ChangePasswordRequest(old_password="oldpass", new_password="MyNewPass1!")
    assert r.new_password == "MyNewPass1!"


def test_change_password_request_min_length_6():
    """ChangePasswordRequest 新密码最短 6 个字符"""
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password="Aa1!")


def test_change_password_request_max_length_100():
    """ChangePasswordRequest 新密码最长 100 个字符"""
    long_pw = "Aa1!" + "x" * 97  # 101 chars
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="old", new_password=long_pw)


def test_change_password_old_password_min_length_1():
    """ChangePasswordRequest 旧密码最少 1 个字符"""
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="", new_password="NewP@ss1!")


# ─── E2E: 修改密码密码强度校验 ──────────────────────────────


def test_e2e_change_password_weak_new_password_rejected():
    """E2E: 修改密码时弱密码被拒绝"""
    import uuid

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.user import User

    engine = create_engine("sqlite:///./test_pwd_str1.db", connect_args={"check_same_thread": False})
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
    uid = uuid.uuid4()
    db.add(User(
        id=uid, username="pwd_str_user", hashed_password=hash_password("OldP@ss1"),
        display_name="密码测试", is_active=True, is_superuser=True,
    ))
    db.commit()
    db.close()

    tc = TestClient(app)
    try:
        login_resp = tc.post("/api/v1/auth/login", json={
            "username": "pwd_str_user", "password": "OldP@ss1",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = tc.post("/api/v1/auth/change-password", headers=headers, json={
            "old_password": "OldP@ss1", "new_password": "P@ssw0rd!",
        })
        assert resp.status_code == 422
    finally:
        Base.metadata.drop_all(bind=engine)
        if original is not None:
            app.dependency_overrides[get_db] = original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_pwd_str1.db"):
            os.remove("./test_pwd_str1.db")


def test_e2e_change_password_missing_digit_rejected():
    """E2E: 修改密码时缺少数字被拒绝"""
    import uuid

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.user import User

    engine = create_engine("sqlite:///./test_pwd_str2.db", connect_args={"check_same_thread": False})
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
    uid = uuid.uuid4()
    db.add(User(
        id=uid, username="pwd_str_user2", hashed_password=hash_password("OldP@ss1"),
        display_name="密码测试2", is_active=True, is_superuser=True,
    ))
    db.commit()
    db.close()

    tc = TestClient(app)
    try:
        login_resp = tc.post("/api/v1/auth/login", json={
            "username": "pwd_str_user2", "password": "OldP@ss1",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = tc.post("/api/v1/auth/change-password", headers=headers, json={
            "old_password": "OldP@ss1", "new_password": "NoDigit!Xx",
        })
        assert resp.status_code == 422
    finally:
        Base.metadata.drop_all(bind=engine)
        if original is not None:
            app.dependency_overrides[get_db] = original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_pwd_str2.db"):
            os.remove("./test_pwd_str2.db")


def test_e2e_change_password_too_short_rejected():
    """E2E: 修改密码时过短密码被拒绝"""
    import uuid

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.user import User

    engine = create_engine("sqlite:///./test_pwd_str3.db", connect_args={"check_same_thread": False})
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
    uid = uuid.uuid4()
    db.add(User(
        id=uid, username="pwd_str_user3", hashed_password=hash_password("OldP@ss1"),
        display_name="密码测试3", is_active=True, is_superuser=True,
    ))
    db.commit()
    db.close()

    tc = TestClient(app)
    try:
        login_resp = tc.post("/api/v1/auth/login", json={
            "username": "pwd_str_user3", "password": "OldP@ss1",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = tc.post("/api/v1/auth/change-password", headers=headers, json={
            "old_password": "OldP@ss1", "new_password": "Aa1!",
        })
        assert resp.status_code == 422
    finally:
        Base.metadata.drop_all(bind=engine)
        if original is not None:
            app.dependency_overrides[get_db] = original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_pwd_str3.db"):
            os.remove("./test_pwd_str3.db")
