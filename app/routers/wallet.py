from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, Wallet, WalletTransaction, User
from app.schemas import WalletResponse, WalletTopup

router = APIRouter()


@router.get("", response_model=WalletResponse)
async def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.post("/topup", response_model=dict)
async def topup_wallet(
    topup_data: WalletTopup,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if topup_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet.balance += topup_data.amount

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        amount=topup_data.amount,
        operation_type="topup",
        comment=topup_data.comment or "Wallet top-up"
    )
    db.add(transaction)

    audit = AuditLog(
        user_id=current_user.id,
        entity_type="wallet",
        entity_id=wallet.id,
        action="update",
        details={"amount": float(topup_data.amount), "operation": "topup", "new_balance": float(wallet.balance)},
    )
    db.add(audit)

    db.commit()
    db.refresh(wallet)

    return {
        "message": "Wallet topped up successfully",
        "new_balance": float(wallet.balance),
        "transaction_id": str(transaction.id)
    }
