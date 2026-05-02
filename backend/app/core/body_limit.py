"""请求体大小限制中间件 — 防止超大体请求耗尽内存"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """限制 JSON API 请求体大小，multipart 和静态资源路径豁免"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 只检查有 body 的写操作
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # 文件上传、静态资源路径豁免（已有独立的大小校验）
        content_type = request.headers.get("content-type", "")
        path = request.url.path
        if "multipart/form-data" in content_type:
            return await call_next(request)
        if path.startswith("/uploads"):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length is not None:
            max_bytes = settings.MAX_JSON_BODY_MB * 1024 * 1024
            if int(content_length) > max_bytes:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": f"请求体超过 {settings.MAX_JSON_BODY_MB}MB 限制",
                        },
                    },
                )

        return await call_next(request)
