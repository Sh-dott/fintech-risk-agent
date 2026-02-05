"""
Transaction scoring endpoints for Risk Decision Engine API
"""

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import time

from ...models.schemas import TransactionRequest, DecisionResponse
from ..dependencies import get_engine, metrics

router = APIRouter(tags=["Scoring"])


@router.post("/score", response_model=DecisionResponse)
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
        start_time = time.time()

        # Get decision engine
        decision_engine = get_engine()
        if not decision_engine:
            raise HTTPException(status_code=503, detail="Decision engine not available")

        # Call decision engine
        decision = decision_engine.score_transaction(
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

        # Record metrics
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        metrics.record_decision(decision.decision.value, decision.risk_score, elapsed)

        # Store in history
        metrics.transaction_history[request.transaction_id] = {
            "transaction_id": request.transaction_id,
            "decision": decision.decision.value,
            "risk_score": decision.risk_score,
            "risk_level": decision.risk_level.value,
            "reason_codes": decision.reason_codes,
            "timestamp": decision.timestamp,
            "user_id": request.user_id,
            "merchant_id": request.merchant_id
        }

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


@router.post("/batch-score")
async def batch_score_transactions(requests: List[TransactionRequest]):
    """
    Score multiple transactions (batch processing).

    Returns list of decisions for bulk transaction processing.
    """
    try:
        decision_engine = get_engine()
        if not decision_engine:
            raise HTTPException(status_code=503, detail="Decision engine not available")

        decisions = []
        for req in requests:
            decision = decision_engine.score_transaction(
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
