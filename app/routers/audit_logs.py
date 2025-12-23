from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import require_admin
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogCreate, AuditLogUpdate, AuditLogResponse

router = APIRouter()


@router.post("", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    payload: AuditLogCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = AuditLog(
        user_id=payload.user_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        action=payload.action,
        details=payload.details,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return obj


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(AuditLog).all()


@router.put("/{log_id}", response_model=AuditLogResponse)
async def update_audit_log(
    log_id: str,
    payload: AuditLogUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Audit log not found")

    if payload.user_id is not None:
        obj.user_id = payload.user_id
    if payload.entity_type is not None:
        obj.entity_type = payload.entity_type
    if payload.entity_id is not None:
        obj.entity_id = payload.entity_id
    if payload.action is not None:
        obj.action = payload.action
    if payload.details is not None:
        obj.details = payload.details

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{log_id}")
async def delete_audit_log():
    # Deleting audit logs is disallowed even for admin
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Deleting audit logs is not allowed")
