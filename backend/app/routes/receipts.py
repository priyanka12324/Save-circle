from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import DigitalReceipt
from app.models.user import User
from app.schemas.transaction import DigitalReceiptOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])

@router.get("", response_model=List[DigitalReceiptOut])
def list_receipts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(DigitalReceipt)
    if current_user.role != "ADMIN":
        query = query.filter(DigitalReceipt.member_id == current_user.id)
    
    receipts = query.order_by(DigitalReceipt.created_at.desc()).all()
    return [DigitalReceiptOut.model_validate(r) for r in receipts]

@router.get("/{receipt_id}", response_model=DigitalReceiptOut)
def get_receipt(
    receipt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(DigitalReceipt).filter(DigitalReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Digital receipt not found.")

    if current_user.role != "ADMIN" and current_user.id != receipt.member_id:
        raise HTTPException(status_code=403, detail="Forbidden access to this receipt.")

    return DigitalReceiptOut.model_validate(receipt)

@router.get("/by-number/{receipt_number}", response_model=DigitalReceiptOut)
def get_receipt_by_number(
    receipt_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(DigitalReceipt).filter(DigitalReceipt.receipt_number == receipt_number).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Digital receipt not found.")

    if current_user.role != "ADMIN" and current_user.id != receipt.member_id:
        raise HTTPException(status_code=403, detail="Forbidden access to this receipt.")

    return DigitalReceiptOut.model_validate(receipt)
