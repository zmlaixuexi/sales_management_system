from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "操作成功"


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


# ── 通用错误响应文档（用于 OpenAPI responses 参数）──

COMMON_ERRORS: dict[int, dict] = {
    401: {"description": "未认证或令牌过期"},
    403: {"description": "无权限访问"},
}

NOT_FOUND: dict[int, dict] = {
    **COMMON_ERRORS,
    404: {"description": "资源不存在"},
}

VALIDATION_ERRORS: dict[int, dict] = {
    **COMMON_ERRORS,
    400: {"description": "请求参数错误"},
    404: {"description": "资源不存在"},
}

ALL_ERRORS: dict[int, dict] = {
    **COMMON_ERRORS,
    400: {"description": "请求参数错误"},
    404: {"description": "资源不存在"},
    409: {"description": "数据冲突（如重复手机号）"},
}
