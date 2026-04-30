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
