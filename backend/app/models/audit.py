import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class AuditLog(Base):
    """
    Immutable, append-only audit trail logging system events,
    administrative actions, security decisions, and data modifications.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(255), nullable=False)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)  # e.g., "CREATE_GROUP", "VERIFY_CONTRIBUTION", "FLAG_TRANSACTION", "REVIEW_ALERT"
    entity_type = Column(String(100), nullable=False)  # e.g., "GROUP", "CONTRIBUTION", "TRANSACTION", "RISK_ALERT"
    entity_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    previous_state = Column(Text, nullable=True)  # JSON representation of before state
    new_state = Column(Text, nullable=True)       # JSON representation of after state
    ip_address = Column(String(50), default="127.0.0.1")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
