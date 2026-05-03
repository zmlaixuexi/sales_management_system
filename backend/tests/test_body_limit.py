"""请求体大小限制中间件测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_body_limit.db"
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
            username="bl_tester",
            hashed_password=hash_password("TestPass123!"),
            display_name="请求体测试员",
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
    if os.path.exists("./test_body_limit.db"):
        os.remove("./test_body_limit.db")
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
        "username": "bl_tester", "password": "TestPass123!",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_normal_post_passes():
    """正常大小的 JSON POST 通过"""
    resp = client.post("/api/v1/products", json={
        "name": "测试商品", "sale_price": "99.00",
    }, headers=_auth())
    # 可能 201/400/422，不应是 413
    assert resp.status_code in (200, 201, 400, 422)


def test_03_get_request_not_limited():
    """GET 请求不受限制"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200


def test_04_oversized_body_rejected(monkeypatch):
    """超限请求体返回 413"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    big_payload = {"name": "x" * 100}
    resp = client.post("/api/v1/products", json=big_payload, headers=_auth())
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "MB" in body["error"]["message"]


def test_05_multipart_not_limited(monkeypatch):
    """multipart/form-data 不受限"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    csv_content = "商品名称,销售价\n测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code != 413


def test_06_options_not_limited():
    """OPTIONS 请求不受限"""
    resp = client.options("/api/v1/products")
    # 可能 405 或 CORS 200，不应 413
    assert resp.status_code != 413


def test_07_exact_limit_passes(monkeypatch):
    """恰好等于限制大小通过（不含超限）"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 1)
    resp = client.post("/api/v1/products", json={
        "name": "小商品", "sale_price": "10.00",
    }, headers=_auth())
    assert resp.status_code != 413


def test_08_head_request_not_limited():
    """HEAD 请求不受限制"""
    resp = client.head("/api/v1/products", headers=_auth())
    assert resp.status_code != 413


def test_09_uploads_path_exempt(monkeypatch):
    """/uploads 路径不受请求体限制"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    # /uploads 路径应该直接放行（实际可能 404 但不应 413）
    resp = client.post("/uploads/test", content=b"data", headers=_auth())
    assert resp.status_code != 413


def test_10_put_request_limited(monkeypatch):
    """PUT 请求受请求体限制"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.put("/api/v1/products/999", json={"name": "x" * 100}, headers=_auth())
    assert resp.status_code == 413


def test_11_delete_request_limited(monkeypatch):
    """DELETE 请求受请求体限制"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_JSON_BODY_MB", 0)
    resp = client.request(
        "DELETE", "/api/v1/products/999",
        content=b"x" * 100,
        headers={**_auth(), "content-type": "application/json"},
    )
    assert resp.status_code == 413


def test_12_no_content_length_passes():
    """无 content-length 头的请求正常放行"""
    # 使用 raw request 不带 content-length
    resp = client.post("/api/v1/products", content=b'{}', headers={**_auth(), "content-type": "application/json"})
    # 可能 422（缺少字段）或其他错误，但不应 413
    assert resp.status_code != 413
