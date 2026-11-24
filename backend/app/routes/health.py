import os
from fastapi import APIRouter
from app.config import settings
from app.models.schemas import HealthResponse
from app.services.vector_store import vector_store_service

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("", response_model=HealthResponse)
async def health_check():
    provider = settings.get_active_provider()
    api_configured = provider != "none"
    
    chroma_ok = vector_store_service.check_health()
    chroma_status = "connected" if chroma_ok else "unreachable"

    return HealthResponse(
        status="healthy",
        provider=provider,
        api_configured=api_configured,
        openai_configured=bool(settings.get_openai_api_key()),
        chroma_status=chroma_status,
        model=settings.get_active_model(),
        embedding_model=settings.get_active_embedding_model()
    )

