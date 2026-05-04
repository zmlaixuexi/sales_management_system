"""需求符合性：后端分页参数默认值运行时验证
验证所有分页端点在未指定参数时使用正确默认值（page=1, page_size=20）"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB = "sqlite:///./test_pagination_defaults.db"
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
        id=_admin_id, username="pag_admin", display_name="管理员",
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
        os.remove("test_pagination_defaults.db")


client = TestClient(app)
_token = create_access_token(str(_admin_id))


def _headers():
    return {"Authorization": f"Bearer {_token}"}


class TestPaginationDefaults:
    """分页端点默认值验证"""

    def test_products_default_page_is_1(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1

    def test_products_default_page_size_is_20(self):
        resp = client.get("/api/v1/products", headers=_headers())
        data = resp.json()["data"]
        assert data["page_size"] == 20

    def test_customers_default_page_is_1(self):
        resp = client.get("/api/v1/customers", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["data"]["page"] == 1

    def test_customers_default_page_size_is_20(self):
        resp = client.get("/api/v1/customers", headers=_headers())
        assert resp.json()["data"]["page_size"] == 20

    def test_users_default_page_is_1(self):
        resp = client.get("/api/v1/users", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["data"]["page"] == 1

    def test_users_default_page_size_is_20(self):
        resp = client.get("/api/v1/users", headers=_headers())
        assert resp.json()["data"]["page_size"] == 20


class TestPaginationCustomValues:
    """自定义分页参数"""

    def test_products_page_2(self):
        resp = client.get("/api/v1/products?page=2", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["data"]["page"] == 2

    def test_products_custom_page_size(self):
        resp = client.get("/api/v1/products?page_size=5", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["data"]["page_size"] == 5

    def test_products_page_size_max_100(self):
        resp = client.get("/api/v1/products?page_size=100", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["data"]["page_size"] == 100

    def test_products_page_size_over_100_rejected(self):
        resp = client.get("/api/v1/products?page_size=101", headers=_headers())
        assert resp.status_code == 422

    def test_products_page_0_rejected(self):
        resp = client.get("/api/v1/products?page=0", headers=_headers())
        assert resp.status_code == 422

    def test_products_page_over_10000_rejected(self):
        resp = client.get("/api/v1/products?page=10001", headers=_headers())
        assert resp.status_code == 422

    def test_products_page_size_0_rejected(self):
        resp = client.get("/api/v1/products?page_size=0", headers=_headers())
        assert resp.status_code == 422

    def test_products_negative_page_rejected(self):
        resp = client.get("/api/v1/products?page=-1", headers=_headers())
        assert resp.status_code == 422


class TestPaginationResponseStructure:
    """分页响应结构"""

    def test_paginated_response_has_items(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert "items" in resp.json()["data"]

    def test_paginated_response_items_is_list(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert isinstance(resp.json()["data"]["items"], list)

    def test_paginated_response_has_total(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert "total" in resp.json()["data"]
        assert isinstance(resp.json()["data"]["total"], int)

    def test_total_non_negative(self):
        resp = client.get("/api/v1/products", headers=_headers())
        assert resp.json()["data"]["total"] >= 0
