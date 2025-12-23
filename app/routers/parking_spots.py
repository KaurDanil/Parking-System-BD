from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import ParkingSpot, AuditLog, User
from app.schemas import (
    ParkingSpotCreate,
    ParkingSpotUpdate,
    ParkingSpotResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="parking_spots",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=ParkingSpotResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_spot(
    payload: ParkingSpotCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.zone_id == payload.zone_id, ParkingSpot.spot_number == payload.spot_number)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Spot with this number already exists in zone")

    obj = ParkingSpot(
        zone_id=payload.zone_id,
        spot_number=payload.spot_number,
        is_reserved=payload.is_reserved,
        is_active=payload.is_active,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"zone_id": str(obj.zone_id), "spot_number": obj.spot_number})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{spot_id}", response_model=ParkingSpotResponse)
async def get_parking_spot(spot_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking spot not found")
    return obj


@router.get("", response_model=List[ParkingSpotResponse])
async def list_parking_spots(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ParkingSpot).all()


@router.put("/{spot_id}", response_model=ParkingSpotResponse)
async def update_parking_spot(
    spot_id: str,
    payload: ParkingSpotUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking spot not found")

    if payload.zone_id is not None:
        obj.zone_id = payload.zone_id
    if payload.spot_number is not None:
        # Check uniqueness within zone
        existing = (
            db.query(ParkingSpot)
            .filter(ParkingSpot.zone_id == obj.zone_id, ParkingSpot.spot_number == payload.spot_number, ParkingSpot.id != spot_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Spot with this number already exists in zone")
        obj.spot_number = payload.spot_number
    if payload.is_reserved is not None:
        obj.is_reserved = payload.is_reserved
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    log_audit(
        db,
        admin.id,
        obj.id,
        "update",
        {
            "zone_id": str(obj.zone_id),
            "spot_number": obj.spot_number,
            "is_reserved": obj.is_reserved,
            "is_active": obj.is_active,
        },
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_spot(
    spot_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking spot not found")

    db.delete(obj)
    log_audit(db, admin.id, spot_id, "delete", {"spot_number": obj.spot_number})
    db.commit()
    return None
