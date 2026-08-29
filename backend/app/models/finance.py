import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from app.database import Base


class CommitteeSettings(Base):
    __tablename__ = "committee_settings"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), unique=True, nullable=False)
    normal_interest_rate = Column(Float, nullable=False, default=1.0)  # percent, one-time
    overdue_interest_rate = Column(Float, nullable=False, default=2.0)  # percent, one-time
    repayment_period_months = Column(Integer, nullable=False, default=6)
    bank_interest_rate = Column(Float, nullable=False, default=0.0)  # percent per annum, informational/estimated
    profit_share_method = Column(String(50), nullable=False, default="EQUAL")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AdvanceRequest(Base):
    __tablename__ = "advance_requests"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED, REPAID, OVERDUE
    requested_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    normal_interest_rate = Column(Float, nullable=False, default=1.0)
    overdue_interest_rate = Column(Float, nullable=False, default=2.0)
    principal_repaid = Column(Float, nullable=False, default=0.0)
    interest_repaid = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
