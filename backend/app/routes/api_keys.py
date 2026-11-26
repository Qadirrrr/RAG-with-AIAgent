"""Agent API keys for the website widget and REST API.

Authentication uses only the SHA256 hash of the key. A Fernet-encrypted
copy is also stored so the workspace owner can view and copy the key
later from the Integrations page (see the reveal endpoint below and
app/services/key_vault.py). List responses never include the full key.
"""
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Agent, ApiKey, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import ApiKeyCreate, ApiKeyCreatedOut, ApiKeyOut
from app.routes.agents import _get_agent_or_404
from app.services.key_vault import decrypt_key, encrypt_key

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
                    key_encrypted=encrypt_key(raw_key),
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


@router.get("/{workspace_id}/agents/{agent_id}/api-keys/{key_id}/reveal")
def reveal_api_key(workspace_id: str, agent_id: str, key_id: str,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the full key to its owner so it can be viewed and copied.

    Owner-only: the same workspace and agent ownership checks as the
    list and delete endpoints apply. Keys created before encrypted
    storage existed have nothing to reveal.
    """
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = _get_agent_or_404(agent_id, ws.id, db)
    record = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.agent_id == agent.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    raw_key = decrypt_key(record.key_encrypted)
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This key was created before key viewing was enabled. Create a new key to view and copy it.")
    return {"api_key": raw_key}


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
