"""
Explainability module for fraud ring detection.

Generates per-transaction reasons and per-ring narratives
with supporting statistics.
"""

from typing import List, Dict, Any, Optional

from .schemas import ClassifiedRing, RingFeatureVector, TransactionScore, ConfirmedRing, MemberEvidence


class RingExplainer:
    """Generates human-readable explanations for ring detections and transaction scores."""

    def explain_transaction(
        self,
        tx_row: dict,
        user_features: dict,
        ring: Optional[ClassifiedRing] = None,
    ) -> List[str]:
        """
        Generate 3-7 reasons ordered by importance for a transaction.
        Draws from device sharing, subnet sharing, threshold amounts,
        burstiness, ring membership, merchant concentration, micro amounts.
        """
        reasons = []

        # Ring membership (highest priority)
        if ring and ring.ring_label != "Legit":
            reasons.append(
                f"Member of detected {ring.ring_label} ring "
                f"({ring.member_count} members, confidence={ring.confidence:.0%})"
            )

        # Device sharing
        device_score = float(user_features.get("device_sharing_score", 0))
        if device_score > 0.5:
            reasons.append(
                f"High device sharing score: {device_score:.2f} "
                f"(avg other users per device)"
            )

        # Subnet sharing /24
        subnet24 = float(user_features.get("subnet_sharing_score_24", 0))
        if subnet24 > 0.3:
            reasons.append(
                f"Subnet /24 sharing: {subnet24:.2f} avg other users on same subnet"
            )

        # Burstiness
        burst_cv = float(user_features.get("burstiness_cv", 0))
        if burst_cv > 0.8:
            reasons.append(
                f"High transaction burstiness: CV={burst_cv:.2f} "
                f"(irregular timing pattern)"
            )

        # Burst windows
        burst_windows = int(user_features.get("burst_window_count", 0))
        if burst_windows > 0:
            reasons.append(
                f"{burst_windows} burst window(s) with 3+ transactions in 5 minutes"
            )

        # Threshold amounts
        thresh_ratio = float(user_features.get("threshold_amount_ratio", 0))
        if thresh_ratio > 0.1:
            reasons.append(
                f"{thresh_ratio:.0%} of transactions near common thresholds "
                f"($49.99, $99.99, etc.)"
            )

        # Micro amounts
        micro_ratio = float(user_features.get("micro_amount_ratio", 0))
        if micro_ratio > 0.2:
            reasons.append(
                f"{micro_ratio:.0%} micro-transactions (< $10) - potential card testing"
            )

        # Merchant concentration
        merchant_hhi = float(user_features.get("merchant_concentration_hhi", 0))
        if merchant_hhi > 0.5:
            reasons.append(
                f"High merchant concentration (HHI={merchant_hhi:.3f}) - "
                f"transactions focused on few merchants"
            )

        # Geo mismatch
        geo_mismatch = float(user_features.get("geo_mismatch_rate", 0))
        if geo_mismatch > 0.1:
            reasons.append(
                f"{geo_mismatch:.0%} geographic mismatch rate "
                f"(IP country != card country)"
            )

        # Subnet /16 sharing
        subnet16 = float(user_features.get("subnet_sharing_score_16", 0))
        if subnet16 > 0.5:
            reasons.append(
                f"Broad subnet /16 sharing: {subnet16:.2f} avg other users"
            )

        # Ensure at least 3 reasons
        if len(reasons) < 3:
            if not reasons:
                reasons.append("No significant risk indicators detected")
            txn_count = int(user_features.get("txn_count", 0))
            if txn_count > 0:
                reasons.append(f"User has {txn_count} total transactions in dataset")
            amount_mean = float(user_features.get("amount_mean", 0))
            if amount_mean > 0:
                reasons.append(f"Average transaction amount: ${amount_mean:.2f}")

        return reasons[:7]

    def explain_ring(
        self,
        ring: ClassifiedRing,
        ring_features: Optional[RingFeatureVector] = None,
    ) -> Dict[str, Any]:
        """
        Generate ring-level explanation with narrative, risk factors, and identifiers.
        """
        # Strongest shared identifiers
        strongest = {}
        for id_type, id_list in ring.shared_identifiers.items():
            if id_list:
                strongest[id_type] = id_list[:5]

        # Top risk factors
        risk_factors = []
        if ring_features:
            factor_map = {
                "Device sharing": (ring_features.mean_device_sharing, 0.1),
                "Subnet sharing (/24)": (ring_features.mean_subnet_sharing_24, 0.1),
                "Burstiness": (ring_features.mean_burstiness_cv, 0.3),
                "Micro-amount ratio": (ring_features.mean_micro_amount_ratio, 0.1),
                "Threshold-amount ratio": (ring_features.mean_threshold_amount_ratio, 0.05),
                "Merchant concentration (HHI)": (ring_features.mean_merchant_hhi, 0.3),
                "Geo mismatch rate": (ring_features.mean_geo_mismatch_rate, 0.05),
                "Graph density": (ring_features.density, 0.1),
            }

            for factor_name, (value, baseline) in factor_map.items():
                if value > baseline:
                    risk_factors.append({
                        "factor": factor_name,
                        "value": round(value, 3),
                        "baseline": baseline,
                        "deviation": round(value - baseline, 3),
                    })

            risk_factors.sort(key=lambda x: x["deviation"], reverse=True)

        # Build narrative
        narrative = self._build_narrative(ring, ring_features, risk_factors)

        return {
            "strongest_shared_identifiers": strongest,
            "risk_narrative": narrative,
            "top_risk_factors": risk_factors[:5],
        }

    def _build_narrative(
        self,
        ring: ClassifiedRing,
        rf: Optional[RingFeatureVector],
        risk_factors: list,
    ) -> str:
        """Build 2-3 sentence risk narrative."""
        parts = []

        # Opening sentence
        if ring.ring_label == "RingA_CardTesting":
            parts.append(
                f"This {ring.member_count}-member ring exhibits card testing behavior, "
                f"with members sharing devices and executing micro-transactions."
            )
        elif ring.ring_label == "RingB_MuleMerchant":
            parts.append(
                f"This {ring.member_count}-member ring shows mule-merchant patterns, "
                f"concentrating transactions through a small number of merchants "
                f"while sharing IP subnets."
            )
        elif ring.ring_label == "UnknownSuspicious":
            parts.append(
                f"This {ring.member_count}-member cluster shows suspicious coordination "
                f"that does not match known fraud ring patterns."
            )
        else:
            parts.append(
                f"This {ring.member_count}-member cluster shows low-risk behavior "
                f"consistent with legitimate usage."
            )

        # Shared resources sentence
        shared_counts = []
        for id_type, id_list in ring.shared_identifiers.items():
            if id_list:
                shared_counts.append(f"{len(id_list)} {id_type}")
        if shared_counts:
            parts.append(
                f"Members share {', '.join(shared_counts)}, "
                f"indicating coordinated activity."
            )

        # Top risk factor sentence
        if risk_factors:
            top = risk_factors[0]
            parts.append(
                f"The strongest signal is {top['factor']} at {top['value']:.3f} "
                f"(baseline: {top['baseline']})."
            )

        return " ".join(parts)

    def enrich_classified_rings(
        self,
        classified_rings: List[ClassifiedRing],
        ring_features: List[RingFeatureVector],
    ) -> List[ClassifiedRing]:
        """Add explanations and narratives to classified rings."""
        for cr, rf in zip(classified_rings, ring_features):
            explanation = self.explain_ring(cr, rf)
            cr.risk_narrative = explanation["risk_narrative"]
            cr.explanation = explanation["risk_narrative"]
            cr.evidence["top_risk_factors"] = explanation["top_risk_factors"]
            cr.evidence["shared_identifiers"] = explanation["strongest_shared_identifiers"]
        return classified_rings

    # ------------------------------------------------------------------
    # v2: Evidence-based explanations for ConfirmedRing
    # ------------------------------------------------------------------

    def enrich_confirmed_rings(
        self, confirmed_rings: List[ConfirmedRing],
    ) -> List[ConfirmedRing]:
        """Generate explanations from structured evidence items."""
        for ring in confirmed_rings:
            ring.risk_narrative = self._narrative_from_evidence(ring)
            ring.explanation = ring.risk_narrative
            ring.evidence_summary["top_evidence"] = self._top_evidence_summary(ring)
        return confirmed_rings

    def _narrative_from_evidence(self, ring: ConfirmedRing) -> str:
        """Build plain-language narrative from the ring's evidence."""
        parts = []

        # Opening: ring type and composition
        type_label = ring.ring_label.replace("RingA_", "").replace("RingB_", "")
        parts.append(
            f"This {ring.member_count}-member {type_label} ring has "
            f"{ring.core_member_count} core members and "
            f"{ring.suspected_member_count} suspected participants."
        )

        # Evidence dimensions active
        if ring.primary_evidence_types:
            readable = [t.replace("_", " ") for t in ring.primary_evidence_types]
            parts.append(
                f"Confirmed by {ring.evidence_type_count} independent evidence "
                f"dimensions: {', '.join(readable)}."
            )

        # Top 3 unique evidence items across all members
        top_items = self._get_top_evidence_items(ring, n=3)
        for item in top_items:
            parts.append(item.description + ".")

        return " ".join(parts)

    def _top_evidence_summary(self, ring: ConfirmedRing) -> List[Dict[str, Any]]:
        """Get the top N strongest evidence items across the ring, deduplicated by dimension."""
        all_items = []
        for me in ring.members:
            if not me.is_trimmed:
                all_items.extend(me.evidence_items)
        all_items.sort(key=lambda e: e.strength, reverse=True)

        seen_dimensions = set()
        top = []
        for item in all_items:
            if item.dimension not in seen_dimensions:
                top.append({
                    "dimension": item.dimension,
                    "type": item.evidence_type,
                    "strength": round(item.strength, 3),
                    "description": item.description,
                })
                seen_dimensions.add(item.dimension)
            if len(top) >= 5:
                break
        return top

    @staticmethod
    def _get_top_evidence_items(ring: ConfirmedRing, n: int = 3):
        """Get top N evidence items by strength, deduplicated by dimension."""
        all_items = []
        for me in ring.members:
            if not me.is_trimmed:
                all_items.extend(me.evidence_items)
        all_items.sort(key=lambda e: e.strength, reverse=True)

        seen = set()
        result = []
        for item in all_items:
            if item.dimension not in seen:
                result.append(item)
                seen.add(item.dimension)
            if len(result) >= n:
                break
        return result

    def explain_member(self, member: MemberEvidence) -> List[str]:
        """Generate per-member explanation from their evidence items."""
        reasons = [
            f"Role: {member.role} (affinity: {member.affinity_score:.2f}, "
            f"{member.evidence_type_count} evidence types)"
        ]
        sorted_items = sorted(member.evidence_items, key=lambda e: e.strength, reverse=True)
        for item in sorted_items[:5]:
            reasons.append(f"[{item.evidence_type}] {item.description}")
        return reasons

    def enrich_transaction_scores(
        self,
        scores: List[TransactionScore],
        df,
        user_features,
        classified_rings: List[ClassifiedRing],
    ) -> List[TransactionScore]:
        """Add explanations to transaction scores."""
        # Build ring lookup
        user_to_ring = {}
        for cr in classified_rings:
            for member in cr.members:
                if member not in user_to_ring:
                    user_to_ring[member] = cr

        # Build user features lookup
        uf_dict = {}
        if user_features is not None and not user_features.empty:
            for _, row in user_features.iterrows():
                uid = str(row.get("user_id", ""))
                uf_dict[uid] = row.to_dict()

        for score in scores:
            user_feats = uf_dict.get(score.user_id, {})
            ring = user_to_ring.get(score.user_id)
            score.explanations = self.explain_transaction({}, user_feats, ring)

        return scores
