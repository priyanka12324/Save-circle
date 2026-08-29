from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.group import GroupMember, SavingsCycle, SavingsGroup
from app.models.transaction import Contribution, Transaction
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/groups", tags=["Committee Ledger"])


def _can_view(db: Session, group: SavingsGroup, user: User) -> bool:
    if user.role == "ADMIN" or group.created_by_id == user.id:
        return True
    return db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.user_id == user.id,
        GroupMember.is_active == True,
    ).first() is not None


def _sum_transactions(db: Session, group_id: int, cycle_number: int, tx_type: str) -> float:
    """Sum committee cash events recorded in Transaction.

    Committee management can record ADVANCE, REPAYMENT, INTEREST and BANK_INTEREST
    transaction types. A cycle marker is stored as `Cycle N` in the description so
    the ledger remains compatible with the existing MVP Transaction table.
    """
    value = db.query(func.sum(Transaction.amount)).filter(
        Transaction.group_id == group_id,
        Transaction.type == tx_type,
        Transaction.status == "COMPLETED",
        Transaction.description.ilike(f"%Cycle {cycle_number}%"),
    ).scalar()
    return float(value or 0.0)


@router.get("/{group_id}/committee-ledger")
def committee_ledger(group_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")
    if not _can_view(db, group, current_user):
        raise HTTPException(status_code=403, detail="Join this group to view its committee ledger.")

    memberships = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.is_active == True,
    ).all()
    member_ids = [m.user_id for m in memberships]
    users = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    names = {u.id: u.full_name for u in users}
    member_count = len(member_ids)
    expected_per_cycle = float(group.contribution_amount) * member_count

    stored_cycles = {
        c.cycle_number: c
        for c in db.query(SavingsCycle).filter(SavingsCycle.group_id == group_id).all()
    }

    rows = []
    bank_balance = 0.0
    outstanding_advance = 0.0
    committee_interest_till_date = 0.0
    bank_interest_till_date = 0.0

    # The creator chooses total_cycles when the group is created. Nothing here assumes 12 months.
    for cycle_number in range(1, int(group.total_cycles) + 1):
        is_future = cycle_number > int(group.current_cycle)
        contributions = db.query(Contribution).filter(
            Contribution.group_id == group_id,
            Contribution.cycle_id == stored_cycles.get(cycle_number).id if stored_cycles.get(cycle_number) else Contribution.id == -1,
            Contribution.status == "VERIFIED",
        ).all()

        actual_submission = sum(float(c.amount) for c in contributions)
        paid_member_ids = {c.member_id for c in contributions}
        missing_ids = [uid for uid in member_ids if uid not in paid_member_ids] if not is_future else []
        missing_amount = max(expected_per_cycle - actual_submission, 0.0) if not is_future else 0.0
        missing_by = ", ".join(names.get(uid, f"Member {uid}") for uid in missing_ids) if missing_ids else ("—" if is_future else "None")

        advance_taken = _sum_transactions(db, group_id, cycle_number, "ADVANCE")
        repayment_received = _sum_transactions(db, group_id, cycle_number, "REPAYMENT")
        interest_received = _sum_transactions(db, group_id, cycle_number, "INTEREST")
        bank_interest = _sum_transactions(db, group_id, cycle_number, "BANK_INTEREST")

        advance_rows = db.query(Transaction).filter(
            Transaction.group_id == group_id,
            Transaction.type == "ADVANCE",
            Transaction.status == "COMPLETED",
            Transaction.description.ilike(f"%Cycle {cycle_number}%"),
        ).all()
        advance_names = ", ".join(names.get(t.member_id, f"Member {t.member_id}") for t in advance_rows) or "None"

        # Late contributions still belong to their original cycle, so they are never double-counted.
        # The existing Contribution.created_at/verified_at timestamps let the UI show late clearance;
        # a dedicated dues table can later provide a separate arrears-cash column with exact meeting attribution.
        previous_missing_collected = 0.0
        total_cash_received = actual_submission + repayment_received + interest_received + bank_interest

        outstanding_advance = max(outstanding_advance + advance_taken - repayment_received, 0.0)
        committee_interest_till_date += interest_received
        bank_interest_till_date += bank_interest
        bank_balance += total_cash_received - advance_taken

        if is_future:
            status_text = "UPCOMING"
        elif missing_amount > 0:
            status_text = "CONTRIBUTION PENDING"
        elif outstanding_advance > 0:
            status_text = "ADVANCE ACTIVE"
        else:
            status_text = "SETTLED"

        rows.append({
            "cycle": cycle_number,
            "expected_amount": expected_per_cycle,
            "actual_submission": actual_submission,
            "missing_contribution": missing_amount,
            "missing_by": missing_by,
            "previous_missing_collected": previous_missing_collected,
            "total_cash_received": total_cash_received,
            "advance_taken": advance_taken,
            "advance_taken_by": advance_names,
            "repayment_received": repayment_received,
            "interest_received": interest_received,
            "bank_interest_received": bank_interest,
            "status": status_text,
            "outstanding_advance": outstanding_advance,
            "committee_interest_till_date": committee_interest_till_date,
            "bank_balance": bank_balance,
        })

    completed_or_current = [r for r in rows if r["cycle"] <= int(group.current_cycle)]
    missing_due = sum(r["missing_contribution"] for r in completed_or_current)
    verified_contributions = sum(r["actual_submission"] for r in rows)
    expected_total = expected_per_cycle * int(group.total_cycles)

    my_verified = float(db.query(func.sum(Contribution.amount)).filter(
        Contribution.group_id == group_id,
        Contribution.member_id == current_user.id,
        Contribution.status == "VERIFIED",
    ).scalar() or 0.0)
    my_expected_to_date = float(group.contribution_amount) * min(int(group.current_cycle), int(group.total_cycles))
    my_outstanding_due = max(my_expected_to_date - my_verified, 0.0)

    realized_profit = committee_interest_till_date + bank_interest_till_date
    profit_share = realized_profit / member_count if member_count else 0.0
    contribution_entitlement = float(group.contribution_amount) * int(group.total_cycles)
    estimated_member_receipt = contribution_entitlement + profit_share - my_outstanding_due

    cycles_finished = int(group.current_cycle) >= int(group.total_cycles)
    ready = cycles_finished and missing_due <= 0 and outstanding_advance <= 0
    settlement_note = (
        "All configured cycles are complete and no contribution or advance balance is outstanding."
        if ready else
        "Final distribution stays pending until the configured cycle limit is reached and all contributions, advances and due interest are settled."
    )

    return {
        "group": {
            "id": group.id,
            "name": group.name,
            "current_cycle": group.current_cycle,
            "total_cycles": group.total_cycles,
            "contribution_amount": group.contribution_amount,
            "member_count": member_count,
            "is_creator": group.created_by_id == current_user.id,
            "can_manage": current_user.role == "ADMIN" or group.created_by_id == current_user.id,
        },
        "rows": rows,
        "summary": {
            "expected_contributions": expected_total,
            "verified_contributions": verified_contributions,
            "missing_contributions_due": missing_due,
            "bank_balance": bank_balance,
            "outstanding_advances": outstanding_advance,
            "committee_interest_received": committee_interest_till_date,
            "bank_interest_received": bank_interest_till_date,
            "realized_total_profit": realized_profit,
            "total_committee_assets_now": bank_balance + outstanding_advance,
            "estimated_final_value_after_recovery": expected_total + realized_profit,
            "ready_to_distribute": ready,
            "settlement_note": settlement_note,
        },
        "member_summary": {
            "member_name": current_user.full_name,
            "verified_contributions": my_verified,
            "final_contribution_entitlement": contribution_entitlement,
            "realized_profit_share": profit_share,
            "outstanding_due": my_outstanding_due,
            "estimated_final_receipt": estimated_member_receipt,
        },
        "calculation_note": "Dynamic ledger calculated from the group's configured cycle limit and recorded SaveCircle transactions. No month count or sample financial row is hard-coded.",
    }
