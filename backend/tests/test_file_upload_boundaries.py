"""异常路径：文件上传边界测试 — 覆盖允许的扩展名/MIME 类型、魔数验证、大小限制、
配置验证、模型字段、文件名安全、端点认证"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.file_service import ALLOWED_EXTENSIONS, ALLOWED_TYPES, MAGIC_SIGNATURES

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. 允许的文件扩展名
# ═══════════════════════════════════════════════════════


def test_allowed_extensions_contains_jpg():
    """允许 .jpg 扩展名"""
    assert ".jpg" in ALLOWED_EXTENSIONS


def test_allowed_extensions_contains_jpeg():
    """允许 .jpeg 扩展名"""
    assert ".jpeg" in ALLOWED_EXTENSIONS


def test_allowed_extensions_contains_png():
    """允许 .png 扩展名"""
    assert ".png" in ALLOWED_EXTENSIONS


def test_allowed_extensions_contains_webp():
    """允许 .webp 扩展名"""
    assert ".webp" in ALLOWED_EXTENSIONS


def test_allowed_extensions_count():
    """仅允许 4 种扩展名"""
    assert len(ALLOWED_EXTENSIONS) == 4


def test_allowed_extensions_no_svg():
    """不允许 .svg（XSS 风险）"""
    assert ".svg" not in ALLOWED_EXTENSIONS


def test_allowed_extensions_no_gif():
    """不允许 .gif"""
    assert ".gif" not in ALLOWED_EXTENSIONS


def test_allowed_extensions_no_bmp():
    """不允许 .bmp"""
    assert ".bmp" not in ALLOWED_EXTENSIONS


# ═══════════════════════════════════════════════════════
# 2. 允许的 MIME 类型
# ═══════════════════════════════════════════════════════


def test_allowed_types_contains_jpeg():
    """允许 image/jpeg"""
    assert "image/jpeg" in ALLOWED_TYPES


def test_allowed_types_contains_png():
    """允许 image/png"""
    assert "image/png" in ALLOWED_TYPES


def test_allowed_types_contains_webp():
    """允许 image/webp"""
    assert "image/webp" in ALLOWED_TYPES


def test_allowed_types_count():
    """仅允许 3 种 MIME 类型"""
    assert len(ALLOWED_TYPES) == 3


def test_allowed_types_no_svg():
    """不允许 image/svg+xml"""
    assert "image/svg+xml" not in ALLOWED_TYPES


def test_allowed_types_no_gif():
    """不允许 image/gif"""
    assert "image/gif" not in ALLOWED_TYPES


# ═══════════════════════════════════════════════════════
# 3. 魔数签名验证
# ═══════════════════════════════════════════════════════


def test_magic_signatures_jpeg():
    """JPEG 签名为 ff d8 ff"""
    assert MAGIC_SIGNATURES["image/jpeg"] == [b"\xff\xd8\xff"]


def test_magic_signatures_png():
    """PNG 签名为 89 50 4e 47 0d 0a 1a 0a"""
    assert MAGIC_SIGNATURES["image/png"] == [b"\x89PNG\r\n\x1a\n"]


def test_magic_signatures_webp():
    """WebP 需要 RIFF 和 WEBP 两个签名"""
    assert MAGIC_SIGNATURES["image/webp"] == [b"RIFF", b"WEBP"]


def test_magic_signatures_all_types_covered():
    """所有允许类型都有魔数签名"""
    for mime_type in ALLOWED_TYPES:
        assert mime_type in MAGIC_SIGNATURES, f"缺少 {mime_type} 的魔数签名"


# ═══════════════════════════════════════════════════════
# 4. _validate_image 验证函数
# ═══════════════════════════════════════════════════════


def test_validate_image_rejects_invalid_extension():
    """非法扩展名被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("test.exe", "image/jpeg", 100)


def test_validate_image_rejects_invalid_mime():
    """非法 MIME 类型被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("test.jpg", "application/pdf", 100)


def test_validate_image_rejects_oversize():
    """超大文件被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("test.jpg", "image/jpeg", settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1)


def test_validate_image_accepts_valid():
    """合法图片通过验证"""
    from app.services.file_service import _validate_image

    _validate_image("test.jpg", "image/jpeg", 1024)  # 不应抛异常


def test_validate_image_accepts_png():
    """合法 PNG 通过验证"""
    from app.services.file_service import _validate_image

    _validate_image("test.png", "image/png", 1024)


def test_validate_image_accepts_webp():
    """合法 WebP 通过验证"""
    from app.services.file_service import _validate_image

    _validate_image("test.webp", "image/webp", 1024)


def test_validate_image_rejects_exe():
    """拒绝 .exe"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("malware.exe", "image/jpeg", 100)


def test_validate_image_rejects_php():
    """拒绝 .php"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("shell.php", "image/jpeg", 100)


def test_validate_image_rejects_html():
    """拒绝 .html"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("xss.html", "text/html", 100)


def test_validate_image_rejects_svg():
    """拒绝 .svg"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    with pytest.raises(HTTPException):
        _validate_image("xss.svg", "image/svg+xml", 100)


# ═══════════════════════════════════════════════════════
# 5. _validate_magic_bytes 验证函数
# ═══════════════════════════════════════════════════════


def test_magic_bytes_rejects_empty():
    """空内容被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException):
        _validate_magic_bytes(b"", "image/jpeg")


def test_magic_bytes_rejects_wrong_jpeg():
    """非 JPEG 内容声明为 JPEG 被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException):
        _validate_magic_bytes(b"not a jpeg at all", "image/jpeg")


def test_magic_bytes_accepts_jpeg():
    """合法 JPEG 头通过验证"""
    from app.services.file_service import _validate_magic_bytes

    jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    _validate_magic_bytes(jpeg_header, "image/jpeg")  # 不应抛异常


def test_magic_bytes_accepts_png():
    """合法 PNG 头通过验证"""
    from app.services.file_service import _validate_magic_bytes

    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    _validate_magic_bytes(png_header, "image/png")


def test_magic_bytes_rejects_wrong_png():
    """非 PNG 内容声明为 PNG 被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException):
        _validate_magic_bytes(b"not png content here", "image/png")


def test_magic_bytes_rejects_php_as_jpeg():
    """PHP 文件声明为 JPEG 被魔数检查拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_magic_bytes

    with pytest.raises(HTTPException):
        _validate_magic_bytes(b"<?php echo 'hack'; ?>", "image/jpeg")


# ═══════════════════════════════════════════════════════
# 6. 文件大小配置验证
# ═══════════════════════════════════════════════════════


def test_max_image_size_positive():
    """MAX_IMAGE_SIZE_MB > 0"""
    assert settings.MAX_IMAGE_SIZE_MB > 0


def test_max_image_size_reasonable():
    """MAX_IMAGE_SIZE_MB 在合理范围内（1-100）"""
    assert 1 <= settings.MAX_IMAGE_SIZE_MB <= 100


def test_max_size_bytes_calculation():
    """MAX_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024"""
    from app.services.file_service import MAX_SIZE_BYTES

    assert MAX_SIZE_BYTES == settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


# ═══════════════════════════════════════════════════════
# 7. 上传目录配置
# ═══════════════════════════════════════════════════════


def test_upload_dir_configured():
    """UPLOAD_DIR 非空"""
    assert settings.UPLOAD_DIR


def test_upload_public_base_url_configured():
    """UPLOAD_PUBLIC_BASE_URL 非空"""
    assert settings.UPLOAD_PUBLIC_BASE_URL


def test_upload_storage_type():
    """UPLOAD_STORAGE_TYPE 为 'local'"""
    assert settings.UPLOAD_STORAGE_TYPE == "local"


# ═══════════════════════════════════════════════════════
# 8. File 模型字段验证
# ═══════════════════════════════════════════════════════


def test_file_model_has_required_fields():
    """File 模型包含必要字段"""
    from app.models.product import File

    for field in [
        "storage_type",
        "object_key",
        "original_name",
        "content_type",
        "size_bytes",
        "public_url",
        "created_by",
    ]:
        assert hasattr(File, field), f"File 模型缺少 {field}"


def test_product_image_model_exists():
    """ProductImage 模型存在"""
    from app.models.product import ProductImage

    assert hasattr(ProductImage, "product_id")
    assert hasattr(ProductImage, "file_id")


# ═══════════════════════════════════════════════════════
# 9. API 端点认证验证
# ═══════════════════════════════════════════════════════


def test_upload_requires_auth():
    """上传端点需要认证"""
    resp = client.post("/api/v1/files/images")
    assert resp.status_code in (401, 403, 422)


def test_get_file_info_requires_auth():
    """获取文件信息需要认证"""
    resp = client.get("/api/v1/files/images/00000000-0000-0000-0000-000000000001")
    assert resp.status_code in (401, 403, 404)


def test_delete_file_requires_auth():
    """删除文件需要认证"""
    resp = client.delete("/api/v1/files/images/00000000-0000-0000-0000-000000000001")
    assert resp.status_code in (401, 403, 404)


def test_upload_invalid_uuid():
    """非法 UUID 返回 422"""
    resp = client.get("/api/v1/files/images/not-a-uuid")
    assert resp.status_code in (401, 422)


# ═══════════════════════════════════════════════════════
# 10. 扩展名大小写不敏感
# ═══════════════════════════════════════════════════════


def test_validate_image_uppercase_extension():
    """大写扩展名通过验证（转为小写比较）"""
    from app.services.file_service import _validate_image

    _validate_image("test.JPG", "image/jpeg", 1024)


def test_validate_image_mixed_case_extension():
    """混合大小写扩展名通过验证"""
    from app.services.file_service import _validate_image

    _validate_image("test.JpG", "image/jpeg", 1024)


def test_validate_image_png_uppercase():
    """大写 .PNG 通过验证"""
    from app.services.file_service import _validate_image

    _validate_image("test.PNG", "image/png", 1024)


# ═══════════════════════════════════════════════════════
# 11. 边界大小值
# ═══════════════════════════════════════════════════════


def test_validate_image_exact_max_size():
    """恰好等于最大限制大小通过验证"""
    from app.services.file_service import _validate_image

    exact_max = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    _validate_image("test.jpg", "image/jpeg", exact_max)


def test_validate_image_one_byte_over():
    """超过最大限制 1 字节被拒绝"""
    from fastapi import HTTPException

    from app.services.file_service import _validate_image

    one_over = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1
    with pytest.raises(HTTPException):
        _validate_image("test.jpg", "image/jpeg", one_over)


def test_validate_image_zero_size():
    """0 字节通过扩展名/MIME 检查（魔数检查会拒绝空内容）"""
    from app.services.file_service import _validate_image

    _validate_image("test.jpg", "image/jpeg", 0)


# ═══════════════════════════════════════════════════════
# 12. StaticFiles 挂载
# ═══════════════════════════════════════════════════════


def test_uploads_static_mount_exists():
    """StaticFiles 挂载在 /uploads"""
    import app.main as mod

    with open(mod.__file__) as f:
        source = f.read()
    assert "/uploads" in source
    assert "StaticFiles" in source
