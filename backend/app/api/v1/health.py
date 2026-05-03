import subprocess

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import resp
from app.db.session import SessionLocal, engine

router = APIRouter(tags=["健康检查"])


def _get_git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:  # pragma: no cover
        return "unknown"


GIT_REVISION = _get_git_revision()


@router.get("/health")
def health_check():
    """服务健康检查（含数据库连接状态和连接池信息）"""
    from app.main import _shutting_down

    if _shutting_down:
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": {"code": "SHUTTING_DOWN", "message": "服务正在关闭"}},
        )

    checks: dict = {"status": "ok", "version": "0.1.0", "revision": GIT_REVISION}
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
    return resp({"version": "0.1.0", "revision": GIT_REVISION}, "查询成功")
