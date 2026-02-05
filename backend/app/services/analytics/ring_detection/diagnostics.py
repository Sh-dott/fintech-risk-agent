"""
Self-validation diagnostics for the fraud ring detection pipeline.

Detects unrealistic outputs, internal inconsistencies, and
evidence-to-flagging ratio problems before results are returned.
"""

import numpy as np
from typing import List, Dict
from collections import defaultdict

from .schemas import ConfirmedRing, CandidateCluster, DiagnosticReport


class PipelineDiagnostics:
    """Self-validation checks for pipeline output health."""

    MAX_RINGS_EXPECTED = 30
    MAX_RING_SIZE_PCT = 0.10
    MIN_EVIDENCE_PER_MEMBER = 1.0
    MAX_FLAGGING_RATE = 0.20
    MIN_CORE_RATIO = 0.10

    def __init__(self, total_users: int, total_transactions: int):
        self.total_users = total_users
        self.total_transactions = total_transactions

    def run_diagnostics(
        self,
        confirmed_rings: List[ConfirmedRing],
        phase1_candidates: List[CandidateCluster],
    ) -> DiagnosticReport:
        """Run all diagnostic checks and return a report."""
        report = DiagnosticReport()
        checks = [
            self._check_ring_count,
            self._check_ring_sizes,
            self._check_evidence_ratios,
            self._check_flagging_rate,
            self._check_core_ratios,
            self._check_severity_distribution,
            self._check_discovery_to_confirmation,
            self._check_member_overlap,
        ]
        for check in checks:
            check(confirmed_rings, phase1_candidates, report)

        report.is_healthy = report.checks_failed == 0 and len(report.errors) == 0
        return report

    def _check_ring_count(self, rings, candidates, report):
        if len(rings) > self.MAX_RINGS_EXPECTED:
            report.warnings.append(
                f"High ring count: {len(rings)} > {self.MAX_RINGS_EXPECTED}. "
                f"Consider stricter confirmation thresholds."
            )
            report.checks_failed += 1
        else:
            report.checks_passed += 1
        report.metrics["ring_count"] = len(rings)

    def _check_ring_sizes(self, rings, candidates, report):
        for ring in rings:
            pct = ring.member_count / max(self.total_users, 1)
            if pct > self.MAX_RING_SIZE_PCT:
                report.errors.append(
                    f"Ring {ring.ring_id} has {ring.member_count} members "
                    f"({pct:.1%} of all users). Likely over-expanded."
                )
                report.checks_failed += 1
                return
        report.checks_passed += 1

    def _check_evidence_ratios(self, rings, candidates, report):
        all_counts = []
        for ring in rings:
            for me in ring.members:
                if not me.is_trimmed:
                    all_counts.append(len(me.evidence_items))
        if all_counts:
            avg = float(np.mean(all_counts))
            report.metrics["avg_evidence_per_member"] = round(avg, 2)
            if avg < self.MIN_EVIDENCE_PER_MEMBER:
                report.warnings.append(
                    f"Low evidence density: avg {avg:.1f} items/member "
                    f"(threshold: {self.MIN_EVIDENCE_PER_MEMBER})"
                )
                report.checks_failed += 1
            else:
                report.checks_passed += 1
        else:
            report.checks_passed += 1

    def _check_flagging_rate(self, rings, candidates, report):
        all_flagged = set()
        for ring in rings:
            for me in ring.members:
                if not me.is_trimmed:
                    all_flagged.add(me.user_id)
        rate = len(all_flagged) / max(self.total_users, 1)
        report.metrics["flagging_rate"] = round(rate, 4)
        report.metrics["flagged_accounts"] = len(all_flagged)
        if rate > self.MAX_FLAGGING_RATE:
            report.warnings.append(
                f"High flagging rate: {len(all_flagged)} users ({rate:.1%}). "
                f"Review confirmation thresholds."
            )
            report.checks_failed += 1
        else:
            report.checks_passed += 1

    def _check_core_ratios(self, rings, candidates, report):
        low_core = []
        for ring in rings:
            if ring.member_count > 0:
                core_ratio = ring.core_member_count / ring.member_count
                if core_ratio < self.MIN_CORE_RATIO:
                    low_core.append(
                        f"{ring.ring_id}: {ring.core_member_count}/{ring.member_count} core"
                    )
        if low_core:
            report.warnings.append(
                f"Low core ratio in {len(low_core)} ring(s): {', '.join(low_core[:3])}"
            )
        report.checks_passed += 1

    def _check_severity_distribution(self, rings, candidates, report):
        if rings and all(r.severity == "CRITICAL" for r in rings):
            report.warnings.append("All rings classified as CRITICAL. Check calibration.")
        report.checks_passed += 1

    def _check_discovery_to_confirmation(self, rings, candidates, report):
        if candidates:
            ratio = len(rings) / len(candidates)
            report.metrics["confirmation_rate"] = round(ratio, 3)
            if ratio < 0.05:
                report.warnings.append(
                    f"Only {ratio:.0%} of candidates confirmed. Discovery may be too noisy."
                )
            elif ratio > 0.9 and len(candidates) > 5:
                report.warnings.append(
                    f"{ratio:.0%} confirmed. Confirmation may be too permissive."
                )
        report.checks_passed += 1

    def _check_member_overlap(self, rings, candidates, report):
        user_ring_count: Dict[str, int] = defaultdict(int)
        for ring in rings:
            for me in ring.members:
                if not me.is_trimmed:
                    user_ring_count[me.user_id] += 1
        multi = sum(1 for c in user_ring_count.values() if c > 1)
        report.metrics["multi_ring_users"] = multi
        if user_ring_count and multi > 0.1 * len(user_ring_count):
            report.warnings.append(
                f"{multi} users appear in multiple rings. Check deduplication."
            )
        report.checks_passed += 1
