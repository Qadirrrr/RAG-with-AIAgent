"""Subscription plans and plan changes.

No real payment gateway is connected yet. POST /subscription is a
manual/admin upgrade path for the MVP; Stripe checkout is a TODO and
the response says so honestly.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import PLANS, Workspace, apply_plan, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import PlanOut, SubscriptionChangeRequest, SubscriptionOut

router = APIRouter(prefix="/api", tags=["plans"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans():
    return [PlanOut(id=pid, name=p["name"], price_usd=p["price_usd"],
                    monthly_message_limit=p["monthly_message_limit"], agent_limit=p["agent_limit"],
                    document_limit=p["document_limit"], description=p["description"])
            for pid, p in PLANS.items()]


@router.post("/workspaces/{workspace_id}/subscription")
def change_subscription(workspace_id: str, payload: SubscriptionChangeRequest,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    if payload.plan not in PLANS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown plan '{payload.plan}'. Available plans: {', '.join(PLANS)}.")
    sub = ensure_free_subscription(db, ws.id)
    apply_plan(sub, payload.plan)
    sub.status = "active"
    db.commit()
    db.refresh(sub)
    return {
        "subscription": SubscriptionOut(id=sub.id, workspace_id=sub.workspace_id, plan=sub.plan, status=sub.status,
                                        monthly_message_limit=sub.monthly_message_limit, agent_limit=sub.agent_limit,
                                        document_limit=sub.document_limit,
                                        messages_used_this_month=sub.messages_used_this_month),
        "note": "Stripe checkout is not connected yet (TODO). This is a manual upgrade path for the MVP; connect Stripe before charging real customers.",
    }
