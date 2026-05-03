"""商品辅助函数单元测试 — _batch_sales_stats / _validate_category_id / _get_default_category_id / _generate_sku"""

import uuid
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.products import (
    _batch_sales_stats,
    _generate_sku,
    _get_default_category_id,
    _validate_category_id,
)
from app.db.session import Base
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
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


# ─── _validate_category_id ────────────────────────────────────


def test_validate_category_id_exists(db):
    """分类存在时返回 category_id"""
    cat_id = uuid.uuid4()
    db.add(ProductCategory(id=cat_id, name="电子产品"))
    db.commit()
    assert _validate_category_id(db, cat_id) == cat_id


def test_validate_category_id_not_found(db):
    """分类不存在时抛 400"""
    with pytest.raises(HTTPException) as exc_info:
        _validate_category_id(db, uuid.uuid4())
    assert exc_info.value.status_code == 400
    assert "商品分类不存在" in str(exc_info.value.detail)


# ─── _get_default_category_id ─────────────────────────────────


def test_get_default_category_existing(db):
    """默认分类已存在时直接返回"""
    from app.api.v1.products import DEFAULT_CATEGORY_NAME

    cat_id = uuid.uuid4()
    db.add(ProductCategory(id=cat_id, name=DEFAULT_CATEGORY_NAME))
    db.commit()
    result = _get_default_category_id(db)
    assert result == cat_id


def test_get_default_category_creates_new(db):
    """默认分类不存在时自动创建"""
    from app.api.v1.products import DEFAULT_CATEGORY_NAME

    result = _get_default_category_id(db)
    db.flush()
    cat = db.query(ProductCategory).filter(ProductCategory.name == DEFAULT_CATEGORY_NAME).first()
    assert cat is not None
    assert cat.id == result


# ─── _batch_sales_stats ───────────────────────────────────────


def _seed_sales_data(db, suffix=""):
    """创建基础数据：用户→客户→商品"""
    uid = uuid.uuid4()
    db.add(User(id=uid, username=f"stats_user{suffix}", hashed_password="x",
                display_name="u", is_active=True, is_superuser=False))
    cid = uuid.uuid4()
    db.add(Customer(id=cid, name=f"测试客户{suffix}"))
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    db.add(Product(id=p1, name="商品A", sku=f"SPU-A{suffix}",
                   sale_price=100, cost_price=60, stock_quantity=10, status="active"))
    db.add(Product(id=p2, name="商品B", sku=f"SPU-B{suffix}",
                   sale_price=200, cost_price=120, stock_quantity=5, status="active"))
    db.flush()
    return uid, cid, p1, p2


def test_batch_sales_stats_empty(db):
    """无商品时返回空 dict"""
    result = _batch_sales_stats(db, [])
    assert result == {}


def test_batch_sales_stats_no_orders(db):
    """有商品但无订单时返回空 dict"""
    _, _, p1, p2 = _seed_sales_data(db, "1")
    db.commit()
    result = _batch_sales_stats(db, [p1, p2])
    assert result == {}


def test_batch_sales_stats_confirmed_order(db):
    """已确认订单的销售统计"""
    uid, cid, p1, p2 = _seed_sales_data(db, "2")
    oid = uuid.uuid4()
    db.add(SalesOrder(id=oid, order_no="ORD-001", customer_id=cid, sales_user_id=uid, status="confirmed"))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid, product_id=p1,
                          product_name_snapshot="商品A", quantity=3, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=300, subtotal_cost=180))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid, product_id=p2,
                          product_name_snapshot="商品B", quantity=2, unit_price=200,
                          cost_price_snapshot=120, subtotal_amount=400, subtotal_cost=240))
    db.commit()
    result = _batch_sales_stats(db, [p1, p2])
    assert result[p1]["sales_quantity"] == 3
    assert result[p1]["sales_amount"] == "300.00"
    assert result[p2]["sales_quantity"] == 2
    assert result[p2]["sales_amount"] == "400.00"


def test_batch_sales_stats_excludes_draft_and_cancelled(db):
    """草稿和已取消订单不计入销售统计"""
    uid, cid, p1, _ = _seed_sales_data(db, "3")
    oid1 = uuid.uuid4()
    db.add(SalesOrder(id=oid1, order_no="ORD-D", customer_id=cid, sales_user_id=uid, status="draft"))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid1, product_id=p1,
                          product_name_snapshot="商品A", quantity=5, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=500, subtotal_cost=300))
    oid2 = uuid.uuid4()
    db.add(SalesOrder(id=oid2, order_no="ORD-X", customer_id=cid, sales_user_id=uid, status="cancelled"))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid2, product_id=p1,
                          product_name_snapshot="商品A", quantity=1, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=100, subtotal_cost=60))
    db.commit()
    result = _batch_sales_stats(db, [p1])
    assert p1 not in result


def test_batch_sales_stats_excludes_soft_deleted_order(db):
    """已软删除的订单不计入"""
    uid, cid, p1, _ = _seed_sales_data(db, "4")
    oid = uuid.uuid4()
    from datetime import datetime
    db.add(SalesOrder(id=oid, order_no="ORD-DEL", customer_id=cid, sales_user_id=uid,
                      status="confirmed", deleted_at=datetime.now(UTC)))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid, product_id=p1,
                          product_name_snapshot="商品A", quantity=2, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=200, subtotal_cost=120))
    db.commit()
    result = _batch_sales_stats(db, [p1])
    assert p1 not in result


def test_batch_sales_stats_multiple_orders_aggregate(db):
    """多张订单汇总同一商品"""
    uid, cid, p1, _ = _seed_sales_data(db, "5")
    oid1 = uuid.uuid4()
    db.add(SalesOrder(id=oid1, order_no="ORD-A", customer_id=cid, sales_user_id=uid, status="confirmed"))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid1, product_id=p1,
                          product_name_snapshot="商品A", quantity=2, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=200, subtotal_cost=120))
    oid2 = uuid.uuid4()
    db.add(SalesOrder(id=oid2, order_no="ORD-B", customer_id=cid, sales_user_id=uid, status="completed"))
    db.add(SalesOrderItem(id=uuid.uuid4(), order_id=oid2, product_id=p1,
                          product_name_snapshot="商品A", quantity=3, unit_price=100,
                          cost_price_snapshot=60, subtotal_amount=300, subtotal_cost=180))
    db.commit()
    result = _batch_sales_stats(db, [p1])
    assert result[p1]["sales_quantity"] == 5
    assert result[p1]["sales_amount"] == "500.00"


# ─── _generate_sku ────────────────────────────────────────────


@patch("app.api.v1.products.generate_sequential_code")
def test_generate_sku_delegates(mock_gen):
    """委托给 generate_sequential_code 并使用 SPU- 前缀"""
    mock_gen.return_value = "SPU-20260503-0001"
    db = MagicMock()
    result = _generate_sku(db)
    assert result == "SPU-20260503-0001"
    mock_gen.assert_called_once()


@patch("app.api.v1.products.generate_sequential_code")
def test_generate_sku_passes_db(mock_gen):
    """传递 db session 给底层函数"""
    mock_gen.return_value = "SPU-001"
    db = MagicMock()
    _generate_sku(db)
    assert mock_gen.call_args[0][0] is db
