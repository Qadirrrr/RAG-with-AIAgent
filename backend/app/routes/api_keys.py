"""Agent API keys for the website widget and REST API.

The full key is shown only once, at creation. Only its SHA256 hash
is stored; later calls show only the prefix.
"""
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, ApiKey, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import ApiKeyCreate, ApiKeyCreatedOut, ApiKeyOut
from app.routes.agents import _get_agent_or_404

router = APIRouter(prefix="/api/workspaces", tags=["api-keys"])


def _key_out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(id=k.id, workspace_id=k.workspace_id, agent_id=k.agent_id, prefix=k.prefix,
                     name=k.name, last_used_at=k.last_used_at, is_active=k.is_active, created_at=k.created_at)


@router.post("/{workspace_id}/agents/{agent_id}/api-keys", response_model=ApiKeyCreatedOut)
def create_api_key(workspace_id: str, agent_id: str, payload: ApiKeyCreate,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    raw_key = "sk-live-" + secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    record = ApiKey(workspace_id=ws.id, agent_id=agent.id, key_hash=key_hash,
                    prefix=raw_key[:15], name=payload.name or "Default")
    db.add(record)
    db.commit()
    db.refresh(record)
    out = _key_out(record)
    return ApiKeyCreatedOut(**out.model_dump(), api_key=raw_key)


@router.get("/{workspace_id}/agents/{agent_id}/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(workspace_id: str, agent_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    rows = db.query(ApiKey).filter(ApiKey.agent_id == agent.id).order_by(ApiKey.created_at.desc()).all()
    return [_key_out(k) for k in rows]


@router.delete("/{workspace_id}/agents/{agent_id}/api-keys/{key_id}")
def delete_api_key(workspace_id: str, agent_id: str, key_id: str,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    record = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.agent_id == agent.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    db.delete(record)
    db.commit()
    return {"message": "API key deleted successfully", "id": key_id}
