from fastapi import APIRouter
from app.models.schemas import DashboardStats
from app.services.storage import storage_service

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("", response_model=DashboardStats)
async def get_dashboard_stats():
    stats = storage_service.get_stats()
    return DashboardStats(**stats)

