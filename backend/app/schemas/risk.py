from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ReasonItem(BaseModel):
    indicator: str  # "+" or "-"
    type: str       # "FLAG", "INFO", "POSITIVE"
    message: str

class RiskAlertOut(BaseModel):
    id: int
    transaction_id: Optional[int] = None
    member_id: int
    member_name: str
    group_id: int
    group_name: str
    amount: float
    risk_level: str  # LOW, MEDIUM, HIGH
    anomaly_score: float
    reasons: List[ReasonItem] = []
    reasons_json: Optional[str] = None
    recommended_action: str
    status: str  # PENDING_REVIEW, VALIDATED, INVESTIGATING
    admin_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RiskAlertReview(BaseModel):
    status: str = Field(..., description="VALIDATED or INVESTIGATING")
    admin_notes: Optional[str] = None

class AnalyzeTransactionRequest(BaseModel):
    member_id: int
    group_id: int
    amount: float
    type: str = "CONTRIBUTION"

class AnalyzeTransactionResponse(BaseModel):
    is_anomalous: bool
    risk_level: str  # LOW, MEDIUM, HIGH
    anomaly_score: float
    reasons: List[ReasonItem]
    recommended_action: str
