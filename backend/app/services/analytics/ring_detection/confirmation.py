"""
Phase 2 confirmation: converts raw candidate clusters into high-quality
confirmed rings using multi-evidence gating, membership scoring,
sub-cluster splitting, and deduplication.
"""

import numpy as np
import networkx as nx
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from .schemas import (
    EvidenceType, MembershipRole, MemberEvidence,
    CandidateCluster, ConfirmedRing,
)
from .evidence import EvidenceCollector
from .membership import MembershipScorer


class RingConfirmation:
    """Phase 2: Confirms candidate clusters into high-quality rings."""

    # Evidence types that demonstrate coordination between members
    RELATIONAL_TYPES = {
        EvidenceType.INFRASTRUCTURE.value,
        EvidenceType.TEMPORAL.value,
        EvidenceType.FINANCIAL_FLOW.value,
    }

    def __init__(
        self,
        evidence_collector: EvidenceCollector,
        membership_scorer: MembershipScorer,
        min_evidence_types: int = 3,
        max_ring_size: int = 80,
        min_ring_size: int = 4,
        min_cohesion: float = 0.25,
        min_relational_ratio: float = 0.25,
    ):
        self.evidence_collector = evidence_collector
        self.membership_scorer = membership_scorer
        self.min_evidence_types = min_evidence_types
        self.max_ring_size = max_ring_size
        self.min_ring_size = min_ring_size
        self.min_cohesion = min_cohesion
        self.min_relational_ratio = min_relational_ratio
        self.confirmation_log: List[Dict] = []

    def confirm_candidates(
        self, candidates: List[CandidateCluster],
    ) -> List[ConfirmedRing]:
        """
        Process all candidates through the confirmation pipeline.

        For each candidate:
        1. Collect evidence for all members
        2. Score membership, assign roles
        3. If oversized, split into sub-clusters
        4. Trim weak members
        5. Apply multi-evidence gate
        6. Assemble ConfirmedRing
        """
        confirmed = []

        for candidate in candidates:
            rings = self._confirm_single(candidate)
            confirmed.extend(rings)

        # Merge confirmed sub-clusters from the same parent community
        confirmed = self._merge_siblings(confirmed)

        # Deduplicate: merge rings with high member overlap
        confirmed = self._deduplicate_rings(confirmed)

        print(f"[Confirmation] {len(candidates)} candidates -> {len(confirmed)} confirmed rings")
        return confirmed

    def _confirm_single(
        self, candidate: CandidateCluster,
    ) -> List[ConfirmedRing]:
        """Confirm a single candidate cluster."""
        is_behavioral = candidate.discovery_method in (
            "behavioral_hdbscan", "temporal_cooccurrence"
        )

        if len(candidate.member_user_ids) > self.max_ring_size:
            if is_behavioral:
                # Behavioral/temporal: don't split by infrastructure.
                # Confirm the full cluster with cohort evidence added.
                member_evidence = self.evidence_collector.collect_for_cluster(candidate)
                member_evidence = self.evidence_collector.add_cluster_cohort_evidence(
                    member_evidence, candidate
                )
                member_evidence = self.membership_scorer.score_and_assign_roles(member_evidence)
                ring = self._gate_and_assemble(candidate, member_evidence)
                return [ring] if ring is not None else []
            else:
                # Graph-discovered: split by shared identifiers, then
                # collect evidence per sub-cluster.
                sub_clusters = self._split_oversized_raw(candidate)
                results = []
                for sub_candidate in sub_clusters:
                    sub_evidence = self.evidence_collector.collect_for_cluster(sub_candidate)
                    sub_evidence = self.membership_scorer.score_and_assign_roles(sub_evidence)
                    ring = self._gate_and_assemble(sub_candidate, sub_evidence)
                    if ring is not None:
                        results.append(ring)
                return results

        # For small candidates: collect evidence directly
        member_evidence = self.evidence_collector.collect_for_cluster(candidate)
        if is_behavioral:
            member_evidence = self.evidence_collector.add_cluster_cohort_evidence(
                member_evidence, candidate
            )
        member_evidence = self.membership_scorer.score_and_assign_roles(member_evidence)
        ring = self._gate_and_assemble(candidate, member_evidence)
        return [ring] if ring is not None else []

    def _gate_and_assemble(
        self,
        candidate: CandidateCluster,
        member_evidence: Dict[str, MemberEvidence],
    ) -> ConfirmedRing:
        """Trim, apply multi-evidence gate, and assemble a ConfirmedRing."""
        # Trim weak members
        member_evidence = self.membership_scorer.trim_weak_members(member_evidence)

        active_members = {
            uid: me for uid, me in member_evidence.items()
            if not me.is_trimmed
        }

        if len(active_members) < self.min_ring_size:
            self.confirmation_log.append({
                "cluster_id": candidate.cluster_id,
                "reason": "too_small_after_trim",
                "size_before": len(member_evidence),
                "size_after": len(active_members),
            })
            return None

        # Multi-evidence gate: check ring-level evidence diversity
        ring_evidence_types: Set[str] = set()
        for me in active_members.values():
            for ei in me.evidence_items:
                ring_evidence_types.add(ei.evidence_type)

        if len(ring_evidence_types) < self.min_evidence_types:
            self.confirmation_log.append({
                "cluster_id": candidate.cluster_id,
                "reason": "insufficient_evidence_types",
                "evidence_types": len(ring_evidence_types),
                "required": self.min_evidence_types,
            })
            return None

        # Relational evidence gate: a fraud RING requires coordination signals,
        # not just individual anomalies. The requirement depends on discovery method:
        # - Graph-discovered: MUST have relational evidence (that's how they were found)
        # - Behavioral/temporal: the clustering itself is the coordination signal,
        #   so we require strong evidence diversity instead.
        relational_in_ring = ring_evidence_types & self.RELATIONAL_TYPES
        is_behavioral = candidate.discovery_method in (
            "behavioral_hdbscan", "temporal_cooccurrence"
        )

        if not is_behavioral:
            # Graph-discovered: require relational evidence with member coverage
            if not relational_in_ring:
                self.confirmation_log.append({
                    "cluster_id": candidate.cluster_id,
                    "reason": "no_relational_evidence",
                    "evidence_types": sorted(ring_evidence_types),
                })
                return None

            members_with_relational = sum(
                1 for me in active_members.values()
                if any(ei.evidence_type in self.RELATIONAL_TYPES for ei in me.evidence_items)
            )
            relational_ratio = members_with_relational / max(len(active_members), 1)
            if relational_ratio < self.min_relational_ratio:
                self.confirmation_log.append({
                    "cluster_id": candidate.cluster_id,
                    "reason": "low_relational_coverage",
                    "relational_ratio": round(relational_ratio, 3),
                    "required": self.min_relational_ratio,
                })
                return None
        else:
            # Behavioral/temporal: the clustering is the coordination signal.
            # Require at least 2 evidence types for basic diversity.
            if len(ring_evidence_types) < 2:
                self.confirmation_log.append({
                    "cluster_id": candidate.cluster_id,
                    "reason": "behavioral_insufficient_diversity",
                    "evidence_types": sorted(ring_evidence_types),
                })
                return None

        # Cohesion gate: mean affinity of active members must be sufficient
        cohesion = self.membership_scorer.compute_ring_cohesion(
            {uid: me for uid, me in member_evidence.items() if uid in active_members}
        )
        if cohesion < self.min_cohesion:
            self.confirmation_log.append({
                "cluster_id": candidate.cluster_id,
                "reason": "low_cohesion",
                "cohesion": round(cohesion, 3),
                "required": self.min_cohesion,
            })
            return None

        # Assemble confirmed ring and check minimum confidence
        ring = self._assemble_ring(candidate, active_members, ring_evidence_types)
        if ring.confidence < 0.40:
            self.confirmation_log.append({
                "cluster_id": candidate.cluster_id,
                "reason": "low_confidence",
                "confidence": ring.confidence,
            })
            return None

        return ring

    def _split_oversized_raw(
        self, candidate: CandidateCluster,
    ) -> List[CandidateCluster]:
        """
        Split oversized communities using shared identifiers from the
        evidence collector's pre-built indices. Does NOT require evidence
        to be collected first.
        """
        member_set = set(candidate.member_user_ids)
        ec = self.evidence_collector

        G = nx.Graph()
        for uid in candidate.member_user_ids:
            G.add_node(uid)

        # Build edges from shared devices
        for uid in candidate.member_user_ids:
            for dev in ec._user_devices.get(uid, set()):
                shared = ec._device_users.get(dev, set()) & member_set - {uid}
                for other in shared:
                    if G.has_edge(uid, other):
                        G[uid][other]["weight"] += 1.0
                    else:
                        G.add_edge(uid, other, weight=1.0)

            # And shared subnets
            for subnet in ec._user_subnets.get(uid, set()):
                shared = ec._subnet_users.get(subnet, set()) & member_set - {uid}
                for other in shared:
                    if G.has_edge(uid, other):
                        G[uid][other]["weight"] += 0.5
                    else:
                        G.add_edge(uid, other, weight=0.5)

        # Run Louvain with high resolution for tighter clusters
        try:
            sub_communities = list(
                nx.community.louvain_communities(
                    G, weight="weight", resolution=2.0, seed=42
                )
            )
        except Exception:
            return [candidate]

        results = []
        for idx, community in enumerate(sub_communities):
            members = [uid for uid in community if uid in member_set]
            if len(members) < self.min_ring_size:
                continue
            results.append(CandidateCluster(
                cluster_id=f"{candidate.cluster_id}_sub{idx}",
                member_user_ids=members,
                size=len(members),
                discovery_method=candidate.discovery_method,
                discovery_score=candidate.discovery_score,
                metadata=dict(candidate.metadata),
            ))

        if not results:
            return [candidate]

        print(f"[Confirmation] Split {candidate.cluster_id} "
              f"({len(candidate.member_user_ids)} members) into {len(results)} sub-clusters")
        return results

    def _merge_siblings(self, rings: List[ConfirmedRing]) -> List[ConfirmedRing]:
        """
        Merge confirmed sub-clusters from the same parent community.

        After splitting ring_000 into ring_000_sub1, ring_000_sub5, etc.,
        if multiple sub-clusters are confirmed, merge them back into one
        ring to improve coverage of large GT rings.
        """
        if len(rings) <= 1:
            return rings

        # Group by parent community ID (strip _sub* suffix)
        parent_groups: Dict[str, List[int]] = defaultdict(list)
        for i, ring in enumerate(rings):
            rid = ring.ring_id
            if "_sub" in rid:
                parent = rid[:rid.index("_sub")]
            else:
                parent = rid
            parent_groups[parent].append(i)

        merged = []
        for parent, indices in parent_groups.items():
            if len(indices) == 1:
                merged.append(rings[indices[0]])
                continue

            # Merge all siblings into one ring
            all_members = []
            all_evidence_types = set()
            all_methods = set()
            for idx in indices:
                r = rings[idx]
                all_members.extend(r.members)
                all_evidence_types.update(r.primary_evidence_types)
                all_methods.update(r.discovery_methods)

            # Deduplicate members by user_id (keep highest affinity)
            member_by_uid: Dict[str, MemberEvidence] = {}
            for m in all_members:
                if m.user_id not in member_by_uid or m.affinity_score > member_by_uid[m.user_id].affinity_score:
                    member_by_uid[m.user_id] = m

            member_list = list(member_by_uid.values())
            core = [m for m in member_list if m.role == MembershipRole.CORE.value and not m.is_trimmed]
            suspected = [m for m in member_list if m.role == MembershipRole.SUSPECTED.value and not m.is_trimmed]
            peripheral = [m for m in member_list if m.role == MembershipRole.PERIPHERAL.value and not m.is_trimmed]
            active = [m for m in member_list if not m.is_trimmed]

            mean_affinity = float(np.mean([m.affinity_score for m in active])) if active else 0
            core_ratio = len(core) / max(len(active), 1)
            evidence_diversity = len(all_evidence_types) / len(EvidenceType)
            confidence = min(1.0, mean_affinity * 0.4 + core_ratio * 0.3 + evidence_diversity * 0.3)

            # Collect shared identifiers from all siblings
            shared_ids: Dict[str, List[str]] = defaultdict(list)
            for idx in indices:
                for id_type, id_list in rings[idx].shared_identifiers.items():
                    shared_ids[id_type].extend(id_list)
            # Deduplicate
            shared_ids = {k: list(set(v)) for k, v in shared_ids.items()}

            merged_ring = ConfirmedRing(
                ring_id=parent,
                confidence=round(confidence, 3),
                members=member_list,
                member_count=len(active),
                core_member_count=len(core),
                suspected_member_count=len(suspected),
                peripheral_member_count=len(peripheral),
                evidence_type_count=len(all_evidence_types),
                primary_evidence_types=sorted(all_evidence_types),
                shared_identifiers=dict(shared_ids),
                discovery_methods=sorted(all_methods),
                detection_method=rings[indices[0]].detection_method,
                evidence_summary={
                    "mean_affinity": round(mean_affinity, 3),
                    "core_ratio": round(core_ratio, 3),
                    "evidence_diversity": round(evidence_diversity, 3),
                    "merged_from": len(indices),
                },
            )
            merged.append(merged_ring)

        if len(merged) < len(rings):
            print(f"[Confirmation] Sibling merge: {len(rings)} -> {len(merged)} rings")

        return merged

    def _deduplicate_rings(
        self, rings: List[ConfirmedRing], jaccard_threshold: float = 0.4
    ) -> List[ConfirmedRing]:
        """Merge rings with high member overlap using union-find."""
        if len(rings) <= 1:
            return rings

        member_sets = [
            set(m.user_id for m in r.members if not m.is_trimmed)
            for r in rings
        ]
        n = len(rings)
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
                union_size = len(si | sj)
                jaccard = intersection / union_size
                containment = max(
                    intersection / len(si) if si else 0,
                    intersection / len(sj) if sj else 0,
                )
                if jaccard > jaccard_threshold or containment > 0.5:
                    union(i, j)

        # Group by root, keep highest-confidence ring per group
        groups: Dict[int, List[int]] = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        deduplicated = []
        for indices in groups.values():
            best_idx = max(indices, key=lambda i: (
                rings[i].evidence_type_count,
                rings[i].confidence,
                rings[i].member_count,
            ))
            deduplicated.append(rings[best_idx])

        if len(deduplicated) < n:
            print(f"[Confirmation] Deduplication: {n} -> {len(deduplicated)} rings")

        return deduplicated

    def _assemble_ring(
        self,
        candidate: CandidateCluster,
        active_members: Dict[str, MemberEvidence],
        evidence_types: Set[str],
    ) -> ConfirmedRing:
        """Assemble a ConfirmedRing from confirmed members and evidence."""
        member_list = list(active_members.values())
        core = [m for m in member_list if m.role == MembershipRole.CORE.value]
        suspected = [m for m in member_list if m.role == MembershipRole.SUSPECTED.value]
        peripheral = [m for m in member_list if m.role == MembershipRole.PERIPHERAL.value]

        # Confidence from evidence diversity, affinity, and core ratio
        mean_affinity = float(np.mean([m.affinity_score for m in member_list]))
        core_ratio = len(core) / max(len(member_list), 1)
        evidence_diversity = len(evidence_types) / len(EvidenceType)
        confidence = min(1.0, mean_affinity * 0.4 + core_ratio * 0.3 + evidence_diversity * 0.3)

        # Build shared identifiers from infrastructure evidence
        shared_ids: Dict[str, List[str]] = defaultdict(list)
        seen_shared: Dict[str, set] = defaultdict(set)
        for me in member_list:
            for ei in me.evidence_items:
                if ei.dimension == "shared_device" and ei.raw_value:
                    dev = ei.raw_value.get("device", "") if isinstance(ei.raw_value, dict) else ""
                    if dev and dev not in seen_shared["devices"]:
                        shared_ids["devices"].append(dev)
                        seen_shared["devices"].add(dev)
                elif ei.dimension == "shared_subnet" and ei.raw_value:
                    sub = ei.raw_value.get("subnet", "") if isinstance(ei.raw_value, dict) else ""
                    if sub and sub not in seen_shared["ip_prefixes"]:
                        shared_ids["ip_prefixes"].append(sub)
                        seen_shared["ip_prefixes"].add(sub)

        return ConfirmedRing(
            ring_id=candidate.cluster_id,
            confidence=round(confidence, 3),
            members=member_list,
            member_count=len(member_list),
            core_member_count=len(core),
            suspected_member_count=len(suspected),
            peripheral_member_count=len(peripheral),
            evidence_type_count=len(evidence_types),
            primary_evidence_types=sorted(evidence_types),
            shared_identifiers=dict(shared_ids),
            discovery_methods=[candidate.discovery_method],
            detection_method=candidate.discovery_method,
            evidence_summary={
                "mean_affinity": round(mean_affinity, 3),
                "core_ratio": round(core_ratio, 3),
                "evidence_diversity": round(evidence_diversity, 3),
                "member_roles": {
                    "core": len(core),
                    "suspected": len(suspected),
                    "peripheral": len(peripheral),
                },
            },
        )
