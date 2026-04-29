"""输入清理工具测试"""

from app.core.sanitize import escape_like


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
