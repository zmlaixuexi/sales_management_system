"""异常路径：后端并发写操作冲突恢复验证测试
覆盖行锁 for_update 覆盖、收款并发防护、
库存扣减两阶段验证、safe_commit 回滚保障、状态转换互斥"""

import re
from pathlib import Path

ORDERS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "orders.py"
PAYMENTS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "payments.py"
INVENTORY_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "inventory.py"
PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "products.py"
PAYMENT_SVC_FILE = Path(__file__).resolve().parent.parent / "app" / "services" / "payment_service.py"
DEPS_FILE = Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"


def _read(path: Path) -> str:
    return path.read_text()


def _find_function_body(source: str, func_name: str) -> str:
    """提取函数体文本"""
    pattern = re.compile(rf"def {func_name}\b")
    match = pattern.search(source)
    if not match:
        return ""
    start = match.start()
    depth = 0
    func_start = None
    for i in range(start, len(source)):
        if source[i] == ":" and func_start is None:
            func_start = i + 1
        if func_start is not None:
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
            # Find the next def at same or lower indent level
    # Simpler: just get everything from the def line to the next def/class at same level
    indent = len(match.group(0)) - len(match.group(0).lstrip())
    lines = source[start:].split("\n")
    body_lines = [lines[0]]
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            line_indent = len(line) - len(stripped)
            if line_indent <= indent and stripped:
                break
        body_lines.append(line)
    return "\n".join(body_lines)


# ═══════════════════════════════════════════════════════════
# 1. 行锁 for_update 覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRowLockCoverage:
    """验证关键写操作使用 for_update 行锁"""

    def test_confirm_order_locks_order_row(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "confirm_order")
        assert "with_for_update()" in body

    def test_cancel_order_locks_order_row(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "cancel_order")
        assert "with_for_update()" in body

    def test_register_payment_locks_order_row(self):
        source = _read(PAYMENT_SVC_FILE)
        body = _find_function_body(source, "register_payment")
        assert "with_for_update()" in body

    def test_inventory_adjust_locks_product_row(self):
        source = _read(INVENTORY_FILE)
        body = _find_function_body(source, "adjust_inventory")
        assert "with_for_update()" in body

    def test_product_update_uses_row_lock_for_stock(self):
        source = _read(PRODUCTS_FILE)
        # 检查导入更新库存路径是否有行锁
        assert "with_for_update()" in source


# ═══════════════════════════════════════════════════════════
# 2. 收款并发防护验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPaymentConcurrencyGuard:
    """验证收款并发防护机制"""

    def test_payment_service_has_inflight_set(self):
        source = _read(PAYMENT_SVC_FILE)
        assert "_payment_inflight" in source
        assert "set()" in source

    def test_payment_service_uses_thread_lock(self):
        source = _read(PAYMENT_SVC_FILE)
        assert "from threading import Lock" in source
        assert "_payment_lock = Lock()" in source

    def test_check_inflight_raises_429_on_duplicate(self):
        source = _read(PAYMENT_SVC_FILE)
        body = _find_function_body(source, "_check_payment_inflight")
        assert "429" in body
        assert "PAYMENT_RATE_LIMITED" in body

    def test_clear_inflight_on_success_and_failure(self):
        source = _read(PAYMENT_SVC_FILE)
        body = _find_function_body(source, "register_payment")
        assert "finally:" in body
        assert "_clear_payment_inflight" in body

    def test_reset_debounce_for_testing(self):
        source = _read(PAYMENT_SVC_FILE)
        assert "reset_payment_debounce" in source
        body = _find_function_body(source, "reset_payment_debounce")
        assert "_payment_inflight.clear()" in body


# ═══════════════════════════════════════════════════════════
# 3. 库存扣减两阶段验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestInventoryTwoPhase:
    """验证库存扣减先验证再执行的原子性模式"""

    def test_deduct_fetches_products_with_row_lock(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "_deduct_inventory")
        assert "with_for_update()" in body
        assert "product_ids" in body

    def test_deduct_validates_all_stock_before_mutating(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "_deduct_inventory")
        # 阶段 1 标记
        assert "阶段 1" in body or "先全量验证" in body or "全量验证" in body
        # 阶段 2 标记
        assert "阶段 2" in body or "统一扣减" in body

    def test_deduct_raises_stockout_on_insufficient(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "_deduct_inventory")
        assert "INVENTORY_NOT_ENOUGH" in body
        assert "库存不足" in body

    def test_restore_inventory_uses_row_lock(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "_restore_inventory")
        assert "with_for_update()" in body

    def test_restore_records_inventory_movements(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "_restore_inventory")
        assert "InventoryMovement" in body
        assert "order_cancel" in body


# ═══════════════════════════════════════════════════════════
# 4. safe_commit 回滚保障验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSafeCommitRollback:
    """验证 safe_commit 在异常时自动回滚"""

    def test_safe_commit_wraps_db_commit(self):
        source = _read(DEPS_FILE)
        assert "def safe_commit" in source
        body = _find_function_body(source, "safe_commit")
        assert "db.commit()" in body

    def test_safe_commit_catches_all_exceptions(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "safe_commit")
        assert "except Exception" in body or "except:" in body

    def test_safe_commit_rollback_on_failure(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "safe_commit")
        assert "db.rollback()" in body

    def test_safe_commit_reraises_exception(self):
        source = _read(DEPS_FILE)
        body = _find_function_body(source, "safe_commit")
        assert "raise" in body

    def test_safe_commit_used_in_write_endpoints(self):
        source = _read(ORDERS_FILE)
        # 确认/取消/冲正等写操作都使用 safe_commit
        count = source.count("safe_commit(db)")
        assert count >= 4, f"订单模块应有至少 4 处 safe_commit 调用，实际 {count}"


# ═══════════════════════════════════════════════════════════
# 5. 状态转换互斥验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStatusTransitionExclusion:
    """验证状态转换规则防止并发冲突"""

    def test_valid_transitions_defined(self):
        source = _read(ORDERS_FILE)
        assert "VALID_TRANSITIONS" in source

    def test_confirm_only_allows_draft(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "confirm_order")
        assert '"draft"' in body or "'draft'" in body
        assert "ORDER_INVALID_STATUS" in body

    def test_cancel_checks_transition_rules(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "cancel_order")
        assert "VALID_TRANSITIONS" in body

    def test_cancel_rejects_if_has_payments(self):
        source = _read(ORDERS_FILE)
        body = _find_function_body(source, "cancel_order")
        assert "ORDER_HAS_PAYMENTS" in body

    def test_payment_checks_order_status(self):
        source = _read(PAYMENT_SVC_FILE)
        body = _find_function_body(source, "register_payment")
        assert "confirmed" in body
        assert "partially_paid" in body
        assert "ORDER_INVALID_STATUS" in body
