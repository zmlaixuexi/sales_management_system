"""并发安全测试 — 验证库存扣减/回滚的锁策略和竞态防护"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.orders import _deduct_inventory, _restore_inventory
from app.db.session import Base
from app.models.customer import Customer
from app.models.order import InventoryMovement, SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User


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


def _seed_product(db, stock=50, suffix=""):
    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name=f"商品{suffix}", sku=f"SKU-{suffix}",
        sale_price=100, cost_price=60, stock_quantity=stock, status="active",
    ))
    db.flush()
    return pid


def _make_item(db, product_id, qty=5, price=100, cost=60):
    uid = uuid.uuid4()
    db.add(User(id=uid, username=f"cu_{uuid.uuid4().hex[:6]}",
                hashed_password="x", display_name="u", is_active=True, is_superuser=False))
    cid = uuid.uuid4()
    db.add(Customer(id=cid, name="客户"))
    oid = uuid.uuid4()
    db.add(SalesOrder(id=oid, order_no=f"ORD-{uuid.uuid4().hex[:6]}",
                      customer_id=cid, sales_user_id=uid, status="confirmed"))
    db.flush()
    item = SalesOrderItem(
        id=uuid.uuid4(),
        order_id=oid,
        product_id=product_id,
        product_name_snapshot="商品",
        quantity=qty,
        unit_price=price,
        cost_price_snapshot=cost,
        subtotal_amount=price * qty,
        subtotal_cost=cost * qty,
    )
    db.add(item)
    db.flush()
    return item


# ─── with_for_update 调用验证 ─────────────────────────────────


def test_deduct_calls_with_for_update(db):
    """_deduct_inventory 必须对商品行调用 with_for_update（悲观锁）"""
    pid = _seed_product(db, 50, "L1")
    item = _make_item(db, pid, qty=5)

    with patch("app.api.v1.orders.active_query") as mock_aq:
        product = db.get(Product, pid)
        mock_query = mock_aq.return_value.filter.return_value
        mock_query.with_for_update.return_value.all.return_value = [product]

        _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())

        mock_query.with_for_update.assert_called_once()


def test_restore_calls_with_for_update(db):
    """_restore_inventory 必须对商品行调用 with_for_update（悲观锁）"""
    pid = _seed_product(db, 50, "L2")
    item = _make_item(db, pid, qty=5)

    with patch("app.api.v1.orders.active_query") as mock_aq:
        product = db.get(Product, pid)
        mock_query = mock_aq.return_value.filter.return_value
        mock_query.with_for_update.return_value.all.return_value = [product]

        _restore_inventory(db, uuid.uuid4(), [item], uuid.uuid4())

        mock_query.with_for_update.assert_called_once()


# ─── 竞态模拟：库存被并发修改后检查防护 ─────────────────────────


def test_deduct_detects_stale_stock_via_for_update(db):
    """模拟竞态：FOR UPDATE 读到最新库存（已被并发扣减），库存不足应拒绝"""
    pid = _seed_product(db, 10, "R1")
    item = _make_item(db, pid, qty=8)

    # 第一次调用正常通过，第二次 FOR UPDATE 读到已被扣减后的库存
    original_all = db.query(Product).all

    call_count = 0

    def fake_all():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # 模拟并发已扣减：返回 stock_quantity=5（原始 10，被别的请求扣了 5）
            product = db.get(Product, pid)
            product.stock_quantity = 5
            return [product]
        return original_all()

    with patch("app.api.v1.orders.active_query") as mock_aq:
        mock_query = mock_aq.return_value.filter.return_value
        mock_query.with_for_update.return_value.all = fake_all

        with pytest.raises(HTTPException) as exc_info:
            _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
        assert exc_info.value.status_code == 400
        assert "库存不足" in str(exc_info.value.detail)


def test_deduct_after_concurrent_decrement_leaves_consistent(db):
    """并发扣减后库存应保持一致（不超过零）"""
    pid = _seed_product(db, 10, "R2")

    # 第一笔扣减 8 成功
    item1 = _make_item(db, pid, qty=8)
    _deduct_inventory(db, uuid.uuid4(), [item1], uuid.uuid4())
    db.flush()
    assert db.get(Product, pid).stock_quantity == 2

    # 第二笔扣减 5 应失败（只剩 2）
    item2 = _make_item(db, pid, qty=5)
    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item2], uuid.uuid4())
    assert exc_info.value.status_code == 400

    # 库存应仍为 2，无异常扣减
    assert db.get(Product, pid).stock_quantity == 2
    assert db.query(InventoryMovement).count() == 1


def test_restore_idempotent_after_partial_deduct(db):
    """多次回滚库存应正确累加（幂等安全场景）"""
    pid = _seed_product(db, 20, "R3")

    # 扣减 5
    item = _make_item(db, pid, qty=5)
    _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    db.flush()
    assert db.get(Product, pid).stock_quantity == 15

    # 回滚两次（模拟异常场景）
    item2 = _make_item(db, pid, qty=5)
    _restore_inventory(db, uuid.uuid4(), [item2], uuid.uuid4())
    db.flush()
    assert db.get(Product, pid).stock_quantity == 20

    _restore_inventory(db, uuid.uuid4(), [_make_item(db, pid, qty=5)], uuid.uuid4())
    db.flush()
    assert db.get(Product, pid).stock_quantity == 25
    assert db.query(InventoryMovement).count() == 3


def test_deduct_zero_stock_rejected(db):
    """库存为 0 时扣减应直接拒绝"""
    pid = _seed_product(db, 0, "R4")
    item = _make_item(db, pid, qty=1)
    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    assert exc_info.value.status_code == 400
    assert "库存不足" in str(exc_info.value.detail)


def test_deduct_multiple_products_partial_failure(db):
    """多商品扣减时，部分商品库存不足应整体拒绝"""
    p1 = _seed_product(db, 10, "R5")
    p2 = _seed_product(db, 2, "R6")

    item1 = _make_item(db, p1, qty=5)
    item2 = _make_item(db, p2, qty=10)

    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item1, item2], uuid.uuid4())
    assert exc_info.value.status_code == 400

    # 两个商品库存均不变
    assert db.get(Product, p1).stock_quantity == 10
    assert db.get(Product, p2).stock_quantity == 2
    assert db.query(InventoryMovement).count() == 0
