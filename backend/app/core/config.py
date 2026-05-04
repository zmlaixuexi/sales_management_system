import logging
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    APP_ENV: str = "development"
    BACKEND_PORT: int = 8000
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sales_management"
    DATABASE_ASYNC_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sales_management"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "sales-management-system"
    JWT_AUDIENCE: str = "sales-management-system"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"
    UPLOAD_STORAGE_TYPE: str = "local"
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "uploads")
    UPLOAD_PUBLIC_BASE_URL: str = "/uploads"
    MAX_IMAGE_SIZE_MB: int = 5
    MAX_CSV_IMPORT_SIZE_MB: int = 10
    MAX_CSV_IMPORT_ROWS: int = 1000
    INVENTORY_WARNING_THRESHOLD: int = 10
    RATE_LIMIT_MAX: int = 1000
    RATE_LIMIT_WINDOW: int = 60
    LOGIN_FAIL_MAX: int = 10
    LOGIN_FAIL_WINDOW_SECONDS: int = 900
    ACCOUNT_LOCK_MAX_FAILURES: int = 5
    ACCOUNT_LOCK_WINDOW_SECONDS: int = 900
    SLOW_REQUEST_THRESHOLD_MS: int = 1000
    SLOW_SQL_THRESHOLD_MS: int = 200
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_CONNECT_TIMEOUT_SECONDS: int = 3
    MAX_JSON_BODY_MB: int = 1
    HSTS_MAX_AGE: int = 31536000  # 1 年，仅在 HTTPS 生产环境生效

    @field_validator("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def _positive_int(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("必须为正整数")
        return v

    @field_validator("DB_POOL_SIZE", "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_ROWS", "DB_CONNECT_TIMEOUT_SECONDS")
    @classmethod
    def _strictly_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("必须大于 0")
        return v

    @field_validator("RATE_LIMIT_MAX")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("不能为负数")
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _validate_cors_origins(cls, v: str) -> str:
        origins = [o.strip() for o in v.split(",") if o.strip()]
        for origin in origins:
            if origin == "*":
                raise ValueError("CORS_ORIGINS 不允许使用通配符 '*'（与 allow_credentials=True 不兼容）")
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"CORS origin 必须以 http:// 或 https:// 开头: {origin!r}")
        if not origins:
            raise ValueError("CORS_ORIGINS 不能为空")
        # 生产环境 localhost 告警在 lifespan 中处理（validator 无法访问其他字段）
        return ",".join(origins)

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("JWT_SECRET_KEY 不能为空")
        if len(v) < 8:
            raise ValueError("JWT_SECRET_KEY 长度不能少于 8 个字符")
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
