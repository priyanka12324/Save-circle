import json
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Contribution, Transaction, DigitalReceipt
from app.models.group import SavingsGroup, SavingsCycle, GroupMember
from app.models.user import User
from app.models.risk_alert import RiskAlert
from app.schemas.transaction import ContributionCreate, ContributionVerify, ContributionOut
from app.services.auth_service import get_current_user, require_admin
from app.services.audit_service import log_audit
from app.services.receipt_service import generate_digital_receipt
from app.ml.detector import detector

router = APIRouter(prefix="/api/contributions", tags=["Contributions"])

@router.get("", response_model=List[ContributionOut])
def list_contributions(
    group_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Contribution)
    
    # If standard member, restrict to their own contributions
    if current_user.role != "ADMIN":
        query = query.filter(Contribution.member_id == current_user.id)
    
    if group_id:
        query = query.filter(Contribution.group_id == group_id)
    if status_filter:
        query = query.filter(Contribution.status == status_filter.upper())

    contributions = query.order_by(Contribution.created_at.desc()).all()
    results = []
    for c in contributions:
        c_out = ContributionOut.model_validate(c)
        mem = db.query(User).filter(User.id == c.member_id).first()
        grp = db.query(SavingsGroup).filter(SavingsGroup.id == c.group_id).first()
        rec = db.query(DigitalReceipt).filter(DigitalReceipt.contribution_id == c.id).first()

        c_out.member_name = mem.full_name if mem else f"Member #{c.member_id}"
        c_out.group_name = grp.name if grp else f"Group #{c.group_id}"
        c_out.receipt_id = rec.id if rec else None
        results.append(c_out)
    return results

@router.post("", response_model=ContributionOut, status_code=status.HTTP_201_CREATED)
def record_contribution(
    contrib_in: ContributionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == contrib_in.group_id, SavingsGroup.is_active == True).first()
    if not group:
        raise HTTPException(status_code=404, detail="Active savings group not found.")

    # Check member enrollment
    enrollment = db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.user_id == current_user.id,
        GroupMember.is_active == True
    ).first()
    if not enrollment and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You must be an active member of this group to make a contribution.")

    # Get active cycle
    active_cycle = db.query(SavingsCycle).filter(
        SavingsCycle.group_id == group.id,
        SavingsCycle.status == "ACTIVE"
    ).order_by(SavingsCycle.cycle_number.desc()).first()

    cycle_id = active_cycle.id if active_cycle else None

    # Generate transaction reference
    tx_ref = contrib_in.transaction_ref or f"TXN-DEMO-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # 1. Save Contribution record (Manual/Demo simulated)
    contribution = Contribution(
        member_id=current_user.id,
        group_id=group.id,
        cycle_id=cycle_id,
        amount=contrib_in.amount,
        payment_method=contrib_in.payment_method,
        transaction_ref=tx_ref,
        status="PENDING",
        notes=contrib_in.notes
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)

    # 2. Record Transaction entry
    tx = Transaction(
        reference_id=tx_ref,
        member_id=current_user.id,
        group_id=group.id,
        amount=contrib_in.amount,
        type="CONTRIBUTION",
        status="PENDING",
        description=f"Manual/Demo contribution of ₹{contrib_in.amount:,.2f} to {group.name} via {contrib_in.payment_method}"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # 3. AI / ML Anomaly Detection Scan
    ai_result = detector.analyze_transaction(
        db=db,
        member_id=current_user.id,
        group_id=group.id,
        amount=contrib_in.amount
    )

    if ai_result["is_anomalous"] or ai_result["risk_level"] in ["MEDIUM", "HIGH"]:
        # Flag transaction status
        tx.status = "FLAGGED"
        db.commit()

        # Create Explainable Risk Alert
        risk_alert = RiskAlert(
            transaction_id=tx.id,
            member_id=current_user.id,
            member_name=current_user.full_name,
            group_id=group.id,
            group_name=group.name,
            amount=contrib_in.amount,
            risk_level=ai_result["risk_level"],
            anomaly_score=ai_result["anomaly_score"],
            reasons_json=json.dumps(ai_result["reasons"]),
            recommended_action=ai_result["recommended_action"],
            status="PENDING_REVIEW"
        )
        db.add(risk_alert)
        db.commit()

        # Audit log anomaly flag
        log_audit(
            db=db,
            actor=None,
            action="TRANSACTION_FLAGGED_BY_AI",
            entity_type="RISK_ALERT",
            entity_id=tx.id,
            description=f"AI Engine flagged unusual pattern on transaction {tx_ref} (₹{contrib_in.amount:,.2f}) — Risk: {ai_result['risk_level']}",
            new_state={"risk_level": ai_result["risk_level"], "reasons": ai_result["reasons"]},
            ip_address=request.client.host if request.client else "127.0.0.1"
        )

    # Standard audit log for recording contribution
    log_audit(
        db=db,
        actor=current_user,
        action="RECORD_CONTRIBUTION",
        entity_type="CONTRIBUTION",
        entity_id=contribution.id,
        description=f"User {current_user.full_name} submitted demo contribution of ₹{contrib_in.amount:,.2f} (Ref: {tx_ref})",
        new_state={"amount": contrib_in.amount, "group": group.name, "method": contrib_in.payment_method},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    c_out = ContributionOut.model_validate(contribution)
    c_out.member_name = current_user.full_name
    c_out.group_name = group.name
    return c_out

@router.put("/{contrib_id}/verify", response_model=ContributionOut)
def verify_contribution(
    contrib_id: int,
    verify_in: ContributionVerify,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    contribution = db.query(Contribution).filter(Contribution.id == contrib_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution record not found.")

    if contribution.status == "VERIFIED":
        raise HTTPException(status_code=400, detail="Contribution has already been verified.")

    prev_status = contribution.status
    target_status = verify_in.status.upper()
    if target_status not in ["VERIFIED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be VERIFIED or REJECTED.")

    contribution.status = target_status
    contribution.verified_by_id = admin_user.id
    contribution.verified_at = datetime.datetime.utcnow()
    if verify_in.notes:
        contribution.notes = (contribution.notes or "") + f" [Admin: {verify_in.notes}]"

    # Update matching transaction record
    tx = db.query(Transaction).filter(Transaction.reference_id == contribution.transaction_ref).first()
    if tx:
        tx.status = "COMPLETED" if target_status == "VERIFIED" else "REJECTED"

    # If verified, generate Digital Receipt & update cycle total
    receipt_id = None
    if target_status == "VERIFIED":
        receipt = generate_digital_receipt(db=db, contribution=contribution, verifier=admin_user)
        receipt_id = receipt.id

        if contribution.cycle_id:
            cycle = db.query(SavingsCycle).filter(SavingsCycle.id == contribution.cycle_id).first()
            if cycle:
                cycle.collected_amount += contribution.amount

    db.commit()
    db.refresh(contribution)

    log_audit(
        db=db,
        actor=admin_user,
        action=f"ADMIN_{target_status}_CONTRIBUTION",
        entity_type="CONTRIBUTION",
        entity_id=contribution.id,
        description=f"Admin {admin_user.full_name} marked contribution {contribution.transaction_ref} as {target_status}.",
        previous_state={"status": prev_status},
        new_state={"status": target_status, "notes": verify_in.notes},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    mem = db.query(User).filter(User.id == contribution.member_id).first()
    grp = db.query(SavingsGroup).filter(SavingsGroup.id == contribution.group_id).first()

    c_out = ContributionOut.model_validate(contribution)
    c_out.member_name = mem.full_name if mem else f"Member #{contribution.member_id}"
    c_out.group_name = grp.name if grp else f"Group #{contribution.group_id}"
    c_out.receipt_id = receipt_id
    return c_out
