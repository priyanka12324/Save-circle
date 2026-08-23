import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    cycle_id = Column(Integer, ForeignKey("savings_cycles.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(100), default="UPI (Demo)")  # UPI (Demo), Bank Transfer (Demo), Cash (Demo)
    transaction_ref = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, VERIFIED, REJECTED
    notes = Column(Text, nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    member = relationship("User", foreign_keys=[member_id], back_populates="contributions")
    group = relationship("SavingsGroup", back_populates="contributions")
    cycle = relationship("SavingsCycle", back_populates="contributions")
    receipt = relationship("DigitalReceipt", back_populates="contribution", uselist=False, cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String(100), unique=True, index=True, nullable=False)
    member_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(50), default="CONTRIBUTION")  # CONTRIBUTION, WITHDRAWAL, REFUND, ADJUSTMENT
    status = Column(String(50), default="COMPLETED")   # PENDING, COMPLETED, FLAGGED, REJECTED
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    member = relationship("User", foreign_keys=[member_id], back_populates="transactions")
    group = relationship("SavingsGroup", back_populates="transactions")
    risk_alert = relationship("RiskAlert", back_populates="transaction", uselist=False, cascade="all, delete-orphan")


class DigitalReceipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(100), unique=True, index=True, nullable=False)
    transaction_ref = Column(String(100), nullable=False)
    contribution_id = Column(Integer, ForeignKey("contributions.id", ondelete="SET NULL"), nullable=True)
    member_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    member_name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    group_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(100), nullable=False)
    payment_status = Column(String(50), default="VERIFIED")
    verified_by_name = Column(String(255), nullable=False)
    verification_date = Column(DateTime, default=datetime.datetime.utcnow)
    security_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    member = relationship("User", foreign_keys=[member_id], back_populates="receipts")
    contribution = relationship("Contribution", back_populates="receipt")
