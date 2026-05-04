"""代码质量：后端异常处理器覆盖完整性验证测试
覆盖 HTTPException 处理器、Starlette 异常处理器、
RequestValidationError 处理器、全局未处理异常、响应结构一致性"""

import re
from pathlib import Path

MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"


def _read(path: Path) -> str:
    return path.read_text()


def _find_function_body(source: str, func_name: str) -> str:
    pattern = re.compile(rf"(?:async )?def {func_name}\b")
    match = pattern.search(source)
    if not match:
        return ""
    start = match.start()
    lines = source[start:].split("\n")
    body_lines = [lines[0]]
    indent = len(lines[0]) - len(lines[0].lstrip())
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped and (len(line) - len(stripped)) <= indent:
            if stripped.startswith(("def ", "async def ", "class ", "@")):
                break
        body_lines.append(line)
    return "\n".join(body_lines)


# ═══════════════════════════════════════════════════════════
# 1. HTTPException 处理器验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHTTPExceptionHandler:
    """验证 HTTPException 处理器"""

    def test_handler_registered(self):
        source = _read(MAIN_FILE)
        assert '@app.exception_handler(HTTPException)' in source

    def test_extracts_code_and_message_from_dict_detail(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "http_exception_handler")
        assert 'isinstance(detail, dict)' in body
        assert 'detail.get("code"' in body
        assert 'detail.get("message"' in body

    def test_fallback_for_non_dict_detail(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "http_exception_handler")
        assert "SYSTEM_INTERNAL_ERROR" in body
        assert "str(detail)" in body

    def test_includes_request_id(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "http_exception_handler")
        assert "request_id_ctx" in body
        assert '"request_id"' in body

    def test_returns_json_response_with_status_code(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "http_exception_handler")
        assert "JSONResponse" in body
        assert "exc.status_code" in body


# ═══════════════════════════════════════════════════════════
# 2. Starlette 异常处理器验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestStarletteExceptionHandler:
    """验证 Starlette 路由异常处理器"""

    def test_handler_registered(self):
        source = _read(MAIN_FILE)
        assert '@app.exception_handler(StarletteHTTPException)' in source

    def test_maps_404_to_resource_not_found(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "starlette_exception_handler")
        assert "RESOURCE_NOT_FOUND" in body
        assert "404" in body

    def test_maps_405_to_method_not_allowed(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "starlette_exception_handler")
        assert "METHOD_NOT_ALLOWED" in body

    def test_includes_request_id(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "starlette_exception_handler")
        assert "request_id_ctx" in body

    def test_returns_json_response(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "starlette_exception_handler")
        assert "JSONResponse" in body
        assert "success" in body


# ═══════════════════════════════════════════════════════════
# 3. RequestValidationError 处理器验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestValidationErrorHandler:
    """验证 Pydantic 校验错误处理器"""

    def test_handler_registered(self):
        source = _read(MAIN_FILE)
        assert '@app.exception_handler(RequestValidationError)' in source

    def test_uses_code_validation_failed(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "validation_exception_handler")
        assert "VALIDATION_FAILED" in body

    def test_formats_field_location_with_arrow(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "validation_exception_handler")
        assert '" → "' in body or '"→"' in body
        assert "loc" in body

    def test_returns_422_status_code(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "validation_exception_handler")
        assert "422" in body
        assert "JSONResponse" in body

    def test_includes_request_id(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "validation_exception_handler")
        assert "request_id_ctx" in body


# ═══════════════════════════════════════════════════════════
# 4. 全局未处理异常验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestUnhandledExceptionHandler:
    """验证全局未处理异常处理器"""

    def test_handler_registered_for_base_exception(self):
        source = _read(MAIN_FILE)
        assert '@app.exception_handler(Exception)' in source

    def test_returns_500_status_code(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "unhandled_exception_handler")
        assert "500" in body
        assert "JSONResponse" in body

    def test_does_not_leak_internal_error_details(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "unhandled_exception_handler")
        assert "服务器内部错误" in body
        # 不应返回 exc 信息
        assert "str(_exc)" not in body
        assert "str(exc)" not in body

    def test_logs_exception_with_request_details(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "unhandled_exception_handler")
        assert "logger.exception" in body
        assert "request.method" in body
        assert "request.url.path" in body

    def test_includes_request_id(self):
        source = _read(MAIN_FILE)
        body = _find_function_body(source, "unhandled_exception_handler")
        assert "request_id_ctx" in body


# ═══════════════════════════════════════════════════════════
# 5. 响应结构一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestResponseStructureConsistency:
    """验证所有异常处理器响应结构一致"""

    def test_all_handlers_use_success_false(self):
        source = _read(MAIN_FILE)
        count = source.count('"success": False')
        assert count >= 4, f"应有 4 处 success: False，实际 {count}"

    def test_all_handlers_use_error_object(self):
        source = _read(MAIN_FILE)
        # 每个 handler 应该有 error dict
        handlers = [
            "http_exception_handler",
            "starlette_exception_handler",
            "validation_exception_handler",
            "unhandled_exception_handler",
        ]
        for name in handlers:
            body = _find_function_body(source, name)
            assert '"error"' in body, f"{name} 缺少 error 字段"

    def test_all_handlers_import_request_id_ctx(self):
        source = _read(MAIN_FILE)
        count = source.count("from app.core.request_id import request_id_ctx")
        assert count >= 4, f"应有 4 处 request_id 导入，实际 {count}"

    def test_all_handlers_use_json_response(self):
        source = _read(MAIN_FILE)
        handlers = [
            "http_exception_handler",
            "starlette_exception_handler",
            "validation_exception_handler",
            "unhandled_exception_handler",
        ]
        for name in handlers:
            body = _find_function_body(source, name)
            assert "JSONResponse" in body, f"{name} 未使用 JSONResponse"

    def test_imports_all_exception_types(self):
        source = _read(MAIN_FILE)
        assert "HTTPException" in source
        assert "RequestValidationError" in source
        assert "StarletteHTTPException" in source
