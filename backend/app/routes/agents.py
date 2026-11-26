"""Agent CRUD inside a workspace. Enforces provider/model combos and plan limits."""
import os
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, UsageEvent, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import AgentCreate, AgentOut, AgentUpdate
from app.services.agent_engine import ALL_TOOL_NAMES
from app.services.rag_agent import is_model_allowed

router = APIRouter(prefix="/api/workspaces", tags=["agents"])


def _agent_out(a: Agent) -> AgentOut:
    return AgentOut(id=a.id, workspace_id=a.workspace_id, name=a.name, instructions=a.instructions or "",
                    language=a.language, provider=a.provider, model=a.model,
                    temperature=a.temperature, greeting=a.greeting or "",
                    description=a.description or "", is_active=bool(a.is_active),
                    mode=a.mode or "rag", show_citations=bool(a.show_citations),
                    tools_enabled=a.tools_enabled or "",
                    widget_title=a.widget_title or "",
                    widget_welcome_message=a.widget_welcome_message or "Hello! How can I help you?",
                    widget_color=a.widget_color or "#0F766E",
                    widget_position=a.widget_position or "right",
                    widget_icon=a.widget_icon or "chat",
                    widget_icon_url=a.widget_icon_url or "",
                    created_at=a.created_at)


def _validate_provider_model(provider: str, model: str):
    if provider != "ollama":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Provider '{provider}' is not supported. This platform is "
                                   "self-hosted only: use provider 'ollama'.")
    if not is_model_allowed(provider, model):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Model '{model}' is not available for provider 'ollama'. "
                                   "Use a Qwen model tag, for example 'qwen2.5:7b'.")


def _validate_mode(mode: str):
    if mode not in ("rag", "agent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Mode must be 'rag' (strict RAG) or 'agent' (RAG + Agent).")


_WIDGET_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
WIDGET_POSITIONS = ("right", "left")
WIDGET_ICONS = ("chat", "robot", "custom")


def _validate_widget_settings(color: str, position: str, icon: str):
    if not _WIDGET_COLOR_RE.match(color or ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Widget color must be a hex color like #0F766E.")
    if position not in WIDGET_POSITIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Widget position must be 'right' or 'left'.")
    if icon not in WIDGET_ICONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Widget icon must be 'chat', 'robot' or 'custom'.")


def _validate_tools_enabled(raw: str):
    names = [p.strip() for p in (raw or "").split(",") if p.strip()]
    unknown = [n for n in names if n not in ALL_TOOL_NAMES]
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown tool(s): {', '.join(unknown)}. "
                                   f"Available tools: {', '.join(ALL_TOOL_NAMES)}.")


def _get_agent_or_404(agent_id: str, workspace_id: str, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.workspace_id == workspace_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return agent


@router.post("/{workspace_id}/agents", response_model=AgentOut)
def create_agent(workspace_id: str, payload: AgentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    _validate_provider_model(payload.provider, payload.model)
    _validate_mode(payload.mode or "rag")
    _validate_tools_enabled(payload.tools_enabled or "")
    _validate_widget_settings(payload.widget_color, payload.widget_position, payload.widget_icon)
    sub = ensure_free_subscription(db, ws.id)
    # Single-tenant self-hosted: no agent count limits enforced.
    agent = Agent(workspace_id=ws.id, name=payload.name.strip(), instructions=payload.instructions or "",
                  language=payload.language or "en", provider=payload.provider, model=payload.model,
                  temperature=payload.temperature, greeting=payload.greeting or "",
                  description=payload.description or "", is_active=bool(payload.is_active),
                  mode=payload.mode or "rag", show_citations=bool(payload.show_citations),
                  tools_enabled=payload.tools_enabled or "",
                  widget_title=(payload.widget_title or "").strip(),
                  widget_welcome_message=payload.widget_welcome_message or "Hello! How can I help you?",
                  widget_color=payload.widget_color, widget_position=payload.widget_position,
                  widget_icon=payload.widget_icon,
                  widget_icon_url=(payload.widget_icon_url or "").strip())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.get("/{workspace_id}/agents", response_model=list[AgentOut])
def list_agents(workspace_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    return [_agent_out(a) for a in db.query(Agent).filter(Agent.workspace_id == ws.id).all()]


@router.get("/{workspace_id}/agents/{agent_id}", response_model=AgentOut)
def get_agent(workspace_id: str, agent_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    return _agent_out(_get_agent_or_404(agent_id, ws.id, db))


@router.patch("/{workspace_id}/agents/{agent_id}", response_model=AgentOut)
def update_agent(workspace_id: str, agent_id: str, payload: AgentUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    provider = payload.provider if payload.provider is not None else agent.provider
    model = payload.model if payload.model is not None else agent.model
    _validate_provider_model(provider, model)
    if payload.mode is not None:
        _validate_mode(payload.mode)
    if payload.tools_enabled is not None:
        _validate_tools_enabled(payload.tools_enabled)
    _validate_widget_settings(
        payload.widget_color if payload.widget_color is not None else (agent.widget_color or "#0F766E"),
        payload.widget_position if payload.widget_position is not None else (agent.widget_position or "right"),
        payload.widget_icon if payload.widget_icon is not None else (agent.widget_icon or "chat"))
    for field in ("name", "instructions", "language", "provider", "model", "temperature", "greeting",
                  "description", "is_active", "mode", "show_citations", "tools_enabled",
                  "widget_title", "widget_welcome_message", "widget_color", "widget_position",
                  "widget_icon", "widget_icon_url"):
        value = getattr(payload, field)
        if value is not None:
            setattr(agent, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.post("/{workspace_id}/agents/{agent_id}/toggle-active", response_model=AgentOut)
def toggle_agent_active(workspace_id: str, agent_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    agent.is_active = not bool(agent.is_active)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.delete("/{workspace_id}/agents/{agent_id}")
def delete_agent(workspace_id: str, agent_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    # Best effort: remove the agent's private Chroma collection.
    try:
        from app.services.tenant_vector_store import tenant_vector_store
        tenant_vector_store.delete_agent_collection(agent.id)
    except Exception:
        pass
    # Best effort: remove this agent's uploaded files (same pattern as the
    # single-document delete in routes/knowledge.py).
    for doc in list(agent.documents):
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception:
                pass
    # Usage events carry an agent_id foreign key but are workspace-level
    # analytics rows; delete this agent's events explicitly in the same
    # transaction. Without this the delete fails with an FK constraint
    # violation (HTTP 500) for any chatbot that has ever been used.
    # The agent's documents, conversations (with messages) and API keys are
    # removed by the ORM delete-orphan cascades on the Agent relationships.
    db.query(UsageEvent).filter(UsageEvent.agent_id == agent.id).delete(synchronize_session=False)
    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted successfully", "id": agent_id}
