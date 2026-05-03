"""角色管理 CRUD 测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import Permission, Role, RolePermission, User, UserRole

TEST_DB_URL = "sqlite:///./test_roles_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_admin_id: str = ""
_role_id: str = ""
_perm_id_1: str = ""
_perm_id_2: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _admin_id, _role_id, _perm_id_1, _perm_id_2
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        admin = User(
            id=uuid.uuid4(),
            username="roles_admin",
            hashed_password=hash_password("TestPass123!"),
            display_name="角色管理员",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        _admin_id = str(admin.id)

        p1 = Permission(id=uuid.uuid4(), code="user:list", name="查看用户列表", module="用户管理")
        p2 = Permission(id=uuid.uuid4(), code="product:list", name="查看商品列表", module="商品管理")
        db.add_all([p1, p2])
        _perm_id_1 = str(p1.id)
        _perm_id_2 = str(p2.id)

        role = Role(id=uuid.uuid4(), name="test_role", display_name="测试角色", description="已有角色")
        db.add(role)
        _role_id = str(role.id)

        rp = RolePermission(id=uuid.uuid4(), role_id=role.id, permission_id=p1.id)
        db.add(rp)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_roles_crud.db"):
        os.remove("./test_roles_crud.db")
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
        "username": "roles_admin", "password": "TestPass123!",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_list_roles():
    """获取角色列表"""
    resp = client.get("/api/v1/roles", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


def test_03_list_roles_contains_permissions():
    """角色列表包含权限详情"""
    resp = client.get("/api/v1/roles", headers=_auth())
    assert resp.status_code == 200
    roles = resp.json()["data"]
    test_role = next((r for r in roles if r["name"] == "test_role"), None)
    assert test_role is not None
    assert len(test_role["permissions"]) >= 1
    assert test_role["permissions"][0]["code"] == "user:list"


def test_04_list_roles_contains_user_count():
    """角色列表包含用户数"""
    resp = client.get("/api/v1/roles", headers=_auth())
    assert resp.status_code == 200
    roles = resp.json()["data"]
    test_role = next((r for r in roles if r["name"] == "test_role"), None)
    assert test_role is not None
    assert test_role["user_count"] == 0


def test_05_list_permissions():
    """获取所有权限（按模块分组）"""
    resp = client.get("/api/v1/roles/permissions", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, dict)
    assert "用户管理" in data
    assert "商品管理" in data


def test_06_create_role():
    """创建新角色"""
    resp = client.post("/api/v1/roles", json={
        "name": "new_role",
        "display_name": "新角色",
        "description": "测试创建",
        "permission_ids": [_perm_id_1, _perm_id_2],
    }, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "new_role"
    assert data["display_name"] == "新角色"
    assert len(data["permissions"]) == 2


def test_07_create_role_duplicate_name():
    """创建同名角色返回 400"""
    resp = client.post("/api/v1/roles", json={
        "name": "test_role",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "已存在" in resp.json()["error"]["message"]


def test_08_update_role():
    """编辑角色"""
    resp = client.put(f"/api/v1/roles/{_role_id}", json={
        "display_name": "更新角色名",
        "description": "更新描述",
        "permission_ids": [_perm_id_2],
    }, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["display_name"] == "更新角色名"
    assert data["description"] == "更新描述"
    assert len(data["permissions"]) == 1
    assert data["permissions"][0]["code"] == "product:list"


def test_09_update_role_rename():
    """编辑角色名称"""
    resp = client.put(f"/api/v1/roles/{_role_id}", json={
        "name": "test_role_renamed",
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "test_role_renamed"


def test_10_update_role_duplicate_name():
    """编辑角色为已存在的名称返回 400"""
    resp = client.put(f"/api/v1/roles/{_role_id}", json={
        "name": "new_role",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "已存在" in resp.json()["error"]["message"]


def test_11_update_nonexistent_role():
    """编辑不存在的角色返回 404"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/roles/{fake_id}", json={
        "name": "ghost",
    }, headers=_auth())
    assert resp.status_code == 404


def test_12_delete_role_no_users():
    """删除无用户关联的角色"""
    # 创建一个临时角色并删除
    resp = client.post("/api/v1/roles", json={
        "name": "to_delete",
        "display_name": "待删除",
    }, headers=_auth())
    assert resp.status_code == 200
    role_id = resp.json()["data"]["id"]

    resp = client.delete(f"/api/v1/roles/{role_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["message"] == "删除成功"


def test_13_delete_role_with_users():
    """删除有用户关联的角色返回 400"""
    # 将管理员关联到 test_role
    db = TestSession()
    try:
        ur = UserRole(id=uuid.uuid4(), user_id=uuid.UUID(_admin_id), role_id=uuid.UUID(_role_id))
        db.add(ur)
        db.commit()
    finally:
        db.close()

    resp = client.delete(f"/api/v1/roles/{_role_id}", headers=_auth())
    assert resp.status_code == 400
    assert "用户" in resp.json()["error"]["message"]


def test_14_delete_nonexistent_role():
    """删除不存在的角色返回 404"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/roles/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_15_create_role_invalid_permission():
    """创建角色时使用不存在的权限 ID 返回 400"""
    fake_perm = str(uuid.uuid4())
    resp = client.post("/api/v1/roles", json={
        "name": "bad_perm_role",
        "permission_ids": [fake_perm],
    }, headers=_auth())
    assert resp.status_code == 400


def test_16_list_roles_no_auth():
    """未认证访问返回 401"""
    resp = client.get("/api/v1/roles")
    assert resp.status_code == 401


def test_17_create_role_empty_name():
    """角色名为空返回 422"""
    resp = client.post("/api/v1/roles", json={
        "name": "",
    }, headers=_auth())
    assert resp.status_code == 422


def test_18_update_role_empty_permissions():
    """编辑角色清空权限"""
    # 创建新角色带权限然后清空
    resp = client.post("/api/v1/roles", json={
        "name": "clear_perms",
        "permission_ids": [_perm_id_1],
    }, headers=_auth())
    assert resp.status_code == 200
    role_id = resp.json()["data"]["id"]
    assert len(resp.json()["data"]["permissions"]) == 1

    resp = client.put(f"/api/v1/roles/{role_id}", json={
        "permission_ids": [],
    }, headers=_auth())
    assert resp.status_code == 200
    assert len(resp.json()["data"]["permissions"]) == 0
