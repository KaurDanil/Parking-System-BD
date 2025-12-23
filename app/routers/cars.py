from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, Car, User
from app.schemas import CarCreate, CarResponse

router = APIRouter()


def ensure_car_owner(car: Car, user_id: UUID):
    if car.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this car")


def log_audit(db: Session, user_id: UUID, entity_id: UUID, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="car",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    car_data: CarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Car).filter(Car.plate_number == car_data.plate_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Car with this plate number already exists"
        )

    new_car = Car(
        user_id=current_user.id,
        plate_number=car_data.plate_number,
        model=car_data.model
    )
    db.add(new_car)
    db.commit()
    db.refresh(new_car)

    log_audit(
        db,
        current_user.id,
        new_car.id,
        action="create",
        details={"plate_number": new_car.plate_number, "model": new_car.model},
    )
    db.commit()

    return new_car


@router.get("", response_model=List[CarResponse])
async def get_cars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cars = db.query(Car).filter(Car.user_id == current_user.id).all()
    return cars


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: UUID,
    car_data: CarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    ensure_car_owner(car, current_user.id)

    if car.plate_number != car_data.plate_number:
        conflict = db.query(Car).filter(Car.plate_number == car_data.plate_number).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Car with this plate number already exists")

    car.plate_number = car_data.plate_number
    car.model = car_data.model
    log_audit(
        db,
        current_user.id,
        car.id,
        action="update",
        details={"plate_number": car.plate_number, "model": car.model},
    )
    db.commit()
    db.refresh(car)
    return car


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    ensure_car_owner(car, current_user.id)

    db.delete(car)
    log_audit(
        db,
        current_user.id,
        car.id,
        action="delete",
        details={"plate_number": car.plate_number},
    )
    db.commit()
    return None
