import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserOut
from app.services.auth_service import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    if user_in.password != user_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )
    
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Normalize role
    role = user_in.role.upper()
    if role not in ["ADMIN", "MEMBER"]:
        role = "MEMBER"

    new_user = User(
        full_name=user_in.full_name.strip(),
        email=user_in.email.lower().strip(),
        phone=user_in.phone.strip() if user_in.phone else None,
        hashed_password=get_password_hash(user_in.password),
        role=role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log audit entry
    log_audit(
        db=db,
        actor=new_user,
        action="USER_REGISTERED",
        entity_type="USER",
        entity_id=new_user.id,
        description=f"New {new_user.role} user registered: {new_user.full_name} ({new_user.email})",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    access_token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    return TokenResponse(access_token=access_token, user=UserOut.model_validate(new_user))

@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email.lower().strip()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    # Log audit entry
    log_audit(
        db=db,
        actor=user,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=user.id,
        description=f"User {user.full_name} logged in successfully.",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return TokenResponse(access_token=access_token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
