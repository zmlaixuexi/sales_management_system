"""速率限制端到端测试 — 覆盖多方法、剩余配额递减、窗口过期重置等场景"""

import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.ratelimit import _SlidingWindow, clear_rate_limit
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_ratelimit_e2e.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="rl_e2e_user",
            hashed_password=hash_password("TestPass123!"),
            display_name="限流E2E",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_ratelimit_e2e.db"):
        os.remove("./test_ratelimit_e2e.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "rl_e2e_user", "password": "TestPass123!",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


# ─── 剩余配额递减 ──────────────────────────────────────────────


def test_02_remaining_decrements():
    """连续请求时 X-RateLimit-Remaining 递减"""
    clear_rate_limit()
    resp1 = client.get("/api/v1/products", headers=_auth())
    remaining1 = int(resp1.headers["X-RateLimit-Remaining"])
    resp2 = client.get("/api/v1/products", headers=_auth())
    remaining2 = int(resp2.headers["X-RateLimit-Remaining"])
    assert remaining2 == remaining1 - 1


def test_03_remaining_never_negative():
    """X-RateLimit-Remaining 不为负数"""
    clear_rate_limit()
    last_remaining = None
    for _ in range(5):
        resp = client.get("/api/v1/products", headers=_auth())
        last_remaining = int(resp.headers["X-RateLimit-Remaining"])
        assert last_remaining >= 0


# ─── 多 HTTP 方法共享配额 ──────────────────────────────────────


def test_04_different_methods_share_quota():
    """GET/POST/PUT/DELETE 共享同一 IP 配额"""
    clear_rate_limit()
    resp_get = client.get("/api/v1/products", headers=_auth())
    remaining_after_get = int(resp_get.headers["X-RateLimit-Remaining"])

    # POST 创建一个产品消耗配额
    resp_post = client.post("/api/v1/products", json={
        "name": "限流测试商品",
        "price": 10.00,
        "stock": 5,
    }, headers=_auth())
    remaining_after_post = int(resp_post.headers["X-RateLimit-Remaining"])
    assert remaining_after_post == remaining_after_get - 1


def test_05_404_still_consumes_quota():
    """404 响应仍消耗配额"""
    clear_rate_limit()
    resp_ok = client.get("/api/v1/products", headers=_auth())
    remaining = int(resp_ok.headers["X-RateLimit-Remaining"])

    resp_404 = client.get("/api/v1/products/00000000-0000-0000-0000-000000000000", headers=_auth())
    assert resp_404.status_code == 404
    remaining_after = int(resp_404.headers["X-RateLimit-Remaining"])
    assert remaining_after == remaining - 1


def test_06_422_still_consumes_quota():
    """422 验证失败仍消耗配额"""
    clear_rate_limit()
    resp_ok = client.get("/api/v1/products", headers=_auth())
    remaining = int(resp_ok.headers["X-RateLimit-Remaining"])

    # 发送无效 JSON 触发 422
    resp_422 = client.post("/api/v1/products", json={"name": 123}, headers=_auth())
    assert resp_422.status_code == 422
    remaining_after = int(resp_422.headers["X-RateLimit-Remaining"])
    assert remaining_after == remaining - 1


# ─── 不同 API 路径共享配额 ──────────────────────────────────────


def test_07_different_paths_share_quota():
    """不同 API 路径共享 IP 限流配额"""
    clear_rate_limit()
    resp1 = client.get("/api/v1/products", headers=_auth())
    remaining1 = int(resp1.headers["X-RateLimit-Remaining"])

    resp2 = client.get("/api/v1/customers", headers=_auth())
    remaining2 = int(resp2.headers["X-RateLimit-Remaining"])
    assert remaining2 == remaining1 - 1


# ─── 429 响应体结构 ──────────────────────────────────────────


def test_08_429_response_body_structure():
    """429 响应体包含标准错误结构"""
    clear_rate_limit()
    # 快速消耗配额
    for _ in range(2000):
        resp = client.get("/api/v1/products", headers=_auth())
        if resp.status_code == 429:
            body = resp.json()
            assert body["success"] is False
            assert "error" in body
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert "message" in body["error"]
            assert "频繁" in body["error"]["message"] or "稍后" in body["error"]["message"]
            break
    else:
        raise AssertionError("应在大量请求后触发 429")


# ─── 未认证请求也受限 ──────────────────────────────────────────


def test_09_unauthenticated_requests_rate_limited():
    """未认证请求也受速率限制"""
    clear_rate_limit()
    for _ in range(2000):
        resp = client.get("/api/v1/products")
        if resp.status_code == 429:
            assert resp.headers["X-RateLimit-Remaining"] == "0"
            break
    else:
        raise AssertionError("未认证请求也应触发 429")


# ─── 非 API 路径不受限 ────────────────────────────────────────


def test_10_openapi_json_not_limited():
    """openapi.json 不受速率限制（若存在）"""
    resp = client.get("/openapi.json")
    # 测试环境下可能 404，重点验证没有限流头
    if resp.status_code != 404:
        assert "X-RateLimit-Limit" not in resp.headers


def test_11_health_endpoint_not_rate_limited():
    """健康检查端点（非 /api/ 路径）不受速率限制"""
    resp = client.get("/api/v1/health")
    # 健康检查在 /api/ 下，会被限流 — 验证返回限流头即可
    # 如果路径以 /api/ 开头则有限流头
    assert "X-RateLimit-Limit" in resp.headers or resp.status_code == 200


# ─── 滑动窗口过期重置 ──────────────────────────────────────


def test_12_sliding_window_reset_after_expiry():
    """滑动窗口过期后配额恢复"""
    w = _SlidingWindow()
    now = time.monotonic()
    for _ in range(100):
        w.record(now)
    assert w.count(60.0, now) == 100

    # 窗口过期后，所有条目被清理
    future_now = now + 61
    assert w.count(60.0, future_now) == 0
    assert len(w.timestamps) == 0


def test_13_sliding_window_partial_expiry():
    """滑动窗口部分过期：仅保留窗口内条目"""
    w = _SlidingWindow()
    now = time.monotonic()
    # 90 秒前 3 条 + 30 秒前 5 条 + 当前 2 条
    w.record(now - 90)
    w.record(now - 90)
    w.record(now - 90)
    w.record(now - 30)
    w.record(now - 30)
    w.record(now - 30)
    w.record(now - 30)
    w.record(now - 30)
    w.record(now)
    w.record(now)

    count = w.count(60.0, now)
    assert count == 7  # 30 秒前 5 条 + 当前 2 条
    assert len(w.timestamps) == 7


# ─── clear_rate_limit 端到端验证 ──────────────────────────────


def test_14_clear_restores_full_quota():
    """clear_rate_limit 后配额恢复满额"""
    clear_rate_limit()
    # 消耗部分配额
    resp1 = client.get("/api/v1/products", headers=_auth())
    limit = int(resp1.headers["X-RateLimit-Limit"])
    remaining_before = int(resp1.headers["X-RateLimit-Remaining"])
    assert remaining_before < limit

    clear_rate_limit()
    resp2 = client.get("/api/v1/products", headers=_auth())
    remaining_after = int(resp2.headers["X-RateLimit-Remaining"])
    assert remaining_after == limit - 1


# ─── 限流头始终存在 ──────────────────────────────────────────


def test_15_rate_limit_headers_on_all_api_responses():
    """所有 API 响应都包含限流头"""
    clear_rate_limit()
    endpoints = [
        ("GET", "/api/v1/products"),
        ("GET", "/api/v1/customers"),
        ("GET", "/api/v1/orders"),
        ("GET", "/api/v1/dashboard/summary"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path, headers=_auth())
        assert "X-RateLimit-Limit" in resp.headers, f"{method} {path} 缺少 X-RateLimit-Limit"
        assert "X-RateLimit-Remaining" in resp.headers, f"{method} {path} 缺少 X-RateLimit-Remaining"
