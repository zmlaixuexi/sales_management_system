"""输入清理工具"""

_LIKE_SPECIAL_CHARS = {"%", "_", "\\"}


def escape_like(value: str) -> str:
    """转义 LIKE/ILIKE 查询中的特殊字符（%、_、\\）"""
    result = []
    for ch in value:
        if ch in _LIKE_SPECIAL_CHARS:
            result.append("\\")
        result.append(ch)
    return "".join(result)
