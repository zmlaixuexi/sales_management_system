"""操作日志服务"""

import json
import logging
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

# 敏感字段列表，记录日志时自动脱敏
SENSITIVE_FIELDS = {"password", "hashed_password", "token", "secret", "credit_card"}


def get_request_meta(request: Request) -> dict:
    """从 FastAPI Request 对象提取 IP、user_agent、request_id"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())[:8]
    return {"ip_address": ip, "user_agent": ua, "request_id": rid}


def _mask_sensitive(data: dict | None) -> dict | None:
    """脱敏敏感字段"""
    if not data:
        return data
    masked = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_FIELDS):
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


def log_action(
    db: Session,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    actor_name: str | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """记录操作日志"""
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_data=json.dumps(_mask_sensitive(before_data), ensure_ascii=False, default=str) if before_data else None,
            after_data=json.dumps(_mask_sensitive(after_data), ensure_ascii=False, default=str) if after_data else None,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            request_id=request_id,
        )
        db.add(entry)
        db.flush()
        return entry
    except Exception:
        logger.exception("写入操作日志失败: action=%s resource_type=%s", action, resource_type)
        return None


def model_to_dict(obj: Any) -> dict:
    """将 SQLAlchemy 模型转为字典，用于日志记录"""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.key, None)
        if val is not None:
            result[col.key] = str(val) if isinstance(val, uuid.UUID) else val
    return result
