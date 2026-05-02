"""文件服务校验函数单元测试"""

import pytest

from app.services.file_service import _validate_image


def test_validate_image_bad_extension():
    with pytest.raises(ValueError, match="不支持的图片类型"):
        _validate_image("file.gif", "image/gif", 100)


def test_validate_image_bad_mime():
    with pytest.raises(ValueError, match="不支持的 MIME 类型"):
        _validate_image("file.jpg", "application/pdf", 100)


def test_validate_image_too_large():
    with pytest.raises(ValueError, match="图片大小超过限制"):
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

    with pytest.raises(ValueError, match="超过限制"):
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

    with pytest.raises(ValueError, match="不匹配"):
        _validate_magic_bytes(b"GIF89a" + b"\x00" * 100, "image/jpeg")


def test_validate_magic_bytes_empty():
    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(ValueError, match="为空"):
        _validate_magic_bytes(b"", "image/jpeg")
