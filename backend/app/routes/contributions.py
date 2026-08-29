import json
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.transaction import Contribution, Transaction, DigitalReceipt, PaymentProof
from app.models.group import SavingsGroup, SavingsCycle, GroupMember
from app.models.user import User
from app.models.risk_alert import RiskAlert
from app.schemas.transaction import ContributionCreate, ContributionVerify, ContributionOut
from app.services.auth_service import get_current_user
from app.services.audit_service import log_audit
from app.services.receipt_service import generate_digital_receipt
from app.ml.detector import detector

router = APIRouter(prefix="/api/contributions", tags=["Contributions"])

def to_output(db: Session, contribution: Contribution, viewer: User) -> ContributionOut:
    out=ContributionOut.model_validate(contribution)
    member=db.query(User).filter(User.id==contribution.member_id).first();group=db.query(SavingsGroup).filter(SavingsGroup.id==contribution.group_id).first();receipt=db.query(DigitalReceipt).filter(DigitalReceipt.contribution_id==contribution.id).first();proof=db.query(PaymentProof).filter(PaymentProof.contribution_id==contribution.id).first()
    out.member_name=member.full_name if member else f"Member #{contribution.member_id}";out.group_name=group.name if group else f"Group #{contribution.group_id}";out.receipt_id=receipt.id if receipt else None;out.payment_proof_url=proof.data_url if proof else None;out.payment_proof_filename=proof.filename if proof else None
    out.can_verify=bool(group and (viewer.role=="ADMIN" or (group.created_by_id==viewer.id and contribution.member_id!=viewer.id)))
    return out

@router.get("",response_model=List[ContributionOut])
def list_contributions(group_id:Optional[int]=None,status_filter:Optional[str]=None,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=db.query(Contribution)
    if current_user.role!="ADMIN":
        creator_group_ids=[g.id for g in db.query(SavingsGroup).filter(SavingsGroup.created_by_id==current_user.id).all()]
        query=query.filter(or_(Contribution.member_id==current_user.id,Contribution.group_id.in_(creator_group_ids))) if creator_group_ids else query.filter(Contribution.member_id==current_user.id)
    if group_id: query=query.filter(Contribution.group_id==group_id)
    if status_filter: query=query.filter(Contribution.status==status_filter.upper())
    return [to_output(db,c,current_user) for c in query.order_by(Contribution.created_at.desc()).all()]

@router.post("",response_model=ContributionOut,status_code=status.HTTP_201_CREATED)
def record_contribution(contrib_in:ContributionCreate,request:Request,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==contrib_in.group_id,SavingsGroup.is_active==True).first()
    if not group: raise HTTPException(status_code=404,detail="Active savings group not found.")
    enrollment=db.query(GroupMember).filter(GroupMember.group_id==group.id,GroupMember.user_id==current_user.id,GroupMember.is_active==True).first()
    if not enrollment and current_user.role!="ADMIN": raise HTTPException(status_code=403,detail="You must join this group before making a contribution.")
    if contrib_in.proof_data_url:
        if not contrib_in.proof_data_url.startswith("data:image/"): raise HTTPException(status_code=400,detail="Payment proof must be an image.")
        if len(contrib_in.proof_data_url)>2_000_000: raise HTTPException(status_code=400,detail="Payment proof is too large. Please upload an image under about 1.4 MB.")
    active_cycle=db.query(SavingsCycle).filter(SavingsCycle.group_id==group.id,SavingsCycle.status=="ACTIVE").order_by(SavingsCycle.cycle_number.desc()).first();tx_ref=(contrib_in.transaction_ref or "").strip() or f"TXN-DEMO-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    if db.query(Contribution).filter(Contribution.transaction_ref==tx_ref).first(): raise HTTPException(status_code=400,detail="This transaction/UTR reference has already been submitted.")
    contribution=Contribution(member_id=current_user.id,group_id=group.id,cycle_id=active_cycle.id if active_cycle else None,amount=contrib_in.amount,payment_method=contrib_in.payment_method,transaction_ref=tx_ref,status="PENDING",notes=contrib_in.notes);db.add(contribution);db.commit();db.refresh(contribution)
    if contrib_in.proof_data_url: db.add(PaymentProof(contribution_id=contribution.id,filename=contrib_in.proof_filename or "payment-proof.jpg",content_type=contrib_in.proof_content_type or "image/jpeg",data_url=contrib_in.proof_data_url));db.commit()
    tx=Transaction(reference_id=tx_ref,member_id=current_user.id,group_id=group.id,amount=contrib_in.amount,type="CONTRIBUTION",status="PENDING",description=f"Demo contribution of ₹{contrib_in.amount:,.2f} to {group.name} via {contrib_in.payment_method}");db.add(tx);db.commit();db.refresh(tx)
    ai=detector.analyze_transaction(db=db,member_id=current_user.id,group_id=group.id,amount=contrib_in.amount)
    if ai["is_anomalous"] or ai["risk_level"] in ["MEDIUM","HIGH"]:
        tx.status="FLAGGED";db.add(RiskAlert(transaction_id=tx.id,member_id=current_user.id,member_name=current_user.full_name,group_id=group.id,group_name=group.name,amount=contrib_in.amount,risk_level=ai["risk_level"],anomaly_score=ai["anomaly_score"],reasons_json=json.dumps(ai["reasons"]),recommended_action=ai["recommended_action"],status="PENDING_REVIEW"));db.commit();log_audit(db=db,actor=None,action="TRANSACTION_FLAGGED_BY_AI",entity_type="RISK_ALERT",entity_id=tx.id,description=f"AI Engine flagged unusual pattern on transaction {tx_ref} — Risk: {ai['risk_level']}",new_state={"risk_level":ai["risk_level"],"reasons":ai["reasons"]},ip_address=request.client.host if request.client else "127.0.0.1")
    log_audit(db=db,actor=current_user,action="RECORD_CONTRIBUTION",entity_type="CONTRIBUTION",entity_id=contribution.id,description=f"{current_user.full_name} submitted ₹{contrib_in.amount:,.2f} (Ref: {tx_ref})",new_state={"amount":contrib_in.amount,"group":group.name,"method":contrib_in.payment_method,"proof_uploaded":bool(contrib_in.proof_data_url)},ip_address=request.client.host if request.client else "127.0.0.1");return to_output(db,contribution,current_user)

@router.put("/{contrib_id}/verify",response_model=ContributionOut)
def verify_contribution(contrib_id:int,verify_in:ContributionVerify,request:Request,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    contribution=db.query(Contribution).filter(Contribution.id==contrib_id).first()
    if not contribution: raise HTTPException(status_code=404,detail="Contribution record not found.")
    group=db.query(SavingsGroup).filter(SavingsGroup.id==contribution.group_id).first()
    if current_user.role!="ADMIN" and (not group or group.created_by_id!=current_user.id): raise HTTPException(status_code=403,detail="Only this Group Creator or the Platform Admin can verify this contribution.")
    if contribution.member_id==current_user.id and current_user.role!="ADMIN": raise HTTPException(status_code=403,detail="Group Creators cannot verify their own contribution. Platform Admin review is required.")
    if contribution.status=="VERIFIED": raise HTTPException(status_code=400,detail="Contribution has already been verified.")
    target=verify_in.status.upper()
    if target not in ["VERIFIED","REJECTED"]: raise HTTPException(status_code=400,detail="Status must be VERIFIED or REJECTED.")
    prev=contribution.status;contribution.status=target;contribution.verified_by_id=current_user.id;contribution.verified_at=datetime.datetime.utcnow()
    if verify_in.notes: contribution.notes=(contribution.notes or "")+f" [Reviewer: {verify_in.notes}]"
    tx=db.query(Transaction).filter(Transaction.reference_id==contribution.transaction_ref).first()
    if tx: tx.status="COMPLETED" if target=="VERIFIED" else "REJECTED"
    if target=="VERIFIED":
        if not db.query(DigitalReceipt).filter(DigitalReceipt.contribution_id==contribution.id).first(): generate_digital_receipt(db=db,contribution=contribution,verifier=current_user)
        if contribution.cycle_id:
            cycle=db.query(SavingsCycle).filter(SavingsCycle.id==contribution.cycle_id).first()
            if cycle: cycle.collected_amount+=contribution.amount
    db.commit();db.refresh(contribution);log_audit(db=db,actor=current_user,action=f"{target}_CONTRIBUTION",entity_type="CONTRIBUTION",entity_id=contribution.id,description=f"{current_user.full_name} marked {contribution.transaction_ref} as {target}.",previous_state={"status":prev},new_state={"status":target,"notes":verify_in.notes},ip_address=request.client.host if request.client else "127.0.0.1");return to_output(db,contribution,current_user)
