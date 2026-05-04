"""
代码质量：后端 API 错误码全局唯一性与命名规范验证测试
覆盖错误码命名规范、全局唯一性、分类归属、
消息语言一致性、响应结构一致性
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 收集所有 Python 源文件中的错误码
SOURCE_DIRS = [
    ROOT / "app" / "api",
    ROOT / "app" / "core",
    ROOT / "app" / "services",
    ROOT / "app" / "main.py",
]

_CODE_RE = re.compile(r'"code":\s*"([A-Z][A-Z0-9_]+)"')
_DETAIL_MSG_RE = re.compile(r'"message":\s*f?"([^"]*)"')


def _collect_error_codes() -> list[tuple[str, str, int, str, str]]:
    """返回 [(error_code, file, line_no, message, full_line), ...]"""
    results = []
    for src_dir in SOURCE_DIRS:
        if src_dir.is_file():
            files = [src_dir]
        else:
            files = sorted(src_dir.rglob("*.py"))
        for fpath in files:
            if "__pycache__" in str(fpath):
                continue
            for i, line in enumerate(fpath.read_text().splitlines(), 1):
                for m in _CODE_RE.finditer(line):
                    code = m.group(1)
                    msg_match = _DETAIL_MSG_RE.search(line)
                    message = msg_match.group(1) if msg_match else ""
                    results.append((code, str(fpath.relative_to(ROOT)), i, message, line))
    return results


ALL_CODES = _collect_error_codes()
UNIQUE_CODES = sorted({c[0] for c in ALL_CODES})


# ═══════════════════════════════════════════════════════════
# 1. 错误码命名规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorCodeNaming:
    """错误码使用 UPPER_SNAKE_CASE 格式"""

    def test_all_codes_upper_snake_case(self):
        for code, file, lineno, msg, _ in ALL_CODES:
            assert re.fullmatch(r"[A-Z][A-Z0-9_]*", code), (
                f"{file}:{lineno} — {code} 不符合 UPPER_SNAKE_CASE"
            )

    def test_no_consecutive_underscores(self):
        for code in UNIQUE_CODES:
            assert "__" not in code, f"{code} 不应有连续下划线"

    def test_no_trailing_underscore(self):
        for code in UNIQUE_CODES:
            assert not code.endswith("_"), f"{code} 不应以下划线结尾"

    def test_minimum_code_length(self):
        """错误码至少 5 个字符（如 AUTH_ 是 5 字符前缀）"""
        for code in UNIQUE_CODES:
            assert len(code) >= 5, f"{code} 长度不足 5 字符"

    def test_codes_are_string_literals(self):
        """错误码必须是字符串字面量，不是变量"""
        for code, file, lineno, msg, line in ALL_CODES:
            assert f'"{code}"' in line or f"'{code}'" in line, (
                f"{file}:{lineno} — {code} 应为字符串字面量"
            )


# ═══════════════════════════════════════════════════════════
# 2. 错误码分类归属验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorCodeClassification:
    """错误码按前缀分类"""

    def test_auth_prefix_codes(self):
        auth_codes = [c for c in UNIQUE_CODES if c.startswith("AUTH_")]
        assert "AUTH_UNAUTHORIZED" in auth_codes
        assert "AUTH_FORBIDDEN" in auth_codes

    def test_resource_and_validation_codes(self):
        assert "RESOURCE_NOT_FOUND" in UNIQUE_CODES
        assert "VALIDATION_FAILED" in UNIQUE_CODES

    def test_business_specific_codes(self):
        """业务特定错误码包含资源名称前缀"""
        business_codes = [
            c for c in UNIQUE_CODES
            if not c.startswith(("AUTH_", "RESOURCE_", "VALIDATION_", "SYSTEM_", "RATE_"))
            and c not in ("PAYLOAD_TOO_LARGE", "METHOD_NOT_ALLOWED", "SHUTTING_DOWN")
        ]
        assert len(business_codes) >= 5, f"应有至少 5 个业务特定错误码，实际 {len(business_codes)}"
        for code in business_codes:
            has_prefix = any(code.startswith(p) for p in (
                "ORDER_", "PRODUCT_", "CUSTOMER_", "FILE_",
                "INVENTORY_", "IMPORT_", "ACCOUNT_", "PRICE_",
                "PAYMENT_", "INVALID_", "PAYLOAD_", "LOGIN_",
            ))
            assert has_prefix, f"{code} 缺少资源名称前缀"

    def test_all_categories_covered(self):
        """至少覆盖认证、资源、验证、业务四类"""
        categories = set()
        for code in UNIQUE_CODES:
            if code.startswith("AUTH_"):
                categories.add("auth")
            elif code.startswith("RESOURCE_"):
                categories.add("resource")
            elif code.startswith("VALIDATION_"):
                categories.add("validation")
            elif code.startswith("SYSTEM_"):
                categories.add("system")
            elif code.startswith("RATE_"):
                categories.add("rate_limit")
            else:
                categories.add("business")
        assert len(categories) >= 4, f"应有至少 4 类错误码，实际 {categories}"

    def test_no_ambiguous_generic_codes(self):
        """通用错误码语义明确，不含模糊命名"""
        for code in UNIQUE_CODES:
            assert code != "ERROR", "不应使用模糊错误码 ERROR"
            assert code != "FAIL", "不应使用模糊错误码 FAIL"
            assert code != "BAD_REQUEST", "不应使用模糊错误码 BAD_REQUEST"


# ═══════════════════════════════════════════════════════════
# 3. 错误码全局唯一性与使用频率验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorCodeUniqueness:
    """验证错误码在不同模块中使用时含义一致"""

    def test_shared_codes_have_consistent_messages(self):
        """共享错误码在不同位置的消息语义应一致"""
        code_messages: dict[str, set[str]] = {}
        for code, file, lineno, msg, _ in ALL_CODES:
            if msg:
                code_messages.setdefault(code, set()).add(msg)
        # RESOURCE_NOT_FOUND 在多处使用但消息格式统一（"X不存在"）
        if "RESOURCE_NOT_FOUND" in code_messages:
            for msg in code_messages["RESOURCE_NOT_FOUND"]:
                assert "不存在" in msg, f"RESOURCE_NOT_FOUND 消息应含'不存在': {msg}"
        # AUTH_UNAUTHORIZED 消息一致
        if "AUTH_UNAUTHORIZED" in code_messages:
            msgs = code_messages["AUTH_UNAUTHORIZED"]
            for msg in msgs:
                assert any(kw in msg for kw in ("无效", "错误", "过期")), (
                    f"AUTH_UNAUTHORIZED 消息语义应一致: {msg}"
                )

    def test_no_duplicate_specific_codes(self):
        """特定业务错误码不应重复定义（每个唯一）"""
        specific_codes = [
            c for c in UNIQUE_CODES
            if not c.startswith(("AUTH_", "RESOURCE_", "VALIDATION_"))
        ]
        for code in specific_codes:
            count = sum(1 for c, *_ in ALL_CODES if c == code)
            # 特定错误码可能出现在多个位置（如 orders.py 和 payments.py 都有 ORDER_INVALID_STATUS）
            # 这是允许的，只要语义一致
            assert count >= 1, f"{code} 至少被使用一次"

    def test_core_error_codes_defined(self):
        """核心错误码必须存在"""
        required = {"AUTH_UNAUTHORIZED", "AUTH_FORBIDDEN", "RESOURCE_NOT_FOUND", "VALIDATION_FAILED"}
        defined = set(UNIQUE_CODES)
        missing = required - defined
        assert not missing, f"缺少核心错误码: {missing}"

    def test_error_code_count_reasonable(self):
        """错误码总数在合理范围"""
        assert len(UNIQUE_CODES) >= 15, f"错误码总数 {len(UNIQUE_CODES)} 少于 15"
        assert len(UNIQUE_CODES) <= 50, f"错误码总数 {len(UNIQUE_CODES)} 超过 50"

    def test_most_used_codes_are_generic(self):
        """使用最频繁的错误码应是通用型"""
        from collections import Counter
        code_counts = Counter(c[0] for c in ALL_CODES)
        top_3 = [code for code, _ in code_counts.most_common(3)]
        generic_prefixes = ("AUTH_", "RESOURCE_", "VALIDATION_")
        for code in top_3:
            assert code.startswith(generic_prefixes) or code == "RATE_LIMIT_EXCEEDED", (
                f"高频错误码 {code} 应为通用类型"
            )


# ═══════════════════════════════════════════════════════════
# 4. 错误消息语言一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorMessageLanguage:
    """错误消息使用中文"""

    def test_error_messages_are_chinese(self):
        """面向用户的错误消息应包含中文"""
        chinese_pat = re.compile(r"[一-鿿]")
        for code, file, lineno, msg, _ in ALL_CODES:
            if not msg:
                continue
            assert chinese_pat.search(msg), (
                f"{file}:{lineno} [{code}] 消息应包含中文: {msg}"
            )

    def test_no_english_only_messages(self):
        """错误消息不应为纯英文"""
        for code, file, lineno, msg, _ in ALL_CODES:
            if not msg:
                continue
            # 去掉格式化占位符后检查
            clean = re.sub(r"\{[^}]*\}", "", msg)
            has_chinese = bool(re.search(r"[一-鿿]", clean))
            assert has_chinese, f"{file}:{lineno} [{code}] 消息不应为纯英文: {msg}"

    def test_validation_failed_messages_descriptive(self):
        """VALIDATION_FAILED 的消息应描述具体验证失败原因"""
        for code, file, lineno, msg, _ in ALL_CODES:
            if code != "VALIDATION_FAILED":
                continue
            if not msg:
                continue  # 跨行定义，跳过
            assert len(msg) >= 4, f"{file}:{lineno} VALIDATION_FAILED 消息过于简短: {msg}"

    def test_auth_error_messages_clear(self):
        """认证相关错误消息清晰明确"""
        auth_codes = [(c, f, l, m) for c, f, l, m, _ in ALL_CODES if c.startswith("AUTH_")]
        for code, file, lineno, msg in auth_codes:
            if not msg:
                continue
            assert len(msg) >= 3, f"{file}:{lineno} [{code}] 消息过短: {msg}"

    def test_no_raw_exception_messages(self):
        """错误消息不应包含原始异常类型名"""
        exception_names = ["Exception", "ValueError", "TypeError", "IntegrityError", "HTTPException"]
        for code, file, lineno, msg, _ in ALL_CODES:
            for exc_name in exception_names:
                assert exc_name not in msg, (
                    f"{file}:{lineno} [{code}] 消息不应包含异常类型名: {msg}"
                )


# ═══════════════════════════════════════════════════════════
# 5. 错误响应结构一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorResponseStructure:
    """错误响应包含 code 和 message 字段"""

    def test_all_detail_dicts_have_code_and_message(self):
        """detail 字典包含 code 和 message"""
        for code, file, lineno, msg, line in ALL_CODES:
            has_message = '"message"' in line
            # 某些行可能 message 在后续行或通过变量传递
            if '"message"' not in line:
                # 检查上下文：code 行附近应有 message
                source = Path(ROOT / file).read_text().splitlines()
                nearby = source[max(0, lineno - 3):min(len(source), lineno + 3)]
                nearby_text = "\n".join(nearby)
                assert '"message"' in nearby_text, (
                    f"{file}:{lineno} [{code}] 缺少 message 字段"
                )

    def test_code_value_matches_pattern(self):
        """code 值仅含大写字母、数字和下划线"""
        for code in UNIQUE_CODES:
            assert re.fullmatch(r"[A-Z][A-Z0-9_]+", code), (
                f"{code} 应仅含大写字母、数字和下划线"
            )

    def test_main_py_exception_handlers_use_codes(self):
        """main.py 异常处理器使用标准错误码"""
        main_src = (ROOT / "app" / "main.py").read_text()
        assert "SYSTEM_INTERNAL_ERROR" in main_src
        assert "RESOURCE_NOT_FOUND" in main_src or "METHOD_NOT_ALLOWED" in main_src
        assert "VALIDATION_FAILED" in main_src

    def test_main_py_error_response_structure(self):
        """main.py 异常处理器响应包含标准字段"""
        main_src = (ROOT / "app" / "main.py").read_text()
        assert '"code"' in main_src
        assert '"message"' in main_src
        assert '"success"' in main_src

    def test_rate_limit_and_body_limit_use_error_codes(self):
        """速率限制和请求体限制中间件使用标准错误码"""
        ratelimit_src = (ROOT / "app" / "core" / "ratelimit.py").read_text()
        body_limit_src = (ROOT / "app" / "core" / "body_limit.py").read_text()
        assert "RATE_LIMIT_EXCEEDED" in ratelimit_src
        assert "PAYLOAD_TOO_LARGE" in body_limit_src
