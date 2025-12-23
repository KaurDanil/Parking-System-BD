from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import AccessLevel, AuditLog, User
from app.schemas import (
    AccessLevelCreate,
    AccessLevelUpdate,
    AccessLevelResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="access_levels",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=AccessLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_access_level(
    payload: AccessLevelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = db.query(AccessLevel).filter(AccessLevel.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Access level with this code already exists")

    obj = AccessLevel(code=payload.code, description=payload.description)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"code": obj.code})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{access_level_id}", response_model=AccessLevelResponse)
async def get_access_level(access_level_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(AccessLevel).filter(AccessLevel.id == access_level_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Access level not found")
    return obj


@router.get("", response_model=List[AccessLevelResponse])
async def list_access_levels(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(AccessLevel).all()


@router.put("/{access_level_id}", response_model=AccessLevelResponse)
async def update_access_level(
    access_level_id: str,
    payload: AccessLevelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(AccessLevel).filter(AccessLevel.id == access_level_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Access level not found")

    if payload.code and payload.code != obj.code:
        conflict = db.query(AccessLevel).filter(AccessLevel.code == payload.code).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Access level with this code already exists")
        obj.code = payload.code
    if payload.description is not None:
        obj.description = payload.description

    log_audit(db, admin.id, obj.id, "update", {"code": obj.code, "description": obj.description})
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{access_level_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_access_level(
    access_level_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(AccessLevel).filter(AccessLevel.id == access_level_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Access level not found")

    db.delete(obj)
    log_audit(db, admin.id, access_level_id, "delete", {"code": obj.code})
    db.commit()
    return None
