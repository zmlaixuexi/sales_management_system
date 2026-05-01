"""商品 CSV 批量导入测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_product_import.db"
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
            username="import_tester",
            hashed_password=hash_password("testpass123"),
            display_name="导入测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_product_import.db"):
        os.remove("./test_product_import.db")
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
        "username": "import_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_import_csv_success():
    """CSV 批量导入成功"""
    csv_content = "商品名称,销售价,成本价,库存数量\n测试商品A,100.00,50.00,20\n测试商品B,200.00,80.00,10"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert len(data["errors"]) == 0
    assert "成功导入 2" in resp.json()["message"]


def test_03_import_with_sku():
    """CSV 导入带自定义 SKU"""
    csv_content = "商品名称,SKU,销售价\n自定义SKU商品,IMP-001,150.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_04_import_duplicate_sku():
    """CSV 导入 SKU 重复跳过"""
    csv_content = "商品名称,SKU,销售价\n重复SKU商品,IMP-001,99.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


def test_05_import_empty_name():
    """CSV 导入空名称跳过"""
    csv_content = "商品名称,销售价\n,100.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_06_import_non_csv():
    """上传非 CSV 文件报错"""
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_07_import_requires_auth():
    """导入需要认证"""
    csv_content = "商品名称,销售价\n测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 401


def test_08_import_chinese_headers():
    """CSV 使用中文表头"""
    csv_content = "商品名称,销售价,成本价,库存数量\n中文表头商品,88.00,44.00,5"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8-sig"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_09_import_file_too_large(monkeypatch):
    """超过大小限制的 CSV 文件被拒绝"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_SIZE_MB", 0)  # 设置极小限制
    csv_content = "商品名称,销售价\n测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "CSV 文件不能超过" in resp.json()["detail"]["message"]


def test_10_import_row_limit(monkeypatch):
    """超过行数上限的 CSV 只导入前 N 行"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_ROWS", 3)
    rows = "\n".join([f"商品{ i},100,50,10" for i in range(5)])
    csv_content = f"商品名称,销售价,成本价,库存数量\n{rows}"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 3
    assert any("超过最大行数限制" in e["message"] for e in data["errors"])


def test_11_import_strips_html():
    """CSV 导入自动剥离 HTML 标签"""
    csv_content = '商品名称,销售价\n<script>alert(1)</script>安全商品,99.00'
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
