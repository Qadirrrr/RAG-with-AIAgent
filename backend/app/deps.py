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
    from app.db import User

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated. Please log in.")
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token. Please log in again.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or disabled.")
    return user


def get_workspace_or_404(workspace_id: str, user, db: Session) -> Workspace:
    """Return the workspace if the user owns it or is a super-admin.

    Returns 404 (not 403) for workspaces the user cannot see, so one
    customer cannot probe another customer's workspace ids.
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    if user.is_super_admin or ws.owner_id == user.id:
        return ws
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")


def require_super_admin(user=Depends(get_current_user)):
    if not user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin access required.")
    return user
