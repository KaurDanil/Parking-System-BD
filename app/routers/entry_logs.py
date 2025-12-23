from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import EntryLog, Car, User, AuditLog
from app.schemas import (
    EntryLogCreate,
    EntryLogUpdate,
    EntryLogResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="entry_logs",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=EntryLogResponse, status_code=status.HTTP_201_CREATED)
async def create_entry_log(
    payload: EntryLogCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = EntryLog(
        plate_number=payload.plate_number,
        gate_id=payload.gate_id,
        attempt_time=payload.attempt_time,
        result=payload.result.value,
        reason=payload.reason,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"plate_number": obj.plate_number, "result": obj.result})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{log_id}", response_model=EntryLogResponse)
async def get_entry_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(EntryLog)
    # Normal users see only logs for their cars
    from app.deps import ADMIN_PHONE

    if current_user.phone != ADMIN_PHONE:
        q = q.join(Car, Car.plate_number == EntryLog.plate_number).filter(Car.user_id == current_user.id)
    obj = q.filter(EntryLog.id == log_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry log not found")
    return obj


@router.get("", response_model=List[EntryLogResponse])
async def list_entry_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(EntryLog)
    from app.deps import ADMIN_PHONE

    if current_user.phone != ADMIN_PHONE:
        q = q.join(Car, Car.plate_number == EntryLog.plate_number).filter(Car.user_id == current_user.id)
    return q.all()


@router.put("/{log_id}", response_model=EntryLogResponse)
async def update_entry_log(
    log_id: str,
    payload: EntryLogUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(EntryLog).filter(EntryLog.id == log_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry log not found")

    if payload.plate_number is not None:
        obj.plate_number = payload.plate_number
    if payload.gate_id is not None:
        obj.gate_id = payload.gate_id
    if payload.attempt_time is not None:
        obj.attempt_time = payload.attempt_time
    if payload.result is not None:
        obj.result = payload.result.value
    if payload.reason is not None:
        obj.reason = payload.reason

    log_audit(
        db,
        admin.id,
        obj.id,
        "update",
        {"plate_number": obj.plate_number, "result": obj.result},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry_log(
    log_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(EntryLog).filter(EntryLog.id == log_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry log not found")

    db.delete(obj)
    log_audit(db, admin.id, log_id, "delete", {"plate_number": obj.plate_number})
    db.commit()
    return None
