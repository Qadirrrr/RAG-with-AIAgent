"""Signup / login / me. The email matching SUPER_ADMIN_EMAIL becomes super-admin."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr, TypeAdapter
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import settings
from app.db import User, Workspace, ensure_free_subscription, get_db
from app.deps import get_current_user
from app.models.schemas import TokenResponse, UserCreate, UserLogin, UserOut, WorkspaceOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, is_super_admin=user.is_super_admin,
                   is_active=user.is_active, created_at=user.created_at)


@router.post("/signup", response_model=TokenResponse)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    # Validate email format (TypeAdapter raises a clear error on bad input).
    try:
        email = str(TypeAdapter(EmailStr).validate_python(payload.email.strip().lower()))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide a valid email address.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
    is_admin = bool(settings.SUPER_ADMIN_EMAIL) and email == settings.SUPER_ADMIN_EMAIL.strip().lower()
    user = User(email=email, hashed_password=hash_password(payload.password), is_super_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    # Every user gets their own workspace with the free plan.
    ws = Workspace(owner_id=user.id, name="My Workspace")
    db.add(ws)
    db.commit()
    db.refresh(ws)
    ensure_free_subscription(db, ws.id)
    return TokenResponse(access_token=create_access_token(user.id), user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled. Contact support.")
    return TokenResponse(access_token=create_access_token(user.id), user=_user_out(user))


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    return {
        "user": _user_out(user),
        "workspaces": [WorkspaceOut(id=w.id, owner_id=w.owner_id, name=w.name, created_at=w.created_at) for w in workspaces],
    }
