"""速率限制中间件测试"""

import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.ratelimit import _SlidingWindow
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_ratelimit.db"
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
            username="rl_tester",
            hashed_password=hash_password("testpass123"),
            display_name="限流测试员",
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
    if os.path.exists("./test_ratelimit.db"):
        os.remove("./test_ratelimit.db")
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
        "username": "rl_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_rate_limit_headers():
    """正常请求返回 RateLimit 响应头"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers


def test_03_rate_limit_429():
    """高频请求触发 429（放在最后，会耗尽 IP 配额）"""
    got_429 = False
    for _ in range(2000):
        resp = client.get("/api/v1/products", headers=_auth())
        if resp.status_code == 429:
            got_429 = True
            body = resp.json()
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            break
    assert got_429, "应在大量请求后触发 429"


def test_03b_rate_limit_429_has_headers():
    """429 响应也应携带 RateLimit 响应头"""
    got_429 = False
    for _ in range(2000):
        resp = client.get("/api/v1/products", headers=_auth())
        if resp.status_code == 429:
            got_429 = True
            assert "X-RateLimit-Limit" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers
            assert resp.headers["X-RateLimit-Remaining"] == "0"
            break
    assert got_429


def test_04_sliding_window_cleans_expired():
    """滑动窗口清理过期条目"""
    w = _SlidingWindow()
    now = time.monotonic()
    w.record(now - 120)  # 2 分钟前，已过期
    w.record(now - 61)   # 61 秒前，已过期
    w.record(now)         # 当前记录
    # 60 秒窗口应清理 2 条过期
    count = w.count(60.0, now)
    assert count == 1
    assert len(w.timestamps) == 1
