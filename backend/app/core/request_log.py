"""请求日志中间件 — 记录每个 API 请求的方法、路径、状态码和耗时"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.request_id import request_id_ctx

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
            is_slow = duration_ms >= settings.SLOW_REQUEST_THRESHOLD_MS
            level = logging.WARNING if is_slow else logging.INFO
            record = logging.LogRecord(
                name="app.request", level=level,
                pathname="", lineno=0, msg="", args=None, exc_info=None,
            )
            record.extra_fields = {  # type: ignore[attr-defined]
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "-",
                "slow": is_slow,
                "request_id": request_id_ctx.get(""),
            }
            label = "SLOW " if is_slow else ""
            record.msg = f"{label}{request.method} {path} {response.status_code} {duration_ms}ms"
            logger.handle(record)

        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response
