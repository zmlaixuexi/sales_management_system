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
    assert "已存在" in resp.json()["error"]["message"]


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


def test_12_update_user_invalid_role_ids():
    """编辑用户时传入不存在的角色 ID 返回 400"""
    user_id = resp_id_from_list("newuser")
    fake_role_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/users/{user_id}", json={
        "role_ids": [fake_role_id],
    }, headers=_auth())
    assert resp.status_code == 400
    assert "角色不存在" in resp.json()["error"]["message"]


def test_13_list_users_pagination():
    """用户列表分页"""
    resp = client.get("/api/v1/users?page=1&page_size=1", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] >= 2


def test_14_list_users_requires_auth():
    """用户列表需要认证"""
    resp = client.get("/api/v1/users")
    assert resp.status_code == 401


def test_15_create_user_weak_password_422():
    """创建用户弱密码被拒绝"""
    resp = client.post("/api/v1/users", json={
        "username": "weakpwuser",
        "password": "123456",
        "display_name": "弱密码用户",
    }, headers=_auth())
    assert resp.status_code == 422


def test_16_create_user_invalid_role_ids_400():
    """创建用户时传入不存在的角色 ID 返回 400"""
    fake_role_id = str(uuid.uuid4())
    resp = client.post("/api/v1/users", json={
        "username": "badroleuser",
        "password": "password123",
        "display_name": "无效角色用户",
        "role_ids": [fake_role_id],
    }, headers=_auth())
    assert resp.status_code == 400
    assert "角色不存在" in resp.json()["error"]["message"]


def test_17_list_roles():
    """角色列表返回已创建角色"""
    resp = client.get("/api/v1/users/roles", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert isinstance(items, list)
    assert any(r["name"] == "test_role" for r in items)
    role = next(r for r in items if r["name"] == "test_role")
    assert role["display_name"] == "测试角色"
    assert "id" in role


def test_18_list_roles_requires_admin():
    """非管理员不能查看角色列表"""
    db = TestSession()
    user = db.query(User).filter(User.username == "newuser").first()
    user.is_active = True
    db.commit()
    db.close()

    login = client.post("/api/v1/auth/login", json={
        "username": "newuser", "password": "password123",
    })
    token = login.json()["data"]["access_token"]

    resp = client.get("/api/v1/users/roles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_19_list_roles_requires_auth():
    """角色列表需要认证"""
    resp = client.get("/api/v1/users/roles")
    assert resp.status_code == 401


def test_20_cannot_deactivate_self():
    """管理员不能停用自己的账号"""
    resp = client.put(f"/api/v1/users/{_admin_id}", json={
        "is_active": False,
    }, headers=_auth())
    assert resp.status_code == 400
    assert "不能停用" in resp.json()["error"]["message"]


def test_21_list_users_non_admin_forbidden():
    """非管理员查看用户列表返回 403"""
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

    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_22_create_user_audit_log():
    """创建用户产生审计日志"""
    resp = client.post("/api/v1/users", json={
        "username": "audit_target",
        "password": "password123",
        "display_name": "审计目标用户",
    }, headers=_auth())
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/audit-logs?action=user_create", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["resource_type"] == "user"
    assert log["resource_id"] == uid
    assert log["after_data"]["username"] == "audit_target"


def test_23_update_user_audit_log():
    """编辑用户产生审计日志"""
    user_id = resp_id_from_list("audit_target")
    resp = client.put(f"/api/v1/users/{user_id}", json={
        "display_name": "审计后改名",
        "is_active": False,
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?action=user_update", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    log = items[0]
    assert log["resource_type"] == "user"
    assert log["after_data"]["display_name"] == "审计后改名"


def test_24_create_user_display_name_too_long_422():
    """display_name 超过 max_length 返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "longnameuser",
        "password": "password123",
        "display_name": "A" * 101,
    }, headers=_auth())
    assert resp.status_code == 422


def test_25_create_user_phone_too_long_422():
    """phone 超过 max_length 返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "longphoneuser",
        "password": "password123",
        "phone": "1" * 21,
    }, headers=_auth())
    assert resp.status_code == 422


def _admin_auth():
    from helpers import admin_auth_header
    return admin_auth_header(TestSession, "mgmt_admin")


def test_26_update_user_invalid_uuid_400():
    """无效 UUID 编辑用户返回 400"""
    resp = client.put("/api/v1/users/not-a-uuid", json={
        "display_name": "无效测试",
    }, headers=_admin_auth())
    assert resp.status_code == 400
    assert "格式无效" in resp.json()["error"]["message"]


def test_27_create_user_malformed_role_ids_400():
    """创建用户时 role_ids 含非 UUID 字符串返回 400"""
    resp = client.post("/api/v1/users", json={
        "username": "badroleuser",
        "password": "password123",
        "role_ids": ["not-a-uuid"],
    }, headers=_admin_auth())
    assert resp.status_code == 400
    assert "格式无效" in resp.json()["error"]["message"]


def test_28_update_user_empty_role_ids():
    """编辑用户 role_ids 为空列表清除所有角色"""
    resp = client.post("/api/v1/users", json={
        "username": "emptyroleuser",
        "password": "password123",
        "role_ids": [_role_id],
    }, headers=_admin_auth())
    assert resp.status_code == 200
    uid = resp.json()["data"]["id"]

    # 清空角色
    resp = client.put(f"/api/v1/users/{uid}", json={
        "role_ids": [],
    }, headers=_admin_auth())
    assert resp.status_code == 200

    # 通过列表确认角色已清空
    resp = client.get("/api/v1/users", params={"keyword": "emptyroleuser"}, headers=_admin_auth())
    items = resp.json()["data"]["items"]
    user = next(u for u in items if u["username"] == "emptyroleuser")
    assert user["roles"] == []


def test_29_create_user_password_no_digits_422():
    """创建用户密码仅含字母无数字返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "nodigituser",
        "password": "abcdefgh",
    }, headers=_admin_auth())
    assert resp.status_code == 422


def test_30_update_user_display_name_too_long_422():
    """编辑用户 display_name 超过 max_length 返回 422"""
    uid = resp_id_from_list("newuser")
    resp = client.put(f"/api/v1/users/{uid}", json={
        "display_name": "X" * 101,
    }, headers=_admin_auth())
    assert resp.status_code == 422


def test_31_list_users_keyword_like_injection():
    """关键字搜索含 % 不应匹配全部用户"""
    resp = client.get("/api/v1/users", params={"keyword": "%"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all("%" not in u.get("username", "") for u in items)


def test_32_list_users_keyword_like_underscore():
    """关键字搜索含 _ 不应匹配任意单字符，只返回实际含 _ 的用户"""
    resp = client.get("/api/v1/users", params={"keyword": "_"}, headers=_admin_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    # escape_like 应转义 _，所以搜索 _ 只匹配用户名中真正含 _ 的用户
    assert all("_" in u.get("username", "") for u in items)


def test_33_list_users_page_size_100():
    """用户列表 page_size=100（最大值）正常返回"""
    resp = client.get("/api/v1/users", params={"page_size": 100}, headers=_admin_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page_size"] == 100
    assert isinstance(data["items"], list)


def test_34_list_users_page_size_over_max_422():
    """用户列表 page_size=101 超出上限返回 422"""
    resp = client.get("/api/v1/users", params={"page_size": 101}, headers=_admin_auth())
    assert resp.status_code == 422


def test_35_create_user_password_too_short_422():
    """密码少于 6 位返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "shortpwuser",
        "password": "a1b2",
        "display_name": "短密码用户",
    }, headers=_admin_auth())
    assert resp.status_code == 422


def test_36_create_user_password_only_special_chars_422():
    """密码仅含特殊字符无字母数字返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "specialcharsuser",
        "password": "!@#$%^",
        "display_name": "特殊字符密码用户",
    }, headers=_admin_auth())
    assert resp.status_code == 422


def test_37_create_user_password_letters_and_special_no_digits_422():
    """密码含字母和特殊字符但无数字返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "nodigituser2",
        "password": "abc!@#$",
        "display_name": "无数字密码用户",
    }, headers=_admin_auth())
    assert resp.status_code == 422
    assert "数字" in str(resp.json())


def test_38_create_user_password_digits_and_special_no_letters_422():
    """密码含数字和特殊字符但无字母返回 422"""
    resp = client.post("/api/v1/users", json={
        "username": "noletteruser",
        "password": "123!@#$",
        "display_name": "无字母密码用户",
    }, headers=_admin_auth())
    assert resp.status_code == 422
    assert "字母" in str(resp.json())


def test_39_change_password_special_only_422():
    """修改密码为纯特殊字符返回 422"""
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "mgmt_admin", "password": "admin123",
    })
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "admin123",
        "new_password": "!@#$%^",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
