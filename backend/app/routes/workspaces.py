"""Workspace CRUD. A workspace is one customer's isolated area."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import UsageEvent, Workspace, ensure_free_subscription, get_db
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


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Owner only: deleting another user's project (or a missing one) is a
    # 404, matching the read endpoints, so ids cannot be probed.
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws or ws.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    # A user must always keep at least one project.
    owned_count = db.query(Workspace).filter(Workspace.owner_id == user.id).count()
    if owned_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your only project. Create another project first.")

    agent_ids = [a.id for a in ws.agents]

    # Best effort: remove each chatbot's private Chroma collection.
    if agent_ids:
        try:
            from app.services.tenant_vector_store import tenant_vector_store
            for agent_id in agent_ids:
                try:
                    tenant_vector_store.delete_agent_collection(agent_id)
                except Exception:
                    pass
        except Exception:
            pass

    # Usage events carry a workspace_id foreign key but have no cascade
    # from Workspace (rows with agent_id NULL are not covered by the Agent
    # cascade either), so delete them explicitly in the same transaction.
    # Without this the delete fails with an FK constraint violation (HTTP
    # 500) for any project that has ever been used. The chatbots, their
    # documents, conversations (with messages) and API keys, and the
    # subscription are removed by the ORM delete-orphan cascades.
    db.query(UsageEvent).filter(UsageEvent.workspace_id == ws.id).delete(synchronize_session=False)
    db.delete(ws)
    db.commit()
    return {"message": "Project deleted successfully", "id": workspace_id}


@router.get("/{workspace_id}/subscription", response_model=SubscriptionOut)
def get_subscription(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    sub = ensure_free_subscription(db, ws.id)
    return SubscriptionOut(id=sub.id, workspace_id=sub.workspace_id, plan=sub.plan, status=sub.status,
                           monthly_message_limit=sub.monthly_message_limit, agent_limit=sub.agent_limit,
                           document_limit=sub.document_limit, messages_used_this_month=sub.messages_used_this_month)
