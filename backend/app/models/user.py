import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="MEMBER", nullable=False)  # "ADMIN" | "MEMBER"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    contributions = relationship("Contribution", back_populates="member", cascade="all, delete-orphan", foreign_keys="Contribution.member_id")
    transactions = relationship("Transaction", back_populates="member", cascade="all, delete-orphan", foreign_keys="Transaction.member_id")
    receipts = relationship("DigitalReceipt", back_populates="member", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="member", cascade="all, delete-orphan")
