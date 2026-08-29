from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupMember, SavingsGroup
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/groups", tags=["Committee Ledger"])


DEMO_ROWS = [
    {"month":"Jan","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":0,"total_cash_received":20000,"advance_taken":10000,"advance_taken_by":"Rahul","repayment_received":0,"interest_received":0,"status":"Rahul advance active","outstanding_advance":10000,"committee_interest_till_date":0,"bank_balance":10000},
    {"month":"Feb","expected_amount":20000,"actual_submission":18000,"missing_contribution":2000,"missing_by":"Aman","previous_missing_collected":0,"total_cash_received":18000,"advance_taken":12500,"advance_taken_by":"Priya","repayment_received":0,"interest_received":0,"status":"Aman contribution pending","outstanding_advance":22500,"committee_interest_till_date":0,"bank_balance":15500},
    {"month":"Mar","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":2000,"total_cash_received":22000,"advance_taken":8000,"advance_taken_by":"Aman","repayment_received":0,"interest_received":0,"status":"Aman cleared Feb contribution","outstanding_advance":30500,"committee_interest_till_date":0,"bank_balance":29500},
    {"month":"Apr","expected_amount":20000,"actual_submission":18000,"missing_contribution":2000,"missing_by":"Neha","previous_missing_collected":0,"total_cash_received":18000,"advance_taken":15000,"advance_taken_by":"Neha","repayment_received":0,"interest_received":0,"status":"Neha advance active","outstanding_advance":45500,"committee_interest_till_date":0,"bank_balance":32500},
    {"month":"May","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":2000,"total_cash_received":22000,"advance_taken":11000,"advance_taken_by":"Karan","repayment_received":12625,"interest_received":125,"status":"Priya repaid ₹12,500 + 1%","outstanding_advance":44000,"committee_interest_till_date":125,"bank_balance":56125},
    {"month":"Jun","expected_amount":20000,"actual_submission":16000,"missing_contribution":4000,"missing_by":"Rahul, Simran","previous_missing_collected":0,"total_cash_received":16000,"advance_taken":9000,"advance_taken_by":"Meera","repayment_received":8080,"interest_received":80,"status":"Aman repaid ₹8,000 + 1%","outstanding_advance":45000,"committee_interest_till_date":205,"bank_balance":71205},
    {"month":"Jul","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":4000,"total_cash_received":24000,"advance_taken":14000,"advance_taken_by":"Rohit","repayment_received":0,"interest_received":0,"status":"Rahul + Simran cleared June dues","outstanding_advance":59000,"committee_interest_till_date":205,"bank_balance":81205},
    {"month":"Aug","expected_amount":20000,"actual_submission":18000,"missing_contribution":2000,"missing_by":"Karan","previous_missing_collected":0,"total_cash_received":18000,"advance_taken":10500,"advance_taken_by":"Simran","repayment_received":10200,"interest_received":200,"status":"Rahul overdue; repaid ₹10,000 + 2%","outstanding_advance":59500,"committee_interest_till_date":405,"bank_balance":98905},
    {"month":"Sep","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":2000,"total_cash_received":22000,"advance_taken":13000,"advance_taken_by":"Vijay","repayment_received":0,"interest_received":0,"status":"Karan cleared Aug contribution","outstanding_advance":72500,"committee_interest_till_date":405,"bank_balance":107905},
    {"month":"Oct","expected_amount":20000,"actual_submission":18000,"missing_contribution":2000,"missing_by":"Meera","previous_missing_collected":0,"total_cash_received":18000,"advance_taken":7500,"advance_taken_by":"Anjali","repayment_received":9090,"interest_received":90,"status":"Meera repaid ₹9,000 + 1%","outstanding_advance":71000,"committee_interest_till_date":495,"bank_balance":127495},
    {"month":"Nov","expected_amount":20000,"actual_submission":20000,"missing_contribution":0,"missing_by":"None","previous_missing_collected":2000,"total_cash_received":22000,"advance_taken":12000,"advance_taken_by":"Rahul","repayment_received":0,"interest_received":0,"status":"Meera cleared Oct due; Karan advance overdue","outstanding_advance":83000,"committee_interest_till_date":495,"bank_balance":137495},
    {"month":"Dec","expected_amount":20000,"actual_submission":18000,"missing_contribution":2000,"missing_by":"Vijay","previous_missing_collected":0,"total_cash_received":18000,"advance_taken":9500,"advance_taken_by":"Priya","repayment_received":25905,"interest_received":405,"status":"Neha repaid ₹15,000 + 2%; Simran repaid ₹10,500 + 1%","outstanding_advance":67000,"committee_interest_till_date":900,"bank_balance":171900},
]


def _can_view(db: Session, group: SavingsGroup, user: User) -> bool:
    if user.role == "ADMIN" or group.created_by_id == user.id:
        return True
    return db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.user_id == user.id,
        GroupMember.is_active == True,
    ).first() is not None


@router.get("/{group_id}/committee-ledger")
def committee_ledger(group_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")
    if not _can_view(db, group, current_user):
        raise HTTPException(status_code=403, detail="Join this group to view its committee ledger.")

    member_count = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.is_active == True).count()
    demo_member_count = max(member_count, 10)
    expected_total = sum(r["expected_amount"] for r in DEMO_ROWS)
    current_month_submissions = sum(r["actual_submission"] for r in DEMO_ROWS)
    arrears_recovered = sum(r["previous_missing_collected"] for r in DEMO_ROWS)
    committee_interest = sum(r["interest_received"] for r in DEMO_ROWS)
    missing_due = 2000
    outstanding_advances = DEMO_ROWS[-1]["outstanding_advance"]
    bank_balance = DEMO_ROWS[-1]["bank_balance"]

    # Projection: current earned interest + expected interest on currently outstanding advances.
    # Karan's overdue ₹11,000 uses 2%; remaining ₹56,000 uses normal 1% for this demo.
    projected_future_interest = 220 + 560
    projected_committee_interest = committee_interest + projected_future_interest
    bank_interest = 0.0  # Enter actual bank-credit data later; do not fabricate bank earnings.
    projected_profit = projected_committee_interest + bank_interest
    profit_share = projected_profit / demo_member_count
    contribution_share = expected_total / demo_member_count

    my_outstanding_due = 2000 if current_user.full_name.strip().lower().startswith("vijay") else 0
    estimated_member_receipt = contribution_share + profit_share - my_outstanding_due

    return {
        "group": {
            "id": group.id,
            "name": group.name,
            "is_creator": group.created_by_id == current_user.id,
            "can_manage": current_user.role == "ADMIN" or group.created_by_id == current_user.id,
        },
        "rows": DEMO_ROWS,
        "summary": {
            "expected_contributions": expected_total,
            "current_month_submissions": current_month_submissions,
            "arrears_recovered": arrears_recovered,
            "missing_contributions_due": missing_due,
            "bank_balance": bank_balance,
            "outstanding_advances": outstanding_advances,
            "committee_interest_received": committee_interest,
            "projected_committee_interest": projected_committee_interest,
            "bank_interest_received": bank_interest,
            "projected_total_profit": projected_profit,
            "total_committee_assets_now": bank_balance + outstanding_advances,
            "estimated_final_value_after_recovery": expected_total + projected_profit,
            "ready_to_distribute": False,
            "settlement_note": "Final distribution becomes ready after Vijay's missing ₹2,000 and all outstanding advances/interest are recovered.",
        },
        "member_summary": {
            "member_name": current_user.full_name,
            "estimated_contribution_share": contribution_share,
            "estimated_profit_share": profit_share,
            "outstanding_due": my_outstanding_due,
            "estimated_final_receipt": estimated_member_receipt,
        },
        "demo_note": "Hackathon demo ledger. Bank interest is intentionally ₹0 until an actual bank-interest credit is recorded.",
    }
