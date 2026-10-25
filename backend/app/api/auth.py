from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import create_token, get_current_user, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import Institute, User
from app.schemas.auth import BootstrapAdminRequest, LoginRequest, LoginResponse, PasswordChangeRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)):
    return {
        "needs_admin": db.scalar(select(User.id).limit(1)) is None,
        "has_department_data": db.scalar(select(Institute.id).limit(1)) is not None,
    }


@router.post("/bootstrap", response_model=LoginResponse, status_code=201)
def bootstrap_admin(body: BootstrapAdminRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).limit(1)) is not None:
        raise HTTPException(409, "The first administrator has already been created")
    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role="admin",
        active=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    return LoginResponse(access_token=create_token(user), user=UserResponse.model_validate(user))


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.active.is_(True)))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if body.role and user.role != body.role:
        raise HTTPException(403, f"This account is registered as {user.role}. Choose the {user.role.title()} workspace.")
    return LoginResponse(access_token=create_token(user), user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)): return user


@router.post("/change-password")
def change_password(body: PasswordChangeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

