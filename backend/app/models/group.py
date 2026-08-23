import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class SavingsGroup(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contribution_amount = Column(Float, nullable=False, default=2000.0)
    contribution_frequency = Column(String(50), nullable=False, default="Monthly")  # Monthly, Weekly, Bi-Weekly
    max_members = Column(Integer, nullable=False, default=20)
    current_cycle = Column(Integer, nullable=False, default=1)
    total_cycles = Column(Integer, nullable=False, default=12)
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    cycles = relationship("SavingsCycle", back_populates="group", cascade="all, delete-orphan")
    contributions = relationship("Contribution", back_populates="group")
    transactions = relationship("Transaction", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_group = Column(String(50), default="MEMBER")  # MEMBER, TREASURER, AUDITOR
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    group = relationship("SavingsGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class SavingsCycle(Base):
    __tablename__ = "savings_cycles"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    target_amount = Column(Float, nullable=False, default=0.0)
    collected_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="ACTIVE")  # UPCOMING, ACTIVE, COMPLETED
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    group = relationship("SavingsGroup", back_populates="cycles")
    contributions = relationship("Contribution", back_populates="cycle")
