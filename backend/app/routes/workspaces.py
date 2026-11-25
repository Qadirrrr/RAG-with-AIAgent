"""Workspace CRUD. A workspace is one customer's isolated area."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import Workspace, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import SubscriptionOut, WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _ws_out(ws: Workspace) -> WorkspaceOut:
    return WorkspaceOut(id=ws.id, owner_id=ws.owner_id, name=ws.name, created_at=ws.created_at)


@router.post("", response_model=WorkspaceOut)
def create_workspace(payload: WorkspaceCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = Workspace(owner_id=user.id, name=payload.name.strip())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    ensure_free_subscription(db, ws.id)
    return _ws_out(ws)


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_super_admin:
        rows = db.query(Workspace).all()
    else:
        rows = db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    return [_ws_out(w) for w in rows]


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    return _ws_out(ws)


@router.get("/{workspace_id}/subscription", response_model=SubscriptionOut)
def get_subscription(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    sub = ensure_free_subscription(db, ws.id)
    return SubscriptionOut(id=sub.id, workspace_id=sub.workspace_id, plan=sub.plan, status=sub.status,
                           monthly_message_limit=sub.monthly_message_limit, agent_limit=sub.agent_limit,
                           document_limit=sub.document_limit, messages_used_this_month=sub.messages_used_this_month)
