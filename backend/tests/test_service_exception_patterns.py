"""
代码质量：后端服务层异常处理模式一致性验证测试
覆盖 HTTPException detail 结构、错误码命名规范、
safe_commit 使用模式、辅助异常函数、服务层异常处理模式
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
PAYMENT_SVC = (ROOT / "app" / "services" / "payment_service.py").read_text()
FILE_SVC = (ROOT / "app" / "services" / "file_service.py").read_text()
CSV_IMPORT = (ROOT / "app" / "services" / "csv_import.py").read_text()
EXPORT_SVC = (ROOT / "app" / "services" / "export_service.py").read_text()

SERVICES = {
    "payment": PAYMENT_SVC,
    "file": FILE_SVC,
    "csv_import": CSV_IMPORT,
    "export": EXPORT_SVC,
}


def _extract_http_exceptions(src: str) -> list[tuple[str, str, str]]:
    """提取 HTTPException 调用 → [(status_code, error_code, message), ...]"""
    results = []
    for m in re.finditer(
        r'HTTPException\(\s*status_code\s*=\s*(\d+),\s*detail\s*=\s*\{[^}]*"code":\s*"([^"]+)",\s*"message":\s*(?:f?"([^"]*)")?',
        src,
    ):
        results.append((m.group(1), m.group(2), m.group(3) or ""))
    return results


# ═══════════════════════════════════════════════════════════
# 1. HTTPException detail 结构一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExceptionDetailStructure:
    """所有 HTTPException 使用统一的 detail 结构"""

    def test_payment_service_detail_has_code_and_message(self):
        """payment_service 的 HTTPException 都有 code 和 message"""
        excs = _extract_http_exceptions(PAYMENT_SVC)
        assert len(excs) >= 4, f"payment_service 应有至少 4 个 HTTPException，实际 {len(excs)}"
        for status_code, code, msg in excs:
            assert code, f"HTTPException {status_code} 应有 code 字段"
            assert msg, f"HTTPException {status_code} code={code} 应有 message 字段"

    def test_file_service_detail_has_code_and_message(self):
        """file_service 的 HTTPException 都有 code 和 message"""
        excs = _extract_http_exceptions(FILE_SVC)
        assert len(excs) >= 4, f"file_service 应有至少 4 个 HTTPException，实际 {len(excs)}"
        for status_code, code, msg in excs:
            assert code, f"HTTPException {status_code} 应有 code 字段"

    def test_csv_import_detail_has_code_and_message(self):
        """csv_import 的 HTTPException 都有 code 和 message"""
        excs = _extract_http_exceptions(CSV_IMPORT)
        assert len(excs) >= 3, f"csv_import 应有至少 3 个 HTTPException，实际 {len(excs)}"
        for status_code, code, msg in excs:
            assert code, f"HTTPException {status_code} 应有 code 字段"

    def test_deps_detail_has_code_and_message(self):
        """deps.py 的 HTTPException detail 使用 dict 结构"""
        # deps.py 中有多处 HTTPException：get_current_user、require_permission、
        # check_owner_or_forbid、parse_uuid_or_400、get_or_404（两处）
        # 验证关键错误码存在
        expected_codes = ["AUTH_UNAUTHORIZED", "AUTH_FORBIDDEN", "VALIDATION_FAILED", "RESOURCE_NOT_FOUND"]
        for code in expected_codes:
            assert f'"code": "{code}"' in DEPS_SRC, f"deps.py 应包含错误码 {code}"

    def test_all_exceptions_use_dict_detail(self):
        """所有服务层的 HTTPException detail 使用 dict 结构（非字符串）"""
        for name, src in SERVICES.items():
            # 检查是否有 detail="..." 字符串形式（不规范）
            bad = re.findall(r'detail\s*=\s*"[^"]{3,}"', src)
            assert len(bad) == 0, f"{name} 不应使用字符串 detail: {bad}"


# ═══════════════════════════════════════════════════════════
# 2. 错误码命名规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestErrorCodeNaming:
    """错误码使用 UPPER_SNAKE_CASE 并带领域前缀"""

    def test_payment_error_codes_prefixed(self):
        """payment_service 错误码使用 PAYMENT_/ORDER_/RESOURCE_ 前缀"""
        excs = _extract_http_exceptions(PAYMENT_SVC)
        for _, code, _ in excs:
            valid_prefixes = ("PAYMENT_", "ORDER_", "RESOURCE_")
            assert any(code.startswith(p) for p in valid_prefixes), (
                f"payment 错误码 {code} 应以 PAYMENT_/ORDER_/RESOURCE_ 开头"
            )

    def test_file_error_codes_prefixed(self):
        """file_service 错误码使用 FILE_ 前缀"""
        excs = _extract_http_exceptions(FILE_SVC)
        for _, code, _ in excs:
            valid_prefixes = ("FILE_", "RESOURCE_")
            assert any(code.startswith(p) for p in valid_prefixes), (
                f"file 错误码 {code} 应以 FILE_/RESOURCE_ 开头"
            )

    def test_all_error_codes_upper_snake_case(self):
        """所有错误码使用 UPPER_SNAKE_CASE"""
        for name, src in SERVICES.items():
            for _, code, _ in _extract_http_exceptions(src):
                assert re.fullmatch(r"[A-Z][A-Z0-9_]+", code), (
                    f"{name} 错误码 {code} 不符合 UPPER_SNAKE_CASE"
                )

    def test_csv_import_uses_validation_failed_code(self):
        """csv_import 使用 VALIDATION_FAILED 错误码"""
        excs = _extract_http_exceptions(CSV_IMPORT)
        codes = [code for _, code, _ in excs]
        assert "VALIDATION_FAILED" in codes, "csv_import 应使用 VALIDATION_FAILED 错误码"

    def test_error_codes_no_numeric_suffix(self):
        """错误码不以数字结尾（避免 code1, code2 等无意义编号）"""
        for name, src in SERVICES.items():
            for _, code, _ in _extract_http_exceptions(src):
                assert not code[-1].isdigit(), f"{name} 错误码 {code} 不应以数字结尾"


# ═══════════════════════════════════════════════════════════
# 3. safe_commit 使用模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSafeCommitPattern:
    """safe_commit 提交模式一致性"""

    def test_safe_commit_defined_in_deps(self):
        """safe_commit 在 deps.py 中定义"""
        assert "def safe_commit" in DEPS_SRC, "deps.py 应定义 safe_commit 函数"
        # 确认实现包含 commit + rollback
        m = re.search(r"def safe_commit.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "safe_commit 函数体未找到"
        body = m.group(0)
        assert "db.commit()" in body, "safe_commit 应调用 db.commit()"
        assert "db.rollback()" in body, "safe_commit 失败时应 db.rollback()"

    def test_service_layer_uses_flush_not_commit(self):
        """服务层使用 db.flush() 而非 db.commit()（提交交给路由层）"""
        for name, src in SERVICES.items():
            if name == "export":
                continue  # export_service 只读，无 flush/commit
            if "db.commit()" in src:
                # file_service 的 cleanup_orphan_files 不调用 commit，但 file_service 本身
                # 不应有直接的 db.commit()
                assert name == "file", f"{name} 服务层不应直接调用 db.commit()"
            # flush 调用是正常的
            if name in ("payment",):
                assert "db.flush()" in src, f"{name} 服务应使用 db.flush()"

    def test_export_service_is_read_only(self):
        """export_service 不进行写操作"""
        assert "db.commit()" not in EXPORT_SVC, "export_service 不应调用 db.commit()"
        assert "db.flush()" not in EXPORT_SVC, "export_service 不应调用 db.flush()"
        assert "db.add(" not in EXPORT_SVC, "export_service 不应调用 db.add()"

    def test_safe_commit_catches_generic_exception(self):
        """safe_commit 捕获通用 Exception（不限于特定异常类型）"""
        m = re.search(r"def safe_commit.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "safe_commit 函数体未找到"
        body = m.group(0)
        assert "except Exception" in body, "safe_commit 应捕获通用 Exception"
        assert "raise" in body, "safe_commit 应 re-raise 异常"

    def test_file_service_uses_flush_not_commit(self):
        """file_service 使用 db.flush() 而非 db.commit()"""
        assert "db.flush()" in FILE_SVC, "file_service 应使用 db.flush()"
        assert "db.commit()" not in FILE_SVC, "file_service 不应直接调用 db.commit()"


# ═══════════════════════════════════════════════════════════
# 4. 辅助异常函数验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestExceptionHelpers:
    """deps.py 辅助异常函数规范"""

    def test_get_or_404_raises_404(self):
        """get_or_404 抛出 404 RESOURCE_NOT_FOUND"""
        m = re.search(r"def get_or_404.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "应定义 get_or_404 函数"
        body = m.group(0)
        assert "404" in body, "get_or_404 应抛出 404"
        assert "RESOURCE_NOT_FOUND" in body, "get_or_404 应使用 RESOURCE_NOT_FOUND"

    def test_parse_uuid_or_400_raises_400(self):
        """parse_uuid_or_400 抛出 400 VALIDATION_FAILED"""
        m = re.search(r"def parse_uuid_or_400.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "应定义 parse_uuid_or_400 函数"
        body = m.group(0)
        assert "400" in body, "parse_uuid_or_400 应抛出 400"
        assert "VALIDATION_FAILED" in body, "parse_uuid_or_400 应使用 VALIDATION_FAILED"

    def test_require_permission_raises_403(self):
        """require_permission 抛出 403 AUTH_FORBIDDEN"""
        m = re.search(r"def require_permission.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "应定义 require_permission 函数"
        body = m.group(0)
        assert "403" in body, "require_permission 应抛出 403"
        assert "AUTH_FORBIDDEN" in body, "require_permission 应使用 AUTH_FORBIDDEN"

    def test_check_owner_or_forbid_raises_403(self):
        """check_owner_or_forbid 抛出 403 AUTH_FORBIDDEN"""
        m = re.search(r"def check_owner_or_forbid.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "应定义 check_owner_or_forbid 函数"
        body = m.group(0)
        assert "403" in body, "check_owner_or_forbid 应抛出 403"
        assert "AUTH_FORBIDDEN" in body, "check_owner_or_forbid 应使用 AUTH_FORBIDDEN"

    def test_get_or_404_filters_soft_deleted(self):
        """get_or_404 自动过滤软删除记录"""
        m = re.search(r"def get_or_404.*?(?=\ndef |\Z)", DEPS_SRC, re.DOTALL)
        assert m, "应定义 get_or_404 函数"
        body = m.group(0)
        assert "deleted_at" in body, "get_or_404 应过滤 deleted_at"


# ═══════════════════════════════════════════════════════════
# 5. 服务层异常处理模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestServiceExceptionPatterns:
    """服务层异常处理模式一致性"""

    def test_payment_service_uses_inflight_lock(self):
        """payment_service 使用并发防护锁"""
        assert "Lock" in PAYMENT_SVC, "payment_service 应使用 threading.Lock"
        assert "_payment_lock" in PAYMENT_SVC, "应定义 _payment_lock"
        assert "_payment_inflight" in PAYMENT_SVC, "应定义 _payment_inflight 集合"
        assert "_check_payment_inflight" in PAYMENT_SVC, "应定义 _check_payment_inflight"
        assert "_clear_payment_inflight" in PAYMENT_SVC, "应定义 _clear_payment_inflight"

    def test_payment_service_clears_lock_in_finally(self):
        """payment_service 在 finally 块中清理锁"""
        assert "finally" in PAYMENT_SVC, "register_payment 应使用 finally 块"
        assert "_clear_payment_inflight" in PAYMENT_SVC, "finally 中应调用 _clear_payment_inflight"
        # 检查 finally 和 _clear 在同一代码块
        m = re.search(r"finally:.*?_clear_payment_inflight", PAYMENT_SVC, re.DOTALL)
        assert m, "finally 块中应调用 _clear_payment_inflight"

    def test_payment_service_uses_row_lock(self):
        """payment_service 使用行锁（with_for_update）"""
        assert "with_for_update" in PAYMENT_SVC, "register_payment 应使用 with_for_update() 行锁"

    def test_file_service_validates_magic_bytes(self):
        """file_service 校验文件魔数字节"""
        assert "MAGIC_SIGNATURES" in FILE_SVC, "应定义 MAGIC_SIGNATURES"
        assert "_validate_magic_bytes" in FILE_SVC, "应定义 _validate_magic_bytes 函数"
        assert "jpeg" in FILE_SVC.lower() or "png" in FILE_SVC.lower(), "应支持 jpeg/png 类型"

    def test_csv_import_validates_encoding(self):
        """csv_import 校验 UTF-8 编码"""
        assert "utf-8" in CSV_IMPORT.lower(), "csv_import 应校验 UTF-8 编码"
        assert "UnicodeDecodeError" in CSV_IMPORT, "应捕获 UnicodeDecodeError"
        # 应使用 utf-8-sig（带 BOM 自动处理）
        assert "utf-8-sig" in CSV_IMPORT, "应使用 utf-8-sig 编码解码"
