"""安全加固：认证安全回归测试
覆盖账户锁定机制、密码哈希参数、登录流程完整性、密码修改安全性、配置一致性"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.session import Base
from app.main import app
from app.models.user import User

AUTH_SOURCE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "auth.py"
SECURITY_SOURCE = Path(__file__).resolve().parent.parent / "app" / "core" / "security.py"
CONFIG_SOURCE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
SCHEMA_SOURCE = Path(__file__).resolve().parent.parent / "app" / "schemas" / "auth.py"


# ═══════════════════════════════════════════════════════════
# 1. 密码哈希安全性静态验证（8 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordHashStaticSecurity:
    """密码哈希相关代码静态安全验证"""

    def test_uses_bcrypt(self):
        source = SECURITY_SOURCE.read_text()
        assert "import bcrypt" in source

    def test_hashpw_used(self):
        source = SECURITY_SOURCE.read_text()
        assert "bcrypt.hashpw(" in source

    def test_checkpw_used(self):
        source = SECURITY_SOURCE.read_text()
        assert "bcrypt.checkpw(" in source

    def test_gensalt_rounds_12(self):
        source = SECURITY_SOURCE.read_text()
        assert "rounds=12" in source or "gensalt(12" in source

    def test_password_truncated_at_72_bytes(self):
        """hash_password 和 verify_password 都截断到 72 字节"""
        source = SECURITY_SOURCE.read_text()
        assert ":72]" in source
        # 截断出现在两个函数中
        count = source.count(":72]")
        assert count >= 2, f"72字节截断应出现至少 2 次，实际 {count} 次"

    def test_verify_password_catches_exceptions(self):
        """verify_password 捕获异常返回 False"""
        source = SECURITY_SOURCE.read_text()
        assert "except" in source
        assert "return False" in source

    def test_hash_returns_string(self):
        """hash_password 返回解码后的字符串"""
        source = SECURITY_SOURCE.read_text()
        assert '.decode("utf-8")' in source

    def test_hash_encodes_utf8(self):
        """密码使用 UTF-8 编码"""
        source = SECURITY_SOURCE.read_text()
        assert '.encode("utf-8")' in source


# ═══════════════════════════════════════════════════════════
# 2. 账户锁定配置一致性（6 项）
# ═══════════════════════════════════════════════════════════


class TestAccountLockConfig:
    """账户锁定配置安全默认值"""

    def test_account_lock_max_failures_positive(self):
        assert settings.ACCOUNT_LOCK_MAX_FAILURES > 0

    def test_account_lock_window_positive(self):
        assert settings.ACCOUNT_LOCK_WINDOW_SECONDS > 0

    def test_login_fail_max_positive(self):
        assert settings.LOGIN_FAIL_MAX > 0

    def test_login_fail_window_positive(self):
        assert settings.LOGIN_FAIL_WINDOW_SECONDS > 0

    def test_account_lock_less_than_login_fail(self):
        """账户锁定阈值应 <= IP 限流阈值（逐用户更严格）"""
        assert settings.ACCOUNT_LOCK_MAX_FAILURES <= settings.LOGIN_FAIL_MAX

    def test_config_fields_exist(self):
        """config.py 定义了账户锁定和登录限流字段"""
        source = CONFIG_SOURCE.read_text()
        assert "ACCOUNT_LOCK_MAX_FAILURES" in source
        assert "ACCOUNT_LOCK_WINDOW_SECONDS" in source
        assert "LOGIN_FAIL_MAX" in source
        assert "LOGIN_FAIL_WINDOW_SECONDS" in source


# ═══════════════════════════════════════════════════════════
# 3. 登录流程完整性静态验证（10 项）
# ═══════════════════════════════════════════════════════════


class TestLoginFlowStaticSecurity:
    """登录流程静态安全验证"""

    def test_login_checks_ip_rate_limit(self):
        source = AUTH_SOURCE.read_text()
        assert "_check_login_rate_limit" in source

    def test_login_checks_account_lock(self):
        source = AUTH_SOURCE.read_text()
        assert "_check_account_lock" in source

    def test_ip_rate_limit_before_credential_check(self):
        """IP 限流在凭证验证之前"""
        source = AUTH_SOURCE.read_text()
        login_start = source.index("def login(")
        rate_limit_pos = source.index("_check_login_rate_limit", login_start)
        verify_pos = source.index("verify_password", login_start)
        assert rate_limit_pos < verify_pos

    def test_account_lock_before_credential_check(self):
        """账户锁定在凭证验证之前"""
        source = AUTH_SOURCE.read_text()
        login_start = source.index("def login(")
        lock_pos = source.index("_check_account_lock", login_start)
        verify_pos = source.index("verify_password", login_start)
        assert lock_pos < verify_pos

    def test_failed_login_records_failure(self):
        """登录失败记录失败次数"""
        source = AUTH_SOURCE.read_text()
        assert "_record_login_fail" in source

    def test_failed_login_audited(self):
        """登录失败记录审计日志"""
        source = AUTH_SOURCE.read_text()
        assert 'action="login_failed"' in source

    def test_success_login_audited(self):
        """登录成功记录审计日志"""
        source = AUTH_SOURCE.read_text()
        assert 'action="login_success"' in source

    def test_login_uses_verify_password_not_direct_compare(self):
        """登录使用 verify_password 而非直接比较"""
        source = AUTH_SOURCE.read_text()
        login_start = source.index("def login(")
        login_end = source.index("\n@router", login_start + 1)
        login_body = source[login_start:login_end]
        assert "verify_password" in login_body
        assert "==" not in login_body or "status.HTTP" in login_body

    def test_account_lock_uses_thread_lock(self):
        """账户锁定使用线程锁"""
        source = AUTH_SOURCE.read_text()
        assert "_account_fail_lock" in source
        assert "Lock()" in source

    def test_ip_rate_limit_uses_thread_lock(self):
        """IP 限流使用线程锁"""
        source = AUTH_SOURCE.read_text()
        assert "_login_fail_lock" in source


# ═══════════════════════════════════════════════════════════
# 4. 密码强度 Schema 集成静态验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordSchemaStaticSecurity:
    """密码 Schema 安全性静态验证"""

    def test_user_create_has_password_validator(self):
        source = SCHEMA_SOURCE.read_text()
        assert "validate_password_strength" in source

    def test_change_password_has_password_validator(self):
        source = SCHEMA_SOURCE.read_text()
        assert "ChangePasswordRequest" in source
        # ChangePasswordRequest 应使用 validate_password_strength
        change_start = source.index("class ChangePasswordRequest")
        change_end = source.index("\nclass ", change_start + 1)
        change_body = source[change_start:change_end]
        assert "validate_password_strength" in change_body

    def test_user_create_password_min_length(self):
        """UserCreate 密码最短 6 个字符"""
        source = SCHEMA_SOURCE.read_text()
        assert 'min_length=6' in source or 'min_length=6' in source

    def test_change_password_new_min_length(self):
        """ChangePasswordRequest 新密码最短 6 个字符"""
        source = SCHEMA_SOURCE.read_text()
        change_start = source.index("class ChangePasswordRequest")
        change_end = source.index("\nclass ", change_start + 1)
        change_body = source[change_start:change_end]
        assert "min_length=6" in change_body or "min_length=6" in change_body

    def test_password_max_length_100(self):
        """密码最大长度 100"""
        source = SCHEMA_SOURCE.read_text()
        assert "max_length=100" in source

    def test_login_no_password_strength_check(self):
        """登录请求不验证密码强度（性能考虑）"""
        source = SCHEMA_SOURCE.read_text()
        login_start = source.index("class LoginRequest")
        login_end = source.index("\nclass ", login_start + 1)
        login_body = source[login_start:login_end]
        assert "validate_password_strength" not in login_body


# ═══════════════════════════════════════════════════════════
# 5. 修改密码安全性静态验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestChangePasswordStaticSecurity:
    """修改密码安全性静态验证"""

    def test_change_password_verifies_old_password(self):
        source = AUTH_SOURCE.read_text()
        assert "old_password" in source
        assert "verify_password" in source

    def test_change_password_hashes_new_password(self):
        source = AUTH_SOURCE.read_text()
        cp_start = source.index("def change_password(")
        cp_end = source.index("return resp(", cp_start)
        cp_body = source[cp_start:cp_end]
        assert "hash_password" in cp_body

    def test_change_password_updates_password_changed_at(self):
        """修改密码更新 password_changed_at 使旧 refresh token 失效"""
        source = AUTH_SOURCE.read_text()
        assert "password_changed_at" in source

    def test_change_password_audited(self):
        source = AUTH_SOURCE.read_text()
        assert 'action="password_change"' in source

    def test_refresh_checks_password_changed_at(self):
        """刷新 Token 检查 password_changed_at 防止旧 token 复用"""
        source = AUTH_SOURCE.read_text()
        refresh_start = source.index("def refresh_token(")
        refresh_end = source.index("return resp(", refresh_start)
        refresh_body = source[refresh_start:refresh_end]
        assert "password_changed_at" in refresh_body


# ═══════════════════════════════════════════════════════════
# 6. 密码哈希运行时安全验证（7 项）
# ═══════════════════════════════════════════════════════════


class TestPasswordHashRuntime:
    """密码哈希运行时安全回归"""

    def test_hash_format_bcrypt_2b(self):
        h = hash_password("Test123!")
        assert h.startswith("$2b$")

    def test_hash_rounds_12(self):
        h = hash_password("Test123!")
        parts = h.split("$")
        assert parts[2] == "12"

    def test_72_byte_truncation_consistent(self):
        """hash 和 verify 的 72 字节截断一致"""
        base = "A" * 72
        extended = base + "extra"
        h = hash_password(extended)
        assert verify_password(base, h) is True
        assert verify_password(extended, h) is True

    def test_unicode_password_hash_verify(self):
        pw = "中文密码Test123!@"
        h = hash_password(pw)
        assert verify_password(pw, h) is True
        assert verify_password("中文密码Test123!@", h) is True

    def test_hash_not_reversible(self):
        """哈希不等于明文且不以明文开头"""
        pw = "MySecret123!"
        h = hash_password(pw)
        assert h != pw
        assert not h.startswith(pw)

    def test_empty_password_hashed(self):
        """空密码也能被哈希（Schema 层做长度限制）"""
        h = hash_password("")
        assert h.startswith("$2b$")

    def test_hash_deterministic_verify(self):
        """相同密码的哈希不同但都可验证"""
        pw = "VerifyMe123!"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2
        assert verify_password(pw, h1) is True
        assert verify_password(pw, h2) is True


# ═══════════════════════════════════════════════════════════
# 7. 账户锁定机制运行时验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestAccountLockRuntime:
    """账户锁定机制运行时回归"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.engine = create_engine(
            "sqlite:///./test_auth_sec_lock.db",
            connect_args={"check_same_thread": False},
        )
        self.TestSession = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self._original = app.dependency_overrides.get(get_db)

        def _override():
            db = self.TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override
        Base.metadata.create_all(bind=self.engine)

        db = self.TestSession()
        self.uid = uuid.uuid4()
        db.add(User(
            id=self.uid, username="locktest_user",
            hashed_password=hash_password("RealP@ss1"),
            display_name="锁定测试", is_active=True, is_superuser=True,
        ))
        db.commit()
        db.close()

        # 重置认证模块的失败计数器
        from app.api.v1 import auth as auth_mod
        auth_mod._account_fail_counts.clear()
        auth_mod._login_fail_counts.clear()

        yield

        Base.metadata.drop_all(bind=self.engine)
        if self._original is not None:
            app.dependency_overrides[get_db] = self._original
        elif get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        import os
        if os.path.exists("./test_auth_sec_lock.db"):
            os.remove("./test_auth_sec_lock.db")

    def test_login_success_resets_no_lock(self):
        """成功登录不会触发锁定"""
        tc = TestClient(app)
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user", "password": "RealP@ss1",
        })
        assert resp.status_code == 200

    def test_wrong_password_returns_401(self):
        tc = TestClient(app)
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user", "password": "WrongP@ss1",
        })
        assert resp.status_code == 401

    def test_locked_account_returns_429(self):
        """连续失败达到阈值后返回 429"""
        tc = TestClient(app)
        max_failures = settings.ACCOUNT_LOCK_MAX_FAILURES
        for i in range(max_failures):
            resp = tc.post("/api/v1/auth/login", json={
                "username": "locktest_user", "password": "WrongP@ss1",
            })
            if i < max_failures - 1:
                assert resp.status_code == 401, f"第 {i+1} 次应为 401"
        # 第 max_failures 次应触发锁定
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user", "password": "RealP@ss1",
        })
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "ACCOUNT_LOCKED"

    def test_locked_account_error_message(self):
        """锁定错误消息语义正确"""
        tc = TestClient(app)
        max_failures = settings.ACCOUNT_LOCK_MAX_FAILURES
        for _ in range(max_failures):
            tc.post("/api/v1/auth/login", json={
                "username": "locktest_user", "password": "WrongP@ss1",
            })
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user", "password": "RealP@ss1",
        })
        body = resp.json()
        assert "登录失败" in body["error"]["message"] or "稍后" in body["error"]["message"]

    def test_different_users_independent(self):
        """不同用户的锁定状态独立"""
        db = self.TestSession()
        uid2 = uuid.uuid4()
        db.add(User(
            id=uid2, username="locktest_user2",
            hashed_password=hash_password("RealP@ss2"),
            display_name="锁定测试2", is_active=True, is_superuser=True,
        ))
        db.commit()
        db.close()

        tc = TestClient(app)
        max_failures = settings.ACCOUNT_LOCK_MAX_FAILURES
        # 锁定 user1
        for _ in range(max_failures):
            tc.post("/api/v1/auth/login", json={
                "username": "locktest_user", "password": "WrongP@ss1",
            })
        # user2 仍可登录
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user2", "password": "RealP@ss2",
        })
        assert resp.status_code == 200

    def test_correct_password_after_lock_fails(self):
        """锁定后即使正确密码也无法登录"""
        tc = TestClient(app)
        max_failures = settings.ACCOUNT_LOCK_MAX_FAILURES
        for _ in range(max_failures):
            tc.post("/api/v1/auth/login", json={
                "username": "locktest_user", "password": "WrongP@ss1",
            })
        resp = tc.post("/api/v1/auth/login", json={
            "username": "locktest_user", "password": "RealP@ss1",
        })
        assert resp.status_code == 429
