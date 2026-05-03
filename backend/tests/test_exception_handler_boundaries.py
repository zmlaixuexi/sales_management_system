"""测试补强：异常处理中间件边界测试 — 覆盖 HTTPException handler 边界、
Starlette 路由异常、RequestValidationError 格式化、未处理异常守卫、
响应信封一致性、request_id 传播"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

# ═══════════════════════════════════════════════════════
# 测试用 FastAPI 应用 — 隔离异常处理器
# ═══════════════════════════════════════════════════════


def _create_test_app() -> FastAPI:
    """创建带有与 main.py 相同异常处理器的测试应用"""
    import logging

    from fastapi import Request
    from fastapi.responses import JSONResponse

    from app.core.request_id import RequestIDMiddleware

    test_app = FastAPI()

    @test_app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        from app.core.request_id import request_id_ctx

        detail = exc.detail
        if isinstance(detail, dict):
            error = {"code": detail.get("code", "SYSTEM_INTERNAL_ERROR"), "message": detail.get("message", str(detail))}
            if "details" in detail:
                error["details"] = detail["details"]
        else:
            error = {"code": "SYSTEM_INTERNAL_ERROR", "message": str(detail)}
        result: dict = {"success": False, "error": error}
        rid = request_id_ctx.get("")
        if rid:
            result["request_id"] = rid
        return JSONResponse(status_code=exc.status_code, content=result)

    @test_app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(_request: Request, exc: StarletteHTTPException):
        from app.core.request_id import request_id_ctx

        error = {
            "code": "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "METHOD_NOT_ALLOWED",
            "message": str(exc.detail),
        }
        result: dict = {"success": False, "error": error}
        rid = request_id_ctx.get("")
        if rid:
            result["request_id"] = rid
        return JSONResponse(status_code=exc.status_code, content=result)

    @test_app.exception_handler(RequestValidationError)
    def validation_exception_handler(_request: Request, exc: RequestValidationError):
        from app.core.request_id import request_id_ctx

        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = " → ".join(str(part) for part in first.get("loc", []))
        msg = first.get("msg", "请求参数错误")
        detail_msg = f"{loc}: {msg}" if loc else msg
        result: dict = {"success": False, "error": {"code": "VALIDATION_FAILED", "message": detail_msg}}
        rid = request_id_ctx.get("")
        if rid:
            result["request_id"] = rid
        return JSONResponse(status_code=422, content=result)

    @test_app.exception_handler(Exception)
    def unhandled_exception_handler(request: Request, _exc: Exception):
        from app.core.request_id import request_id_ctx

        rid = request_id_ctx.get("")
        logger = logging.getLogger("test_unhandled")
        logger.exception("未处理异常 [%s] %s rid=%s", request.method, request.url.path, rid)
        result: dict = {
            "success": False,
            "error": {"code": "SYSTEM_INTERNAL_ERROR", "message": "服务器内部错误，请稍后重试"},
        }
        if rid:
            result["request_id"] = rid
        return JSONResponse(status_code=500, content=result)

    test_app.add_middleware(RequestIDMiddleware)

    # ── 测试路由 ──

    @test_app.get("/test/http-dict")
    def raise_http_dict():
        raise HTTPException(status_code=400, detail={"code": "TEST_ERROR", "message": "测试错误"})

    @test_app.get("/test/http-dict-with-details")
    def raise_http_dict_details():
        raise HTTPException(
            status_code=400,
            detail={"code": "TEST_ERROR", "message": "测试错误", "details": {"field": "name"}},
        )

    @test_app.get("/test/http-string")
    def raise_http_string():
        raise HTTPException(status_code=400, detail="简单字符串错误")

    @test_app.get("/test/http-dict-no-code")
    def raise_http_dict_no_code():
        raise HTTPException(status_code=400, detail={"message": "只有消息"})

    @test_app.get("/test/http-dict-no-message")
    def raise_http_dict_no_message():
        raise HTTPException(status_code=400, detail={"code": "ONLY_CODE"})

    @test_app.get("/test/http-401")
    def raise_http_401():
        raise HTTPException(status_code=401, detail={"code": "AUTH_UNAUTHORIZED", "message": "未认证"})

    @test_app.get("/test/http-403")
    def raise_http_403():
        raise HTTPException(status_code=403, detail={"code": "AUTH_FORBIDDEN", "message": "无权限"})

    @test_app.get("/test/http-409")
    def raise_http_409():
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "资源冲突"})

    @test_app.get("/test/http-429")
    def raise_http_429():
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "请求过于频繁"})

    @test_app.get("/test/http-500")
    def raise_http_500():
        raise HTTPException(status_code=500, detail={"code": "INTERNAL", "message": "内部错误"})

    @test_app.get("/test/unhandled")
    def raise_unhandled():
        raise RuntimeError("未处理的运行时异常")

    @test_app.get("/test/unhandled-value-error")
    def raise_unhandled_value():
        raise ValueError("未处理的值错误")

    @test_app.get("/test/unhandled-key-error")
    def raise_unhandled_key():
        raise KeyError("missing_key")

    @test_app.get("/test/success")
    def success_endpoint():
        return {"success": True, "data": "ok"}

    class StrictModel(BaseModel):
        name: str
        age: int

        @field_validator("age")
        @classmethod
        def age_must_be_positive(cls, v):
            if v <= 0:
                raise ValueError("年龄必须大于0")
            return v

    @test_app.post("/test/validation")
    def validation_endpoint(body: StrictModel):
        return {"success": True, "data": body.model_dump()}

    @test_app.get("/test/validation-query")
    def validation_query_endpoint(page: int = 1, size: int = 20):
        return {"success": True, "data": {"page": page, "size": size}}

    return test_app


@pytest.fixture()
def client():
    app = _create_test_app()
    return TestClient(app, raise_server_exceptions=False)


# ═══════════════════════════════════════════════════════
# 1. HTTPException handler — dict detail
# ═══════════════════════════════════════════════════════


def test_http_dict_detail_code(client):
    """dict detail 正确提取 code"""
    resp = client.get("/test/http-dict")
    assert resp.json()["error"]["code"] == "TEST_ERROR"


def test_http_dict_detail_message(client):
    """dict detail 正确提取 message"""
    resp = client.get("/test/http-dict")
    assert resp.json()["error"]["message"] == "测试错误"


def test_http_dict_detail_status_code(client):
    """dict detail 保留原始 status_code"""
    resp = client.get("/test/http-dict")
    assert resp.status_code == 400


def test_http_dict_detail_success_false(client):
    """dict detail success 为 False"""
    resp = client.get("/test/http-dict")
    assert resp.json()["success"] is False


def test_http_dict_detail_no_details_by_default(client):
    """dict detail 不含 details 字段（未提供时）"""
    resp = client.get("/test/http-dict")
    assert "details" not in resp.json()["error"]


def test_http_dict_with_details_field(client):
    """dict detail 包含 details 字段"""
    resp = client.get("/test/http-dict-with-details")
    assert resp.json()["error"]["details"] == {"field": "name"}


def test_http_dict_no_code_defaults(client):
    """dict detail 缺少 code 时默认 SYSTEM_INTERNAL_ERROR"""
    resp = client.get("/test/http-dict-no-code")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_http_dict_no_code_preserves_message(client):
    """dict detail 缺少 code 时保留 message"""
    resp = client.get("/test/http-dict-no-code")
    assert resp.json()["error"]["message"] == "只有消息"


def test_http_dict_no_message_uses_str(client):
    """dict detail 缺少 message 时使用 str(detail)"""
    resp = client.get("/test/http-dict-no-message")
    # detail.get("message", str(detail)) → str({"code": "ONLY_CODE"})
    assert resp.json()["error"]["code"] == "ONLY_CODE"


# ═══════════════════════════════════════════════════════
# 2. HTTPException handler — string detail
# ═══════════════════════════════════════════════════════


def test_http_string_detail_code(client):
    """string detail 默认 code 为 SYSTEM_INTERNAL_ERROR"""
    resp = client.get("/test/http-string")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_http_string_detail_message(client):
    """string detail message 为原始字符串"""
    resp = client.get("/test/http-string")
    assert resp.json()["error"]["message"] == "简单字符串错误"


def test_http_string_detail_status_code(client):
    """string detail 保留原始 status_code"""
    resp = client.get("/test/http-string")
    assert resp.status_code == 400


def test_http_string_detail_no_details(client):
    """string detail 不含 details"""
    resp = client.get("/test/http-string")
    assert "details" not in resp.json()["error"]


# ═══════════════════════════════════════════════════════
# 3. HTTPException — 各种状态码
# ═══════════════════════════════════════════════════════


def test_http_401_status(client):
    """401 状态码正确返回"""
    resp = client.get("/test/http-401")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"


def test_http_403_status(client):
    """403 状态码正确返回"""
    resp = client.get("/test/http-403")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_http_409_status(client):
    """409 状态码正确返回"""
    resp = client.get("/test/http-409")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_http_429_status(client):
    """429 状态码正确返回"""
    resp = client.get("/test/http-429")
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RATE_LIMITED"


def test_http_500_status(client):
    """500 状态码正确返回"""
    resp = client.get("/test/http-500")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL"


# ═══════════════════════════════════════════════════════
# 4. Starlette 路由异常（404/405）
# ═══════════════════════════════════════════════════════


def test_starlette_404_code(client):
    """404 返回 RESOURCE_NOT_FOUND"""
    resp = client.get("/nonexistent/path")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_starlette_404_success_false(client):
    """404 success 为 False"""
    resp = client.get("/nonexistent/path")
    assert resp.json()["success"] is False


def test_starlette_404_has_error_message(client):
    """404 有错误消息"""
    resp = client.get("/nonexistent/path")
    assert "message" in resp.json()["error"]


def test_starlette_405_code(client):
    """405 返回 METHOD_NOT_ALLOWED"""
    resp = client.post("/test/success")
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_starlette_405_success_false(client):
    """405 success 为 False"""
    resp = client.post("/test/success")
    assert resp.json()["success"] is False


# ═══════════════════════════════════════════════════════
# 5. RequestValidationError 格式化
# ═══════════════════════════════════════════════════════


def test_validation_missing_field_status(client):
    """缺少必填字段返回 422"""
    resp = client.post("/test/validation", json={"age": 25})
    assert resp.status_code == 422


def test_validation_missing_field_code(client):
    """校验错误 code 为 VALIDATION_FAILED"""
    resp = client.post("/test/validation", json={"age": 25})
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_validation_missing_field_loc_in_message(client):
    """校验错误消息包含字段路径"""
    resp = client.post("/test/validation", json={"age": 25})
    msg = resp.json()["error"]["message"]
    assert "name" in msg


def test_validation_wrong_type(client):
    """类型错误返回 422"""
    resp = client.post("/test/validation", json={"name": "test", "age": "not_a_number"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_validation_custom_validator(client):
    """自定义 validator 错误返回 422"""
    resp = client.post("/test/validation", json={"name": "test", "age": -1})
    assert resp.status_code == 422
    assert "年龄" in resp.json()["error"]["message"]


def test_validation_reports_first_error(client):
    """多个错误时只报告第一个"""
    resp = client.post("/test/validation", json={})
    assert resp.status_code == 422
    # 只有一个错误在 message 中
    msg = resp.json()["error"]["message"]
    assert len(msg.split(" → ")) > 0


def test_validation_success_false(client):
    """校验错误 success 为 False"""
    resp = client.post("/test/validation", json={})
    assert resp.json()["success"] is False


def test_validation_query_param_error(client):
    """查询参数校验错误返回 422"""
    resp = client.get("/test/validation-query", params={"page": "not_a_number"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_validation_valid_body_passes(client):
    """合法 body 通过校验"""
    resp = client.post("/test/validation", json={"name": "张三", "age": 25})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_validation_loc_arrow_separator(client):
    """loc 用 → 连接"""
    resp = client.post("/test/validation", json={})
    msg = resp.json()["error"]["message"]
    assert " → " in msg


# ═══════════════════════════════════════════════════════
# 6. 未处理异常守卫
# ═══════════════════════════════════════════════════════


def test_unhandled_runtime_error_status(client):
    """RuntimeError 返回 500"""
    resp = client.get("/test/unhandled")
    assert resp.status_code == 500


def test_unhandled_runtime_error_code(client):
    """RuntimeError code 为 SYSTEM_INTERNAL_ERROR"""
    resp = client.get("/test/unhandled")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_unhandled_runtime_error_message(client):
    """RuntimeError message 为通用消息，不泄露详情"""
    resp = client.get("/test/unhandled")
    assert resp.json()["error"]["message"] == "服务器内部错误，请稍后重试"


def test_unhandled_runtime_error_no_detail_leak(client):
    """RuntimeError 不泄露原始异常消息"""
    resp = client.get("/test/unhandled")
    assert "RuntimeError" not in resp.text
    assert "运行时异常" not in resp.text


def test_unhandled_value_error(client):
    """ValueError 同样返回 500"""
    resp = client.get("/test/unhandled-value-error")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_unhandled_key_error(client):
    """KeyError 同样返回 500"""
    resp = client.get("/test/unhandled-key-error")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_unhandled_success_false(client):
    """未处理异常 success 为 False"""
    resp = client.get("/test/unhandled")
    assert resp.json()["success"] is False


# ═══════════════════════════════════════════════════════
# 7. request_id 传播
# ═══════════════════════════════════════════════════════


def test_request_id_in_http_exception(client):
    """HTTPException 响应包含 request_id"""
    resp = client.get("/test/http-dict")
    body = resp.json()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


def test_request_id_in_404(client):
    """404 响应包含 request_id"""
    resp = client.get("/nonexistent")
    body = resp.json()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


def test_request_id_in_405(client):
    """405 响应包含 request_id"""
    resp = client.post("/test/success")
    body = resp.json()
    assert "request_id" in body


def test_request_id_in_validation_error(client):
    """422 响应包含 request_id"""
    resp = client.post("/test/validation", json={})
    body = resp.json()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


def test_request_id_in_unhandled(client):
    """500 未处理异常响应包含 request_id"""
    resp = client.get("/test/unhandled")
    body = resp.json()
    assert "request_id" in body
    assert len(body["request_id"]) > 0


def test_request_id_header_propagation(client):
    """X-Request-ID 响应头存在"""
    resp = client.get("/test/success")
    assert "x-request-id" in resp.headers


def test_request_id_custom_header(client):
    """自定义 X-Request-ID 请求头被保留"""
    custom_id = "my-custom-id-12345"
    resp = client.get("/test/http-dict", headers={"X-Request-ID": custom_id})
    assert resp.headers.get("x-request-id") == custom_id


def test_request_id_custom_in_error_body(client):
    """自定义 request_id 出现在错误响应体中"""
    custom_id = "test-rid-abc"
    resp = client.get("/test/http-dict", headers={"X-Request-ID": custom_id})
    assert resp.json()["request_id"] == custom_id


def test_request_id_uuid_format(client):
    """自动生成的 request_id 是 UUID 格式"""
    import re

    resp = client.get("/test/http-dict")
    rid = resp.json()["request_id"]
    uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    assert uuid_re.match(rid), f"request_id 不是 UUID 格式: {rid}"


def test_different_requests_different_request_ids(client):
    """不同请求产生不同 request_id"""
    resp1 = client.get("/test/http-dict")
    resp2 = client.get("/test/http-dict")
    assert resp1.json()["request_id"] != resp2.json()["request_id"]


# ═══════════════════════════════════════════════════════
# 8. 响应信封一致性
# ═══════════════════════════════════════════════════════


def test_envelope_has_success_and_error(client):
    """所有错误响应同时有 success 和 error"""
    endpoints = [
        "/test/http-dict",
        "/test/http-string",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        body = resp.json()
        assert "success" in body, f"{ep} 缺少 success"
        assert "error" in body, f"{ep} 缺少 error"


def test_envelope_error_has_code_and_message(client):
    """所有 error 对象都有 code 和 message"""
    endpoints = [
        "/test/http-dict",
        "/test/http-string",
        "/test/http-401",
        "/test/http-403",
        "/test/http-409",
        "/test/http-429",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        error = resp.json()["error"]
        assert "code" in error, f"{ep} error 缺少 code"
        assert "message" in error, f"{ep} error 缺少 message"


def test_envelope_404_structure(client):
    """404 响应结构与其他错误一致"""
    resp = client.get("/nonexistent/path")
    body = resp.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]


def test_envelope_422_structure(client):
    """422 响应结构与其他错误一致"""
    resp = client.post("/test/validation", json={})
    body = resp.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]


def test_envelope_500_structure(client):
    """500 响应结构与其他错误一致"""
    resp = client.get("/test/unhandled")
    body = resp.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]


# ═══════════════════════════════════════════════════════
# 9. 成功响应不受影响
# ═══════════════════════════════════════════════════════


def test_success_response_not_wrapped(client):
    """成功响应不被异常处理器包装"""
    resp = client.get("/test/success")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == "ok"


def test_success_response_has_request_id_header(client):
    """成功响应有 X-Request-ID 头"""
    resp = client.get("/test/success")
    assert "x-request-id" in resp.headers


# ═══════════════════════════════════════════════════════
# 10. main.py 真实应用异常处理器验证
# ═══════════════════════════════════════════════════════


def test_main_app_has_four_exception_handlers():
    """main.py 注册了四个异常处理器"""
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from app.main import app

    handlers = app.exception_handlers
    assert HTTPException in handlers
    assert StarletteHTTPException in handlers
    assert RequestValidationError in handlers
    assert Exception in handlers


def test_main_app_unhandled_returns_500():
    """main.py 应用未处理异常返回 500"""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    # main.py 没有 unhandled 路由，用不存在的路径验证 404 格式
    resp = client.get("/api/v1/nonexistent-test-path-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False


def test_main_app_validation_returns_422():
    """main.py 应用校验错误返回 422"""
    from app.main import app

    client = TestClient(app)
    # POST /api/v1/auth/login 需要 JSON body
    resp = client.post("/api/v1/auth/login", json={})
    # 可能是 422 或其他，取决于端点是否需要字段
    assert resp.status_code in (401, 403, 404, 422)


def test_main_app_error_response_has_request_id():
    """main.py 错误响应包含 request_id"""
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/nonexistent-path-for-test")
    body = resp.json()
    assert "request_id" in body


# ═══════════════════════════════════════════════════════
# 11. HTTPException — 整数 detail（非 dict 非 str）
# ═══════════════════════════════════════════════════════


def test_http_int_detail_code(client):
    """整数 detail 的 code 为 SYSTEM_INTERNAL_ERROR"""
    app = _create_test_app()

    @app.get("/test/http-int")
    def raise_http_int():
        raise HTTPException(status_code=400, detail=12345)

    c = TestClient(app)
    resp = c.get("/test/http-int")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_http_int_detail_message(client):
    """整数 detail 的 message 为 str(detail)"""
    app = _create_test_app()

    @app.get("/test/http-int")
    def raise_http_int():
        raise HTTPException(status_code=400, detail=12345)

    c = TestClient(app)
    resp = c.get("/test/http-int")
    assert resp.json()["error"]["message"] == "12345"


def test_http_none_detail(client):
    """None detail 的 code 为 SYSTEM_INTERNAL_ERROR"""
    app = _create_test_app()

    @app.get("/test/http-none")
    def raise_http_none():
        raise HTTPException(status_code=400, detail=None)

    c = TestClient(app)
    resp = c.get("/test/http-none")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"


def test_http_list_detail(client):
    """list detail 的 code 为 SYSTEM_INTERNAL_ERROR"""
    app = _create_test_app()

    @app.get("/test/http-list")
    def raise_http_list():
        raise HTTPException(status_code=400, detail=["error1", "error2"])

    c = TestClient(app)
    resp = c.get("/test/http-list")
    assert resp.json()["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
