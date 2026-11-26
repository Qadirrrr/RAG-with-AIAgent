import httpx
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api/health", tags=["health"])


def _ollama_reachable() -> bool:
    try:
        resp = httpx.get(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


@router.get("")
async def health_check():
    reachable = _ollama_reachable()
    return {
        "status": "healthy",
        "ollama_reachable": reachable,
        "model": settings.OLLAMA_MODEL,
        "embedding_model": settings.BGE_EMBEDDING_MODEL,
    }
