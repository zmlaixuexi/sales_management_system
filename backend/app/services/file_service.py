"""文件上传、校验、存储服务"""

import uuid
from datetime import datetime
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.product import File

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024

# 文件头魔数字节映射
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF", b"WEBP"],
}


def _validate_image(filename: str, content_type: str, size: int) -> None:
    """校验图片类型和大小"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的图片类型: {ext}，仅支持 jpg/jpeg/png/webp")
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"不支持的 MIME 类型: {content_type}")
    if size > MAX_SIZE_BYTES:
        raise ValueError(f"图片大小超过限制: {size / 1024 / 1024:.1f}MB > {settings.MAX_IMAGE_SIZE_MB}MB")


def _validate_magic_bytes(content: bytes, content_type: str) -> None:
    """校验文件头魔数字节，防止伪装扩展名上传"""
    if not content:
        raise ValueError("文件内容为空")
    for sig in MAGIC_SIGNATURES[content_type]:
        if content.startswith(sig):
            return
    raise ValueError(f"文件内容与声明的类型 {content_type} 不匹配")


async def upload_image(db: Session, file: UploadFile, user_id: uuid.UUID | None = None) -> File:
    """上传图片文件并保存元数据"""
    content = await file.read()
    _validate_image(file.filename or "", file.content_type or "", len(content))
    _validate_magic_bytes(content, file.content_type or "")

    now = datetime.now()
    date_path = f"{now.year}/{now:02m}"
    storage_dir = Path(settings.UPLOAD_DIR) / "products" / date_path
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_uuid = uuid.uuid4()
    ext = Path(file.filename or "image.jpg").suffix.lower()
    stored_name = f"{file_uuid}{ext}"
    object_key = f"products/{date_path}/{stored_name}"
    full_path = storage_dir / stored_name

    async with aiofiles.open(full_path, "wb") as f:
        await f.write(content)

    public_url = f"{settings.UPLOAD_PUBLIC_BASE_URL}/products/{date_path}/{stored_name}"

    file_record = File(
        storage_type=settings.UPLOAD_STORAGE_TYPE,
        bucket="products",
        object_key=object_key,
        original_name=file.filename or "unknown",
        content_type=file.content_type or "image/jpeg",
        size_bytes=len(content),
        public_url=public_url,
        created_by=user_id,
    )
    db.add(file_record)
    db.flush()

    return file_record


def delete_file(db: Session, file_id: uuid.UUID) -> bool:
    """删除文件记录和物理文件"""
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        return False

    if file_record.object_key:
        full_path = Path(settings.UPLOAD_DIR) / file_record.object_key
        if full_path.exists():
            full_path.unlink()

    db.delete(file_record)
    return True
