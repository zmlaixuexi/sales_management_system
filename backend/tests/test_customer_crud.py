"""客户 CRUD 成功路径测试：详情、编辑、删除、转移"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_customer_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_customer_id: str = ""
_admin_id: str = ""
_second_user_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _customer_id, _admin_id, _second_user_id
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        admin = User(
            id=uuid.uuid4(),
            username="crud_admin",
            hashed_password=hash_password("testpass123"),
            display_name="CRUD管理员",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        _admin_id = str(admin.id)

        second = User(
            id=uuid.uuid4(),
            username="second_user",
            hashed_password=hash_password("testpass123"),
            display_name="第二销售员",
            is_active=True,
            is_superuser=True,
        )
        db.add(second)
        _second_user_id = str(second.id)

        customer = Customer(
            id=uuid.uuid4(),
            name="测试客户",
            phone="13800001001",
            contact_name="张三",
            email="zhang@test.com",
            source="online",
            level="normal",
            owner_user_id=admin.id,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(customer)
        _customer_id = str(customer.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_customer_crud.db"):
        os.remove("./test_customer_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    resp = client.post("/api/v1/auth/login", json={
        "username": "crud_admin", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_get_customer_detail():
    """获取客户详情"""
    resp = client.get(f"/api/v1/customers/{_customer_id}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "测试客户"
    assert data["phone"] == "13800001001"
    assert data["contact_name"] == "张三"
    assert data["email"] == "zhang@test.com"
    assert data["source"] == "online"
    assert data["level"] == "normal"
    assert data["owner_name"] == "CRUD管理员"


def test_03_get_customer_not_found():
    """获取不存在的客户"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/customers/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_03b_list_customers_by_source():
    """按来源筛选客户"""
    resp = client.get("/api/v1/customers", params={"source": "online"}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert all(c["source"] == "online" for c in items)


def test_03c_list_customers_by_keyword():
    """关键词搜索客户"""
    resp = client.get("/api/v1/customers", params={"keyword": "测试"}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert any("测试" in c["name"] for c in items)


def test_04_update_customer():
    """编辑客户"""
    resp = client.put(f"/api/v1/customers/{_customer_id}", json={
        "name": "更新后客户",
        "contact_name": "李四",
        "level": "vip",
    }, headers=_auth())
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]


def test_05_verify_update():
    """验证编辑结果"""
    resp = client.get(f"/api/v1/customers/{_customer_id}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "更新后客户"
    assert data["contact_name"] == "李四"
    assert data["level"] == "vip"


def test_06_transfer_customer():
    """转移客户归属"""
    resp = client.post(f"/api/v1/customers/{_customer_id}/transfer", json={
        "owner_user_id": _second_user_id,
    }, headers=_auth())
    assert resp.status_code == 200
    assert "转移" in resp.json()["message"]


def test_07_verify_transfer():
    """验证转移结果"""
    resp = client.get(f"/api/v1/customers/{_customer_id}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["owner_user_id"] == _second_user_id
    assert data["owner_name"] == "第二销售员"


def test_08_delete_customer():
    """软删除客户"""
    resp = client.delete(f"/api/v1/customers/{_customer_id}", headers=_auth())
    assert resp.status_code == 200
    assert "删除成功" in resp.json()["message"]


def test_09_verify_deleted():
    """验证删除后不可见"""
    resp = client.get(f"/api/v1/customers/{_customer_id}", headers=_auth())
    assert resp.status_code == 404
