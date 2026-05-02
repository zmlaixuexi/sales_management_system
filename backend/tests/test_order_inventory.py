"""订单库存辅助函数单元测试 — _deduct_inventory / _restore_inventory"""

import uuid
from datetime import UTC, datetime

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


def _make_item(db, product_id, qty=5, price=100, cost=60):
    """创建订单明细 ORM 对象（含依赖的订单和客户）"""
    uid = uuid.uuid4()
    db.add(User(id=uid, username=f"iu_{uuid.uuid4().hex[:6]}",
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


def _seed_product(db, stock=50, suffix=""):
    """创建商品并返回 id"""
    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name=f"商品{suffix}", sku=f"SKU-{suffix}",
        sale_price=100, cost_price=60, stock_quantity=stock, status="active",
    ))
    db.flush()
    return pid


# ─── _deduct_inventory ────────────────────────────────────────


def test_deduct_inventory_success(db):
    """正常扣减库存"""
    pid = _seed_product(db, 50, "D1")
    item = _make_item(db, pid, qty=10)
    operator_id = uuid.uuid4()

    _deduct_inventory(db, uuid.uuid4(), [item], operator_id)
    db.flush()

    product = db.get(Product, pid)
    assert product.stock_quantity == 40

    movements = db.query(InventoryMovement).all()
    assert len(movements) == 1
    m = movements[0]
    assert m.movement_type == "order_confirm"
    assert m.quantity_before == 50
    assert m.quantity_change == -10
    assert m.quantity_after == 40


def test_deduct_inventory_insufficient_stock(db):
    """库存不足时抛 400"""
    pid = _seed_product(db, 3, "D2")
    item = _make_item(db, pid, qty=10)
    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    assert exc_info.value.status_code == 400
    assert "库存不足" in str(exc_info.value.detail)


def test_deduct_inventory_product_not_found(db):
    """商品不存在（已删除）时抛 404"""
    item = _make_item(db, uuid.uuid4(), qty=1)
    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_deduct_inventory_soft_deleted_product(db):
    """软删除的商品视为不存在"""
    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name="已删除", sku="SKU-DEL",
        sale_price=100, cost_price=60, stock_quantity=50, status="active",
        deleted_at=datetime.now(UTC),
    ))
    db.flush()
    item = _make_item(db, pid, qty=1)
    with pytest.raises(HTTPException) as exc_info:
        _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_deduct_inventory_multiple_items(db):
    """多个明细同时扣减"""
    p1 = _seed_product(db, 20, "D3")
    p2 = _seed_product(db, 30, "D4")
    i1 = _make_item(db, p1, qty=5)
    i2 = _make_item(db, p2, qty=10)

    _deduct_inventory(db, uuid.uuid4(), [i1, i2], uuid.uuid4())
    db.flush()

    assert db.get(Product, p1).stock_quantity == 15
    assert db.get(Product, p2).stock_quantity == 20
    assert db.query(InventoryMovement).count() == 2


def test_deduct_inventory_exact_stock(db):
    """库存刚好等于需求数量时通过"""
    pid = _seed_product(db, 10, "D5")
    item = _make_item(db, pid, qty=10)
    _deduct_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    db.flush()
    assert db.get(Product, pid).stock_quantity == 0


# ─── _restore_inventory ───────────────────────────────────────


def test_restore_inventory_success(db):
    """正常回滚库存"""
    pid = _seed_product(db, 40, "R1")
    item = _make_item(db, pid, qty=10)
    order_id = uuid.uuid4()

    _restore_inventory(db, order_id, [item], uuid.uuid4())
    db.flush()

    product = db.get(Product, pid)
    assert product.stock_quantity == 50

    movements = db.query(InventoryMovement).all()
    assert len(movements) == 1
    m = movements[0]
    assert m.movement_type == "order_cancel"
    assert m.quantity_change == 10
    assert m.quantity_after == 50
    assert m.related_id == order_id


def test_restore_inventory_missing_product_ok(db):
    """商品不存在时静默跳过（不报错）"""
    item = _make_item(db, uuid.uuid4(), qty=1)
    _restore_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    db.flush()
    assert db.query(InventoryMovement).count() == 0


def test_restore_inventory_soft_deleted_product_skipped(db):
    """软删除的商品跳过回滚"""
    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name="已删除", sku="SKU-DEL2",
        sale_price=100, cost_price=60, stock_quantity=50, status="active",
        deleted_at=datetime.now(UTC),
    ))
    db.flush()
    item = _make_item(db, pid, qty=5)
    _restore_inventory(db, uuid.uuid4(), [item], uuid.uuid4())
    db.flush()
    assert db.query(InventoryMovement).count() == 0


def test_restore_inventory_multiple_items(db):
    """多个明细同时回滚"""
    p1 = _seed_product(db, 15, "R2")
    p2 = _seed_product(db, 20, "R3")
    i1 = _make_item(db, p1, qty=5)
    i2 = _make_item(db, p2, qty=10)

    _restore_inventory(db, uuid.uuid4(), [i1, i2], uuid.uuid4())
    db.flush()

    assert db.get(Product, p1).stock_quantity == 20
    assert db.get(Product, p2).stock_quantity == 30
    assert db.query(InventoryMovement).count() == 2
