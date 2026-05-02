"""收款登记服务单元测试 — payment_service.register_payment"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base
from app.models.customer import Customer
from app.models.order import SalesOrder
from app.models.user import User
from app.schemas.payment import PaymentCreate
from app.services.payment_service import register_payment, reset_payment_debounce


@pytest.fixture(autouse=True)
def _reset_debounce():
    """每个测试前后清空收款防抖状态"""
    reset_payment_debounce()
    yield
    reset_payment_debounce()


@pytest.fixture()
def db():
    """每个测试独立内存 SQLite"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = maker()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _seed_user(db, is_superuser=False, suffix=""):
    uid = uuid.uuid4()
    db.add(User(
        id=uid, username=f"pay_user_{suffix}", hashed_password=hash_password("x"),
        display_name="u", is_active=True, is_superuser=is_superuser,
    ))
    db.flush()
    return uid


def _seed_order(db, sales_user_id, status="confirmed", total=1000, paid=0):
    cid = uuid.uuid4()
    db.add(Customer(id=cid, name="客户"))
    oid = uuid.uuid4()
    db.add(SalesOrder(
        id=oid, order_no=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cid,
        sales_user_id=sales_user_id, status=status,
        total_amount=Decimal(str(total)), paid_amount=Decimal(str(paid)),
        total_cost=Decimal("0"), gross_profit=Decimal("0"), gross_margin=Decimal("0"),
    ))
    db.flush()
    return oid


def test_register_payment_confirmed_order(db):
    """已确认订单登记收款 → 订单变为部分收款"""
    uid = _seed_user(db, is_superuser=True, suffix="R1")
    oid = _seed_order(db, uid, status="confirmed", total=1000, paid=0)

    data = PaymentCreate(amount="300", payment_method="cash")
    user = db.get(User, uid)
    result = register_payment(db, str(oid), data, user)
    db.flush()

    assert result["payment"].amount == Decimal("300")
    assert result["payment"].payment_method == "cash"
    assert result["payment"].status == "normal"
    order = db.get(SalesOrder, oid)
    assert order.paid_amount == Decimal("300")
    assert order.status == "partially_paid"


def test_register_payment_full_amount_completes_order(db):
    """全额收款 → 订单变为已完成"""
    uid = _seed_user(db, is_superuser=True, suffix="R2")
    oid = _seed_order(db, uid, status="confirmed", total=1000, paid=0)

    data = PaymentCreate(amount="1000", payment_method="transfer")
    register_payment(db, str(oid), data, db.get(User, uid))
    db.flush()

    order = db.get(SalesOrder, oid)
    assert order.paid_amount == Decimal("1000")
    assert order.status == "completed"


def test_register_payment_partial_then_full(db):
    """先部分收款再收尾款 → 订单完成"""
    uid = _seed_user(db, is_superuser=True, suffix="R3")
    oid = _seed_order(db, uid, status="confirmed", total=1000, paid=0)

    # 第一次部分收款
    data1 = PaymentCreate(amount="400", payment_method="wechat")
    register_payment(db, str(oid), data1, db.get(User, uid))
    db.flush()
    assert db.get(SalesOrder, oid).status == "partially_paid"

    # 第二次收尾款
    data2 = PaymentCreate(amount="600", payment_method="cash")
    register_payment(db, str(oid), data2, db.get(User, uid))
    db.flush()
    assert db.get(SalesOrder, oid).status == "completed"


def test_register_payment_order_not_found(db):
    """订单不存在抛 404"""
    uid = _seed_user(db, is_superuser=True, suffix="R4")
    data = PaymentCreate(amount="100", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(uuid.uuid4()), data, db.get(User, uid))
    assert exc_info.value.status_code == 404


def test_register_payment_draft_order_rejected(db):
    """草稿订单不可收款"""
    uid = _seed_user(db, is_superuser=True, suffix="R5")
    oid = _seed_order(db, uid, status="draft", total=1000)

    data = PaymentCreate(amount="100", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(oid), data, db.get(User, uid))
    assert exc_info.value.status_code == 400
    assert "已确认" in str(exc_info.value.detail) or "部分收款" in str(exc_info.value.detail)


def test_register_payment_cancelled_order_rejected(db):
    """已取消订单不可收款"""
    uid = _seed_user(db, is_superuser=True, suffix="R6")
    oid = _seed_order(db, uid, status="cancelled", total=1000)

    data = PaymentCreate(amount="100", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(oid), data, db.get(User, uid))
    assert exc_info.value.status_code == 400


def test_register_payment_completed_order_rejected(db):
    """已完成订单不可收款"""
    uid = _seed_user(db, is_superuser=True, suffix="R7")
    oid = _seed_order(db, uid, status="completed", total=1000)

    data = PaymentCreate(amount="100", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(oid), data, db.get(User, uid))
    assert exc_info.value.status_code == 400


def test_register_payment_amount_exceeded(db):
    """超额收款被拒绝"""
    uid = _seed_user(db, is_superuser=True, suffix="R8")
    oid = _seed_order(db, uid, status="confirmed", total=1000, paid=800)

    data = PaymentCreate(amount="300", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(oid), data, db.get(User, uid))
    assert exc_info.value.status_code == 400
    assert "超过" in str(exc_info.value.detail)


def test_register_payment_exact_remaining_ok(db):
    """恰好等于剩余应收金额通过"""
    uid = _seed_user(db, is_superuser=True, suffix="R9")
    oid = _seed_order(db, uid, status="confirmed", total=1000, paid=800)

    data = PaymentCreate(amount="200", payment_method="alipay")
    register_payment(db, str(oid), data, db.get(User, uid))
    db.flush()
    assert db.get(SalesOrder, oid).status == "completed"


def test_register_payment_operator_recorded(db):
    """操作人和更新人正确记录"""
    uid = _seed_user(db, is_superuser=True, suffix="R10")
    oid = _seed_order(db, uid, status="confirmed", total=1000)

    data = PaymentCreate(amount="100", payment_method="cash", remark="测试")
    result = register_payment(db, str(oid), data, db.get(User, uid))
    db.flush()

    assert result["payment"].operator_id == uid
    order = db.get(SalesOrder, oid)
    assert order.updated_by == uid
    assert result["payment"].remark == "测试"


def test_register_payment_debounce_blocks_rapid_duplicate(db):
    """同一订单有请求处理中时第二次收款被 429 拦截"""
    from app.services.payment_service import _payment_inflight, _payment_lock

    uid = _seed_user(db, is_superuser=True, suffix="D1")
    oid = _seed_order(db, uid, status="confirmed", total=2000, paid=0)
    order_id_str = str(oid)

    # 手动模拟 inflight 状态
    with _payment_lock:
        _payment_inflight.add(order_id_str)

    data = PaymentCreate(amount="500", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, order_id_str, data, db.get(User, uid))
    assert exc_info.value.status_code == 429
    assert "PAYMENT_RATE_LIMITED" in str(exc_info.value.detail)

    # 清除后可正常提交
    reset_payment_debounce()
    result = register_payment(db, order_id_str, data, db.get(User, uid))
    db.flush()
    assert result["payment"].amount == Decimal("500")


def test_register_payment_debounce_different_orders_ok(db):
    """不同订单的收款互不干扰"""
    uid = _seed_user(db, is_superuser=True, suffix="D2")
    oid1 = _seed_order(db, uid, status="confirmed", total=1000, paid=0)
    oid2 = _seed_order(db, uid, status="confirmed", total=1000, paid=0)

    data1 = PaymentCreate(amount="100", payment_method="cash")
    register_payment(db, str(oid1), data1, db.get(User, uid))
    db.flush()

    # 不同订单不受影响
    data2 = PaymentCreate(amount="100", payment_method="cash")
    result = register_payment(db, str(oid2), data2, db.get(User, uid))
    db.flush()
    assert result["payment"].amount == Decimal("100")


def test_register_payment_debounce_clears_on_failure(db):
    """收款失败时 inflight 标记被清除，可立即重试"""
    uid = _seed_user(db, is_superuser=True, suffix="D3")
    oid = _seed_order(db, uid, status="confirmed", total=500, paid=0)

    # 第一次超额收款 → 400 失败
    data_bad = PaymentCreate(amount="9999", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(oid), data_bad, db.get(User, uid))
    assert exc_info.value.status_code == 400

    # inflight 已被清除，正确金额可立即提交
    data_ok = PaymentCreate(amount="100", payment_method="cash")
    result = register_payment(db, str(oid), data_ok, db.get(User, uid))
    db.flush()
    assert result["payment"].amount == Decimal("100")
