from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import ParkingSession, Car, AuditLog, User
from app.schemas import (
    ParkingSessionCreate,
    ParkingSessionUpdate,
    ParkingSessionResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="parking_sessions",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


def is_admin(current_user: User) -> bool:
    # Reuse require_admin indirectly if needed, but here just check role via deps.ADMIN_PHONE
    from app.deps import ADMIN_PHONE

    return current_user.phone == ADMIN_PHONE


@router.post("", response_model=ParkingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_session(
    payload: ParkingSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # For simplicity, allow only admin to create arbitrary sessions; normal users go via /api/parking/entry
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use /api/parking/entry to create sessions")

    obj = ParkingSession(
        car_id=payload.car_id,
        spot_id=payload.spot_id,
        tariff_id=payload.tariff_id,
        entry_time=payload.entry_time,
        exit_time=payload.exit_time,
        total_cost=payload.total_cost,
        status=payload.status,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, current_user.id, obj.id, "create", {"car_id": str(obj.car_id)})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{session_id}", response_model=ParkingSessionResponse)
async def get_parking_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ParkingSession)
    if not is_admin(current_user):
        q = q.join(Car).filter(Car.user_id == current_user.id)
    obj = q.filter(ParkingSession.id == session_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking session not found")
    return obj


@router.get("", response_model=List[ParkingSessionResponse])
async def list_parking_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ParkingSession)
    if not is_admin(current_user):
        q = q.join(Car).filter(Car.user_id == current_user.id)
    return q.all()


@router.put("/{session_id}", response_model=ParkingSessionResponse)
async def update_parking_session(
    session_id: str,
    payload: ParkingSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can update sessions")

    obj = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking session not found")

    if payload.car_id is not None:
        obj.car_id = payload.car_id
    if payload.spot_id is not None:
        obj.spot_id = payload.spot_id
    if payload.tariff_id is not None:
        obj.tariff_id = payload.tariff_id
    if payload.entry_time is not None:
        obj.entry_time = payload.entry_time
    if payload.exit_time is not None:
        obj.exit_time = payload.exit_time
    if payload.total_cost is not None:
        obj.total_cost = payload.total_cost
    if payload.status is not None:
        obj.status = payload.status

    log_audit(
        db,
        current_user.id,
        obj.id,
        "update",
        {
            "car_id": str(obj.car_id),
            "spot_id": str(obj.spot_id) if obj.spot_id else None,
            "tariff_id": str(obj.tariff_id),
            "status": obj.status,
        },
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can delete sessions")

    obj = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Parking session not found")

    db.delete(obj)
    log_audit(db, current_user.id, session_id, "delete", {"car_id": str(obj.car_id)})
    db.commit()
    return None
