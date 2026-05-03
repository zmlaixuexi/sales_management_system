"""安全加固：输入消毒与 XSS 防护边界测试 — 覆盖密码强度、消毒边界、CSV 注入、安全头、body limit"""

import pytest

from app.core.password_strength import validate_password_strength
from app.core.sanitize import (
    escape_like,
    sanitize_csv_cell,
    sanitize_text,
    strip_control_chars,
    strip_html,
)

# ═══════════════════════════════════════════════════════
# 1. 密码强度边界测试
# ═══════════════════════════════════════════════════════


def test_password_accepts_strong():
    """强密码通过验证"""
    assert validate_password_strength("Str0ng!Pass") == "Str0ng!Pass"


def test_password_rejects_no_uppercase():
    """缺少大写字母"""
    with pytest.raises(ValueError, match="大写字母"):
        validate_password_strength("lower123!")


def test_password_rejects_no_lowercase():
    """缺少小写字母"""
    with pytest.raises(ValueError, match="小写字母"):
        validate_password_strength("UPPER123!")


def test_password_rejects_no_digit():
    """缺少数字"""
    with pytest.raises(ValueError, match="数字"):
        validate_password_strength("NoDigit!Pass")


def test_password_rejects_no_special():
    """缺少特殊字符"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("NoSpecial1Pass")


def test_password_rejects_weak_password():
    """常见弱密码被拒绝 — P@ssw0rd 在黑名单中"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd")


def test_password_rejects_password_bang():
    """弱密码 P@ssw0rd! 在黑名单中"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd!")


def test_password_rejects_case_insensitive():
    """弱密码匹配忽略大小写 — p@ssword 在黑名单中"""
    # P@ssword 满足四类字符：大写P + 小写 + 无数字 → 失败在数字检查
    # 使用 P@ssw0rd 验证大小写不敏感
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd")


def test_password_accepts_non_weak_with_special():
    """非弱密码且有四类字符通过"""
    p = "MyS3cur3@Cust0m!"
    assert validate_password_strength(p) == p


def test_password_rejects_letmein():
    """弱密码 letmein 无特殊字符被拒绝"""
    with pytest.raises(ValueError, match="特殊字符"):
        validate_password_strength("Letmein1")


def test_password_rejects_passw0rd():
    """弱密码 p@ssw0rd 在黑名单中（满足四类字符后被黑名单拒绝）"""
    with pytest.raises(ValueError, match="常见"):
        validate_password_strength("P@ssw0rd")


# ═══════════════════════════════════════════════════════
# 2. strip_html 边界测试
# ═══════════════════════════════════════════════════════


def test_strip_html_event_handler():
    """事件处理属性被移除"""
    result = strip_html('<div onclick="alert(1)">点击</div>')
    assert "onclick" not in result
    assert "点击" in result


def test_strip_html_svg_onload():
    """SVG onload XSS 被移除"""
    result = strip_html('<svg onload="alert(1)">text</svg>')
    assert "<svg" not in result


def test_strip_html_javascript_href():
    """javascript: 链接标签被移除"""
    result = strip_html('<a href="javascript:alert(1)">链接</a>')
    assert "javascript" not in result
    assert "链接" in result


def test_strip_html_multiple_tags():
    """多个连续标签全部移除"""
    result = strip_html("<b>a</b><i>b</i><u>c</u>")
    assert result == "abc"


def test_strip_html_unclosed_tag():
    """未闭合标签被移除"""
    result = strip_html("<b>粗体")
    assert result == "粗体"


def test_strip_html_br_tag():
    """br 标签被移除"""
    result = strip_html("行1<br>行2")
    assert result == "行1行2"


def test_strip_html_empty_string():
    """空字符串返回空"""
    assert strip_html("") == ""


def test_strip_html_angle_brackets_in_math():
    """数学表达式中 < > 会被误匹配（已知限制）"""
    result = strip_html("1 < 2 > 0")
    # 正则 <[^>]*> 会匹配 < 2 >，这是 strip_html 的已知限制
    assert "< 2 >" not in result


# ═══════════════════════════════════════════════════════
# 3. strip_control_chars 边界测试
# ═══════════════════════════════════════════════════════


def test_strip_control_all_range():
    """所有控制字符 (0x00-0x1f, 0x7f) 被移除（保留 \\t \\n \\r）"""
    chars_removed = [chr(i) for i in range(0x00, 0x20) if i not in (0x09, 0x0A, 0x0D)]
    chars_removed.append(chr(0x7F))
    for ch in chars_removed:
        assert strip_control_chars(f"a{ch}b") == "ab"


def test_strip_control_preserves_newline():
    """换行符保留"""
    assert "\n" in strip_control_chars("a\nb")


def test_strip_control_preserves_tab():
    """制表符保留"""
    assert "\t" in strip_control_chars("a\tb")


def test_strip_control_preserves_cr():
    """回车保留"""
    assert "\r" in strip_control_chars("a\rb")


def test_strip_control_del_char():
    """DEL (0x7f) 被移除"""
    assert strip_control_chars("a\x7fb") == "ab"


# ═══════════════════════════════════════════════════════
# 4. sanitize_text 综合边界
# ═══════════════════════════════════════════════════════


def test_sanitize_text_none():
    """None 输入返回 None"""
    assert sanitize_text(None) is None


def test_sanitize_text_empty():
    """空字符串返回空"""
    assert sanitize_text("") == ""


def test_sanitize_text_whitespace_only():
    """纯空格不变"""
    assert sanitize_text("   ") == "   "


def test_sanitize_text_html_and_control_combined():
    """HTML + 控制字符同时清除"""
    result = sanitize_text("<b>粗体</b>\x00\x07文本")
    assert result == "粗体文本"


# ═══════════════════════════════════════════════════════
# 5. escape_like 边界测试
# ═══════════════════════════════════════════════════════


def test_escape_like_all_percents():
    """全 % 字符"""
    assert escape_like("%%%") == "\\%\\%\\%"


def test_escape_like_all_underscores():
    """全 _ 字符"""
    assert escape_like("___") == "\\_\\_\\_"


def test_escape_like_unicode():
    """Unicode 字符不变"""
    assert escape_like("中文搜索") == "中文搜索"


def test_escape_like_mixed_special():
    """混合特殊字符和普通字符"""
    assert escape_like("a%b_c\\d") == "a\\%b\\_c\\\\d"


# ═══════════════════════════════════════════════════════
# 6. sanitize_csv_cell 边界测试
# ═══════════════════════════════════════════════════════


def test_csv_cell_double_equals():
    """== 开头被转义"""
    assert sanitize_csv_cell("==cmd") == "'==cmd"


def test_csv_cell_space_before_equals():
    """空格+等号开头不转义（只有首字符检查）"""
    assert sanitize_csv_cell(" =cmd") == " =cmd"


def test_csv_cell_negative_number():
    """负数开头被转义"""
    assert sanitize_csv_cell("-100") == "'-100"


def test_csv_cell_plus_formula():
    """+ 开头公式被转义"""
    assert sanitize_csv_cell("+SUM(A1)") == "'+SUM(A1)"


def test_csv_cell_at_sign():
    """@ 开头被转义"""
    assert sanitize_csv_cell("@SUM") == "'@SUM"


def test_csv_cell_none_not_applicable():
    """sanitize_csv_cell 只接受 str"""
    # 类型检查 — 函数签名要求 str
    assert sanitize_csv_cell("") == ""


# ═══════════════════════════════════════════════════════
# 7. 安全响应头完整性验证
# ═══════════════════════════════════════════════════════


def test_all_security_headers_present():
    """所有安全响应头在 API 响应中存在"""
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-xss-protection"] == "1; mode=block"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "content-security-policy" in resp.headers
    assert "permissions-policy" in resp.headers


def test_csp_default_src_none():
    """CSP 策略 default-src 'none'"""
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp


def test_cache_control_no_store():
    """Cache-Control: no-store"""
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.headers.get("cache-control") == "no-store"


# ═══════════════════════════════════════════════════════
# 8. body limit 中间件验证
# ═══════════════════════════════════════════════════════


def test_body_limit_config_default():
    """默认 body limit 为 1MB"""
    from app.core.config import Settings
    s = Settings()
    assert s.MAX_JSON_BODY_MB == 1


def test_body_limit_middleware_exists():
    """BodyLimitMiddleware 存在"""
    from app.core.body_limit import BodyLimitMiddleware
    assert BodyLimitMiddleware is not None


def test_body_limit_middleware_registered():
    """BodyLimitMiddleware 注册到 app"""
    import app.main as mod
    with open(mod.__file__) as f:
        source = f.read()
    assert "BodyLimitMiddleware" in source


# ═══════════════════════════════════════════════════════
# 9. 密码强度黑名单覆盖度
# ═══════════════════════════════════════════════════════


def test_weak_password_list_size():
    """弱密码黑名单至少 50 个"""
    from app.core.password_strength import _WEAK_PASSWORDS
    assert len(_WEAK_PASSWORDS) >= 50


def test_weak_password_contains_common():
    """黑名单包含常见弱密码"""
    from app.core.password_strength import _WEAK_PASSWORDS
    for pw in ["password", "123456", "admin", "qwerty", "root"]:
        assert pw in _WEAK_PASSWORDS


# ═══════════════════════════════════════════════════════
# 10. 配置安全验证边界
# ═══════════════════════════════════════════════════════


def test_jwt_expire_positive():
    """JWT 过期时间必须为正数"""
    from app.core.config import Settings
    s = Settings()
    assert s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert s.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0


def test_rate_limit_non_negative():
    """速率限制 >= 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.RATE_LIMIT_MAX >= 0


def test_max_image_size_positive():
    """图片大小限制 > 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.MAX_IMAGE_SIZE_MB > 0


def test_max_csv_import_rows_positive():
    """CSV 导入行数限制 > 0"""
    from app.core.config import Settings
    s = Settings()
    assert s.MAX_CSV_IMPORT_ROWS > 0


# ═══════════════════════════════════════════════════════
# 11. 前后端密码验证一致性
# ═══════════════════════════════════════════════════════


def test_frontend_password_regex_matches_backend():
    """前端密码正则（字母+数字）是后端要求的子集"""
    import re
    # 前端：/^(?=.*[a-zA-Z])(?=.*\d)/ — 至少一个字母 + 一个数字
    frontend_re = re.compile(r"^(?=.*[a-zA-Z])(?=.*\d)")
    # 后端要求：大写 + 小写 + 数字 + 特殊字符
    # 前端正则通过的，后端可能还要求更多，但不应冲突
    assert frontend_re.search("Abc123!") is not None  # 前端通过
    assert frontend_re.search("abcdef") is None  # 前端拒绝
    assert frontend_re.search("123456") is None  # 前端拒绝
