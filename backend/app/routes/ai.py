import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.risk_alert import RiskAlert
from app.models.user import User
from app.schemas.risk import RiskAlertOut, RiskAlertReview, AnalyzeTransactionRequest, AnalyzeTransactionResponse, ReasonItem
from app.services.auth_service import get_current_user, require_admin
from app.services.audit_service import log_audit
from app.ml.detector import detector

router = APIRouter(prefix="/api/ai", tags=["AI & Risk Anomaly Detection"])

@router.post("/analyze", response_model=AnalyzeTransactionResponse)
def analyze_transaction_preview(
    req: AnalyzeTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run the explainable AI anomaly detection engine against any candidate transaction amount.
    """
    result = detector.analyze_transaction(
        db=db,
        member_id=req.member_id,
        group_id=req.group_id,
        amount=req.amount
    )
    reasons = [ReasonItem(**r) for r in result["reasons"]]
    return AnalyzeTransactionResponse(
        is_anomalous=result["is_anomalous"],
        risk_level=result["risk_level"],
        anomaly_score=result["anomaly_score"],
        reasons=reasons,
        recommended_action=result["recommended_action"]
    )

@router.get("/alerts", response_model=List[RiskAlertOut])
def list_risk_alerts(
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(RiskAlert)
    if risk_level:
        query = query.filter(RiskAlert.risk_level == risk_level.upper())
    if status_filter:
        query = query.filter(RiskAlert.status == status_filter.upper())

    alerts = query.order_by(RiskAlert.created_at.desc()).all()
    results = []
    for a in alerts:
        a_out = RiskAlertOut.model_validate(a)
        try:
            raw_reasons = json.loads(a.reasons_json) if a.reasons_json else []
            a_out.reasons = [ReasonItem(**r) for r in raw_reasons]
        except Exception:
            a_out.reasons = []
        results.append(a_out)
    return results

@router.get("/alerts/{alert_id}", response_model=RiskAlertOut)
def get_risk_alert(
    alert_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Risk alert not found.")

    a_out = RiskAlertOut.model_validate(alert)
    try:
        raw_reasons = json.loads(alert.reasons_json) if alert.reasons_json else []
        a_out.reasons = [ReasonItem(**r) for r in raw_reasons]
    except Exception:
        a_out.reasons = []
    return a_out

@router.put("/alerts/{alert_id}/review", response_model=RiskAlertOut)
def review_risk_alert(
    alert_id: int,
    review_in: RiskAlertReview,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Human-in-the-loop review action by Administrator.
    Admin options: VALIDATED (Mark as Valid), INVESTIGATING (Mark for Further Investigation).
    AI never automatically punishes or changes accounts.
    """
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Risk alert not found.")

    prev_status = alert.status
    alert.status = review_in.status.upper()
    alert.admin_notes = review_in.admin_notes
    alert.reviewed_by = admin_user.full_name
    alert.reviewed_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(alert)

    log_audit(
        db=db,
        actor=admin_user,
        action="ADMIN_REVIEW_AI_RISK_ALERT",
        entity_type="RISK_ALERT",
        entity_id=alert.id,
        description=f"Admin {admin_user.full_name} reviewed AI Risk Alert #{alert.id} for {alert.member_name} (Amount: ₹{alert.amount:,.2f}) -> Set status to {alert.status}",
        previous_state={"status": prev_status},
        new_state={"status": alert.status, "notes": alert.admin_notes},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    a_out = RiskAlertOut.model_validate(alert)
    try:
        raw_reasons = json.loads(alert.reasons_json) if alert.reasons_json else []
        a_out.reasons = [ReasonItem(**r) for r in raw_reasons]
    except Exception:
        a_out.reasons = []
    return a_out
