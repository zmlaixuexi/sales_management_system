from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.core.logging  # noqa: F401 — 确保日志初始化
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.ratelimit import add_rate_limit
from app.core.request_log import RequestLogMiddleware
from app.core.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保上传目录存在
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    yield


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
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLogMiddleware)

app.include_router(api_router, prefix="/api/v1")

# 速率限制（注册在路由之后，中间件执行顺序为后注册先执行）
add_rate_limit(app)

# 静态文件服务：上传的图片
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")
