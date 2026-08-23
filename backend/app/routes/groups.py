from typing import List, Optional
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.group import SavingsGroup, GroupMember, SavingsCycle
from app.models.transaction import Contribution
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate, GroupOut, GroupMemberAdd, GroupMemberOut, SavingsCycleOut
from app.services.auth_service import get_current_user, require_admin
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/groups", tags=["Groups"])

@router.get("", response_model=List[GroupOut])
def list_groups(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(SavingsGroup)
    if active_only:
        query = query.filter(SavingsGroup.is_active == True)
    
    groups = query.order_by(SavingsGroup.created_at.desc()).all()
    results = []
    for g in groups:
        member_cnt = db.query(GroupMember).filter(GroupMember.group_id == g.id, GroupMember.is_active == True).count()
        total_coll = db.query(func.sum(Contribution.amount)).filter(
            Contribution.group_id == g.id,
            Contribution.status == "VERIFIED"
        ).scalar() or 0.0

        g_out = GroupOut.model_validate(g)
        g_out.member_count = member_cnt
        g_out.total_collected = float(total_coll)
        results.append(g_out)
    return results

@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    group_in: GroupCreate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    new_group = SavingsGroup(
        name=group_in.name.strip(),
        description=group_in.description,
        contribution_amount=group_in.contribution_amount,
        contribution_frequency=group_in.contribution_frequency,
        max_members=group_in.max_members,
        current_cycle=1,
        total_cycles=group_in.total_cycles,
        start_date=group_in.start_date or datetime.datetime.utcnow(),
        is_active=True,
        created_by_id=admin_user.id
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    # Initialize cycle 1
    cycle_target = group_in.contribution_amount * group_in.max_members
    initial_cycle = SavingsCycle(
        group_id=new_group.id,
        cycle_number=1,
        target_amount=cycle_target,
        collected_amount=0.0,
        status="ACTIVE",
        start_date=datetime.datetime.utcnow()
    )
    db.add(initial_cycle)
    db.commit()

    log_audit(
        db=db,
        actor=admin_user,
        action="CREATE_GROUP",
        entity_type="GROUP",
        entity_id=new_group.id,
        description=f"Admin {admin_user.full_name} created group '{new_group.name}' with ₹{new_group.contribution_amount:,.2f} {new_group.contribution_frequency} rule.",
        new_state={"name": new_group.name, "amount": new_group.contribution_amount, "cycles": new_group.total_cycles},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    g_out = GroupOut.model_validate(new_group)
    g_out.member_count = 0
    g_out.total_collected = 0.0
    return g_out

@router.get("/{group_id}", response_model=GroupOut)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")
    
    member_cnt = db.query(GroupMember).filter(GroupMember.group_id == group.id, GroupMember.is_active == True).count()
    total_coll = db.query(func.sum(Contribution.amount)).filter(
        Contribution.group_id == group.id,
        Contribution.status == "VERIFIED"
    ).scalar() or 0.0

    g_out = GroupOut.model_validate(group)
    g_out.member_count = member_cnt
    g_out.total_collected = float(total_coll)
    return g_out

@router.put("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")
    
    prev_state = {"name": group.name, "amount": group.contribution_amount, "frequency": group.contribution_frequency, "is_active": group.is_active}
    
    if group_update.name is not None:
        group.name = group_update.name
    if group_update.description is not None:
        group.description = group_update.description
    if group_update.contribution_amount is not None:
        group.contribution_amount = group_update.contribution_amount
    if group_update.contribution_frequency is not None:
        group.contribution_frequency = group_update.contribution_frequency
    if group_update.max_members is not None:
        group.max_members = group_update.max_members
    if group_update.is_active is not None:
        group.is_active = group_update.is_active

    db.commit()
    db.refresh(group)

    log_audit(
        db=db,
        actor=admin_user,
        action="UPDATE_GROUP",
        entity_type="GROUP",
        entity_id=group.id,
        description=f"Admin {admin_user.full_name} updated settings for group '{group.name}'",
        previous_state=prev_state,
        new_state=group_update.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    g_out = GroupOut.model_validate(group)
    return g_out

@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
def deactivate_group(
    group_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Savings group not found.")
    
    group.is_active = False
    db.commit()

    log_audit(
        db=db,
        actor=admin_user,
        action="DEACTIVATE_GROUP",
        entity_type="GROUP",
        entity_id=group.id,
        description=f"Admin {admin_user.full_name} deactivated savings group '{group.name}'",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"message": f"Group '{group.name}' has been deactivated successfully."}

@router.get("/{group_id}/members", response_model=List[GroupMemberOut])
def get_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.is_active == True).all()
    results = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        m_out = GroupMemberOut.model_validate(m)
        if user:
            m_out.user_name = user.full_name
            m_out.user_email = user.email
            m_out.user_phone = user.phone
        results.append(m_out)
    return results

@router.post("/{group_id}/members", response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
def add_member_to_group(
    group_id: int,
    member_in: GroupMemberAdd,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Member can self-join or Admin can add
    if current_user.role != "ADMIN" and current_user.id != member_in.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to enroll another user.")

    group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id, SavingsGroup.is_active == True).first()
    if not group:
        raise HTTPException(status_code=404, detail="Active savings group not found.")

    target_user = db.query(User).filter(User.id == member_in.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check capacity
    current_count = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.is_active == True).count()
    if current_count >= group.max_members:
        raise HTTPException(status_code=400, detail="Group has reached maximum member capacity.")

    # Check if already joined
    existing = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == member_in.user_id).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="User is already an active member of this group.")
        existing.is_active = True
        existing.joined_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        mem_obj = existing
    else:
        mem_obj = GroupMember(
            group_id=group_id,
            user_id=member_in.user_id,
            role_in_group=member_in.role_in_group,
            is_active=True
        )
        db.add(mem_obj)
        db.commit()
        db.refresh(mem_obj)

    log_audit(
        db=db,
        actor=current_user,
        action="ENROLL_GROUP_MEMBER",
        entity_type="GROUP_MEMBER",
        entity_id=mem_obj.id,
        description=f"User {target_user.full_name} enrolled into group '{group.name}'",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    out = GroupMemberOut.model_validate(mem_obj)
    out.user_name = target_user.full_name
    out.user_email = target_user.email
    out.user_phone = target_user.phone
    return out

@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_member_from_group(
    group_id: int,
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    mem = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Member enrollment record not found.")

    mem.is_active = False
    db.commit()

    log_audit(
        db=db,
        actor=admin_user,
        action="REMOVE_GROUP_MEMBER",
        entity_type="GROUP_MEMBER",
        entity_id=mem.id,
        description=f"Admin {admin_user.full_name} removed User ID {user_id} from group ID {group_id}",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"message": "Member removed from group successfully."}

@router.get("/{group_id}/cycles", response_model=List[SavingsCycleOut])
def get_group_cycles(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cycles = db.query(SavingsCycle).filter(SavingsCycle.group_id == group_id).order_by(SavingsCycle.cycle_number.asc()).all()
    return [SavingsCycleOut.model_validate(c) for c in cycles]
