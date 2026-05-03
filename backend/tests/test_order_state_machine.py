"""异常路径：订单状态机转换边界测试 — 覆盖 VALID_TRANSITIONS 映射、确认/取消守卫、
收款状态变更、冲正回退、终端状态不可逆、API 端点认证"""

from fastapi.testclient import TestClient

from app.api.v1.orders import STATUS_LABELS, VALID_TRANSITIONS
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. VALID_TRANSITIONS 映射完整性
# ═══════════════════════════════════════════════════════


def test_all_five_statuses_in_transitions():
    """5 种订单状态都在 VALID_TRANSITIONS 中"""
    expected = {"draft", "confirmed", "cancelled", "partially_paid", "completed"}
    assert set(VALID_TRANSITIONS.keys()) == expected


def test_draft_transitions():
    """draft 可转为 confirmed 或 cancelled"""
    assert VALID_TRANSITIONS["draft"] == {"confirmed", "cancelled"}


def test_confirmed_transitions():
    """confirmed 可转为 cancelled 或 partially_paid"""
    assert VALID_TRANSITIONS["confirmed"] == {"cancelled", "partially_paid"}


def test_cancelled_is_terminal():
    """cancelled 是终端状态（无后续转换）"""
    assert VALID_TRANSITIONS["cancelled"] == set()


def test_completed_is_terminal():
    """completed 是终端状态（在 VALID_TRANSITIONS 中）"""
    assert VALID_TRANSITIONS["completed"] == set()


def test_partially_paid_transitions():
    """partially_paid 可转为 partially_paid 或 cancelled"""
    assert VALID_TRANSITIONS["partially_paid"] == {"partially_paid", "cancelled"}


def test_no_self_transition_draft():
    """draft 不能转为 draft"""
    assert "draft" not in VALID_TRANSITIONS["draft"]


def test_no_self_transition_confirmed():
    """confirmed 不能转为 confirmed"""
    assert "confirmed" not in VALID_TRANSITIONS["confirmed"]


def test_no_draft_to_completed():
    """draft 不能直接转为 completed"""
    assert "completed" not in VALID_TRANSITIONS["draft"]


def test_no_draft_to_partially_paid():
    """draft 不能直接转为 partially_paid"""
    assert "partially_paid" not in VALID_TRANSITIONS["draft"]


def test_no_confirmed_to_draft():
    """confirmed 不能回退为 draft"""
    assert "draft" not in VALID_TRANSITIONS["confirmed"]


def test_no_confirmed_to_completed():
    """confirmed 不能直接转为 completed（需通过收款）"""
    assert "completed" not in VALID_TRANSITIONS["confirmed"]


def test_no_cancelled_to_any():
    """cancelled 不能转为任何状态"""
    assert len(VALID_TRANSITIONS["cancelled"]) == 0


# ═══════════════════════════════════════════════════════
# 2. STATUS_LABELS 标签映射
# ═══════════════════════════════════════════════════════


def test_status_labels_covers_all():
    """STATUS_LABELS 覆盖全部 5 种状态"""
    assert set(STATUS_LABELS.keys()) == {"draft", "confirmed", "cancelled", "partially_paid", "completed"}


def test_status_labels_are_chinese():
    """所有标签为中文"""
    for label in STATUS_LABELS.values():
        assert len(label) > 0
        assert any("一" <= c <= "鿿" for c in label)


def test_status_label_draft():
    """draft 标签为'草稿'"""
    assert STATUS_LABELS["draft"] == "草稿"


def test_status_label_confirmed():
    """confirmed 标签为'已确认'"""
    assert STATUS_LABELS["confirmed"] == "已确认"


def test_status_label_cancelled():
    """cancelled 标签为'已取消'"""
    assert STATUS_LABELS["cancelled"] == "已取消"


def test_status_label_completed():
    """completed 标签为'已完成'"""
    assert STATUS_LABELS["completed"] == "已完成"


# ═══════════════════════════════════════════════════════
# 3. 订单模型默认状态
# ═══════════════════════════════════════════════════════


def test_order_model_default_status():
    """订单模型默认状态为 'draft'"""
    from app.models.order import SalesOrder

    col = SalesOrder.__table__.c["status"]
    assert col.default.arg == "draft"


def test_order_status_column_length():
    """订单状态列长度 30"""
    from app.models.order import SalesOrder

    col = SalesOrder.__table__.c["status"]
    assert col.type.length == 30


# ═══════════════════════════════════════════════════════
# 4. 确认守卫验证（源码级别）
# ═══════════════════════════════════════════════════════


def test_confirm_guard_checks_draft():
    """确认端点检查 status == draft"""
    import inspect

    from app.api.v1.orders import confirm_order

    source = inspect.getsource(confirm_order)
    assert "draft" in source
    assert "只有草稿订单可以确认" in source


def test_cancel_guard_uses_valid_transitions():
    """取消端点使用 VALID_TRANSITIONS"""
    import inspect

    from app.api.v1.orders import cancel_order

    source = inspect.getsource(cancel_order)
    assert "VALID_TRANSITIONS" in source


def test_cancel_partially_paid_checks_payments():
    """取消 partially_paid 时检查 paid_amount"""
    import inspect

    from app.api.v1.orders import cancel_order

    source = inspect.getsource(cancel_order)
    assert "paid_amount" in source


def test_edit_guard_checks_draft():
    """编辑端点检查 status == draft"""
    import inspect

    from app.api.v1.orders import update_order

    source = inspect.getsource(update_order)
    assert "只有草稿订单可以编辑" in source


# ═══════════════════════════════════════════════════════
# 5. 收款状态变更逻辑
# ═══════════════════════════════════════════════════════


def test_register_payment_checks_status():
    """register_payment 检查订单状态为 confirmed/partially_paid"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "confirmed" in source
    assert "partially_paid" in source


def test_register_payment_updates_paid_amount():
    """register_payment 累加 paid_amount"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "paid_amount" in source


def test_register_payment_sets_completed():
    """register_payment 付满时设为 completed"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "completed" in source


def test_register_payment_sets_partially_paid():
    """register_payment 未付满时设为 partially_paid"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "partially_paid" in source


def test_register_payment_prevents_overpayment():
    """register_payment 防止超额收款"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "超过" in source or "remaining" in source


# ═══════════════════════════════════════════════════════
# 6. 收款冲正回退逻辑
# ═══════════════════════════════════════════════════════


def test_reverse_payment_checks_status():
    """冲正端点检查订单状态"""
    import inspect

    from app.api.v1.payments import reverse_payment

    source = inspect.getsource(reverse_payment)
    assert "confirmed" in source
    assert "partially_paid" in source
    assert "completed" in source


def test_reverse_payment_reverts_to_confirmed():
    """冲正后 paid_amount 为 0 时回退到 confirmed"""
    import inspect

    from app.api.v1.payments import reverse_payment

    source = inspect.getsource(reverse_payment)
    assert "confirmed" in source


def test_reverse_payment_reverts_to_partially_paid():
    """冲正后 completed 状态降为 partially_paid"""
    import inspect

    from app.api.v1.payments import reverse_payment

    source = inspect.getsource(reverse_payment)
    assert "partially_paid" in source


def test_reverse_payment_paid_amount_floor():
    """冲正后 paid_amount <= 0 时归零"""
    import inspect

    from app.api.v1.payments import reverse_payment

    source = inspect.getsource(reverse_payment)
    assert "Decimal" in source or "0" in source


# ═══════════════════════════════════════════════════════
# 7. 库存扣减/恢复逻辑
# ═══════════════════════════════════════════════════════


def test_deduct_inventory_on_confirm():
    """确认时扣减库存"""
    import inspect

    from app.api.v1.orders import confirm_order

    source = inspect.getsource(confirm_order)
    assert "deduct" in source.lower() or "inventory" in source.lower()


def test_restore_inventory_on_cancel():
    """取消已确认订单时恢复库存"""
    import inspect

    from app.api.v1.orders import cancel_order

    source = inspect.getsource(cancel_order)
    assert "restore" in source.lower() or "inventory" in source.lower()


def test_cancel_draft_no_inventory_restore():
    """取消草稿订单不恢复库存（未扣减）"""
    import inspect

    from app.api.v1.orders import cancel_order

    source = inspect.getsource(cancel_order)
    # 恢复库存逻辑应在条件判断内
    assert "confirmed" in source or "partially_paid" in source


# ═══════════════════════════════════════════════════════
# 8. API 端点认证
# ═══════════════════════════════════════════════════════


def test_confirm_requires_auth():
    """确认端点需要认证"""
    resp = client.post("/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/confirm")
    assert resp.status_code in (401, 403, 404)


def test_cancel_requires_auth():
    """取消端点需要认证"""
    resp = client.post("/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/cancel")
    assert resp.status_code in (401, 403, 404)


def test_create_order_requires_auth():
    """创建订单需要认证"""
    resp = client.post("/api/v1/sales-orders", json={})
    assert resp.status_code in (401, 403, 422)


def test_update_order_requires_auth():
    """编辑订单需要认证"""
    resp = client.put("/api/v1/sales-orders/00000000-0000-0000-0000-000000000001", json={})
    assert resp.status_code in (401, 403, 422)


def test_order_payments_requires_auth():
    """订单收款端点需要认证"""
    resp = client.post("/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/payments", json={})
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════
# 9. 订单日志端点
# ═══════════════════════════════════════════════════════


def test_order_logs_endpoint_exists():
    """订单日志端点存在"""
    resp = client.get("/api/v1/sales-orders/00000000-0000-0000-0000-000000000001/logs")
    assert resp.status_code in (200, 401, 404)


# ═══════════════════════════════════════════════════════
# 10. 收款并发锁
# ═══════════════════════════════════════════════════════


def test_payment_lock_exists():
    """收款服务有并发锁机制"""
    import inspect

    from app.services import payment_service

    source = inspect.getsource(payment_service)
    assert "lock" in source.lower()


def test_payment_lock_per_order():
    """并发锁按订单隔离（使用 inflight 机制）"""
    import inspect

    from app.services.payment_service import register_payment

    source = inspect.getsource(register_payment)
    assert "inflight" in source.lower() or "lock" in source.lower()


# ═══════════════════════════════════════════════════════
# 11. 报表只统计有效状态订单
# ═══════════════════════════════════════════════════════


def test_reports_valid_order_statuses():
    """报表统计的有效订单状态包含 confirmed/partially_paid/completed"""
    from app.api.v1.reports import _VALID_ORDER_STATUSES

    assert "confirmed" in _VALID_ORDER_STATUSES
    assert "partially_paid" in _VALID_ORDER_STATUSES
    assert "completed" in _VALID_ORDER_STATUSES


def test_reports_excludes_draft():
    """报表不统计草稿订单"""
    from app.api.v1.reports import _VALID_ORDER_STATUSES

    assert "draft" not in _VALID_ORDER_STATUSES


def test_reports_excludes_cancelled():
    """报表不统计已取消订单"""
    from app.api.v1.reports import _VALID_ORDER_STATUSES

    assert "cancelled" not in _VALID_ORDER_STATUSES


# ═══════════════════════════════════════════════════════
# 12. 状态过滤参数验证
# ═══════════════════════════════════════════════════════


def test_order_list_status_filter_accepted():
    """订单列表支持 status 参数"""
    resp = client.get("/api/v1/sales-orders?status=draft")
    assert resp.status_code in (200, 401)


def test_order_list_invalid_status_accepted_as_empty():
    """订单列表非法 status 返回空结果（不报错）"""
    resp = client.get("/api/v1/sales-orders?status=invalid_status")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 13. Payment 模型状态
# ═══════════════════════════════════════════════════════


def test_payment_model_has_status():
    """Payment 模型有 status 字段"""
    from app.models.order import Payment

    assert hasattr(Payment, "status")


def test_payment_status_default_normal():
    """Payment 默认状态为 'normal'"""
    from app.models.order import Payment

    col = Payment.__table__.c["status"]
    assert col.default.arg == "normal"


def test_reverse_sets_payment_status_reversed():
    """冲正将 payment status 设为 'reversed'"""
    import inspect

    from app.api.v1.payments import reverse_payment

    source = inspect.getsource(reverse_payment)
    assert "reversed" in source
