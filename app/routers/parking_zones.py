from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import ParkingZone, AuditLog, User
from app.schemas import (
    ParkingZoneCreate,
    ParkingZoneUpdate,
    ParkingZoneResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="parking_zones",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=ParkingZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_zone(
    payload: ParkingZoneCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = ParkingZone(name=payload.name, description=payload.description)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"name": obj.name})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{zone_id}", response_model=ParkingZoneResponse)
async def get_parking_zone(zone_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(ParkingZone).filter(ParkingZone.id == zone_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking zone not found")
    return obj


@router.get("", response_model=List[ParkingZoneResponse])
async def list_parking_zones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ParkingZone).all()


@router.put("/{zone_id}", response_model=ParkingZoneResponse)
async def update_parking_zone(
    zone_id: str,
    payload: ParkingZoneUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(ParkingZone).filter(ParkingZone.id == zone_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking zone not found")

    if payload.name is not None:
        obj.name = payload.name
    if payload.description is not None:
        obj.description = payload.description

    log_audit(db, admin.id, obj.id, "update", {"name": obj.name, "description": obj.description})
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(ParkingZone).filter(ParkingZone.id == zone_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking zone not found")

    db.delete(obj)
    log_audit(db, admin.id, zone_id, "delete", {"name": obj.name})
    db.commit()
    return None
