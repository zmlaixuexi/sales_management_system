"""数据导出集成测试 — 验证 CSV 导出功能"""

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
