"""输入清理工具测试"""

from app.core.sanitize import escape_like, strip_html


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
        customer_id="fake-id",
        items=[{"product_id": "fake-id", "quantity": 1}],
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
