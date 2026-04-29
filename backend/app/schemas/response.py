from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict | list | None = None
    message: str = "操作成功"
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict
    request_id: str | None = None


class PaginatedData(BaseModel):
    items: list
    page: int
    page_size: int
    total: int
