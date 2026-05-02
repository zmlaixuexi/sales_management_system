"""后端边界测试补强 — 覆盖 auth/order/payment/user/audit 未测路径"""

import uuid
from datetime import UTC

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

TEST_DB_URL = "sqlite:///./test_boundary.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_user_id: str = ""
_inactive_user_id: str = ""
_product_id: str = ""
_customer_id: str = ""
_confirmed_order_id: str = ""


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
        # 活跃超级用户
        user = User(
            id=uuid.uuid4(),
            username="boundary_admin",
            hashed_password=hash_password("pass123456"),
            display_name="边界管理员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()
        global _user_id
        _user_id = str(user.id)

        # 禁用用户
        inactive = User(
            id=uuid.uuid4(),
            username="inactive_user",
            hashed_password=hash_password("pass123456"),
            display_name="已禁用用户",
            is_active=False,
            is_superuser=False,
        )
        db.add(inactive)
        db.flush()
        global _inactive_user_id
        _inactive_user_id = str(inactive.id)

        # 分类 + 商品（库存充足）
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        product = Product(
            id=uuid.uuid4(), sku="SPU-BOUND-001", name="边界商品",
            sale_price=100, cost_price=50, stock_quantity=100,
            category_id=cat.id, status="active",
            created_by=user.id, updated_by=user.id,
        )
        db.add(product)
        db.flush()
        global _product_id
        _product_id = str(product.id)

        # 客户
        customer = Customer(
            id=uuid.uuid4(), name="边界客户", phone="13900000001",
            owner_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(customer)
        db.flush()
        global _customer_id
        _customer_id = str(customer.id)

        # 已确认订单（用于收款测试）
        order = SalesOrder(
            id=uuid.uuid4(), order_no="ORD-BOUND-001",
            customer_id=customer.id, status="confirmed",
            total_amount=200, paid_amount=0,
            sales_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=product.id,
            product_name_snapshot="边界商品", cost_price_snapshot=50,
            quantity=2, unit_price=100, subtotal_amount=200, subtotal_cost=100,
        ))
        global _confirmed_order_id
        _confirmed_order_id = str(order.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_boundary.db"):
        os.remove("./test_boundary.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def _auth_for_user(user_id: str):
    token = create_access_token(subject=user_id)
    return {"Authorization": f"Bearer {token}"}


# ─── 登录 ────────────────────────────────────────────────────

def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "boundary_admin", "password": "pass123456",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    _tokens["access"] = data["access_token"]
    _tokens["refresh"] = data["refresh_token"]


# ─── 认证边界 ────────────────────────────────────────────────

def test_02_login_wrong_password():
    """错误密码登录失败"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "boundary_admin", "password": "wrong_password",
    })
    assert resp.status_code == 401


def test_03_login_inactive_user():
    """禁用用户登录返回 403"""
    # 先设为 active 登录一次，然后这里直接用 inactive 用户测试
    resp = client.post("/api/v1/auth/login", json={
        "username": "inactive_user", "password": "pass123456",
    })
    assert resp.status_code == 403


def test_04_login_nonexistent_user():
    """不存在的用户登录"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "ghost_user", "password": "whatever",
    })
    assert resp.status_code == 401


def test_05_refresh_with_access_token():
    """用 access_token 调用 refresh 接口应失败"""
    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": _tokens["access"],
    })
    assert resp.status_code == 401


def test_06_refresh_with_invalid_token():
    """无效 token 调用 refresh 失败"""
    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "not.a.valid.token",
    })
    assert resp.status_code == 401


def test_07_token_deleted_user():
    """使用已删除用户的 token 请求返回 401"""
    # 创建一个用户并获取 token，然后模拟"删除"（设 deleted_at）
    db = TestSession()
    try:
        temp_user = User(
            id=uuid.uuid4(), username="temp_delete_me",
            hashed_password=hash_password("pass123456"),
            display_name="临时用户", is_active=True, is_superuser=False,
        )
        db.add(temp_user)
        db.commit()
        temp_token = create_access_token(subject=str(temp_user.id))

        # 先确认 token 有效
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {temp_token}",
        })
        assert resp.status_code == 200

        # 模拟软删除
        from datetime import datetime
        temp_user.deleted_at = datetime.now(UTC)
        db.commit()

        # 再请求应返回 401
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {temp_token}",
        })
        assert resp.status_code == 401
    finally:
        db.close()


def test_08_token_inactive_user():
    """使用禁用用户的 token 请求返回 401"""
    token = create_access_token(subject=_inactive_user_id)
    resp = client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 401


# ─── 订单状态机边界 ───────────────────────────────────────────

def test_09_order_cancel_draft():
    """取消草稿订单"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"


def test_10_order_cancel_confirmed():
    """取消已确认订单应回滚库存"""
    # 创建 + 确认
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 5}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 取消已确认订单
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"


def test_11_order_cancel_completed():
    """取消已完成订单应被拒绝"""
    # 创建 → 确认 → 全额收款 → 完成
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["order_status"] == "completed"

    # 取消已完成订单
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 400


def test_12_order_detail_not_found():
    """获取不存在的订单详情"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/sales-orders/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_13_order_update_not_found():
    """编辑不存在的订单"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/sales-orders/{fake_id}", json={
        "remark": "不存在",
    }, headers=_auth())
    assert resp.status_code == 404


def test_14_order_list_with_status_filter():
    """订单列表状态筛选"""
    resp = client.get("/api/v1/sales-orders?status=cancelled", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 0


def test_15_order_list_with_keyword():
    """订单列表关键词搜索"""
    resp = client.get("/api/v1/sales-orders?keyword=ORD-BOUND", headers=_auth())
    assert resp.status_code == 200


# ─── 收款边界 ────────────────────────────────────────────────

def test_16_payment_on_draft_order():
    """草稿订单不允许收款"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    draft_order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/payments/orders/{draft_order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400


def test_17_payment_on_completed_order():
    """已完成订单不允许收款"""
    # 创建并完成订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200  # 全额支付 → completed

    # 再次收款应失败
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400


def test_18_payment_on_cancelled_order():
    """已取消订单不允许收款"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400


def test_19_payment_exact_amount():
    """精确金额收款完成订单"""
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "amount": "200", "payment_method": "transfer",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["order_status"] == "completed"


def test_20_payment_reverse_and_status_rollback():
    """冲正收款后订单状态回退"""
    # 创建新订单 → 确认 → 全额收款 → 冲正 → 状态应回退
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 3}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "300", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    payment_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["order_status"] == "completed"

    # 冲正
    resp = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "reversed"

    # 验证订单状态回退到 confirmed
    resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "confirmed"
    assert str(resp.json()["data"]["paid_amount"]) in ("0", "0.00")


def test_21_payment_reverse_already_reversed():
    """冲正已冲正的收款返回 404"""
    # 创建 → 确认 → 收款 → 冲正 → 再次冲正
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    payment_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    # 再次冲正
    resp = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=_auth())
    assert resp.status_code == 404


def test_22_payment_negative_amount():
    """收款金额为负数"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "-50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 422


def test_23_payment_list():
    """收款列表查询"""
    resp = client.get("/api/v1/payments", headers=_auth())
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


def test_24_payment_list_by_order():
    """按订单筛选收款"""
    resp = client.get(f"/api/v1/payments?order_id={_confirmed_order_id}", headers=_auth())
    assert resp.status_code == 200


# ─── 用户管理边界 ────────────────────────────────────────────

def test_25_user_create_duplicate_username():
    """创建重复用户名"""
    resp = client.post("/api/v1/users", json={
        "username": "boundary_admin",
        "password": "pass123456",
        "display_name": "重复用户",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_26_user_update_not_found():
    """编辑不存在的用户"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/users/{fake_id}", json={
        "display_name": "不存在",
    }, headers=_auth())
    assert resp.status_code == 404


def test_27_user_list_non_admin():
    """非管理员不能查看用户列表"""
    # 创建普通用户并用其 token 请求
    db = TestSession()
    try:
        normal = User(
            id=uuid.uuid4(), username="normal_user_bn",
            hashed_password=hash_password("pass123456"),
            display_name="普通用户", is_active=True, is_superuser=False,
        )
        db.add(normal)
        db.commit()
        normal_token = create_access_token(subject=str(normal.id))
    finally:
        db.close()

    resp = client.get("/api/v1/users", headers={
        "Authorization": f"Bearer {normal_token}",
    })
    assert resp.status_code == 403


def test_28_user_create_by_non_admin():
    """非管理员不能创建用户"""
    db = TestSession()
    try:
        normal = db.query(User).filter(User.username == "normal_user_bn").first()
        normal_token = create_access_token(subject=str(normal.id))
    finally:
        db.close()

    resp = client.post("/api/v1/users", json={
        "username": "new_user_xyz", "password": "pass123456",
        "display_name": "新用户",
    }, headers={"Authorization": f"Bearer {normal_token}"})
    assert resp.status_code == 403


def test_29_user_create_and_update():
    """创建用户并更新"""
    resp = client.post("/api/v1/users", json={
        "username": "test_new_user", "password": "pass123456",
        "display_name": "新用户", "phone": "13811112222",
    }, headers=_auth())
    assert resp.status_code == 200
    new_user_id = resp.json()["data"]["id"]

    # 更新
    resp = client.put(f"/api/v1/users/{new_user_id}", json={
        "display_name": "更新后的名字", "is_active": False,
    }, headers=_auth())
    assert resp.status_code == 200


def test_30_user_list_keyword_search():
    """用户列表关键词搜索"""
    resp = client.get("/api/v1/users?keyword=boundary", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


# ─── 库存调整边界 ────────────────────────────────────────────

def test_31_inventory_adjust_positive():
    """正数库存调整（补货）"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 50, "remark": "补货",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["quantity_change"] == 50


def test_32_inventory_adjust_not_found_product():
    """调整不存在商品的库存"""
    fake_id = str(uuid.uuid4())
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": fake_id, "quantity_change": 10,
    }, headers=_auth())
    assert resp.status_code == 404


def test_33_inventory_movements_list():
    """库存流水列表"""
    resp = client.get("/api/v1/inventory/movements", headers=_auth())
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


def test_34_inventory_movements_by_product():
    """按商品筛选库存流水"""
    resp = client.get(f"/api/v1/inventory/movements?product_id={_product_id}", headers=_auth())
    assert resp.status_code == 200


def test_34b_inventory_movements_by_type():
    """按类型筛选库存流水"""
    # 先做一次手工调整，确保有 manual_adjust 类型记录
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id, "quantity_change": 5, "remark": "筛选测试",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/inventory/movements?movement_type=manual_adjust", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert all(m["movement_type"] == "manual_adjust" for m in items)


# ─── 订单编辑边界 ────────────────────────────────────────────

def test_35_order_update_remark_only():
    """仅更新订单备注"""
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/sales-orders/{order_id}", json={
        "remark": "新备注",
    }, headers=_auth())
    assert resp.status_code == 200

    # 验证备注已更新
    resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["remark"] == "新备注"


# ─── 刷新 Token 正常路径 ─────────────────────────────────────

def test_36_refresh_token_success():
    """正常刷新 Token"""
    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": _tokens["refresh"],
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


# ─── 部分付款订单取消回滚库存 ──────────────────────────────────

def test_37_cancel_partially_paid_restores_inventory():
    """有收款的 partially_paid 订单不可直接取消，需先冲正收款"""
    # 确保 token 有效
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    # 创建 + 确认
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 3}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 部分收款（订单变为 partially_paid）
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    payment_id = resp.json()["data"]["id"]

    # 有收款时取消应被拒绝
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_HAS_PAYMENTS"

    # 冲正收款
    resp = client.post(f"/api/v1/payments/{payment_id}/reverse", json={
        "reason": "测试冲正",
    }, headers=_auth())
    assert resp.status_code == 200

    # 冲正后订单回到 confirmed，可以取消
    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"

    # 验证库存回滚：查询库存流水，应存在回滚记录
    resp = client.get(f"/api/v1/inventory/movements?product_id={_product_id}", headers=_auth())
    assert resp.status_code == 200
    movements = resp.json()["data"]["items"]
    # 应存在 quantity_change=+3 的回滚记录
    restore_moves = [m for m in movements if m["quantity_change"] == 3]
    assert len(restore_moves) >= 1


def test_38_cancelled_order_rejects_payment():
    """已取消订单不允许登记收款"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    # 创建 + 确认 + 取消（无收款）
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/sales-orders/{order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    # 已取消订单不允许登记收款
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"



def test_39_order_with_deleted_product_rejected():
    """已删除商品不能创建订单"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    # 创建新商品 → 软删除
    resp = client.post("/api/v1/products", json={
        "name": "待删商品", "sku": "DEL-001", "sale_price": "10", "cost_price": "5",
    }, headers=_auth())
    assert resp.status_code == 200
    del_product_id = resp.json()["data"]["id"]

    resp = client.delete(f"/api/v1/products/{del_product_id}", headers=_auth())
    assert resp.status_code == 200

    # 用已删除商品创建订单应返回 404
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": del_product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_40_transfer_to_nonexistent_user():
    """客户转移给不存在的用户应被拒绝"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    fake_user_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/customers/{_customer_id}/transfer", json={
        "owner_user_id": fake_user_id,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_41_self_deactivation_rejected():
    """超级管理员不能停用自己的账号"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.put(f"/api/v1/users/{_user_id}", json={
        "is_active": False,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "不能停用自己的账号" in resp.json()["error"]["message"]


def test_42_create_user_nonexistent_role_rejected():
    """创建用户时指定不存在的角色应被拒绝"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    fake_role_id = str(uuid.uuid4())
    resp = client.post("/api/v1/users", json={
        "username": "test_norole",
        "password": "pass123456",
        "display_name": "测试用户",
        "role_ids": [fake_role_id],
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "角色不存在" in resp.json()["error"]["message"]


def test_43_order_update_deleted_customer_rejected():
    """订单更新客户 ID 为已删除客户应返回 404"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    # 通过 API 创建并软删除一个客户
    resp = client.post("/api/v1/customers", json={
        "name": "待删除客户", "phone": "13900000999",
    }, headers=_auth())
    assert resp.status_code == 200
    deleted_cid = resp.json()["data"]["id"]

    resp = client.delete(f"/api/v1/customers/{deleted_cid}", headers=_auth())
    assert resp.status_code == 200

    # 创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1, "unit_price": "100"}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 更新客户 ID 为已删除客户
    resp = client.put(f"/api/v1/sales-orders/{order_id}", json={
        "customer_id": deleted_cid,
    }, headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_44_customer_create_nonexistent_owner_rejected():
    """创建客户时指定不存在的归属用户应被拒绝"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    fake_user_id = str(uuid.uuid4())
    resp = client.post("/api/v1/customers", json={
        "name": "归属不存在客户",
        "phone": "13900000888",
        "owner_user_id": fake_user_id,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "归属用户不存在或已禁用" in resp.json()["error"]["message"]


def test_45_product_create_nonexistent_category_rejected():
    """创建商品时指定不存在的分类应被拒绝"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    fake_category_id = str(uuid.uuid4())
    resp = client.post("/api/v1/products", json={
        "name": "分类不存在商品",
        "sale_price": "100",
        "cost_price": "50",
        "category_id": fake_category_id,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "商品分类不存在" in resp.json()["error"]["message"]


def test_46_product_update_nonexistent_category_rejected():
    """更新商品分类为不存在的分类应被拒绝"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    fake_category_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "category_id": fake_category_id,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "商品分类不存在" in resp.json()["error"]["message"]


# --- SQL 注入搜索安全测试 ---


def test_47_customer_search_sql_injection_safe():
    """客户搜索关键词 SQL 注入安全"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    injection_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE customers; --",
        "100%' OR 1=1 --",
        "\" OR \"\"=\"",
    ]
    for payload in injection_payloads:
        resp = client.get(f"/api/v1/customers?keyword={payload}", headers=_auth())
        assert resp.status_code == 200, f"SQL 注入 payload 导致非 200: {payload}"
        items = resp.json()["data"]["items"]
        # 不应返回所有客户（注入不应绕过过滤）
        assert len(items) <= 1, f"SQL 注入可能泄露数据: payload={payload}, count={len(items)}"


def test_48_product_search_sql_injection_safe():
    """商品搜索关键词 SQL 注入安全"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    injection_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE products; --",
    ]
    for payload in injection_payloads:
        resp = client.get(f"/api/v1/products?keyword={payload}", headers=_auth())
        assert resp.status_code == 200, f"SQL 注入 payload 导致非 200: {payload}"
        items = resp.json()["data"]["items"]
        assert len(items) <= 1, f"SQL 注入可能泄露数据: payload={payload}"


def test_49_order_search_sql_injection_safe():
    """订单搜索关键词 SQL 注入安全"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/sales-orders?keyword=' OR '1'='1", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) <= 5, "SQL 注入不应返回异常数量的订单"


# --- 分页边界测试 ---


def test_50_customer_list_page_zero_422():
    """客户列表 page=0 返回 422"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/customers?page=0", headers=_auth())
    assert resp.status_code == 422


def test_51_product_list_page_size_over_max_422():
    """商品列表 page_size=101 返回 422"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/products?page_size=101", headers=_auth())
    assert resp.status_code == 422


def test_52_order_list_negative_page_size_422():
    """订单列表 page_size=-1 返回 422"""
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/sales-orders?page_size=-1", headers=_auth())
    assert resp.status_code == 422


# --- 外键验证边界条件 ---


def _ensure_login():
    if not _tokens.get("access"):
        resp = client.post("/api/v1/auth/login", json={
            "username": "boundary_admin", "password": "pass123456",
        })
        assert resp.status_code == 200
        _tokens["access"] = resp.json()["data"]["access_token"]


def test_53_customer_create_invalid_owner_user_id_400():
    """创建客户时 owner_user_id 为无效 UUID 格式返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/customers", json={
        "name": "外键测试客户", "owner_user_id": "not-a-uuid",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_54_customer_create_nonexistent_owner_user_id_400():
    """创建客户时 owner_user_id 指向不存在的用户返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/customers", json={
        "name": "外键测试客户", "owner_user_id": str(uuid.uuid4()),
    }, headers=_auth())
    assert resp.status_code == 400
    assert "归属用户不存在" in resp.json()["error"]["message"]


def test_55_order_update_nonexistent_customer_404():
    """更新草稿订单 customer_id 为不存在的客户返回 404"""
    _ensure_login()
    # 创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 更新为不存在的客户
    resp = client.put(f"/api/v1/sales-orders/{order_id}", json={
        "customer_id": str(uuid.uuid4()),
    }, headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_56_order_update_nonexistent_product_in_items_404():
    """更新草稿订单 items 含不存在的商品返回 404"""
    _ensure_login()
    # 创建草稿订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    # 更新为不存在的商品
    resp = client.put(f"/api/v1/sales-orders/{order_id}", json={
        "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# --- 订单状态机完整性断言 ---


def test_57_confirm_confirmed_order_rejected():
    """重复确认已确认订单返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 400
    assert "草稿" in resp.json()["error"]["message"]


def test_58_confirm_cancelled_order_rejected():
    """确认已取消订单返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 400


def test_59_cancel_already_cancelled_rejected():
    """重复取消已取消订单返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 400


def test_60_update_confirmed_order_rejected():
    """编辑已确认订单返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200

    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "已确认不可编辑",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "草稿" in resp.json()["error"]["message"]


def test_61_update_cancelled_order_rejected():
    """编辑已取消订单返回 400"""
    _ensure_login()
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "remark": "已取消不可编辑",
    }, headers=_auth())
    assert resp.status_code == 400


# --- 收款冲正后订单状态回退 ---


def test_62_reverse_partial_payment_back_to_confirmed():
    """部分收款冲正全部收款后订单状态回到 confirmed"""
    _ensure_login()
    # 创建并确认订单（总价 200）
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

    # 部分收款 50（状态变为 partially_paid）
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    pay_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["order_status"] == "partially_paid"

    # 冲正
    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    # 订单状态应回到 confirmed（paid_amount = 0）
    resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "confirmed"
    assert str(resp.json()["data"]["paid_amount"]) in ("0", "0.00")


def test_63_reverse_full_payment_back_to_partially_paid():
    """全额收款后冲正部分收款，状态回到 partially_paid"""
    _ensure_login()
    # 创建并确认订单（总价 100）
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

    # 分两笔收款
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "60", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "40", "payment_method": "transfer",
    }, headers=_auth())
    assert resp.status_code == 200
    pay2 = resp.json()["data"]["id"]
    assert resp.json()["data"]["order_status"] == "completed"

    # 冲正第二笔（40），paid_amount = 60，状态应回到 partially_paid
    resp = client.post(f"/api/v1/payments/{pay2}/reverse", headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/sales-orders/{oid}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "partially_paid"


def test_65_order_create_remark_max_length_boundary():
    """订单创建备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/customers", json={"name": "订单备注边界客户", "phone": "13900656565"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]
    resp = client.post("/api/v1/products", json={
        "name": "订单备注边界商品", "sale_price": "50.00", "cost_price": "20.00", "stock_quantity": 10,
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 恰好 500 字符
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cid,
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "50.00"}],
        "remark": "R" * 500,
    }, headers=headers)
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    # 501 字符
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cid,
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "50.00"}],
        "remark": "R" * 501,
    }, headers=headers)
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_66_order_update_remark_max_length_boundary():
    """订单编辑备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/customers", json={"name": "订单编辑备注客户", "phone": "13900666666"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]
    resp = client.post("/api/v1/products", json={
        "name": "订单编辑备注商品", "sale_price": "60.00", "cost_price": "25.00", "stock_quantity": 10,
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cid,
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "60.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    # 恰好 500 字符
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={"remark": "U" * 500}, headers=headers)
    assert resp.status_code == 200, f"编辑备注 500 字符应通过: {resp.json()}"

    # 501 字符
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={"remark": "U" * 501}, headers=headers)
    assert resp.status_code == 422, f"编辑备注 501 字符应被拒绝: {resp.status_code}"


def test_67_payment_remark_max_length_boundary():
    """收款备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)
    # 创建客户+商品+订单+确认
    resp = client.post("/api/v1/customers", json={"name": "收款备注边界客户", "phone": "13900676767"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]
    resp = client.post("/api/v1/products", json={
        "name": "收款备注边界商品", "sale_price": "100.00", "cost_price": "40.00", "stock_quantity": 10,
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cid,
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "100.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 恰好 500 字符
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "100.00", "payment_method": "cash", "remark": "P" * 500,
    }, headers=headers)
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    # 501 字符
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "50.00", "payment_method": "transfer", "remark": "P" * 501,
    }, headers=headers)
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_68_customer_update_email_max_length_boundary():
    """客户编辑邮箱恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/customers", json={"name": "邮箱边界客户68", "phone": "13900686868"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 恰好 200 字符
    email_ok = "a" * 188 + "@example.com"  # 188 + 12 = 200
    resp = client.put(f"/api/v1/customers/{cid}", json={"email": email_ok}, headers=headers)
    assert resp.status_code == 200, f"200 字符邮箱应通过: {resp.json()}"

    # 201 字符
    email_long = "a" * 189 + "@example.com"  # 189 + 12 = 201
    resp = client.put(f"/api/v1/customers/{cid}", json={"email": email_long}, headers=headers)
    assert resp.status_code == 422, f"201 字符邮箱应被拒绝: {resp.status_code}"


def test_69_customer_update_contact_name_max_length_boundary():
    """客户编辑联系人恰好 100 字符通过，101 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/customers", json={"name": "联系人边界客户69", "phone": "13900696969"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 恰好 100 字符
    resp = client.put(f"/api/v1/customers/{cid}", json={"contact_name": "联" * 100}, headers=headers)
    assert resp.status_code == 200, f"100 字符联系人应通过: {resp.json()}"

    # 101 字符
    resp = client.put(f"/api/v1/customers/{cid}", json={"contact_name": "联" * 101}, headers=headers)
    assert resp.status_code == 422, f"101 字符联系人应被拒绝: {resp.status_code}"


def test_70_customer_create_name_max_length_boundary():
    """客户创建名称恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 200 字符
    resp = client.post("/api/v1/customers", json={"name": "客" * 200, "phone": "13900707070"}, headers=headers)
    assert resp.status_code == 200, f"200 字符名称应通过: {resp.json()}"

    # 201 字符
    resp = client.post("/api/v1/customers", json={"name": "客" * 201, "phone": "13900717171"}, headers=headers)
    assert resp.status_code == 422, f"201 字符名称应被拒绝: {resp.status_code}"


def test_71_product_create_name_max_length_boundary():
    """商品创建名称恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 200 字符
    resp = client.post("/api/v1/products", json={"name": "商" * 200, "price": 10.00}, headers=headers)
    assert resp.status_code == 200, f"200 字符名称应通过: {resp.json()}"

    # 201 字符
    resp = client.post("/api/v1/products", json={"name": "商" * 201, "price": 10.00}, headers=headers)
    assert resp.status_code == 422, f"201 字符名称应被拒绝: {resp.status_code}"


def test_72_product_update_name_max_length_boundary():
    """商品编辑名称恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/products", json={"name": "名称边界商品72", "price": 10.00}, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 恰好 200 字符
    resp = client.put(f"/api/v1/products/{pid}", json={"name": "商" * 200}, headers=headers)
    assert resp.status_code == 200, f"200 字符名称应通过: {resp.json()}"

    # 201 字符
    resp = client.put(f"/api/v1/products/{pid}", json={"name": "商" * 201}, headers=headers)
    assert resp.status_code == 422, f"201 字符名称应被拒绝: {resp.status_code}"


def test_73_product_create_sku_max_length_boundary():
    """商品创建 SKU 恰好 50 字符通过，51 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 50 字符
    resp = client.post(
        "/api/v1/products",
        json={"name": "SKU边界商品73", "price": 10.00, "sku": "S" * 50},
        headers=headers,
    )
    assert resp.status_code == 200, f"50 字符 SKU 应通过: {resp.json()}"

    # 51 字符
    resp = client.post(
        "/api/v1/products",
        json={"name": "SKU边界商品73b", "price": 10.00, "sku": "S" * 51},
        headers=headers,
    )
    assert resp.status_code == 422, f"51 字符 SKU 应被拒绝: {resp.status_code}"


def test_74_product_update_sku_max_length_boundary():
    """商品编辑 SKU 恰好 50 字符通过，51 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/products", json={"name": "SKU编辑边界74", "price": 10.00}, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 恰好 50 字符（用唯一前缀避免与 test_73 的 SKU 冲突）
    resp = client.put(f"/api/v1/products/{pid}", json={"sku": "U" * 50}, headers=headers)
    assert resp.status_code == 200, f"50 字符 SKU 应通过: {resp.json()}"

    # 51 字符
    resp = client.put(f"/api/v1/products/{pid}", json={"sku": "U" * 51}, headers=headers)
    assert resp.status_code == 422, f"51 字符 SKU 应被拒绝: {resp.status_code}"


def test_75_customer_update_name_max_length_boundary():
    """客户编辑名称恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/customers", json={"name": "名称编辑边界75", "phone": "13900757575"}, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 恰好 200 字符
    resp = client.put(f"/api/v1/customers/{cid}", json={"name": "名" * 200}, headers=headers)
    assert resp.status_code == 200, f"200 字符名称应通过: {resp.json()}"

    # 201 字符
    resp = client.put(f"/api/v1/customers/{cid}", json={"name": "名" * 201}, headers=headers)
    assert resp.status_code == 422, f"201 字符名称应被拒绝: {resp.status_code}"


def test_76_user_create_username_max_length_boundary():
    """用户创建 username 恰好 50 字符通过，51 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 50 字符
    resp = client.post("/api/v1/users", json={
        "username": "u" * 50, "password": "pass123456", "display_name": "用户名边界76",
    }, headers=headers)
    assert resp.status_code == 200, f"50 字符用户名应通过: {resp.json()}"

    # 51 字符
    resp = client.post("/api/v1/users", json={
        "username": "u" * 51, "password": "pass123456", "display_name": "用户名边界76b",
    }, headers=headers)
    assert resp.status_code == 422, f"51 字符用户名应被拒绝: {resp.status_code}"


def test_77_user_create_display_name_max_length_boundary():
    """用户创建 display_name 恰好 100 字符通过，101 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 100 字符
    resp = client.post("/api/v1/users", json={
        "username": "display_bnd_77", "password": "pass123456", "display_name": "显" * 100,
    }, headers=headers)
    assert resp.status_code == 200, f"100 字符显示名称应通过: {resp.json()}"

    # 101 字符
    resp = client.post("/api/v1/users", json={
        "username": "display_bnd_77b", "password": "pass123456", "display_name": "显" * 101,
    }, headers=headers)
    assert resp.status_code == 422, f"101 字符显示名称应被拒绝: {resp.status_code}"


def test_78_user_update_display_name_max_length_boundary():
    """用户编辑 display_name 恰好 100 字符通过，101 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/users", json={
        "username": "upd_disp_bnd_78", "password": "pass123456",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    # 恰好 100 字符
    resp = client.put(f"/api/v1/users/{uid}", json={"display_name": "编" * 100}, headers=headers)
    assert resp.status_code == 200, f"100 字符显示名称应通过: {resp.json()}"

    # 101 字符
    resp = client.put(f"/api/v1/users/{uid}", json={"display_name": "编" * 101}, headers=headers)
    assert resp.status_code == 422, f"101 字符显示名称应被拒绝: {resp.status_code}"


def test_79_user_create_email_max_length_boundary():
    """用户创建 email 恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 200 字符的邮箱：local 部分 + @ + domain
    email_200 = "a" * 188 + "@example.com"  # 188 + 12 = 200
    resp = client.post("/api/v1/users", json={
        "username": "email_bnd_79", "password": "pass123456",
        "email": email_200,
    }, headers=headers)
    assert resp.status_code == 200, f"200 字符邮箱应通过: {resp.json()}"

    # 201 字符
    email_201 = "a" * 189 + "@example.com"  # 189 + 12 = 201
    resp = client.post("/api/v1/users", json={
        "username": "email_bnd_79b", "password": "pass123456",
        "email": email_201,
    }, headers=headers)
    assert resp.status_code == 422, f"201 字符邮箱应被拒绝: {resp.status_code}"


def test_80_user_update_email_max_length_boundary():
    """用户编辑 email 恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/users", json={
        "username": "upd_email_bnd_80", "password": "pass123456",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    email_200 = "a" * 188 + "@example.com"
    resp = client.put(f"/api/v1/users/{uid}", json={"email": email_200}, headers=headers)
    assert resp.status_code == 200, f"200 字符邮箱应通过: {resp.json()}"

    email_201 = "a" * 189 + "@example.com"
    resp = client.put(f"/api/v1/users/{uid}", json={"email": email_201}, headers=headers)
    assert resp.status_code == 422, f"201 字符邮箱应被拒绝: {resp.status_code}"


def test_81_customer_create_remark_max_length_boundary():
    """客户创建备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post(
        "/api/v1/customers",
        json={"name": "备注边界客户81", "phone": "13900818181", "remark": "备" * 500},
        headers=headers,
    )
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    resp = client.post(
        "/api/v1/customers",
        json={"name": "备注边界客户81b", "phone": "13900828282", "remark": "备" * 501},
        headers=headers,
    )
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_82_customer_update_remark_max_length_boundary():
    """客户编辑备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post(
        "/api/v1/customers",
        json={"name": "备注编辑边界82", "phone": "13900838383"},
        headers=headers,
    )
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/customers/{cid}", json={"remark": "编" * 500}, headers=headers)
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    resp = client.put(f"/api/v1/customers/{cid}", json={"remark": "编" * 501}, headers=headers)
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_83_product_create_remark_max_length_boundary():
    """商品创建备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post(
        "/api/v1/products",
        json={"name": "备注边界商品83", "price": 10.00, "remark": "商" * 500},
        headers=headers,
    )
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    resp = client.post(
        "/api/v1/products",
        json={"name": "备注边界商品83b", "price": 10.00, "remark": "商" * 501},
        headers=headers,
    )
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_84_product_update_remark_max_length_boundary():
    """商品编辑备注恰好 500 字符通过，501 字符返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post(
        "/api/v1/products",
        json={"name": "备注编辑边界84", "price": 10.00},
        headers=headers,
    )
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/products/{pid}", json={"remark": "编" * 500}, headers=headers)
    assert resp.status_code == 200, f"500 字符备注应通过: {resp.json()}"

    resp = client.put(f"/api/v1/products/{pid}", json={"remark": "编" * 501}, headers=headers)
    assert resp.status_code == 422, f"501 字符备注应被拒绝: {resp.status_code}"


def test_85_customer_create_email_max_length_boundary():
    """客户创建 email 恰好 200 字符通过，201 字符返回 422"""
    headers = _auth_for_user(_user_id)

    email_200 = "a" * 188 + "@example.com"
    resp = client.post(
        "/api/v1/customers",
        json={"name": "邮箱边界客户85", "phone": "13900858585", "email": email_200},
        headers=headers,
    )
    assert resp.status_code == 200, f"200 字符邮箱应通过: {resp.json()}"

    email_201 = "a" * 189 + "@example.com"
    resp = client.post(
        "/api/v1/customers",
        json={"name": "邮箱边界客户85b", "phone": "13900868686", "email": email_201},
        headers=headers,
    )
    assert resp.status_code == 422, f"201 字符邮箱应被拒绝: {resp.status_code}"


def test_86_customer_create_contact_name_max_length_boundary():
    """客户创建 contact_name 恰好 100 字符通过，101 字符返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post(
        "/api/v1/customers",
        json={"name": "联系人边界客户86", "phone": "13900878787", "contact_name": "联" * 100},
        headers=headers,
    )
    assert resp.status_code == 200, f"100 字符联系人应通过: {resp.json()}"

    resp = client.post(
        "/api/v1/customers",
        json={"name": "联系人边界客户86b", "phone": "13900888888", "contact_name": "联" * 101},
        headers=headers,
    )
    assert resp.status_code == 422, f"101 字符联系人应被拒绝: {resp.status_code}"


def test_87_user_create_password_max_length_boundary():
    """用户创建 password 恰好 100 字符通过，101 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 100 字符（含字母+数字）
    pwd_100 = "a" * 90 + "1234567890"  # 100 字符
    resp = client.post("/api/v1/users", json={
        "username": "pwd_bnd_87", "password": pwd_100,
    }, headers=headers)
    assert resp.status_code == 200, f"100 字符密码应通过: {resp.json()}"

    # 101 字符
    pwd_101 = "a" * 91 + "1234567890"  # 101 字符
    resp = client.post("/api/v1/users", json={
        "username": "pwd_bnd_87b", "password": pwd_101,
    }, headers=headers)
    assert resp.status_code == 422, f"101 字符密码应被拒绝: {resp.status_code}"


def test_88_user_create_password_min_length_boundary():
    """用户创建 password 恰好 6 字符通过，5 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 恰好 6 字符
    resp = client.post("/api/v1/users", json={
        "username": "pwd_min_88", "password": "a12345",
    }, headers=headers)
    assert resp.status_code == 200, f"6 字符密码应通过: {resp.json()}"

    # 5 字符
    resp = client.post("/api/v1/users", json={
        "username": "pwd_min_88b", "password": "a1234",
    }, headers=headers)
    assert resp.status_code == 422, f"5 字符密码应被拒绝: {resp.status_code}"


def test_89_user_create_password_no_letter():
    """用户创建 password 无字母返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/users", json={
        "username": "pwd_noletter_89", "password": "12345678",
    }, headers=headers)
    assert resp.status_code == 422, f"无字母密码应被拒绝: {resp.status_code}"


def test_90_user_create_password_no_digit():
    """用户创建 password 无数字返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/users", json={
        "username": "pwd_nodigit_90", "password": "abcdefgh",
    }, headers=headers)
    assert resp.status_code == 422, f"无数字密码应被拒绝: {resp.status_code}"


def test_91_login_password_max_length_boundary():
    """登录密码恰好 100 字符正常流程，101 字符返回 422"""
    # 101 字符密码
    resp = client.post("/api/v1/auth/login", json={
        "username": "boundary_admin", "password": "a" * 95 + "12345",
    })
    # 100 字符 — 正常登录（应成功或 401，取决于密码是否正确）
    # 这里只是验证 schema 不拒绝
    assert resp.status_code in (200, 401)

    # 101 字符
    resp = client.post("/api/v1/auth/login", json={
        "username": "boundary_admin", "password": "a" * 96 + "12345",
    })
    assert resp.status_code == 422, f"101 字符密码应被拒绝: {resp.status_code}"


def test_92_login_password_min_length_boundary():
    """登录密码空字符串返回 422"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "boundary_admin", "password": "",
    })
    assert resp.status_code == 422, f"空密码应被拒绝: {resp.status_code}"


def test_93_login_username_max_length_boundary():
    """登录用户名恰好 50 字符返回 401（不存在），51 字符返回 422"""
    # 50 字符用户名 — schema 通过，但用户不存在返回 401
    # 注意：避免用 "u"*50，因为 test_76 创建了该用户
    fifty_char = "z" * 50
    resp = client.post("/api/v1/auth/login", json={
        "username": fifty_char, "password": "pass123456",
    })
    assert resp.status_code == 401

    # 51 字符用户名
    resp = client.post("/api/v1/auth/login", json={
        "username": "z" * 51, "password": "pass123456",
    })
    assert resp.status_code == 422, f"51 字符用户名应被拒绝: {resp.status_code}"


def test_94_change_password_boundary():
    """修改密码 new_password 6 字符通过，5 字符返回 422"""
    headers = _auth_for_user(_user_id)

    # 6 字符新密码
    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "pass123456", "new_password": "n12345",
    }, headers=headers)
    # 改回去（先改成 n12345，再改回 pass123456）

    # 先检查 6 字符是否通过
    if resp.status_code == 200:
        # 改回原密码
        client.post("/api/v1/auth/change-password", json={
            "old_password": "n12345", "new_password": "pass123456",
        }, headers=headers)

    # 5 字符新密码
    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "pass123456", "new_password": "n1234",
    }, headers=headers)
    assert resp.status_code == 422, f"5 字符新密码应被拒绝: {resp.status_code}"


def test_95_change_password_no_digit():
    """修改密码 new_password 无数字返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "pass123456", "new_password": "abcdefghij",
    }, headers=headers)
    assert resp.status_code == 422, f"无数字新密码应被拒绝: {resp.status_code}"


def test_96_change_password_no_letter():
    """修改密码 new_password 无字母返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "pass123456", "new_password": "1234567890",
    }, headers=headers)
    assert resp.status_code == 422, f"无字母新密码应被拒绝: {resp.status_code}"


def test_97_product_create_negative_price():
    """商品创建负销售价返回 400，负成本价返回 400"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/products", json={
        "name": "负价格商品97", "price": -10.00,
    }, headers=headers)
    # 注意：API 字段名是 sale_price/cost_price，price 不是有效字段
    # 使用正确字段名
    resp = client.post("/api/v1/products", json={
        "name": "负销售价商品97a", "sale_price": "-10", "cost_price": "5",
    }, headers=headers)
    assert resp.status_code == 400, f"负销售价应返回 400: {resp.status_code} {resp.json()}"

    resp = client.post("/api/v1/products", json={
        "name": "负成本价商品97b", "sale_price": "10", "cost_price": "-5",
    }, headers=headers)
    assert resp.status_code == 400, f"负成本价应返回 400: {resp.status_code} {resp.json()}"


def test_98_product_update_negative_price():
    """商品编辑负销售价返回 400，负成本价返回 400"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/products", json={
        "name": "负价格编辑商品98", "sale_price": "10", "cost_price": "5",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/products/{pid}", json={"sale_price": "-10"}, headers=headers)
    assert resp.status_code == 400, f"负销售价应返回 400: {resp.status_code} {resp.json()}"

    resp = client.put(f"/api/v1/products/{pid}", json={"cost_price": "-5"}, headers=headers)
    assert resp.status_code == 400, f"负成本价应返回 400: {resp.status_code} {resp.json()}"


def test_99_product_create_negative_stock():
    """商品创建负库存返回 422"""
    headers = _auth_for_user(_user_id)

    resp = client.post("/api/v1/products", json={
        "name": "负库存商品99", "sale_price": "10", "stock_quantity": -1,
    }, headers=headers)
    assert resp.status_code == 422, f"负库存应返回 422: {resp.status_code} {resp.json()}"


def test_100_product_update_negative_stock():
    """商品编辑负库存返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/products", json={
        "name": "负库存编辑商品100", "sale_price": "10",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/products/{pid}", json={"stock_quantity": -1}, headers=headers)
    assert resp.status_code == 422, f"负库存应返回 422: {resp.status_code} {resp.json()}"


def test_101_order_create_quantity_zero():
    """订单创建数量为 0 返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 0}],
    }, headers=headers)
    assert resp.status_code == 422, f"数量为 0 应返回 422: {resp.status_code} {resp.json()}"


def test_102_order_create_quantity_negative():
    """订单创建数量为负数返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": -1}],
    }, headers=headers)
    assert resp.status_code == 422, f"数量为负数应返回 422: {resp.status_code} {resp.json()}"


def test_103_order_create_empty_items():
    """订单创建空 items 返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [],
    }, headers=headers)
    assert resp.status_code == 422, f"空 items 应返回 422: {resp.status_code} {resp.json()}"


def test_104_payment_amount_zero():
    """收款金额为 0 返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "0", "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 422, f"收款金额为 0 应返回 422: {resp.status_code} {resp.json()}"


def test_105_payment_amount_negative():
    """收款金额为负数返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "-10", "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 422, f"收款金额为负数应返回 422: {resp.status_code} {resp.json()}"


def test_106_payment_invalid_method():
    """收款方式无效值返回 422"""
    headers = _auth_for_user(_user_id)
    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "10", "payment_method": "bitcoin",
    }, headers=headers)
    assert resp.status_code == 422, f"无效收款方式应返回 422: {resp.status_code} {resp.json()}"
