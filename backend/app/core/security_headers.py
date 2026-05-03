"""安全响应头中间件"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有 API 响应添加安全响应头"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # API 不提供 HTML 内容，使用严格 CSP
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # 跨域隔离策略
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        # 仅在 HTTPS 请求时添加 HSTS（生产环境）
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"
        # 禁止缓存 API 响应，防止敏感数据被中间代理或浏览器缓存
        response.headers["Cache-Control"] = "no-store"
        return response
