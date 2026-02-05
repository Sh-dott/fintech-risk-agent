"""
Two-phase evidence-based fraud ring detection subpackage.

Phase 1: Discovery (graph, behavioral clustering, temporal co-occurrence)
Phase 2: Confirmation (evidence collection, membership scoring, gating)
"""

from .pipeline import RingDetectionPipeline
from .schemas import (
    PipelineOutput,
    ClassifiedRing,
    TransactionScore,
    RingCandidate,
    RingFeatureVector,
    TransactionFeatures,
    EvidenceType,
    MembershipRole,
    EvidenceItem,
    MemberEvidence,
    CandidateCluster,
    ConfirmedRing,
    DiagnosticReport,
)

__all__ = [
    "RingDetectionPipeline",
    "PipelineOutput",
    "ClassifiedRing",
    "TransactionScore",
    "RingCandidate",
    "RingFeatureVector",
    "TransactionFeatures",
    "EvidenceType",
    "MembershipRole",
    "EvidenceItem",
    "MemberEvidence",
    "CandidateCluster",
    "ConfirmedRing",
    "DiagnosticReport",
]
