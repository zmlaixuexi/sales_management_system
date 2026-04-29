from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "操作成功"


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict | list | None = None
    message: str = "操作成功"
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict
    request_id: str | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
