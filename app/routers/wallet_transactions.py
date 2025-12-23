from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import require_admin
from app.database import get_db
from app.models import WalletTransaction, Wallet, User, AuditLog
from app.schemas import (
    WalletTransactionCreate,
    WalletTransactionUpdate,
    WalletTransactionResponse,
)

router = APIRouter()


def log_audit(db: Session, user_id, entity_id, action: str, details: dict):
    audit = AuditLog(
        user_id=user_id,
        entity_type="wallet_transactions",
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit)


@router.post("", response_model=WalletTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet_transaction(
    payload: WalletTransactionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = WalletTransaction(
        wallet_id=payload.wallet_id,
        session_id=payload.session_id,
        amount=payload.amount,
        operation_type=payload.operation_type.value,
        comment=payload.comment,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    log_audit(db, admin.id, obj.id, "create", {"wallet_id": str(obj.wallet_id), "amount": float(obj.amount)})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{tx_id}", response_model=WalletTransactionResponse)
async def get_wallet_transaction(
    tx_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(WalletTransaction).join(Wallet)
    # Normal users see only their wallet transactions
    if not isinstance(current_user, User) or current_user.phone != "000":
        q = q.filter(Wallet.user_id == current_user.id)
    obj = q.filter(WalletTransaction.id == tx_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Wallet transaction not found")
    return obj


@router.get("", response_model=List[WalletTransactionResponse])
async def list_wallet_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(WalletTransaction).join(Wallet)
    if not isinstance(current_user, User) or current_user.phone != "000":
        q = q.filter(Wallet.user_id == current_user.id)
    return q.all()


@router.put("/{tx_id}", response_model=WalletTransactionResponse)
async def update_wallet_transaction(
    tx_id: str,
    payload: WalletTransactionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(WalletTransaction).filter(WalletTransaction.id == tx_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Wallet transaction not found")

    if payload.wallet_id is not None:
        obj.wallet_id = payload.wallet_id
    if payload.session_id is not None:
        obj.session_id = payload.session_id
    if payload.amount is not None:
        obj.amount = payload.amount
    if payload.operation_type is not None:
        obj.operation_type = payload.operation_type.value
    if payload.comment is not None:
        obj.comment = payload.comment

    log_audit(
        db,
        admin.id,
        obj.id,
        "update",
        {"wallet_id": str(obj.wallet_id), "amount": float(obj.amount)},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet_transaction(
    tx_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    obj = db.query(WalletTransaction).filter(WalletTransaction.id == tx_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Wallet transaction not found")

    db.delete(obj)
    log_audit(db, admin.id, tx_id, "delete", {"wallet_id": str(obj.wallet_id)})
    db.commit()
    return None
