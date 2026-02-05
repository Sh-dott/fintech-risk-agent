"""
Multi-dimensional evidence collection for fraud ring confirmation.

Collects evidence across 6 independent dimensions for each member
of a candidate cluster: infrastructure, behavioral, temporal,
financial flow, account anomaly, and merchant pattern.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Set, Any
from collections import defaultdict

from .schemas import (
    EvidenceType, EvidenceItem, MemberEvidence, CandidateCluster,
)


class EvidenceCollector:
    """Collects multi-dimensional evidence for candidate cluster members."""

    def __init__(self, df: pd.DataFrame, user_features: pd.DataFrame):
        self.df = df
        self.user_features = user_features
        self._uf_index: Dict[str, Dict[str, Any]] = {}
        self._user_devices: Dict[str, Set[str]] = defaultdict(set)
        self._user_subnets: Dict[str, Set[str]] = defaultdict(set)
        self._user_merchants: Dict[str, Set[str]] = defaultdict(set)
        self._device_users: Dict[str, Set[str]] = defaultdict(set)
        self._subnet_users: Dict[str, Set[str]] = defaultdict(set)
        self._merchant_users: Dict[str, Set[str]] = defaultdict(set)
        self._pop_percentiles: Dict[str, Dict[str, float]] = {}
        self._temporal_overlaps: Dict[str, Dict[str, float]] = {}
        self._precompute_lookups()

    def _precompute_lookups(self) -> None:
        """Build inverted indices for O(1) evidence lookups."""
        df = self.df

        # Build user features index
        if not self.user_features.empty and "user_id" in self.user_features.columns:
            for _, row in self.user_features.iterrows():
                uid = str(row["user_id"])
                self._uf_index[uid] = row.to_dict()

        # User -> devices, devices -> users
        if "device_fingerprint" in df.columns:
            pairs = df[["user_id", "device_fingerprint"]].dropna()
            pairs = pairs[pairs["device_fingerprint"].astype(str).str.strip() != ""]
            for uid, dev in zip(pairs["user_id"].astype(str), pairs["device_fingerprint"].astype(str)):
                self._user_devices[uid].add(dev)
                self._device_users[dev].add(uid)

        # User -> subnets, subnets -> users
        subnet_col = "ip_prefix_24" if "ip_prefix_24" in df.columns else None
        if subnet_col:
            pairs = df[["user_id", subnet_col]].dropna()
            pairs = pairs[pairs[subnet_col].astype(str).str.strip() != ""]
            for uid, sub in zip(pairs["user_id"].astype(str), pairs[subnet_col].astype(str)):
                self._user_subnets[uid].add(sub)
                self._subnet_users[sub].add(uid)

        # User -> merchants, merchants -> users
        if "merchant_id" in df.columns:
            pairs = df[["user_id", "merchant_id"]].dropna()
            for uid, merch in zip(pairs["user_id"].astype(str), pairs["merchant_id"].astype(str)):
                self._user_merchants[uid].add(merch)
                self._merchant_users[merch].add(uid)

        # Population percentiles for behavioral evidence
        if not self.user_features.empty:
            for col in ["txn_count", "micro_amount_ratio", "burstiness_cv",
                        "merchant_concentration_hhi", "n_unique_merchants",
                        "n_unique_bins", "device_sharing_score"]:
                if col in self.user_features.columns:
                    vals = self.user_features[col].dropna().values
                    if len(vals) > 0:
                        self._pop_percentiles[col] = {
                            "p50": float(np.percentile(vals, 50)),
                            "p75": float(np.percentile(vals, 75)),
                            "p90": float(np.percentile(vals, 90)),
                            "p95": float(np.percentile(vals, 95)),
                            "p99": float(np.percentile(vals, 99)),
                        }

    def set_temporal_overlaps(self, overlaps: Dict[str, Dict[str, float]]) -> None:
        """Inject precomputed temporal overlap scores from TemporalAnalyzer."""
        self._temporal_overlaps = overlaps

    def collect_for_cluster(
        self, cluster: CandidateCluster,
    ) -> Dict[str, MemberEvidence]:
        """
        Collect all evidence for every member in a candidate cluster.
        Returns dict mapping user_id -> MemberEvidence.
        """
        member_set = set(cluster.member_user_ids)
        member_evidence = {}

        for uid in cluster.member_user_ids:
            items: List[EvidenceItem] = []
            items.extend(self._infrastructure_evidence(uid, member_set))
            items.extend(self._behavioral_evidence(uid, member_set))
            items.extend(self._temporal_evidence(uid, member_set))
            items.extend(self._financial_flow_evidence(uid, member_set))
            items.extend(self._account_anomaly_evidence(uid))
            items.extend(self._merchant_pattern_evidence(uid, member_set))

            types_present = len(set(e.evidence_type for e in items))
            affinity = self._compute_affinity(items)

            member_evidence[uid] = MemberEvidence(
                user_id=uid,
                evidence_items=items,
                evidence_type_count=types_present,
                affinity_score=affinity,
            )

        return member_evidence

    # ------------------------------------------------------------------
    # Evidence dimension collectors
    # ------------------------------------------------------------------

    def _infrastructure_evidence(
        self, uid: str, member_set: Set[str]
    ) -> List[EvidenceItem]:
        """Shared devices and IP subnets with other cluster members."""
        items = []
        etype = EvidenceType.INFRASTRUCTURE.value

        # Shared devices (with statistical lift check)
        total_users = max(len(self._uf_index), 1)
        expected_rate = len(member_set) / total_users

        for dev in self._user_devices.get(uid, set()):
            shared_with = self._device_users.get(dev, set()) & member_set - {uid}
            if shared_with:
                total_dev_users = len(self._device_users.get(dev, set()))
                # Lift: is the cluster over-represented on this device?
                actual_rate = (len(shared_with) + 1) / max(total_dev_users, 1)
                lift = actual_rate / max(expected_rate, 0.0001)
                # Require 2x over-representation to count as meaningful
                if lift < 2.0:
                    continue
                strength = min(1.0, len(shared_with) * 0.3)
                items.append(EvidenceItem(
                    evidence_type=etype,
                    dimension="shared_device",
                    strength=strength,
                    description=f"Shares device {dev[:12]}... with {len(shared_with)} cluster member(s) "
                                f"(lift: {lift:.1f}x)",
                    raw_value={"device": dev, "shared_count": len(shared_with),
                               "lift": round(lift, 2)},
                    related_users=sorted(shared_with)[:10],
                ))

        # Shared subnets (/24) -- require 3+ members and statistical lift
        for subnet in self._user_subnets.get(uid, set()):
            shared_with = self._subnet_users.get(subnet, set()) & member_set - {uid}
            if len(shared_with) >= 3:
                total_subnet_users = len(self._subnet_users.get(subnet, set()))
                actual_rate = (len(shared_with) + 1) / max(total_subnet_users, 1)
                lift = actual_rate / max(expected_rate, 0.0001)
                if lift < 2.0:
                    continue
                strength = min(1.0, len(shared_with) * 0.10)
                items.append(EvidenceItem(
                    evidence_type=etype,
                    dimension="shared_subnet",
                    strength=strength,
                    description=f"Shares /24 subnet {subnet} with {len(shared_with)} member(s) "
                                f"(lift: {lift:.1f}x)",
                    raw_value={"subnet": subnet, "shared_count": len(shared_with),
                               "lift": round(lift, 2)},
                    related_users=sorted(shared_with)[:10],
                ))

        return items

    def _behavioral_evidence(
        self, uid: str, member_set: Set[str]
    ) -> List[EvidenceItem]:
        """Behavioral anomalies relative to population baselines."""
        items = []
        etype = EvidenceType.BEHAVIORAL.value
        uf = self._uf_index.get(uid, {})

        # High transaction volume (p95 threshold)
        txn_count = float(uf.get("txn_count", 0))
        p95 = self._pop_percentiles.get("txn_count", {}).get("p95", float("inf"))
        if txn_count > p95 and p95 > 0:
            p99 = self._pop_percentiles.get("txn_count", {}).get("p99", txn_count)
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="high_txn_volume",
                strength=min(1.0, txn_count / max(p99, 1)),
                description=f"Transaction count ({txn_count:.0f}) exceeds 95th percentile ({p95:.0f})",
                raw_value=txn_count,
            ))

        # Micro-amount pattern (stricter threshold)
        micro_ratio = float(uf.get("micro_amount_ratio", 0))
        if micro_ratio > 0.4:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="micro_amount_pattern",
                strength=micro_ratio,
                description=f"{micro_ratio:.0%} of transactions are micro-amounts (<$10)",
                raw_value=micro_ratio,
            ))

        # High burstiness (p95 threshold)
        burst_cv = float(uf.get("burstiness_cv", 0))
        p95_burst = self._pop_percentiles.get("burstiness_cv", {}).get("p95", 2.0)
        if burst_cv > p95_burst and burst_cv > 1.0:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="high_burstiness",
                strength=min(1.0, burst_cv / 3.0),
                description=f"High burstiness CV={burst_cv:.2f} (95th pctl: {p95_burst:.2f})",
                raw_value=burst_cv,
            ))

        # High unique merchants (p95 threshold)
        n_merch = float(uf.get("n_unique_merchants", 0))
        p95_merch = self._pop_percentiles.get("n_unique_merchants", {}).get("p95", float("inf"))
        if n_merch > p95_merch and p95_merch > 0:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="high_merchant_diversity",
                strength=min(1.0, n_merch / max(p95_merch * 2, 1)),
                description=f"Uses {n_merch:.0f} unique merchants (95th pctl: {p95_merch:.0f})",
                raw_value=n_merch,
            ))

        # High unique BINs (p95 threshold)
        n_bins = float(uf.get("n_unique_bins", 0))
        p95_bins = self._pop_percentiles.get("n_unique_bins", {}).get("p95", float("inf"))
        if n_bins > p95_bins and p95_bins > 0:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="high_bin_diversity",
                strength=min(1.0, n_bins / max(p95_bins * 2, 1)),
                description=f"Uses {n_bins:.0f} unique card BINs (95th pctl: {p95_bins:.0f})",
                raw_value=n_bins,
            ))

        return items

    def _temporal_evidence(
        self, uid: str, member_set: Set[str]
    ) -> List[EvidenceItem]:
        """Temporal co-occurrence with other cluster members."""
        items = []
        etype = EvidenceType.TEMPORAL.value

        overlap = self._temporal_overlaps.get(uid, {})
        cooccurring = {u: v for u, v in overlap.items()
                       if u in member_set and v > 0.1}

        if len(cooccurring) >= 2:
            avg_score = float(np.mean(list(cooccurring.values())))
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="temporal_cooccurrence",
                strength=min(1.0, avg_score),
                description=f"Temporal co-occurrence with {len(cooccurring)} cluster members "
                            f"(avg score: {avg_score:.2f})",
                raw_value=len(cooccurring),
                related_users=sorted(cooccurring.keys())[:10],
            ))

        # Burst windows
        uf = self._uf_index.get(uid, {})
        burst_windows = int(uf.get("burst_window_count", 0))
        if burst_windows >= 2:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="burst_windows",
                strength=min(1.0, burst_windows / 10.0),
                description=f"{burst_windows} burst window(s) with 3+ transactions in 5 min",
                raw_value=burst_windows,
            ))

        return items

    def _financial_flow_evidence(
        self, uid: str, member_set: Set[str]
    ) -> List[EvidenceItem]:
        """Shared merchant concentration with cluster members."""
        items = []
        etype = EvidenceType.FINANCIAL_FLOW.value

        user_merchants = self._user_merchants.get(uid, set())
        if not user_merchants:
            return items

        # Count how many cluster members share each of this user's merchants
        merchant_member_counts: Dict[str, int] = defaultdict(int)
        for merch in user_merchants:
            shared = self._merchant_users.get(merch, set()) & member_set - {uid}
            if shared:
                merchant_member_counts[merch] = len(shared)

        # Report merchants shared with 5+ cluster members (stricter)
        for merch, count in sorted(merchant_member_counts.items(),
                                    key=lambda x: x[1], reverse=True)[:3]:
            if count >= 5:
                items.append(EvidenceItem(
                    evidence_type=etype,
                    dimension="shared_merchant_concentration",
                    strength=min(1.0, count * 0.08),
                    description=f"Merchant {merch} shared with {count} cluster members",
                    raw_value={"merchant": merch, "shared_count": count},
                    related_users=sorted(
                        self._merchant_users.get(merch, set()) & member_set - {uid}
                    )[:10],
                ))

        # Threshold-amount pattern (potential structuring)
        uf = self._uf_index.get(uid, {})
        thresh_ratio = float(uf.get("threshold_amount_ratio", 0))
        if thresh_ratio > 0.25:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="threshold_amounts",
                strength=min(1.0, thresh_ratio * 2),
                description=f"{thresh_ratio:.0%} of transactions near common thresholds",
                raw_value=thresh_ratio,
            ))

        return items

    def _account_anomaly_evidence(self, uid: str) -> List[EvidenceItem]:
        """Per-account ATO signals."""
        items = []
        etype = EvidenceType.ACCOUNT_ANOMALY.value
        uf = self._uf_index.get(uid, {})

        # New account (very recent only)
        acct_age = float(uf.get("account_age_days", 365))
        if acct_age < 14:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="new_account",
                strength=max(0.0, 1.0 - acct_age / 14.0),
                description=f"Account only {acct_age:.0f} days old",
                raw_value=acct_age,
            ))

        # Login failures (strong signal only)
        login_fails = float(uf.get("login_failures_24h", 0))
        if login_fails >= 5:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="login_failures",
                strength=min(1.0, login_fails / 10.0),
                description=f"{login_fails:.0f} login failures in 24h",
                raw_value=login_fails,
            ))

        # Recent password change
        pwd_change = float(uf.get("password_change_7d", 0))
        if pwd_change > 0:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="recent_password_change",
                strength=0.6,
                description="Password changed within last 7 days",
                raw_value=pwd_change,
            ))

        # Low KYC (only "none" -- "basic" is too common at 55% of users)
        kyc = str(uf.get("kyc_level", "full"))
        if kyc in ("none", "0", "0.0"):
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="low_kyc",
                strength=0.4,
                description="KYC level: none",
                raw_value=kyc,
            ))

        return items

    def _merchant_pattern_evidence(
        self, uid: str, member_set: Set[str]
    ) -> List[EvidenceItem]:
        """Mule/merchant fraud indicators."""
        items = []
        etype = EvidenceType.MERCHANT_PATTERN.value
        uf = self._uf_index.get(uid, {})

        # High merchant risk (p95+ only)
        mr = float(uf.get("merchant_risk_mean", 0))
        if mr > 0.75:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="high_risk_merchants",
                strength=mr,
                description=f"Average merchant risk score: {mr:.2f}",
                raw_value=mr,
            ))

        # High merchant concentration (mule pattern - stricter)
        hhi = float(uf.get("merchant_concentration_hhi", 0))
        if hhi > 0.7:
            items.append(EvidenceItem(
                evidence_type=etype,
                dimension="merchant_concentration",
                strength=min(1.0, hhi),
                description=f"High merchant concentration HHI={hhi:.3f}",
                raw_value=hhi,
            ))

        # Note: cross_border_ratio removed -- 98% of users in this dataset
        # are cross-border, making it useless as a discriminator.

        return items

    # ------------------------------------------------------------------
    # Cluster-membership evidence for behavioral/temporal candidates
    # ------------------------------------------------------------------

    def add_cluster_cohort_evidence(
        self,
        member_evidence: Dict[str, MemberEvidence],
        candidate: CandidateCluster,
    ) -> Dict[str, MemberEvidence]:
        """
        For behavioral/temporal candidates, add a cohort evidence item
        to each member. The clustering itself IS evidence of coordination:
        HDBSCAN grouped these users by feature similarity.
        """
        discovery = candidate.discovery_method
        anomaly_mean = candidate.metadata.get("anomaly_score_mean", 0.5)
        anomaly_thresh = candidate.metadata.get("anomaly_score_threshold", 1.0)

        if discovery == "behavioral_hdbscan":
            etype = EvidenceType.BEHAVIORAL.value
            dimension = "behavioral_cluster_cohort"
            strength = min(1.0, anomaly_mean / max(anomaly_thresh * 2, 0.1))
            desc = (f"Member of behavioral cluster ({candidate.size} users, "
                    f"mean anomaly={anomaly_mean:.2f})")
        elif discovery == "temporal_cooccurrence":
            etype = EvidenceType.TEMPORAL.value
            dimension = "temporal_cluster_cohort"
            strength = min(1.0, candidate.discovery_score)
            desc = (f"Member of temporal co-occurrence cluster "
                    f"({candidate.size} users)")
        else:
            return member_evidence

        other_members = sorted(candidate.member_user_ids)[:10]
        for uid, me in member_evidence.items():
            me.evidence_items.append(EvidenceItem(
                evidence_type=etype,
                dimension=dimension,
                strength=strength,
                description=desc,
                raw_value={"discovery_method": discovery,
                           "cluster_size": candidate.size},
                related_users=[u for u in other_members if u != uid],
            ))
            # Recompute counts and affinity
            me.evidence_type_count = len(set(e.evidence_type for e in me.evidence_items))
            me.affinity_score = self._compute_affinity(me.evidence_items)

        return member_evidence

    # ------------------------------------------------------------------
    # Affinity scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_affinity(items: List[EvidenceItem]) -> float:
        """
        Composite affinity from evidence items.
        Weighted by evidence type diversity and individual strengths.
        """
        if not items:
            return 0.0

        type_groups: Dict[str, List[float]] = defaultdict(list)
        for item in items:
            type_groups[item.evidence_type].append(item.strength)

        # Per-type: take max strength
        type_max = {t: max(strengths) for t, strengths in type_groups.items()}

        # Diversity bonus: more independent evidence types = stronger signal
        n_types = len(type_max)
        diversity_bonus = min(0.2, n_types * 0.04)

        # Base: average of per-type max strengths
        total_dimensions = len(EvidenceType)
        base = sum(type_max.values()) / max(total_dimensions, 1)

        return min(1.0, base + diversity_bonus)
