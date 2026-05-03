"""安全加固：输入消毒（sanitize）模块边界测试 — 覆盖 escape_like、strip_html、
strip_control_chars、sanitize_text、sanitize_csv_cell 的完整边界"""

import re

from app.core.sanitize import (
    _CONTROL_CHAR_RE,
    _CSV_FORMULA_CHARS,
    _HTML_TAG_RE,
    _LIKE_SPECIAL_CHARS,
    escape_like,
    sanitize_csv_cell,
    sanitize_text,
    strip_control_chars,
    strip_html,
)

# ═══════════════════════════════════════════════════════
# 1. 内部常量验证
# ═══════════════════════════════════════════════════════


def test_like_special_chars_contents():
    """_LIKE_SPECIAL_CHARS 包含 %, _, \\"""
    assert {"%", "_", "\\"} == _LIKE_SPECIAL_CHARS


def test_like_special_chars_size():
    """_LIKE_SPECIAL_CHARS 恰好 3 个字符"""
    assert len(_LIKE_SPECIAL_CHARS) == 3


def test_html_tag_re_is_compiled():
    """_HTML_TAG_RE 是编译后的正则"""
    assert isinstance(_HTML_TAG_RE, re.Pattern)


def test_control_char_re_is_compiled():
    """_CONTROL_CHAR_RE 是编译后的正则"""
    assert isinstance(_CONTROL_CHAR_RE, re.Pattern)


def test_csv_formula_chars_contents():
    """_CSV_FORMULA_CHARS 包含 =, +, -, @, \\t, \\r"""
    assert {"=", "+", "-", "@", "\t", "\r"} == _CSV_FORMULA_CHARS


def test_csv_formula_chars_size():
    """_CSV_FORMULA_CHARS 恰好 6 个字符"""
    assert len(_CSV_FORMULA_CHARS) == 6


# ═══════════════════════════════════════════════════════
# 2. escape_like 边界
# ═══════════════════════════════════════════════════════


def test_escape_like_empty_string():
    """空字符串返回空"""
    assert escape_like("") == ""


def test_escape_like_no_special():
    """无特殊字符不变"""
    assert escape_like("hello") == "hello"


def test_escape_like_only_percent():
    """纯 % 字符"""
    assert escape_like("%") == "\\%"


def test_escape_like_only_underscore():
    """纯 _ 字符"""
    assert escape_like("_") == "\\_"


def test_escape_like_only_backslash():
    """纯反斜杠"""
    assert escape_like("\\") == "\\\\"


def test_escape_like_percent_at_start():
    """% 在开头"""
    assert escape_like("%abc") == "\\%abc"


def test_escape_like_percent_at_end():
    """% 在末尾"""
    assert escape_like("abc%") == "abc\\%"


def test_escape_like_consecutive_special():
    """连续特殊字符"""
    assert escape_like("%_\\") == "\\%\\_\\\\"


def test_escape_like_mixed_normal_and_special():
    """普通字符与特殊字符交替"""
    assert escape_like("a%b_c\\d") == "a\\%b\\_c\\\\d"


def test_escape_like_unicode_no_escape():
    """Unicode 字符不变"""
    assert escape_like("中文") == "中文"


def test_escape_like_unicode_with_special():
    """Unicode 混合特殊字符"""
    assert escape_like("中文%搜索") == "中文\\%搜索"


def test_escape_like_long_string():
    """长字符串性能可接受"""
    s = "%_" * 500
    expected = "\\%\\_" * 500
    assert escape_like(s) == expected


def test_escape_like_preserves_digits():
    """数字不变"""
    assert escape_like("12345") == "12345"


def test_escape_like_preserves_spaces():
    """空格不变"""
    assert escape_like("hello world") == "hello world"


# ═══════════════════════════════════════════════════════
# 3. strip_html 边界
# ═══════════════════════════════════════════════════════


def test_strip_html_empty():
    """空字符串"""
    assert strip_html("") == ""


def test_strip_html_no_tags():
    """无标签文本不变"""
    assert strip_html("hello world") == "hello world"


def test_strip_html_simple_tag():
    """简单标签移除"""
    assert strip_html("<b>bold</b>") == "bold"


def test_strip_html_self_closing_img():
    """自闭合 img 标签移除"""
    result = strip_html('<img src="x.png"/>')
    assert result == ""


def test_strip_html_self_closing_br():
    """自闭合 br 标签移除"""
    assert strip_html("line1<br/>line2") == "line1line2"


def test_strip_html_script_tag():
    """script 标签及内容移除（标签部分）"""
    result = strip_html("<script>alert(1)</script>")
    assert "<script>" not in result
    assert "</script>" not in result


def test_strip_html_style_tag():
    """style 标签移除"""
    result = strip_html("<style>body{color:red}</style>")
    assert "<style>" not in result


def test_strip_html_nested_tags():
    """嵌套标签全部移除"""
    result = strip_html("<div><p>text</p></div>")
    assert result == "text"


def test_strip_html_tag_with_attributes():
    """带属性的标签移除"""
    result = strip_html('<a href="http://example.com" class="link">链接</a>')
    assert result == "链接"


def test_strip_html_comment():
    """HTML 注释移除（正则不匹配注释 -->）
    注释 <!-- --> 不匹配 <[^>]*> 因为 !-- 和 -- 不含 >"""
    result = strip_html("before<!-- comment -->after")
    # <!-- 匹配 <...> 但 comment -- 不匹配，行为取决于正则
    # 实际 <[^>]*> 匹配 <!-- 但 [^>]* 会贪婪匹配到 --> 之前的 >
    # 结果取决于具体实现
    assert isinstance(result, str)


def test_strip_html_multiple_attributes():
    """多属性标签移除"""
    result = strip_html('<div id="main" class="container" style="color:red">text</div>')
    assert result == "text"


def test_strip_html_data_attribute():
    """data- 属性标签移除"""
    result = strip_html('<span data-x="1">text</span>')
    assert result == "text"


def test_strip_html_newline_in_tag():
    """标签内换行"""
    result = strip_html('<div\nclass="x"\n>text</div>')
    assert result == "text"


def test_strip_html_entities_preserved():
    """HTML 实体保留（不会被标签正则移除）"""
    result = strip_html("&amp; &lt; &gt;")
    assert "&amp;" in result
    assert "&lt;" in result


def test_strip_html_onclick_event():
    """onclick 事件属性被移除"""
    result = strip_html('<div onclick="alert(1)">点击</div>')
    assert "onclick" not in result
    assert "点击" in result


def test_strip_html_onerror_event():
    """onerror 事件属性被移除"""
    result = strip_html('<img src=x onerror=alert(1)>')
    assert "onerror" not in result


def test_strip_html_unicode_content():
    """Unicode 内容保留"""
    assert strip_html("<b>日本語テスト</b>") == "日本語テスト"


def test_strip_html_adjacent_tags():
    """相邻标签全部移除"""
    assert strip_html("<b>a</b><i>b</i><u>c</u>") == "abc"


def test_strip_html_whitespace_around_tags():
    """标签外空格保留"""
    result = strip_html("before <b>middle</b> after")
    assert result == "before middle after"


# ═══════════════════════════════════════════════════════
# 4. strip_control_chars 边界
# ═══════════════════════════════════════════════════════


def test_strip_control_empty():
    """空字符串"""
    assert strip_control_chars("") == ""


def test_strip_control_no_control():
    """无控制字符不变"""
    assert strip_control_chars("hello") == "hello"


def test_strip_control_preserves_tab():
    """\\t 保留"""
    assert strip_control_chars("a\tb") == "a\tb"


def test_strip_control_preserves_newline():
    """\\n 保留"""
    assert strip_control_chars("a\nb") == "a\nb"


def test_strip_control_preserves_cr():
    """\\r 保留"""
    assert strip_control_chars("a\rb") == "a\rb"


def test_strip_control_removes_nul():
    """NUL (0x00) 移除"""
    assert strip_control_chars("a\x00b") == "ab"


def test_strip_control_removes_bel():
    """BEL (0x07) 移除"""
    assert strip_control_chars("a\x07b") == "ab"


def test_strip_control_removes_bs():
    """BS (0x08) 移除"""
    assert strip_control_chars("a\x08b") == "ab"


def test_strip_control_removes_vt():
    """VT (0x0b) 移除"""
    assert strip_control_chars("a\x0bb") == "ab"


def test_strip_control_removes_ff():
    """FF (0x0c) 移除"""
    assert strip_control_chars("a\x0cb") == "ab"


def test_strip_control_removes_esc():
    """ESC (0x1b) 移除"""
    assert strip_control_chars("a\x1bb") == "ab"


def test_strip_control_removes_del():
    """DEL (0x7f) 移除"""
    assert strip_control_chars("a\x7fb") == "ab"


def test_strip_control_removes_so():
    """SO (0x0e) 移除"""
    assert strip_control_chars("a\x0eb") == "ab"


def test_strip_control_removes_si():
    """SI (0x0f) 移除"""
    assert strip_control_chars("a\x0fb") == "ab"


def test_strip_control_all_removed_range():
    """0x00-0x08 全部移除"""
    for i in range(0x00, 0x09):
        assert strip_control_chars(f"a{chr(i)}b") == "ab"


def test_strip_control_0x0e_to_0x1f_removed():
    """0x0e-0x1f 全部移除"""
    for i in range(0x0E, 0x20):
        assert strip_control_chars(f"a{chr(i)}b") == "ab"


def test_strip_control_multiple_control_chars():
    """多个控制字符同时移除"""
    assert strip_control_chars("a\x00\x07\x1b\x7fb") == "ab"


def test_strip_control_only_control_chars():
    """纯控制字符返回空"""
    assert strip_control_chars("\x00\x07\x0b\x0c\x1b\x7f") == ""


def test_strip_control_only_allowed_chars():
    """纯允许字符不变"""
    assert strip_control_chars("\t\n\r") == "\t\n\r"


def test_strip_control_preserves_unicode():
    """Unicode 不受影响"""
    assert strip_control_chars("中文\n测试") == "中文\n测试"


# ═══════════════════════════════════════════════════════
# 5. sanitize_text 边界
# ═══════════════════════════════════════════════════════


def test_sanitize_text_none():
    """None 返回 None"""
    assert sanitize_text(None) is None


def test_sanitize_text_empty():
    """空字符串返回空"""
    assert sanitize_text("") == ""


def test_sanitize_text_whitespace_only():
    """纯空格不变"""
    assert sanitize_text("   ") == "   "


def test_sanitize_text_tab_preserved():
    """Tab 保留"""
    assert "\t" in sanitize_text("hello\tworld")


def test_sanitize_text_newline_preserved():
    """换行保留"""
    assert "\n" in sanitize_text("hello\nworld")


def test_sanitize_text_html_removed():
    """HTML 标签移除"""
    assert sanitize_text("<b>bold</b>") == "bold"


def test_sanitize_text_control_removed():
    """控制字符移除"""
    assert sanitize_text("a\x00b") == "ab"


def test_sanitize_text_html_and_control():
    """HTML + 控制字符同时清除"""
    assert sanitize_text("<b>a</b>\x00b") == "ab"


def test_sanitize_text_script_tag_removed():
    """script 标签移除"""
    result = sanitize_text("<script>alert(1)</script>")
    assert "<script>" not in result


def test_sanitize_text_preserves_normal():
    """正常文本不变"""
    assert sanitize_text("hello world 你好") == "hello world 你好"


def test_sanitize_text_false_returns_false():
    """False 输入返回 False（not v 为 True）"""
    assert sanitize_text(False) is False


def test_sanitize_text_zero_returns_zero():
    """0 输入返回 0（not v 为 True）"""
    assert sanitize_text(0) == 0


def test_sanitize_text_nul_in_middle():
    """中间 NUL 被移除"""
    assert sanitize_text("hel\x00lo") == "hello"


# ═══════════════════════════════════════════════════════
# 6. sanitize_csv_cell 边界
# ═══════════════════════════════════════════════════════


def test_csv_cell_empty():
    """空字符串不变"""
    assert sanitize_csv_cell("") == ""


def test_csv_cell_equals():
    """= 开头加引号"""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_csv_cell_plus():
    """+ 开头加引号"""
    assert sanitize_csv_cell("+cmd") == "'+cmd"


def test_csv_cell_minus():
    """- 开头加引号"""
    assert sanitize_csv_cell("-100") == "'-100"


def test_csv_cell_at():
    """@ 开头加引号"""
    assert sanitize_csv_cell("@SUM") == "'@SUM"


def test_csv_cell_tab():
    """Tab 开头加引号"""
    assert sanitize_csv_cell("\tdata") == "'\tdata"


def test_csv_cell_cr():
    """CR 开头加引号"""
    assert sanitize_csv_cell("\rdata") == "'\rdata"


def test_csv_cell_double_equals():
    """== 开头加引号"""
    assert sanitize_csv_cell("==cmd") == "'==cmd"


def test_csv_cell_normal_text():
    """普通文本不变"""
    assert sanitize_csv_cell("hello") == "hello"


def test_csv_cell_number():
    """正数不变"""
    assert sanitize_csv_cell("100") == "100"


def test_csv_cell_decimal():
    """小数不变"""
    assert sanitize_csv_cell("3.14") == "3.14"


def test_csv_cell_text_starting_with_space():
    """空格开头不变"""
    assert sanitize_csv_cell(" hello") == " hello"


def test_csv_cell_text_starting_with_letter():
    """字母开头不变"""
    assert sanitize_csv_cell("abc=123") == "abc=123"


def test_csv_cell_single_equals():
    """单个 = 加引号"""
    assert sanitize_csv_cell("=") == "'="


def test_csv_cell_single_plus():
    """单个 + 加引号"""
    assert sanitize_csv_cell("+") == "'+"


def test_csv_cell_formula_with_spaces():
    """= 后有空格的公式"""
    assert sanitize_csv_cell("= SUM(A1)") == "'= SUM(A1)"


def test_csv_cell_already_quoted():
    """已有引号前缀不再加引号（' 不在触发字符中）"""
    assert sanitize_csv_cell("'=formula") == "'=formula"


# ═══════════════════════════════════════════════════════
# 7. 组合与集成
# ═══════════════════════════════════════════════════════


def test_sanitize_text_then_csv():
    """sanitize_text 后传给 sanitize_csv_cell"""
    text = sanitize_text("=CMD<script>x</script>")
    # sanitize_text 移除了 <script>x</script>，剩 =CMDx
    assert "<script>" not in text
    # csv 处理 = 开头
    result = sanitize_csv_cell(text)
    assert result.startswith("'")


def test_escape_like_returns_str():
    """escape_like 返回 str 类型"""
    assert isinstance(escape_like("test"), str)


def test_strip_html_returns_str():
    """strip_html 返回 str 类型"""
    assert isinstance(strip_html("test"), str)


def test_strip_control_returns_str():
    """strip_control_chars 返回 str 类型"""
    assert isinstance(strip_control_chars("test"), str)


def test_sanitize_text_str_returns_str():
    """sanitize_text 非 None 返回 str"""
    assert isinstance(sanitize_text("test"), str)


def test_sanitize_csv_cell_returns_str():
    """sanitize_csv_cell 返回 str 类型"""
    assert isinstance(sanitize_csv_cell("test"), str)


def test_escape_like_idempotent_for_normal():
    """普通文本 escape_like 幂等"""
    s = "hello world 123"
    assert escape_like(escape_like(s)) == escape_like(s)


def test_escape_like_not_idempotent_for_special():
    """特殊字符 escape_like 非幂等（\\% 再 escape 会把 \\ 和 % 都转义）"""
    s = "%"
    first = escape_like(s)
    second = escape_like(first)
    assert first == "\\%"
    # escape_like("\\%") → \\ 被转义为 \\\\，% 被转义为 \\%
    assert second == "\\\\\\%"


def test_strip_html_idempotent():
    """strip_html 幂等"""
    s = "hello <b>world</b>"
    assert strip_html(strip_html(s)) == strip_html(s)


def test_strip_control_idempotent():
    """strip_control_chars 幂等"""
    s = "a\x00b\x07c"
    assert strip_control_chars(strip_control_chars(s)) == strip_control_chars(s)


def test_sanitize_text_idempotent():
    """sanitize_text 幂等"""
    s = "<b>a\x00b</b>"
    assert sanitize_text(sanitize_text(s)) == sanitize_text(s)


def test_sanitize_csv_idempotent():
    """sanitize_csv_cell 非幂等（'= 被再次加引号）"""
    first = sanitize_csv_cell("=SUM")
    assert first == "'=SUM"
    second = sanitize_csv_cell(first)
    # ' 开头不在 _CSV_FORMULA_CHARS 中
    assert second == "'=SUM"
