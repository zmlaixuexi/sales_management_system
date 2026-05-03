"""文件上传 API"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission, resp, safe_commit
from app.models.product import File, ProductImage
from app.models.user import User
from app.services.audit_service import log_user_action
from app.services.file_service import delete_file, upload_image

router = APIRouter(
    prefix="/files", tags=["文件管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "文件类型不支持"},
        404: {"description": "文件不存在"},
    },
)


@router.post("/images")
async def upload_image_api(
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:create")),
):
    """上传图片，返回文件 ID 和访问 URL"""
    file_record = await upload_image(db, file, current_user.id)
    log_user_action(
        db, request, current_user,
        action="file_upload", resource_type="file",
        resource_id=str(file_record.id),
        after_data={"original_name": file_record.original_name, "size_bytes": file_record.size_bytes},
    )
    safe_commit(db)

    return resp({
        "id": str(file_record.id),
        "url": file_record.public_url,
        "original_name": file_record.original_name,
        "content_type": file_record.content_type,
        "size_bytes": file_record.size_bytes,
    }, "上传成功")


@router.get("/images/{file_id}")
def get_image(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取图片信息"""
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": "文件不存在"},
        )

    if not current_user.is_superuser and file_record.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限访问该文件"},
        )

    return resp({
        "id": str(file_record.id),
        "url": file_record.public_url,
        "original_name": file_record.original_name,
        "content_type": file_record.content_type,
        "size_bytes": file_record.size_bytes,
    })


@router.delete("/images/{file_id}")
def delete_image(
    file_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除未被引用的图片"""
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": "文件不存在"},
        )

    if not current_user.is_superuser and file_record.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权删除此文件"},
        )

    # 已绑定商品的图片不可删除
    bound = db.query(ProductImage).filter(ProductImage.file_id == file_id).first()
    if bound:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILE_NOT_BOUND", "message": "该图片已绑定商品，无法删除"},
        )

    log_user_action(
        db, request, current_user,
        action="file_delete", resource_type="file",
        resource_id=str(file_id),
        before_data={"original_name": file_record.original_name, "object_key": file_record.object_key},
    )
    delete_file(db, file_id)
    safe_commit(db)

    return resp(None, "删除成功")
