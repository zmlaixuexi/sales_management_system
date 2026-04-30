"""用户管理 CRUD 测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import Role, User

TEST_DB_URL = "sqlite:///./test_user_mgmt.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_admin_id: str = ""
_role_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _admin_id, _role_id
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        admin = User(
            id=uuid.uuid4(),
            username="mgmt_admin",
            hashed_password=hash_password("admin123"),
            display_name="管理测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        _admin_id = str(admin.id)

        role = Role(
            id=uuid.uuid4(),
            name="test_role",
            display_name="测试角色",
        )
        db.add(role)
        _role_id = str(role.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_user_mgmt.db"):
        os.remove("./test_user_mgmt.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login_admin():
    """管理员登录"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "mgmt_admin", "password": "admin123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_list_users():
    """用户列表"""
    resp = client.get("/api/v1/users", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["username"] == "mgmt_admin"


def test_03_list_users_keyword_search():
    """用户列表关键词搜索"""
    resp = client.get("/api/v1/users", params={"keyword": "mgmt"}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_04_create_user():
    """创建用户"""
    resp = client.post("/api/v1/users", json={
        "username": "newuser",
        "password": "password123",
        "display_name": "新建用户",
        "phone": "13800001234",
        "role_ids": [_role_id],
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "newuser"
    assert "id" in resp.json()["data"]


def test_05_create_duplicate_username():
    """创建重复用户名"""
    resp = client.post("/api/v1/users", json={
        "username": "newuser",
        "password": "password123",
        "display_name": "重复用户",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]["message"]


def test_06_update_user():
    """编辑用户"""
    user_id = resp_id_from_list("newuser")
    resp = client.put(f"/api/v1/users/{user_id}", json={
        "display_name": "修改后名称",
        "phone": "13899999999",
        "email": "newuser@test.com",
    }, headers=_auth())
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]


def test_07_update_user_toggle_active():
    """禁用用户"""
    user_id = resp_id_from_list("newuser")
    resp = client.put(f"/api/v1/users/{user_id}", json={
        "is_active": False,
    }, headers=_auth())
    assert resp.status_code == 200

    # 验证状态变更
    resp = client.get("/api/v1/users", headers=_auth())
    users = resp.json()["data"]["items"]
    target = next(u for u in users if u["username"] == "newuser")
    assert target["is_active"] is False


def test_08_update_user_not_found():
    """编辑不存在的用户"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/users/{fake_id}", json={
        "display_name": "不存在",
    }, headers=_auth())
    assert resp.status_code == 404


def test_09_update_user_roles():
    """修改用户角色"""
    user_id = resp_id_from_list("newuser")
    resp = client.put(f"/api/v1/users/{user_id}", json={
        "role_ids": [_role_id],
    }, headers=_auth())
    assert resp.status_code == 200

    # 验证角色变更
    resp = client.get("/api/v1/users", headers=_auth())
    users = resp.json()["data"]["items"]
    target = next(u for u in users if u["username"] == "newuser")
    assert len(target["roles"]) == 1
    assert target["roles"][0]["name"] == "test_role"


def test_10_create_user_requires_admin():
    """非管理员创建用户返回 403"""
    # 先重新启用用户并设为非管理员
    db = TestSession()
    user = db.query(User).filter(User.username == "newuser").first()
    user.is_active = True
    user.is_superuser = False
    db.commit()
    db.close()

    login = client.post("/api/v1/auth/login", json={
        "username": "newuser", "password": "password123",
    })
    token = login.json()["data"]["access_token"]

    resp = client.post("/api/v1/users", json={
        "username": "unauthorized", "password": "pass123456",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_11_non_admin_update_user_forbidden():
    """非管理员编辑用户返回 403"""
    db = TestSession()
    user = db.query(User).filter(User.username == "newuser").first()
    user.is_active = True
    user.is_superuser = False
    db.commit()
    db.close()

    login = client.post("/api/v1/auth/login", json={
        "username": "newuser", "password": "password123",
    })
    token = login.json()["data"]["access_token"]
    admin_id = resp_id_from_list("mgmt_admin")

    resp = client.put(f"/api/v1/users/{admin_id}", json={
        "display_name": "篡改",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def resp_id_from_list(username):
    """从用户列表获取指定用户 ID"""
    resp = client.get("/api/v1/users", headers=_auth())
    users = resp.json()["data"]["items"]
    return next(u["id"] for u in users if u["username"] == username)
