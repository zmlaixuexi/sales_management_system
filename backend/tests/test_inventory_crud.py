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
            hashed_password=hash_password("TestPass123!"),
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


app.dependency_overrides[get_db] = override_get_db  # 在 setup_module 中正式设置


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
            hashed_password=hash_password("TestPass123!"),
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
            hashed_password=hash_password("TestPass123!"),
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


def test_16_movements_requires_auth():
    """未认证访问流水列表返回 401"""
    resp = client.get("/api/v1/inventory/movements")
    assert resp.status_code == 401


def test_17_adjust_requires_auth():
    """未认证调整库存返回 401"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id,
        "quantity_change": 1,
    })
    assert resp.status_code == 401


def test_18_adjust_invalid_product_uuid():
    """无效商品 UUID 由 Pydantic 拦截返回 422"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": "not-a-uuid",
        "quantity_change": 1,
    }, headers=_auth())
    assert resp.status_code == 422


def test_19_adjust_response_fields():
    """调整成功返回完整字段"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id,
        "quantity_change": 3,
        "remark": "边界测试",
    }, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["product_id"] == _product_id
    assert data["quantity_change"] == 3
    assert "quantity_before" in data
    assert "quantity_after" in data


def test_20_movements_filter_invalid_product():
    """按不存在 product_id 筛选返回空列表"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/inventory/movements?product_id={fake_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


def test_21_adjust_remark_strips_html():
    """库存备注应自动移除 HTML 标签，防止存储型 XSS"""
    from app.schemas.inventory import InventoryAdjust

    item = InventoryAdjust(
        product_id=str(uuid.uuid4()),
        quantity_change=1,
        remark="<script>alert('xss')</script>正常备注",
    )
    assert "<script>" not in item.remark
    assert "正常备注" in item.remark


def test_22_movements_filter_product_and_type():
    """同时按 product_id 和 movement_type 筛选"""
    # 先增加一笔调整，确保有 manual_adjust 类型的流水
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 2,
    }, headers=_auth())
    assert resp.status_code == 200

    # 同时过滤 product + type
    resp = client.get(
        f"/api/v1/inventory/movements?product_id={_product_id}&movement_type=manual_adjust",
        headers=_auth(),
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    for m in items:
        assert m["product_id"] == _product_id
        assert m["movement_type"] == "manual_adjust"


def test_23_adjust_fractional_quantity_rejected():
    """库存调整数量为小数应被拒绝（数量必须为整数）"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 1.5,
    }, headers=_auth())
    assert resp.status_code == 422


def test_24_adjust_remark_max_length_boundary():
    """备注恰好 500 字符通过，501 字符被拒绝"""
    ok_remark = "x" * 500
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 1,
        "remark": ok_remark,
    }, headers=_auth())
    assert resp.status_code == 200

    long_remark = "x" * 501
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 1,
        "remark": long_remark,
    }, headers=_auth())
    assert resp.status_code == 422


def test_25_movements_page_size_100():
    """库存流水 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/inventory/movements", params={"page_size": 100}, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_26_movements_page_size_over_max_422():
    """库存流水 page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/inventory/movements", params={"page_size": 101}, headers=_auth())
    assert resp.status_code == 422


def test_27_adjust_audit_log_fields():
    """库存调整审计日志 before_data/after_data 字段完整"""
    # 先查询当前库存
    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.status_code == 200
    stock_before = resp.json()["data"]["stock_quantity"]

    # 执行调整
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id,
        "quantity_change": 3,
        "remark": "审计字段验证",
    }, headers=_auth())
    assert resp.status_code == 200

    # 查询审计日志（按时间降序，第一条应为本轮调整）
    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    # 用唯一 remark 匹配本轮调整
    log = next(
        i for i in items
        if i["resource_id"] == _product_id
        and i["before_data"].get("stock_quantity") == stock_before
    )

    # before_data 应包含调整前库存
    assert log["before_data"]["stock_quantity"] == stock_before
    # after_data 应包含调整后库存和变化量
    assert log["after_data"]["stock_quantity"] == stock_before + 3
    assert log["after_data"]["change"] == 3
    # resource_type
    assert log["resource_type"] == "product"
