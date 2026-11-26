import httpx
from fastapi import APIRouter
from app.config import settings
from app.models.schemas import HealthResponse
from app.services.vector_store import vector_store_service

router = APIRouter(prefix="/api/health", tags=["health"])


def _ollama_reachable() -> bool:
    """Short-timeout check against the self-hosted Ollama server.

    Health must never fail just because Ollama is down, so any error
    simply reports ollama_reachable=False.
    """
    try:
        resp = httpx.get(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


@router.get("", response_model=HealthResponse)
async def health_check():
    reachable = _ollama_reachable()

    chroma_ok = vector_store_service.check_health()
    chroma_status = "connected" if chroma_ok else "unreachable"

    return HealthResponse(
        status="healthy",
        provider="ollama",
        ollama_reachable=reachable,
        api_configured=reachable,
        chroma_status=chroma_status,
        model=settings.OLLAMA_MODEL,
        embedding_model=settings.BGE_EMBEDDING_MODEL
    )
