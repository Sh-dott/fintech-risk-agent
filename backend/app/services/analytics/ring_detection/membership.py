"""
Per-account membership scoring and trimming for fraud rings.

Assigns roles (CORE / SUSPECTED / PERIPHERAL) based on multi-dimensional
evidence and trims weakly connected accounts to reduce false positives.
"""

import numpy as np
from typing import Dict

from .schemas import MembershipRole, MemberEvidence


class MembershipScorer:
    """Scores and trims ring membership based on multi-dimensional evidence."""

    def __init__(
        self,
        core_affinity: float = 0.55,
        core_min_types: int = 3,
        suspected_affinity: float = 0.35,
        suspected_min_types: int = 2,
        min_core_members: int = 3,
        trim_min_evidence_types: int = 2,
    ):
        self.core_affinity = core_affinity
        self.core_min_types = core_min_types
        self.suspected_affinity = suspected_affinity
        self.suspected_min_types = suspected_min_types
        self.min_core_members = min_core_members
        self.trim_min_evidence_types = trim_min_evidence_types

    def score_and_assign_roles(
        self, member_evidence: Dict[str, MemberEvidence],
    ) -> Dict[str, MemberEvidence]:
        """Assign CORE / SUSPECTED / PERIPHERAL based on affinity + evidence diversity."""
        for me in member_evidence.values():
            if (me.affinity_score >= self.core_affinity
                    and me.evidence_type_count >= self.core_min_types):
                me.role = MembershipRole.CORE.value
            elif (me.affinity_score >= self.suspected_affinity
                    and me.evidence_type_count >= self.suspected_min_types):
                me.role = MembershipRole.SUSPECTED.value
            else:
                me.role = MembershipRole.PERIPHERAL.value
        return member_evidence

    def trim_weak_members(
        self, member_evidence: Dict[str, MemberEvidence],
    ) -> Dict[str, MemberEvidence]:
        """
        Mark PERIPHERAL members with insufficient evidence as trimmed.
        Safety: keep at least min_core_members to form a valid ring.
        """
        core_count = sum(
            1 for me in member_evidence.values()
            if me.role == MembershipRole.CORE.value
        )

        # Don't trim if the ring is already small
        if core_count < self.min_core_members:
            return member_evidence

        for me in member_evidence.values():
            if me.role == MembershipRole.PERIPHERAL.value:
                if me.evidence_type_count < self.trim_min_evidence_types:
                    me.is_trimmed = True

        # Safety check: make sure we keep enough members
        active = sum(1 for me in member_evidence.values() if not me.is_trimmed)
        if active < self.min_core_members:
            # Undo trimming
            for me in member_evidence.values():
                me.is_trimmed = False

        return member_evidence

    @staticmethod
    def compute_ring_cohesion(
        member_evidence: Dict[str, MemberEvidence],
    ) -> float:
        """Mean affinity of non-trimmed members."""
        active = [me for me in member_evidence.values() if not me.is_trimmed]
        if not active:
            return 0.0
        return float(np.mean([me.affinity_score for me in active]))

    @staticmethod
    def membership_summary(
        member_evidence: Dict[str, MemberEvidence],
    ) -> Dict[str, int]:
        """Count members by role (excluding trimmed)."""
        counts = {"core": 0, "suspected": 0, "peripheral": 0, "trimmed": 0}
        for me in member_evidence.values():
            if me.is_trimmed:
                counts["trimmed"] += 1
            else:
                counts[me.role] += 1
        return counts
