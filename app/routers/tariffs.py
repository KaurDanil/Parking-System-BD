from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import Tariff, AuditLog, User
from app.schemas import TariffCreate, TariffUpdate, TariffResponse

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="tariffs",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
async def create_tariff(
    payload: TariffCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = db.query(Tariff).filter(Tariff.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tariff with this name already exists")

    obj = Tariff(
        name=payload.name,
        price_per_hour=payload.price_per_hour,
        free_minutes=payload.free_minutes,
        zone_id=payload.zone_id,
        access_level_id=payload.access_level_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"name": obj.name})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tariff not found")
    return obj


@router.get("", response_model=List[TariffResponse])
async def list_tariffs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Tariff).all()


@router.put("/{tariff_id}", response_model=TariffResponse)
async def update_tariff(
    tariff_id: str,
    payload: TariffUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tariff not found")

    if payload.name is not None and payload.name != obj.name:
        existing = db.query(Tariff).filter(Tariff.name == payload.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tariff with this name already exists")
        obj.name = payload.name
    if payload.price_per_hour is not None:
        obj.price_per_hour = payload.price_per_hour
    if payload.free_minutes is not None:
        obj.free_minutes = payload.free_minutes
    if payload.zone_id is not None:
        obj.zone_id = payload.zone_id
    if payload.access_level_id is not None:
        obj.access_level_id = payload.access_level_id

    log_audit(
        db,
        admin.id,
        obj.id,
        "update",
        {
            "name": obj.name,
            "price_per_hour": float(obj.price_per_hour),
            "free_minutes": obj.free_minutes,
        },
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tariff(
    tariff_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tariff not found")

    db.delete(obj)
    log_audit(db, admin.id, tariff_id, "delete", {"name": obj.name})
    db.commit()
    return None
