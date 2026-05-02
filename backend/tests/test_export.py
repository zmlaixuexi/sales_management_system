"""数据导出集成测试 — 验证 CSV 导出功能"""

import uuid
from datetime import UTC

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_export.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""
_order_id: str = ""


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
            username="export_tester",
            hashed_password=hash_password("testpass123"),
            display_name="导出测试员",
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
    if os.path.exists("./test_export.db"):
        os.remove("./test_export.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login_and_setup():
    """登录并准备测试数据"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "export_tester",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]

    # 创建商品
    resp = client.post("/api/v1/products", json={
        "name": "导出测试商品",
        "cost_price": "50.00",
        "sale_price": "100.00",
        "stock_quantity": 30,
        "status": "active",
    }, headers=_auth())
    assert resp.status_code == 200
    global _product_id
    _product_id = resp.json()["data"]["id"]

    # 创建客户
    resp = client.post("/api/v1/customers", json={
        "name": "导出测试客户",
        "contact_name": "王五",
        "phone": "13700137000",
    }, headers=_auth())
    assert resp.status_code == 200
    global _customer_id
    _customer_id = resp.json()["data"]["id"]

    # 创建并确认订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 5, "unit_price": "100.00"}],
    }, headers=_auth())
    assert resp.status_code == 200
    global _order_id
    _order_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{_order_id}/confirm", headers=_auth())

    # 登记收款
    client.post(f"/api/v1/payments/orders/{_order_id}/payments", json={
        "amount": "500.00",
        "payment_method": "cash",
    }, headers=_auth())


def test_02_export_products_csv():
    """导出商品 CSV"""
    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")

    content = resp.text
    assert "SKU" in content
    assert "商品名称" in content
    assert "导出测试商品" in content


def test_03_export_products_with_filter():
    """带筛选条件导出商品"""
    resp = client.get("/api/v1/exports/products?status=active", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "导出测试商品" in content


def test_04_export_customers_csv():
    """导出客户 CSV"""
    resp = client.get("/api/v1/exports/customers", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "客户名称" in content
    assert "导出测试客户" in content
    assert "13700137000" in content


def test_05_export_orders_csv():
    """导出订单 CSV"""
    resp = client.get("/api/v1/exports/orders", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "订单号" in content
    assert "ORD-" in content


def test_06_export_payments_csv():
    """导出收款 CSV"""
    resp = client.get("/api/v1/exports/payments", headers=_auth())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    content = resp.text
    assert "收款ID" in content
    assert "金额" in content


def test_07_export_requires_auth():
    """导出需要登录认证"""
    resp = client.get("/api/v1/exports/products")
    assert resp.status_code == 401


def test_08_export_empty_filter():
    """筛选条件无匹配时导出空数据（只有表头）"""
    resp = client.get("/api/v1/exports/products?status=nonexistent", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "SKU" in content
    # 只有一行表头
    lines = [line for line in content.strip().split("\n") if line.strip()]
    assert len(lines) == 1


def test_09_export_creates_audit_log():
    """导出操作生成审计日志"""

    # 执行导出
    resp = client.get("/api/v1/exports/products?status=active", headers=_auth())
    assert resp.status_code == 200

    # 查询审计日志
    resp = client.get("/api/v1/audit-logs?action=export_products", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["action"] == "export_products"
    assert log["resource_type"] == "product"
    assert log["actor_name"] == "导出测试员"
    assert log["ip_address"] is not None


# ── CSV 内容格式验证测试 ──────────────────────────────────────


def test_10_export_products_csv_has_bom():
    """验证商品 CSV 以 UTF-8 BOM 开头"""
    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    assert resp.text.startswith("﻿")


def test_11_export_products_csv_header_and_fields():
    """验证商品 CSV 表头顺序和每行字段数一致"""
    import csv
    import io

    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) >= 2  # 表头 + 至少一行数据

    expected_headers = ["SKU", "商品名称", "销售价", "成本价", "库存", "状态", "分类", "备注", "创建时间"]
    assert rows[0] == expected_headers

    for i, row in enumerate(rows[1:], start=2):
        assert len(row) == len(expected_headers), f"第 {i} 行字段数不匹配: {row}"


def test_12_export_products_status_in_chinese():
    """验证商品 CSV 中状态字段为中文"""
    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "上架" in content


def test_13_export_customers_csv_header_and_fields():
    """验证客户 CSV 表头顺序和每行字段数"""
    import csv
    import io

    resp = client.get("/api/v1/exports/customers", headers=_auth())
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) >= 2

    expected_headers = [
        "客户名称", "联系人", "电话", "邮箱", "来源",
        "等级", "归属销售", "跟进状态", "备注", "创建时间",
    ]
    assert rows[0] == expected_headers

    for i, row in enumerate(rows[1:], start=2):
        assert len(row) == len(expected_headers), f"第 {i} 行字段数不匹配: {row}"


def test_14_export_customers_csv_has_owner():
    """验证客户 CSV 包含归属销售名称"""
    resp = client.get("/api/v1/exports/customers", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "导出测试员" in content


def test_15_export_orders_csv_header_and_fields():
    """验证订单 CSV 表头顺序和每行字段数"""
    import csv
    import io

    resp = client.get("/api/v1/exports/orders", headers=_auth())
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) >= 2

    expected_headers = ["订单号", "客户ID", "状态", "销售额", "成本", "毛利", "毛利率",
                        "已收金额", "明细数", "备注", "创建时间"]
    assert rows[0] == expected_headers

    for i, row in enumerate(rows[1:], start=2):
        assert len(row) == len(expected_headers), f"第 {i} 行字段数不匹配: {row}"


def test_16_export_orders_status_in_chinese():
    """验证订单 CSV 中状态为中文"""
    resp = client.get("/api/v1/exports/orders", headers=_auth())
    assert resp.status_code == 200
    content = resp.text
    assert "已完成" in content


def test_17_export_payments_csv_header_and_fields():
    """验证收款 CSV 表头顺序和每行字段数"""
    import csv
    import io

    resp = client.get("/api/v1/exports/payments", headers=_auth())
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) >= 2

    expected_headers = ["收款ID", "订单ID", "金额", "收款方式", "状态", "收款时间", "备注", "创建时间"]
    assert rows[0] == expected_headers

    for i, row in enumerate(rows[1:], start=2):
        assert len(row) == len(expected_headers), f"第 {i} 行字段数不匹配: {row}"


def test_18_export_products_csv_values():
    """验证商品 CSV 数据行具体值"""
    import csv
    import io

    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    # 找到导出测试商品行
    data_rows = [r for r in rows[1:] if r[1] == "导出测试商品"]
    assert len(data_rows) == 1
    row = data_rows[0]
    assert row[2] == "100.00"  # 销售价
    assert row[4] == "25"      # 库存（原始30 - 订单5）
    assert row[5] == "上架"     # 状态映射
    assert row[6] == "未分类"   # 分类


def test_19_export_products_keyword_filter():
    """商品导出关键字筛选"""
    resp = client.get("/api/v1/exports/products?keyword=导出测试", headers=_auth())
    assert resp.status_code == 200
    assert "导出测试商品" in resp.text


def test_20_export_products_category_filter():
    """商品导出分类筛选"""
    # 先获取分类 ID
    resp = client.get("/api/v1/products", headers=_auth())
    items = resp.json()["data"]["items"]
    cat_id = items[0]["category_id"] if items else None
    if cat_id:
        resp = client.get(f"/api/v1/exports/products?category_id={cat_id}", headers=_auth())
        assert resp.status_code == 200
        assert "导出测试商品" in resp.text


def test_21_export_customers_keyword_filter():
    """客户导出关键字筛选（按电话）"""
    resp = client.get("/api/v1/exports/customers?keyword=13700137000", headers=_auth())
    assert resp.status_code == 200
    assert "导出测试客户" in resp.text


def test_22_export_customers_source_filter():
    """客户导出来源筛选"""
    resp = client.get("/api/v1/exports/customers?source=nonexistent", headers=_auth())
    assert resp.status_code == 200
    lines = [line for line in resp.text.strip().split("\n") if line.strip() and "客户名称" not in line]
    assert len(lines) == 0


def test_23_export_orders_status_filter():
    """订单导出状态筛选"""
    resp = client.get("/api/v1/exports/orders?status=completed", headers=_auth())
    assert resp.status_code == 200
    assert "ORD-" in resp.text


def test_24_export_orders_date_filter():
    """订单导出日期范围筛选"""
    today = "2026-01-01"
    far_future = "2099-12-31"
    resp = client.get(f"/api/v1/exports/orders?start_date={today}&end_date={far_future}", headers=_auth())
    assert resp.status_code == 200
    assert "ORD-" in resp.text


def test_25_export_payments_order_filter():
    """收款导出按订单筛选"""
    resp = client.get(f"/api/v1/exports/payments?order_id={_order_id}", headers=_auth())
    assert resp.status_code == 200
    assert "500.00" in resp.text


def test_26_export_payments_date_filter():
    """收款导出日期范围筛选"""
    today = "2026-01-01"
    far_future = "2099-12-31"
    resp = client.get(f"/api/v1/exports/payments?start_date={today}&end_date={far_future}", headers=_auth())
    assert resp.status_code == 200
    assert "500.00" in resp.text


def test_27_export_orders_keyword_filter():
    """订单导出关键字筛选（按订单号）"""
    resp = client.get("/api/v1/sales-orders", headers=_auth())
    items = resp.json()["data"]["items"]
    if items:
        order_no = items[0]["order_no"]
        resp = client.get(f"/api/v1/exports/orders?keyword={order_no[:6]}", headers=_auth())
        assert resp.status_code == 200
        assert order_no in resp.text


def test_28_export_orders_customer_filter():
    """订单导出按客户筛选"""
    resp = client.get(f"/api/v1/exports/orders?customer_id={_customer_id}", headers=_auth())
    assert resp.status_code == 200
    assert "ORD-" in resp.text


def test_29_export_requires_permission():
    """导出需要对应权限，无权限用户返回 403"""
    from app.core.security import create_access_token

    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_export_perm",
            hashed_password=hash_password("testpass123"),
            display_name="无导出权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    for path in ["/api/v1/exports/products", "/api/v1/exports/customers",
                 "/api/v1/exports/orders", "/api/v1/exports/payments"]:
        resp = client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, f"{path} should return 403"


def test_30_export_products_cost_hidden_without_permission():
    """无 product:view_cost 权限用户导出商品不含成本价"""
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        perm_list = db.query(Permission).filter(Permission.code == "product:list").first()
        if not perm_list:
            perm_list = Permission(id=uuid.uuid4(), code="product:list", name="商品列表", module="product")
            db.add(perm_list)
            db.flush()
        role = Role(id=uuid.uuid4(), name="export_cost_check", display_name="成本检查")
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm_list.id))
        user = User(
            id=uuid.uuid4(), username="cost_checker",
            hashed_password=hash_password("testpass123"),
            display_name="成本检查员", is_active=True, is_superuser=False,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        token = create_access_token(str(user.id))
    finally:
        db.close()

    resp = client.get("/api/v1/exports/products", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    content = resp.text
    assert "成本价" not in content


def test_31_export_orders_data_scope_filtered():
    """非 order:view_all 用户导出订单只包含本人数据"""
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        db.query(User).filter(User.username == "export_tester").first()

        # 创建只有 order:list 权限的用户
        perm = db.query(Permission).filter(Permission.code == "order:list").first()
        if not perm:
            perm = Permission(id=uuid.uuid4(), code="order:list", name="订单列表", module="order")
            db.add(perm)
            db.flush()
        role = Role(id=uuid.uuid4(), name="export_scope", display_name="范围测试")
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        scope_user = User(
            id=uuid.uuid4(), username="scope_exporter",
            hashed_password=hash_password("testpass123"),
            display_name="范围导出员", is_active=True, is_superuser=False,
        )
        db.add(scope_user)
        db.flush()
        db.add(UserRole(user_id=scope_user.id, role_id=role.id))
        db.commit()
        token = create_access_token(str(scope_user.id))
    finally:
        db.close()

    resp = client.get("/api/v1/exports/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # scope_user 没有订单，应只有表头行
    lines = [line for line in resp.text.strip().split("\n") if line.strip()]
    # BOM 行 + header = 1 或 2 行（BOM 可能在 header 行内）
    data_lines = [ln for ln in lines if "订单号" not in ln]
    assert len(data_lines) == 0


# ── 导出异常路径测试 ──────────────────────────────────────────


def test_32_export_customers_requires_auth():
    """客户导出未认证返回 401"""
    resp = client.get("/api/v1/exports/customers")
    assert resp.status_code == 401


def test_33_export_orders_requires_auth():
    """订单导出未认证返回 401"""
    resp = client.get("/api/v1/exports/orders")
    assert resp.status_code == 401


def test_34_export_payments_requires_auth():
    """收款导出未认证返回 401"""
    resp = client.get("/api/v1/exports/payments")
    assert resp.status_code == 401


def test_35_export_products_invalid_category_id_422():
    """商品导出无效 category_id 格式返回 422"""
    resp = client.get("/api/v1/exports/products?category_id=not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_36_export_orders_invalid_customer_id_422():
    """订单导出无效 customer_id 格式返回 422"""
    resp = client.get("/api/v1/exports/orders?customer_id=not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_37_export_payments_invalid_order_id_422():
    """收款导出无效 order_id 格式返回 422"""
    resp = client.get("/api/v1/exports/payments?order_id=not-a-uuid", headers=_auth())
    assert resp.status_code == 422


# ── 软删除记录排除测试 ──────────────────────────────────────────


def test_38_export_products_excludes_deleted():
    """已删除商品不出现在导出结果中"""
    from datetime import datetime

    from app.models.product import Product

    # 创建一个新商品
    resp = client.post("/api/v1/products", json={
        "name": "待删除导出商品",
        "cost_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 5,
        "status": "active",
    }, headers=_auth())
    assert resp.status_code == 200
    del_pid = resp.json()["data"]["id"]

    # 直接在数据库软删除
    db = TestSession()
    try:
        db.query(Product).filter(Product.id == uuid.UUID(del_pid)).update(
            {"deleted_at": datetime.now(UTC)}
        )
        db.commit()
    finally:
        db.close()

    # 导出应不含该商品
    resp = client.get("/api/v1/exports/products", headers=_auth())
    assert resp.status_code == 200
    assert "待删除导出商品" not in resp.text


def test_39_export_customers_excludes_deleted():
    """已删除客户不出现在导出结果中"""
    from datetime import datetime

    from app.models.customer import Customer

    # 创建一个新客户
    resp = client.post("/api/v1/customers", json={
        "name": "待删除导出客户",
        "phone": "13800000001",
    }, headers=_auth())
    assert resp.status_code == 200
    del_cid = resp.json()["data"]["id"]

    # 直接在数据库软删除
    db = TestSession()
    try:
        db.query(Customer).filter(Customer.id == uuid.UUID(del_cid)).update(
            {"deleted_at": datetime.now(UTC)}
        )
        db.commit()
    finally:
        db.close()

    # 导出应不含该客户
    resp = client.get("/api/v1/exports/customers", headers=_auth())
    assert resp.status_code == 200
    assert "待删除导出客户" not in resp.text


def test_40_export_orders_excludes_deleted():
    """已删除订单不出现在导出结果中"""
    from datetime import datetime

    from app.models.order import SalesOrder

    # 创建一个新订单
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 1}],
    }, headers=_auth())
    assert resp.status_code == 200
    del_oid = resp.json()["data"]["id"]

    # 直接在数据库软删除
    db = TestSession()
    try:
        db.query(SalesOrder).filter(SalesOrder.id == uuid.UUID(del_oid)).update(
            {"deleted_at": datetime.now(UTC)}
        )
        db.commit()
    finally:
        db.close()

    # 导出应不含该订单号
    db = TestSession()
    try:
        order = db.query(SalesOrder).filter(SalesOrder.id == uuid.UUID(del_oid)).first()
        order_no = order.order_no if order else None
    finally:
        db.close()

    resp = client.get("/api/v1/exports/orders", headers=_auth())
    assert resp.status_code == 200
    if order_no:
        assert order_no not in resp.text


def test_41_export_payments_excludes_deleted_order():
    """已删除订单关联的收款不出现在导出结果中"""
    from datetime import datetime

    from app.models.order import SalesOrder

    # 创建订单 + 确认 + 收款
    resp = client.post("/api/v1/sales-orders", json={
        "customer_id": _customer_id,
        "items": [{"product_id": _product_id, "quantity": 2}],
    }, headers=_auth())
    assert resp.status_code == 200
    del_oid = resp.json()["data"]["id"]
    client.post(f"/api/v1/sales-orders/{del_oid}/confirm", headers=_auth())
    pay_resp = client.post(f"/api/v1/payments/orders/{del_oid}/payments", json={
        "amount": "200.00",
        "payment_method": "transfer",
    }, headers=_auth())
    assert pay_resp.status_code == 200
    payment_id = pay_resp.json()["data"]["id"]

    # 软删除订单
    db = TestSession()
    try:
        db.query(SalesOrder).filter(SalesOrder.id == uuid.UUID(del_oid)).update(
            {"deleted_at": datetime.now(UTC)}
        )
        db.commit()
    finally:
        db.close()

    # 导出收款应不含该笔
    resp = client.get("/api/v1/exports/payments", headers=_auth())
    assert resp.status_code == 200
    assert payment_id not in resp.text


def test_42_export_customers_data_scope_filtered():
    """非 customer:view_all 用户导出客户只包含本人归属数据"""
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        perm = db.query(Permission).filter(Permission.code == "customer:list").first()
        if not perm:
            perm = Permission(id=uuid.uuid4(), code="customer:list", name="客户列表", module="customer")
            db.add(perm)
            db.flush()
        role = Role(id=uuid.uuid4(), name="cust_export_scope", display_name="客户范围测试")
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        scope_user = User(
            id=uuid.uuid4(), username="scope_cust_exporter",
            hashed_password=hash_password("testpass123"),
            display_name="客户范围导出员", is_active=True, is_superuser=False,
        )
        db.add(scope_user)
        db.flush()
        db.add(UserRole(user_id=scope_user.id, role_id=role.id))
        db.commit()
        token = create_access_token(str(scope_user.id))
    finally:
        db.close()

    resp = client.get("/api/v1/exports/customers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # scope_user 没有客户，应只有表头行
    lines = [line for line in resp.text.strip().split("\n") if line.strip()]
    data_lines = [ln for ln in lines if "客户名称" not in ln]
    assert len(data_lines) == 0


def test_43_export_payments_data_scope_filtered():
    """非 order:view_all 用户导出收款只包含本人订单关联的收款"""
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        perm = db.query(Permission).filter(Permission.code == "payment:list").first()
        if not perm:
            perm = Permission(id=uuid.uuid4(), code="payment:list", name="收款列表", module="payment")
            db.add(perm)
            db.flush()
        role = Role(id=uuid.uuid4(), name="pay_export_scope", display_name="收款范围测试")
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        scope_user = User(
            id=uuid.uuid4(), username="scope_pay_exporter",
            hashed_password=hash_password("testpass123"),
            display_name="收款范围导出员", is_active=True, is_superuser=False,
        )
        db.add(scope_user)
        db.flush()
        db.add(UserRole(user_id=scope_user.id, role_id=role.id))
        db.commit()
        token = create_access_token(str(scope_user.id))
    finally:
        db.close()

    resp = client.get("/api/v1/exports/payments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # scope_user 没有订单和收款，应只有表头行
    lines = [line for line in resp.text.strip().split("\n") if line.strip()]
    data_lines = [ln for ln in lines if "收款ID" not in ln]
    assert len(data_lines) == 0


def test_44_export_customers_audit_log():
    """客户导出产生审计日志"""
    from app.core.security import create_access_token
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()

    resp = client.get("/api/v1/exports/customers", headers=headers)
    assert resp.status_code == 200

    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "export_customers",
        ).first()
        assert log is not None
        assert log.resource_type == "customer"
    finally:
        db.close()


def test_45_export_orders_audit_log():
    """订单导出产生审计日志"""
    from app.core.security import create_access_token
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()

    resp = client.get("/api/v1/exports/orders", headers=headers)
    assert resp.status_code == 200

    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "export_orders",
        ).first()
        assert log is not None
        assert log.resource_type == "order"
    finally:
        db.close()


def test_46_export_payments_audit_log():
    """收款导出产生审计日志"""
    from app.core.security import create_access_token
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()

    resp = client.get("/api/v1/exports/payments", headers=headers)
    assert resp.status_code == 200

    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "export_payments",
        ).first()
        assert log is not None
        assert log.resource_type == "payment"
    finally:
        db.close()


def test_38_export_empty_products_csv():
    """导出空商品列表返回有效 CSV（仅 BOM + 表头行）"""
    from app.core.security import create_access_token
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()
    resp = client.get("/api/v1/exports/products?keyword=ZZZZZ_NONEXISTENT", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert content.startswith("﻿")  # BOM
    lines = content.strip().split("\n")
    assert len(lines) == 1  # 仅表头


def test_39_export_empty_customers_csv():
    """导出空客户列表返回有效 CSV（仅 BOM + 表头行）"""
    from app.core.security import create_access_token
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()
    resp = client.get("/api/v1/exports/customers?keyword=ZZZZZ_NONEXISTENT", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert content.startswith("﻿")
    lines = content.strip().split("\n")
    assert len(lines) == 1


def test_40_export_empty_orders_csv():
    """导出空订单列表返回有效 CSV（仅 BOM + 表头行）"""
    from app.core.security import create_access_token
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()
    resp = client.get("/api/v1/exports/orders?keyword=ZZZZZ_NONEXISTENT", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert content.startswith("﻿")
    lines = content.strip().split("\n")
    assert len(lines) == 1


def test_41_export_empty_payments_csv():
    """导出空收款列表返回有效 CSV（仅 BOM + 表头行）"""
    from app.core.security import create_access_token
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "export_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()
    resp = client.get("/api/v1/exports/payments?order_id=00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert content.startswith("﻿")
    lines = content.strip().split("\n")
    assert len(lines) == 1
