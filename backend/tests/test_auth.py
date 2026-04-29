import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
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
