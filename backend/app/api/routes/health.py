"""
Health check endpoints for Risk Decision Engine API
"""

from fastapi import APIRouter
from datetime import datetime
from app.models.schemas import HealthResponse
from app.api.dependencies import metrics

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - verify API is running."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=True,
        uptime_seconds=metrics.get_uptime(),
        requests_total=metrics.total_requests
    )
