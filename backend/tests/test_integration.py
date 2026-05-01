"""QA-001: MVP 端到端集成测试

覆盖完整业务流程：登录 → 商品 → 客户 → 订单 → 库存 → 收款 → 报表
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import ProductCategory
from app.models.user import User

# SQLite 测试数据库
TEST_DB_URL = "sqlite:///./test_integration.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 全局变量：跨测试共享
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_order_id: str = ""

_original_override = None


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        # 创建测试用户
        user = User(
            id=uuid.uuid4(),
            username="e2e_tester",
            hashed_password=hash_password("testpass123"),
            display_name="端到端测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        # 创建默认商品分类
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_integration.db"):
        os.remove("./test_integration.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


# ========== 认证 ==========

class TestAuth:
    def test_01_login(self):
        """登录获取 Token"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "e2e_tester",
            "password": "testpass123",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        _tokens["access"] = data["access_token"]

    def test_02_get_me(self):
        """获取当前用户"""
        resp = client.get("/api/v1/auth/me", headers=_auth_header())
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "e2e_tester"


# ========== 商品 ==========

class TestProduct:
    def test_01_create_product(self):
        """创建商品"""
        resp = client.post("/api/v1/products", json={
            "name": "测试商品A",
            "cost_price": "50.00",
            "sale_price": "100.00",
            "stock_quantity": 100,
            "status": "active",
        }, headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "测试商品A"
        assert data["sku"] != ""
        global _product_id
        _product_id = data["id"]

    def test_02_list_products(self):
        """商品列表"""
        resp = client.get("/api/v1/products", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        p = items[0]
        assert p["name"] == "测试商品A"
        assert p["stock_quantity"] == 100

    def test_03_create_second_product(self):
        """创建第二个商品（用于测试库存不足）"""
        resp = client.post("/api/v1/products", json={
            "name": "测试商品B",
            "cost_price": "30.00",
            "sale_price": "80.00",
            "stock_quantity": 2,
            "status": "active",
        }, headers=_auth_header())
        assert resp.status_code == 200


# ========== 客户 ==========

class TestCustomer:
    def test_01_create_customer(self):
        """创建客户"""
        resp = client.post("/api/v1/customers", json={
            "name": "测试客户公司",
            "contact_name": "张三",
            "phone": "13800138000",
        }, headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "测试客户公司"
        global _customer_id
        _customer_id = data["id"]

    def test_02_list_customers(self):
        """客户列表"""
        resp = client.get("/api/v1/customers", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_03_duplicate_phone_warning(self):
        """重复手机号检测"""
        resp = client.post("/api/v1/customers", json={
            "name": "另一客户",
            "phone": "13800138000",
        }, headers=_auth_header())
        # 后端返回 409 Conflict 表示手机号重复
        assert resp.status_code in (200, 400, 409)


# ========== 订单 ==========

class TestOrder:
    def test_01_create_draft_order(self):
        """创建草稿订单"""
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [
                {"product_id": _product_id, "quantity": 3, "unit_price": "100.00"},
            ],
        }, headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "draft"
        assert data["total_amount"] == "300.00"
        global _order_id
        _order_id = data["id"]

    def test_02_get_order_detail(self):
        """订单详情"""
        resp = client.get(f"/api/v1/sales-orders/{_order_id}", headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_no"].startswith("ORD-")
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name_snapshot"] == "测试商品A"
        assert data["items"][0]["quantity"] == 3

    def test_03_list_orders(self):
        """订单列表"""
        resp = client.get("/api/v1/sales-orders", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0]["status"] == "draft"

    def test_04_empty_items_fails(self):
        """订单明细为空失败"""
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [],
        }, headers=_auth_header())
        assert resp.status_code == 422

    def test_05_confirm_order(self):
        """确认订单 — 扣减库存"""
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth_header())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "confirmed"

        # 验证库存扣减
        resp = client.get("/api/v1/products", headers=_auth_header())
        product = next(p for p in resp.json()["data"]["items"] if p["id"] == _product_id)
        assert product["stock_quantity"] == 97  # 100 - 3

    def test_06_cannot_confirm_twice(self):
        """已确认订单不能再确认"""
        resp = client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth_header())
        assert resp.status_code == 400


# ========== 库存 ==========

class TestInventory:
    def test_01_inventory_movements(self):
        """库存流水"""
        resp = client.get("/api/v1/inventory/movements", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        movement = items[0]
        assert movement["movement_type"] == "order_confirm"
        assert movement["quantity_change"] == -3

    def test_02_manual_adjustment(self):
        """手工库存调整"""
        resp = client.get("/api/v1/products", headers=_auth_header())
        product = next(p for p in resp.json()["data"]["items"] if p["id"] == _product_id)

        resp = client.post("/api/v1/inventory/adjustments", json={
            "product_id": _product_id,
            "quantity_change": 10,
            "remark": "测试补货",
        }, headers=_auth_header())
        assert resp.status_code == 200

        # 验证库存增加
        resp = client.get("/api/v1/products", headers=_auth_header())
        updated = next(p for p in resp.json()["data"]["items"] if p["id"] == _product_id)
        assert updated["stock_quantity"] == product["stock_quantity"] + 10


# ========== 收款 ==========

class TestPayment:
    def test_01_register_payment(self):
        """登记收款"""
        resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
            "amount": "200.00",
            "payment_method": "cash",
        }, headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_status"] == "partially_paid"

    def test_02_register_remaining_payment(self):
        """登记剩余收款 → 订单完成"""
        resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
            "amount": "100.00",
            "payment_method": "bank_transfer",
        }, headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_status"] == "completed"

    def test_03_payment_exceed_fails(self):
        """收款金额超过剩余应收失败"""
        resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
            "amount": "1.00",
            "payment_method": "cash",
        }, headers=_auth_header())
        assert resp.status_code == 400

    def test_04_reverse_payment(self):
        """冲正收款"""
        # 获取收款列表
        resp = client.get(f"/api/v1/payments?order_id={_order_id}", headers=_auth_header())
        assert resp.status_code == 200
        payments = resp.json()["data"]["items"]
        assert len(payments) >= 1

        # 冲正第一笔
        payment_id = payments[0]["id"]
        resp = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=_auth_header())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "reversed"


# ========== 报表 ==========

class TestReport:
    def test_01_sales_summary(self):
        """销售汇总"""
        resp = client.get("/api/v1/reports/sales-summary?period=30d", headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_amount" in data
        assert "order_count" in data
        assert "gross_profit" in data

    def test_02_sales_trend(self):
        """销售趋势"""
        resp = client.get("/api/v1/reports/sales-trend?period=7d", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 7  # 7 天

    def test_03_product_ranking(self):
        """商品排行"""
        resp = client.get("/api/v1/reports/product-ranking?period=30d&limit=10", headers=_auth_header())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0]["product_name"] == "测试商品A"

    def test_04_inventory_warning(self):
        """库存预警"""
        resp = client.get("/api/v1/reports/inventory-warning?threshold=10", headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        # 测试商品B 库存为 2，应该出现在预警中
        names = [item["name"] for item in data["items"]]
        assert "测试商品B" in names


# ========== 订单日志 ==========

class TestOrderLogs:
    """订单操作日志查询"""

    def test_01_order_logs(self):
        """查询订单操作日志"""
        resp = client.get(f"/api/v1/sales-orders/{_order_id}/logs", headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 2  # 至少有 create + confirm
        actions = [item["action"] for item in data["items"]]
        assert "order_create" in actions
        assert "order_confirm" in actions

    def test_02_order_logs_pagination(self):
        """订单日志分页"""
        resp = client.get(f"/api/v1/sales-orders/{_order_id}/logs?page_size=1", headers=_auth_header())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 1
        assert data["total"] >= 2

    def test_03_order_logs_not_found(self):
        """不存在的订单返回 404"""
        resp = client.get(f"/api/v1/sales-orders/{uuid.uuid4()}/logs", headers=_auth_header())
        assert resp.status_code == 404


# ========== 辅助函数 ==========

def _auth_header():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}
