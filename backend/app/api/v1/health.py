from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import resp
from app.db.session import SessionLocal, engine

router = APIRouter(tags=["健康检查"])


@router.get("/health")
def health_check():
    """服务健康检查（含数据库连接状态和连接池信息）"""
    checks: dict = {"status": "ok", "version": "0.1.0"}
    db_ok = False
    try:
        db: Session = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        finally:
            db.close()
    except Exception:
        pass

    checks["database"] = "ok" if db_ok else "error"
    if not db_ok:
        checks["status"] = "degraded"

    # 连接池状态（便于生产环境诊断）
    pool = engine.pool
    checks["pool"] = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

    return resp(checks, "服务正常" if db_ok else "数据库连接异常")


@router.get("/version")
def version():
    return resp({"version": "0.1.0"}, "查询成功")
