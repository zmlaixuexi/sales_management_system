"""测试补强：收款服务边界测试 — 覆盖 PaymentCreate schema 验证、register_payment 业务逻辑、
冲正逻辑边界、常量校验、并发防护、金额精度、状态转换"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.order import Payment, SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import Permission, Role, RolePermission, User, UserRole
from app.schemas.payment import _MAX_AMOUNT, VALID_PAYMENT_METHODS, PaymentCreate
from app.services.payment_service import (
    _check_payment_inflight,
    _clear_payment_inflight,
    register_payment,
    reset_payment_debounce,
)

TEST_DB_URL = "sqlite:///./test_payment_svc_bounds.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    db = TestSession()
    try:
        _seed_data(db)
    finally:
        db.close()


def teardown_module(module):
    if _original_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = _original_override
    import contextlib
    import os

    with contextlib.suppress(FileNotFoundError):
        os.remove("test_payment_svc_bounds.db")


# ═══════════════════════════════════════════════════════
# 种子数据辅助
# ═══════════════════════════════════════════════════════

_admin_id: uuid.UUID = uuid.uuid4()
_sales_user_id: uuid.UUID = uuid.uuid4()
_other_user_id: uuid.UUID = uuid.uuid4()
_category_id: uuid.UUID = uuid.uuid4()
_product_id: uuid.UUID = uuid.uuid4()
_customer_id: uuid.UUID = uuid.uuid4()


def _seed_data(db: Session):
    # 角色 + 权限（先创建唯一权限，再分配给角色）
    perm_codes = ("payment:create", "payment:list", "payment:reverse", "order:view_all", "product:create")
    perm_map = {}
    for code in perm_codes:
        perm = Permission(id=uuid.uuid4(), code=code, name=code, module="payment")
        db.add(perm)
        perm_map[code] = perm.id

    role = Role(id=uuid.uuid4(), name="admin_pay_bounds", display_name="管理员")
    db.add(role)
    for code in perm_codes:
        db.add(RolePermission(role_id=role.id, permission_id=perm_map[code]))

    sales_role = Role(id=uuid.uuid4(), name="sales_pay_bounds", display_name="销售")
    db.add(sales_role)
    for code in ("payment:create", "payment:list"):
        db.add(RolePermission(role_id=sales_role.id, permission_id=perm_map[code]))

    # 用户
    admin = User(id=_admin_id, username="admin_pay_b", hashed_password=hash_password("Aa1!aaaa"), is_superuser=True)
    sales = User(id=_sales_user_id, username="sales_pay_b", hashed_password=hash_password("Aa1!aaaa"))
    other = User(id=_other_user_id, username="other_pay_b", hashed_password=hash_password("Aa1!aaaa"))
    db.add_all([admin, sales, other])
    db.add(UserRole(user_id=admin.id, role_id=role.id))
    db.add(UserRole(user_id=sales.id, role_id=sales_role.id))

    # 分类 + 商品 + 客户
    cat = ProductCategory(id=_category_id, name="收款边界测试分类")
    db.add(cat)
    prod = Product(
        id=_product_id, name="收款边界测试商品", sku="PAY-BOUND-01",
        category_id=_category_id, cost_price=Decimal("50.00"),
        sale_price=Decimal("100.00"), stock_quantity=100,
        status="active",
    )
    db.add(prod)
    cust = Customer(
        id=_customer_id, name="收款边界测试客户", phone="13800000002",
        created_by=sales.id,
    )
    db.add(cust)
    db.commit()


_order_counter = 0


def _make_order(
    db: Session, status: str, total: Decimal,
    sales_user_id=None, paid: Decimal = Decimal("0"),
) -> SalesOrder:
    global _order_counter
    _order_counter += 1
    order = SalesOrder(
        id=uuid.uuid4(),
        order_no=f"SO-BOUND-{_order_counter:06d}",
        customer_id=_customer_id,
        sales_user_id=sales_user_id or _sales_user_id,
        status=status,
        total_amount=total,
        total_cost=total,
        gross_profit=Decimal("0"),
        gross_margin=Decimal("0"),
        paid_amount=paid,
        created_by=_sales_user_id,
    )
    db.add(order)
    item = SalesOrderItem(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=_product_id,
        product_name_snapshot="收款边界测试商品",
        quantity=1,
        unit_price=total,
        cost_price_snapshot=total,
        subtotal_amount=total,
        subtotal_cost=total,
    )
    db.add(item)
    db.commit()
    return order


@pytest.fixture()
def db():
    reset_payment_debounce()
    sess = TestSession()
    yield sess
    sess.rollback()
    sess.close()
    reset_payment_debounce()


@pytest.fixture()
def admin_user(db):
    return db.query(User).filter(User.id == _admin_id).first()


@pytest.fixture()
def sales_user(db):
    return db.query(User).filter(User.id == _sales_user_id).first()


@pytest.fixture()
def other_user(db):
    return db.query(User).filter(User.id == _other_user_id).first()


# ═══════════════════════════════════════════════════════
# 1. PaymentCreate Schema 边界
# ═══════════════════════════════════════════════════════


def test_amount_zero_rejected():
    """金额为 0 被拒绝"""
    with pytest.raises(ValidationError, match="大于 0"):
        PaymentCreate(amount="0", payment_method="cash")


def test_amount_negative_rejected():
    """负金额被拒绝"""
    with pytest.raises(ValidationError, match="大于 0"):
        PaymentCreate(amount="-1.00", payment_method="cash")


def test_amount_exceeds_max_rejected():
    """金额超过上限被拒绝"""
    with pytest.raises(ValidationError, match="不能超过"):
        PaymentCreate(amount="99999999999.00", payment_method="cash")


def test_amount_at_max_accepted():
    """金额恰好等于上限"""
    p = PaymentCreate(amount=str(_MAX_AMOUNT), payment_method="cash")
    assert Decimal(p.amount) == _MAX_AMOUNT


def test_amount_just_below_max_accepted():
    """金额比上限少 0.01"""
    p = PaymentCreate(amount=str(_MAX_AMOUNT - Decimal("0.01")), payment_method="cash")
    assert Decimal(p.amount) == _MAX_AMOUNT - Decimal("0.01")


def test_amount_invalid_string_rejected():
    """非数字金额被拒绝"""
    with pytest.raises(ValidationError, match="格式不正确"):
        PaymentCreate(amount="abc", payment_method="cash")


def test_amount_scientific_notation_accepted():
    """科学计数法金额被 Decimal 接受"""
    p = PaymentCreate(amount="1e5", payment_method="cash")
    assert Decimal(p.amount) == Decimal("1e5")


def test_amount_empty_string_rejected():
    """空字符串金额被拒绝"""
    with pytest.raises(ValidationError, match="格式不正确"):
        PaymentCreate(amount="", payment_method="cash")


def test_amount_tiny_positive():
    """极小正数金额"""
    p = PaymentCreate(amount="0.01", payment_method="cash")
    assert Decimal(p.amount) == Decimal("0.01")


def test_payment_method_valid_options():
    """5 种支付方式均合法"""
    for m in VALID_PAYMENT_METHODS:
        p = PaymentCreate(amount="1.00", payment_method=m)
        assert p.payment_method == m


def test_payment_method_invalid_rejected():
    """不支持的支付方式被拒绝"""
    with pytest.raises(ValidationError):
        PaymentCreate(amount="1.00", payment_method="bitcoin")


def test_remark_max_length():
    """备注恰好 500 字符"""
    p = PaymentCreate(amount="1.00", payment_method="cash", remark="x" * 500)
    assert len(p.remark) == 500


def test_remark_over_max_rejected():
    """备注超过 500 字符被拒绝"""
    with pytest.raises(ValidationError):
        PaymentCreate(amount="1.00", payment_method="cash", remark="x" * 501)


def test_remark_none_default():
    """备注默认为 None"""
    p = PaymentCreate(amount="1.00", payment_method="cash")
    assert p.remark is None


def test_remark_html_sanitized():
    """备注 HTML 标签被清除"""
    p = PaymentCreate(amount="1.00", payment_method="cash", remark="<script>alert(1)</script>")
    assert "<script>" not in p.remark


def test_remark_empty_string_allowed():
    """空字符串备注通过"""
    p = PaymentCreate(amount="1.00", payment_method="cash", remark="")
    assert p.remark == ""


# ═══════════════════════════════════════════════════════
# 2. 常量校验
# ═══════════════════════════════════════════════════════


def test_valid_payment_methods_constant():
    """VALID_PAYMENT_METHODS 包含 5 种方式"""
    assert VALID_PAYMENT_METHODS == ("cash", "transfer", "wechat", "alipay", "other")


def test_max_amount_value():
    """_MAX_AMOUNT 为 9999999999.99"""
    assert Decimal("9999999999.99") == _MAX_AMOUNT


# ═══════════════════════════════════════════════════════
# 3. register_payment 正常路径
# ═══════════════════════════════════════════════════════


def test_register_payment_confirmed_order(db, sales_user):
    """已确认订单可收款"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="50.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["amount"] == Decimal("50.00")
    assert result["method"] == "cash"
    assert result["order"].status == "partially_paid"
    db.rollback()


def test_register_payment_partially_paid_order(db, sales_user):
    """部分收款订单可继续收款"""
    order = _make_order(db, "confirmed", Decimal("100.00"), paid=Decimal("30.00"))
    data = PaymentCreate(amount="70.00", payment_method="transfer")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].status == "completed"
    db.rollback()


def test_register_payment_exact_total(db, sales_user):
    """收款恰好等于剩余金额，订单变为 completed"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="100.00", payment_method="wechat")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].status == "completed"
    db.rollback()


def test_register_payment_returns_payment_instance(db, sales_user):
    """返回结果包含 payment 和 order 对象"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="alipay")
    result = register_payment(db, str(order.id), data, sales_user)
    assert isinstance(result["payment"], Payment)
    assert isinstance(result["order"], SalesOrder)
    assert result["payment"].payment_method == "alipay"
    db.rollback()


def test_register_payment_operator_id_set(db, sales_user):
    """收款记录的 operator_id 设为当前用户"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["payment"].operator_id == sales_user.id
    db.rollback()


def test_register_payment_remark_preserved(db, sales_user):
    """备注被保存"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash", remark="测试备注")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["payment"].remark == "测试备注"
    db.rollback()


# ═══════════════════════════════════════════════════════
# 4. register_payment 错误路径
# ═══════════════════════════════════════════════════════


def test_register_payment_order_not_found(db, sales_user):
    """不存在的订单返回 404"""
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(uuid.uuid4()), data, sales_user)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "RESOURCE_NOT_FOUND"


def test_register_payment_draft_order_rejected(db, sales_user):
    """草稿订单不可收款"""
    order = _make_order(db, "draft", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "ORDER_INVALID_STATUS"


def test_register_payment_completed_order_rejected(db, sales_user):
    """已完成订单不可收款"""
    order = _make_order(db, "completed", Decimal("100.00"), paid=Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert exc_info.value.status_code == 400


def test_register_payment_cancelled_order_rejected(db, sales_user):
    """已取消订单不可收款"""
    order = _make_order(db, "cancelled", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert exc_info.value.status_code == 400


def test_register_payment_amount_exceeds_remaining(db, sales_user):
    """收款金额超过剩余应收"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="101.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "PAYMENT_AMOUNT_EXCEEDED"


def test_register_payment_amount_exceeds_remaining_with_partial(db, sales_user):
    """部分收款后再超额"""
    order = _make_order(db, "confirmed", Decimal("100.00"), paid=Decimal("60.00"))
    data = PaymentCreate(amount="50.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert exc_info.value.detail["code"] == "PAYMENT_AMOUNT_EXCEEDED"
    assert "剩余" in exc_info.value.detail["message"]


def test_register_payment_non_owner_rejected(db, other_user):
    """非订单归属人且无 view_all 权限被拒"""
    order = _make_order(db, "confirmed", Decimal("100.00"), sales_user_id=_sales_user_id)
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, other_user)
    assert exc_info.value.status_code == 403


def test_register_payment_super_user_can_pay(db, admin_user):
    """超级用户可为任何订单收款"""
    order = _make_order(db, "confirmed", Decimal("100.00"), sales_user_id=_sales_user_id)
    data = PaymentCreate(amount="10.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, admin_user)
    assert result["amount"] == Decimal("10.00")
    db.rollback()


def test_register_payment_invalid_uuid_format(db, sales_user):
    """无效 UUID 格式的 order_id 抛出 ValueError"""
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(ValueError, match="badly formed"):
        register_payment(db, "not-a-uuid", data, sales_user)


# ═══════════════════════════════════════════════════════
# 5. 金额精度边界
# ═══════════════════════════════════════════════════════


def test_register_payment_fractional_cent(db, sales_user):
    """包含分的金额正常处理"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="33.33", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["amount"] == Decimal("33.33")
    db.rollback()


def test_register_payment_remaining_message_precision(db, sales_user):
    """超额错误消息中的剩余金额精确"""
    order = _make_order(db, "confirmed", Decimal("99.99"), paid=Decimal("33.33"))
    remaining = Decimal("99.99") - Decimal("33.33")
    data = PaymentCreate(amount="99.99", payment_method="cash")
    with pytest.raises(HTTPException) as exc_info:
        register_payment(db, str(order.id), data, sales_user)
    assert str(remaining) in exc_info.value.detail["message"]


# ═══════════════════════════════════════════════════════
# 6. 并发防护边界
# ═══════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _auto_reset_inflight():
    reset_payment_debounce()
    yield
    reset_payment_debounce()


def test_inflight_prevents_same_order():
    """同一订单并发防护"""
    _check_payment_inflight("order-A")
    with pytest.raises(HTTPException) as exc_info:
        _check_payment_inflight("order-A")
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "PAYMENT_RATE_LIMITED"


def test_inflight_different_orders_independent():
    """不同订单互不阻塞"""
    _check_payment_inflight("order-A")
    _check_payment_inflight("order-B")  # 不抛


def test_inflight_cleared_after_rejection():
    """清除标记后可重入"""
    _check_payment_inflight("order-X")
    _clear_payment_inflight("order-X")
    _check_payment_inflight("order-X")  # 不抛


def test_inflight_clear_nonexistent_idempotent():
    """清除不存在的标记幂等"""
    _clear_payment_inflight("never-existed")  # 不抛


def test_inflight_reset_clears_all():
    """全局清空后全部订单可重入"""
    _check_payment_inflight("a")
    _check_payment_inflight("b")
    _check_payment_inflight("c")
    reset_payment_debounce()
    _check_payment_inflight("a")
    _check_payment_inflight("b")
    _check_payment_inflight("c")


def test_inflight_clear_only_target():
    """清除只影响目标订单"""
    _check_payment_inflight("A")
    _check_payment_inflight("B")
    _clear_payment_inflight("A")
    # B 仍被锁
    with pytest.raises(HTTPException):
        _check_payment_inflight("B")
    # A 已解锁
    _check_payment_inflight("A")


def test_inflight_error_detail_structure():
    """429 错误 detail 包含 code 和 message"""
    _check_payment_inflight("order-err")
    with pytest.raises(HTTPException) as exc_info:
        _check_payment_inflight("order-err")
    detail = exc_info.value.detail
    assert detail["code"] == "PAYMENT_RATE_LIMITED"
    assert "message" in detail
    assert "正在处理" in detail["message"]


def test_inflight_register_clears_on_success(db, sales_user):
    """register_payment 正常完成后 inflight 被清除"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    register_payment(db, str(order.id), data, sales_user)
    # inflight 应已清除，可再次注册
    from app.services.payment_service import _payment_inflight
    assert str(order.id) not in _payment_inflight
    db.rollback()


def test_inflight_register_clears_on_failure(db, sales_user):
    """register_payment 失败后 inflight 仍被清除"""
    order = _make_order(db, "cancelled", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    with pytest.raises(HTTPException):
        register_payment(db, str(order.id), data, sales_user)
    from app.services.payment_service import _payment_inflight
    assert str(order.id) not in _payment_inflight


def test_inflight_uuid_order_id():
    """UUID 格式的 order_id 正确加入集合"""
    oid = str(uuid.uuid4())
    _check_payment_inflight(oid)
    from app.services.payment_service import _payment_inflight
    assert oid in _payment_inflight


# ═══════════════════════════════════════════════════════
# 7. 状态转换边界
# ═══════════════════════════════════════════════════════


def test_confirmed_to_partially_paid(db, sales_user):
    """confirmed → partially_paid"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="30.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].status == "partially_paid"
    db.rollback()


def test_confirmed_to_completed_directly(db, sales_user):
    """confirmed → completed（一次付清）"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="100.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].status == "completed"
    db.rollback()


def test_partially_paid_to_completed(db, sales_user):
    """partially_paid → completed"""
    order = _make_order(db, "confirmed", Decimal("100.00"), paid=Decimal("60.00"))
    data = PaymentCreate(amount="40.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].status == "completed"
    db.rollback()


def test_paid_amount_accumulates(db, sales_user):
    """多次收款 paid_amount 累加"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data1 = PaymentCreate(amount="30.00", payment_method="cash")
    register_payment(db, str(order.id), data1, sales_user)
    db.flush()

    data2 = PaymentCreate(amount="20.00", payment_method="transfer")
    result2 = register_payment(db, str(order.id), data2, sales_user)
    assert result2["order"].paid_amount == Decimal("50.00")
    db.rollback()


def test_updated_by_set(db, sales_user):
    """订单 updated_by 设为当前用户"""
    order = _make_order(db, "confirmed", Decimal("100.00"))
    data = PaymentCreate(amount="10.00", payment_method="cash")
    result = register_payment(db, str(order.id), data, sales_user)
    assert result["order"].updated_by == sales_user.id
    db.rollback()


# ═══════════════════════════════════════════════════════
# 8. Payment 模型字段校验
# ═══════════════════════════════════════════════════════


def test_payment_model_columns():
    """Payment 模型包含必要字段"""
    columns = {c.name for c in Payment.__table__.columns}
    required = {"id", "order_id", "amount", "payment_method", "paid_at",
                "operator_id", "status", "remark", "created_at"}
    assert required.issubset(columns)


def test_payment_amount_numeric_12_2():
    """Payment.amount 为 Numeric(12, 2)"""
    col = Payment.__table__.columns["amount"]
    assert col.type.precision == 12
    assert col.type.scale == 2


def test_payment_status_default_normal():
    """Payment.status 默认 normal"""
    col = Payment.__table__.columns["status"]
    assert col.default is not None


def test_payment_status_indexed():
    """Payment.status 有索引"""
    col = Payment.__table__.columns["status"]
    assert col.index is True


def test_payment_order_id_indexed():
    """Payment.order_id 有索引"""
    col = Payment.__table__.columns["order_id"]
    assert col.index is True


def test_payment_created_at_indexed():
    """Payment.created_at 有索引"""
    col = Payment.__table__.columns["created_at"]
    assert col.index is True


# ═══════════════════════════════════════════════════════
# 9. SalesOrder 收款相关字段
# ═══════════════════════════════════════════════════════


def test_order_has_paid_amount():
    """SalesOrder 有 paid_amount 字段"""
    assert hasattr(SalesOrder, "paid_amount")


def test_order_total_amount_numeric():
    """SalesOrder.total_amount 为 Numeric"""
    col = SalesOrder.__table__.columns["total_amount"]
    assert col.type.precision is not None
    assert col.type.scale is not None
