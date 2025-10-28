"""
REST API for Risk Decision Engine

Exposes the decision engine via HTTP endpoints for real-time transaction scoring.
Deploy on cloud platforms (Heroku, AWS, Google Cloud, Azure, etc.)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn

from src.core.decision_engine import RiskDecisionEngine, DecisionType, RiskLevel


# ============================================================================
# Request/Response Models
# ============================================================================

class TransactionRequest(BaseModel):
    """Request model for transaction scoring."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    merchant_id: str = Field(..., description="Merchant identifier")
    user_id: str = Field(..., description="User identifier")
    device_id: str = Field(..., description="Device identifier")
    ip_address: str = Field(..., description="IP address")
    user_country: str = Field(default="US", description="User country code")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp")


class DecisionResponse(BaseModel):
    """Response model for decision result."""
    decision: str = Field(..., description="allow/block/review")
    risk_score: float = Field(..., ge=0, le=1, description="Risk score 0-1")
    risk_level: str = Field(..., description="low/medium/high")
    reason_codes: List[str] = Field(..., description="Human-readable reason codes")
    next_actions: List[str] = Field(..., description="Recommended actions")
    compliance_log_id: str = Field(..., description="Audit trail reference")
    latency_ms: float = Field(..., description="Decision latency in milliseconds")
    explanation: str = Field(..., description="Researcher-friendly summary")
    timestamp: str = Field(..., description="Decision timestamp")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    models_loaded: bool


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Risk Decision Engine API",
    description="Real-time transaction scoring & fraud detection for fintech payments",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI
)

# Initialize decision engine
engine = RiskDecisionEngine(config_path="config/model_config.yaml")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint - verify API is running."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=True
    )


@app.post("/score", response_model=DecisionResponse, tags=["Scoring"])
async def score_transaction(request: TransactionRequest):
    """
    Score a transaction in real-time.

    Returns:
    - **decision**: allow/block/review
    - **risk_score**: 0.0-1.0 where 1.0 = highest risk
    - **reason_codes**: Explainable signals driving the decision
    - **next_actions**: Recommended escalations (SCA, manual review, etc.)
    - **compliance_log_id**: Reference for audit trail
    - **latency_ms**: Decision latency

    Example:
    ```json
    {
        "transaction_id": "txn_123",
        "amount": 100.00,
        "currency": "USD",
        "merchant_id": "mch_456",
        "user_id": "usr_789",
        "device_id": "dev_abc",
        "ip_address": "192.168.1.1",
        "user_country": "US"
    }
    ```
    """
    try:
        # Call decision engine
        decision = engine.score_transaction(
            transaction={
                "id": request.transaction_id,
                "amount": request.amount,
                "currency": request.currency,
                "merchant_id": request.merchant_id,
                "user_id": request.user_id
            },
            context={
                "device_id": request.device_id,
                "ip_address": request.ip_address,
                "user_country": request.user_country,
                "timestamp": request.timestamp or datetime.utcnow().isoformat()
            }
        )

        # Convert decision to response
        return DecisionResponse(
            decision=decision.decision.value,
            risk_score=decision.risk_score,
            risk_level=decision.risk_level.value,
            reason_codes=decision.reason_codes,
            next_actions=decision.next_actions,
            compliance_log_id=decision.compliance_log_id,
            latency_ms=decision.latency_ms,
            explanation=decision.explanation,
            timestamp=decision.timestamp
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Decision engine error: {str(e)}"
        )


@app.post("/batch-score", tags=["Scoring"])
async def batch_score_transactions(
    requests: List[TransactionRequest],
    background_tasks: BackgroundTasks
):
    """
    Score multiple transactions (batch processing).

    Returns list of decisions for bulk transaction processing.
    """
    try:
        decisions = []
        for req in requests:
            decision = engine.score_transaction(
                transaction={
                    "id": req.transaction_id,
                    "amount": req.amount,
                    "currency": req.currency,
                    "merchant_id": req.merchant_id,
                    "user_id": req.user_id
                },
                context={
                    "device_id": req.device_id,
                    "ip_address": req.ip_address,
                    "user_country": req.user_country,
                    "timestamp": req.timestamp or datetime.utcnow().isoformat()
                }
            )
            decisions.append({
                "transaction_id": req.transaction_id,
                "decision": decision.decision.value,
                "risk_score": decision.risk_score,
                "reason_codes": decision.reason_codes
            })

        return {
            "count": len(decisions),
            "timestamp": datetime.utcnow().isoformat(),
            "decisions": decisions
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing error: {str(e)}"
        )


@app.get("/docs", tags=["Documentation"])
async def get_docs():
    """Interactive API documentation (Swagger UI)."""
    return {"message": "Visit /docs for interactive documentation"}


# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print("✅ Risk Decision Engine API started")
    print("📚 API Documentation: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("🛑 Risk Decision Engine API stopped")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        reload=True  # Auto-reload on file changes (development only)
    )
