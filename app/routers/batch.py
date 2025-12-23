from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user, get_password_hash
from app.database import get_db
from app.models import AuditLog, Car, User
from app.schemas import BatchImportRequest, BatchImportResult, BatchUserPayload

router = APIRouter()


def log_audit(db: Session, user_id, entity_type: str, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("/batch-import", response_model=BatchImportResult)
async def batch_import(
    payload: BatchImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    created_users = 0
    created_cars = 0
    errors: List[dict] = []

    for user_payload in payload.users:
        try:
            user = User(
                phone=user_payload.phone,
                email=user_payload.email,
                password_hash=get_password_hash(user_payload.password),
            )
            db.add(user)
            db.flush()  # get user.id before commit

            # Create cars
            for car_payload in user_payload.cars:
                car = Car(
                    user_id=user.id,
                    plate_number=car_payload.plate_number,
                    model=car_payload.model,
                )
                db.add(car)
                db.flush()
                created_cars += 1

            log_audit(
                db,
                current_user.id,
                entity_type="batch_import",
                entity_id=user.id,
                action="create",
                details={
                    "phone": user.phone,
                    "email": user.email,
                    "cars": [c.dict() for c in user_payload.cars],
                },
            )

            created_users += 1

            if not payload.dry_run:
                db.commit()
            else:
                db.rollback()
        except IntegrityError as ie:
            db.rollback()
            errors.append(
                {
                    "phone": user_payload.phone,
                    "error": "Integrity error (duplicate phone/email/plate)",
                    "details": str(ie.orig) if hasattr(ie, "orig") else str(ie),
                }
            )
        except Exception as exc:
            db.rollback()
            errors.append(
                {
                    "phone": user_payload.phone,
                    "error": "Unexpected error",
                    "details": str(exc),
                }
            )

    return BatchImportResult(
        created_users=created_users,
        created_cars=created_cars,
        errors=errors,
    )
