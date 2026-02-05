"""
Two-phase fraud ring detection pipeline (v2).

Phase 1 - Discovery: runs multiple parallel detection strategies
    (graph, behavioral clustering, temporal co-occurrence)
Phase 2 - Confirmation: evidence collection, membership scoring,
    sub-cluster splitting, multi-evidence gating, diagnostics

Produces frontend-compatible JSON via backward-compatible ClassifiedRing output.
"""

import pandas as pd
import numpy as np
import json
import argparse
from datetime import datetime
from dataclasses import asdict
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict

from .schemas import (
    PipelineOutput, ClassifiedRing, TransactionScore,
    RingCandidate, RingFeatureVector, CandidateCluster,
    ConfirmedRing, DiagnosticReport,
)
from .feature_engineering import RingFeatureEngineer
from .graph_builder import FraudRingGraphBuilder
from .ring_classifier import RingClassifier
from .explainability import RingExplainer

# Column name mappings: alternate names -> canonical pipeline names
COLUMN_ALIASES = {
    "tx_id": "transaction_id",
    "timestamp_utc": "timestamp",
    "device_id": "device_fingerprint",
    "ip": "ip_address",
    "subnet": "_subnet_raw",
    "device_family": "_device_family",
}

# Candidate deduplication threshold (Jaccard)
CANDIDATE_DEDUP_JACCARD = 0.5


class RingDetectionPipeline:
    """Two-phase fraud ring detection pipeline."""

    def __init__(
        self,
        confidence_threshold: float = 0.45,
        enable_behavioral_clustering: bool = True,
        enable_temporal_analysis: bool = True,
        min_evidence_types: int = 2,
        max_ring_size: int = 500,
    ):
        self.confidence_threshold = confidence_threshold
        self.enable_behavioral = enable_behavioral_clustering
        self.enable_temporal = enable_temporal_analysis
        self.min_evidence_types = min_evidence_types
        self.max_ring_size = max_ring_size
        self.merge_log: List[Dict[str, Any]] = []

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Rename known alternate column names to canonical names."""
        rename_map = {}
        for alt, canonical in COLUMN_ALIASES.items():
            if alt in df.columns and canonical not in df.columns:
                rename_map[alt] = canonical
        if rename_map:
            df = df.rename(columns=rename_map)

        if "email_domain" in df.columns and "email" not in df.columns:
            df["email"] = "user@" + df["email_domain"].fillna("unknown.com").astype(str)

        return df

    def run(
        self,
        df_or_transactions: Union[pd.DataFrame, List[Dict[str, Any]]],
        return_transaction_scores: bool = True,
    ) -> PipelineOutput:
        """
        Execute the two-phase pipeline.

        Phase 1 - Discovery:
          1a. Graph-based candidate discovery
          1b. Behavioral clustering discovery
          1c. Temporal co-occurrence discovery
          1d. Union + deduplicate candidates

        Phase 2 - Confirmation:
          2a. Evidence collection per candidate
          2b. Membership scoring + role assignment
          2c. Sub-cluster splitting for oversized
          2d. Weak member trimming
          2e. Multi-evidence gate
          2f. Type-specific classification
          2g. Explainability
          2h. Self-diagnostics
          2i. Transaction scoring (optional)
        """
        # Convert to DataFrame
        if isinstance(df_or_transactions, pd.DataFrame):
            df = df_or_transactions.copy()
        elif isinstance(df_or_transactions, list):
            if not df_or_transactions:
                return self._empty_output()
            df = pd.DataFrame(df_or_transactions)
        else:
            return self._empty_output()

        if df.empty:
            return self._empty_output()

        df = self._normalize_columns(df)
        if "user_id" not in df.columns:
            return self._empty_output()

        try:
            # Feature engineering (including new features)
            engineer = RingFeatureEngineer(df)
            engineer.derive_ip_features()
            engineer.derive_email_domain()
            engineer.derive_card_bin()
            user_features = engineer.compute_per_user_features()

            print(f"[Pipeline] {len(df)} transactions, "
                  f"{df['user_id'].nunique()} users, "
                  f"{len(user_features)} user feature rows")

            # ============================================================
            # PHASE 1: DISCOVERY
            # ============================================================
            phase1_candidates: List[CandidateCluster] = []

            # 1a. Graph-based discovery
            phase1_candidates.extend(
                self._discover_graph(engineer.df)
            )

            # 1b. Behavioral clustering discovery
            if self.enable_behavioral:
                phase1_candidates.extend(
                    self._discover_behavioral(user_features)
                )

            # 1c. Temporal co-occurrence discovery
            if self.enable_temporal:
                phase1_candidates.extend(
                    self._discover_temporal(df)
                )

            # 1d. Deduplicate candidates
            phase1_candidates = self._deduplicate_candidates(phase1_candidates)

            print(f"[Pipeline] Phase 1: {len(phase1_candidates)} candidate clusters")

            if not phase1_candidates:
                return self._empty_output()

            # ============================================================
            # PHASE 2: CONFIRMATION
            # ============================================================
            from .evidence import EvidenceCollector
            from .membership import MembershipScorer
            from .confirmation import RingConfirmation
            from .temporal_analysis import TemporalAnalyzer

            # Precompute temporal overlaps for evidence collection
            temporal_overlaps = {}
            try:
                all_candidate_users = set()
                for c in phase1_candidates:
                    all_candidate_users.update(c.member_user_ids)
                if all_candidate_users:
                    ta = TemporalAnalyzer()
                    temporal_overlaps = ta.compute_pairwise_overlaps(
                        df, all_candidate_users
                    )
            except Exception as e:
                print(f"[Pipeline] Temporal overlap computation skipped: {e}")

            evidence_collector = EvidenceCollector(df, user_features)
            evidence_collector.set_temporal_overlaps(temporal_overlaps)

            membership_scorer = MembershipScorer()
            confirmation = RingConfirmation(
                evidence_collector=evidence_collector,
                membership_scorer=membership_scorer,
                min_evidence_types=self.min_evidence_types,
                max_ring_size=self.max_ring_size,
            )

            confirmed_rings = confirmation.confirm_candidates(phase1_candidates)
            self.merge_log = confirmation.confirmation_log

            if not confirmed_rings:
                output = self._empty_output()
                output.phase1_candidate_count = len(phase1_candidates)
                return output

            # Type-specific classification
            classifier = RingClassifier(
                confidence_threshold=self.confidence_threshold
            )
            confirmed_rings = classifier.classify_confirmed_rings(confirmed_rings)

            # Explainability
            explainer = RingExplainer()
            confirmed_rings = explainer.enrich_confirmed_rings(confirmed_rings)

            # Self-diagnostics
            from .diagnostics import PipelineDiagnostics
            diagnostics = PipelineDiagnostics(
                total_users=df["user_id"].nunique(),
                total_transactions=len(df),
            )
            diag_report = diagnostics.run_diagnostics(
                confirmed_rings, phase1_candidates
            )

            if diag_report.warnings:
                for w in diag_report.warnings:
                    print(f"[Pipeline] DIAGNOSTIC WARNING: {w}")
            if diag_report.errors:
                for e in diag_report.errors:
                    print(f"[Pipeline] DIAGNOSTIC ERROR: {e}")

            # Convert to ClassifiedRing for backward compatibility
            classified_rings = [r.to_classified_ring() for r in confirmed_rings]

            # Add sample transactions
            self._add_sample_transactions(classified_rings, df)

            # Transaction scoring
            transaction_scores = []
            if return_transaction_scores:
                # Build ring features for scorer (legacy path)
                ring_candidates_compat = self._rings_to_candidates(confirmed_rings)
                ring_features = engineer.compute_per_ring_features(
                    ring_candidates_compat, user_features
                )
                classifier_legacy = RingClassifier(
                    confidence_threshold=self.confidence_threshold
                )
                classifier_legacy.fit(ring_features)
                transaction_scores = classifier_legacy.score_transactions(
                    df, classified_rings, user_features
                )
                transaction_scores = explainer.enrich_transaction_scores(
                    transaction_scores, df, user_features, classified_rings
                )

            # Assemble output
            output = self._assemble_output(classified_rings, transaction_scores)
            output.diagnostics = diag_report
            output.phase1_candidate_count = len(phase1_candidates)
            output.phase2_confirmed_count = len(confirmed_rings)

            print(f"[Pipeline] Phase 2: {len(confirmed_rings)} confirmed rings, "
                  f"{output.phase1_candidate_count} candidates, "
                  f"diagnostics={'HEALTHY' if diag_report.is_healthy else 'ISSUES'}")

            return output

        except Exception as e:
            import traceback
            print(f"[RingDetectionPipeline] Error: {e}")
            traceback.print_exc()
            return self._empty_output()

    # ================================================================
    # Phase 1 discovery methods
    # ================================================================

    def _discover_graph(self, df: pd.DataFrame) -> List[CandidateCluster]:
        """Graph-based community discovery (existing Louvain pipeline)."""
        try:
            graph_builder = FraudRingGraphBuilder(df)
            ring_candidates = graph_builder.build_and_detect()

            candidates = []
            for rc in ring_candidates:
                candidates.append(CandidateCluster(
                    cluster_id=rc.ring_id,
                    member_user_ids=rc.member_user_ids,
                    size=rc.size,
                    discovery_method="graph_louvain",
                    discovery_score=rc.density,
                    metadata={
                        "shared_devices": len(rc.shared_devices),
                        "shared_ips": len(rc.shared_ip_prefixes),
                        "density": rc.density,
                    },
                ))

            print(f"[Pipeline] Graph discovery: {len(candidates)} candidates")
            return candidates
        except Exception as e:
            print(f"[Pipeline] Graph discovery failed: {e}")
            return []

    def _discover_behavioral(
        self, user_features: pd.DataFrame
    ) -> List[CandidateCluster]:
        """Behavioral clustering discovery (HDBSCAN on anomalous users)."""
        try:
            from .behavioral_clustering import BehavioralClusterer
            clusterer = BehavioralClusterer()
            candidates = clusterer.discover(user_features)
            print(f"[Pipeline] Behavioral discovery: {len(candidates)} candidates")
            return candidates
        except Exception as e:
            print(f"[Pipeline] Behavioral discovery skipped: {e}")
            return []

    def _discover_temporal(self, df: pd.DataFrame) -> List[CandidateCluster]:
        """Temporal co-occurrence discovery."""
        try:
            from .temporal_analysis import TemporalAnalyzer
            analyzer = TemporalAnalyzer()
            candidates = analyzer.discover_temporal_clusters(df)
            print(f"[Pipeline] Temporal discovery: {len(candidates)} candidates")
            return candidates
        except Exception as e:
            print(f"[Pipeline] Temporal discovery skipped: {e}")
            return []

    def _deduplicate_candidates(
        self, candidates: List[CandidateCluster],
    ) -> List[CandidateCluster]:
        """Merge candidate clusters with high member overlap."""
        if len(candidates) <= 1:
            return candidates

        n = len(candidates)
        member_sets = [set(c.member_user_ids) for c in candidates]
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                if len(member_sets[ra]) >= len(member_sets[rb]):
                    parent[rb] = ra
                else:
                    parent[ra] = rb

        for i in range(n):
            for j in range(i + 1, n):
                if find(i) == find(j):
                    continue
                si, sj = member_sets[i], member_sets[j]
                intersection = len(si & sj)
                if intersection == 0:
                    continue
                jaccard = intersection / len(si | sj)
                if jaccard > CANDIDATE_DEDUP_JACCARD:
                    union(i, j)

        groups: Dict[int, List[int]] = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        deduplicated = []
        for indices in groups.values():
            # Keep the candidate with the most discovery methods / largest size
            best = max(indices, key=lambda i: (candidates[i].size, candidates[i].discovery_score))
            base = candidates[best]

            # Collect all unique methods
            methods = set()
            all_members = set()
            for idx in indices:
                methods.add(candidates[idx].discovery_method)
                all_members.update(candidates[idx].member_user_ids)

            if len(indices) > 1:
                # Merge: expand member list, note multiple methods
                merged = CandidateCluster(
                    cluster_id=base.cluster_id,
                    member_user_ids=sorted(all_members),
                    size=len(all_members),
                    discovery_method="+".join(sorted(methods)),
                    discovery_score=base.discovery_score,
                    metadata={**base.metadata, "merged_from": len(indices)},
                )
                deduplicated.append(merged)
            else:
                deduplicated.append(base)

        if len(deduplicated) < n:
            print(f"[Pipeline] Candidate dedup: {n} -> {len(deduplicated)}")

        return deduplicated

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _rings_to_candidates(
        confirmed_rings: List[ConfirmedRing],
    ) -> List[RingCandidate]:
        """Convert ConfirmedRing to RingCandidate for legacy feature computation."""
        result = []
        for r in confirmed_rings:
            member_ids = [m.user_id for m in r.members if not m.is_trimmed]
            result.append(RingCandidate(
                ring_id=r.ring_id,
                member_user_ids=member_ids,
                size=len(member_ids),
                density=r.evidence_summary.get("mean_affinity", 0.0),
                shared_devices=r.shared_identifiers.get("devices", []),
                shared_ip_prefixes=r.shared_identifiers.get("ip_prefixes", []),
                detection_method=r.detection_method,
            ))
        return result

    def _add_sample_transactions(
        self, classified_rings: List[ClassifiedRing], df: pd.DataFrame
    ) -> None:
        """Add sample transactions from ring members to each ring."""
        for ring in classified_rings:
            member_set = set(ring.members)
            if "user_id" in df.columns:
                member_txns = df[df["user_id"].isin(member_set)]
                samples = member_txns.head(5)
                ring.sample_transactions = []
                for _, row in samples.iterrows():
                    sample = {}
                    for col in ["transaction_id", "user_id", "amount", "merchant_id", "timestamp"]:
                        val = row.get(col)
                        if val is not None and not (isinstance(val, float) and np.isnan(val)):
                            sample[col] = val
                    ring.sample_transactions.append(sample)

    def _assemble_output(
        self,
        classified_rings: List[ClassifiedRing],
        transaction_scores: List[TransactionScore],
    ) -> PipelineOutput:
        """Assemble the final PipelineOutput."""
        critical = sum(1 for r in classified_rings if r.severity == "CRITICAL")
        high = sum(1 for r in classified_rings if r.severity == "HIGH")
        medium = sum(1 for r in classified_rings if r.severity == "MEDIUM")

        if critical > 0:
            overall_risk = "CRITICAL"
        elif high > 0:
            overall_risk = "HIGH"
        elif medium > 0:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        total = len(classified_rings)
        total_members = sum(r.member_count for r in classified_rings)

        summary_parts = [
            f"Two-phase detection identified {total} fraud ring(s) "
            f"involving {total_members} accounts."
        ]
        if critical:
            summary_parts.append(
                f"{critical} CRITICAL severity ring(s) require immediate action."
            )
        if high:
            summary_parts.append(
                f"{high} HIGH severity ring(s) flagged for investigation."
            )

        return PipelineOutput(
            total_rings_detected=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            rings=classified_rings,
            overall_risk_level=overall_risk,
            executive_summary=" ".join(summary_parts),
            detection_timestamp=datetime.utcnow().isoformat(),
            transaction_scores=transaction_scores,
        )

    @staticmethod
    def _empty_output() -> PipelineOutput:
        return PipelineOutput(
            total_rings_detected=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            rings=[],
            overall_risk_level="LOW",
            executive_summary="No fraud rings detected.",
            detection_timestamp=datetime.utcnow().isoformat(),
            transaction_scores=[],
        )


def _convert_for_json(obj):
    """Recursively convert dataclass/numpy types for JSON serialization."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_for_json(i) for i in obj]
    elif hasattr(obj, "__dataclass_fields__"):
        return _convert_for_json(asdict(obj))
    elif pd.isna(obj):
        return None
    return obj


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run two-phase fraud ring detection pipeline")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", default="out/", help="Output directory")
    args = parser.parse_args()

    print(f"[Pipeline] Reading input from {args.input}...")
    df = pd.read_csv(args.input)
    print(f"[Pipeline] Loaded {len(df)} transactions")

    pipeline = RingDetectionPipeline()
    result = pipeline.run(df, return_transaction_scores=True)

    import os
    os.makedirs(args.output, exist_ok=True)

    result_dict = _convert_for_json(asdict(result))

    rings_output = {k: v for k, v in result_dict.items() if k != "transaction_scores"}
    scores_output = result_dict.get("transaction_scores", [])

    rings_path = os.path.join(args.output, "rings.json")
    scores_path = os.path.join(args.output, "transaction_scores.json")

    with open(rings_path, "w") as f:
        json.dump(rings_output, f, indent=2, default=str)
    print(f"[Pipeline] Wrote rings to {rings_path}")

    with open(scores_path, "w") as f:
        json.dump(scores_output, f, indent=2, default=str)
    print(f"[Pipeline] Wrote transaction scores to {scores_path}")

    print(f"[Pipeline] Done. {result.total_rings_detected} rings detected.")


if __name__ == "__main__":
    main()
