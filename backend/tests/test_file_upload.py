"""文件上传集成测试 — 覆盖上传、校验、查询、删除"""

import os
import tempfile
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_file_upload.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_original_upload_dir = None
_tokens: dict = {}
_file_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _original_upload_dir
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    # 创建临时上传目录
    _original_upload_dir = tempfile.mkdtemp()
    from app.core import config
    config.settings.UPLOAD_DIR = _original_upload_dir

    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="file_tester",
            hashed_password=hash_password("testpass123"),
            display_name="文件测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    import shutil
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_file_upload.db"):
        os.remove("./test_file_upload.db")
    # 清理临时上传目录
    if _original_upload_dir and os.path.exists(_original_upload_dir):
        shutil.rmtree(_original_upload_dir, ignore_errors=True)
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def _make_png_bytes(size_kb: int = 1) -> bytes:
    """生成最小有效 PNG 字节"""
    # PNG 签名 + IHDR + IDAT + IEND（最小有效 PNG）
    import struct
    import zlib

    png_sig = b"\x89PNG\r\n\x1a\n"
    # IHDR: 1x1, 8bit RGB
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    # IDAT
    raw = zlib.compress(b"\x00\x00\x00\x00")
    idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
    idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
    # IEND
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    png = png_sig + ihdr + idat + iend
    # 如果需要更大文件，填充 IDAT
    if size_kb > 1:
        padding = b"\x00" * (size_kb * 1024 - len(png))
        raw2 = zlib.compress(b"\x00" + padding)
        idat_crc2 = zlib.crc32(b"IDAT" + raw2) & 0xFFFFFFFF
        idat2 = struct.pack(">I", len(raw2)) + b"IDAT" + raw2 + struct.pack(">I", idat_crc2)
        png = png_sig + ihdr + idat2 + iend
    return png


def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "file_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_upload_image_success():
    """上传 PNG 图片成功"""
    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("test.png", png_bytes, "image/png")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["original_name"] == "test.png"
    assert data["content_type"] == "image/png"
    assert data["size_bytes"] > 0
    assert "/uploads/" in data["url"]
    global _file_id
    _file_id = data["id"]


def test_03_get_image_info():
    """查询图片信息"""
    resp = client.get(f"/api/v1/files/images/{_file_id}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == _file_id
    assert data["original_name"] == "test.png"


def test_04_upload_invalid_type():
    """上传不支持的文件类型"""
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_INVALID_TYPE"


def test_05_upload_oversized():
    """上传超过大小限制的图片"""
    import app.services.file_service as fs
    old_max = fs.MAX_SIZE_BYTES
    fs.MAX_SIZE_BYTES = 10  # 10 字节限制
    png_bytes = _make_png_bytes(size_kb=1)
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("big.png", png_bytes, "image/png")},
        headers=_auth(),
    )
    fs.MAX_SIZE_BYTES = old_max
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_06_get_image_not_found():
    """查询不存在的文件"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/files/images/{fake_id}", headers=_auth())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_07_delete_image():
    """删除已上传的图片"""
    resp = client.delete(f"/api/v1/files/images/{_file_id}", headers=_auth())
    assert resp.status_code == 200
    # 删除后再查询应 404
    resp = client.get(f"/api/v1/files/images/{_file_id}", headers=_auth())
    assert resp.status_code == 404


def test_08_delete_not_found():
    """删除不存在的文件"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/files/images/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_09_upload_requires_auth():
    """上传需要认证"""
    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("test.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 401


def test_10_upload_fake_image_rejected():
    """伪装扩展名上传（非图片内容声明为 image/jpeg）应被拒绝"""
    fake_content = b"<html><body>malicious</body></html>"
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("fake.jpg", fake_content, "image/jpeg")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_INVALID_TYPE"


def test_11_upload_valid_jpeg_accepted():
    """上传有效 JPEG 文件头应成功"""
    # JPEG 最小文件头: FF D8 FF + 任意字节
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        headers=_auth(),
    )
    assert resp.status_code == 200


def test_12_upload_empty_content_rejected():
    """上传空内容的图片应被拒绝"""
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_INVALID_TYPE"


def test_13_upload_valid_webp_accepted():
    """上传有效 WebP 文件头应成功"""
    # WebP: RIFF....WEBP
    webp_bytes = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("photo.webp", webp_bytes, "image/webp")},
        headers=_auth(),
    )
    assert resp.status_code == 200


def test_14_delete_other_user_file_forbidden():
    """非所有者不能删除他人的文件"""
    # 上传文件（超级用户）
    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("owner.png", png_bytes, "image/png")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    file_id = resp.json()["data"]["id"]

    # 创建第二个普通用户
    other_user = User(
        id=uuid.uuid4(),
        username="file_other",
        hashed_password=hash_password("testpass123"),
        display_name="其他用户",
        is_active=True,
        is_superuser=False,
    )
    db = TestSession()
    db.add(other_user)
    db.commit()
    db.close()

    # 以第二个用户登录
    resp = client.post("/api/v1/auth/login", json={
        "username": "file_other", "password": "testpass123",
    })
    assert resp.status_code == 200
    other_token = resp.json()["data"]["access_token"]

    # 尝试删除第一个用户的文件
    resp = client.delete(
        f"/api/v1/files/images/{file_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_15_delete_file_service_returns_false_for_missing():
    """file_service.delete_file 对不存在的文件返回 False"""
    from app.services.file_service import delete_file

    db = TestSession()
    try:
        result = delete_file(db, uuid.uuid4())
        assert result is False
    finally:
        db.close()


def test_16_delete_bound_image_rejected():
    """已绑定商品的图片不可删除，返回 FILE_NOT_BOUND"""
    from app.models.product import Product, ProductCategory, ProductImage

    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("bound.png", png_bytes, "image/png")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    file_id = resp.json()["data"]["id"]

    db = TestSession()
    try:
        # 创建分类、商品并绑定该图片
        cat = ProductCategory(id=uuid.uuid4(), name="绑定测试分类", sort_order=0)
        db.add(cat)
        db.flush()
        product = Product(
            id=uuid.uuid4(), sku="SKU-BOUND-001", name="绑定测试商品",
            sale_price=100, cost_price=60, stock_quantity=10,
            category_id=cat.id, status="active",
            created_by=uuid.uuid4(), updated_by=uuid.uuid4(),
        )
        db.add(product)
        db.flush()
        pi = ProductImage(
            id=uuid.uuid4(), product_id=product.id,
            file_id=uuid.UUID(file_id), is_primary=True, sort_order=0,
        )
        db.add(pi)
        db.commit()
    finally:
        db.close()

    resp = client.delete(f"/api/v1/files/images/{file_id}", headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_NOT_BOUND"


# ── 异常路径测试 ──────────────────────────────────────────


def test_17_get_image_requires_auth():
    """获取图片信息需要认证返回 401"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/files/images/{fake_id}")
    assert resp.status_code == 401


def test_18_delete_image_requires_auth():
    """删除图片需要认证返回 401"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/files/images/{fake_id}")
    assert resp.status_code == 401


def test_19_get_image_invalid_uuid_422():
    """获取图片信息无效 UUID 格式返回 422"""
    resp = client.get("/api/v1/files/images/not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_20_delete_image_invalid_uuid_422():
    """删除图片无效 UUID 格式返回 422"""
    resp = client.delete("/api/v1/files/images/not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_21_upload_no_file_field_422():
    """上传不提供 file 字段返回 422"""
    resp = client.post("/api/v1/files/images", headers=_auth())
    assert resp.status_code == 422


def test_22_get_other_user_file_forbidden():
    """非所有者、非超级管理员查看他人文件返回 403"""
    # 先上传一个文件
    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/v1/files/images",
        files={"file": ("viewable.png", png_bytes, "image/png")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    file_id = resp.json()["data"]["id"]

    # 其他用户登录
    other_user = User(
        id=uuid.uuid4(),
        username="file_viewer",
        hashed_password=hash_password("testpass123"),
        display_name="查看用户",
        is_active=True,
        is_superuser=False,
    )
    db = TestSession()
    db.add(other_user)
    db.commit()
    db.close()

    resp = client.post("/api/v1/auth/login", json={
        "username": "file_viewer", "password": "testpass123",
    })
    other_token = resp.json()["data"]["access_token"]

    # 非所有者应被拒绝
    resp = client.get(
        f"/api/v1/files/images/{file_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403
