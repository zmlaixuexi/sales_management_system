"""CSV 批量导入共享工具 — 文件校验和解析"""

import csv
import io

from fastapi import HTTPException, UploadFile

from app.core.config import settings


async def validate_csv_upload(file: UploadFile) -> csv.DictReader:
    """校验上传文件为合法 CSV 并返回 DictReader。

    校验：扩展名 .csv、大小限制、UTF-8 编码、非空表头。
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "请上传 CSV 文件",
        })

    content = await file.read()
    max_size = settings.MAX_CSV_IMPORT_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED",
            "message": f"CSV 文件不能超过 {settings.MAX_CSV_IMPORT_SIZE_MB}MB",
        })
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "文件编码错误，请使用 UTF-8",
        }) from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "CSV 文件为空或缺少表头",
        })

    return reader
