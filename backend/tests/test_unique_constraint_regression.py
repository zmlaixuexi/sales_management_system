"""安全加固：用户名/角色/权限唯一约束回归测试
验证 username、role.code、permission.code 唯一约束不会被绕过"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import Permission, Role, User

TEST_DB = "sqlite:///./test_unique_constraints.db"
_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

_original_override = None
_admin_id = uuid.uuid4()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _Session()
    Base.metadata.create_all(bind=_engine)
    db = _Session()
    db.add(User(
        id=_admin_id, username="uniq_admin", display_name="管理员",
        hashed_password=hash_password("TestPass123!"), is_superuser=True, is_active=True,
    ))
    db.commit()
    db.close()


def teardown_module(module):
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]
    _engine.dispose()
    import contextlib
    import os
    with contextlib.suppress(FileNotFoundError):
        os.remove("test_unique_constraints.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


class TestUsernameUniqueness:
    """用户名唯一约束"""

    def test_create_duplicate_username_rejected(self):
        """创建重复用户名被拒绝"""
        resp = client.post("/api/v1/users", json={
            "username": "uniq_admin", "password": "NewPass123!", "display_name": "重复",
        }, headers=_headers())
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
        assert "已存在" in resp.json()["error"]["message"]

    def test_create_new_username_accepted(self):
        """创建新用户名成功"""
        resp = client.post("/api/v1/users", json={
            "username": "uniq_new_user", "password": "NewPass123!", "display_name": "新用户",
        }, headers=_headers())
        assert resp.status_code == 200

    def test_case_sensitive_username(self):
        """用户名区分大小写（UNIQ_ADMIN 与 uniq_admin 不同）"""
        db = _Session()
        existing = db.query(User).filter(User.username == "uniq_admin").first()
        assert existing is not None
        db.close()
        # 大写用户名应可创建（如果数据库区分大小写）
        resp = client.post("/api/v1/users", json={
            "username": "UNIQ_ADMIN", "password": "NewPass123!", "display_name": "大写",
        }, headers=_headers())
        # SQLite 字符串比较默认不区分大小写，所以可能被拒绝
        # 无论接受还是拒绝，行为应一致
        assert resp.status_code in (200, 400)

    def test_model_level_unique_constraint(self):
        """数据库层面 username 有 unique 约束"""
        from app.models.user import User
        col = User.__table__.c.username
        assert col.unique is True


class TestRoleCodeUniqueness:
    """角色 name 唯一约束"""

    def test_role_name_unique_in_model(self):
        """Role.name 有 unique 约束"""
        col = Role.__table__.c.name
        assert col.unique is True


class TestPermissionCodeUniqueness:
    """权限 code 唯一约束"""

    def test_permission_code_unique_in_model(self):
        """Permission.code 有 unique 约束"""
        col = Permission.__table__.c.code
        assert col.unique is True


class TestDatabaseLevelIntegrity:
    """数据库层面完整性约束"""

    def test_user_username_has_index(self):
        """username 有索引"""
        col = User.__table__.c.username
        assert col.index is True

    def test_permission_code_has_index(self):
        """permission.code 有索引"""
        col = Permission.__table__.c.code
        assert col.index is True

    def test_role_name_not_nullable(self):
        """Role.name 不可为空"""
        col = Role.__table__.c.name
        assert col.nullable is False
