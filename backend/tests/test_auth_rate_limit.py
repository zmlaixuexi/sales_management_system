"""登录速率限制辅助函数单元测试 — _check_login_rate_limit / _record_login_fail"""

import time
from collections import defaultdict
from threading import Lock

import pytest
from fastapi import HTTPException

from app.api.v1.auth import _check_login_rate_limit, _record_login_fail


@pytest.fixture(autouse=True)
def _reset_counts():
    """每个测试前重置速率限制计数器"""
    import app.api.v1.auth as mod

    original_counts = mod._login_fail_counts
    original_lock = mod._login_fail_lock
    mod._login_fail_counts = defaultdict(list)
    mod._login_fail_lock = Lock()
    yield
    mod._login_fail_counts = original_counts
    mod._login_fail_lock = original_lock


def test_check_rate_limit_passes_under_threshold():
    """失败次数未达阈值时通过"""
    for _ in range(9):
        _record_login_fail("1.2.3.4")
    _check_login_rate_limit("1.2.3.4")  # 不抛异常


def test_check_rate_limit_blocks_at_threshold():
    """失败次数达到阈值时抛 429"""
    for _ in range(10):
        _record_login_fail("1.2.3.4")
    with pytest.raises(HTTPException) as exc_info:
        _check_login_rate_limit("1.2.3.4")
    assert exc_info.value.status_code == 429
    assert "登录失败次数过多" in str(exc_info.value.detail)


def test_check_rate_limit_independent_ips():
    """不同 IP 独立计数"""
    for _ in range(10):
        _record_login_fail("1.1.1.1")
    # 2.2.2.2 应该不受影响
    _check_login_rate_limit("2.2.2.2")


def test_record_login_fail_appends_timestamp():
    """记录失败时间戳"""
    import app.api.v1.auth as mod

    _record_login_fail("10.0.0.1")
    assert len(mod._login_fail_counts["10.0.0.1"]) == 1
    _record_login_fail("10.0.0.1")
    assert len(mod._login_fail_counts["10.0.0.1"]) == 2


def test_check_rate_limit_expired_entries_cleaned():
    """过期的失败记录被清理"""
    import app.api.v1.auth as mod

    old_time = time.monotonic() - 1000  # 超过 15 分钟窗口
    mod._login_fail_counts["3.3.3.3"] = [old_time] * 10
    _check_login_rate_limit("3.3.3.3")  # 旧记录被清理，不抛异常
