"""文件上传 API"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.file_service import delete_file, upload_image

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/images")
async def upload_image_api(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传图片，返回文件 ID 和访问 URL"""
    try:
        file_record = await upload_image(db, file, current_user.id)
        db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILE_INVALID_TYPE", "message": str(e)},
        )

    return {
        "success": True,
        "data": {
            "id": str(file_record.id),
            "url": file_record.public_url,
            "original_name": file_record.original_name,
            "content_type": file_record.content_type,
            "size_bytes": file_record.size_bytes,
        },
        "message": "上传成功",
    }


@router.get("/images/{file_id}")
def get_image(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取图片信息"""
    from app.models.product import File

    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": "文件不存在"},
        )

    return {
        "success": True,
        "data": {
            "id": str(file_record.id),
            "url": file_record.public_url,
            "original_name": file_record.original_name,
            "content_type": file_record.content_type,
            "size_bytes": file_record.size_bytes,
        },
        "message": "查询成功",
    }


@router.delete("/images/{file_id}")
def delete_image(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除未被引用的图片"""
    if not delete_file(db, file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": "文件不存在"},
        )
    db.commit()

    return {"success": True, "data": None, "message": "删除成功"}
