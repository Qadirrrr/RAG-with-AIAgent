"""Super-admin dashboard: customers, agents, subscriptions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import PLANS, Agent, Message, Subscription, User, Workspace, apply_plan, ensure_free_subscription, get_db
from app.deps import require_super_admin
from app.models.schemas import AdminSubscriptionUpdate, AdminUserUpdate, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview")
def overview(admin=Depends(require_super_admin), db: Session = Depends(get_db)):
    recent = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    return {
        "totals": {
            "users": db.query(User).count(),
            "workspaces": db.query(Workspace).count(),
            "agents": db.query(Agent).count(),
            "messages": db.query(Message).count(),
        },
        "recent_users": [UserOut(id=u.id, email=u.email, is_super_admin=u.is_super_admin,
                                 is_active=u.is_active, created_at=u.created_at) for u in recent],
    }


@router.get("/users", response_model=list[UserOut])
def list_users(admin=Depends(require_super_admin), db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.created_at.desc()).all()
    return [UserOut(id=u.id, email=u.email, is_super_admin=u.is_super_admin,
                    is_active=u.is_active, created_at=u.created_at) for u in rows]


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: AdminUserUpdate, admin=Depends(require_super_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own admin status or active status.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.is_super_admin is not None:
        user.is_super_admin = payload.is_super_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, email=user.email, is_super_admin=user.is_super_admin,
                   is_active=user.is_active, created_at=user.created_at)


@router.get("/subscriptions")
def list_subscriptions(admin=Depends(require_super_admin), db: Session = Depends(get_db)):
    rows = db.query(Subscription).all()
    out = []
    for s in rows:
        ws = db.query(Workspace).filter(Workspace.id == s.workspace_id).first()
        out.append({
            "workspace_id": s.workspace_id,
            "workspace_name": ws.name if ws else "",
            "owner_id": ws.owner_id if ws else "",
            "plan": s.plan, "status": s.status,
            "monthly_message_limit": s.monthly_message_limit, "agent_limit": s.agent_limit,
            "document_limit": s.document_limit, "messages_used_this_month": s.messages_used_this_month,
        })
    return out


@router.patch("/workspaces/{workspace_id}/subscription")
def update_workspace_subscription(workspace_id: str, payload: AdminSubscriptionUpdate,
                                  admin=Depends(require_super_admin), db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    sub = ensure_free_subscription(db, ws.id)
    if payload.plan is not None:
        if payload.plan not in PLANS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown plan '{payload.plan}'.")
        apply_plan(sub, payload.plan)
    if payload.status is not None:
        sub.status = payload.status
    if payload.monthly_message_limit is not None:
        sub.monthly_message_limit = payload.monthly_message_limit
    if payload.agent_limit is not None:
        sub.agent_limit = payload.agent_limit
    if payload.document_limit is not None:
        sub.document_limit = payload.document_limit
    db.commit()
    db.refresh(sub)
    return {"workspace_id": ws.id, "plan": sub.plan, "status": sub.status,
            "monthly_message_limit": sub.monthly_message_limit, "agent_limit": sub.agent_limit,
            "document_limit": sub.document_limit, "messages_used_this_month": sub.messages_used_this_month}
