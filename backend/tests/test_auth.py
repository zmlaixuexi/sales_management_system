import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.api.v1.auth import _login_fail_counts
from app.core.security import create_access_token, create_refresh_token, hash_password
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


def test_refresh_invalid_token_401():
    """无效 refresh token 返回 401"""
    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid-token-value",
    })
    assert resp.status_code == 401


def test_refresh_access_token_rejected_401():
    """使用 access token 作为 refresh token 被拒绝"""
    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    access_token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token,
    })
    assert resp.status_code == 401


def test_change_password_audit_log():
    """修改密码产生审计日志"""
    from app.models.audit import AuditLog

    # 获取用户 ID
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user_id = str(user.id)
    finally:
        db.close()

    login_resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = login_resp.json()["data"]["access_token"]

    resp = client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "auditpass123",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # 直接查询数据库验证审计日志
    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "password_change",
            AuditLog.resource_id == user_id,
        ).first()
        assert log is not None
        assert log.resource_type == "user"
    finally:
        db.close()

    # 改回原密码
    login2 = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "auditpass123"})
    token2 = login2.json()["data"]["access_token"]
    client.post("/api/v1/auth/change-password", json={
        "old_password": "auditpass123",
        "new_password": "testpass123",
    }, headers={"Authorization": f"Bearer {token2}"})


def test_23_login_disabled_user_403():
    """禁用用户登录返回 403"""
    from app.core.security import hash_password
    from app.models.user import User

    db = TestSession()
    try:
        disabled = User(
            id=uuid.uuid4(), username="disabled_login_user",
            hashed_password=hash_password("testpass123"),
            display_name="禁用用户", is_active=False, is_superuser=False,
        )
        db.add(disabled)
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/auth/login", json={
        "username": "disabled_login_user",
        "password": "testpass123",
    })
    assert resp.status_code == 403


def test_24_login_sql_injection_safe():
    """用户名含 SQL 注入字符不会导致异常"""
    for malicious in [
        "' OR '1'='1",
        "admin'--",
        "'; DROP TABLE users;--",
        '" OR 1=1 --',
    ]:
        resp = client.post("/api/v1/auth/login", json={
            "username": malicious,
            "password": "anypass",
        })
        assert resp.status_code == 401, f"{malicious} should return 401"


# ─── JWT 过期边界验证 ───


def test_25_expired_access_token_rejected():
    """已过期的 access token 应返回 401"""
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user_id = str(user.id)
    finally:
        db.close()

    # 创建一个立刻过期的 token（expires_delta 为负数）
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-1),
    )

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_26_token_with_invalid_signature_rejected():
    """签名不正确的 token 应返回 401"""
    from jose import jwt as jose_jwt

    # 用错误密钥签发 token
    fake_payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
    }
    bad_token = jose_jwt.encode(fake_payload, "wrong-secret-key", algorithm="HS256")

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401


def test_27_token_missing_type_field_rejected():
    """缺少 type 字段的 token 应返回 401"""
    from jose import jwt as jose_jwt

    from app.core.config import settings

    payload = {"sub": str(uuid.uuid4())}
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_28_token_wrong_type_rejected():
    """type 字段为非 access 的 token 应返回 401"""
    from jose import jwt as jose_jwt

    from app.core.config import settings

    payload = {"sub": str(uuid.uuid4()), "type": "other"}
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_29_token_deleted_user_rejected():
    """已软删除用户的 token 应返回 401"""
    from app.core.security import hash_password
    from app.models.user import User

    # 创建临时用户
    temp_id = uuid.uuid4()
    db = TestSession()
    try:
        temp = User(
            id=temp_id, username="temp_del_user",
            hashed_password=hash_password("testpass123"),
            display_name="临时用户", is_active=True, is_superuser=False,
        )
        db.add(temp)
        db.commit()
    finally:
        db.close()

    token = create_access_token(subject=str(temp_id))

    # 软删除用户
    db = TestSession()
    try:
        from datetime import UTC, datetime

        temp = db.query(User).filter(User.id == temp_id).first()
        temp.deleted_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401

    # 清理
    db = TestSession()
    try:
        db.query(User).filter(User.id == temp_id).delete()
        db.commit()
    finally:
        db.close()


def test_30_token_nonexistent_user_rejected():
    """用户不存在时 token 应返回 401"""
    ghost_id = uuid.uuid4()
    token = create_access_token(subject=str(ghost_id))

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ─── JWT refresh token 边界验证 ───


def test_31_expired_refresh_token_rejected():
    """已过期的 refresh token 应返回 401"""
    from datetime import UTC, datetime, timedelta

    from jose import jwt as jose_jwt

    from app.core.config import settings

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user_id = str(user.id)
    finally:
        db.close()

    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "exp": now - timedelta(seconds=1),
        "iat": now - timedelta(seconds=100),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    expired_token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": expired_token})
    assert resp.status_code == 401


def test_32_refresh_token_wrong_signature_rejected():
    """错误签名的 refresh token 应返回 401"""
    from jose import jwt as jose_jwt

    fake_payload = {"sub": str(uuid.uuid4()), "type": "refresh", "jti": str(uuid.uuid4())}
    bad_token = jose_jwt.encode(fake_payload, "wrong-secret-key", algorithm="HS256")

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": bad_token})
    assert resp.status_code == 401


def test_33_refresh_token_nonexistent_user_rejected():
    """不存在用户的 refresh token 应返回 401"""
    ghost_id = uuid.uuid4()
    token = create_refresh_token(subject=str(ghost_id))

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 401


def test_34_refresh_token_missing_type_rejected():
    """缺少 type 字段的 refresh token 应返回 401"""
    from jose import jwt as jose_jwt

    from app.core.config import settings

    payload = {"sub": str(uuid.uuid4()), "jti": str(uuid.uuid4())}
    token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 401


# ─── 用户禁用后 token 立即失效 ───


def test_35_disabled_user_access_token_immediately_invalid():
    """用户禁用后，已发放的 access token 立即返回 401"""
    # 用正常用户登录获取 token
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "testpass123",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]

    # 先验证 token 正常工作
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # 禁用用户
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    # 同一个 token 现在应该返回 401
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401

    # 恢复用户状态
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user.is_active = True
        db.commit()
    finally:
        db.close()


def test_36_disabled_user_refresh_token_immediately_invalid():
    """用户禁用后，已发放的 refresh token 立即返回 401"""
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "testpass123",
    })
    assert login_resp.status_code == 200
    refresh = login_resp.json()["data"]["refresh_token"]

    # 禁用用户
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    # refresh token 应被拒绝
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401

    # 恢复用户状态
    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "testuser").first()
        user.is_active = True
        db.commit()
    finally:
        db.close()
