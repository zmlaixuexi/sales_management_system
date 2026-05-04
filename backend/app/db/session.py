from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings
from app.core.slow_query import register_slow_query_listener


def _connect_args() -> dict[str, int]:
    if settings.DATABASE_URL.startswith("postgresql"):
        return {"connect_timeout": settings.DB_CONNECT_TIMEOUT_SECONDS}
    return {}


engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    connect_args=_connect_args(),
)
register_slow_query_listener(engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass

