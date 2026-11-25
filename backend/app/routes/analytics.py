"""Workspace analytics and conversation history."""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, Conversation, Document, Message, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import ConversationOut, MessageOut

router = APIRouter(prefix="/api/workspaces", tags=["analytics"])


@router.get("/{workspace_id}/analytics")
def get_analytics(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    sub = ensure_free_subscription(db, ws.id)
    # SQLite stores datetimes without tzinfo, so compare naive UTC here.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=14)
    conv_ids = [c.id for c in db.query(Conversation.id).filter(Conversation.workspace_id == ws.id).all()]
    messages = db.query(Message).filter(Message.conversation_id.in_(conv_ids)).all() if conv_ids else []

    per_day = Counter()
    for m in messages:
        if m.created_at and m.created_at >= since:
            per_day[m.created_at.date().isoformat()] += 1
    days = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date().isoformat()
        days.append({"date": day, "messages": per_day.get(day, 0)})

    conv_agent = {}
    for c in db.query(Conversation).filter(Conversation.workspace_id == ws.id).all():
        conv_agent[c.id] = c.agent_id
    per_agent = Counter()
    for m in messages:
        agent_id = conv_agent.get(m.conversation_id)
        if agent_id:
            per_agent[agent_id] += 1
    agents = {a.id: a.name for a in db.query(Agent).filter(Agent.workspace_id == ws.id).all()}
    per_agent_list = [{"agent_id": aid, "agent_name": agents.get(aid, aid), "messages": n}
                        for aid, n in per_agent.most_common()]

    top_questions = Counter(m.content for m in messages if m.role == "user").most_common(10)
    return {
        "messages_per_day_last_14d": days,
        "messages_per_agent": per_agent_list,
        "top_questions": [{"question": q, "count": n} for q, n in top_questions],
        "total_messages": len(messages),
        "total_conversations": len(conv_ids),
        "documents_count": db.query(Document).filter(Document.workspace_id == ws.id).count(),
        "agents_count": len(agents),
        "usage": {
            "plan": sub.plan,
            "status": sub.status,
            "messages_used_this_month": sub.messages_used_this_month,
            "monthly_message_limit": sub.monthly_message_limit,
            "agent_limit": sub.agent_limit,
            "document_limit": sub.document_limit,
        },
    }


@router.get("/{workspace_id}/conversations", response_model=list[ConversationOut])
def list_conversations(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    rows = db.query(Conversation).filter(Conversation.workspace_id == ws.id).order_by(Conversation.created_at.desc()).all()
    return [ConversationOut(id=c.id, agent_id=c.agent_id, workspace_id=c.workspace_id, title=c.title,
                            channel=c.channel, created_at=c.created_at, messages=[]) for c in rows]


@router.get("/{workspace_id}/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(workspace_id: str, conversation_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.workspace_id == ws.id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    msgs = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.asc()).all()
    out_msgs = []
    for m in msgs:
        try:
            sources = json.loads(m.sources or "[]")
        except Exception:
            sources = []
        out_msgs.append(MessageOut(id=m.id, role=m.role, content=m.content, sources=sources, created_at=m.created_at))
    return ConversationOut(id=conv.id, agent_id=conv.agent_id, workspace_id=conv.workspace_id, title=conv.title,
                           channel=conv.channel, created_at=conv.created_at, messages=out_msgs)
