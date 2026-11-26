"""Self-hosted Ollama server info for the dashboard (authenticated).

The model list comes from the Ollama server itself (GET /api/tags via
the cached helper in rag_agent), so the dashboard only ever offers
models that are actually pulled on the server.
"""
from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.services import rag_agent

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


def _is_embedding_model(name: str) -> bool:
    """True for the configured BGE embedding model (and its :latest tag)."""
    base = settings.BGE_EMBEDDING_MODEL
    return name == base or name == f"{base}:latest"


@router.get("/models")
def list_ollama_models(user=Depends(get_current_user)):
    """Chat models pulled on the Ollama server, plus the default model.

    Embedding-only models are excluded. When Ollama is unreachable the
    list is empty (still 200); the frontend then falls back to showing
    just the default model.
    """
    pulled = rag_agent._get_pulled_model_names()
    if pulled is None:
        return {"models": [], "default": settings.OLLAMA_MODEL}
    models = sorted(name for name in pulled if not _is_embedding_model(name))
    return {"models": models, "default": settings.OLLAMA_MODEL}
