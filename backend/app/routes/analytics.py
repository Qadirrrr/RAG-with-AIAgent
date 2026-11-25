"""Workspace analytics and conversation history."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, Conversation, Document, Message, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import ConversationOut, MessageOut, TenantDocumentOut

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
        out_msgs.append(MessageOut(id=m.id, role=m.role, content=m.content, sources=[], created_at=m.created_at))
    return ConversationOut(id=conv.id, agent_id=conv.agent_id, workspace_id=conv.workspace_id, title=conv.title,
                           channel=conv.channel, created_at=conv.created_at, messages=out_msgs)


@router.get("/{workspace_id}/stats")
def get_workspace_stats(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Dashboard numbers scoped to one workspace only. A fresh workspace returns zeros."""
    ws = get_workspace_or_404(workspace_id, user, db)
    docs = db.query(Document).filter(Document.workspace_id == ws.id).all()
    convs = db.query(Conversation).filter(Conversation.workspace_id == ws.id).order_by(Conversation.created_at.desc()).all()
    conv_ids = [c.id for c in convs]
    total_messages = db.query(Message).filter(Message.conversation_id.in_(conv_ids)).count() if conv_ids else 0
    recent = []
    for c in convs[:5]:
        recent.append({"id": c.id, "type": "chat", "title": c.title or "Conversation",
                       "details": "", "timestamp": c.created_at.isoformat() if c.created_at else None})
    for d in sorted(docs, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]:
        recent.append({"id": d.id, "type": "upload", "title": d.filename,
                       "details": d.status, "timestamp": d.created_at.isoformat() if d.created_at else None})
    recent = sorted(recent, key=lambda x: x.get("timestamp") or "", reverse=True)[:5]
    return {
        "total_documents": len(docs),
        "processed_documents": sum(1 for d in docs if d.status == "processed"),
        "total_chunks": sum(d.chunks_count or 0 for d in docs),
        "total_questions_asked": total_messages,
        "total_conversations": len(convs),
        "agents_count": db.query(Agent).filter(Agent.workspace_id == ws.id).count(),
        "recent_activity": recent,
    }


@router.get("/{workspace_id}/documents", response_model=list[TenantDocumentOut])
def list_workspace_documents(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """All documents of one workspace, across its agents. Never the legacy global store."""
    ws = get_workspace_or_404(workspace_id, user, db)
    docs = db.query(Document).filter(Document.workspace_id == ws.id).order_by(Document.created_at.desc()).all()
    return [TenantDocumentOut(id=d.id, agent_id=d.agent_id, workspace_id=d.workspace_id, filename=d.filename,
                              file_type=d.file_type, file_size=d.file_size, status=d.status,
                              chunks_count=d.chunks_count, source_type=d.source_type, source_url=d.source_url,
                              error_message=d.error_message, created_at=d.created_at) for d in docs]
