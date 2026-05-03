"""登录速率限制辅助函数单元测试 — _check_login_rate_limit / _check_account_lock / _record_login_fail"""

import time
from collections import defaultdict
from threading import Lock

import pytest
from fastapi import HTTPException

from app.api.v1.auth import _check_account_lock, _check_login_rate_limit, _record_login_fail
from app.core.config import settings


@pytest.fixture(autouse=True)
def _reset_counts():
    """每个测试前重置速率限制计数器"""
    import app.api.v1.auth as mod

    original_counts = mod._login_fail_counts
    original_lock = mod._login_fail_lock
    mod._login_fail_counts = defaultdict(list)
    mod._login_fail_lock = Lock()
    mod._account_fail_counts = defaultdict(list)
    mod._account_fail_lock = Lock()
    yield
    mod._login_fail_counts = original_counts
    mod._login_fail_lock = original_lock


def test_check_rate_limit_passes_under_threshold():
    """失败次数未达阈值时通过"""
    for _ in range(9):
        _record_login_fail("1.2.3.4", "user1")
    _check_login_rate_limit("1.2.3.4")  # 不抛异常


def test_check_rate_limit_blocks_at_threshold():
    """失败次数达到阈值时抛 429"""
    for _ in range(10):
        _record_login_fail("1.2.3.4", "user1")
    with pytest.raises(HTTPException) as exc_info:
        _check_login_rate_limit("1.2.3.4")
    assert exc_info.value.status_code == 429
    assert "登录失败次数过多" in str(exc_info.value.detail)


def test_check_rate_limit_independent_ips():
    """不同 IP 独立计数"""
    for _ in range(10):
        _record_login_fail("1.1.1.1", "user1")
    # 2.2.2.2 应该不受影响
    _check_login_rate_limit("2.2.2.2")


def test_record_login_fail_appends_timestamp():
    """记录失败时间戳"""
    import app.api.v1.auth as mod

    _record_login_fail("10.0.0.1", "user1")
    assert len(mod._login_fail_counts["10.0.0.1"]) == 1
    _record_login_fail("10.0.0.1", "user1")
    assert len(mod._login_fail_counts["10.0.0.1"]) == 2


def test_check_rate_limit_expired_entries_cleaned():
    """过期的失败记录被清理"""
    import app.api.v1.auth as mod

    old_time = time.monotonic() - 1000  # 超过 15 分钟窗口
    mod._login_fail_counts["3.3.3.3"] = [old_time] * 10
    _check_login_rate_limit("3.3.3.3")  # 旧记录被清理，不抛异常


def test_check_rate_limit_mixed_expired_and_fresh_passes():
    """5 条过期 + 5 条新鲜 → 仅 5 条有效，不触发"""
    import app.api.v1.auth as mod

    now = time.monotonic()
    old_time = now - 1000
    mod._login_fail_counts["4.4.4.4"] = [old_time] * 5 + [now] * 5
    _check_login_rate_limit("4.4.4.4")  # 5 条有效，不抛异常


def test_check_rate_limit_mixed_expired_and_fresh_blocks():
    """5 条过期 + 10 条新鲜 → 10 条有效，触发 429"""
    import app.api.v1.auth as mod

    now = time.monotonic()
    old_time = now - 1000
    mod._login_fail_counts["5.5.5.5"] = [old_time] * 5 + [now] * 10
    with pytest.raises(HTTPException) as exc_info:
        _check_login_rate_limit("5.5.5.5")
    assert exc_info.value.status_code == 429


def test_check_rate_limit_error_code():
    """速率限制错误包含 RATE_LIMIT_EXCEEDED 错误码"""
    for _ in range(10):
        _record_login_fail("6.6.6.6", "user1")
    with pytest.raises(HTTPException) as exc_info:
        _check_login_rate_limit("6.6.6.6")
    detail = exc_info.value.detail
    assert detail["code"] == "RATE_LIMIT_EXCEEDED"


# ─── _check_account_lock 每账户锁定测试 ───────────────────────


def test_account_lock_passes_under_threshold():
    """账户失败次数未达阈值时通过"""
    for _ in range(4):
        _record_login_fail("1.2.3.4", "target_user")
    _check_account_lock("target_user")  # 不抛异常


def test_account_lock_blocks_at_threshold():
    """账户失败次数达到阈值时抛 429"""
    for _ in range(5):
        _record_login_fail("1.2.3.4", "locked_user")
    with pytest.raises(HTTPException) as exc_info:
        _check_account_lock("locked_user")
    assert exc_info.value.status_code == 429
    assert "账户" in str(exc_info.value.detail)
    assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


def test_account_lock_independent_usernames():
    """不同用户名独立计数"""
    for _ in range(5):
        _record_login_fail("1.1.1.1", "user_a")
    # user_b 应该不受影响
    _check_account_lock("user_b")


def test_account_lock_records_per_username():
    """失败记录按用户名分别记录"""
    import app.api.v1.auth as mod

    _record_login_fail("10.0.0.1", "user_x")
    _record_login_fail("10.0.0.1", "user_y")
    assert len(mod._account_fail_counts["user_x"]) == 1
    assert len(mod._account_fail_counts["user_y"]) == 1


def test_account_lock_expired_entries_cleaned():
    """过期的账户失败记录被清理"""
    import app.api.v1.auth as mod

    old_time = time.monotonic() - 1000  # 超过 15 分钟窗口
    mod._account_fail_counts["old_user"] = [old_time] * 5
    _check_account_lock("old_user")  # 旧记录被清理，不抛异常


def test_account_lock_mixed_expired_and_fresh_passes():
    """2 条过期 + 3 条新鲜 → 仅 3 条有效，不触发"""
    import app.api.v1.auth as mod

    now = time.monotonic()
    old_time = now - 1000
    mod._account_fail_counts["mixed_user"] = [old_time] * 2 + [now] * 3
    _check_account_lock("mixed_user")  # 3 条有效 < 5，不抛异常


def test_account_lock_mixed_expired_and_fresh_blocks():
    """2 条过期 + 5 条新鲜 → 5 条有效，触发 429"""
    import app.api.v1.auth as mod

    now = time.monotonic()
    old_time = now - 1000
    mod._account_fail_counts["blocked_user"] = [old_time] * 2 + [now] * 5
    with pytest.raises(HTTPException) as exc_info:
        _check_account_lock("blocked_user")
    assert exc_info.value.status_code == 429


def test_account_lock_different_ips_same_username():
    """不同 IP 对同一用户名的失败累积到同一计数器"""
    _record_login_fail("1.1.1.1", "shared_user")
    _record_login_fail("2.2.2.2", "shared_user")
    _record_login_fail("3.3.3.3", "shared_user")
    _record_login_fail("4.4.4.4", "shared_user")
    _record_login_fail("5.5.5.5", "shared_user")
    with pytest.raises(HTTPException) as exc_info:
        _check_account_lock("shared_user")
    assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


# ─── 账户锁定配置与边界 ──────────────────────────────────────


def test_account_lock_config_defaults():
    """账户锁定配置默认值"""
    from app.core.config import settings

    assert settings.ACCOUNT_LOCK_MAX_FAILURES == 5
    assert settings.ACCOUNT_LOCK_WINDOW_SECONDS == 900


def test_account_lock_max_failures_is_positive():
    """锁定阈值必须为正数"""
    from app.core.config import settings

    assert settings.ACCOUNT_LOCK_MAX_FAILURES > 0


def test_account_lock_window_is_positive():
    """锁定窗口必须为正数"""
    from app.core.config import settings

    assert settings.ACCOUNT_LOCK_WINDOW_SECONDS > 0


def test_account_lock_threshold_minus_one_passes():
    """失败次数 = 阈值 - 1 不触发锁定"""
    for _ in range(settings.ACCOUNT_LOCK_MAX_FAILURES - 1):
        _record_login_fail("1.2.3.4", "almost_locked")
    _check_account_lock("almost_locked")  # 不抛异常


def test_account_lock_exactly_at_threshold_blocks():
    """失败次数恰好等于阈值触发锁定"""
    from app.core.config import settings

    for _ in range(settings.ACCOUNT_LOCK_MAX_FAILURES):
        _record_login_fail("1.2.3.4", "exact_locked")
    with pytest.raises(HTTPException) as exc_info:
        _check_account_lock("exact_locked")
    assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


def test_account_lock_window_expiry_allows_relogin():
    """窗口过期后可以再次登录"""
    import app.api.v1.auth as mod

    now = time.monotonic()
    old_time = now - settings.ACCOUNT_LOCK_WINDOW_SECONDS - 1
    mod._account_fail_counts["expired_user"] = [old_time] * settings.ACCOUNT_LOCK_MAX_FAILURES
    # 旧记录已过期，不触发锁定
    _check_account_lock("expired_user")


def test_account_lock_response_body_structure():
    """锁定响应体包含正确的 code 和 message"""
    for _ in range(settings.ACCOUNT_LOCK_MAX_FAILURES):
        _record_login_fail("1.2.3.4", "struct_user")
    with pytest.raises(HTTPException) as exc_info:
        _check_account_lock("struct_user")
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "ACCOUNT_LOCKED"
    assert isinstance(detail["message"], str)
    assert len(detail["message"]) > 0


def test_account_lock_case_sensitive_username():
    """用户名区分大小写（不同大小写独立计数）"""
    for _ in range(settings.ACCOUNT_LOCK_MAX_FAILURES):
        _record_login_fail("1.1.1.1", "TestUser")
    # 不同大小写的用户名不受影响
    _check_account_lock("testuser")
    _check_account_lock("TESTUSER")


def test_account_lock_empty_username_passes():
    """空用户名不触发锁定（无失败记录）"""
    _check_account_lock("")
