"""用户辅助函数单元测试 — _validate_roles_exist"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.users import _validate_roles_exist
from app.db.session import Base
from app.models.user import Role


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = maker()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_validate_roles_exist_all_found(db):
    """所有角色 ID 存在时不抛异常"""
    rid1 = uuid.uuid4()
    rid2 = uuid.uuid4()
    db.add(Role(id=rid1, name="admin", display_name="管理员"))
    db.add(Role(id=rid2, name="sales", display_name="销售"))
    db.commit()
    _validate_roles_exist(db, [rid1, rid2])  # 不抛异常


def test_validate_roles_exist_missing(db):
    """有不存在的角色 ID 时抛 400"""
    rid = uuid.uuid4()
    db.add(Role(id=rid, name="admin", display_name="管理员"))
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        _validate_roles_exist(db, [rid, uuid.uuid4()])
    assert exc_info.value.status_code == 400
    assert "角色不存在" in str(exc_info.value.detail)


def test_validate_roles_exist_empty_list(db):
    """空列表不抛异常"""
    _validate_roles_exist(db, [])  # 不抛异常


def test_validate_roles_exist_all_missing(db):
    """所有角色 ID 不存在时抛 400"""
    with pytest.raises(HTTPException) as exc_info:
        _validate_roles_exist(db, [uuid.uuid4(), uuid.uuid4()])
    assert exc_info.value.status_code == 400
