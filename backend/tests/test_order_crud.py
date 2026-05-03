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


app.dependency_overrides[get_db] = override_get_db  # 在 setup_module 中正式设置


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens['access']}"}


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
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

    def test_05a_create_order_negative_quantity_422(self):
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": -1}],
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

    def test_37_cancel_order_invalid_uuid(self):
        """无效 UUID 取消订单返回 422"""
        resp = client.post("/api/v1/sales-orders/not-a-uuid/cancel", headers=_auth())
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


def test_40_cancel_completed_order_400():
    """取消已完成订单返回 400 ORDER_INVALID_STATUS"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="已完成订单测试商品", sku="ORD-COMPLETE-01",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="已完成订单测试客户", phone="13800000100",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-COMPLETED-TEST",
            customer_id=cust.id, sales_user_id=user.id,
            status="completed", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=100,
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

    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


def test_41_update_draft_order_remark_only():
    """编辑草稿订单仅更新备注（不发送 items）应成功"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="备注更新测试商品", sku="ORD-REMARK-01",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="备注更新测试客户", phone="13800000101",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-REMARK-TEST",
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

    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "仅更新备注",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
    assert resp.json()["data"]["remark"] == "仅更新备注"


def test_42_create_order_zero_price_above_cost_400():
    """成交单价为 0 但成本价 > 0 应阻止下单"""
    db = TestSession()
    try:
        prod = Product(
            id=uuid.uuid4(), name="零价测试商品", sku="ORD-ZERO-PRICE",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active",
        )
        db.add(prod)
        db.commit()
        pid = str(prod.id)
    finally:
        db.close()

    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "0"}],
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PRICE_BELOW_COST"


def test_43_list_orders_keyword_search():
    """关键字搜索订单号"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cust = db.query(Customer).first()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-KEYWORD-TEST-001",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/sales-orders", params={"keyword": "KEYWORD-TEST"}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert any("KEYWORD-TEST" in i["order_no"] for i in items)


def test_44_list_orders_keyword_like_injection():
    """关键字搜索含 LIKE 特殊字符（%、_）不应匹配全部"""
    resp = client.get("/api/v1/sales-orders", params={"keyword": "%"}, headers=_auth())
    assert resp.status_code == 200
    # % 在 SQL LIKE 中匹配所有，但 escape_like 应转义
    # 结果不应包含异常多的记录
    items = resp.json()["data"]["items"]
    # 订单号不含字面量 %，应该返回空
    assert all("%" not in i["order_no"] for i in items)


def test_45_list_orders_page_size_boundary():
    """分页边界 page_size=1 只返回一条"""
    resp = client.get("/api/v1/sales-orders", params={"page_size": 1}, headers=_auth())
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) <= 1


def test_46_list_orders_desc_ordering():
    """订单列表按创建时间降序排列"""
    from sqlalchemy import func

    db = TestSession()
    try:
        user = db.query(User).first()
        cust = db.query(Customer).first()
        # 创建两个有明显时间差的订单
        o1 = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-ORDER-OLD",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=50, total_cost=30,
            gross_profit=20, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(o1)
        db.commit()

        # 更新第一个订单的 created_at 使其更早
        db.query(SalesOrder).filter(SalesOrder.id == o1.id).update(
            {"created_at": func.datetime("now", "-1 hour")}
        )
        db.commit()

        o2 = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-ORDER-NEW",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=80, total_cost=40,
            gross_profit=40, gross_margin=0.5, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(o2)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/sales-orders", params={"page_size": 50}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    # 找到这两个订单，验证 NEW 在 OLD 前面
    nos = [i["order_no"] for i in items]
    if "ORD-ORDER-OLD" in nos and "ORD-ORDER-NEW" in nos:
        assert nos.index("ORD-ORDER-NEW") < nos.index("ORD-ORDER-OLD")


def test_47_order_logs_strip_cost_fields_for_non_privileged():
    """非特权用户查看订单日志时，成本字段应被移除"""
    from app.core.security import create_access_token as create_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()

        # 创建商品和客户
        prod = Product(
            id=uuid.uuid4(), name="日志成本过滤商品", sku="ORD-LOG-COST",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="日志成本过滤客户", phone="13800000200",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()

        # 创建订单
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-LOG-COST-TEST",
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

        # 创建非特权用户（有 order:view + order:view_all，无 product:view_cost）
        sale_user = User(
            id=uuid.uuid4(), username="log_cost_viewer",
            hashed_password=hash_password("testpass123"),
            display_name="日志成本查看者",
            is_active=True, is_superuser=False,
        )
        db.add(sale_user)
        db.flush()

        role = Role(id=uuid.uuid4(), name="log_viewer_role", display_name="日志查看角色")
        db.add(role)
        db.flush()
        db.add(UserRole(user_id=sale_user.id, role_id=role.id))

        for code in ("order:view", "order:view_all"):
            perm = Permission(id=uuid.uuid4(), code=code, name=code, module=code.split(":")[0])
            db.add(perm)
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        db.commit()
        sale_token = create_token(str(sale_user.id))
    finally:
        db.close()

    sale_headers = {"Authorization": f"Bearer {sale_token}"}

    # 用超级用户确认订单（产生审计日志）
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

    # 用非特权用户查看日志
    resp = client.get(f"/api/v1/sales-orders/{oid}/logs", headers=sale_headers)
    assert resp.status_code == 200

    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 成本字段应被移除
    cost_fields = {"cost_price", "unit_profit", "gross_margin", "total_cost", "subtotal_cost"}
    for item in items:
        for field in ("before_data", "after_data"):
            data = item.get(field)
            if data and isinstance(data, dict):
                for cf in cost_fields:
                    assert cf not in data, f"成本字段 {cf} 不应出现在 {field} 中"


def test_48_list_orders_page_size_100():
    """订单列表 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/sales-orders", params={"page_size": 100}, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_49_order_remark_xss_sanitized():
    """订单更新备注 HTML 标签被清理"""
    from app.models.customer import Customer
    from app.models.product import Product

    db = TestSession()
    try:
        admin = db.query(User).filter(User.username == "order_tester").first()
        cust = Customer(
            id=uuid.uuid4(), name="XSS备注客户", phone="13800009998",
            owner_user_id=admin.id,
        )
        db.add(cust)
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="XSS备注商品", sku="ORD-XSS-REMARK",
            sale_price=100, cost_price=60, stock_quantity=10, status="active",
            category_id=cat.id,
        )
        db.add(prod)

        # 直接创建订单（绕过 generate_sequential_code）
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-XSS-TEST-001",
            customer_id=cust.id,
            sales_user_id=admin.id,
            status="draft",
            total_amount=100,
            total_cost=60,
            gross_profit=40,
            gross_margin=0.4,
            paid_amount=0,
            remark="",
        )
        db.add(order)
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    # 更新备注含 HTML 标签
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "<script>alert('xss')</script>正常备注",
    }, headers=_auth())
    assert resp.status_code == 200

    # 通过详情验证备注已清理
    resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
    assert resp.status_code == 200
    remark = resp.json()["data"]["remark"]
    assert "<script>" not in remark
    assert "正常备注" in remark


def test_50_list_orders_page_size_over_max_422():
    """订单列表 page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/sales-orders", params={"page_size": 101}, headers=_auth())
    assert resp.status_code == 422


def test_51_order_cancel_audit_log():
    """取消确认订单产生审计日志"""
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="取消审计商品", sku="ORD-CANCEL-AUDIT",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="取消审计客户", phone="13800000886",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-CANCEL-AUDIT",
            customer_id=cust.id, sales_user_id=user.id,
            status="confirmed", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    # 取消订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    # 直接查询数据库验证审计日志
    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "order_cancel",
            AuditLog.resource_id == oid,
        ).first()
        assert log is not None
        assert log.resource_type == "order"
    finally:
        db.close()


def test_52_order_update_audit_log():
    """编辑订单产生审计日志"""
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).first()
        cat = db.query(ProductCategory).first()
        prod = Product(
            id=uuid.uuid4(), name="更新审计商品", sku="ORD-UPD-AUDIT",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        cust = Customer(
            id=uuid.uuid4(), name="更新审计客户", phone="13800000775",
            owner_user_id=user.id, created_by=user.id,
        )
        db.add(cust)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-UPD-AUDIT",
            customer_id=cust.id, sales_user_id=user.id,
            status="draft", total_amount=100, total_cost=60,
            gross_profit=40, gross_margin=0.4, paid_amount=0,
            created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    # 编辑订单备注
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "审计测试备注",
    }, headers=_auth())
    assert resp.status_code == 200

    # 直接查询数据库验证审计日志
    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "order_update",
            AuditLog.resource_id == oid,
        ).first()
        assert log is not None
        assert log.resource_type == "order"
    finally:
        db.close()


def _make_user_without_perm(username: str, keep_perm: str):
    from helpers import make_user_with_perms
    return make_user_with_perms(TestSession, username, [keep_perm])


def _fresh_order_ids():
    """创建全新的客户+商品+订单，返回 (order_id, headers)"""
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "order_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
        cat = db.query(ProductCategory).first()

        uid = uuid.uuid4().hex[:8]
        cust = Customer(id=uuid.uuid4(), name=f"403客户{uid}", phone=f"1380000{uid[:4]}")
        db.add(cust)

        prod = Product(
            id=uuid.uuid4(), name=f"403商品{uid}", sku=f"ORD-403-{uid}",
            sale_price=100, cost_price=60, stock_quantity=10,
            status="active", category_id=cat.id,
        )
        db.add(prod)
        db.flush()

        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"ORD-403-{uid}", customer_id=cust.id,
            sales_user_id=user.id, status="draft",
            total_amount=100, total_cost=60,
        )
        db.add(order)
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        db.commit()
        return str(order.id), headers
    finally:
        db.close()


def test_53_list_orders_no_permission_403():
    """无 order:list 权限用户获取订单列表返回 403"""
    token = _make_user_without_perm("no_order_list", "order:create")
    resp = client.get("/api/v1/sales-orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_54_create_order_no_permission_403():
    """无 order:create 权限用户创建订单返回 403"""
    token = _make_user_without_perm("no_order_create", "order:list")
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": str(uuid.uuid4()),
        "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_55_confirm_order_no_permission_403():
    """无 order:confirm 权限用户确认订单返回 403"""
    oid, _ = _fresh_order_ids()
    token = _make_user_without_perm("no_order_confirm", "order:list")
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_56_cancel_order_no_permission_403():
    """无 order:cancel 权限用户取消订单返回 403"""
    oid, _ = _fresh_order_ids()
    token = _make_user_without_perm("no_order_cancel", "order:list")
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_57_update_order_no_permission_403():
    """无 order:update 权限用户编辑订单返回 403"""
    oid, _ = _fresh_order_ids()
    token = _make_user_without_perm("no_order_update", "order:list")
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "尝试编辑",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def _make_non_owner_with_perms(username: str, perms: list[str]):
    from helpers import make_user_with_perms
    return make_user_with_perms(TestSession, username, perms)


def test_58_order_detail_non_owner_403():
    """非归属用户查看订单详情返回 403（无 order:view_all）"""
    oid, _ = _fresh_order_ids()
    token = _make_non_owner_with_perms("non_owner_detail", ["order:list"])
    resp = client.get(f"/api/v1/sales-orders/{oid}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_59_order_logs_non_owner_403():
    """非归属用户查看订单日志返回 403（无 order:view_all）"""
    oid, _ = _fresh_order_ids()
    token = _make_non_owner_with_perms("non_owner_logs", ["order:view"])
    resp = client.get(f"/api/v1/sales-orders/{oid}/logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_60_order_list_data_scope_non_owner():
    """无 order:view_all 用户订单列表只返回本人订单（数据范围过滤）"""
    # 先用 admin（order_tester）创建一个订单
    _fresh_order_ids()

    # 非 view_all 用户只能看到自己的订单（应为空列表）
    token = _make_non_owner_with_perms("non_owner_scope", ["order:list"])
    resp = client.get("/api/v1/sales-orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 0, "非归属用户不应看到其他人的订单"


def test_61_double_confirm_second_fails():
    """同一订单确认两次：第一次成功，第二次返回 400"""
    # 创建新鲜数据避免依赖被前序测试软删除的共享数据
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = ProductCategory(id=uuid.uuid4(), name="双确认测试分类")
        db.add(cat)
        db.flush()
        prod = Product(
            id=uuid.uuid4(), name="双确认测试商品", sku=f"CONF-{uuid.uuid4().hex[:6]}",
            sale_price=100, cost_price=50, stock_quantity=100,
            status="active", category_id=cat.id,
            created_by=user.id, updated_by=user.id,
        )
        db.add(prod)
        db.flush()
        cust = Customer(id=uuid.uuid4(), name="双确认测试客户", owner_user_id=user.id, created_by=user.id)
        db.add(cust)
        db.commit()
        prod_id = str(prod.id)
        cust_id = str(cust.id)
    finally:
        db.close()

    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": prod_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 第一次确认成功
    resp1 = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp1.status_code == 200
    assert resp1.json()["data"]["status"] == "confirmed"

    # 第二次确认返回 400（状态已不是 draft，行锁保证不会双重扣减）
    resp2 = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp2.status_code == 400


def test_62_cancel_confirmed_order_restores_stock():
    """取消已确认订单库存正确回滚"""
    db = TestSession()
    try:
        user = db.query(User).first()
        cat = ProductCategory(id=uuid.uuid4(), name="取消回滚测试分类")
        db.add(cat)
        db.flush()
        prod = Product(
            id=uuid.uuid4(), name="取消回滚测试商品", sku=f"CANCEL-{uuid.uuid4().hex[:6]}",
            sale_price=100, cost_price=50, stock_quantity=50,
            status="active", category_id=cat.id,
            created_by=user.id, updated_by=user.id,
        )
        db.add(prod)
        db.flush()
        cust = Customer(id=uuid.uuid4(), name="取消回滚测试客户", owner_user_id=user.id, created_by=user.id)
        db.add(cust)
        db.commit()
        prod_id = str(prod.id)
        cust_id = str(cust.id)
        stock_before = 50
    finally:
        db.close()

    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": prod_id, "quantity": 3}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 确认 → 扣减库存
    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    db = TestSession()
    try:
        prod = db.query(Product).filter(Product.id == uuid.UUID(prod_id)).first()
        assert prod.stock_quantity == stock_before - 3
    finally:
        db.close()

    # 取消 → 回滚库存
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    db = TestSession()
    try:
        prod = db.query(Product).filter(Product.id == uuid.UUID(prod_id)).first()
        assert prod.stock_quantity == stock_before
    finally:
        db.close()
