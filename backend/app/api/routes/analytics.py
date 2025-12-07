"""
Analytics and metrics endpoints for Risk Decision Engine API
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Optional

from backend.app.models.schemas import MetricsResponse
from backend.app.api.dependencies import metrics

router = APIRouter(tags=["Analytics"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get real-time metrics and KPIs."""
    return MetricsResponse(
        total_requests=metrics.total_requests,
        total_decisions=metrics.total_decisions,
        allow_count=metrics.allow_count,
        block_count=metrics.block_count,
        review_count=metrics.review_count,
        avg_risk_score=round(metrics.get_avg_risk_score(), 4),
        p95_latency_ms=round(metrics.get_p95_latency(), 2),
        approval_rate=round(metrics.get_approval_rate(), 2),
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/history")
async def get_transaction_history(
    limit: int = 100,
    user_id: Optional[str] = None,
    merchant_id: Optional[str] = None
):
    """Get transaction decision history with optional filters."""
    history = list(metrics.transaction_history.values())

    # Filter by user_id if provided
    if user_id:
        history = [h for h in history if h["user_id"] == user_id]

    # Filter by merchant_id if provided
    if merchant_id:
        history = [h for h in history if h["merchant_id"] == merchant_id]

    # Return limited results
    return {
        "total": len(history),
        "limit": limit,
        "transactions": history[-limit:] if history else []
    }


@router.get("/analytics")
async def get_analytics():
    """Get comprehensive analytics dashboard data."""
    total = metrics.total_decisions
    return {
        "summary": {
            "total_transactions": total,
            "total_allowed": metrics.allow_count,
            "total_blocked": metrics.block_count,
            "total_review": metrics.review_count,
            "approval_rate_percent": round(metrics.get_approval_rate(), 2),
            "block_rate_percent": round((metrics.block_count / total * 100) if total > 0 else 0, 2),
            "review_rate_percent": round((metrics.review_count / total * 100) if total > 0 else 0, 2)
        },
        "performance": {
            "avg_risk_score": round(metrics.get_avg_risk_score(), 4),
            "p95_latency_ms": round(metrics.get_p95_latency(), 2),
            "uptime_seconds": metrics.get_uptime(),
            "requests_per_minute": round((metrics.total_requests / (metrics.get_uptime() / 60)) if metrics.get_uptime() > 0 else 0, 2)
        },
        "timestamp": datetime.utcnow().isoformat()
    }
