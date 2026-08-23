import hashlib
import uuid
import datetime
from sqlalchemy.orm import Session
from app.models.transaction import Contribution, DigitalReceipt
from app.models.user import User
from app.models.group import SavingsGroup

def generate_digital_receipt(
    db: Session,
    contribution: Contribution,
    verifier: User
) -> DigitalReceipt:
    """
    Generates an authentic tamper-resistant digital receipt for a verified contribution.
    """
    member = db.query(User).filter(User.id == contribution.member_id).first()
    group = db.query(SavingsGroup).filter(SavingsGroup.id == contribution.group_id).first()

    member_name = member.full_name if member else f"Member #{contribution.member_id}"
    group_name = group.name if group else f"Group #{contribution.group_id}"
    
    unique_suffix = uuid.uuid4().hex[:8].upper()
    receipt_number = f"SC-REC-{datetime.datetime.utcnow().year}-{unique_suffix}"
    now = datetime.datetime.utcnow()

    # Generate cryptographic hash representing transaction signature
    payload = f"{receipt_number}:{contribution.transaction_ref}:{member_name}:{contribution.amount}:{now.isoformat()}:{verifier.id}"
    security_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    receipt = DigitalReceipt(
        receipt_number=receipt_number,
        transaction_ref=contribution.transaction_ref,
        contribution_id=contribution.id,
        member_id=contribution.member_id,
        member_name=member_name,
        group_id=contribution.group_id,
        group_name=group_name,
        amount=contribution.amount,
        payment_method=contribution.payment_method,
        payment_status="VERIFIED",
        verified_by_name=verifier.full_name,
        verification_date=now,
        security_hash=security_hash,
        created_at=now
    )

    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt
