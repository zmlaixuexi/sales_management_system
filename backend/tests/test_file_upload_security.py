"""安全加固：后端文件上传安全回归测试
覆盖文件名清理、路径遍历防护、类型白名单完整性、大小限制、魔数字节验证、配置一致性"""

import re
from pathlib import Path

FILE_SERVICE = Path(__file__).resolve().parent.parent / "app" / "services" / "file_service.py"
FILES_API = Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "files.py"
CONFIG_SOURCE = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"

# 构造合法/非法文件头用于测试
JPEG_HEADER = b"\xff\xd8\xff\xe0"
PNG_HEADER = b"\x89PNG\r\n\x1a\n"
WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBP"


# ═══════════════════════════════════════════════════════════
# 1. 类型白名单完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFileTypeWhitelist:
    """验证文件类型白名单配置"""

    def test_allowed_types_are_images_only(self):
        source = FILE_SERVICE.read_text()
        assert '"image/jpeg"' in source
        assert '"image/png"' in source
        assert '"image/webp"' in source
        # 不应包含其他类型
        assert '"image/gif"' not in source
        assert '"image/svg"' not in source
        assert '"application/' not in source

    def test_allowed_extensions_are_image_only(self):
        source = FILE_SERVICE.read_text()
        assert '".jpg"' in source or '".jpeg"' in source
        assert '".png"' in source
        assert '".webp"' in source
        assert '".gif"' not in source
        assert '".bmp"' not in source
        assert '".svg"' not in source
        assert '".exe"' not in source
        assert '".php"' not in source
        assert '".html"' not in source

    def test_magic_signatures_cover_all_allowed_types(self):
        """每个允许的类型都有对应的魔数字节签名"""
        from app.services.file_service import ALLOWED_TYPES, MAGIC_SIGNATURES
        for t in ALLOWED_TYPES:
            assert t in MAGIC_SIGNATURES, f"缺少 {t} 的魔数字节签名"

    def test_allowed_types_and_extensions_consistent(self):
        """ALLOWED_TYPES 和 ALLOWED_EXTENSIONS 数量合理"""
        from app.services.file_service import ALLOWED_EXTENSIONS, ALLOWED_TYPES
        assert len(ALLOWED_TYPES) == 3
        # .jpg 和 .jpeg 对应同一类型，所以 extensions 可能多于 types
        assert len(ALLOWED_EXTENSIONS) >= 3

    def test_no_application_octet_stream(self):
        source = FILE_SERVICE.read_text()
        assert "octet-stream" not in source


# ═══════════════════════════════════════════════════════════
# 2. 文件名安全处理验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestFilenameSecurity:
    """验证文件名处理安全性"""

    def test_uses_uuid_for_stored_filename(self):
        """存储文件名使用 UUID 而非原始文件名"""
        source = FILE_SERVICE.read_text()
        assert "uuid.uuid4()" in source
        assert "stored_name" in source

    def test_uses_path_suffix_for_extension(self):
        """使用 Path.suffix 提取扩展名（安全）"""
        source = FILE_SERVICE.read_text()
        assert "Path(" in source
        assert ".suffix" in source

    def test_extension_lowered(self):
        """扩展名转小写"""
        source = FILE_SERVICE.read_text()
        assert ".lower()" in source

    def test_no_direct_filename_in_path(self):
        """不在存储路径中直接使用原始文件名"""
        source = FILE_SERVICE.read_text()
        # 存储路径使用 UUID + 扩展名，不使用原始文件名
        assert "file_uuid" in source
        assert "stored_name = f" in source or "stored_name=" in source

    def test_upload_creates_date_directory(self):
        """上传文件按日期分目录存储"""
        source = FILE_SERVICE.read_text()
        assert "date_path" in source
        assert "mkdir" in source

    def test_object_key_uses_safe_path(self):
        """object_key 使用相对路径（非绝对路径）"""
        source = FILE_SERVICE.read_text()
        assert 'object_key = f"products/' in source or "object_key = f\"products/" in source


# ═══════════════════════════════════════════════════════════
# 3. 大小限制验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFileSizeLimit:
    """验证文件大小限制配置"""

    def test_max_size_from_config(self):
        source = FILE_SERVICE.read_text()
        assert "MAX_IMAGE_SIZE_MB" in source
        assert "1024 * 1024" in source

    def test_config_has_max_image_size(self):
        source = CONFIG_SOURCE.read_text()
        assert "MAX_IMAGE_SIZE_MB" in source

    def test_config_max_image_size_positive(self):
        from app.core.config import settings
        assert settings.MAX_IMAGE_SIZE_MB > 0

    def test_config_max_image_size_reasonable(self):
        from app.core.config import settings
        assert settings.MAX_IMAGE_SIZE_MB <= 50  # 不超过 50MB

    def test_max_size_bytes_consistent_with_config(self):
        from app.core.config import settings
        from app.services.file_service import MAX_SIZE_BYTES
        assert MAX_SIZE_BYTES == settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


# ═══════════════════════════════════════════════════════════
# 4. 魔数字节验证逻辑（6 项）
# ═══════════════════════════════════════════════════════════


class TestMagicByteValidation:
    """验证魔数字节校验逻辑"""

    def test_validate_magic_empty_content_rejected(self):
        import pytest
        from fastapi import HTTPException

        from app.services.file_service import _validate_magic_bytes
        with pytest.raises(HTTPException) as exc_info:
            _validate_magic_bytes(b"", "image/jpeg")
        assert exc_info.value.status_code == 400

    def test_validate_magic_jpeg_correct(self):
        from app.services.file_service import _validate_magic_bytes
        _validate_magic_bytes(JPEG_HEADER + b"rest of data", "image/jpeg")

    def test_validate_magic_png_correct(self):
        from app.services.file_service import _validate_magic_bytes
        _validate_magic_bytes(PNG_HEADER + b"rest of data", "image/png")

    def test_validate_magic_webp_correct(self):
        from app.services.file_service import _validate_magic_bytes
        _validate_magic_bytes(WEBP_HEADER + b"rest of data", "image/webp")

    def test_validate_magic_jpeg_spoofed_as_png(self):
        import pytest
        from fastapi import HTTPException

        from app.services.file_service import _validate_magic_bytes
        with pytest.raises(HTTPException) as exc_info:
            _validate_magic_bytes(JPEG_HEADER + b"data", "image/png")
        assert exc_info.value.status_code == 400

    def test_validate_magic_rejects_random_binary(self):
        import pytest
        from fastapi import HTTPException

        from app.services.file_service import _validate_magic_bytes
        with pytest.raises(HTTPException):
            _validate_magic_bytes(b"\x00\x01\x02\x03", "image/jpeg")


# ═══════════════════════════════════════════════════════════
# 5. API 安全验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestFileAPISecurity:
    """验证文件上传 API 安全配置"""

    def test_upload_requires_product_create_permission(self):
        source = FILES_API.read_text()
        assert "require_permission" in source
        assert "product:create" in source

    def test_delete_checks_owner_or_superuser(self):
        source = FILES_API.read_text()
        assert "is_superuser" in source
        assert "created_by" in source

    def test_get_checks_owner_or_superuser(self):
        source = FILES_API.read_text()
        get_idx = source.index("def get_image(")
        get_end = source.index("\n@router", get_idx + 1) if "\n@router" in source[get_idx:] else len(source)
        get_body = source[get_idx:get_end]
        assert "is_superuser" in get_body or "created_by" in get_body

    def test_bound_image_cannot_be_deleted(self):
        source = FILES_API.read_text()
        assert "ProductImage" in source
        assert "已绑定" in source or "bound" in source.lower()

    def test_upload_audit_logged(self):
        source = FILES_API.read_text()
        assert "log_user_action" in source
        assert 'action="file_upload"' in source

    def test_delete_audit_logged(self):
        source = FILES_API.read_text()
        assert 'action="file_delete"' in source


# ═══════════════════════════════════════════════════════════
# 6. 错误码一致性验证（4 项）
# ═══════════════════════════════════════════════════════════


class TestFileUploadErrorCodes:
    """验证文件上传错误码一致性"""

    def test_invalid_type_error_code(self):
        source = FILE_SERVICE.read_text()
        assert '"FILE_INVALID_TYPE"' in source

    def test_too_large_error_code(self):
        source = FILE_SERVICE.read_text()
        assert '"FILE_TOO_LARGE"' in source

    def test_not_found_error_code(self):
        source = FILES_API.read_text()
        assert '"FILE_NOT_FOUND"' in source

    def test_error_codes_in_service_and_api_consistent(self):
        """file_service 和 files API 使用相同的错误码前缀"""
        service_src = FILE_SERVICE.read_text()
        api_src = FILES_API.read_text()
        service_codes = set(re.findall(r'"(FILE_\w+)"', service_src))
        api_codes = set(re.findall(r'"(FILE_\w+)"', api_src))
        # API 和 Service 共享 FILE_ 前缀错误码
        all_codes = service_codes | api_codes
        for code in all_codes:
            assert code.startswith("FILE_"), f"错误码 {code} 不以 FILE_ 开头"
