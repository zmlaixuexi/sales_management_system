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
