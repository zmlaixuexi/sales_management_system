"""用户 ID 上下文 — 供请求日志和审计使用"""

from contextvars import ContextVar

user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
