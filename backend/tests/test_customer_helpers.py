"""客户辅助函数单元测试 — _validate_owner_user"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.customers import _validate_owner_user
from app.core.security import hash_password
from app.db.session import Base
from app.models.user import User


@pytest.fixture()
def db():
    """每个测试独立内存 SQLite"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = maker()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_validate_owner_user_active(db):
    """活跃用户通过校验"""
    uid = uuid.uuid4()
    db.add(User(id=uid, username="owner", hashed_password=hash_password("x"),
                display_name="owner", is_active=True, is_superuser=False))
    db.commit()
    _validate_owner_user(db, uid)  # 不抛异常


def test_validate_owner_user_not_found(db):
    """用户不存在时抛 400"""
    with pytest.raises(HTTPException) as exc_info:
        _validate_owner_user(db, uuid.uuid4())
    assert exc_info.value.status_code == 400
    assert "归属用户不存在或已禁用" in str(exc_info.value.detail)


def test_validate_owner_user_inactive(db):
    """已禁用用户抛 400"""
    uid = uuid.uuid4()
    db.add(User(id=uid, username="inactive", hashed_password=hash_password("x"),
                display_name="u", is_active=False, is_superuser=False))
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        _validate_owner_user(db, uid)
    assert exc_info.value.status_code == 400


def test_validate_owner_user_soft_deleted(db):
    """软删除用户抛 400"""
    uid = uuid.uuid4()
    db.add(User(id=uid, username="deleted", hashed_password=hash_password("x"),
                display_name="u", is_active=True, is_superuser=False,
                deleted_at=datetime.now(UTC)))
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        _validate_owner_user(db, uid)
    assert exc_info.value.status_code == 400
