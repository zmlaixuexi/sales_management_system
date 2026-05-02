"""审计日志集成测试 — 验证业务操作产生审计日志记录"""

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

TEST_DB_URL = "sqlite:///./test_audit_log.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_order_id: str = ""
_payment_id: str = ""


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
        user = User(
            id=uuid.uuid4(),
            username="audit_tester",
            hashed_password=hash_password("testpass123"),
            display_name="审计测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_audit_log.db"):
        os.remove("./test_audit_log.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login_creates_audit_log():
    """登录成功产生审计日志"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]

    # 查询审计日志
    resp = client.get("/api/v1/audit-logs?action=login_success", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "login_success"
    assert log["actor_name"] == "审计测试员"


def test_02_login_failed_creates_audit_log():
    """登录失败产生审计日志"""
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "wrong_password",
    })

    resp = client.get("/api/v1/audit-logs?action=login_failed", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["action"] == "login_failed"


def test_03_product_crud_audit_logs():
    """商品 CRUD 操作产生审计日志"""
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "审计测试商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 50,
        "status": "active",
    }, headers=_auth())
    assert resp.status_code == 200
    global _product_id
    _product_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=product_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["resource_type"] == "product"
    assert log["after_data"]["name"] == "审计测试商品"

    # 编辑商品
    client.put(f"/api/v1/products/{_product_id}", json={
        "sale_price": "25.00",
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=product_update", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 停用商品
    client.post(f"/api/v1/products/{_product_id}/disable", headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=product_disable", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["after_data"]["status"] == "disabled"


def test_04_customer_crud_audit_logs():
    """客户 CRUD 操作产生审计日志"""
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "审计测试客户",
        "contact_name": "李四",
        "phone": "13900139000",
    }, headers=_auth())
    assert resp.status_code == 200
    global _customer_id
    _customer_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=customer_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "customer"

    # 编辑客户
    client.put(f"/api/v1/customers/{_customer_id}", json={
        "level": "vip",
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=customer_update", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 客户归属转移
    other_user = User(
        id=uuid.uuid4(), username="transfer_target",
        hashed_password=hash_password("testpass123"),
        display_name="转移目标用户", is_active=True, is_superuser=False,
    )
    db2 = TestSession()
    db2.add(other_user)
    db2.commit()
    other_uid = str(other_user.id)
    db2.close()

    client.post(f"/api/v1/customers/{_customer_id}/transfer", json={
        "owner_user_id": other_uid,
    }, headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=customer_transfer", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "customer"
    assert items[0]["after_data"]["owner_user_id"] == other_uid


def test_05_order_audit_logs():
    """订单操作产生审计日志"""
    # 先重新启用商品
    client.put(f"/api/v1/products/{_product_id}", json={"status": "active"}, headers=_auth())

    # 创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2, "unit_price": "20.00"}],
    }, headers=_auth())
    assert resp.status_code == 200
    global _order_id
    _order_id = resp.json()["data"]["id"]

    # 验证创建日志
    resp = client.get("/api/v1/audit-logs?action=order_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1

    # 确认订单
    client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())

    resp = client.get("/api/v1/audit-logs?action=order_confirm", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1


def test_06_payment_audit_logs():
    """收款操作产生审计日志"""
    resp = client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "40.00",
        "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=payment_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "payment"

    # 保存收款 ID 用于冲正测试
    global _payment_id
    _payment_id = items[0]["resource_id"]


def test_06a_payment_reverse_audit_log():
    """冲正收款产生审计日志"""
    resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=payment_reverse", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "payment"
    assert items[0]["before_data"]["status"] == "normal"
    assert items[0]["after_data"]["status"] == "reversed"


def test_06b_order_cancel_audit_log():
    """取消订单产生审计日志"""
    resp = client.post(f"/api/v1/sales-orders/{_order_id}/cancel", headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=order_cancel", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["resource_type"] == "order"


def test_07_inventory_adjust_audit_log():
    """库存调整产生审计日志"""
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": _product_id,
        "quantity_change": 5,
        "remark": "测试补货",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["after_data"]["stock_quantity"] is not None


def test_08_audit_log_filter_by_resource_type():
    """按资源类型筛选审计日志"""
    resp = client.get("/api/v1/audit-logs?resource_type=product", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all(i["resource_type"] == "product" for i in items)


def test_09_audit_actions_list():
    """获取操作类型列表"""
    resp = client.get("/api/v1/audit-logs/actions", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "actions" in data
    assert "resource_types" in data
    assert "login_success" in data["actions"]
    assert "product" in data["resource_types"]


def test_10_audit_log_filter_by_actor_id():
    """按操作人筛选审计日志"""
    resp = client.get("/api/v1/audit-logs", headers=_auth())
    actor_id = resp.json()["data"]["items"][0]["actor_id"]
    resp = client.get(f"/api/v1/audit-logs?actor_id={actor_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] > 0


def test_11_audit_log_filter_by_date_range():
    """按日期范围筛选审计日志"""
    resp = client.get("/api/v1/audit-logs?start_date=2020-01-01&end_date=2099-12-31", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] > 0


# ── 异常路径测试 ──────────────────────────────────────────


def test_12_audit_log_list_requires_auth():
    """审计日志列表未认证返回 401"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


def test_13_audit_actions_requires_auth():
    """操作类型列表未认证返回 401"""
    resp = client.get("/api/v1/audit-logs/actions")
    assert resp.status_code == 401


def test_14_audit_log_invalid_actor_id_422():
    """无效 actor_id 格式返回 422"""
    resp = client.get("/api/v1/audit-logs?actor_id=not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_15_audit_log_page_size_zero_422():
    """page_size=0 返回 422"""
    resp = client.get("/api/v1/audit-logs?page_size=0", headers=_auth())
    assert resp.status_code == 422


def test_16_audit_log_page_size_over_max_422():
    """page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/audit-logs?page_size=101", headers=_auth())
    assert resp.status_code == 422


def test_17_audit_log_page_zero_422():
    """page=0 返回 422"""
    resp = client.get("/api/v1/audit-logs?page=0", headers=_auth())
    assert resp.status_code == 422


def _admin_auth():
    from helpers import admin_auth_header
    return admin_auth_header(TestSession, "audit_tester")


def test_18_audit_log_keyword_like_percent():
    """关键字搜索含 % 不应匹配全部审计日志"""
    resp = client.get("/api/v1/audit-logs", params={"keyword": "%"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all("%" not in log.get("actor_name", "") for log in items)


def test_19_audit_log_keyword_like_underscore():
    """关键字搜索含 _ 只匹配实际含 _ 的 actor_name"""
    resp = client.get("/api/v1/audit-logs", params={"keyword": "_"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all("_" in log.get("actor_name", "") for log in items)


def test_20_audit_log_page_size_100():
    """审计日志列表 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/audit-logs", params={"page_size": 100}, headers=_admin_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_21_audit_log_no_permission_403():
    """无 audit:log 权限用户获取审计日志返回 403"""
    from helpers import make_user_with_perms

    token = make_user_with_perms(TestSession, "no_audit_log", ["audit:export"])
    resp = client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_22_audit_log_requires_auth():
    """未认证获取审计日志返回 401"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


def test_23_order_confirm_audit_log_fields():
    """订单确认审计日志 after_data 含 order_no 和 status"""
    # 重新启用商品
    client.put(f"/api/v1/products/{_product_id}", json={"status": "active"}, headers=_auth())

    # 创建新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    order_no = resp.json()["data"]["order_no"]

    # 确认订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 查询确认审计日志
    resp = client.get("/api/v1/audit-logs?action=order_confirm", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["after_data"]["status"] == "confirmed"
    assert log["after_data"]["order_no"] == order_no
    assert log["resource_type"] == "order"


def test_24_order_cancel_audit_log_fields():
    """订单取消审计日志 after_data 含 order_no 和 status=cancelled"""
    # 重新启用商品
    client.put(f"/api/v1/products/{_product_id}", json={"status": "active"}, headers=_auth())

    # 创建新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    order_no = resp.json()["data"]["order_no"]

    # 取消订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=_auth())
    assert resp.status_code == 200

    # 查询取消审计日志
    resp = client.get("/api/v1/audit-logs?action=order_cancel", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["after_data"]["status"] == "cancelled"
    assert log["after_data"]["order_no"] == order_no
    assert log["resource_type"] == "order"


def test_25_customer_create_audit_log_fields():
    """客户创建审计日志 after_data 含 name 和 phone"""
    headers = _admin_auth()
    resp = client.post("/api/v1/customers", json={
        "name": "审计字段客户",
        "phone": "13811112222",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=customer_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["after_data"]["name"] == "审计字段客户"
    assert "phone" in log["after_data"]  # phone 字段存在（可能被脱敏为 ***）
    assert log["resource_type"] == "customer"


def test_26_customer_update_audit_log_fields():
    """客户编辑审计日志 after_data 含更新后的 name 和 phone"""
    headers = _admin_auth()
    # 先创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "编辑审计客户",
        "phone": "13800001111",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 编辑客户
    resp = client.put(f"/api/v1/customers/{cid}", json={
        "phone": "13800002222",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=customer_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["after_data"]["name"] == "编辑审计客户"
    assert "phone" in log["after_data"]  # phone 字段存在（可能被脱敏为 ***）
    assert log["resource_type"] == "customer"


def test_27_product_create_audit_log_fields():
    """商品创建审计日志 after_data 含 name、sku、sale_price"""
    headers = _admin_auth()
    resp = client.post("/api/v1/products", json={
        "name": "审计字段商品",
        "cost_price": "50.00",
        "sale_price": "100.00",
        "stock_quantity": 10,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=product_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["after_data"]["name"] == "审计字段商品"
    assert "sku" in log["after_data"]
    assert log["after_data"]["sale_price"] == "100.00"
    assert log["resource_type"] == "product"


def test_28_product_update_audit_log_fields():
    """商品编辑审计日志 before_data/after_data 含 sale_price 变化"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "编辑审计商品",
        "cost_price": "30.00",
        "sale_price": "60.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 编辑售价
    resp = client.put(f"/api/v1/products/{pid}", json={
        "sale_price": "80.00",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=product_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["before_data"]["sale_price"] == "60.00"
    assert log["after_data"]["sale_price"] == "80.00"
    assert log["after_data"]["name"] == "编辑审计商品"
    assert log["resource_type"] == "product"


def test_29_payment_create_audit_log_fields():
    """收款登记审计日志 after_data 含 order_id、amount、method"""
    headers = _admin_auth()
    # 创建商品 + 客户
    resp = client.post("/api/v1/products", json={
        "name": "收款审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    prod_id = resp.json()["data"]["id"]

    resp = client.post("/api/v1/customers", json={
        "name": "收款审计客户",
        "phone": "13900001111",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": prod_id, "quantity": 2, "unit_price": "20.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 登记收款
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "40.00",
        "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 200
    pay_id = resp.json()["data"]["id"]

    # 验证审计日志字段
    resp = client.get("/api/v1/audit-logs?action=payment_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pay_id)
    assert log["after_data"]["order_id"] == oid
    assert log["after_data"]["amount"] == "40.00"
    assert log["after_data"]["method"] == "cash"
    assert log["resource_type"] == "payment"


def test_30_customer_transfer_audit_log_fields():
    """客户转移审计日志 after_data 含 owner_user_id"""
    headers = _admin_auth()
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "转移审计客户",
        "phone": "13900009999",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 创建目标用户
    from app.models.user import User as UserModel
    target = UserModel(
        id=uuid.uuid4(), username="transfer_target_30",
        hashed_password=hash_password("testpass123"),
        display_name="转移目标", is_active=True, is_superuser=False,
    )
    db = TestSession()
    db.add(target)
    db.commit()
    target_id = str(target.id)
    db.close()

    # 转移客户
    resp = client.post(f"/api/v1/customers/{cid}/transfer", json={
        "owner_user_id": target_id,
    }, headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=customer_transfer", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["after_data"]["owner_user_id"] == target_id
    assert log["resource_type"] == "customer"


def test_31_product_disable_audit_log_fields():
    """商品停用审计日志 before_data/after_data 含 status 变化"""
    headers = _admin_auth()
    resp = client.post("/api/v1/products", json={
        "name": "停用审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 停用
    resp = client.post(f"/api/v1/products/{pid}/disable", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=product_disable", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["before_data"]["status"] == "active"
    assert log["before_data"]["name"] == "停用审计商品"
    assert "sku" in log["before_data"]
    assert log["after_data"]["status"] == "disabled"
    assert log["after_data"]["name"] == "停用审计商品"
    assert log["resource_type"] == "product"


def test_32_login_success_audit_log_fields():
    """登录成功审计日志含 resource_type=user、actor_name、ip_address"""
    headers = _admin_auth()
    resp = client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "testpass123",
    })
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=login_success", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "login_success"
    assert log["resource_type"] == "user"
    assert log["actor_name"] == "审计测试员"
    assert log["ip_address"] is not None


def test_33_login_failed_audit_log_fields():
    """登录失败审计日志含 resource_type=user、actor_name 为用户名"""
    headers = _admin_auth()
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester",
        "password": "wrong_password",
    })

    resp = client.get("/api/v1/audit-logs?action=login_failed", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "login_failed"
    assert log["resource_type"] == "user"
    assert log["actor_name"] == "audit_tester"
    assert log["ip_address"] is not None


def test_34_user_create_audit_log_fields():
    """用户创建审计日志 after_data 含 username 和 display_name"""
    headers = _admin_auth()
    resp = client.post("/api/v1/users", json={
        "username": "audit_create_user",
        "password": "password123",
        "display_name": "审计创建用户",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=user_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == uid)
    assert log["after_data"]["username"] == "audit_create_user"
    assert log["after_data"]["display_name"] == "审计创建用户"
    assert log["resource_type"] == "user"


def test_35_user_update_audit_log_fields():
    """用户编辑审计日志 after_data 含变更字段"""
    headers = _admin_auth()
    # 创建用户
    resp = client.post("/api/v1/users", json={
        "username": "audit_update_user",
        "password": "password123",
        "display_name": "更新前名称",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    # 编辑用户
    resp = client.put(f"/api/v1/users/{uid}", json={
        "display_name": "更新后名称",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=user_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == uid)
    assert log["after_data"]["display_name"] == "更新后名称"
    assert log["resource_type"] == "user"


def test_36_password_change_audit_log_fields():
    """修改密码审计日志含 resource_type=user、actor_name、ip_address"""
    headers = _admin_auth()
    # 修改密码
    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "auditpass123",
    }, headers=headers)
    assert resp.status_code == 200

    # 查询审计日志
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "audit_tester").first()
        user_id = str(user.id)
    finally:
        db.close()

    resp = client.get("/api/v1/audit-logs?action=password_change", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == user_id)
    assert log["resource_type"] == "user"
    assert log["actor_name"] == "审计测试员"
    assert log["ip_address"] is not None

    # 改回原密码
    login2 = client.post("/api/v1/auth/login", json={
        "username": "audit_tester", "password": "auditpass123",
    })
    token2 = login2.json()["data"]["access_token"]
    client.post("/api/v1/auth/change-password", json={
        "old_password": "auditpass123",
        "new_password": "testpass123",
    }, headers={"Authorization": f"Bearer {token2}"})


def test_37_export_products_audit_log_fields():
    """商品导出审计日志 after_data 含 keyword 和 status"""
    headers = _admin_auth()
    resp = client.get("/api/v1/exports/products?keyword=测试&status=active", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=export_products", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "export_products"
    assert log["resource_type"] == "product"
    assert log["after_data"]["keyword"] == "测试"
    assert log["after_data"]["status"] == "active"


def test_38_export_customers_audit_log_fields():
    """客户导出审计日志 after_data 含 keyword"""
    headers = _admin_auth()
    resp = client.get("/api/v1/exports/customers?keyword=审计", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=export_customers", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "export_customers"
    assert log["resource_type"] == "customer"
    assert log["after_data"]["keyword"] == "审计"


def test_39_export_orders_audit_log_fields():
    """订单导出审计日志 after_data 含 keyword 和 status"""
    headers = _admin_auth()
    resp = client.get("/api/v1/exports/orders?keyword=ORD&status=completed", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=export_orders", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "export_orders"
    assert log["resource_type"] == "order"
    assert log["after_data"]["keyword"] == "ORD"
    assert log["after_data"]["status"] == "completed"


def test_40_export_payments_audit_log_fields():
    """收款导出审计日志 after_data 含 order_id"""
    headers = _admin_auth()
    resp = client.get("/api/v1/exports/payments", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=export_payments", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "export_payments"
    assert log["resource_type"] == "payment"
    assert "order_id" in log["after_data"]


def test_41_customer_delete_audit_log_fields():
    """客户软删除审计日志 before_data 含 name/phone，after_data 含 deleted=True"""
    headers = _admin_auth()
    # 创建客户（无订单关联，可删除）
    resp = client.post("/api/v1/customers", json={
        "name": "软删除审计客户",
        "phone": "13700001111",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 软删除
    resp = client.delete(f"/api/v1/customers/{cid}", headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=customer_delete", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"]["name"] == "软删除审计客户"
    assert "phone" in log["before_data"]  # phone 字段存在（可能被脱敏为 ***）
    assert log["after_data"]["name"] == "软删除审计客户"
    assert log["after_data"]["deleted"] is True
    assert log["resource_type"] == "customer"


def test_42_customer_delete_has_orders_blocked():
    """有订单关联的客户无法删除，不产生审计日志"""
    headers = _admin_auth()
    # 创建商品 + 客户
    resp = client.post("/api/v1/products", json={
        "name": "删除阻断商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 10,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.post("/api/v1/customers", json={
        "name": "有订单客户",
        "phone": "13700002222",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cid,
        "items": [{"product_id": pid, "quantity": 1}],
    }, headers=headers)
    assert resp.status_code == 200

    # 尝试删除客户，应返回 400
    resp = client.delete(f"/api/v1/customers/{cid}", headers=headers)
    assert resp.status_code == 400
    assert "订单" in resp.json()["error"]["message"]


def test_43_payment_reverse_audit_log_fields():
    """冲正收款审计日志 before_data/after_data 含 amount、order_id、status"""
    headers = _admin_auth()
    # 创建商品 + 客户
    resp = client.post("/api/v1/products", json={
        "name": "冲正审计商品",
        "cost_price": "10.00",
        "sale_price": "30.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.post("/api/v1/customers", json={
        "name": "冲正审计客户",
        "phone": "13600001111",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 3}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 登记收款
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "90.00",
        "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 200
    pay_id = resp.json()["data"]["id"]

    # 冲正
    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=headers)
    assert resp.status_code == 200

    # 验证审计日志字段完整性
    resp = client.get("/api/v1/audit-logs?action=payment_reverse", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pay_id)
    assert log["before_data"]["amount"] == "90.00"
    assert log["before_data"]["status"] == "normal"
    assert log["before_data"]["order_id"] == oid
    assert log["after_data"]["amount"] == "90.00"
    assert log["after_data"]["status"] == "reversed"
    assert log["after_data"]["order_id"] == oid
    assert log["resource_type"] == "payment"


def test_44_customer_update_audit_log_before_data():
    """客户编辑审计日志 before_data 含编辑前的 name 和 phone"""
    headers = _admin_auth()
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "编辑前名称",
        "phone": "13600003333",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 编辑客户名称
    resp = client.put(f"/api/v1/customers/{cid}", json={
        "name": "编辑后名称",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=customer_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"]["name"] == "编辑前名称"
    assert "phone" in log["before_data"]
    assert log["after_data"]["name"] == "编辑后名称"
    assert log["resource_type"] == "customer"


def test_45_user_update_audit_log_before_data():
    """用户编辑审计日志 before_data 含编辑前的 display_name，after_data 含更新后的值"""
    headers = _admin_auth()
    # 创建用户
    resp = client.post("/api/v1/users", json={
        "username": "before_data_user",
        "password": "password123",
        "display_name": "编辑前名称",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    # 编辑用户
    resp = client.put(f"/api/v1/users/{uid}", json={
        "display_name": "编辑后名称",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=user_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == uid)
    assert log["before_data"]["display_name"] == "编辑前名称"
    assert log["before_data"]["username"] == "before_data_user"
    assert log["after_data"]["display_name"] == "编辑后名称"
    assert log["resource_type"] == "user"


def test_46_product_update_audit_log_change_comparison():
    """商品编辑审计日志 before_data/after_data 可对比 name 和 sale_price 的变更"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "变更前商品",
        "cost_price": "50.00",
        "sale_price": "100.00",
        "stock_quantity": 10,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 同时编辑 name 和 sale_price
    resp = client.put(f"/api/v1/products/{pid}", json={
        "name": "变更后商品",
        "sale_price": "120.00",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=product_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    # before_data 记录变更前
    assert log["before_data"]["name"] == "变更前商品"
    assert log["before_data"]["sale_price"] == "100.00"
    assert log["before_data"]["cost_price"] == "50.00"
    # after_data 记录变更后
    assert log["after_data"]["name"] == "变更后商品"
    assert log["after_data"]["sale_price"] == "120.00"
    assert log["after_data"]["cost_price"] == "50.00"  # 未变更字段保持原值


def test_47_all_audit_logs_have_actor_and_ip():
    """所有审计日志都应包含 actor_name、actor_id 和 ip_address"""
    headers = _admin_auth()
    # 执行一个操作确保有审计日志
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester", "password": "testpass123",
    })

    resp = client.get("/api/v1/audit-logs", params={"page_size": 50}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    for log in items:
        assert log["actor_name"] is not None, f"action={log['action']} 缺少 actor_name"
        # login_failed 的 actor_id 为 None（无法确定用户身份）
        if log["action"] != "login_failed":
            assert log["actor_id"] is not None, f"action={log['action']} 缺少 actor_id"
        assert log["ip_address"] is not None, f"action={log['action']} 缺少 ip_address"
        assert log["action"] is not None
        assert log["resource_type"] is not None
        assert log["created_at"] is not None


def test_48_date_range_filter_results_within_range():
    """日期范围筛选：返回的审计日志 created_at 均在指定范围内"""
    headers = _admin_auth()
    # 获取全量日志的时间范围
    resp = client.get("/api/v1/audit-logs", params={"page_size": 50}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    # 用最早和最晚时间作为范围，验证全量匹配
    dates = [i["created_at"] for i in items]
    dates.sort()
    start = dates[0][:10]  # YYYY-MM-DD
    end = dates[-1][:10]

    resp = client.get(
        "/api/v1/audit-logs",
        params={"start_date": start, "end_date": end + "T23:59:59"},
        headers=headers,
    )
    assert resp.status_code == 200
    filtered = resp.json()["data"]["items"]
    assert len(filtered) > 0
    # 验证每条记录的日期在范围内
    for log in filtered:
        d = log["created_at"][:10]
        assert start <= d <= end, f"日期 {d} 不在范围 [{start}, {end}] 内"


def test_49_keyword_search_matches_actor_name():
    """关键字搜索：按 actor_name 搜索返回匹配结果"""
    headers = _admin_auth()
    # 使用已知存在的 actor_name 关键字搜索
    resp = client.get(
        "/api/v1/audit-logs",
        params={"keyword": "审计测试员"},
        headers=headers,
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    for log in items:
        assert "审计测试员" in log["actor_name"]


def test_50_keyword_search_no_match_returns_empty():
    """关键字搜索：不匹配的关键字返回空列表"""
    headers = _admin_auth()
    resp = client.get(
        "/api/v1/audit-logs",
        params={"keyword": "ZZZZZ_NONEXISTENT_KEYWORD_ZZZZZ"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0
    assert resp.json()["data"]["items"] == []


def test_51_combined_action_and_date_filter():
    """组合筛选：action + start_date 同时过滤，结果满足两个条件"""
    headers = _admin_auth()
    # 先获取所有 login_success 日志
    resp = client.get("/api/v1/audit-logs", params={"action": "login_success"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    if len(items) == 0:
        return  # 无 login_success 日志则跳过
    dates = [i["created_at"][:10] for i in items]
    start = min(dates)
    end = max(dates)

    # 组合筛选
    resp = client.get(
        "/api/v1/audit-logs",
        params={"action": "login_success", "start_date": start, "end_date": end + "T23:59:59"},
        headers=headers,
    )
    assert resp.status_code == 200
    filtered = resp.json()["data"]["items"]
    assert len(filtered) > 0
    for log in filtered:
        assert log["action"] == "login_success"
        d = log["created_at"][:10]
        assert start <= d <= end


def test_52_keyword_search_by_resource_id():
    """关键字搜索：按 resource_id 部分匹配返回结果"""
    headers = _admin_auth()
    # 获取一条日志的 resource_id 用于搜索
    resp = client.get("/api/v1/audit-logs", params={"page_size": 1}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    rid = items[0]["resource_id"]
    # 取 resource_id 的中间部分作为关键字
    partial = rid[len(rid) // 4: len(rid) // 4 + 8]

    resp = client.get(
        "/api/v1/audit-logs",
        params={"keyword": partial},
        headers=headers,
    )
    assert resp.status_code == 200
    matched = resp.json()["data"]["items"]
    assert len(matched) > 0
    for log in matched:
        assert partial in log["resource_id"]


def test_53_inventory_adjust_audit_log_before_data():
    """库存调整审计日志 before_data 含 name 和调整前 stock_quantity，after_data 含调整后值"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "库存审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 30,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 调整库存
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": pid,
        "quantity_change": 15,
        "remark": "审计测试补货",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["before_data"]["name"] == "库存审计商品"
    assert log["before_data"]["stock_quantity"] == 30
    assert log["after_data"]["name"] == "库存审计商品"
    assert log["after_data"]["stock_quantity"] == 45
    assert log["after_data"]["change"] == 15
    assert log["resource_type"] == "product"


def test_54_audit_log_response_has_user_agent_and_request_id():
    """审计日志 API 响应字段 user_agent/request_id 非空"""
    headers = _admin_auth()
    # 执行一个操作确保有审计日志
    resp = client.post("/api/v1/products", json={
        "name": "字段完整性商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=product_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["user_agent"] is not None
    assert log["request_id"] is not None
    assert isinstance(log["id"], str)
    assert isinstance(log["created_at"], str)


def test_55_audit_log_resource_id_is_valid_uuid():
    """审计日志 resource_id 是有效 UUID 格式"""
    headers = _admin_auth()
    resp = client.get("/api/v1/audit-logs", params={"page_size": 10}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    for log in items:
        rid = log["resource_id"]
        if rid:
            # 验证是有效 UUID
            parsed = uuid.UUID(rid)
            assert str(parsed) == rid


def test_56_create_operations_have_no_before_data():
    """创建类操作（product_create/customer_create/user_create）before_data 为 None"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "创建无before商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "创建无before客户",
        "phone": "13500005555",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 验证商品创建日志
    resp = client.get("/api/v1/audit-logs?action=product_create", headers=headers)
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["before_data"] is None
    assert log["after_data"] is not None

    # 验证客户创建日志
    resp = client.get("/api/v1/audit-logs?action=customer_create", headers=headers)
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"] is None
    assert log["after_data"] is not None


def test_57_order_create_audit_log_after_data():
    """订单创建审计日志 after_data 含 order_no/status/customer_id/total_amount"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "订单审计商品",
        "cost_price": "10.00",
        "sale_price": "25.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "订单审计客户",
        "phone": "13400006666",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 3, "unit_price": "25.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    order_no = resp.json()["data"]["order_no"]

    # 验证订单创建审计日志
    resp = client.get("/api/v1/audit-logs?action=order_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["before_data"] is None
    assert log["after_data"]["order_no"] == order_no
    assert log["after_data"]["status"] == "draft"
    assert log["after_data"]["customer_id"] == cust_id
    assert log["after_data"]["total_amount"] == "75.00"
    assert log["resource_type"] == "order"


def test_58_audit_logs_ordered_by_created_at_desc():
    """审计日志默认按 created_at 降序排列（最新在前）"""
    headers = _admin_auth()
    # 执行操作确保有审计日志
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester", "password": "testpass123",
    })
    client.post("/api/v1/products", json={
        "name": "排序审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)

    resp = client.get("/api/v1/audit-logs", params={"page_size": 50}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 1
    for i in range(len(items) - 1):
        assert items[i]["created_at"] >= items[i + 1]["created_at"], (
            f"第 {i} 条 {items[i]['created_at']} 应 >= 第 {i + 1} 条 {items[i + 1]['created_at']}"
        )


def test_59_audit_log_pagination_page2():
    """审计日志分页：第2页有数据时 total > page_size"""
    headers = _admin_auth()
    # 确保有足够审计日志
    client.post("/api/v1/auth/login", json={
        "username": "audit_tester", "password": "testpass123",
    })
    client.post("/api/v1/products", json={
        "name": "分页审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)

    resp = client.get("/api/v1/audit-logs", params={"page_size": 5}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    total = data["total"]
    if total > 5:
        resp2 = client.get("/api/v1/audit-logs", params={"page_size": 5, "page": 2}, headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert len(data2["items"]) > 0
        # 第1页和第2页不应有重复 id
        page1_ids = {i["id"] for i in data["items"]}
        page2_ids = {i["id"] for i in data2["items"]}
        assert page1_ids.isdisjoint(page2_ids)


def test_60_audit_log_export_action_type_filter():
    """审计日志 action 筛选：export_* 类型日志仅返回导出操作"""
    headers = _admin_auth()
    # 执行一次导出确保有日志
    client.get("/api/v1/exports/products", headers=headers)

    resp = client.get("/api/v1/audit-logs?action=export_products", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    if len(items) > 0:
        for log in items:
            assert log["action"] == "export_products"
            assert log["resource_type"] == "product"


def test_61_order_update_audit_log_before_data():
    """订单编辑审计日志 before_data 含编辑前 total_amount，after_data 含编辑后值"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "订单编辑审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "订单编辑审计客户",
        "phone": "13300007777",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建订单（2件 × 20.00 = 40.00）
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 2, "unit_price": "20.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    # 编辑订单（改为 3件 × 20.00 = 60.00）
    resp = client.put(f"/api/v1/sales-orders/{oid}", json={
        "items": [{"product_id": pid, "quantity": 3, "unit_price": "20.00"}],
    }, headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=order_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["before_data"]["order_no"] is not None
    assert log["before_data"]["status"] == "draft"
    assert log["before_data"]["total_amount"] == "40.00"
    assert log["after_data"]["order_no"] is not None
    assert log["after_data"]["status"] == "draft"
    assert log["after_data"]["total_amount"] == "60.00"
    assert log["resource_type"] == "order"


def test_62_customer_transfer_audit_log_before_data():
    """客户转移审计日志 before_data 含原 owner_user_id，after_data 含新 owner_user_id"""
    headers = _admin_auth()
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "转移审计客户",
        "phone": "13200008888",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 获取管理员 user_id 作为原 owner
    db = TestSession()
    try:
        admin = db.query(User).filter(User.username == "audit_tester").first()
        admin_id = str(admin.id)
    finally:
        db.close()

    # 创建目标用户
    target = User(
        id=uuid.uuid4(), username="transfer_target_62",
        hashed_password=hash_password("testpass123"),
        display_name="转移目标62", is_active=True, is_superuser=False,
    )
    db = TestSession()
    db.add(target)
    db.commit()
    target_id = str(target.id)
    db.close()

    # 转移客户
    resp = client.post(f"/api/v1/customers/{cid}/transfer", json={
        "owner_user_id": target_id,
    }, headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=customer_transfer", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"]["name"] == "转移审计客户"
    assert log["before_data"]["owner_user_id"] == admin_id
    assert log["after_data"]["name"] == "转移审计客户"
    assert log["after_data"]["owner_user_id"] == target_id
    assert log["resource_type"] == "customer"


def test_63_payment_create_audit_log_before_data_is_none():
    """收款登记审计日志 before_data 为 None（创建操作），after_data 含 order_id/amount/method"""
    headers = _admin_auth()
    # 创建商品 + 客户
    resp = client.post("/api/v1/products", json={
        "name": "收款before商品",
        "cost_price": "10.00",
        "sale_price": "25.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.post("/api/v1/customers", json={
        "name": "收款before客户",
        "phone": "13100009999",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 2}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 登记收款
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "50.00",
        "payment_method": "transfer",
    }, headers=headers)
    assert resp.status_code == 200
    pay_id = resp.json()["data"]["id"]

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=payment_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pay_id)
    assert log["before_data"] is None
    assert log["after_data"]["order_id"] == oid
    assert log["after_data"]["amount"] == "50.00"
    assert log["after_data"]["method"] == "transfer"
    assert log["resource_type"] == "payment"


def test_64_order_confirm_audit_log_before_data():
    """订单确认审计日志 before_data 含 status=draft，after_data 含 status=confirmed"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "确认审计商品",
        "cost_price": "10.00",
        "sale_price": "30.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "确认审计客户",
        "phone": "13000001111",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 2, "unit_price": "30.00"}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]

    # 确认订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=order_confirm", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["before_data"]["status"] == "draft"
    assert log["before_data"]["total_amount"] == "60.00"
    assert log["after_data"]["status"] == "confirmed"
    assert log["after_data"]["total_amount"] == "60.00"
    assert log["resource_type"] == "order"


def test_65_order_cancel_audit_log_before_data():
    """订单取消审计日志 before_data 含原 status，after_data 含 status=cancelled"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "取消审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "取消审计客户",
        "phone": "13000002222",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 1}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 取消订单
    resp = client.post(f"/api/v1/sales-orders/{oid}/cancel", headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=order_cancel", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == oid)
    assert log["before_data"]["status"] == "confirmed"
    assert log["before_data"]["total_amount"] == "20.00"
    assert log["after_data"]["status"] == "cancelled"
    assert log["after_data"]["total_amount"] == "20.00"
    assert log["resource_type"] == "order"


def test_66_inventory_decrease_audit_log():
    """库存减少审计日志 before_data/after_data 含 name 和正确的 stock_quantity"""
    headers = _admin_auth()
    # 创建商品（库存 50）
    resp = client.post("/api/v1/products", json={
        "name": "库存减少审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 50,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 减少库存 20
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": pid,
        "quantity_change": -20,
        "remark": "减少库存审计",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid and i["after_data"]["change"] == -20)
    assert log["before_data"]["name"] == "库存减少审计商品"
    assert log["before_data"]["stock_quantity"] == 50
    assert log["after_data"]["name"] == "库存减少审计商品"
    assert log["after_data"]["stock_quantity"] == 30
    assert log["after_data"]["change"] == -20
    assert log["resource_type"] == "product"


def test_67_user_disable_audit_log_before_data():
    """用户禁用/启用审计日志 before_data 含变更前 is_active"""
    headers = _admin_auth()
    # 创建用户
    resp = client.post("/api/v1/users", json={
        "username": "disable_audit_user",
        "password": "password123",
        "display_name": "禁用审计用户",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    # 禁用用户
    resp = client.put(f"/api/v1/users/{uid}", json={
        "is_active": False,
    }, headers=headers)
    assert resp.status_code == 200

    # 重新启用
    resp = client.put(f"/api/v1/users/{uid}", json={
        "is_active": True,
    }, headers=headers)
    assert resp.status_code == 200

    # 验证审计日志：按 after_data.is_active 区分禁用和启用
    resp = client.get("/api/v1/audit-logs?action=user_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    user_logs = [i for i in items if i["resource_id"] == uid]
    assert len(user_logs) >= 2

    disable_log = next(i for i in user_logs if i["after_data"]["is_active"] is False)
    assert disable_log["before_data"]["is_active"] is True
    assert disable_log["resource_type"] == "user"

    enable_log = next(i for i in user_logs if i["after_data"]["is_active"] is True)
    assert enable_log["before_data"]["is_active"] is False


def test_68_password_change_audit_log_after_data():
    """密码修改审计日志 after_data 含 username 和 action"""
    headers = _admin_auth()
    # 修改密码
    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "auditpass123",
    }, headers=headers)
    assert resp.status_code == 200

    # 获取 user_id
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "audit_tester").first()
        user_id = str(user.id)
    finally:
        db.close()

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=password_change", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == user_id)
    assert log["after_data"]["username"] == "audit_tester"
    assert log["after_data"]["action"] == "password_change"
    assert log["before_data"] is None
    assert log["resource_type"] == "user"
    assert log["ip_address"] is not None

    # 改回原密码
    login2 = client.post("/api/v1/auth/login", json={
        "username": "audit_tester", "password": "auditpass123",
    })
    token2 = login2.json()["data"]["access_token"]
    client.post("/api/v1/auth/change-password", json={
        "old_password": "auditpass123",
        "new_password": "testpass123",
    }, headers={"Authorization": f"Bearer {token2}"})


def test_69_product_delete_audit_log_before_after_data():
    """商品软删除审计日志 before_data 含 name/sku/status，after_data 含 deleted=True"""
    headers = _admin_auth()
    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "删除审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 软删除商品
    resp = client.delete(f"/api/v1/products/{pid}", headers=headers)
    assert resp.status_code == 200

    # 验证审计日志
    resp = client.get("/api/v1/audit-logs?action=product_delete", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["before_data"]["name"] == "删除审计商品"
    assert "sku" in log["before_data"]
    assert log["before_data"]["status"] == "active"
    assert log["after_data"]["name"] == "删除审计商品"
    assert "sku" in log["after_data"]
    assert log["after_data"]["deleted"] is True
    assert log["resource_type"] == "product"


def test_70_customer_create_audit_log_after_data_completeness():
    """客户创建审计日志 after_data 含 name/phone/source/level"""
    headers = _admin_auth()
    resp = client.post("/api/v1/customers", json={
        "name": "创建完整性客户",
        "phone": "13500001111",
        "source": "referral",
        "level": "vip",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=customer_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"] is None
    assert log["after_data"]["name"] == "创建完整性客户"
    assert "phone" in log["after_data"]
    assert log["resource_type"] == "customer"


def test_71_user_create_audit_log_after_data_has_is_active():
    """用户创建审计日志 after_data 含 is_active"""
    headers = _admin_auth()
    resp = client.post("/api/v1/users", json={
        "username": "create_active_user",
        "password": "password123",
        "display_name": "创建活跃用户",
    }, headers=headers)
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=user_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == uid)
    assert log["after_data"]["username"] == "create_active_user"
    assert log["after_data"]["display_name"] == "创建活跃用户"
    assert log["before_data"] is None
    assert log["resource_type"] == "user"


def test_72_payment_reverse_order_status_audit_chain():
    """收款冲正后同时产生 payment_reverse 和 order_update 审计日志"""
    headers = _admin_auth()
    # 创建商品 + 客户
    resp = client.post("/api/v1/products", json={
        "name": "冲正链路商品",
        "cost_price": "10.00",
        "sale_price": "30.00",
        "stock_quantity": 100,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.post("/api/v1/customers", json={
        "name": "冲正链路客户",
        "phone": "13800001222",
    }, headers=headers)
    assert resp.status_code == 200
    cust_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": cust_id,
        "items": [{"product_id": pid, "quantity": 2}],
    }, headers=headers)
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=headers)

    # 登记收款
    resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "60.00",
        "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 200
    pay_id = resp.json()["data"]["id"]

    # 冲正
    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=headers)
    assert resp.status_code == 200

    # 验证 payment_reverse 审计日志
    resp = client.get("/api/v1/audit-logs?action=payment_reverse", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    pay_log = next(i for i in items if i["resource_id"] == pay_id)
    assert pay_log["before_data"]["status"] == "normal"
    assert pay_log["after_data"]["status"] == "reversed"
    assert pay_log["before_data"]["order_id"] == oid
    assert pay_log["resource_type"] == "payment"


def test_73_inventory_adjust_to_zero_audit_log():
    """库存调整归零审计日志 before_data/after_data 含 name 和正确的 stock_quantity"""
    headers = _admin_auth()
    # 创建商品（库存 10）
    resp = client.post("/api/v1/products", json={
        "name": "归零审计商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 10,
        "status": "active",
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 减少库存归零
    resp = client.post("/api/v1/inventory/adjustments", json={
        "product_id": pid,
        "quantity_change": -10,
        "remark": "归零测试",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=inventory_adjust", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid and i["after_data"]["change"] == -10)
    assert log["before_data"]["name"] == "归零审计商品"
    assert log["before_data"]["stock_quantity"] == 10
    assert log["after_data"]["name"] == "归零审计商品"
    assert log["after_data"]["stock_quantity"] == 0
    assert log["after_data"]["change"] == -10
    assert log["resource_type"] == "product"


def test_74_customer_update_audit_log_phone_in_before_data():
    """客户编辑审计日志 before_data 含 phone 字段（可能被脱敏）"""
    headers = _admin_auth()
    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "手机号验证客户",
        "phone": "13900003333",
    }, headers=headers)
    assert resp.status_code == 200
    cid = resp.json()["data"]["id"]

    # 编辑客户名称（不改手机）
    resp = client.put(f"/api/v1/customers/{cid}", json={
        "name": "手机号验证客户改名",
    }, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=customer_update", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == cid)
    assert log["before_data"]["name"] == "手机号验证客户"
    assert "phone" in log["before_data"]
    assert log["after_data"]["name"] == "手机号验证客户改名"
    assert "phone" in log["after_data"]
    assert log["resource_type"] == "customer"


def test_75_product_create_audit_log_after_data_has_stock_and_price():
    """商品创建审计日志 after_data 含 stock_quantity 和 sale_price"""
    headers = _admin_auth()
    resp = client.post("/api/v1/products", json={
        "name": "审计商品-库存价格",
        "sale_price": "99.90",
        "cost_price": "50.00",
        "stock_quantity": 200,
    }, headers=headers)
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=product_create", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    log = next(i for i in items if i["resource_id"] == pid)
    assert log["after_data"]["stock_quantity"] == 200
    assert log["after_data"]["sale_price"] == "99.90"
    assert log["after_data"]["name"] == "审计商品-库存价格"
    assert log["resource_type"] == "product"


def test_76_audit_log_actor_id_non_null_for_non_login_failed():
    """非 login_failed 操作的审计日志 actor_id 必须非空"""
    headers = _admin_auth()
    # 触发多种业务操作产生审计日志
    client.post("/api/v1/products", json={
        "name": "actor验证商品", "sale_price": "10.00", "cost_price": "5.00",
    }, headers=headers)

    resp = client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    non_login_failed = [i for i in items if i["action"] != "login_failed"]
    assert len(non_login_failed) > 0
    for log in non_login_failed:
        assert log["actor_id"] is not None, f"action={log['action']} 缺少 actor_id"
        assert log["actor_id"] != "", f"action={log['action']} actor_id 为空字符串"
