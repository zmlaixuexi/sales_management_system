"""文件服务校验函数单元测试"""

from datetime import UTC

import pytest
from fastapi import HTTPException

from app.services.file_service import _validate_image


def test_validate_image_bad_extension():
    with pytest.raises(HTTPException, match="不支持的图片类型"):
        _validate_image("file.gif", "image/gif", 100)


def test_validate_image_bad_mime():
    with pytest.raises(HTTPException, match="不支持的 MIME 类型"):
        _validate_image("file.jpg", "application/pdf", 100)


def test_validate_image_too_large():
    with pytest.raises(HTTPException, match="图片大小超过限制"):
        _validate_image("file.jpg", "image/jpeg", 100 * 1024 * 1024)


def test_validate_image_ok():
    _validate_image("file.jpg", "image/jpeg", 1024)


def test_validate_image_webp():
    _validate_image("photo.webp", "image/webp", 2048)


def test_validate_image_uppercase_extension():
    _validate_image("photo.JPG", "image/jpeg", 512)


def test_validate_image_extension_mime_mismatch():
    """扩展名 jpg 但 MIME 是 image/png 应通过（校验各自独立）"""
    _validate_image("file.jpg", "image/png", 1024)


def test_validate_image_exactly_at_limit():
    """文件大小恰好等于限制值应通过"""
    from app.services.file_service import MAX_SIZE_BYTES

    _validate_image("file.jpg", "image/jpeg", MAX_SIZE_BYTES)


def test_validate_image_one_byte_over_limit():
    """文件大小超限 1 字节应拒绝"""
    from app.services.file_service import MAX_SIZE_BYTES

    with pytest.raises(HTTPException, match="超过限制"):
        _validate_image("file.jpg", "image/jpeg", MAX_SIZE_BYTES + 1)


# ─── _validate_magic_bytes ──────────────────────────────────


def test_validate_magic_bytes_valid_jpeg():
    from app.services.file_service import _validate_magic_bytes

    _validate_magic_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")


def test_validate_magic_bytes_valid_png():
    from app.services.file_service import _validate_magic_bytes

    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    _validate_magic_bytes(png_header, "image/png")


def test_validate_magic_bytes_invalid():
    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException, match="不匹配"):
        _validate_magic_bytes(b"GIF89a" + b"\x00" * 100, "image/jpeg")


def test_validate_magic_bytes_empty():
    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException, match="为空"):
        _validate_magic_bytes(b"", "image/jpeg")


# ─── cleanup_orphan_files ──────────────────────────────────


def test_cleanup_orphan_files_removes_old_unbound(tmp_path):
    """超过 24 小时未绑定商品的文件被清理"""
    import uuid
    from datetime import datetime, timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.product import Base, File

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    upload_dir = tmp_path / "uploads" / "products"
    upload_dir.mkdir(parents=True)

    # 创建一个旧文件（25 小时前）
    old_file = File(
        id=uuid.uuid4(),
        storage_type="local",
        bucket="products",
        object_key="products/old.jpg",
        original_name="old.jpg",
        content_type="image/jpeg",
        size_bytes=100,
        public_url="/uploads/products/old.jpg",
        created_at=datetime.now(UTC) - timedelta(hours=25),
    )
    db.add(old_file)
    db.flush()

    # 创建旧文件的物理文件
    (upload_dir / "old.jpg").write_bytes(b"old")

    # 用 monkeypatch 无法直接使用，手动替换 UPLOAD_DIR
    import app.services.file_service as fs_mod
    original_upload_dir = fs_mod.settings.UPLOAD_DIR
    fs_mod.settings.UPLOAD_DIR = str(tmp_path / "uploads")

    try:
        count = fs_mod.cleanup_orphan_files(db, max_age_hours=24)
    finally:
        fs_mod.settings.UPLOAD_DIR = original_upload_dir

    assert count == 1
    assert db.query(File).count() == 0
    assert not (upload_dir / "old.jpg").exists()


def test_cleanup_orphan_files_keeps_bound_files(tmp_path):
    """已绑定商品的文件不被清理"""
    import uuid
    from datetime import datetime, timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.product import Base, File, Product, ProductImage

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    # 创建商品
    product = Product(
        id=uuid.uuid4(),
        name="测试商品",
        sku="TEST-001",
        cost_price=10,
        sale_price=20,
    )
    db.add(product)
    db.flush()

    # 创建一个旧但已绑定的文件
    bound_file = File(
        id=uuid.uuid4(),
        storage_type="local",
        original_name="bound.jpg",
        content_type="image/jpeg",
        size_bytes=100,
        created_at=datetime.now(UTC) - timedelta(hours=25),
    )
    db.add(bound_file)
    db.flush()

    pi = ProductImage(
        id=uuid.uuid4(),
        product_id=product.id,
        file_id=bound_file.id,
    )
    db.add(pi)
    db.flush()

    import app.services.file_service as fs_mod
    count = fs_mod.cleanup_orphan_files(db, max_age_hours=24)

    assert count == 0
    assert db.query(File).count() == 1


def test_cleanup_orphan_files_keeps_recent_unbound(tmp_path):
    """未绑定但不超过 24 小时的文件不被清理"""
    import uuid
    from datetime import datetime

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.product import Base, File

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    recent_file = File(
        id=uuid.uuid4(),
        storage_type="local",
        original_name="recent.jpg",
        content_type="image/jpeg",
        size_bytes=100,
        created_at=datetime.now(UTC),
    )
    db.add(recent_file)
    db.flush()

    import app.services.file_service as fs_mod
    count = fs_mod.cleanup_orphan_files(db, max_age_hours=24)

    assert count == 0
    assert db.query(File).count() == 1


def test_cleanup_orphan_files_returns_count(tmp_path):
    """返回清理的文件数量"""
    import uuid
    from datetime import datetime, timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.product import Base, File

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    for _ in range(3):
        f = File(
            id=uuid.uuid4(),
            storage_type="local",
            original_name="old.jpg",
            content_type="image/jpeg",
            size_bytes=100,
            created_at=datetime.now(UTC) - timedelta(hours=30),
        )
        db.add(f)
    db.flush()

    import app.services.file_service as fs_mod
    count = fs_mod.cleanup_orphan_files(db, max_age_hours=24)

    assert count == 3


# ─── webp 魔数验证安全测试 ──────────────────────────────────


def test_validate_magic_bytes_webp_rejects_non_webp_riff():
    """非 WebP 的 RIFF 文件（如 WAV）不应通过 webp 验证"""
    from app.services.file_service import _validate_magic_bytes
    # RIFF 头但不是 WebP（WAV 格式）
    fake_wav = b"RIFF\x24\x08\x00\x00WAVD" + b"\x00" * 100
    with pytest.raises(HTTPException) as exc_info:
        _validate_magic_bytes(fake_wav, "image/webp")
    assert exc_info.value.status_code == 400


def test_validate_magic_bytes_webp_accepts_valid():
    """合法 WebP 文件通过验证"""
    from app.services.file_service import _validate_magic_bytes
    valid_webp = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    _validate_magic_bytes(valid_webp, "image/webp")  # 不抛异常


def test_validate_magic_bytes_webp_rejects_only_webp_no_riff():
    """只有 WEBP 头但缺少 RIFF 头不应通过"""
    from app.services.file_service import _validate_magic_bytes
    bad_content = b"WEBP" + b"\x00" * 100
    with pytest.raises(HTTPException) as exc_info:
        _validate_magic_bytes(bad_content, "image/webp")
    assert exc_info.value.status_code == 400
