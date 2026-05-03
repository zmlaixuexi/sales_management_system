"""输入清理工具"""

import re

_LIKE_SPECIAL_CHARS = {"%", "_", "\\"}
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def escape_like(value: str) -> str:
    """转义 LIKE/ILIKE 查询中的特殊字符（%、_、\\）"""
    result = []
    for ch in value:
        if ch in _LIKE_SPECIAL_CHARS:
            result.append("\\")
        result.append(ch)
    return "".join(result)


def strip_html(value: str) -> str:
    """移除字符串中的 HTML 标签，防止存储型 XSS"""
    return _HTML_TAG_RE.sub("", value)


def strip_control_chars(value: str) -> str:
    """移除 ASCII 控制字符（保留 \\t \\n \\r）"""
    return _CONTROL_CHAR_RE.sub("", value)


def sanitize_text(v: str | None) -> str | None:
    """Pydantic field_validator 用的文本消毒函数，None 安全。"""
    if not v:
        return v
    v = strip_html(v)
    v = strip_control_chars(v)
    return v
