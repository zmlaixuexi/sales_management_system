"""密码强度验证 — 字符类别检查 + 常见弱密码黑名单"""

import re

# 常见弱密码黑名单（Top 50，大小写不敏感匹配）
_WEAK_PASSWORDS = frozenset({
    "password", "password1", "password123",
    "123456", "12345678", "123456789", "1234567890",
    "qwerty", "qwerty123", "qwertyuiop",
    "abc123", "abcdef", "abcdefg", "abcdefgh",
    "admin", "admin123", "admin888", "admin666",
    "root", "root123", "rootroot",
    "test", "test123", "testing",
    "letmein", "welcome", "welcome1",
    "monkey", "monkey123",
    "master", "master123",
    "dragon", "dragon123",
    "login", "login123",
    "princess", "sunshine",
    "football", "baseball", "shadow",
    "michael", "jennifer", "jessica",
    "charlie", "thomas", "robert",
    "iloveyou", "trustno1",
    "passw0rd", "p@ssw0rd", "p@ssword", "p@ssw0rd!",
    "1q2w3e4r", "1q2w3e",
    "aa123456", "666666", "888888",
    "woaini", "woaini1314", "taobao",
    "password!", "qwer1234",
})


def validate_password_strength(password: str) -> str:
    """验证密码强度。通过则返回原值，否则抛出 ValueError。

    规则：
    - 至少一个大写字母
    - 至少一个小写字母
    - 至少一个数字
    - 至少一个特殊字符
    - 不在常见弱密码黑名单中（忽略大小写）
    """
    if not re.search(r"[A-Z]", password):
        raise ValueError("密码必须包含至少一个大写字母")
    if not re.search(r"[a-z]", password):
        raise ValueError("密码必须包含至少一个小写字母")
    if not re.search(r"\d", password):
        raise ValueError("密码必须包含至少一个数字")
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("密码必须包含至少一个特殊字符")
    if password.lower() in _WEAK_PASSWORDS:
        raise ValueError("密码过于常见，请使用更强的密码")
    return password
