"""收款服务辅助函数单元测试 — _check_payment_inflight / _clear_payment_inflight / reset_payment_debounce"""

import pytest
from fastapi import HTTPException

from app.services.payment_service import (
    _check_payment_inflight,
    _clear_payment_inflight,
    reset_payment_debounce,
)


@pytest.fixture(autouse=True)
def _clean_inflight():
    """每个测试前后清空进行中标记"""
    reset_payment_debounce()
    yield
    reset_payment_debounce()


# ─── _check_payment_inflight ───────────────────────────────────


def test_check_inflight_passes():
    """无进行中标记时通过"""
    _check_payment_inflight("order-1")  # 不抛异常


def test_check_inflight_rejects_duplicate():
    """同一订单已有进行中标记时拒绝"""
    _check_payment_inflight("order-1")
    with pytest.raises(HTTPException) as exc_info:
        _check_payment_inflight("order-1")
    assert exc_info.value.status_code == 429
    assert "PAYMENT_RATE_LIMITED" in str(exc_info.value.detail)


def test_check_inflight_different_orders():
    """不同订单互不影响"""
    _check_payment_inflight("order-1")
    _check_payment_inflight("order-2")  # 不抛异常


def test_check_inflight_adds_to_set():
    """成功检查后订单标记被加入集合"""
    from app.services.payment_service import _payment_inflight
    _check_payment_inflight("order-abc")
    assert "order-abc" in _payment_inflight


# ─── _clear_payment_inflight ───────────────────────────────────


def test_clear_inflight_removes_mark():
    """清除后可重新提交"""
    _check_payment_inflight("order-1")
    _clear_payment_inflight("order-1")
    _check_payment_inflight("order-1")  # 不抛异常


def test_clear_inflight_idempotent():
    """清除不存在的标记不报错"""
    _clear_payment_inflight("nonexistent")  # 不抛异常


def test_clear_only_target():
    """只清除目标订单标记"""
    _check_payment_inflight("order-1")
    _check_payment_inflight("order-2")
    _clear_payment_inflight("order-1")
    # order-2 仍然被锁
    with pytest.raises(HTTPException):
        _check_payment_inflight("order-2")
    # order-1 已解锁
    _check_payment_inflight("order-1")


# ─── reset_payment_debounce ────────────────────────────────────


def test_reset_clears_all():
    """清空全部进行中标记"""
    _check_payment_inflight("a")
    _check_payment_inflight("b")
    reset_payment_debounce()
    _check_payment_inflight("a")  # 不抛异常
    _check_payment_inflight("b")  # 不抛异常


def test_reset_on_empty():
    """空集合上 reset 不报错"""
    reset_payment_debounce()  # 不抛异常
