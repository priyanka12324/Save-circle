import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.models.group import SavingsGroup
from app.models.user import User
from app.models.risk_alert import RiskAlert
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.auth_service import get_current_user, require_admin
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionOut])
def list_transactions(
    group_id: Optional[int] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    
    # Non-admins can only see their own transactions
    if current_user.role != "ADMIN":
        query = query.filter(Transaction.member_id == current_user.id)
    
    if group_id:
        query = query.filter(Transaction.group_id == group_id)
    if type_filter:
        query = query.filter(Transaction.type == type_filter.upper())
    if status_filter:
        query = query.filter(Transaction.status == status_filter.upper())

    transactions = query.order_by(Transaction.created_at.desc()).all()
    results = []
    for t in transactions:
        t_out = TransactionOut.model_validate(t)
        mem = db.query(User).filter(User.id == t.member_id).first()
        grp = db.query(SavingsGroup).filter(SavingsGroup.id == t.group_id).first()
        alert = db.query(RiskAlert).filter(RiskAlert.transaction_id == t.id).first()

        t_out.member_name = mem.full_name if mem else f"Member #{t.member_id}"
        t_out.group_name = grp.name if grp else f"Group #{t.group_id}"
        t_out.risk_level = alert.risk_level if alert else "LOW"
        results.append(t_out)
    return results

@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    t = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    if current_user.role != "ADMIN" and current_user.id != t.member_id:
        raise HTTPException(status_code=403, detail="Forbidden access to this transaction.")

    t_out = TransactionOut.model_validate(t)
    mem = db.query(User).filter(User.id == t.member_id).first()
    grp = db.query(SavingsGroup).filter(SavingsGroup.id == t.group_id).first()
    alert = db.query(RiskAlert).filter(RiskAlert.transaction_id == t.id).first()

    t_out.member_name = mem.full_name if mem else f"Member #{t.member_id}"
    t_out.group_name = grp.name if grp else f"Group #{t.group_id}"
    t_out.risk_level = alert.risk_level if alert else "LOW"
    return t_out

@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_manual_transaction(
    tx_in: TransactionCreate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == tx_in.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")

    member = db.query(User).filter(User.id == tx_in.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Target member not found.")

    ref_id = f"TXN-SYS-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    tx = Transaction(
        reference_id=ref_id,
        member_id=member.id,
        group_id=group.id,
        amount=tx_in.amount,
        type=tx_in.type.upper(),
        status="COMPLETED",
        description=tx_in.description or f"Manual {tx_in.type} adjustment by Admin"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    log_audit(
        db=db,
        actor=admin_user,
        action=f"ADMIN_RECORD_{tx.type}",
        entity_type="TRANSACTION",
        entity_id=tx.id,
        description=f"Admin {admin_user.full_name} recorded {tx.type} of ₹{tx.amount:,.2f} for member {member.full_name} in {group.name}",
        new_state={"amount": tx.amount, "type": tx.type, "ref": ref_id},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    t_out = TransactionOut.model_validate(tx)
    t_out.member_name = member.full_name
    t_out.group_name = group.name
    t_out.risk_level = "LOW"
    return t_out
