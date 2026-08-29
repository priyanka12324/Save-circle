from typing import List
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.group import SavingsGroup, GroupMember, SavingsCycle
from app.models.transaction import Contribution
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate, GroupOut, GroupMemberAdd, GroupMemberOut, SavingsCycleOut
from app.services.auth_service import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/groups", tags=["Groups"])

def can_manage_group(user: User, group: SavingsGroup) -> bool:
    return user.role == "ADMIN" or group.created_by_id == user.id

def group_out(db: Session, group: SavingsGroup, user: User) -> GroupOut:
    out = GroupOut.model_validate(group)
    out.member_count = db.query(GroupMember).filter(GroupMember.group_id == group.id, GroupMember.is_active == True).count()
    out.total_collected = float(db.query(func.sum(Contribution.amount)).filter(Contribution.group_id == group.id, Contribution.status == "VERIFIED").scalar() or 0.0)
    membership = db.query(GroupMember).filter(GroupMember.group_id == group.id, GroupMember.user_id == user.id, GroupMember.is_active == True).first()
    out.is_creator = group.created_by_id == user.id
    out.can_manage = can_manage_group(user, group)
    out.is_member = membership is not None
    return out

@router.get("", response_model=List[GroupOut])
def list_groups(active_only: bool = True, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SavingsGroup)
    if active_only:
        query = query.filter(SavingsGroup.is_active == True)
    return [group_out(db, g, current_user) for g in query.order_by(SavingsGroup.created_at.desc()).all()]

@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(group_in: GroupCreate, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_group = SavingsGroup(name=group_in.name.strip(), description=group_in.description, contribution_amount=group_in.contribution_amount, contribution_frequency=group_in.contribution_frequency, max_members=group_in.max_members, current_cycle=1, total_cycles=group_in.total_cycles, start_date=group_in.start_date or datetime.datetime.utcnow(), is_active=True, created_by_id=current_user.id)
    db.add(new_group); db.commit(); db.refresh(new_group)
    creator_membership = GroupMember(group_id=new_group.id, user_id=current_user.id, role_in_group="CREATOR", is_active=True)
    cycle = SavingsCycle(group_id=new_group.id, cycle_number=1, target_amount=group_in.contribution_amount * group_in.max_members, collected_amount=0.0, status="ACTIVE", start_date=new_group.start_date)
    db.add_all([creator_membership, cycle]); db.commit()
    log_audit(db=db, actor=current_user, action="CREATE_GROUP", entity_type="GROUP", entity_id=new_group.id, description=f"{current_user.full_name} created savings group '{new_group.name}' and became its Group Creator.", new_state={"name":new_group.name,"amount":new_group.contribution_amount,"cycles":new_group.total_cycles,"creator_id":current_user.id}, ip_address=request.client.host if request.client else "127.0.0.1")
    return group_out(db, new_group, current_user)

@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id).first()
    if not group: raise HTTPException(status_code=404,detail="Savings group not found.")
    return group_out(db,group,current_user)

@router.put("/{group_id}", response_model=GroupOut)
def update_group(group_id:int, group_update:GroupUpdate, request:Request, current_user:User=Depends(get_current_user), db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id).first()
    if not group: raise HTTPException(status_code=404,detail="Savings group not found.")
    if not can_manage_group(current_user,group): raise HTTPException(status_code=403,detail="Only the Group Creator or Platform Admin can manage this group.")
    prev={"name":group.name,"amount":group.contribution_amount,"frequency":group.contribution_frequency,"is_active":group.is_active}
    for field,val in group_update.model_dump(exclude_unset=True).items(): setattr(group,field,val)
    db.commit();db.refresh(group)
    log_audit(db=db,actor=current_user,action="UPDATE_GROUP",entity_type="GROUP",entity_id=group.id,description=f"{current_user.full_name} updated group '{group.name}'.",previous_state=prev,new_state=group_update.model_dump(exclude_unset=True),ip_address=request.client.host if request.client else "127.0.0.1")
    return group_out(db,group,current_user)

@router.delete("/{group_id}")
def deactivate_group(group_id:int,request:Request,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id).first()
    if not group: raise HTTPException(status_code=404,detail="Savings group not found.")
    if not can_manage_group(current_user,group): raise HTTPException(status_code=403,detail="Only the Group Creator or Platform Admin can deactivate this group.")
    group.is_active=False;db.commit()
    log_audit(db=db,actor=current_user,action="DEACTIVATE_GROUP",entity_type="GROUP",entity_id=group.id,description=f"{current_user.full_name} deactivated '{group.name}'.",ip_address=request.client.host if request.client else "127.0.0.1")
    return {"message":f"Group '{group.name}' has been deactivated successfully."}

@router.get("/{group_id}/members",response_model=List[GroupMemberOut])
def get_group_members(group_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id).first()
    if not group: raise HTTPException(status_code=404,detail="Savings group not found.")
    membership=db.query(GroupMember).filter(GroupMember.group_id==group_id,GroupMember.user_id==current_user.id,GroupMember.is_active==True).first()
    if current_user.role!="ADMIN" and not membership: raise HTTPException(status_code=403,detail="Join this group to view its members.")
    results=[]
    for m in db.query(GroupMember).filter(GroupMember.group_id==group_id,GroupMember.is_active==True).all():
        u=db.query(User).filter(User.id==m.user_id).first();o=GroupMemberOut.model_validate(m)
        if u:o.user_name=u.full_name;o.user_email=u.email;o.user_phone=u.phone
        results.append(o)
    return results

@router.post("/{group_id}/members",response_model=GroupMemberOut,status_code=status.HTTP_201_CREATED)
def add_member_to_group(group_id:int,member_in:GroupMemberAdd,request:Request,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id,SavingsGroup.is_active==True).first()
    if not group: raise HTTPException(status_code=404,detail="Active savings group not found.")
    if current_user.role!="ADMIN" and current_user.id!=member_in.user_id and group.created_by_id!=current_user.id: raise HTTPException(status_code=403,detail="Only the Group Creator or Platform Admin can add another user.")
    target=db.query(User).filter(User.id==member_in.user_id).first()
    if not target: raise HTTPException(status_code=404,detail="User not found.")
    if db.query(GroupMember).filter(GroupMember.group_id==group_id,GroupMember.is_active==True).count()>=group.max_members: raise HTTPException(status_code=400,detail="Group has reached maximum member capacity.")
    existing=db.query(GroupMember).filter(GroupMember.group_id==group_id,GroupMember.user_id==member_in.user_id).first()
    if existing:
        if existing.is_active: raise HTTPException(status_code=400,detail="User is already an active member of this group.")
        existing.is_active=True;existing.joined_at=datetime.datetime.utcnow();mem=existing
    else:
        role="MEMBER" if current_user.role!="ADMIN" and member_in.user_id==current_user.id else member_in.role_in_group
        mem=GroupMember(group_id=group_id,user_id=member_in.user_id,role_in_group=role,is_active=True);db.add(mem)
    db.commit();db.refresh(mem)
    log_audit(db=db,actor=current_user,action="ENROLL_GROUP_MEMBER",entity_type="GROUP_MEMBER",entity_id=mem.id,description=f"{target.full_name} enrolled into group '{group.name}'.",ip_address=request.client.host if request.client else "127.0.0.1")
    out=GroupMemberOut.model_validate(mem);out.user_name=target.full_name;out.user_email=target.email;out.user_phone=target.phone;return out

@router.delete("/{group_id}/members/{user_id}")
def remove_member_from_group(group_id:int,user_id:int,request:Request,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    group=db.query(SavingsGroup).filter(SavingsGroup.id==group_id).first()
    if not group: raise HTTPException(status_code=404,detail="Savings group not found.")
    if not can_manage_group(current_user,group): raise HTTPException(status_code=403,detail="Only the Group Creator or Platform Admin can remove members.")
    if user_id==group.created_by_id: raise HTTPException(status_code=400,detail="The Group Creator cannot be removed from their own group.")
    mem=db.query(GroupMember).filter(GroupMember.group_id==group_id,GroupMember.user_id==user_id).first()
    if not mem: raise HTTPException(status_code=404,detail="Member enrollment record not found.")
    mem.is_active=False;db.commit()
    log_audit(db=db,actor=current_user,action="REMOVE_GROUP_MEMBER",entity_type="GROUP_MEMBER",entity_id=mem.id,description=f"{current_user.full_name} removed User ID {user_id} from group '{group.name}'.",ip_address=request.client.host if request.client else "127.0.0.1")
    return {"message":"Member removed from group successfully."}

@router.get("/{group_id}/cycles",response_model=List[SavingsCycleOut])
def get_group_cycles(group_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return [SavingsCycleOut.model_validate(c) for c in db.query(SavingsCycle).filter(SavingsCycle.group_id==group_id).order_by(SavingsCycle.cycle_number.asc()).all()]
