"""操作日志查询 API"""

import json
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission, resp
from app.core.sanitize import escape_like
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(
    prefix="/audit-logs", tags=["操作日志"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
    },
)


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:view")),
):
    """查询操作日志列表"""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    if keyword:
        escaped = escape_like(keyword)
        query = query.filter(
            AuditLog.actor_name.ilike(f"%{escaped}%", escape="\\")
            | AuditLog.resource_id.ilike(f"%{escaped}%", escape="\\")
        )

    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result_items = []
    for item in items:
        row = {
            "id": str(item.id),
            "actor_id": str(item.actor_id) if item.actor_id else None,
            "actor_name": item.actor_name,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "before_data": json.loads(item.before_data) if item.before_data else None,
            "after_data": json.loads(item.after_data) if item.after_data else None,
            "ip_address": item.ip_address,
            "user_agent": item.user_agent,
            "request_id": item.request_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        result_items.append(row)

    return resp(
        data={
            "items": result_items,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        message="查询成功",
    )


@router.get("/actions")
def list_audit_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:view")),
):
    """获取所有操作类型列表（用于筛选）"""
    actions = db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    resource_types = db.query(AuditLog.resource_type).distinct().order_by(AuditLog.resource_type).all()
    return resp(
        data={
            "actions": [a[0] for a in actions if a[0]],
            "resource_types": [r[0] for r in resource_types if r[0]],
        },
        message="查询成功",
    )
