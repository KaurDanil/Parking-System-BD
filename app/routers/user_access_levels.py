from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import UserAccessLevel, AuditLog, User
from app.schemas import (
    UserAccessLevelCreate,
    UserAccessLevelUpdate,
    UserAccessLevelResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="user_access_levels",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=UserAccessLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_user_access_level(
    payload: UserAccessLevelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = (
        db.query(UserAccessLevel)
        .filter(
            UserAccessLevel.user_id == payload.user_id,
            UserAccessLevel.access_level_id == payload.access_level_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already has this access level")

    obj = UserAccessLevel(user_id=payload.user_id, access_level_id=payload.access_level_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"user_id": str(obj.user_id), "access_level_id": str(obj.access_level_id)})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{ua_id}", response_model=UserAccessLevelResponse)
async def get_user_access_level(ua_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(UserAccessLevel).filter(UserAccessLevel.id == ua_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User access level not found")
    return obj


@router.get("", response_model=List[UserAccessLevelResponse])
async def list_user_access_levels(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(UserAccessLevel).all()


@router.put("/{ua_id}", response_model=UserAccessLevelResponse)
async def update_user_access_level(
    ua_id: str,
    payload: UserAccessLevelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(UserAccessLevel).filter(UserAccessLevel.id == ua_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User access level not found")

    if payload.user_id is not None:
        obj.user_id = payload.user_id
    if payload.access_level_id is not None:
        obj.access_level_id = payload.access_level_id

    log_audit(
        db,
        admin.id,
        obj.id,
        "update",
        {"user_id": str(obj.user_id), "access_level_id": str(obj.access_level_id)},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{ua_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_access_level(
    ua_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(UserAccessLevel).filter(UserAccessLevel.id == ua_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User access level not found")

    db.delete(obj)
    log_audit(db, admin.id, ua_id, "delete", {})
    db.commit()
    return None
