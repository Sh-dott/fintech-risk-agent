"""
Pydantic models for Risk Decision Engine API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


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
