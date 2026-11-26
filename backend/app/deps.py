"""Shared FastAPI dependencies: current user, workspace access, admin guard."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.db import Workspace, get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    from app.db import User, Workspace, ensure_free_subscription
    import uuid

    if credentials and credentials.credentials:
        try:
            user_id = decode_access_token(credentials.credentials)
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active:
                    return user
        except Exception:
            pass

    # Single-Tenant Auto-User: find existing or create default admin
    user = db.query(User).first()
    if not user:
        user = User(
            id=uuid.uuid4().hex,
            email="admin@ragagent.local",
            name="Admin",
            hashed_password="local_password_hash",
            is_active=True,
            is_super_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        ws = Workspace(
            id=uuid.uuid4().hex,
            name="Default Workspace",
            owner_id=user.id,
        )
        db.add(ws)
        ensure_free_subscription(user.id, ws.id, db)
        db.commit()

    return user


def get_workspace_or_404(workspace_id: str, user, db: Session) -> Workspace:
    """Return workspace, falling back to default workspace in single-user mode."""
    if workspace_id:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if ws:
            return ws
    # Fallback to any workspace owned by user or first workspace
    ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
    if not ws:
        ws = db.query(Workspace).first()
    if ws:
        return ws
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")


def require_super_admin(user=Depends(get_current_user)):
    if not user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin access required.")
    return user
