import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import app.core.logging
from app.api.v1.router import api_router
from app.core.body_limit import BodyLimitMiddleware
from app.core.config import settings
from app.core.ratelimit import add_rate_limit
from app.core.request_id import RequestIDMiddleware
from app.core.request_log import RequestLogMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保上传目录存在
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生产环境安全检查
    if settings.APP_ENV == "production" and settings.JWT_SECRET_KEY == "change-me":
        logging.critical("JWT_SECRET_KEY 未设置，请在环境变量中配置安全密钥")
        raise RuntimeError("JWT_SECRET_KEY 不能使用默认值")

    # 启动配置摘要
    logger.info(
        "服务启动 — env=%s pool=%d/%d rate_limit=%d/%ds log=%s/%s",
        settings.APP_ENV,
        settings.DB_POOL_SIZE,
        settings.DB_MAX_OVERFLOW,
        settings.RATE_LIMIT_MAX,
        settings.RATE_LIMIT_WINDOW,
        settings.LOG_LEVEL,
        settings.LOG_FORMAT,
    )

    yield

    # 优雅关闭：释放数据库连接池
    logger.info("服务关闭 — 释放数据库连接池")
    engine.dispose()


OPENAPI_TAGS = [
    {"name": "认证", "description": "用户登录、令牌刷新、获取当前用户信息"},
    {"name": "用户管理", "description": "用户 CRUD、角色分配"},
    {"name": "商品管理", "description": "商品 CRUD、批量导入、价格历史"},
    {"name": "客户管理", "description": "客户 CRUD、批量导入、归属转移"},
    {"name": "订单管理", "description": "订单 CRUD、确认/取消、库存联动"},
    {"name": "收款管理", "description": "收款记录 CRUD"},
    {"name": "库存管理", "description": "库存查询、库存流水"},
    {"name": "报表", "description": "销售汇总、趋势、商品排名"},
    {"name": "操作日志", "description": "操作审计日志查询"},
    {"name": "数据导出", "description": "CSV/Excel 数据导出"},
    {"name": "文件管理", "description": "文件上传"},
]

app = FastAPI(
    title="销售管理系统",
    description="销售管理系统 API — 包含商品、客户、订单、收款、库存、报表等模块",
    version="0.1.0",
    docs_url=None if settings.APP_ENV == "production" else "/api/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/api/redoc",
    openapi_url=None if settings.APP_ENV == "production" else "/api/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """将 HTTPException 统一为 {success: false, error: {code, message}, request_id} 格式"""
    from app.core.request_id import request_id_ctx

    detail = exc.detail
    if isinstance(detail, dict):
        error = {"code": detail.get("code", "SYSTEM_INTERNAL_ERROR"), "message": detail.get("message", str(detail))}
        if "details" in detail:
            error["details"] = detail["details"]
    else:
        error = {"code": "SYSTEM_INTERNAL_ERROR", "message": str(detail)}
    result: dict = {"success": False, "error": error}
    rid = request_id_ctx.get("")
    if rid:
        result["request_id"] = rid
    return JSONResponse(status_code=exc.status_code, content=result)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    """将 FastAPI 默认 422 校验错误统一为规范格式"""
    from app.core.request_id import request_id_ctx

    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = " → ".join(str(part) for part in first.get("loc", []))
    msg = first.get("msg", "请求参数错误")
    detail_msg = f"{loc}: {msg}" if loc else msg
    result: dict = {"success": False, "error": {"code": "VALIDATION_FAILED", "message": detail_msg}}
    rid = request_id_ctx.get("")
    if rid:
        result["request_id"] = rid
    return JSONResponse(status_code=422, content=result)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """全局未处理异常：返回一致 JSON 格式，防泄露内部详情"""
    from app.core.request_id import request_id_ctx

    rid = request_id_ctx.get("")
    logger.exception("未处理异常 [%s] %s rid=%s", request.method, request.url.path, rid)
    result: dict = {
        "success": False,
        "error": {"code": "SYSTEM_INTERNAL_ERROR", "message": "服务器内部错误，请稍后重试"},
    }
    if rid:
        result["request_id"] = rid
    return JSONResponse(status_code=500, content=result)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.add_middleware(BodyLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(api_router, prefix="/api/v1")

# 速率限制（注册在路由之后，中间件执行顺序为后注册先执行）
add_rate_limit(app)

# 静态文件服务：上传的图片
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")
