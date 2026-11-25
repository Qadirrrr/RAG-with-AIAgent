"""Tenant playground chat (JWT) and public widget/API chat (API key).

Both use the same RAG pipeline with the agent's own instructions,
language, provider and model, searching only that agent's collection.
"""
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import Agent, ApiKey, Conversation, Message, Subscription, UsageEvent, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import PublicChatRequest, TenantChatRequest, TenantChatResponse, WidgetConfigOut
from app.services.rag_agent import rag_agent_service

tenant_router = APIRouter(prefix="/api/workspaces", tags=["tenant-chat"])
public_router = APIRouter(prefix="/api/public", tags=["public-chat"])


def _agent_config(agent: Agent) -> dict:
    return {"name": agent.name, "instructions": agent.instructions or "", "language": agent.language,
            "provider": agent.provider, "model": agent.model, "temperature": agent.temperature,
            "greeting": agent.greeting or "", "mode": agent.mode or "rag",
            "show_citations": bool(agent.show_citations),
            "workspace_id": agent.workspace_id,
            "tools_enabled": agent.tools_enabled or ""}


def _require_active(agent: Agent):
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This chatbot is deactivated. Please activate it before chatting.")


def _check_message_limit(sub: Subscription):
    if sub.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Your subscription is not active. Please upgrade or contact support.")
    if sub.messages_used_this_month >= sub.monthly_message_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Monthly message limit reached ({sub.monthly_message_limit} messages on the {sub.plan} plan). Upgrade your plan to continue.")


def _record_usage(db: Session, workspace_id: str, agent_id: str, sub: Subscription):
    db.add(UsageEvent(workspace_id=workspace_id, agent_id=agent_id, kind="chat", tokens_or_count=1))
    sub.messages_used_this_month = (sub.messages_used_this_month or 0) + 1
    db.commit()


async def _run_chat(db: Session, agent: Agent, workspace_id: str, sub: Subscription,
                    message: str, conversation_id, channel: str) -> TenantChatResponse:
    if not message or not message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")
    _require_active(agent)
    _check_message_limit(sub)
    conversation = None
    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id, Conversation.agent_id == agent.id).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if conversation is None:
        conversation = Conversation(agent_id=agent.id, workspace_id=workspace_id,
                                    title=message.strip()[:60], channel=channel)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    db.add(Message(conversation_id=conversation.id, role="user", content=message.strip()))
    db.commit()

    history_rows = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    # history_rows already includes the new user message as last; pass earlier turns only.
    history = [{"role": m.role, "content": m.content} for m in history_rows[:-1]][-6:]

    result = await rag_agent_service.answer_question(
        question=message.strip(), history=history, agent_config=_agent_config(agent), agent_id=agent.id)

    sources = result.sources if agent.show_citations else []
    stored = json.dumps([s.model_dump(mode="json") for s in sources]) if sources else "[]"
    db.add(Message(conversation_id=conversation.id, role="assistant", content=result.response,
                   sources=stored))
    db.commit()
    _record_usage(db, workspace_id, agent.id, sub)
    return TenantChatResponse(conversation_id=conversation.id, response=result.response,
                              sources=sources, agent_steps=[])


@tenant_router.post("/{workspace_id}/agents/{agent_id}/chat", response_model=TenantChatResponse)
async def tenant_chat(workspace_id: str, agent_id: str, payload: TenantChatRequest,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.workspace_id == ws.id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    sub = ensure_free_subscription(db, ws.id)
    return await _run_chat(db, agent, ws.id, sub, payload.message, payload.conversation_id, payload.channel or "playground")


def _api_key_or_401(db: Session, request: Request) -> ApiKey:
    """Resolve the X-Agent-Key header (or ?key=) to an active ApiKey row."""
    provided = request.headers.get("X-Agent-Key") or request.query_params.get("key") or ""
    if not provided:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing API key. Send it as the X-Agent-Key header or ?key= query parameter.")
    key_hash = hashlib.sha256(provided.encode("utf-8")).hexdigest()
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    return api_key


@public_router.get("/widget-config", response_model=WidgetConfigOut)
def widget_config(request: Request, db: Session = Depends(get_db)):
    """Appearance config for the embeddable widget, keyed like public chat.

    Returns appearance only (title, welcome message, color, position, icon)
    so the widget can style itself per chatbot. No instructions, documents
    or other agent internals are exposed.
    """
    api_key = _api_key_or_401(db, request)
    agent = db.query(Agent).filter(Agent.id == api_key.agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    _require_active(agent)
    icon = agent.widget_icon or "chat"
    icon_url = agent.widget_icon_url or ""
    if icon == "custom" and not icon_url:
        icon = "chat"
    return WidgetConfigOut(
        title=(agent.widget_title or "").strip() or agent.name,
        welcome_message=agent.widget_welcome_message or "Hello! How can I help you?",
        color=agent.widget_color or "#0F766E",
        position=agent.widget_position or "right",
        icon=icon,
        icon_url=icon_url,
        agent_name=agent.name)


@public_router.post("/chat", response_model=TenantChatResponse)
async def public_chat(payload: PublicChatRequest, request: Request, db: Session = Depends(get_db)):
    api_key = _api_key_or_401(db, request)
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent or agent.id != api_key.agent_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key does not match this agent.")
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    sub = ensure_free_subscription(db, agent.workspace_id)
    return await _run_chat(db, agent, agent.workspace_id, sub, payload.message,
                           payload.conversation_id, payload.channel or "widget")
