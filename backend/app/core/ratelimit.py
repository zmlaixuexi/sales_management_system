"""基于内存的滑动窗口速率限制中间件"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings


class _SlidingWindow:
    """单 IP 的滑动窗口计数器"""

    __slots__ = ("timestamps",)

    def __init__(self) -> None:
        self.timestamps: list[float] = []

    def count(self, window: float, now: float) -> int:
        ts = self.timestamps
        # 清理过期条目
        cutoff = now - window
        while ts and ts[0] < cutoff:
            ts.pop(0)
        return len(ts)

    def record(self, now: float) -> None:
        self.timestamps.append(now)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 限制 API 请求频率"""

    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window = float(window_seconds)
        self._buckets: dict[str, _SlidingWindow] = defaultdict(_SlidingWindow)
        self._lock = Lock()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 只限制 API 路径
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with self._lock:
            bucket = self._buckets[client_ip]
            count = bucket.count(self.window, now)
            if count >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "请求过于频繁，请稍后再试"},
                    },
                )
            bucket.record(now)

        response = await call_next(request)
        remaining = max(0, self.max_requests - count - 1)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def add_rate_limit(app: FastAPI) -> None:
    """根据配置注册速率限制中间件"""
    max_requests = getattr(settings, "RATE_LIMIT_MAX", 100)
    window_seconds = getattr(settings, "RATE_LIMIT_WINDOW", 60)
    if max_requests > 0:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
