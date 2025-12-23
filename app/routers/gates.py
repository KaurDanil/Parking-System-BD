from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import Gate, AuditLog, User
from app.schemas import GateCreate, GateUpdate, GateResponse

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="gates",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=GateResponse, status_code=status.HTTP_201_CREATED)
async def create_gate(
    payload: GateCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = Gate(name=payload.name, type=payload.type.value)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"name": obj.name, "type": obj.type})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(gate_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Gate).filter(Gate.id == gate_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Gate not found")
    return obj


@router.get("", response_model=List[GateResponse])
async def list_gates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Gate).all()


@router.put("/{gate_id}", response_model=GateResponse)
async def update_gate(
    gate_id: str,
    payload: GateUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(Gate).filter(Gate.id == gate_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Gate not found")

    if payload.name is not None:
        obj.name = payload.name
    if payload.type is not None:
        obj.type = payload.type.value

    log_audit(db, admin.id, obj.id, "update", {"name": obj.name, "type": obj.type})
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{gate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gate(
    gate_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(Gate).filter(Gate.id == gate_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Gate not found")

    db.delete(obj)
    log_audit(db, admin.id, gate_id, "delete", {"name": obj.name})
    db.commit()
    return None
