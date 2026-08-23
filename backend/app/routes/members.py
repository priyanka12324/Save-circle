from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.group import GroupMember, SavingsGroup
from app.schemas.user import UserOut, UserUpdate
from app.services.auth_service import get_current_user, require_admin
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/members", tags=["Members"])

@router.get("", response_model=List[UserOut])
def list_members(
    search: Optional[str] = None,
    role: Optional[str] = None,
    group_id: Optional[int] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.upper())
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern)) | 
            (User.phone.ilike(search_pattern))
        )
    if group_id:
        user_ids = db.query(GroupMember.user_id).filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        ).subquery()
        query = query.filter(User.id.in_(user_ids))

    users = query.order_by(User.created_at.desc()).all()
    return [UserOut.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserOut)
def get_member(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Member can view their own profile, admin can view any
    if current_user.role != "ADMIN" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden access to member details.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found.")
    return UserOut.model_validate(user)

@router.put("/{user_id}", response_model=UserOut)
def update_member(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "ADMIN" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden access to update profile.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found.")

    prev_state = {"full_name": user.full_name, "phone": user.phone, "is_active": user.is_active}

    if user_update.full_name is not None:
        user.full_name = user_update.full_name.strip()
    if user_update.phone is not None:
        user.phone = user_update.phone.strip()
    if user_update.is_active is not None and current_user.role == "ADMIN":
        user.is_active = user_update.is_active

    db.commit()
    db.refresh(user)

    log_audit(
        db=db,
        actor=current_user,
        action="UPDATE_MEMBER_PROFILE",
        entity_type="USER",
        entity_id=user.id,
        description=f"Profile for user {user.full_name} ({user.email}) updated by {current_user.full_name}",
        previous_state=prev_state,
        new_state=user_update.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return UserOut.model_validate(user)
