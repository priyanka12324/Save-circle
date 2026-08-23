from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    description: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
