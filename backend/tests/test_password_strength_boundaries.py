"""安全加固：密码强度策略边界测试 — 覆盖最小可行密码、规则优先级、
完整黑名单遍历、特殊字符类别、Unicode、长度边界、返回值不变性"""

import string

import pytest

from app.core.password_strength import (
    _WEAK_PASSWORDS,
    validate_password_strength,
)


@pytest.fixture(autouse=True)
def _no_side_effects():
    """密码验证无副作用，无需清理"""
    yield


# ═══════════════════════════════════════════════════════
# 1. 最小可行密码
# ═══════════════════════════════════════════════════════


def test_min_4_chars_with_all_classes():
    """刚好满足四类字符的最短密码（4 字符）"""
    result = validate_password_strength("Aa1!")
    assert result == "Aa1!"


def test_min_5_chars_with_all_classes():
    """5 字符满足四类"""
    result = validate_password_strength("Ab1@c")
    assert result == "Ab1@c"


def test_3_chars_fails_either_rule():
    """3 字符不可能同时满足四类（大写+小写+数字+特殊=4 字符）"""
    # 只有 3 字符，至少缺一类
    with pytest.raises(ValueError):
        validate_password_strength("Aa1")


def test_single_char_fails():
    """单字符密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("A")


def test_two_chars_fails():
    """两字符密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("A1")


def test_exactly_4_chars_each_class():
    """4 字符，每类恰好 1 个"""
    assert validate_password_strength("Xb3$") == "Xb3$"


# ═══════════════════════════════════════════════════════
# 2. 规则评估顺序（大写 → 小写 → 数字 → 特殊 → 黑名单）
# ═══════════════════════════════════════════════════════


def test_rule_order_no_uppercase_first():
    """缺少大写和数字时，大写规则先触发"""
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("lower123!")


def test_rule_order_no_lowercase_second():
    """有大写无小写，触发小写规则"""
    with pytest.raises(ValueError, match="小写字母"):
        validate_password_strength("UPPER123!")


def test_rule_order_no_digit_third():
    """有大写有小写无数字，观数字规则"""
    with pytest.raises(ValueError, match="数字"):
        validate_password_strength("NoDigit!Pass")


def test_rule_order_no_special_fourth():
    """有大写有小写有数字无特殊，触特殊字符规则"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("NoSpecial1Pass")


def test_rule_order_blacklist_last():
    """四类都满足但命中黑名单，触发黑名单规则"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd")


def test_rule_order_multiple_violations_reports_first():
    """缺大写和特殊字符时，报告大写（先检查的规则）"""
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("nocaps123")


# ═══════════════════════════════════════════════════════
# 3. 特殊字符类别全面覆盖
# ═══════════════════════════════════════════════════════


@pytest.mark.parametrize("special", list("!@#$%^&*()-_=+[]{}|;:',.<>?/`~"))
def test_common_special_chars_accepted(special):
    """常见 ASCII 特殊字符都被接受"""
    pw = f"Aa1{special}"
    assert validate_password_strength(pw) == pw


def test_backslash_accepted():
    """反斜杠作为特殊字符被接受"""
    pw = "Aa1\\"
    assert validate_password_strength(pw) == pw


def test_double_quote_accepted():
    """双引号作为特殊字符被接受"""
    pw = 'Aa1"'
    assert validate_password_strength(pw) == pw


def test_single_quote_accepted():
    """单引号作为特殊字符被接受"""
    pw = "Aa1'"
    assert validate_password_strength(pw) == pw


def test_space_as_special_char():
    """空格算特殊字符"""
    pw = "Aa1 "
    assert validate_password_strength(pw) == pw


def test_tab_as_special_char():
    """Tab 算特殊字符"""
    pw = "Aa1\t"
    assert validate_password_strength(pw) == pw


def test_tilde_accepted():
    """波浪号被接受"""
    pw = "Aa1~"
    assert validate_password_strength(pw) == pw


def test_grave_accent_accepted():
    """反引号被接受"""
    pw = "Aa1`"
    assert validate_password_strength(pw) == pw


# ═══════════════════════════════════════════════════════
# 4. Unicode 字符处理
# ═══════════════════════════════════════════════════════


def test_chinese_chars_as_lowercase():
    """中文字符不算大写也不算小写（不匹配 [A-Z] 和 [a-z]）"""
    # 纯中文 + 数字 + 特殊 = 缺大写和小写
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("密码1!")


def test_unicode_with_all_ascii_classes():
    """包含中文但四类 ASCII 字符都齐全时通过"""
    pw = "Aa1!密码"
    assert validate_password_strength(pw) == pw


def test_emoji_with_all_ascii_classes():
    """包含 emoji 但四类 ASCII 字符都齐全时通过"""
    pw = "Aa1!🔒"
    assert validate_password_strength(pw) == pw


def test_japanese_chars_with_all_classes():
    """日文字符不干扰四类检查"""
    pw = "Aa1!テスト"
    assert validate_password_strength(pw) == pw


def test_mixed_script_password():
    """混合文字系统正常工作"""
    pw = "Aa1!中文テスト한글"
    assert validate_password_strength(pw) == pw


# ═══════════════════════════════════════════════════════
# 5. 长度边界
# ═══════════════════════════════════════════════════════


def test_very_long_password():
    """1000 字符密码正常通过"""
    pw = "Aa1!" + "x" * 996
    assert validate_password_strength(pw) == pw


def test_10000_char_password():
    """10000 字符密码正常通过"""
    pw = "Aa1!" + "y" * 9996
    assert validate_password_strength(pw) == pw


def test_exactly_4_chars_passes():
    """恰好 4 字符且满足四类"""
    assert validate_password_strength("Zz9@") == "Zz9@"


# ═══════════════════════════════════════════════════════
# 6. 返回值不变性
# ═══════════════════════════════════════════════════════


def test_returns_exact_input_string():
    """返回值是输入值的同一字符串"""
    pw = "MyStr0ng!Pass#2026"
    result = validate_password_strength(pw)
    assert result is pw


def test_returns_not_stripped():
    """返回值不做 strip"""
    pw = "Aa1! "
    result = validate_password_strength(pw)
    assert result == "Aa1! "


def test_returns_not_lowered():
    """返回值不做小写转换"""
    pw = "AbCd1234!"
    result = validate_password_strength(pw)
    assert result == "AbCd1234!"


# ═══════════════════════════════════════════════════════
# 7. 完整黑名单遍历
# ═══════════════════════════════════════════════════════


def test_blacklist_is_frozenset():
    """_WEAK_PASSWORDS 是 frozenset"""
    assert isinstance(_WEAK_PASSWORDS, frozenset)


def test_blacklist_size():
    """黑名单大小 >= 50"""
    assert len(_WEAK_PASSWORDS) >= 50


def test_all_blacklist_entries_are_lowercase_strings():
    """黑名单中所有条目是小写字符串"""
    for pw in _WEAK_PASSWORDS:
        assert isinstance(pw, str)
        assert pw == pw.lower(), f"黑名单条目不是小写: {pw!r}"


def test_all_blacklist_entries_nonempty():
    """黑名单中没有空字符串"""
    for pw in _WEAK_PASSWORDS:
        assert len(pw) > 0


def test_blacklist_entries_satisfying_four_classes_are_rejected():
    """黑名单中满足四类字符的条目会被拒绝"""
    # P@ssw0rd 满足四类：大写P + 小写assw + 数字0 + 特殊@
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd")


def test_blacklist_case_insensitive_upper():
    """黑名单大写匹配 — P@SSW0RD 全大写非字母部分不变"""
    # P@SSW0RD: P(upper) 但缺少小写字母 → 先失败在小写规则
    # 用 P@ssw0RD 测试大小写不敏感：四类都满足，lower 匹配黑名单
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0RD")


def test_blacklist_case_insensitive_mixed():
    """黑名单混合大小写匹配"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("p@ssW0rd")


def test_blacklist_does_not_match_similar():
    """相似但非黑名单密码不被拒绝（仅因黑名单）"""
    # "P@ssw0rd2" 不在黑名单中（黑名单只有 p@ssw0rd）
    # 需要确认是否在黑名单
    if "p@ssw0rd2" not in _WEAK_PASSWORDS:
        assert validate_password_strength("P@ssw0rd2") == "P@ssw0rd2"


def test_blacklist_no_duplicates():
    """黑名单无重复条目（frozenset 天然去重）"""
    assert len(_WEAK_PASSWORDS) == len(set(_WEAK_PASSWORDS))


# ═══════════════════════════════════════════════════════
# 8. 特定黑名单条目验证（抽查满足四类的条目）
# ═══════════════════════════════════════════════════════


def test_weak_password_in_blacklist():
    """password 在黑名单中"""
    assert "password" in _WEAK_PASSWORDS


def test_weak_password123_in_blacklist():
    """password123 在黑名单中"""
    assert "password123" in _WEAK_PASSWORDS


def test_weak_admin123_in_blacklist():
    """admin123 在黑名单中"""
    assert "admin123" in _WEAK_PASSWORDS


def test_weak_123456_in_blacklist():
    """123456 在黑名单中"""
    assert "123456" in _WEAK_PASSWORDS


def test_weak_qwerty123_in_blacklist():
    """qwerty123 在黑名单中"""
    assert "qwerty123" in _WEAK_PASSWORDS


def test_weak_p_at_ss_w0rd_in_blacklist():
    """p@ssw0rd 在黑名单中"""
    assert "p@ssw0rd" in _WEAK_PASSWORDS


def test_weak_p_at_ssword_in_blacklist():
    """p@ssword 在黑名单中"""
    assert "p@ssword" in _WEAK_PASSWORDS


def test_weak_p_at_ssw0rd_bang_in_blacklist():
    """p@ssw0rd! 在黑名单中"""
    assert "p@ssw0rd!" in _WEAK_PASSWORDS


def test_weak_password_bang_in_blacklist():
    """password! 在黑名单中"""
    assert "password!" in _WEAK_PASSWORDS


def test_weak_qwer1234_in_blacklist():
    """qwer1234 在黑名单中"""
    assert "qwer1234" in _WEAK_PASSWORDS


# ═══════════════════════════════════════════════════════
# 9. 黑名单中满足四类字符的密码被正确拦截
# ═══════════════════════════════════════════════════════


def _satisfies_four_classes(pw: str) -> bool:
    """检查密码是否同时包含大写、小写、数字、特殊字符"""
    import re

    return bool(
        re.search(r"[A-Z]", pw)
        and re.search(r"[a-z]", pw)
        and re.search(r"\d", pw)
        and re.search(r"[^a-zA-Z0-9]", pw)
    )


def test_blacklist_four_class_entries_caught():
    """黑名单中满足四类的条目全部被拦截（大写首字母版本）"""
    caught = 0
    for pw in _WEAK_PASSWORDS:
        # 给黑名单条目加大写首字母
        test_pw = pw[0].upper() + pw[1:] if pw else pw
        if _satisfies_four_classes(test_pw):
            with pytest.raises(ValueError, match="常见"):
                validate_password_strength(test_pw)
            caught += 1
    # 至少 p@ssw0rd / p@ssw0rd! 满足四类
    assert caught >= 2


def test_blacklist_entries_without_four_classes_fail_earlier():
    """黑名单中不满足四类的条目在字符类检查阶段就失败"""
    for pw in _WEAK_PASSWORDS:
        test_pw = pw[0].upper() + pw[1:] if pw else pw
        if not _satisfies_four_classes(test_pw):
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(test_pw)
            # 不应命中黑名单消息
            assert "常见" not in str(exc_info.value)


# ═══════════════════════════════════════════════════════
# 10. 错误消息文本验证
# ═══════════════════════════════════════════════════════


def test_error_message_uppercase():
    """大写字母错误消息文本"""
    with pytest.raises(ValueError, match="密码必须包含至少一个大写字母"):
        validate_password_strength("aa1!")


def test_error_message_lowercase():
    """小写字母错误消息文本"""
    with pytest.raises(ValueError, match="密码必须包含至少一个小写字母"):
        validate_password_strength("AA1!")


def test_error_message_digit():
    """数字错误消息文本"""
    with pytest.raises(ValueError, match="密码必须包含至少一个数字"):
        validate_password_strength("Aa!!")


def test_error_message_special():
    """特殊字符错误消息文本"""
    with pytest.raises(ValueError, match="密码必须包含至少一个特殊字符"):
        validate_password_strength("Aa11")


def test_error_message_weak():
    """弱密码错误消息文本"""
    with pytest.raises(ValueError, match="密码过于常见，请使用更强的密码"):
        validate_password_strength("P@ssw0rd")


# ═══════════════════════════════════════════════════════
# 11. 大写/小写字母全面覆盖
# ═══════════════════════════════════════════════════════


@pytest.mark.parametrize("upper", list(string.ascii_uppercase))
def test_each_uppercase_letter_accepted(upper):
    """每个大写字母都能满足大写规则"""
    pw = f"{upper}a1!"
    assert validate_password_strength(pw) == pw


@pytest.mark.parametrize("lower", list(string.ascii_lowercase))
def test_each_lowercase_letter_accepted(lower):
    """每个小写字母都能满足小写规则"""
    pw = f"A{lower}1!"
    assert validate_password_strength(pw) == pw


@pytest.mark.parametrize("digit", list(string.digits))
def test_each_digit_accepted(digit):
    """每个数字都能满足数字规则"""
    pw = f"Aa{digit}!"
    assert validate_password_strength(pw) == pw


# ═══════════════════════════════════════════════════════
# 12. 仅包含单类字符的密码
# ═══════════════════════════════════════════════════════


def test_only_uppercase():
    """纯大写密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("ABCDEF")


def test_only_lowercase():
    """纯小写密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("abcdef")


def test_only_digits():
    """纯数字密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("123456")


def test_only_special():
    """纯特殊字符密码失败"""
    with pytest.raises(ValueError):
        validate_password_strength("!@#$%^")


def test_upper_and_lower_only():
    """只有大小写字母失败"""
    with pytest.raises(ValueError, match="数字"):
        validate_password_strength("AbCdEf")


def test_upper_lower_digit_only():
    """大写+小写+数字但无特殊字符失败"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("Abc123")


# ═══════════════════════════════════════════════════════
# 13. 重复特殊字符
# ═══════════════════════════════════════════════════════


def test_multiple_same_special_chars():
    """多个相同特殊字符"""
    pw = "Aa1!!!"
    assert validate_password_strength(pw) == pw


def test_all_special_chars_different():
    """多个不同特殊字符"""
    pw = "Aa1!@#$"
    assert validate_password_strength(pw) == pw


# ═══════════════════════════════════════════════════════
# 14. 黑名单对比大小写验证
# ═══════════════════════════════════════════════════════


def test_password_all_lowercase_in_blacklist():
    """password 全小写在黑名单中"""
    assert "password" in _WEAK_PASSWORDS


def test_password_upper_not_in_blacklist():
    """PASSWORD 全大写不在黑名单中（黑名单都是小写）"""
    assert "PASSWORD" not in _WEAK_PASSWORDS


def test_password_mixed_not_in_blacklist():
    """Password 混合大小写不在黑名单中"""
    assert "Password" not in _WEAK_PASSWORDS


def test_but_lowered_matches_blacklist():
    """Password.lower() 匹配黑名单"""
    assert "Password".lower() in _WEAK_PASSWORDS
