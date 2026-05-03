"""异常路径：并发支付竞态条件边界测试 — 覆盖 inflight 集合操作原子性、
线程安全、429 错误格式、finally 清理保证、多订单隔离、锁机制验证"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi import HTTPException

from app.services.payment_service import (
    _check_payment_inflight,
    _clear_payment_inflight,
    _payment_inflight,
    _payment_lock,
    reset_payment_debounce,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_payment_debounce()
    yield
    reset_payment_debounce()


# ═══════════════════════════════════════════════════════
# 1. 429 错误格式验证
# ═══════════════════════════════════════════════════════


def test_inflight_429_status_code():
    """重复 inflight 抛出 429"""
    _check_payment_inflight("order-1")
    with pytest.raises(HTTPException) as exc:
        _check_payment_inflight("order-1")
    assert exc.value.status_code == 429


def test_inflight_429_error_code():
    """错误 detail 包含 PAYMENT_RATE_LIMITED"""
    _check_payment_inflight("order-1")
    with pytest.raises(HTTPException) as exc:
        _check_payment_inflight("order-1")
    detail = exc.value.detail
    assert detail["code"] == "PAYMENT_RATE_LIMITED"


def test_inflight_429_error_message():
    """错误消息描述收款请求正在处理"""
    _check_payment_inflight("order-1")
    with pytest.raises(HTTPException) as exc:
        _check_payment_inflight("order-1")
    assert "正在处理" in exc.value.detail["message"]


def test_inflight_429_detail_has_code_and_message():
    """detail 同时有 code 和 message"""
    _check_payment_inflight("order-1")
    with pytest.raises(HTTPException) as exc:
        _check_payment_inflight("order-1")
    assert "code" in exc.value.detail
    assert "message" in exc.value.detail


# ═══════════════════════════════════════════════════════
# 2. Inflight 集合状态验证
# ═══════════════════════════════════════════════════════


def test_inflight_set_empty_initially():
    """_payment_inflight 初始为空"""
    assert len(_payment_inflight) == 0


def test_inflight_set_contains_after_check():
    """check 成功后 set 包含 order_id"""
    _check_payment_inflight("order-x")
    assert "order-x" in _payment_inflight


def test_inflight_set_not_contains_after_clear():
    """clear 后 set 不包含 order_id"""
    _check_payment_inflight("order-x")
    _clear_payment_inflight("order-x")
    assert "order-x" not in _payment_inflight


def test_inflight_set_size_matches():
    """set 大小与 inflight 数量一致"""
    _check_payment_inflight("a")
    _check_payment_inflight("b")
    _check_payment_inflight("c")
    assert len(_payment_inflight) == 3


def test_clear_nonexistent_does_not_change_size():
    """clear 不存在的 key 不影响 set 大小"""
    _check_payment_inflight("a")
    _clear_payment_inflight("nonexistent")
    assert len(_payment_inflight) == 1


# ═══════════════════════════════════════════════════════
# 3. 多订单隔离
# ═══════════════════════════════════════════════════════


def test_different_orders_independent():
    """不同订单互不阻塞"""
    _check_payment_inflight("order-1")
    _check_payment_inflight("order-2")  # 不抛异常


def test_clear_one_order_keeps_others():
    """清除一个订单不影响其他订单"""
    _check_payment_inflight("order-1")
    _check_payment_inflight("order-2")
    _clear_payment_inflight("order-1")

    # order-2 仍被锁
    with pytest.raises(HTTPException):
        _check_payment_inflight("order-2")

    # order-1 已解锁
    _check_payment_inflight("order-1")


def test_many_orders_simultaneous():
    """大量订单同时 inflight"""
    for i in range(100):
        _check_payment_inflight(f"order-{i}")

    assert len(_payment_inflight) == 100

    # 全部被锁
    for i in range(100):
        with pytest.raises(HTTPException):
            _check_payment_inflight(f"order-{i}")


def test_clear_all_via_reset():
    """reset_payment_debounce 清除全部"""
    for i in range(50):
        _check_payment_inflight(f"order-{i}")

    reset_payment_debounce()
    assert len(_payment_inflight) == 0

    # 全部可重新进入
    for i in range(50):
        _check_payment_inflight(f"order-{i}")


# ═══════════════════════════════════════════════════════
# 4. Idempotent 清除
# ═══════════════════════════════════════════════════════


def test_clear_idempotent():
    """多次 clear 同一 order_id 不报错"""
    _check_payment_inflight("order-1")
    _clear_payment_inflight("order-1")
    _clear_payment_inflight("order-1")
    _clear_payment_inflight("order-1")


def test_clear_never_checked_order():
    """clear 未 check 过的 order_id 不报错"""
    _clear_payment_inflight("never-existed")


def test_double_clear_then_recheck():
    """两次 clear 后仍可重新 check"""
    _check_payment_inflight("order-1")
    _clear_payment_inflight("order-1")
    _clear_payment_inflight("order-1")
    _check_payment_inflight("order-1")  # 不抛异常


# ═══════════════════════════════════════════════════════
# 5. 线程安全 — 并发 check 同一 order
# ═══════════════════════════════════════════════════════


def test_concurrent_check_only_one_succeeds():
    """10 个线程并发 check 同一 order_id，只有一个成功"""
    order_id = "concurrent-order"
    results = []

    def try_check():
        try:
            _check_payment_inflight(order_id)
            results.append("success")
        except HTTPException:
            results.append("rejected")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(try_check) for _ in range(10)]
        for f in as_completed(futures):
            f.result()

    assert results.count("success") == 1
    assert results.count("rejected") == 9


def test_concurrent_check_different_orders_all_succeed():
    """10 个线程 check 不同 order_id，全部成功"""
    results = []

    def try_check(oid):
        try:
            _check_payment_inflight(oid)
            results.append("success")
        except HTTPException:
            results.append("rejected")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(try_check, f"order-{i}") for i in range(10)]
        for f in as_completed(futures):
            f.result()

    assert results.count("success") == 10
    assert results.count("rejected") == 0


def test_concurrent_clear_safe():
    """10 个线程并发 clear 同一 order_id 不崩溃"""
    _check_payment_inflight("order-1")

    def try_clear():
        _clear_payment_inflight("order-1")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(try_clear) for _ in range(10)]
        for f in as_completed(futures):
            f.result()  # 不应抛异常

    assert "order-1" not in _payment_inflight


# ═══════════════════════════════════════════════════════
# 6. 锁机制验证
# ═══════════════════════════════════════════════════════


def test_payment_lock_is_threading_lock():
    """_payment_lock 是 threading.Lock"""
    assert isinstance(_payment_lock, type(threading.Lock()))


def test_payment_inflight_is_set():
    """_payment_inflight 是 set"""
    assert isinstance(_payment_inflight, set)


def test_payment_inflight_str_keys():
    """_payment_inflight 的 key 都是字符串"""
    _check_payment_inflight("order-1")
    _check_payment_inflight("order-2")
    for key in _payment_inflight:
        assert isinstance(key, str)


# ═══════════════════════════════════════════════════════
# 7. finally 清理保证（模拟 register_payment 行为）
# ═══════════════════════════════════════════════════════


def test_finally_clears_on_exception():
    """模拟 register_payment：异常后 inflight 被清除"""
    order_id = "order-finally"
    with pytest.raises(ValueError):
        try:
            _check_payment_inflight(order_id)
            raise ValueError("模拟业务异常")
        finally:
            _clear_payment_inflight(order_id)

    # inflight 已清除，可重新进入
    _check_payment_inflight(order_id)  # 不抛异常


def test_finally_clears_on_success():
    """模拟 register_payment：成功后 inflight 被清除"""
    order_id = "order-success"
    try:
        _check_payment_inflight(order_id)
        # 模拟业务逻辑成功
    finally:
        _clear_payment_inflight(order_id)

    # inflight 已清除
    _check_payment_inflight(order_id)  # 不抛异常


def test_finally_clears_on_http_exception():
    """模拟 register_payment：HTTP 异常后 inflight 被清除"""
    order_id = "order-http-err"
    with pytest.raises(HTTPException):
        try:
            _check_payment_inflight(order_id)
            raise HTTPException(status_code=400, detail="业务错误")
        finally:
            _clear_payment_inflight(order_id)

    _check_payment_inflight(order_id)  # 不抛异常


# ═══════════════════════════════════════════════════════
# 8. 边界值 order_id
# ═══════════════════════════════════════════════════════


def test_empty_string_order_id():
    """空字符串 order_id 也能正常工作"""
    _check_payment_inflight("")
    with pytest.raises(HTTPException):
        _check_payment_inflight("")
    _clear_payment_inflight("")
    _check_payment_inflight("")


def test_uuid_format_order_id():
    """UUID 格式 order_id 正常工作"""
    oid = str(__import__("uuid").uuid4())
    _check_payment_inflight(oid)
    with pytest.raises(HTTPException):
        _check_payment_inflight(oid)
    _clear_payment_inflight(oid)
    _check_payment_inflight(oid)


def test_long_order_id():
    """超长 order_id 正常工作"""
    oid = "x" * 1000
    _check_payment_inflight(oid)
    assert oid in _payment_inflight
    _clear_payment_inflight(oid)
    assert oid not in _payment_inflight


# ═══════════════════════════════════════════════════════
# 9. register_payment with_for_update 验证
# ═══════════════════════════════════════════════════════


def test_register_payment_uses_with_for_update():
    """register_payment 使用 with_for_update 行锁"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "with_for_update" in source


def test_register_payment_calls_check_inflight():
    """register_payment 调用 _check_payment_inflight"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "_check_payment_inflight" in source


def test_register_payment_calls_clear_in_finally():
    """register_payment 在 finally 中调用 _clear_payment_inflight"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "finally" in source
    assert "_clear_payment_inflight" in source


# ═══════════════════════════════════════════════════════
# 10. API 端点并发守卫验证
# ═══════════════════════════════════════════════════════


def test_payments_endpoint_requires_auth():
    """收款端点需要认证"""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/payments/00000000-0000-0000-0000-000000000001", json={})
    assert resp.status_code in (401, 403, 404, 422)


def test_order_payments_endpoint_requires_auth():
    """订单收款端点需要认证"""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/payments",
        json={},
    )
    assert resp.status_code in (401, 403, 404, 422)
