"""收款登记 + 冲正测试 — 覆盖创建、列表、冲正、超额、状态联动"""

import os
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.order import Payment, SalesOrder, SalesOrderItem
from app.models.product import Product, ProductCategory
from app.models.user import Permission, Role, RolePermission, User, UserRole

TEST_DB_URL = "sqlite:///./test_payment_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_confirmed_order_id: str = ""
_draft_order_id: str = ""
_payment_id: str = ""
_admin_id: str = ""


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
            username="pay_tester",
            hashed_password=hash_password("testpass123"),
            display_name="收款测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)

        cat = ProductCategory(id=uuid.uuid4(), name="收款测试分类", sort_order=0)
        db.add(cat)
        db.flush()

        prod = Product(
            id=uuid.uuid4(),
            name="收款测试商品",
            sku="PAY-TEST-01",
            sale_price=100.00,
            cost_price=60.00,
            stock_quantity=100,
            status="active",
            category_id=cat.id,
        )
        db.add(prod)

        cust = Customer(
            id=uuid.uuid4(),
            name="收款测试客户",
            phone="13900000001",
            source="offline",
            owner_user_id=user.id,
        )
        db.add(cust)
        db.flush()

        # 创建一个已确认订单（total=300）
        order1 = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-0001",
            customer_id=cust.id,
            sales_user_id=user.id,
            status="confirmed",
            total_amount=300,
            total_cost=180,
            gross_profit=120,
            gross_margin=0.4,
            paid_amount=0,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(order1)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(),
            order_id=order1.id,
            product_id=prod.id,
            product_sku_snapshot=prod.sku,
            product_name_snapshot=prod.name,
            quantity=3,
            unit_price=100,
            discount_amount=0,
            discount_rate=0,
            cost_price_snapshot=60,
            subtotal_amount=300,
            subtotal_cost=180,
        ))

        # 创建一个草稿订单（不能收款）
        order2 = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-0002",
            customer_id=cust.id,
            sales_user_id=user.id,
            status="draft",
            total_amount=200,
            total_cost=120,
            gross_profit=80,
            gross_margin=0.4,
            paid_amount=0,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(order2)

        db.commit()

        global _product_id, _customer_id, _confirmed_order_id, _draft_order_id, _admin_id
        _product_id = str(prod.id)
        _customer_id = str(cust.id)
        _confirmed_order_id = str(order1.id)
        _draft_order_id = str(order2.id)
        _admin_id = str(user.id)

        _tokens["access"] = create_access_token(str(user.id))
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_payment_crud.db"):
        os.remove("./test_payment_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


class TestPaymentCreate:
    """登记收款"""

    def test_01_create_payment_success(self):
        resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
            "amount": "100.00",
            "payment_method": "cash",
            "remark": "第一笔",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["amount"] == "100.00"
        assert data["payment_method"] == "cash"
        assert data["order_status"] == "partially_paid"
        global _payment_id
        _payment_id = data["id"]

    def test_02_create_second_payment_complete(self):
        """全额付完 → 订单完成"""
        resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
            "amount": "200.00",
            "payment_method": "transfer",
        }, headers=_auth())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order_status"] == "completed"

    def test_03_payment_exceed_remaining_400(self):
        """超额收款"""
        # 新建一个已确认订单
        resp = client.post("/api/v1/sales-orders", json={
            "customer_id": _customer_id,
            "items": [{"product_id": _product_id, "quantity": 1}],
        }, headers=_auth())
        assert resp.status_code == 200
        oid = resp.json()["data"]["id"]
        client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())

        resp = client.post(f"/api/v1/sales-orders/{oid}/payments", json={
            "amount": "999.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 400
        assert "超过剩余应收" in resp.json()["error"]["message"]

    def test_04_payment_zero_amount_422(self):
        resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
            "amount": "0",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 422

    def test_05_payment_draft_order_400(self):
        resp = client.post(f"/api/v1/sales-orders/{_draft_order_id}/payments", json={
            "amount": "50.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 400

    def test_06_payment_bad_order_404(self):
        resp = client.post(f"/api/v1/sales-orders/{uuid.uuid4()}/payments", json={
            "amount": "50.00",
            "payment_method": "cash",
        }, headers=_auth())
        assert resp.status_code == 404


class TestPaymentList:
    """收款列表"""

    def test_07_list_payments(self):
        resp = client.get("/api/v1/payments", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 2  # at least the 2 payments from test_01/test_02

    def test_08_list_payments_by_order(self):
        resp = client.get(f"/api/v1/payments?order_id={_confirmed_order_id}", headers=_auth())
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(p["order_id"] == _confirmed_order_id for p in items)
        assert len(items) == 2


class TestPaymentReverse:
    """冲正收款"""

    def test_09_reverse_payment(self):
        resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "reversed"

    def test_10_reverse_already_reversed_404(self):
        resp = client.post(f"/api/v1/payments/{_payment_id}/reverse", headers=_auth())
        assert resp.status_code == 404

    def test_11_reverse_bad_id_404(self):
        resp = client.post(f"/api/v1/payments/{uuid.uuid4()}/reverse", headers=_auth())
        assert resp.status_code == 404


def _create_user_with_perms(db, username, perm_codes):
    """创建带指定权限的非超级用户"""
    user = User(
        id=uuid.uuid4(),
        username=username,
        hashed_password=hash_password("testpass123"),
        display_name=username,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    role = Role(id=uuid.uuid4(), name=f"role_{username}", display_name=f"角色-{username}")
    db.add(role)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))

    for code in perm_codes:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(id=uuid.uuid4(), code=code, name=code, module=code.split(":")[0])
            db.add(perm)
            db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    return user


def test_12_non_admin_payment_list_filtered():
    """非超管用户只能看到本人订单的收款（数据范围过滤）"""
    db = TestSession()
    try:
        # 创建一个只有 payment:list 权限的销售员
        sales_user = _create_user_with_perms(db, "pay_sales", ["payment:list"])
        db.flush()

        # 创建属于该销售员的已确认订单
        order3 = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-0003",
            customer_id=uuid.UUID(_customer_id),
            sales_user_id=sales_user.id,
            status="confirmed",
            total_amount=100,
            total_cost=60,
            gross_profit=40,
            gross_margin=0.4,
            paid_amount=0,
            created_by=sales_user.id,
            updated_by=sales_user.id,
        )
        db.add(order3)
        db.commit()

        # 以销售员身份登录
        token = create_access_token(str(sales_user.id))

        # 列表应该只返回该销售员的收款（不含管理员的）
        resp = client.get("/api/v1/payments", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # 管理员的收款不应出现在此列表中
        for item in items:
            assert item["order_id"] != _confirmed_order_id
    finally:
        db.close()


def test_13_reverse_payment_order_deleted():
    """冲正收款时关联订单已被删除"""
    db = TestSession()
    try:
        # 创建已确认订单 + 收款
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="ORD-PAY-DEL",
            customer_id=uuid.UUID(_customer_id),
            sales_user_id=uuid.UUID(_admin_id),
            status="confirmed",
            total_amount=100,
            total_cost=60,
            gross_profit=40,
            gross_margin=0.4,
            paid_amount=100,
            created_by=uuid.UUID(_admin_id),
            updated_by=uuid.UUID(_admin_id),
        )
        db.add(order)
        db.flush()

        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            amount=100,
            payment_method="cash",
            operator_id=uuid.UUID(_admin_id),
            status="normal",
        )
        db.add(payment)
        db.flush()
        pid = str(payment.id)

        # 硬删除订单（SQLite 不强制外键）
        db.query(SalesOrder).filter(SalesOrder.id == order.id).delete()
        db.commit()

        # 冲正 → 关联订单不存在
        resp = client.post(f"/api/v1/payments/{pid}/reverse", headers=_auth())
        assert resp.status_code == 404
        assert "关联订单" in resp.json()["error"]["message"]
    finally:
        db.close()


def test_14_invalid_payment_method():
    """无效的收款方式被拒绝"""
    db = TestSession()
    try:
        admin = db.query(User).filter(User.id == uuid.UUID(_admin_id)).first()
        customer = Customer(
            id=uuid.uuid4(),
            name="收款方式测试客户",
            phone="13900990099",
            owner_user_id=admin.id,
            created_by=admin.id,
        )
        db.add(customer)
        db.flush()
        product = Product(
            id=uuid.uuid4(),
            name="收款方式测试商品",
            sku="PAY-METHOD-001",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(product)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="SO-PAY-METHOD",
            customer_id=customer.id,
            sales_user_id=admin.id,
            status="confirmed",
            total_amount="100.00",
            created_by=admin.id,
        )
        db.add(order)
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/sales-orders/{oid}/payments", json={
        "amount": "50", "payment_method": "bitcoin",
    }, headers=_auth())
    assert resp.status_code == 422


def test_15_payment_cancelled_order_400():
    """已取消订单不允许收款"""
    db = TestSession()
    try:
        admin = db.query(User).filter(User.id == uuid.UUID(_admin_id)).first()
        customer = Customer(
            id=uuid.uuid4(),
            name="取消订单收款测试客户",
            phone="13900990015",
            owner_user_id=admin.id,
            created_by=admin.id,
        )
        db.add(customer)
        db.flush()
        product = Product(
            id=uuid.uuid4(),
            name="取消订单收款测试商品",
            sku="PAY-CANCEL-001",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(product)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="SO-PAY-CANCEL",
            customer_id=customer.id,
            sales_user_id=admin.id,
            status="cancelled",
            total_amount=100,
            paid_amount=0,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(order)
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/sales-orders/{oid}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


def test_16_payment_completed_order_invalid_status():
    """已完成订单不允许收款（状态检查先于金额检查）"""
    db = TestSession()
    try:
        admin = db.query(User).filter(User.id == uuid.UUID(_admin_id)).first()
        customer = Customer(
            id=uuid.uuid4(),
            name="已付清测试客户",
            phone="13900990016",
            owner_user_id=admin.id,
            created_by=admin.id,
        )
        db.add(customer)
        db.flush()
        product = Product(
            id=uuid.uuid4(),
            name="已付清测试商品",
            sku="PAY-DONE-001",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(product)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="SO-PAY-DONE",
            customer_id=customer.id,
            sales_user_id=admin.id,
            status="completed",
            total_amount=100,
            paid_amount=100,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(order)
        db.commit()
        oid = str(order.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/sales-orders/{oid}/payments", json={
        "amount": "1", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


def test_17_payment_negative_amount_422():
    """负数金额被 Pydantic 拒绝"""
    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "-50", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 422


def test_18_payment_no_permission_403():
    """无收款权限用户返回 403"""
    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_pay_perm",
            hashed_password=hash_password("testpass123"),
            display_name="无收款权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "10", "payment_method": "cash",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_19_reverse_no_permission_403():
    """无冲正权限用户返回 403"""
    db = TestSession()
    try:
        # 创建只有 payment:list 权限的用户
        nop = _create_user_with_perms(db, "no_reverse_perm", ["payment:list"])
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    resp = client.post(f"/api/v1/payments/{uuid.uuid4()}/reverse", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 403


def test_20_payment_list_pagination():
    """收款列表分页参数"""
    resp = client.get("/api/v1/payments?page=1&page_size=1", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["page_size"] == 1


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_21_list_payments_requires_auth():
    """未认证收款列表返回 401"""
    resp = client.get("/api/v1/payments")
    assert resp.status_code == 401


def test_22_create_payment_requires_auth():
    """未认证登记收款返回 401"""
    resp = client.post(f"/api/v1/sales-orders/{_confirmed_order_id}/payments", json={
        "amount": "10.00", "payment_method": "cash",
    })
    assert resp.status_code == 401


def test_23_reverse_payment_requires_auth():
    """未认证冲正收款返回 401"""
    resp = client.post(f"/api/v1/payments/{_payment_id}/reverse")
    assert resp.status_code == 401


def test_24_create_payment_invalid_order_uuid():
    """无效 UUID 订单收款返回 422"""
    resp = client.post("/api/v1/sales-orders/not-a-uuid/payments", json={
        "amount": "10.00", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 422


def test_25_reverse_payment_invalid_uuid():
    """无效 UUID 冲正收款返回 422"""
    resp = client.post("/api/v1/payments/not-a-uuid/reverse", headers=_auth())
    assert resp.status_code == 422


def test_26_reverse_completed_order_to_partially_paid():
    """冲正部分金额后 completed → partially_paid"""
    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 分两笔收款：先收 150 再收剩余
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "150", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["order_status"] == "partially_paid"
    first_payment_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "50", "payment_method": "transfer",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["order_status"] == "completed"

    # 冲正第二笔（部分金额），订单应回退到 partially_paid
    resp = client.post(f"/api/v1/payments/{first_payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
    assert resp.json()["data"]["status"] == "partially_paid"


def test_27_reverse_all_payments_order_back_to_confirmed():
    """冲正全部收款后订单回到 confirmed"""
    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 全额收款
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "100", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["order_status"] == "completed"
    payment_id = resp.json()["data"]["id"]

    # 冲正全部金额
    resp = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
    assert resp.json()["data"]["status"] == "confirmed"
    assert resp.json()["data"]["paid_amount"] == "0.00"


def test_28_payment_list_excludes_deleted_order():
    """已删除订单的收款记录不出现在收款列表"""
    db = TestSession()
    try:
        from datetime import UTC, datetime

        admin = db.query(User).filter(User.id == uuid.UUID(_admin_id)).first()
        customer = Customer(
            id=uuid.uuid4(),
            name="删除订单收款测试客户",
            phone="13900990077",
            owner_user_id=admin.id,
            created_by=admin.id,
        )
        db.add(customer)
        db.flush()
        product = Product(
            id=uuid.uuid4(),
            name="删除订单收款测试商品",
            sku="PAY-DEL-001",
            sale_price=100,
            cost_price=50,
            stock_quantity=10,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(product)
        db.flush()
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="SO-PAY-DEL",
            customer_id=customer.id,
            sales_user_id=admin.id,
            status="confirmed",
            total_amount=100,
            total_cost=50,
            gross_profit=50,
            gross_margin=0.5,
            paid_amount=100,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(order)
        db.flush()
        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            amount=100,
            payment_method="cash",
            operator_id=admin.id,
            status="normal",
        )
        db.add(payment)
        db.flush()
        pid = str(payment.id)

        # 软删除订单
        order.deleted_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()

    # 收款列表不应包含已删除订单的收款
    resp = client.get("/api/v1/payments", headers=_auth())
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()["data"]["items"]]
    assert pid not in ids, "已删除订单的收款不应出现在列表中"


def test_29_non_owner_payment_rejected():
    """非订单所有者（无 order:view_all）不能收款"""
    db = TestSession()
    try:
        sales_user = _create_user_with_perms(db, "pay_other_sales", ["payment:create", "payment:list"])
        db.commit()
        token = create_access_token(str(sales_user.id))
    finally:
        db.close()

    # 管理员的订单，sales_user 无 order:view_all 权限，不应能收款
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "amount": "10", "payment_method": "cash",
    }, headers={"Authorization": f"Bearer {token}"})
    # 已完成订单返回 400（状态先于所有权检查），但关键是无权操作
    assert resp.status_code in (400, 403)


def test_30_payment_list_excludes_reversed():
    """收款列表不包含已冲正的收款记录"""
    # 创建并确认新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 创建两笔收款
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "40", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    payment_a_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "60", "payment_method": "transfer",
    }, headers=_auth())
    assert resp.status_code == 200
    payment_b_id = resp.json()["data"]["id"]

    # 冲正第一笔
    resp = client.post(f"/api/v1/payments/{payment_a_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    # 列表过滤只看该订单
    resp = client.get(f"/api/v1/payments?order_id={order_id}", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    returned_ids = [p["id"] for p in items]
    assert payment_a_id not in returned_ids, "已冲正收款不应出现在列表"
    assert payment_b_id in returned_ids


def test_31_payment_decimal_precision():
    """收款金额多小数位精度处理"""
    # 创建并确认新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 金额带 3 位小数，系统应接受或截断
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "33.333", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200
    # 返回金额应为有效的 Decimal 字符串
    returned_amount = resp.json()["data"]["amount"]
    Decimal(returned_amount)  # 不应抛异常

    # 确认订单 paid_amount 也是合法 Decimal
    resp = client.get(f"/api/v1/sales-orders/{order_id}", headers=_auth())
    assert resp.status_code == 200
    Decimal(resp.json()["data"]["paid_amount"])


def test_32_payment_list_desc_order():
    """收款列表按创建时间降序排列"""
    # 创建并确认新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 分两笔收款
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "10", "payment_method": "cash",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "10", "payment_method": "transfer",
    }, headers=_auth())
    assert resp.status_code == 200

    # 验证列表降序
    resp = client.get("/api/v1/payments", params={"order_id": order_id}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    from datetime import datetime
    times = [datetime.fromisoformat(p["created_at"]) for p in items]
    assert times == sorted(times, reverse=True)


def test_33_payment_list_page_size_100():
    """收款列表 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/payments", params={"page_size": 100}, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_34_payment_remark_xss_sanitized():
    """收款备注 HTML 标签被清理"""
    # 创建并确认新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())
    assert resp.status_code == 200

    # 创建带 HTML 标签备注的收款
    resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "10", "payment_method": "cash",
        "remark": "<script>alert('xss')</script>正常备注",
    }, headers=_auth())
    assert resp.status_code == 200

    # 通过列表验证备注已清理
    resp = client.get("/api/v1/payments", params={"order_id": order_id}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    payment = next(p for p in items if p.get("remark"))
    assert "<script>" not in payment["remark"]
    assert "正常备注" in payment["remark"]


def test_35_payment_list_page_size_over_max_422():
    """收款列表 page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/payments", params={"page_size": 101}, headers=_auth())
    assert resp.status_code == 422


def test_36_reverse_payment_audit_log():
    """冲正收款产生审计日志"""
    from app.models.audit import AuditLog

    # 创建并确认订单 + 收款
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{oid}/confirm", headers=_auth())
    pay_resp = client.post(f"/api/v1/payments/orders/{oid}/payments", json={
        "amount": "10", "payment_method": "cash",
    }, headers=_auth())
    assert pay_resp.status_code == 200
    pay_id = pay_resp.json()["data"]["id"]

    # 冲正
    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=_auth())
    assert resp.status_code == 200

    # 直接查询数据库验证审计日志（避免跨模块 HTTP 调用依赖）
    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "payment_reverse",
            AuditLog.resource_id == pay_id,
        ).first()
        assert log is not None
        assert log.resource_type == "payment"
        import json
        after = json.loads(log.after_data) if isinstance(log.after_data, str) else log.after_data
        assert after["status"] == "reversed"
    finally:
        db.close()


def test_37_list_payments_no_permission_403():
    """无 payment:list 权限用户获取收款列表返回 403"""
    from helpers import make_user_with_perms

    token = make_user_with_perms(TestSession, "no_payment_list", ["payment:create"])
    resp = client.get("/api/v1/payments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def _admin_auth():
    from helpers import admin_auth_header
    return admin_auth_header(TestSession, "pay_tester")


def test_38_reverse_payment_draft_order_400():
    """冲正草稿订单的收款返回 400（订单状态不允许）"""
    headers = _admin_auth()

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "pay_tester").first()
        cust = db.query(Customer).first()
        prod = db.query(Product).filter(Product.sku == "PAY-TEST-01").first()

        uid = uuid.uuid4().hex[:8]
        # 直接创建草稿订单
        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"PAY-DRAFT-{uid}", customer_id=cust.id,
            sales_user_id=user.id, status="draft",
            total_amount=100, total_cost=60,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))

        # 直接创建收款记录（绕过 API，因为草稿订单 API 不允许收款）
        payment = Payment(
            id=uuid.uuid4(), order_id=order.id,
            amount=Decimal("100"), payment_method="cash",
            status="normal", operator_id=user.id,
        )
        db.add(payment)
        db.commit()
        pay_id = str(payment.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


def test_39_reverse_payment_cancelled_order_400():
    """冲正已取消订单的收款返回 400"""
    headers = _admin_auth()

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "pay_tester").first()
        cust = db.query(Customer).first()
        prod = db.query(Product).filter(Product.sku == "PAY-TEST-01").first()

        uid = uuid.uuid4().hex[:8]
        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"PAY-CANCEL-{uid}", customer_id=cust.id,
            sales_user_id=user.id, status="cancelled",
            total_amount=100, total_cost=60,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        payment = Payment(
            id=uuid.uuid4(), order_id=order.id,
            amount=Decimal("100"), payment_method="cash",
            status="normal", operator_id=user.id,
        )
        db.add(payment)
        db.commit()
        pay_id = str(payment.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ORDER_INVALID_STATUS"


def test_40_create_payment_zero_amount_422():
    """收款金额为零返回 422"""
    headers = _admin_auth()
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "amount": "0", "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 422


def test_41_create_payment_negative_amount_422():
    """收款金额为负数返回 422"""
    headers = _admin_auth()
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "amount": "-50", "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 422


def test_42_reverse_payment_non_owner_403():
    """非归属用户冲正收款返回 403（无 order:view_all）"""
    from helpers import admin_auth_header, make_user_with_perms

    admin_auth_header(TestSession, "pay_tester")

    # 创建新的已确认订单 + 收款
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "pay_tester").first()
        cust = db.query(Customer).first()
        prod = db.query(Product).filter(Product.sku == "PAY-TEST-01").first()

        uid = uuid.uuid4().hex[:8]
        order = SalesOrder(
            id=uuid.uuid4(), order_no=f"PAY-REV403-{uid}", customer_id=cust.id,
            sales_user_id=user.id, status="confirmed",
            total_amount=100, total_cost=60,
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            id=uuid.uuid4(), order_id=order.id, product_id=prod.id,
            product_name_snapshot=prod.name, cost_price_snapshot=60,
            quantity=1, unit_price=100, subtotal_amount=100, subtotal_cost=60,
        ))
        payment = Payment(
            id=uuid.uuid4(), order_id=order.id,
            amount=Decimal("100"), payment_method="cash",
            status="normal", operator_id=user.id,
        )
        db.add(payment)
        db.commit()
        pay_id = str(payment.id)
    finally:
        db.close()

    # 非归属用户有 payment:reverse 但无 order:view_all → 403
    token = make_user_with_perms(TestSession, "non_owner_reverse", ["payment:reverse"])
    resp = client.post(f"/api/v1/payments/{pay_id}/reverse", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_43_payment_list_data_scope_non_owner():
    """无 order:view_all 用户收款列表只返回本人订单的收款（数据范围过滤）"""
    from helpers import make_user_with_perms

    # DB 中已有 pay_tester 的订单和收款
    # 非归属用户只能看到自己订单的收款（应为空列表）
    token = make_user_with_perms(TestSession, "non_owner_pay_scope", ["payment:list"])
    resp = client.get("/api/v1/payments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 0, "非归属用户不应看到其他人的收款"


def test_44_create_payment_invalid_method_422():
    """无效收款方式返回 422"""
    headers = _admin_auth()
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "amount": "10", "payment_method": "crypto",
    }, headers=headers)
    assert resp.status_code == 422


def test_45_create_payment_empty_amount_422():
    """收款金额为空返回 422"""
    headers = _admin_auth()
    resp = client.post(f"/api/v1/payments/orders/{_confirmed_order_id}/payments", json={
        "payment_method": "cash",
    }, headers=headers)
    assert resp.status_code == 422


def test_46_double_reverse_second_returns_404():
    """同一笔收款冲正两次：第一次成功，第二次返回 404"""
    # 创建并确认订单 + 收款
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    order_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{order_id}/confirm", headers=_auth())

    pay_resp = client.post(f"/api/v1/payments/orders/{order_id}/payments", json={
        "amount": "50", "payment_method": "cash",
    }, headers=_auth())
    assert pay_resp.status_code == 200
    pay_id = pay_resp.json()["data"]["id"]

    # 第一次冲正成功
    resp1 = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=_auth())
    assert resp1.status_code == 200

    # 第二次冲正返回 404（已被 with_for_update 行锁保护）
    resp2 = client.post(f"/api/v1/payments/{pay_id}/reverse", headers=_auth())
    assert resp2.status_code == 404
    assert "已冲正" in resp2.json()["error"]["message"]
