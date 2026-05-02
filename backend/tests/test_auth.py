import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.api.v1.auth import _login_fail_counts
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

# 测试用内存 SQLite 数据库
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)

_original_override = None


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        # 创建测试用户
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            hashed_password=hash_password("testpass123"),
            display_name="测试用户",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


def test_login_success():
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


def test_login_wrong_password():
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "wrong"})
    assert response.status_code == 401


def test_login_nonexistent_user():
    response = client.post("/api/v1/auth/login", json={"username": "nouser", "password": "pass"})
    assert response.status_code == 401


def test_get_me():
    # 先登录获取 token
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["username"] == "testuser"


def test_get_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_refresh_token():
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    refresh_token = login_resp.json()["data"]["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]


def test_refresh_rejected_for_inactive_user():
    """已禁用用户的 Refresh Token 应被拒绝"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    refresh_token = login_resp.json()["data"]["refresh_token"]

    db = TestSession()
    user = db.query(User).filter(User.username == "testuser").first()
    user.is_active = False
    db.commit()
    db.close()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401

    db = TestSession()
    user = db.query(User).filter(User.username == "testuser").first()
    user.is_active = True
    db.commit()
    db.close()


def test_logout():
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200


def test_users_list_requires_admin():
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_access_with_refresh_token_rejected():
    """使用 refresh token 作为 Bearer 应被拒绝（type != access）"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    refresh_token = login_resp.json()["data"]["refresh_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert response.status_code == 401


def test_change_password_success():
    """修改密码成功"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "newpass456",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "成功" in resp.json()["message"]

    # 用新密码登录验证
    login2 = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "newpass456"})
    assert login2.status_code == 200

    # 改回原密码
    token2 = login2.json()["data"]["access_token"]
    client.post("/api/v1/auth/change-password", json={
        "old_password": "newpass456",
        "new_password": "testpass123",
    }, headers={"Authorization": f"Bearer {token2}"})


def test_change_password_wrong_old():
    """原密码错误"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "wrongpass1",
        "new_password": "newpass456",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert "原密码" in resp.json()["error"]["message"]


def test_change_password_weak_new():
    """新密码不符合强度要求（纯数字）"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "123456",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


def test_change_password_no_digits():
    """新密码纯字母无数字被拒绝"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "abcdef",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
    assert "数字" in str(resp.json())


def test_login_rate_limit_after_failures():
    """连续登录失败 10 次后触发速率限制"""
    _login_fail_counts.clear()
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"username": "testuser", "password": "wrongpass1"})
    resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "wrongpass1"})
    assert resp.status_code == 429
    assert "次数过多" in resp.json()["error"]["message"]
    _login_fail_counts.clear()


def test_login_rate_limit_does_not_affect_success():
    """正确密码不受速率限制影响"""
    _login_fail_counts.clear()
    resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert resp.status_code == 200
    _login_fail_counts.clear()


def test_change_password_requires_auth():
    """未认证修改密码返回 401"""
    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "newpass123",
    })
    assert resp.status_code == 401


def test_change_password_empty_old_password_422():
    """空旧密码返回 422"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "",
        "new_password": "newpass123",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
