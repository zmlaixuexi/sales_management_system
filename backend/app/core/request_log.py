"""请求日志中间件 — 记录每个 API 请求的方法、路径、状态码和耗时"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """为每个 API 请求记录结构化日志"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # 只记录 API 路径
        path = request.url.path
        if path.startswith("/api/"):
            record = logging.LogRecord(
                name="app.request", level=logging.INFO,
                pathname="", lineno=0, msg="", args=None, exc_info=None,
            )
            record.extra_fields = {  # type: ignore[attr-defined]
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "-",
            }
            record.msg = f"{request.method} {path} {response.status_code} {duration_ms}ms"
            logger.handle(record)

        return response
