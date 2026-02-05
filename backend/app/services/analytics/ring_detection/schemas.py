"""
Data contracts for the ring detection pipeline.

Uses dataclasses (not Pydantic) to match existing detector conventions.
Includes evidence framework, membership roles, and diagnostic types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvidenceType(str, Enum):
    """Six independent evidence dimensions for fraud confirmation."""
    INFRASTRUCTURE = "infrastructure"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    FINANCIAL_FLOW = "financial_flow"
    ACCOUNT_ANOMALY = "account_anomaly"
    MERCHANT_PATTERN = "merchant_pattern"


class MembershipRole(str, Enum):
    """Per-account role within a confirmed ring."""
    CORE = "core"
    SUSPECTED = "suspected"
    PERIPHERAL = "peripheral"


# ---------------------------------------------------------------------------
# Evidence & membership
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    """A single piece of evidence linking a user to a ring."""
    evidence_type: str = ""        # EvidenceType value
    dimension: str = ""            # e.g. "shared_device", "temporal_burst"
    strength: float = 0.0          # 0.0 - 1.0 normalised
    description: str = ""          # plain-language explanation
    raw_value: Any = None
    related_users: List[str] = field(default_factory=list)


@dataclass
class MemberEvidence:
    """All evidence for a single member's connection to a ring."""
    user_id: str = ""
    role: str = "peripheral"       # MembershipRole value
    affinity_score: float = 0.0    # composite 0-1
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    evidence_type_count: int = 0   # distinct EvidenceType dimensions
    is_trimmed: bool = False


# ---------------------------------------------------------------------------
# Discovery phase
# ---------------------------------------------------------------------------

@dataclass
class CandidateCluster:
    """Pre-confirmation cluster from any discovery method."""
    cluster_id: str = ""
    member_user_ids: List[str] = field(default_factory=list)
    size: int = 0
    discovery_method: str = ""     # "graph_louvain", "behavioral_hdbscan", "temporal"
    discovery_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Confirmation phase
# ---------------------------------------------------------------------------

@dataclass
class ConfirmedRing:
    """Post-confirmation ring with full evidence and membership detail."""
    ring_id: str = ""
    ring_label: str = ""
    ring_type: str = ""
    ring_name: str = ""
    confidence: float = 0.0
    severity: str = "MEDIUM"
    risk_score: float = 0.0
    # Membership with roles
    members: List[MemberEvidence] = field(default_factory=list)
    member_count: int = 0
    core_member_count: int = 0
    suspected_member_count: int = 0
    peripheral_member_count: int = 0
    # Evidence summary
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    evidence_type_count: int = 0
    primary_evidence_types: List[str] = field(default_factory=list)
    # Shared identifiers (backward compat)
    shared_identifiers: Dict[str, List[str]] = field(default_factory=dict)
    # Explainability
    risk_narrative: str = ""
    explanation: str = ""
    recommendations: List[str] = field(default_factory=list)
    # Discovery provenance
    discovery_methods: List[str] = field(default_factory=list)
    detection_method: str = ""
    # Frontend compat
    sample_transactions: List[Dict[str, Any]] = field(default_factory=list)
    network_data: Optional[Dict[str, Any]] = None

    def to_classified_ring(self) -> "ClassifiedRing":
        """Flatten to legacy ClassifiedRing for backward compatibility."""
        member_ids = [m.user_id for m in self.members if not m.is_trimmed]
        evidence = dict(self.evidence_summary)
        evidence["evidence_types"] = self.primary_evidence_types
        evidence["core_members"] = self.core_member_count
        evidence["suspected_members"] = self.suspected_member_count
        return ClassifiedRing(
            ring_id=self.ring_id,
            ring_label=self.ring_label,
            confidence=self.confidence,
            severity=self.severity,
            members=sorted(member_ids),
            member_count=len(member_ids),
            risk_score=self.risk_score,
            shared_identifiers=self.shared_identifiers,
            risk_narrative=self.risk_narrative,
            recommendations=self.recommendations,
            evidence=evidence,
            ring_type=self.ring_type,
            ring_name=self.ring_name,
            detection_method=self.detection_method,
            explanation=self.explanation,
            sample_transactions=self.sample_transactions,
            network_data=self.network_data,
        )


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticReport:
    """Self-validation report for pipeline output."""
    checks_passed: int = 0
    checks_failed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    is_healthy: bool = True


# ---------------------------------------------------------------------------
# Legacy / existing types (preserved for backward compatibility)
# ---------------------------------------------------------------------------

@dataclass
class TransactionFeatures:
    """Per-transaction feature vector."""
    transaction_id: str = ""
    user_id: str = ""
    ip_prefix_24: str = ""
    ip_prefix_16: str = ""
    email_domain: str = ""
    card_bin: str = ""
    micro_amount_ratio: float = 0.0
    threshold_amount_ratio: float = 0.0
    merchant_concentration_hhi: float = 0.0
    merchant_concentration_gini: float = 0.0
    bin_concentration: float = 0.0
    device_sharing_score: float = 0.0
    subnet_sharing_score_24: float = 0.0
    subnet_sharing_score_16: float = 0.0
    geo_mismatch_rate: float = 0.0
    burstiness_cv: float = 0.0
    burst_window_count: int = 0
    mean_inter_arrival_sec: float = 0.0


@dataclass
class RingCandidate:
    """Pre-classification ring detected by graph analysis."""
    ring_id: str = ""
    member_user_ids: List[str] = field(default_factory=list)
    size: int = 0
    density: float = 0.0
    shared_devices: List[str] = field(default_factory=list)
    shared_ip_prefixes: List[str] = field(default_factory=list)
    shared_bins: List[str] = field(default_factory=list)
    shared_merchants: List[str] = field(default_factory=list)
    shared_email_domains: List[str] = field(default_factory=list)
    detection_method: str = ""


@dataclass
class RingFeatureVector:
    """Aggregated ring features for classifier input."""
    ring_id: str = ""
    size: int = 0
    density: float = 0.0
    mean_micro_amount_ratio: float = 0.0
    mean_threshold_amount_ratio: float = 0.0
    mean_merchant_hhi: float = 0.0
    mean_merchant_gini: float = 0.0
    mean_bin_concentration: float = 0.0
    mean_device_sharing: float = 0.0
    mean_subnet_sharing_24: float = 0.0
    mean_subnet_sharing_16: float = 0.0
    mean_geo_mismatch_rate: float = 0.0
    mean_burstiness_cv: float = 0.0
    mean_burst_window_count: float = 0.0
    mean_inter_arrival_sec: float = 0.0
    mean_txn_count: float = 0.0
    mean_amount_mean: float = 0.0
    mean_amount_std: float = 0.0
    mean_amount_max: float = 0.0
    shared_device_count: int = 0
    shared_ip_prefix_count: int = 0
    shared_bin_count: int = 0
    shared_merchant_count: int = 0
    shared_email_domain_count: int = 0


@dataclass
class ClassifiedRing:
    """Final ring output after ML classification."""
    ring_id: str = ""
    ring_label: str = ""
    confidence: float = 0.0
    severity: str = "MEDIUM"
    members: List[str] = field(default_factory=list)
    member_count: int = 0
    risk_score: float = 0.0
    shared_identifiers: Dict[str, List[str]] = field(default_factory=dict)
    risk_narrative: str = ""
    recommendations: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    ring_type: str = ""
    ring_name: str = ""
    detection_method: str = ""
    explanation: str = ""
    sample_transactions: List[Dict[str, Any]] = field(default_factory=list)
    network_data: Optional[Dict[str, Any]] = None


@dataclass
class TransactionScore:
    """Per-transaction risk output."""
    transaction_id: str = ""
    user_id: str = ""
    risk_score: float = 0.0  # 0-100
    label: str = ""
    confidence: float = 0.0
    ring_id: str = ""
    explanations: List[str] = field(default_factory=list)


@dataclass
class PipelineOutput:
    """Top-level output matching frontend contract."""
    total_rings_detected: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    rings: List[ClassifiedRing] = field(default_factory=list)
    overall_risk_level: str = "LOW"
    executive_summary: str = ""
    detection_timestamp: str = ""
    transaction_scores: List[TransactionScore] = field(default_factory=list)
    # v2 fields
    diagnostics: Optional[DiagnosticReport] = None
    phase1_candidate_count: int = 0
    phase2_confirmed_count: int = 0
