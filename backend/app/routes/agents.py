"""Agent CRUD inside a workspace. Enforces provider/model combos and plan limits."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import AgentCreate, AgentOut, AgentUpdate
from app.services.agent_engine import ALL_TOOL_NAMES
from app.services.rag_agent import ALLOWED_MODELS, is_model_allowed

router = APIRouter(prefix="/api/workspaces", tags=["agents"])


def _agent_out(a: Agent) -> AgentOut:
    return AgentOut(id=a.id, workspace_id=a.workspace_id, name=a.name, instructions=a.instructions or "",
                    language=a.language, provider=a.provider, model=a.model,
                    temperature=a.temperature, greeting=a.greeting or "",
                    description=a.description or "", is_active=bool(a.is_active),
                    mode=a.mode or "rag", show_citations=bool(a.show_citations),
                    tools_enabled=a.tools_enabled or "",
                    created_at=a.created_at)


def _validate_provider_model(provider: str, model: str):
    if provider not in ALLOWED_MODELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown provider '{provider}'. Use 'gemini', 'openai' or 'ollama'.")
    if not is_model_allowed(provider, model):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Model '{model}' is not available for provider '{provider}'. "
                                   f"Allowed: {', '.join(sorted(ALLOWED_MODELS[provider]))}.")


def _validate_mode(mode: str):
    if mode not in ("rag", "agent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Mode must be 'rag' (strict RAG) or 'agent' (RAG + Agent).")


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
    sub = ensure_free_subscription(db, ws.id)
    count = db.query(Agent).filter(Agent.workspace_id == ws.id).count()
    if count >= sub.agent_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Your {sub.plan} plan allows {sub.agent_limit} agent(s). Upgrade your plan to create more agents.")
    agent = Agent(workspace_id=ws.id, name=payload.name.strip(), instructions=payload.instructions or "",
                  language=payload.language or "en", provider=payload.provider, model=payload.model,
                  temperature=payload.temperature, greeting=payload.greeting or "",
                  description=payload.description or "", is_active=bool(payload.is_active),
                  mode=payload.mode or "rag", show_citations=bool(payload.show_citations),
                  tools_enabled=payload.tools_enabled or "")
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
    for field in ("name", "instructions", "language", "provider", "model", "temperature", "greeting",
                  "description", "is_active", "mode", "show_citations", "tools_enabled"):
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
    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted successfully", "id": agent_id}
