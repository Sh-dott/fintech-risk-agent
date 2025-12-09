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


class FraudRingResponse(BaseModel):
    """Response model for individual fraud ring detection."""
    ring_type: str = Field(..., description="Type of fraud ring (e.g., HIGH_VELOCITY, CROSS_BORDER)")
    ring_name: str = Field(..., description="Human-readable name of the fraud ring")
    severity: str = Field(..., description="Severity level: CRITICAL, HIGH, or MEDIUM")
    members: List[str] = Field(..., description="List of user IDs in the fraud ring")
    member_count: int = Field(..., description="Number of members in the ring")
    detection_method: str = Field(..., description="Method used to detect this ring")
    evidence: Dict[str, Any] = Field(..., description="Evidence supporting the detection")
    sample_transactions: List[Dict[str, Any]] = Field(..., description="Sample transactions from ring members")
    risk_score: float = Field(..., description="Risk score (0.0 to 1.0)")
    explanation: str = Field(..., description="Detailed explanation of the fraud pattern")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    network_data: Optional[Dict[str, Any]] = Field(default=None, description="Network graph data for visualization")


class FraudRingsReport(BaseModel):
    """Complete fraud rings detection report."""
    total_rings_detected: int = Field(..., description="Total number of fraud rings detected")
    critical_count: int = Field(..., description="Number of critical severity rings")
    high_count: int = Field(..., description="Number of high severity rings")
    medium_count: int = Field(..., description="Number of medium severity rings")
    rings: List[FraudRingResponse] = Field(default_factory=list, description="Detected fraud rings")
    overall_risk_level: str = Field(..., description="Overall risk level: CRITICAL, HIGH, MEDIUM, or LOW")
    executive_summary: str = Field(..., description="Executive summary of fraud ring detections")
    detection_timestamp: str = Field(..., description="Timestamp of detection")


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
    fraud_insights: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Fraud intelligence insights with explainable patterns"
    )
    fraud_rings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detected fraud rings with targeted detection methods"
    )
    organized_fraud: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Organized fraud rings (fake identity, email, geographic mismatches)"
    )
    data_driven_fraud_rings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data-driven fraud ring detection based on discovered patterns"
    )
