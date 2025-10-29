"""
REST API for Risk Decision Engine

Exposes the decision engine via HTTP endpoints for real-time transaction scoring.
Deploy on cloud platforms (Heroku, AWS, Google Cloud, Azure, etc.)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import uvicorn
import time
import os
import tempfile
import shutil

from src.core.decision_engine import RiskDecisionEngine, DecisionType, RiskLevel
from src.analytics import AIInsightsEngine, FileProcessor, AdvancedFraudDetectionEngine


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
    uptime_seconds: float
    requests_total: int


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_requests: int
    total_decisions: int
    allow_count: int
    block_count: int
    review_count: int
    avg_risk_score: float
    p95_latency_ms: float
    approval_rate: float
    timestamp: str


class TransactionHistoryResponse(BaseModel):
    """Transaction history response."""
    transaction_id: str
    decision: str
    risk_score: float
    risk_level: str
    reason_codes: List[str]
    timestamp: str
    user_id: str
    merchant_id: str


class FileUploadResponse(BaseModel):
    """File upload and analysis response."""
    status: str
    file_name: str
    records_processed: int
    data_quality_score: float
    insights: List[Dict[str, Any]]
    summary: Dict[str, Any]


class InsightDetail(BaseModel):
    """Single insight detail."""
    title: str
    description: str
    severity: str
    impact: str
    recommendation: str
    metrics: Dict[str, Any]


class RiskProfileResponse(BaseModel):
    """Risk profile for an entity."""
    entity_id: str
    entity_type: str
    base_risk_score: float
    ml_risk_score: float
    behavioral_risk_score: float
    network_risk_score: float
    anomaly_score: float
    final_risk_score: float
    risk_level: str
    risk_factors: List[str]
    red_flags: List[str]
    confidence_score: float


class AdvancedAnalysisResponse(BaseModel):
    """Advanced fraud detection analysis response."""
    status: str
    file_name: str
    records_processed: int
    timestamp: str
    summary: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    fraud_networks: Dict[str, Any]
    money_laundering_patterns: List[Dict[str, Any]]
    risk_profiles: List[RiskProfileResponse]


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Risk Decision Engine API",
    description="Real-time transaction scoring & fraud detection for fintech payments",
    version="1.0.0",
    docs_url="/api-docs",  # Swagger UI (custom path)
    redoc_url="/api-redoc"  # ReDoc UI (custom path)
)

# Add CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize decision engine (lazy loaded to avoid startup delays)
engine = None

def get_engine():
    """Get or initialize the decision engine lazily."""
    global engine
    if engine is None:
        try:
            engine = RiskDecisionEngine(config_path="config/model_config.yaml")
        except Exception as e:
            print(f"[WARNING] Could not load RiskDecisionEngine: {e}")
            engine = None
    return engine

# Metrics tracking
class APIMetrics:
    def __init__(self):
        self.total_requests = 0
        self.total_decisions = 0
        self.allow_count = 0
        self.block_count = 0
        self.review_count = 0
        self.risk_scores = []
        self.latencies = []
        self.start_time = datetime.utcnow()
        self.transaction_history = {}

    def record_decision(self, decision_str: str, risk_score: float, latency: float):
        self.total_requests += 1
        self.total_decisions += 1
        self.risk_scores.append(risk_score)
        self.latencies.append(latency)

        if decision_str == "allow":
            self.allow_count += 1
        elif decision_str == "block":
            self.block_count += 1
        elif decision_str == "review":
            self.review_count += 1

    def get_uptime(self) -> float:
        return (datetime.utcnow() - self.start_time).total_seconds()

    def get_avg_risk_score(self) -> float:
        return sum(self.risk_scores) / len(self.risk_scores) if self.risk_scores else 0.0

    def get_p95_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    def get_approval_rate(self) -> float:
        total = self.total_decisions
        return (self.allow_count / total * 100) if total > 0 else 0.0

metrics = APIMetrics()


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
        models_loaded=True,
        uptime_seconds=metrics.get_uptime(),
        requests_total=metrics.total_requests
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


@app.get("/metrics", response_model=MetricsResponse, tags=["Analytics"])
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


@app.get("/history", tags=["Analytics"])
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


@app.get("/analytics", tags=["Analytics"])
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


@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    """Serve the modern fraud detection dashboard."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "modern_dashboard.html"),
        media_type="text/html"
    )


@app.get("/dashboard", tags=["Dashboard"], include_in_schema=False)
async def get_dashboard():
    """Get the modern interactive web dashboard."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "modern_dashboard.html"),
        media_type="text/html"
    )


@app.get("/classic", tags=["Dashboard"], include_in_schema=False)
async def get_classic_dashboard():
    """Get the classic dashboard."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "dashboard.html"),
        media_type="text/html"
    )


@app.get("/docs", tags=["Documentation"], include_in_schema=False)
async def get_docs():
    """Interactive API documentation (Swagger UI)."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "modern_dashboard.html"),
        media_type="text/html"
    )


@app.post("/upload-and-analyze", response_model=AdvancedAnalysisResponse, tags=["Advanced Analytics"])
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a transaction data file (CSV/JSON/Excel) and get world-class fraud detection analysis.

    Supported formats:
    - CSV (comma-separated values)
    - JSON (array of transactions)
    - JSONL (JSON Lines format)
    - Excel (XLSX/XLS)

    Returns comprehensive fraud detection including:
    - Multi-dimensional risk profiling
    - Anomaly detection (Isolation Forest + Local Outlier Factor)
    - Fraud network detection (graph analysis)
    - Money laundering pattern detection
    - Entity risk scoring (base + ML + behavioral + network + anomaly)
    - Detailed risk factors and red flags
    - Suspicious network clusters
    """
    temp_file_path = None

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            temp_file_path = tmp.name
            content = await file.read()
            tmp.write(content)

        # Process file
        transactions = FileProcessor.process_file(temp_file_path)

        # Validate data quality
        validation = FileProcessor.validate_transactions(transactions)

        if validation["data_quality_score"] < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Data quality too low: {validation['data_quality_score']:.1f}%"
            )

        # Initialize advanced fraud detection engine
        fraud_engine = AdvancedFraudDetectionEngine()
        fraud_engine.load_transactions(transactions)

        # Run all detection analyses
        anomalies = fraud_engine.detect_anomalies()
        fraud_networks = fraud_engine.detect_fraud_networks()
        ml_patterns = fraud_engine.detect_money_laundering_patterns()
        risk_profiles = fraud_engine.calculate_comprehensive_risk_scores()

        # Generate comprehensive report
        report = fraud_engine.generate_comprehensive_report()

        # Convert risk profiles to response format
        risk_profile_responses = [
            RiskProfileResponse(
                entity_id=profile.entity_id,
                entity_type=profile.entity_type,
                base_risk_score=profile.base_risk_score,
                ml_risk_score=profile.ml_risk_score,
                behavioral_risk_score=profile.behavioral_risk_score,
                network_risk_score=profile.network_risk_score,
                anomaly_score=profile.anomaly_score,
                final_risk_score=profile.final_risk_score,
                risk_level=profile.risk_level,
                risk_factors=profile.risk_factors,
                red_flags=profile.red_flags,
                confidence_score=profile.confidence_score
            )
            for profile in risk_profiles.values()
        ]

        return AdvancedAnalysisResponse(
            status="success",
            file_name=file.filename,
            records_processed=validation["valid_records"],
            timestamp=datetime.utcnow().isoformat(),
            summary=report["summary"],
            anomalies=anomalies,
            fraud_networks=fraud_networks,
            money_laundering_patterns=ml_patterns,
            risk_profiles=risk_profile_responses
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/analyze-transactions", response_model=AdvancedAnalysisResponse, tags=["Advanced Analytics"])
async def analyze_transactions(transactions: List[Dict[str, Any]]):
    """
    Analyze a list of transactions (JSON) with world-class fraud detection.

    Provides:
    - Multi-dimensional risk profiling
    - Anomaly detection (Isolation Forest + Local Outlier Factor)
    - Fraud network detection (graph analysis)
    - Money laundering pattern detection
    - Entity risk scoring (base + ML + behavioral + network + anomaly)
    - Detailed risk factors and red flags
    - Comprehensive fraud intelligence
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        # Initialize advanced fraud detection engine
        fraud_engine = AdvancedFraudDetectionEngine()
        fraud_engine.load_transactions(transactions)

        # Run all detection analyses
        anomalies = fraud_engine.detect_anomalies()
        fraud_networks = fraud_engine.detect_fraud_networks()
        ml_patterns = fraud_engine.detect_money_laundering_patterns()
        risk_profiles = fraud_engine.calculate_comprehensive_risk_scores()

        # Generate comprehensive report
        report = fraud_engine.generate_comprehensive_report()

        # Convert risk profiles to response format
        risk_profile_responses = [
            RiskProfileResponse(
                entity_id=profile.entity_id,
                entity_type=profile.entity_type,
                base_risk_score=profile.base_risk_score,
                ml_risk_score=profile.ml_risk_score,
                behavioral_risk_score=profile.behavioral_risk_score,
                network_risk_score=profile.network_risk_score,
                anomaly_score=profile.anomaly_score,
                final_risk_score=profile.final_risk_score,
                risk_level=profile.risk_level,
                risk_factors=profile.risk_factors,
                red_flags=profile.red_flags,
                confidence_score=profile.confidence_score
            )
            for profile in risk_profiles.values()
        ]

        return AdvancedAnalysisResponse(
            status="success",
            file_name="json_input",
            records_processed=len(transactions),
            timestamp=datetime.utcnow().isoformat(),
            summary=report["summary"],
            anomalies=anomalies,
            fraud_networks=fraud_networks,
            money_laundering_patterns=ml_patterns,
            risk_profiles=risk_profile_responses
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing transactions: {str(e)}")


# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print("[OK] Risk Decision Engine API started")
    print("[INFO] API Documentation: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("[STOP] Risk Decision Engine API stopped")


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


# ============================================================================
# Enhanced Dashboard Routes
# ============================================================================

@app.get("/enhanced", tags=["Dashboard"], include_in_schema=False)
async def get_enhanced_dashboard():
    """Get the ultra-modern enhanced analytics dashboard."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "enhanced_dashboard.html"),
        media_type="text/html"
    )


# ============================================================================
# Advanced Analytics Routes (Registered Below)
# ============================================================================

from src.api.advanced_analytics_routes import router as analytics_router
app.include_router(analytics_router)

