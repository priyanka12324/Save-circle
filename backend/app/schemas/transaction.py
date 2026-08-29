from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ContributionCreate(BaseModel):
    group_id: int
    amount: float = Field(..., gt=0, description="Amount in INR")
    payment_method: str = Field("UPI (Demo)", description="UPI (Demo), Bank Transfer (Demo), Cash (Demo)")
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None
    proof_filename: Optional[str] = None
    proof_content_type: Optional[str] = None
    proof_data_url: Optional[str] = None


class ContributionVerify(BaseModel):
    status: str = Field(..., description="VERIFIED or REJECTED")
    notes: Optional[str] = None


class ContributionOut(BaseModel):
    id: int
    member_id: int
    member_name: Optional[str] = None
    group_id: int
    group_name: Optional[str] = None
    cycle_id: Optional[int] = None
    amount: float
    payment_method: str
    transaction_ref: str
    status: str
    notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    receipt_id: Optional[int] = None
    payment_proof_url: Optional[str] = None
    payment_proof_filename: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    member_id: int
    group_id: int
    amount: float = Field(..., gt=0)
    type: str = Field("CONTRIBUTION", description="CONTRIBUTION, WITHDRAWAL, REFUND, ADJUSTMENT")
    description: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    reference_id: str
    member_id: int
    member_name: Optional[str] = None
    group_id: int
    group_name: Optional[str] = None
    amount: float
    type: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    risk_level: Optional[str] = None

    class Config:
        from_attributes = True


class DigitalReceiptOut(BaseModel):
    id: int
    receipt_number: str
    transaction_ref: str
    contribution_id: Optional[int] = None
    member_id: int
    member_name: str
    group_id: int
    group_name: str
    amount: float
    payment_method: str
    payment_status: str
    verified_by_name: str
    verification_date: datetime
    security_hash: str
    created_at: datetime

    class Config:
        from_attributes = True
