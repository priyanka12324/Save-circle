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
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    email = user_in.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

    # Public registration must never grant administrator privileges.
    new_user = User(
        full_name=user_in.full_name.strip(),
        email=email,
        phone=user_in.phone.strip() if user_in.phone else None,
        hashed_password=get_password_hash(user_in.password),
        role="MEMBER",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(
        db=db,
        actor=new_user,
        action="USER_REGISTERED",
        entity_type="USER",
        entity_id=new_user.id,
        description=f"New MEMBER user registered: {new_user.full_name} ({new_user.email})",
        ip_address=request.client.host if request.client else "unknown",
    )

    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(new_user))


@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email.lower().strip()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    log_audit(
        db=db,
        actor=user,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=user.id,
        description=f"User {user.full_name} logged in successfully.",
        ip_address=request.client.host if request.client else "unknown",
    )
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
