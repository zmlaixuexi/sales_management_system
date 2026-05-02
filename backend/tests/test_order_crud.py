"""订单 CRUD + 状态流转测试 — 覆盖创建、详情、编辑、确认、取消、库存联动"""

import os
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_order_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_product2_id: str = ""
_customer_id: str = ""
_order_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


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
            username="order_tester",
            hashed_password=hash_password("testpass123"),
            display_name="订单测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        cat = ProductCategory(id=uuid.uuid4(), name="订单测试分类", sort_order=0)
        db.add(cat)
        db.flush()

        p1 = Product(
            id=uuid.uuid4(),
            name="订单测试商品A",
            sku="ORD-TEST-A",
            sale_price=100.00,
            cost_price=60.00,
            stock_quantity=50,
            status="active",
            category_id=cat.id,
        )
        p2 = Product(
            id=uuid.uuid4(),
            name="订单测试商品B",
            sku="ORD-TEST-B",
            sale_price=200.00,
            cost_price=120.00,
            stock_quantity=10,
            status="active",
            category_id=cat.id,
        )
        db.add_all([p1, p2])

        cust = Customer(
            id=uuid.uuid4(),
            name="订单测试客户",
            phone="13800000001",
            source="offline",
            owner_user_id=user.id,
        )
        db.add(cust)
        db.commit()

        global _product_id, _product2_id, _customer_id
        _product_id = str(p1.id)
        _product2_id = str(p2.id)
        _customer_id = str(cust.id)

        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_order_crud.db"):
        os.remove("./test_order_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


class TestOrderCreate:
    """创建订单"""

    def test_01_create_draft_order(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [
                {"product_id": _product_id, "quantity": 3, "unit_price": "90.00"},
            ],
            "remark": "测试订单",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "draft"
        assert data["total_amount"] == "270.00"
        assert data["order_no"].startswith("ORD-")
        global _order_id
        _order_id = data["id"]

    def test_02_create_order_empty_items_400(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [],
        }, headers=_auth())
        assert resp.status_code == 422

    def test_03_create_order_bad_customer_404(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 404

    def test_04_create_order_bad_product_404(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 404

    def test_05_create_order_zero_quantity_422(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 0}],
        }, headers=_auth())
        assert resp.status_code == 422

    def test_05b_create_order_negative_price_422(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "-10.00"}],
        }, headers=_auth())
        assert resp.status_code == 422
        assert "不能为负" in resp.json()["error"]["message"]


class TestOrderRead:
    """查询订单"""

    def test_06_get_order_detail(self):
        resp = client.get(f"/api/v1/sales-orders/{_order_id}", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_no"].startswith("ORD-")
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name_snapshot"] == "订单测试商品A"
        assert data["items"][0]["quantity"] == 3
        assert data["items"][0]["unit_price"] == "90.00"

    def test_07_get_order_404(self):
        resp = client.get(f"/api/v1/sales-orders/{uuid.uuid4()}", headers=_auth())
        assert resp.status_code == 404

    def test_08_list_orders(self):
        resp = client.get("/api/v1/sales-orders", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_09_list_orders_filter_status(self):
        resp = client.get("/api/v1/sales-orders?status=draft", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(o["status"] == "draft" for o in items)


class TestOrderUpdate:
    """编辑草稿订单"""

    def test_10_update_draft_order(self):
        resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
            "items": [
                {"product_id": _product_id, "quantity": 5, "unit_price": "85.00"},
                {"product_id": _product2_id, "quantity": 2},
            ],
            "remark": "修改后",
        }, headers=_auth())
        assert resp.status_code == 200

    def test_11_verify_update(self):
        resp = client.get(f"/api/v1/sales-orders/{_order_id}", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["remark"] == "修改后"
        # 5*85 + 2*200 = 425 + 400 = 825
        assert data["total_amount"] == "825.00"

    def test_11b_update_order_negative_price_422(self):
        """验证 update_order 也拒绝负价（之前遗漏的 bug）"""
        # 先创建一个新草稿订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 200
        draft_id = resp.json()["data"]["id"]

        resp = client.put(f"/api/v1/sales-orders/{draft_id}", json={
            "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "-5.00"}],
        }, headers=_auth())
        assert resp.status_code == 422
        assert "不能为负" in resp.json()["error"]["message"]


class TestOrderConfirm:
    """确认订单 — 库存扣减"""

    def test_12_confirm_draft_order(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "confirmed"

    def test_13_verify_inventory_deducted(self):
        resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["stock_quantity"] == 45  # 50 - 5

    def test_14_confirm_already_confirmed_400(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())
        assert resp.status_code == 400

    def test_15_update_confirmed_order_400(self):
        resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
            "remark": "不应成功",
        }, headers=_auth())
        assert resp.status_code == 400


class TestOrderCancel:
    """取消订单 — 库存回滚"""

    def test_16_cancel_confirmed_order(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_17_verify_inventory_restored(self):
        resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["stock_quantity"] == 50  # 恢复

    def test_18_cancel_already_cancelled_400(self):
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
        assert resp.status_code == 400


class TestOrderInventoryInsufficient:
    """库存不足确认失败"""

    def test_19_create_order_exceed_stock(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product2_id, "quantity": 999}],
        }, headers=_auth())
        assert resp.status_code == 200
        order_id = resp.json()["data"]["id"]

        resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
        assert resp.status_code == 400
        assert "库存不足" in resp.json()["error"]["message"]


class TestOrderFilterAndEdge:
    """订单列表筛选和边界情况"""

    def test_20_list_orders_filter_customer(self):
        """按客户筛选订单"""
        resp = client.get(f"/api/v1/sales-orders?customer_id={_customer_id}", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert all(o["customer_id"] == _customer_id for o in items)

    def test_21_create_order_disabled_product_400(self):
        """停用商品不可下单"""
        # 先停用商品
        client.post(f"/api/v1/products/{_product2_id}/disable", headers=_auth())
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product2_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 400
        assert "已停用" in resp.json()["error"]["message"]

    def test_22_order_detail_shows_payments(self):
        """订单详情显示收款记录"""
        # 创建并确认订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        oid = resp.json()["data"]["id"]
        client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

        # 登记收款
        client.post(f"/api/v1/payments/orders/{oid}/payments", json={
            "amount": "100.00", "payment_method": "cash",
        }, headers=_auth())

        # 查看详情应有收款记录
        resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
        assert resp.status_code == 200
        payments = resp.json()["data"]["payments"]
        assert len(payments) >= 1
        assert payments[0]["amount"] == "100.00"

    def test_23_update_order_customer_id(self):
        """编辑订单更换客户"""
        # 创建新客户
        resp = client.post("/api/v1/customers", json={
            "name": "换绑客户", "phone": "13800000099",
        }, headers=_auth())
        new_cust_id = resp.json()["data"]["id"]

        # 创建草稿订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        draft_id = resp.json()["data"]["id"]

        # 更换客户
        resp = client.put(f"/api/v1/sales-orders/{draft_id}", json={
            "customer_id": new_cust_id,
        }, headers=_auth())
        assert resp.status_code == 200

        # 验证客户已更换
        resp = client.get(f"/api/v1/sales-orders/{draft_id}", headers=_auth())
        assert resp.json()["data"]["customer_id"] == new_cust_id

    def test_24_update_order_empty_items(self):
        """编辑订单明细为空"""
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        draft_id = resp.json()["data"]["id"]

        resp = client.put(f"/api/v1/sales-orders/{draft_id}", json={
            "items": [],
        }, headers=_auth())
        # Pydantic schema 校验先捕获
        assert resp.status_code == 422

    def test_25_confirm_order_product_deleted(self):
        """确认订单时商品已被硬删除 → 404"""
        from app.models.product import Product as ProdModel
        # 创建草稿订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        draft_id = resp.json()["data"]["id"]

        # 硬删除商品（直接从数据库删除，模拟极端情况）
        db = TestSession()
        db.query(ProdModel).filter(ProdModel.id == uuid.UUID(_product_id)).delete()
        db.commit()
        db.close()

        resp = client.post(f"/api/v1/sales-orders/{draft_id}/confirm", headers=_auth())
        assert resp.status_code == 404

    def test_26_cancel_order_product_deleted(self):
        """取消已确认订单时商品已删除 → 跳过库存回滚仍成功"""
        from app.models.product import Product as ProdModel
        # 创建新商品
        db = TestSession()
        new_prod = ProdModel(
            id=uuid.uuid4(),
            sku="ORD-CANCEL-DEL",
            name="取消删除测试商品",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
        )
        db.add(new_prod)
        db.commit()
        pid = str(new_prod.id)
        db.close()

        # 创建并确认订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": pid, "quantity": 2}],
        }, headers=_auth())
        oid = resp.json()["data"]["id"]
        client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

        # 硬删除商品
        db = TestSession()
        db.query(ProdModel).filter(ProdModel.id == uuid.UUID(pid)).delete()
        db.commit()
        db.close()

        # 取消订单应成功（跳过已删除商品的库存回滚）
        resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
        assert resp.status_code == 200

    def test_26b_confirm_order_product_soft_deleted(self):
        """确认订单时商品已被软删除 → 404（deleted_at 过滤）"""
        from app.models.product import Product as ProdModel
        # 创建独立商品避免被其他测试干扰
        db = TestSession()
        soft_del_prod = ProdModel(
            id=uuid.uuid4(),
            sku="ORD-SOFT-CONFIRM",
            name="软删除确认测试商品",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
        )
        db.add(soft_del_prod)
        db.commit()
        pid = str(soft_del_prod.id)
        db.close()

        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": pid, "quantity": 1}],
        }, headers=_auth())
        draft_id = resp.json()["data"]["id"]

        # 软删除商品
        db = TestSession()
        prod = db.query(ProdModel).filter(ProdModel.id == uuid.UUID(pid)).first()
        prod.deleted_at = datetime.now()
        db.commit()
        db.close()

        resp = client.post(f"/api/v1/sales-orders/{draft_id}/confirm", headers=_auth())
        assert resp.status_code == 404

    def test_26c_cancel_order_product_soft_deleted(self):
        """取消已确认订单时商品已被软删除 → 跳过库存回滚仍成功"""
        from app.models.product import Product as ProdModel
        db = TestSession()
        new_prod = ProdModel(
            id=uuid.uuid4(),
            sku="ORD-SOFT-DEL",
            name="软删除测试商品",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
        )
        db.add(new_prod)
        db.commit()
        pid = str(new_prod.id)
        db.close()

        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": pid, "quantity": 2}],
        }, headers=_auth())
        oid = resp.json()["data"]["id"]
        client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

        # 软删除商品
        db = TestSession()
        prod = db.query(ProdModel).filter(ProdModel.id == uuid.UUID(pid)).first()
        prod.deleted_at = datetime.now()
        db.commit()
        db.close()

        # 取消订单应成功（软删除商品的库存不回滚）
        resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
        assert resp.status_code == 200

    def test_27_order_no_nonnumeric_suffix_fallback(self):
        """订单号生成：已有非数字后缀时回退到 1"""
        from datetime import datetime

        from app.models.order import SalesOrder as OrderModel

        today = datetime.now().strftime("%Y%m%d")
        prefix = f"ORD-{today}-"

        db = TestSession()
        # 将所有已有同前缀订单号改为非数字后缀，避免冲突
        orders = db.query(OrderModel).filter(
            OrderModel.order_no.like(f"{prefix}%")
        ).all()
        for i, o in enumerate(orders):
            o.order_no = f"{prefix}OLD{i:04d}"
        db.commit()
        db.close()

        # 将最后一个改为纯非数字后缀以触发回退
        db = TestSession()
        last = db.query(OrderModel).filter(
            OrderModel.order_no.like(f"{prefix}%")
        ).order_by(OrderModel.order_no.desc()).first()
        if last:
            last.order_no = f"{prefix}ABCD"
            db.commit()
        db.close()

        # 创建新订单应得到 {prefix}0001
        db2 = TestSession()
        new_prod = Product(
            id=uuid.uuid4(),
            sku=f"ORD-SUFFIX-{uuid.uuid4().hex[:6]}",
            name="订单号后缀测试",
            sale_price=10,
            cost_price=5,
            stock_quantity=100,
            status="active",
        )
        db2.add(new_prod)
        db2.commit()
        pid2 = str(new_prod.id)
        db2.close()

        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": pid2, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["order_no"] == f"{prefix}0001"

    def test_28_create_order_price_below_cost_400(self):
        """成交单价低于成本价阻止下单"""
        # 创建新商品（_product_id 可能已被之前的测试删除）
        db = TestSession()
        prod = Product(
            id=uuid.uuid4(), sku="ORD-BELOW-COST",
            name="低于成本测试商品", sale_price=100, cost_price=60,
            stock_quantity=10, status="active",
        )
        db.add(prod)
        db.commit()
        pid = str(prod.id)
        db.close()

        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "30"}],
        }, headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "PRICE_BELOW_COST"

    def test_29_update_order_price_below_cost_400(self):
        """编辑草稿订单时成交单价低于成本价阻止"""
        from jose import jwt

        from app.core.config import settings

        db = TestSession()
        prod = Product(
            id=uuid.uuid4(), sku="ORD-UPD-BELOW-COST",
            name="编辑低于成本测试", sale_price=100, cost_price=60,
            stock_quantity=10, status="active",
        )
        db.add(prod)
        db.flush()

        pid = str(prod.id)

        # 直接在数据库创建草稿订单，避免 order_no 与已有订单冲突
        payload = jwt.decode(_tokens["access"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = uuid.UUID(payload["sub"])
        draft = SalesOrder(
            id=uuid.uuid4(),
            order_no=f"ORD-UPD-TEST-{uuid.uuid4().hex[:8]}",
            customer_id=uuid.UUID(_customer_id),
            sales_user_id=user_id,
            status="draft",
            total_amount=0,
            total_cost=0,
            gross_profit=0,
            gross_margin=0,
            paid_amount=0,
        )
        db.add(draft)
        db.commit()
        draft_id = str(draft.id)
        db.close()

        # 编辑订单时使用低于成本价的单价
        resp = client.put(f"/api/v1/sales-orders/{draft_id}", json={
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "30"}],
        }, headers=_auth())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "PRICE_BELOW_COST"

    def test_30_order_preserves_snapshot_after_product_update(self):
        """修改商品价格/名称后，历史订单保留快照值"""
        from jose import jwt as jose_jwt

        from app.core.config import settings

        db = TestSession()
        prod = Product(
            id=uuid.uuid4(), sku="ORD-SNAPSHOT-001",
            name="快照原名称", sale_price=100, cost_price=60,
            stock_quantity=20, status="active",
        )
        db.add(prod)
        db.flush()
        pid = str(prod.id)

        # 直接在 DB 创建订单和明细，避免 order_no 冲突
        payload = jose_jwt.decode(_tokens["access"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = uuid.UUID(payload["sub"])
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no=f"ORD-SNAP-{uuid.uuid4().hex[:8]}",
            customer_id=uuid.UUID(_customer_id),
            sales_user_id=user_id,
            status="draft",
            total_amount=190, total_cost=120, gross_profit=70,
            gross_margin=0.3684, paid_amount=0,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_sku_snapshot="ORD-SNAPSHOT-001",
            product_name_snapshot="快照原名称",
            quantity=2, unit_price=95, cost_price_snapshot=60,
            discount_amount=5, discount_rate=0.05,
            subtotal_amount=190, subtotal_cost=120,
        ))
        db.commit()
        order_id = str(order.id)
        db.close()

        # 验证快照值
        resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
        data = resp.json()["data"]
        assert data["items"][0]["product_name_snapshot"] == "快照原名称"
        assert data["items"][0]["unit_price"] == "95.00"
        assert data["items"][0]["cost_price_snapshot"] == "60.00"
        assert data["items"][0]["product_sku_snapshot"] == "ORD-SNAPSHOT-001"

        # 修改商品价格和名称
        client.put(f"/api/v1/products/{pid}", json={
            "name": "快照新名称",
            "sale_price": "120.00",
            "cost_price": "70.00",
        }, headers=_auth())

        # 再次获取订单，快照值应保持不变
        resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
        data = resp.json()["data"]
        assert data["items"][0]["product_name_snapshot"] == "快照原名称"
        assert data["items"][0]["unit_price"] == "95.00"
        assert data["items"][0]["cost_price_snapshot"] == "60.00"
        assert data["total_amount"] == "190.00"


class TestOrderAuthBoundary:
    """订单认证边界测试"""

    def test_28_list_orders_requires_auth(self):
        """未认证订单列表返回 401"""
        resp = client.get("/api/v1/sales-orders")
        assert resp.status_code == 401

    def test_29_get_order_requires_auth(self):
        """未认证获取订单详情返回 401"""
        resp = client.get(f"/api/v1/sales-orders/{_order_id}")
        assert resp.status_code == 401

    def test_30_create_order_requires_auth(self):
        """未认证创建订单返回 401"""
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        })
        assert resp.status_code == 401

    def test_31_update_order_requires_auth(self):
        """未认证编辑订单返回 401"""
        resp = client.put(f"/api/v1/sales-orders/{_order_id}", json={
            "remark": "未认证修改",
        })
        assert resp.status_code == 401

    def test_32_confirm_order_requires_auth(self):
        """未认证确认订单返回 401"""
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm")
        assert resp.status_code == 401

    def test_33_cancel_order_requires_auth(self):
        """未认证取消订单返回 401"""
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel")
        assert resp.status_code == 401

    def test_34_get_order_invalid_uuid(self):
        """无效 UUID 获取订单详情返回 422"""
        resp = client.get("/api/v1/sales-orders/not-a-uuid", headers=_auth())
        assert resp.status_code == 422

    def test_35_update_order_invalid_uuid(self):
        """无效 UUID 编辑订单返回 422"""
        resp = client.put("/api/v1/sales-orders/not-a-uuid", json={
            "remark": "test",
        }, headers=_auth())
        assert resp.status_code == 422

    def test_36_confirm_order_invalid_uuid(self):
        """无效 UUID 确认订单返回 422"""
        resp = client.post("/api/v1/sales-orders/not-a-uuid/confirm", headers=_auth())
        assert resp.status_code == 422


def test_37_unit_price_equals_cost_price_zero_margin():
    """成交单价等于成本价应成功，毛利率为 0"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="零利润商品", sku="ORD-ZERO-01",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="零利润客户", phone="13800000099",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-ZERO-MARGIN",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=120, total_cost=120,
            gross_profit=0, gross_margin=0, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_sku_snapshot=prod.sku, product_name_snapshot=prod.name,
            quantity=2, unit_price=60, discount_amount=40, discount_rate=0.4,
            cost_price_snapshot=60, subtotal_amount=120, subtotal_cost=120,
        ))
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    # 验证通过 API 获取详情确认金额
    resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gross_profit"] == "0.00"
    assert data["gross_margin"] == "0.0000"


def test_38_order_logs_endpoint():
    """订单操作日志端点返回审计记录"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="日志测试商品", sku="ORD-LOG-01",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="日志测试客户", phone="13800000098",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        # 直接创建订单，避免序列冲突
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-LOG-TEST",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_sku_snapshot=prod.sku, product_name_snapshot=prod.name,
            quantity=1, unit_price=100, discount_amount=0, discount_rate=0,
            cost_price_snapshot=60, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    # 确认订单（通过 API 以产生审计日志）
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 查询日志
    resp = client.get(f"/api/v1/sales-orders/{oid}/logs", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert "action" in items[0]
    assert "created_at" in items[0]


def test_39_draft_cancel_no_inventory_movement():
    """取消草稿订单不应产生库存变动记录"""
    from app.models.order import InventoryMovement
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="草稿取消测试商品", sku="ORD-DRAFT-CANCEL",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="草稿取消测试客户", phone="13800000097",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        # 直接创建草稿订单，避免序列冲突
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-DRAFT-CANCEL",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_sku_snapshot=prod.sku, product_name_snapshot=prod.name,
            quantity=1, unit_price=100, discount_amount=0, discount_rate=0,
            cost_price_snapshot=60, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        oid = str(order.id)
        pid = str(prod.id)

        before_count = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == prod.id,
        ).count()
    finally:
        db.close()

    # 取消草稿（通过 API）
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    db = TestSession()
    try:
        after_count = db.query(InventoryMovement).filter(
            InventoryMovement.product_id == uuid.UUID(pid),
        ).count()
        assert after_count == before_count, "取消草稿订单不应产生库存变动"
    finally:
        db.close()
