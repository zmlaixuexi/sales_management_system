"""订单明细校验函数单元测试 — _validate_and_prepare_items"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.orders import _validate_and_prepare_items
from app.db.session import Base
from app.models.product import Product
from app.schemas.order import OrderItemInput


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


def _seed_product(db, status="active", suffix=""):
    """创建商品并返回 id"""
    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name=f"商品{suffix}", sku=f"SKU-{suffix}",
        sale_price=100, cost_price=60, stock_quantity=50, status=status,
    ))
    db.flush()
    return pid


def _item(pid, qty=1, unit_price=None):
    """创建 OrderItemInput"""
    return OrderItemInput(product_id=str(pid), quantity=qty, unit_price=unit_price)


def test_validate_items_single_active_product(db):
    """单个活跃商品正常返回"""
    pid = _seed_product(db, suffix="V1")
    result = _validate_and_prepare_items(db, [_item(pid, 3)])
    assert len(result) == 1
    assert result[0]["product_id"] == pid
    assert result[0]["quantity"] == 3
    assert result[0]["unit_price"] == Decimal("100")


def test_validate_items_multiple_products(db):
    """多个商品同时校验"""
    p1 = _seed_product(db, suffix="V2")
    p2 = _seed_product(db, suffix="V3")
    result = _validate_and_prepare_items(db, [_item(p1, 2), _item(p2, 5)])
    assert len(result) == 2


def test_validate_items_product_not_found(db):
    """商品不存在抛 404"""
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_items(db, [_item(uuid.uuid4())])
    assert exc_info.value.status_code == 404
    assert "商品不存在" in str(exc_info.value.detail)


def test_validate_items_soft_deleted_product(db):
    """软删除商品视为不存在"""
    from datetime import UTC, datetime

    pid = uuid.uuid4()
    db.add(Product(
        id=pid, name="已删除", sku="SKU-DEL",
        sale_price=100, cost_price=60, stock_quantity=50, status="active",
        deleted_at=datetime.now(UTC),
    ))
    db.flush()
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_items(db, [_item(pid)])
    assert exc_info.value.status_code == 404


def test_validate_items_inactive_product(db):
    """已停用商品抛 400"""
    pid = _seed_product(db, status="inactive", suffix="V4")
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_items(db, [_item(pid)])
    assert exc_info.value.status_code == 400
    assert "已停用" in str(exc_info.value.detail)


def test_validate_items_disabled_product(db):
    """已停用（disabled）商品抛 400"""
    pid = _seed_product(db, status="disabled", suffix="V5")
    with pytest.raises(HTTPException) as exc_info:
        _validate_and_prepare_items(db, [_item(pid)])
    assert exc_info.value.status_code == 400


def test_validate_items_custom_unit_price(db):
    """指定成交单价"""
    pid = _seed_product(db, suffix="V6")
    result = _validate_and_prepare_items(db, [_item(pid, 2, "80")])
    assert result[0]["unit_price"] == Decimal("80")
    assert result[0]["discount_amount"] == Decimal("20")


def test_validate_items_empty_list(db):
    """空明细列表返回空"""
    result = _validate_and_prepare_items(db, [])
    assert result == []


def test_validate_items_invalid_uuid(db):
    """无效 product_id 格式由 Pydantic 拦截"""
    with pytest.raises(ValidationError, match="商品 ID"):
        OrderItemInput(product_id="not-a-uuid", quantity=1)


def test_validate_items_mixed_valid_and_invalid(db):
    """一个有效一个无效商品时在无效处中断"""
    p1 = _seed_product(db, suffix="V7")
    with pytest.raises(HTTPException):
        _validate_and_prepare_items(db, [_item(p1), _item(uuid.uuid4())])
