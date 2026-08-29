import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finance import AdvanceRequest, CommitteeSettings
from app.models.group import GroupMember, SavingsGroup
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/advances", tags=["Committee Advances"])


class AdvanceCreate(BaseModel):
    group_id: int
    amount: float = Field(..., gt=0)
    reason: str | None = None


class AdvanceDecision(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|REJECTED)$")


class RepaymentCreate(BaseModel):
    principal_amount: float = Field(..., ge=0)
    interest_amount: float = Field(..., ge=0)


def _group(db: Session, group_id: int) -> SavingsGroup:
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id, SavingsGroup.is_active == True).first()
    if not group:
        raise HTTPException(status_code=404, detail="Active savings group not found.")
    return group


def _is_member(db: Session, group_id: int, user_id: int) -> bool:
    return db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id,
        GroupMember.is_active == True,
    ).first() is not None


def _can_manage(group: SavingsGroup, user: User) -> bool:
    return user.role == "ADMIN" or group.created_by_id == user.id


def _settings(db: Session, group_id: int) -> CommitteeSettings:
    settings = db.query(CommitteeSettings).filter(CommitteeSettings.group_id == group_id).first()
    if not settings:
        settings = CommitteeSettings(group_id=group_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _serialize(db: Session, advance: AdvanceRequest, current_user: User):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == advance.group_id).first()
    member = db.query(User).filter(User.id == advance.member_id).first()
    now = datetime.datetime.utcnow()
    outstanding = max(float(advance.amount) - float(advance.principal_repaid or 0), 0.0)
    overdue = bool(advance.due_date and now > advance.due_date and outstanding > 0 and advance.status == "APPROVED")
    rate = float(advance.overdue_interest_rate if overdue else advance.normal_interest_rate)
    expected_interest = round(float(advance.amount) * rate / 100.0, 2) if advance.status in {"APPROVED", "OVERDUE", "REPAID"} else 0.0
    return {
        "id": advance.id,
        "group_id": advance.group_id,
        "group_name": group.name if group else f"Group {advance.group_id}",
        "member_id": advance.member_id,
        "member_name": member.full_name if member else f"Member {advance.member_id}",
        "cycle_number": advance.cycle_number,
        "amount": advance.amount,
        "reason": advance.reason,
        "status": "OVERDUE" if overdue else advance.status,
        "requested_at": advance.requested_at,
        "approved_at": advance.approved_at,
        "due_date": advance.due_date,
        "normal_interest_rate": advance.normal_interest_rate,
        "overdue_interest_rate": advance.overdue_interest_rate,
        "applied_interest_rate": rate if advance.status != "PENDING" else 0.0,
        "expected_interest": expected_interest,
        "principal_repaid": advance.principal_repaid,
        "interest_repaid": advance.interest_repaid,
        "outstanding_principal": outstanding,
        "can_manage": bool(group and _can_manage(group, current_user)),
        "is_owner": current_user.id == advance.member_id,
    }


@router.get("")
def list_advances(group_id: int | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(AdvanceRequest)
    if group_id is not None:
        group = _group(db, group_id)
        if not (_can_manage(group, current_user) or _is_member(db, group_id, current_user.id)):
            raise HTTPException(status_code=403, detail="Join this group to view its advance records.")
        query = query.filter(AdvanceRequest.group_id == group_id)
    elif current_user.role != "ADMIN":
        managed = [g.id for g in db.query(SavingsGroup).filter(SavingsGroup.created_by_id == current_user.id).all()]
        joined = [m.group_id for m in db.query(GroupMember).filter(GroupMember.user_id == current_user.id, GroupMember.is_active == True).all()]
        visible = list(set(managed + joined))
        query = query.filter(AdvanceRequest.group_id.in_(visible or [-1]))
    rows = query.order_by(AdvanceRequest.requested_at.desc()).all()
    return [_serialize(db, row, current_user) for row in rows]


@router.post("")
def request_advance(payload: AdvanceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = _group(db, payload.group_id)
    if not _is_member(db, group.id, current_user.id):
        raise HTTPException(status_code=403, detail="Only active group members can request an advance.")
    settings = _settings(db, group.id)
    request = AdvanceRequest(
        group_id=group.id,
        member_id=current_user.id,
        cycle_number=min(int(group.current_cycle), int(group.total_cycles)),
        amount=payload.amount,
        reason=payload.reason,
        status="PENDING",
        normal_interest_rate=settings.normal_interest_rate,
        overdue_interest_rate=settings.overdue_interest_rate,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _serialize(db, request, current_user)


@router.put("/{advance_id}/decision")
def decide_advance(advance_id: int, payload: AdvanceDecision, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    advance = db.query(AdvanceRequest).filter(AdvanceRequest.id == advance_id).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance request not found.")
    group = _group(db, advance.group_id)
    if not _can_manage(group, current_user):
        raise HTTPException(status_code=403, detail="Only the Group Creator or Platform Admin can approve advances.")
    if advance.status != "PENDING":
        raise HTTPException(status_code=400, detail="This advance request has already been reviewed.")

    advance.status = payload.status
    if payload.status == "APPROVED":
        settings = _settings(db, group.id)
        now = datetime.datetime.utcnow()
        advance.approved_at = now
        advance.approved_by_id = current_user.id
        advance.due_date = now + datetime.timedelta(days=30 * int(settings.repayment_period_months))
        db.add(Transaction(
            reference_id=f"ADV-{uuid.uuid4().hex[:12].upper()}",
            member_id=advance.member_id,
            group_id=group.id,
            amount=advance.amount,
            type="ADVANCE",
            status="COMPLETED",
            description=f"Cycle {advance.cycle_number} | Approved advance request #{advance.id}",
        ))
    db.commit()
    db.refresh(advance)
    return _serialize(db, advance, current_user)


@router.post("/{advance_id}/repay")
def record_repayment(advance_id: int, payload: RepaymentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    advance = db.query(AdvanceRequest).filter(AdvanceRequest.id == advance_id).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance request not found.")
    group = _group(db, advance.group_id)
    if not _can_manage(group, current_user):
        raise HTTPException(status_code=403, detail="Only the Group Creator or Platform Admin can record a verified repayment.")
    if advance.status not in {"APPROVED", "OVERDUE"}:
        raise HTTPException(status_code=400, detail="Only an approved advance can be repaid.")

    outstanding = max(float(advance.amount) - float(advance.principal_repaid or 0), 0.0)
    if payload.principal_amount > outstanding + 0.01:
        raise HTTPException(status_code=400, detail="Principal repayment cannot exceed the outstanding advance.")

    advance.principal_repaid = float(advance.principal_repaid or 0) + payload.principal_amount
    advance.interest_repaid = float(advance.interest_repaid or 0) + payload.interest_amount
    if payload.principal_amount > 0:
        db.add(Transaction(
            reference_id=f"REP-{uuid.uuid4().hex[:12].upper()}", member_id=advance.member_id,
            group_id=advance.group_id, amount=payload.principal_amount, type="REPAYMENT", status="COMPLETED",
            description=f"Cycle {advance.cycle_number} | Repayment for advance #{advance.id}",
        ))
    if payload.interest_amount > 0:
        db.add(Transaction(
            reference_id=f"INT-{uuid.uuid4().hex[:12].upper()}", member_id=advance.member_id,
            group_id=advance.group_id, amount=payload.interest_amount, type="INTEREST", status="COMPLETED",
            description=f"Cycle {advance.cycle_number} | Interest for advance #{advance.id}",
        ))
    if advance.principal_repaid + 0.01 >= advance.amount:
        advance.status = "REPAID"
    db.commit()
    db.refresh(advance)
    return _serialize(db, advance, current_user)
