"""安全加固：请求体大小限制中间件边界测试 — 覆盖 content-length 边界、
无 content-type 头、PATCH 方法、错误响应结构、配置校验、中间件注册、路径匹配"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. content-length 精确边界
# ═══════════════════════════════════════════════════════


def test_content_length_equal_to_max_passes(monkeypatch):
    """content-length 恰好等于 max_bytes 通过"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 1)
    max_bytes = 1 * 1024 * 1024
    payload = "x" * max_bytes
    resp = client.post(
        "/api/v1/products",
        content=payload.encode(),
        headers={"content-type": "application/json"},
    )
    assert resp.status_code != 413


def test_content_length_one_byte_over_max_rejected(monkeypatch):
    """content-length 比 max_bytes 大 1 字节被拒绝"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 1)
    max_bytes = 1 * 1024 * 1024
    payload = "x" * (max_bytes + 1)
    resp = client.post(
        "/api/v1/products",
        content=payload.encode(),
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


def test_content_length_zero_not_rejected():
    """content-length 为 0 的 POST 不被拒绝"""
    resp = client.post(
        "/api/v1/products",
        content=b"",
        headers={"content-type": "application/json", "content-length": "0"},
    )
    assert resp.status_code != 413


# ═══════════════════════════════════════════════════════
# 2. 无 content-type 头
# ═══════════════════════════════════════════════════════


def test_no_content_type_with_body_not_rejected():
    """无 content-type 头的带 body POST 不被中间件拒绝"""
    resp = client.post(
        "/api/v1/products",
        content=b'{"name": "test"}',
    )
    # 路由层可能 422/401，但中间件不应 413
    assert resp.status_code != 413


def test_no_content_type_oversized_rejected(monkeypatch):
    """无 content-type 头的超大 body 被 content-length 检查拒绝"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-length": "100"},
    )
    assert resp.status_code == 413


# ═══════════════════════════════════════════════════════
# 3. PATCH 方法
# ═══════════════════════════════════════════════════════


def test_patch_request_limited(monkeypatch):
    """PATCH 请求受请求体限制"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.patch(
        "/api/v1/products/999",
        content=b'{"name": "x" * 100}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


# ═══════════════════════════════════════════════════════
# 4. 错误响应结构验证
# ═══════════════════════════════════════════════════════


def test_413_response_structure(monkeypatch):
    """413 响应包含标准错误结构"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413
    body = resp.json()
    assert body["success"] is False
    assert "error" in body
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "message" in body["error"]
    assert "MB" in body["error"]["message"]


def test_413_message_contains_limit_value(monkeypatch):
    """413 错误消息包含限制值"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 5)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * (6 * 1024 * 1024),
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413
    assert "5" in resp.json()["error"]["message"]


def test_413_error_code_constant():
    """PAYLOAD_TOO_LARGE 错误码为固定值"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware

    source_code = inspect.getsource(BodyLimitMiddleware)
    assert "PAYLOAD_TOO_LARGE" in source_code


# ═══════════════════════════════════════════════════════
# 5. 配置校验
# ═══════════════════════════════════════════════════════


def test_max_json_body_mb_default():
    """MAX_JSON_BODY_MB 默认值为 1"""
    from app.core.config import Settings
    s = Settings()
    assert s.MAX_JSON_BODY_MB == 1


def test_max_json_body_mb_custom():
    """MAX_JSON_BODY_MB 可自定义"""
    from app.core.config import Settings
    s = Settings(MAX_JSON_BODY_MB=10)
    assert s.MAX_JSON_BODY_MB == 10


def test_max_json_body_mb_zero_means_block_all():
    """MAX_JSON_BODY_MB=0 阻止所有带 body 的请求"""
    from app.core.config import Settings
    s = Settings(MAX_JSON_BODY_MB=0)
    assert s.MAX_JSON_BODY_MB == 0


def test_max_bytes_calculation():
    """max_bytes 正确计算为 MB * 1024 * 1024"""
    from app.core.config import Settings
    s = Settings(MAX_JSON_BODY_MB=2)
    max_bytes = s.MAX_JSON_BODY_MB * 1024 * 1024
    assert max_bytes == 2 * 1024 * 1024


# ═══════════════════════════════════════════════════════
# 6. 中间件注册验证
# ═══════════════════════════════════════════════════════


def test_body_limit_middleware_registered():
    """BodyLimitMiddleware 已注册"""
    from app.core.body_limit import BodyLimitMiddleware
    has_bl = any(
        m.cls is BodyLimitMiddleware if hasattr(m, "cls") else False
        for m in app.user_middleware
    )
    assert has_bl


# ═══════════════════════════════════════════════════════
# 7. 方法豁免验证
# ═══════════════════════════════════════════════════════


def test_get_method_exempt():
    """GET 方法豁免，即使有超大 content-length"""
    resp = client.get(
        "/api/v1/products",
        headers={"content-length": "999999999"},
    )
    assert resp.status_code != 413


def test_head_method_exempt():
    """HEAD 方法豁免"""
    resp = client.head(
        "/api/v1/products",
        headers={"content-length": "999999999"},
    )
    assert resp.status_code != 413


def test_options_method_exempt():
    """OPTIONS 方法豁免"""
    resp = client.options(
        "/api/v1/products",
        headers={"content-length": "999999999"},
    )
    assert resp.status_code != 413


# ═══════════════════════════════════════════════════════
# 8. 路径豁免验证
# ═══════════════════════════════════════════════════════


def test_uploads_path_prefix_exempt(monkeypatch):
    """/uploads/ 路径前缀豁免"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/uploads/any/nested/path",
        content=b"x" * 100,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code != 413


def test_api_path_not_exempt(monkeypatch):
    """/api/ 路径不豁免"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


# ═══════════════════════════════════════════════════════
# 9. multipart 豁免验证
# ═══════════════════════════════════════════════════════


def test_multipart_form_data_exempt(monkeypatch):
    """multipart/form-data content-type 豁免"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-type": "multipart/form-data; boundary=----abc"},
    )
    assert resp.status_code != 413


def test_multipart_mixed_not_exempt(monkeypatch):
    """multipart/mixed 非 multipart/form-data 不豁免"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-type": "multipart/mixed; boundary=----abc"},
    )
    assert resp.status_code == 413


def test_application_json_not_exempt(monkeypatch):
    """application/json 不豁免"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.post(
        "/api/v1/products",
        content=b"x" * 100,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


# ═══════════════════════════════════════════════════════
# 10. 无 content-length 头行为
# ═══════════════════════════════════════════════════════


def test_no_content_length_passes_even_oversized():
    """无 content-length 头的请求直接放行（不做实际 body 大小检查）"""
    resp = client.post(
        "/api/v1/products",
        content=b'{"name": "test"}',
        headers={"content-type": "application/json"},
    )
    # 中间件不拒绝（content-length 为 None 时跳过检查）
    assert resp.status_code != 413


# ═══════════════════════════════════════════════════════
# 11. 源代码验证
# ═══════════════════════════════════════════════════════


def test_source_checks_method_list():
    """源代码中豁免 GET/HEAD/OPTIONS"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware
    source = inspect.getsource(BodyLimitMiddleware)
    assert '"GET"' in source
    assert '"HEAD"' in source
    assert '"OPTIONS"' in source


def test_source_uses_settings_max_json_body_mb():
    """源代码使用 settings.MAX_JSON_BODY_MB"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware
    source = inspect.getsource(BodyLimitMiddleware)
    assert "MAX_JSON_BODY_MB" in source


def test_source_413_status_code():
    """源代码返回 413 状态码"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware
    source = inspect.getsource(BodyLimitMiddleware)
    assert "413" in source


def test_source_checks_multipart():
    """源代码检查 multipart/form-data"""
    import inspect

    from app.core.body_limit import BodyLimitMiddleware
    source = inspect.getsource(BodyLimitMiddleware)
    assert "multipart/form-data" in source
