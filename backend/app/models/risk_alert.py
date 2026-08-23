import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RiskAlert(Base):
    """
    AI/ML Anomaly Detection Risk Alert record.
    Provides explainable indicators, risk score, and human-in-the-loop audit trail.
    """
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True)
    member_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    member_name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    group_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    risk_level = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH
    anomaly_score = Column(Float, default=0.0)  # -1.0 to 1.0 (isolation forest score or probability)
    reasons_json = Column(Text, nullable=False)  # JSON encoded list of explainable reasoning points
    recommended_action = Column(String(255), default="Administrator review required")
    status = Column(String(50), default="PENDING_REVIEW")  # PENDING_REVIEW, VALIDATED, INVESTIGATING
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    member = relationship("User", back_populates="risk_alerts")
    transaction = relationship("Transaction", back_populates="risk_alert")
