import json
import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.user import User

def log_audit(
    db: Session,
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[Any],
    description: str,
    previous_state: Optional[Any] = None,
    new_state: Optional[Any] = None,
    ip_address: str = "127.0.0.1"
) -> AuditLog:
    """
    Append-only audit logger for compliance, traceability and security.
    """
    actor_id = actor.id if actor else None
    actor_name = actor.full_name if actor else "SYSTEM_AUTOMATION"
    actor_role = actor.role if actor else "SYSTEM"

    prev_str = json.dumps(previous_state, default=str) if isinstance(previous_state, (dict, list)) else (str(previous_state) if previous_state is not None else None)
    new_str = json.dumps(new_state, default=str) if isinstance(new_state, (dict, list)) else (str(new_state) if new_state is not None else None)

    audit_entry = AuditLog(
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
        previous_state=prev_str,
        new_state=new_str,
        ip_address=ip_address,
        created_at=datetime.datetime.utcnow()
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
