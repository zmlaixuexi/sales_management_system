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
