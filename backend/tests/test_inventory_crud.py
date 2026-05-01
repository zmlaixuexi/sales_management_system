"""库存调整 + 流水查询测试 — 覆盖手工调整、流水列表、筛选、边界"""

import os
import uuid
from datetime import UTC

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_inventory_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_product2_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def _auth():
    return {"Authorization": f"Bearer {_tokens['access']}"}


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="inv_tester",
            hashed_password=hash_password("testpass123"),
            display_name="库存测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        cat = ProductCategory(id=uuid.uuid4(), name="库存测试分类", sort_order=0)
        db.add(cat)
        db.flush()

        p1 = Product(
            id=uuid.uuid4(),
            name="库存测试商品A",
            sku="INV-TEST-A",
            sale_price=100.00,
            cost_price=60.00,
            stock_quantity=20,
            status="active",
            category_id=cat.id,
        )
        p2 = Product(
            id=uuid.uuid4(),
            name="库存测试商品B",
            sku="INV-TEST-B",
            sale_price=50.00,
            cost_price=30.00,
            stock_quantity=5,
            status="active",
            category_id=cat.id,
        )
        db.add_all([p1, p2])
        db.commit()

        global _product_id, _product2_id
        _product_id = str(p1.id)
        _product2_id = str(p2.id)

        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_inventory_crud.db"):
        os.remove("./test_inventory_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestInventoryAdjust:
    """手工库存调整"""

    def test_01_adjust_increase(self):
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product_id,
            "quantity_change": 10,
            "remark": "入库测试",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["quantity_before"] == 20
        assert data["quantity_change"] == 10
        assert data["quantity_after"] == 30

    def test_02_adjust_decrease(self):
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product_id,
            "quantity_change": -5,
            "remark": "出库测试",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["quantity_before"] == 30
        assert data["quantity_after"] == 25

    def test_03_adjust_zero_400(self):
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product_id,
            "quantity_change": 0,
        }, headers=_auth())
        assert resp.status_code == 400
        assert "不能为 0" in resp.json()["error"]["message"]

    def test_04_adjust_over_decrease_400(self):
        """调整后库存不能为负"""
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product2_id,
            "quantity_change": -999,
        }, headers=_auth())
        assert resp.status_code == 400
        assert "不能为负" in resp.json()["error"]["message"]

    def test_05_adjust_bad_product_404(self):
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": str(uuid.uuid4()),
            "quantity_change": 1,
        }, headers=_auth())
        assert resp.status_code == 404


class TestInventoryMovements:
    """库存流水查询"""

    def test_06_list_movements(self):
        resp = client.get("/api/v1/inventory/movements", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 2  # at least the 2 adjustments above

    def test_07_list_movements_by_product(self):
        resp = client.get(f"/api/v1/inventory/movements?product_id={_product_id}", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(m["product_id"] == _product_id for m in items)

    def test_08_list_movements_by_type(self):
        resp = client.get("/api/v1/inventory/movements?movement_type=manual_adjust", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(m["movement_type"] == "manual_adjust" for m in items)

    def test_09_movement_fields(self):
        """验证流水记录字段完整性"""
        resp = client.get(f"/api/v1/inventory/movements?product_id={_product_id}", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        m = items[0]
        assert "quantity_before" in m
        assert "quantity_change" in m
        assert "quantity_after" in m
        assert m["quantity_after"] == m["quantity_before"] + m["quantity_change"]

    def test_10_adjust_exactly_to_zero(self):
        """调整到恰好 0 应成功"""
        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product2_id,
            "quantity_change": -5,
        }, headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["quantity_after"] == 0


def test_11_adjust_no_permission_403():
    """无 inventory:adjust 权限用户返回 403"""
    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_inv_adjust",
            hashed_password=hash_password("testpass123"),
            display_name="无库存调整权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_12_list_no_permission_403():
    """无 inventory:list 权限用户返回 403"""
    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_inv_list",
            hashed_password=hash_password("testpass123"),
            display_name="无库存列表权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    resp = client.get("/api/v1/inventory/movements", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 403


def test_13_adjust_deleted_product_404():
    """已删除商品不可调整库存"""
    db = TestSession()
    try:
        from datetime import datetime
        db.query(User).filter(User.username == "inv_tester").first()
        cat = db.query(ProductCategory).first()
        deleted_p = Product(
            id=uuid.uuid4(), name="已删除商品", sku="INV-DEL-001",
            sale_price=10, cost_price=5, stock_quantity=5,
            status="active", category_id=cat.id,
            deleted_at=datetime.now(UTC),
        )
        db.add(deleted_p)
        db.commit()
        pid = str(deleted_p.id)
    finally:
        db.close()

    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": pid, "quantity_change": 1,
    }, headers=_auth())
    assert resp.status_code == 404


def test_14_movements_pagination():
    """库存流水分页"""
    resp = client.get("/api/v1/inventory/movements?page=1&page_size=1", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] >= 2


def test_15_movements_filter_order_confirm_type():
    """筛选 order_confirm 类型流水（无匹配）"""
    resp = client.get("/api/v1/inventory/movements?movement_type=order_confirm", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 0
