from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None
    contribution_amount: float = Field(..., gt=0)
    contribution_frequency: str = Field("Monthly", description="Monthly, Weekly, Bi-Weekly")
    max_members: int = Field(20, ge=2, le=500)
    total_cycles: int = Field(12, ge=1, le=100)
    start_date: Optional[datetime] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contribution_amount: Optional[float] = None
    contribution_frequency: Optional[str] = None
    max_members: Optional[int] = None
    is_active: Optional[bool] = None

class SavingsCycleOut(BaseModel):
    id: int
    group_id: int
    cycle_number: int
    target_amount: float
    collected_amount: float
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class GroupMemberOut(BaseModel):
    id: int
    user_id: int
    group_id: int
    role_in_group: str
    joined_at: datetime
    is_active: bool
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

    class Config:
        from_attributes = True

class GroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    contribution_amount: float
    contribution_frequency: str
    max_members: int
    current_cycle: int
    total_cycles: int
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    member_count: Optional[int] = 0
    total_collected: Optional[float] = 0.0

    class Config:
        from_attributes = True

class GroupMemberAdd(BaseModel):
    user_id: int
    role_in_group: str = "MEMBER"
