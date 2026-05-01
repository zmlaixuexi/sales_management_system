"""客户 CSV 批量导入测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_customer_import.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="customer_importer",
            hashed_password=hash_password("testpass123"),
            display_name="客户导入员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_customer_import.db"):
        os.remove("./test_customer_import.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "customer_importer", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_import_csv_success():
    """CSV 批量导入成功"""
    csv_content = (
        "客户名称,电话,联系人,邮箱\n"
        "测试客户A,13800001111,张三,a@test.com\n"
        "测试客户B,13800002222,李四,b@test.com"
    )
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert len(data["errors"]) == 0
    assert "成功导入 2" in resp.json()["message"]


def test_03_import_with_details():
    """CSV 导入带来源和等级"""
    csv_content = "客户名称,电话,来源,等级\nVIP客户,13900001111,online,vip"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_04_import_duplicate_phone():
    """CSV 导入手机号重复跳过"""
    csv_content = "客户名称,电话\n重复手机客户,13800001111"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


def test_05_import_duplicate_in_batch():
    """CSV 批量内手机号重复"""
    csv_content = "客户名称,电话\n客户X,13899991111\n客户Y,13899991111"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
    assert len(resp.json()["data"]["errors"]) == 1


def test_06_import_empty_name():
    """CSV 导入空名称跳过"""
    csv_content = "客户名称,电话\n,13800009999"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_07_import_non_csv():
    """上传非 CSV 文件报错"""
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_08_import_requires_auth():
    """导入需要认证"""
    csv_content = "客户名称,电话\n测试,13800008888"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 401


def test_09_import_file_too_large(monkeypatch):
    """超过大小限制的 CSV 文件被拒绝"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_SIZE_MB", 0)
    csv_content = "客户名称,电话\n测试,13800008888"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "CSV 文件不能超过" in resp.json()["detail"]["message"]


def test_10_import_row_limit(monkeypatch):
    """超过行数上限的 CSV 只导入前 N 行"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_ROWS", 2)
    rows = "\n".join([f"客户{ i},138000{i:05d}" for i in range(4)])
    csv_content = f"客户名称,电话\n{rows}"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert any("超过最大行数限制" in e["message"] for e in data["errors"])


def test_11_import_strips_html():
    """CSV 导入自动剥离 HTML 标签"""
    csv_content = '客户名称,电话,联系人,邮箱\n<script>x</script>安全客户,13800007777,<b>张</b>,a@b.com'
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
