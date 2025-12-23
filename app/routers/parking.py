from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Car, EntryLog, Gate, ParkingSession, Tariff, User
from app.schemas import EntryLogResponse, ParkingEntry, ParkingExit, ParkingSessionResponse

router = APIRouter()


@router.post("/entry", response_model=dict)
async def process_entry(
    entry_data: ParkingEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify gate exists and is entry gate
    gate = db.query(Gate).filter(Gate.id == entry_data.gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    if gate.type != "entry":
        raise HTTPException(status_code=400, detail="Gate is not an entry gate")
    
    # Call database function to check entry
    result = db.execute(
        text("SELECT * FROM check_entry_allowed(:plate_number, :gate_id)"),
        {"plate_number": entry_data.plate_number, "gate_id": str(entry_data.gate_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to check entry")
    
    allowed = result[0]
    reason = result[1]
    car_id = result[2]
    user_id = result[3]
    wallet_id = result[4]
    balance = result[5]
    
    # Log entry attempt
    entry_log = EntryLog(
        plate_number=entry_data.plate_number,
        gate_id=entry_data.gate_id,
        result="allowed" if allowed else "denied",
        reason=reason
    )
    db.add(entry_log)
    
    if not allowed:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )
    
    # Get default tariff (in production, determine by user access level)
    tariff = db.query(Tariff).first()
    if not tariff:
        raise HTTPException(status_code=500, detail="No tariffs configured")
    
    # Create parking session
    session = ParkingSession(
        car_id=UUID(car_id),
        tariff_id=tariff.id,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {
        "message": "Entry allowed",
        "session_id": str(session.id),
        "car_id": str(car_id),
        "balance": float(balance) if balance else 0
    }


@router.post("/exit", response_model=dict)
async def process_exit(exit_data: ParkingExit, db: Session = Depends(get_db)):
    # Verify gate exists and is exit gate
    gate = db.query(Gate).filter(Gate.id == exit_data.gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    if gate.type != "exit":
        raise HTTPException(status_code=400, detail="Gate is not an exit gate")
    
    # Find car
    car = db.query(Car).filter(Car.plate_number == exit_data.plate_number).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    
    # Call database function to process exit
    result = db.execute(
        text("SELECT * FROM process_exit(:car_id, :exit_time)"),
        {"car_id": str(car.id), "exit_time": datetime.now()}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process exit")
    
    success = result[0]
    session_id = result[1]
    cost = result[2]
    message = result[3]
    
    db.commit()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "message": message,
        "session_id": str(session_id) if session_id else None,
        "cost": float(cost) if cost else 0
    }


@router.get("/sessions/active", response_model=list[ParkingSessionResponse])
async def get_active_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ParkingSession).filter(ParkingSession.status == "active").all()
    return sessions
