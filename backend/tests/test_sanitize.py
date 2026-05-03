"""输入清理工具测试"""

from app.core.sanitize import escape_like, sanitize_csv_cell, sanitize_text, strip_control_chars, strip_html


def test_escape_like_percent():
    """转义 % 通配符"""
    assert escape_like("100%") == "100\\%"


def test_escape_like_underscore():
    """转义 _ 通配符"""
    assert escape_like("test_name") == "test\\_name"


def test_escape_like_backslash():
    """转义反斜杠"""
    assert escape_like("path\\file") == "path\\\\file"


def test_escape_like_combined():
    """混合特殊字符"""
    assert escape_like("100%_test\\end") == "100\\%\\_test\\\\end"


def test_escape_like_no_special():
    """无特殊字符不变"""
    assert escape_like("hello") == "hello"


def test_escape_like_empty():
    """空字符串不变"""
    assert escape_like("") == ""


def test_strip_html_removes_tags():
    """移除 HTML 标签"""
    assert strip_html("<script>alert('xss')</script>商品") == "alert('xss')商品"


def test_strip_html_no_tags():
    """无标签不变"""
    assert strip_html("普通文本") == "普通文本"


def test_strip_html_nested_tags():
    """嵌套标签全部移除"""
    assert strip_html("<div><b>粗体</b></div>") == "粗体"


def test_strip_html_self_closing():
    """自闭合标签移除"""
    assert strip_html("图片<img src='x'>结束") == "图片结束"


def test_product_schema_sanitizes_name():
    """ProductCreate schema 净化名称中的 HTML"""
    from app.schemas.product import ProductCreate
    p = ProductCreate(name="<b>XSS</b>商品", sale_price="10", cost_price="5")
    assert p.name == "XSS商品"


def test_customer_schema_sanitizes_name():
    """CustomerCreate schema 净化名称中的 HTML"""
    from app.schemas.customer import CustomerCreate
    c = CustomerCreate(name="<script>alert(1)</script>客户")
    assert c.name == "alert(1)客户"


def test_customer_schema_sanitizes_email():
    """CustomerCreate schema 净化邮箱中的 HTML"""
    from app.schemas.customer import CustomerCreate
    c = CustomerCreate(name="测试客户", email="<b>xss</b>@test.com")
    assert c.email == "xss@test.com"


def test_user_schema_sanitizes_email():
    """UserCreate schema 净化邮箱中的 HTML"""
    from app.schemas.auth import UserCreate
    u = UserCreate(username="testuser", password="pass123", email="<script>x</script>@evil.com")
    assert u.email == "x@evil.com"


def test_sanitize_product_name_strips_html():
    """商品名称中的 HTML 标签被移除"""
    from app.schemas.product import ProductCreate
    data = ProductCreate(name="<script>alert(1)</script>正常商品", sale_price="10")
    assert "<script>" not in data.name
    assert "正常商品" in data.name


def test_sanitize_product_remark_strips_html():
    """商品备注中的 HTML 标签被移除"""
    from app.schemas.product import ProductCreate
    data = ProductCreate(name="test", sale_price="10", remark="<b>粗体</b>备注")
    assert "<b>" not in data.remark
    assert "粗体备注" in data.remark


def test_sanitize_customer_name_strips_html():
    """客户名称中的 HTML 标签被移除"""
    from app.schemas.customer import CustomerCreate
    data = CustomerCreate(name="<img src=x>客户名")
    assert "<img" not in data.name
    assert "客户名" in data.name


def test_sanitize_customer_contact_name_strips_html():
    """客户联系人中的 HTML 标签被移除"""
    from app.schemas.customer import CustomerCreate
    data = CustomerCreate(name="测试客户", contact_name="<i>张三</i>")
    assert "<i>" not in data.contact_name
    assert "张三" in data.contact_name


def test_sanitize_customer_remark_strips_html():
    """客户备注中的 HTML 标签被移除"""
    from app.schemas.customer import CustomerCreate
    data = CustomerCreate(name="测试客户", remark="<script>xss</script>正常备注")
    assert "<script>" not in data.remark
    assert "正常备注" in data.remark


def test_sanitize_user_username_strips_html():
    """用户名中的 HTML 标签被移除"""
    from app.schemas.auth import UserCreate
    data = UserCreate(username="<b>admin</b>", password="pass123456")
    assert "<b>" not in data.username
    assert "admin" in data.username


def test_sanitize_user_display_name_strips_html():
    """用户显示名称中的 HTML 标签被移除"""
    from app.schemas.auth import UserCreate
    data = UserCreate(username="testuser", password="pass123456", display_name="<script>x</script>管理员")
    assert "<script>" not in data.display_name
    assert "管理员" in data.display_name


def test_sanitize_order_remark_strips_html():
    """订单备注中的 HTML 标签被移除"""
    from app.schemas.order import OrderCreate
    data = OrderCreate(
        customer_id="00000000-0000-0000-0000-000000000002",
        items=[{"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}],
        remark="<b>重要</b>订单",
    )
    assert "<b>" not in data.remark
    assert "重要订单" in data.remark


def test_sanitize_payment_remark_strips_html():
    """收款备注中的 HTML 标签被移除"""
    from app.schemas.payment import PaymentCreate
    data = PaymentCreate(amount="100", payment_method="cash", remark="<script>alert(1)</script>收款")
    assert "<script>" not in data.remark
    assert "收款" in data.remark


# ─── strip_control_chars ────────────────────────────────────


def test_strip_control_chars_removes_null_byte():
    assert strip_control_chars("hello\x00world") == "helloworld"


def test_strip_control_chars_removes_bell():
    assert strip_control_chars("alert\x07") == "alert"


def test_strip_control_chars_removes_escape():
    assert strip_control_chars("text\x1b") == "text"


def test_strip_control_chars_preserves_tab_newline_cr():
    assert strip_control_chars("line1\nline2\ttab\r\n") == "line1\nline2\ttab\r\n"


def test_strip_control_chars_no_control():
    assert strip_control_chars("normal text 123") == "normal text 123"


def test_strip_control_chars_empty():
    assert strip_control_chars("") == ""


def test_sanitize_text_strips_control_chars_and_html():
    result = sanitize_text("<b>bold</b>\x00text")
    assert result == "boldtext"


# ─── sanitize_csv_cell ──────────────────────────────────────────


def test_csv_cell_equals_prefix():
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_csv_cell_plus_prefix():
    assert sanitize_csv_cell("+cmd|calc") == "'+cmd|calc"


def test_csv_cell_minus_prefix():
    assert sanitize_csv_cell("-1+1") == "'-1+1"


def test_csv_cell_at_prefix():
    assert sanitize_csv_cell("@SUM") == "'@SUM"


def test_csv_cell_tab_prefix():
    assert sanitize_csv_cell("\t=cmd") == "'\t=cmd"


def test_csv_cell_cr_prefix():
    assert sanitize_csv_cell("\rcmd") == "'\rcmd"


def test_csv_cell_normal_text():
    assert sanitize_csv_cell("普通文本") == "普通文本"


def test_csv_cell_formula_midstring():
    assert sanitize_csv_cell("价格=100") == "价格=100"


def test_csv_cell_empty():
    assert sanitize_csv_cell("") == ""


def test_csv_cell_number():
    assert sanitize_csv_cell("123.45") == "123.45"


# ─── API 级别端到端注入向量测试 ──────────────────────────────────

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

_API_TEST_DB = "sqlite:///./test_sanitize_api.db"
_api_engine = create_engine(_API_TEST_DB, connect_args={"check_same_thread": False})
_ApiSession = sessionmaker(bind=_api_engine, autocommit=False, autoflush=False)

_client = TestClient(app)
_original_override = None


def _api_admin_headers() -> dict:
    db = _ApiSession()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _ApiSession()
    Base.metadata.create_all(bind=_api_engine)
    db = _ApiSession()
    db.add(User(
        id=uuid.uuid4(), username="admin", display_name="管理员",
        hashed_password=hash_password("testpass123"), is_superuser=True, is_active=True,
    ))
    db.commit()
    db.close()


def teardown_module(module):
    app.dependency_overrides[get_db] = _original_override if _original_override else lambda: None
    if _original_override is None:
        app.dependency_overrides.pop(get_db, None)
    _api_engine.dispose()
    import os
    try:
        os.remove("test_sanitize_api.db")
    except FileNotFoundError:
        pass


def test_api_xss_in_product_name_sanitized():
    """通过 API 创建商品时 XSS 载荷被消毒"""
    headers = _api_admin_headers()
    resp = _client.post("/api/v1/products", json={
        "name": "<script>alert('xss')</script>商品",
        "sale_price": "100",
        "cost_price": "50",
    }, headers=headers)
    assert resp.status_code == 200
    name = resp.json()["data"]["name"]
    assert "<script>" not in name
    assert "alert" in name


def test_api_sql_injection_in_search_safe():
    """搜索关键字中的 SQL 注入载荷不影响服务"""
    headers = _api_admin_headers()
    for payload in ["'; DROP TABLE products;--", "1 OR 1=1", "' UNION SELECT * FROM users--"]:
        resp = _client.get(f"/api/v1/products?keyword={payload}", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"]["items"], list)


def test_api_xss_in_customer_name_sanitized():
    """通过 API 创建客户时 XSS 载荷被消毒"""
    headers = _api_admin_headers()
    resp = _client.post("/api/v1/customers", json={
        "name": "<img src=x onerror=alert(1)>客户",
        "contact_name": "<b>张三</b>",
        "phone": "13800138001",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "<img" not in data["name"]
    assert "<b>" not in data["contact_name"]


def test_api_sql_injection_in_customer_search_safe():
    """客户搜索中的 SQL 注入载荷不影响服务"""
    headers = _api_admin_headers()
    for payload in ["' OR '1'='1", "'; DELETE FROM customers;--"]:
        resp = _client.get(f"/api/v1/customers?keyword={payload}", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"]["items"], list)


def test_api_like_wildcard_in_search_safe():
    """搜索关键字中的 LIKE 通配符被正确转义"""
    headers = _api_admin_headers()
    _client.post("/api/v1/products", json={
        "name": "100%纯棉T恤",
        "sale_price": "50",
    }, headers=headers)
    resp = _client.get("/api/v1/products?keyword=100%25", headers=headers)
    assert resp.status_code == 200


def test_api_control_chars_in_input_sanitized():
    """输入中的控制字符被移除"""
    headers = _api_admin_headers()
    resp = _client.post("/api/v1/products", json={
        "name": "商品\x00名称\x07",
        "sale_price": "100",
    }, headers=headers)
    assert resp.status_code == 200
    name = resp.json()["data"]["name"]
    assert "\x00" not in name
    assert "\x07" not in name
