"""
ML-based ring classification with calibrated probabilities.

Uses GradientBoosting wrapped in CalibratedClassifierCV for
probability calibration. Falls back to RandomForest for small samples.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict
from dataclasses import fields

from .schemas import (
    RingFeatureVector,
    ClassifiedRing,
    TransactionScore,
)
from .synthetic_labels import SyntheticLabelGenerator, LABEL_NAMES
from .schemas import ConfirmedRing, EvidenceType

# Feature columns extracted from RingFeatureVector for the classifier
FEATURE_COLUMNS = [
    "size", "density",
    "mean_micro_amount_ratio", "mean_threshold_amount_ratio",
    "mean_merchant_hhi", "mean_merchant_gini",
    "mean_bin_concentration", "mean_device_sharing",
    "mean_subnet_sharing_24", "mean_subnet_sharing_16",
    "mean_geo_mismatch_rate", "mean_burstiness_cv",
    "mean_burst_window_count", "mean_inter_arrival_sec",
    "mean_txn_count", "mean_amount_mean", "mean_amount_std", "mean_amount_max",
    "shared_device_count", "shared_ip_prefix_count",
    "shared_bin_count", "shared_merchant_count", "shared_email_domain_count",
]

# Severity thresholds based on confidence and label
SEVERITY_MAP = {
    "RingA_CardTesting": {"high_conf": "CRITICAL", "low_conf": "HIGH"},
    "RingB_MuleMerchant": {"high_conf": "CRITICAL", "low_conf": "HIGH"},
    "AccountTakeover": {"high_conf": "CRITICAL", "low_conf": "HIGH"},
    "CoordinatedInfra": {"high_conf": "HIGH", "low_conf": "MEDIUM"},
    "UnknownSuspicious": {"high_conf": "HIGH", "low_conf": "MEDIUM"},
    "Legit": {"high_conf": "LOW", "low_conf": "LOW"},
}


class RingClassifier:
    """Classifies ring candidates using gradient boosting with calibrated probabilities."""

    def __init__(self, confidence_threshold: float = 0.45):
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.is_fitted = False

    def _build_feature_matrix(self, ring_features: List[RingFeatureVector]) -> np.ndarray:
        """Convert RingFeatureVector list to numpy feature matrix."""
        rows = []
        for rf in ring_features:
            row = [getattr(rf, col, 0.0) for col in FEATURE_COLUMNS]
            rows.append(row)
        X = np.array(rows, dtype=float)
        # Replace NaN/inf with 0
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return X

    def fit(self, ring_features: List[RingFeatureVector]) -> None:
        """
        Build feature matrix, generate synthetic labels, train classifier.
        Uses GradientBoosting with CalibratedClassifierCV.
        Falls back to RandomForest if too few samples.
        """
        if not ring_features:
            self.is_fitted = False
            return

        X = self._build_feature_matrix(ring_features)
        y = SyntheticLabelGenerator.label_rings(ring_features)

        n_samples = len(X)
        n_classes = len(set(y))

        try:
            if n_samples >= 10 and n_classes >= 2:
                from sklearn.ensemble import GradientBoostingClassifier
                from sklearn.calibration import CalibratedClassifierCV

                base_clf = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=4,
                    random_state=42,
                )
                # Use prefit=False with cv if enough samples
                if n_samples >= 20:
                    cv_folds = min(3, n_samples // n_classes) if n_classes > 1 else 2
                    cv_folds = max(2, cv_folds)
                    self.model = CalibratedClassifierCV(
                        base_clf, method="isotonic", cv=cv_folds
                    )
                else:
                    # Not enough for cross-validation, train directly
                    base_clf.fit(X, y)
                    self.model = base_clf
                    self.is_fitted = True
                    return

                self.model.fit(X, y)
                self.is_fitted = True
            elif n_samples >= 3 and n_classes >= 2:
                from sklearn.ensemble import RandomForestClassifier

                self.model = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=3,
                    random_state=42,
                )
                self.model.fit(X, y)
                self.is_fitted = True
            else:
                # Too few samples for ML, use rule-based labels directly
                self.is_fitted = False
        except Exception:
            self.is_fitted = False

    def predict(
        self, ring_features: List[RingFeatureVector]
    ) -> List[Tuple[str, float]]:
        """
        Returns (label, confidence) per ring.
        If max(predict_proba) < threshold -> UnknownSuspicious.
        """
        if not ring_features:
            return []

        # Fallback to synthetic labels if model not fitted
        if not self.is_fitted or self.model is None:
            labels = SyntheticLabelGenerator.label_rings(ring_features)
            return [
                (LABEL_NAMES.get(int(lbl), "UnknownSuspicious"), 0.5)
                for lbl in labels
            ]

        X = self._build_feature_matrix(ring_features)

        try:
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)
                results = []
                for i in range(len(X)):
                    max_prob = float(np.max(proba[i]))
                    pred_class = int(self.model.classes_[np.argmax(proba[i])])

                    if max_prob < self.confidence_threshold:
                        results.append(("UnknownSuspicious", max_prob))
                    else:
                        label_name = LABEL_NAMES.get(pred_class, "UnknownSuspicious")
                        results.append((label_name, max_prob))
                return results
            else:
                preds = self.model.predict(X)
                return [
                    (LABEL_NAMES.get(int(p), "UnknownSuspicious"), 0.5)
                    for p in preds
                ]
        except Exception:
            labels = SyntheticLabelGenerator.label_rings(ring_features)
            return [
                (LABEL_NAMES.get(int(lbl), "UnknownSuspicious"), 0.5)
                for lbl in labels
            ]

    def classify_rings(
        self,
        ring_candidates: list,
        ring_features: List[RingFeatureVector],
        predictions: List[Tuple[str, float]],
    ) -> List[ClassifiedRing]:
        """Assemble ClassifiedRing objects from candidates + predictions."""
        classified = []
        for rc, rf, (label, confidence) in zip(ring_candidates, ring_features, predictions):
            severity = self._compute_severity(label, confidence, rf)
            risk_score = self._compute_ring_risk_score(label, confidence, rf)

            # Build human-readable ring name
            ring_name = self._generate_ring_name(label, rc)
            ring_type = label.upper().replace("RINGA_", "").replace("RINGB_", "")

            # Shared identifiers dict
            shared_ids = {}
            if rc.shared_devices:
                shared_ids["devices"] = rc.shared_devices
            if rc.shared_ip_prefixes:
                shared_ids["ip_prefixes"] = rc.shared_ip_prefixes
            if rc.shared_bins:
                shared_ids["card_bins"] = rc.shared_bins
            if rc.shared_merchants:
                shared_ids["merchants"] = rc.shared_merchants
            if rc.shared_email_domains:
                shared_ids["email_domains"] = rc.shared_email_domains

            # Evidence
            evidence = {
                "density": rc.density,
                "shared_device_count": rf.shared_device_count,
                "shared_ip_prefix_count": rf.shared_ip_prefix_count,
                "shared_bin_count": rf.shared_bin_count,
                "mean_device_sharing": round(rf.mean_device_sharing, 3),
                "mean_burstiness_cv": round(rf.mean_burstiness_cv, 3),
                "mean_micro_amount_ratio": round(rf.mean_micro_amount_ratio, 3),
                "mean_merchant_hhi": round(rf.mean_merchant_hhi, 3),
            }

            # Recommendations
            recommendations = self._generate_recommendations(label, severity)

            classified.append(ClassifiedRing(
                ring_id=rc.ring_id,
                ring_label=label,
                confidence=round(confidence, 3),
                severity=severity,
                members=rc.member_user_ids,
                member_count=rc.size,
                risk_score=round(risk_score, 3),
                shared_identifiers=shared_ids,
                risk_narrative="",  # Filled by explainability module
                recommendations=recommendations,
                evidence=evidence,
                ring_type=ring_type,
                ring_name=ring_name,
                detection_method=rc.detection_method,
                explanation="",  # Filled by explainability module
                sample_transactions=[],
            ))

        return classified

    def score_transactions(
        self,
        df: pd.DataFrame,
        classified_rings: List[ClassifiedRing],
        user_features: Optional[pd.DataFrame] = None,
    ) -> List[TransactionScore]:
        """
        Per-transaction risk scoring.
        risk_score (0-100) = ring_risk * 0.6 + user_anomaly * 0.3 + isolation * 0.1
        """
        # Build ring membership lookup
        user_to_ring = {}
        ring_risk_map = {}
        for cr in classified_rings:
            ring_risk_map[cr.ring_id] = cr.risk_score
            for member in cr.members:
                if member not in user_to_ring:
                    user_to_ring[member] = cr

        scores = []
        for _, row in df.iterrows():
            tx_id = str(row.get("transaction_id", row.get("id", "")))
            user_id = str(row.get("user_id", ""))

            ring = user_to_ring.get(user_id)

            # Ring risk component (0-100)
            ring_risk = ring.risk_score * 100 if ring else 0.0

            # User anomaly component (0-100)
            user_anomaly = 0.0
            if user_features is not None and not user_features.empty and user_id:
                user_row = user_features[user_features["user_id"] == user_id]
                if not user_row.empty:
                    ur = user_row.iloc[0]
                    anomaly_signals = [
                        float(ur.get("device_sharing_score", 0)) * 30,
                        float(ur.get("burstiness_cv", 0)) * 20,
                        float(ur.get("micro_amount_ratio", 0)) * 20,
                        float(ur.get("subnet_sharing_score_24", 0)) * 15,
                        float(ur.get("geo_mismatch_rate", 0)) * 15,
                    ]
                    user_anomaly = min(100.0, sum(anomaly_signals))

            # Isolation component (simple heuristic)
            isolation = 10.0 if ring else 0.0

            final_score = ring_risk * 0.6 + user_anomaly * 0.3 + isolation * 0.1
            final_score = min(100.0, max(0.0, final_score))

            label = ring.ring_label if ring else "Legit"
            confidence = ring.confidence if ring else 0.9
            ring_id = ring.ring_id if ring else ""

            scores.append(TransactionScore(
                transaction_id=tx_id,
                user_id=user_id,
                risk_score=round(final_score, 2),
                label=label,
                confidence=round(confidence, 3),
                ring_id=ring_id,
                explanations=[],  # Filled by explainability
            ))

        return scores

    # ---- Private helpers ----

    @staticmethod
    def _compute_severity(label: str, confidence: float, rf: RingFeatureVector) -> str:
        """Determine severity from label + confidence."""
        conf_key = "high_conf" if confidence >= 0.6 else "low_conf"
        label_map = SEVERITY_MAP.get(label, SEVERITY_MAP["UnknownSuspicious"])
        return label_map[conf_key]

    @staticmethod
    def _compute_ring_risk_score(
        label: str, confidence: float, rf: RingFeatureVector
    ) -> float:
        """Compute 0-1 risk score for a ring."""
        base = 0.0
        if label == "RingA_CardTesting":
            base = 0.8
        elif label == "RingB_MuleMerchant":
            base = 0.75
        elif label == "UnknownSuspicious":
            base = 0.5
        else:  # Legit
            base = 0.1

        # Adjust by confidence and features
        sharing_boost = min(0.15, (rf.shared_device_count + rf.shared_ip_prefix_count) * 0.03)
        size_boost = min(0.1, rf.size * 0.01)

        return min(1.0, base * confidence + sharing_boost + size_boost)

    @staticmethod
    def _generate_ring_name(label: str, rc) -> str:
        """Generate human-readable ring name."""
        if label == "RingA_CardTesting":
            return f"Card Testing Ring ({rc.size} members)"
        elif label == "RingB_MuleMerchant":
            return f"Mule Merchant Ring ({rc.size} members)"
        elif label == "UnknownSuspicious":
            return f"Suspicious Cluster ({rc.size} members)"
        else:
            return f"Low-Risk Cluster ({rc.size} members)"

    @staticmethod
    def _generate_recommendations(label: str, severity: str) -> List[str]:
        """Generate actionable recommendations based on ring classification."""
        recs = []
        if label == "RingA_CardTesting":
            recs = [
                "Block all ring member accounts pending investigation",
                "Review micro-transactions for card testing patterns",
                "Check shared devices for automated testing tools",
                "Implement velocity limits on small-amount transactions",
            ]
        elif label == "RingB_MuleMerchant":
            recs = [
                "Freeze transactions to concentrated merchants",
                "Investigate shared IP subnets for proxy usage",
                "Review merchant accounts for collusion patterns",
                "Implement merchant diversity requirements",
            ]
        elif label == "AccountTakeover":
            recs = [
                "Force password reset on all ring member accounts",
                "Review login failure patterns and IP origins",
                "Check for compromised credentials on dark web",
                "Enable mandatory 2FA for affected accounts",
            ]
        elif label == "CoordinatedInfra":
            recs = [
                "Investigate shared device fingerprints for emulator usage",
                "Check IP ranges for VPN/proxy/datacenter origins",
                "Review account creation patterns for automation",
                "Implement device trust scoring",
            ]
        elif label == "UnknownSuspicious":
            recs = [
                "Flag accounts for enhanced monitoring",
                "Request additional verification for high-value transactions",
                "Monitor for evolving patterns over next 30 days",
            ]
        else:
            recs = [
                "Continue standard monitoring",
                "No immediate action required",
            ]

        if severity == "CRITICAL":
            recs.insert(0, "IMMEDIATE: Escalate to fraud operations team")

        return recs

    # ------------------------------------------------------------------
    # Evidence-based classification for v2 ConfirmedRing
    # ------------------------------------------------------------------

    def classify_confirmed_rings(
        self, confirmed_rings: List[ConfirmedRing],
    ) -> List[ConfirmedRing]:
        """
        Classify confirmed rings using evidence patterns.

        Type-specific detection:
        - ATO: dominant ACCOUNT_ANOMALY evidence
        - Mule: dominant FINANCIAL_FLOW + MERCHANT_PATTERN
        - CardTesting: dominant BEHAVIORAL + TEMPORAL
        - CoordinatedInfra: dominant INFRASTRUCTURE
        - UnknownSuspicious: no dominant pattern
        """
        from collections import defaultdict

        for ring in confirmed_rings:
            strengths = self._aggregate_evidence_strengths(ring)
            ring.ring_label, ring.ring_type = self._type_from_evidence(strengths)
            ring.severity = self._severity_from_evidence(ring)
            ring.risk_score = self._risk_score_from_evidence(ring, strengths)
            ring.ring_name = self._name_from_type(ring)
            ring.recommendations = self._generate_recommendations(
                ring.ring_label, ring.severity
            )

        return confirmed_rings

    @staticmethod
    def _aggregate_evidence_strengths(
        ring: ConfirmedRing,
    ) -> Dict[str, float]:
        """Aggregate mean evidence strength per type across all ring members."""
        from collections import defaultdict
        type_strengths: Dict[str, List[float]] = defaultdict(list)
        for me in ring.members:
            if me.is_trimmed:
                continue
            for ei in me.evidence_items:
                type_strengths[ei.evidence_type].append(ei.strength)
        return {
            t: float(np.mean(strengths))
            for t, strengths in type_strengths.items()
        }

    @staticmethod
    def _type_from_evidence(
        strengths: Dict[str, float],
    ) -> Tuple[str, str]:
        """Determine ring type from evidence pattern."""
        ato = strengths.get(EvidenceType.ACCOUNT_ANOMALY.value, 0)
        infra = strengths.get(EvidenceType.INFRASTRUCTURE.value, 0)
        mule = (
            strengths.get(EvidenceType.FINANCIAL_FLOW.value, 0) * 0.5
            + strengths.get(EvidenceType.MERCHANT_PATTERN.value, 0) * 0.5
        )
        card_test = (
            strengths.get(EvidenceType.BEHAVIORAL.value, 0) * 0.5
            + strengths.get(EvidenceType.TEMPORAL.value, 0) * 0.5
        )

        scores = {
            "AccountTakeover": ato,
            "RingA_CardTesting": card_test,
            "RingB_MuleMerchant": mule,
            "CoordinatedInfra": infra,
        }

        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]

        # Require minimum strength for a specific type
        if best_score < 0.25:
            return "UnknownSuspicious", "UNKNOWN_SUSPICIOUS"

        type_map = {
            "AccountTakeover": "ACCOUNT_TAKEOVER",
            "RingA_CardTesting": "CARD_TESTING",
            "RingB_MuleMerchant": "MULE_MERCHANT",
            "CoordinatedInfra": "COORDINATED_INFRA",
        }
        return best_label, type_map[best_label]

    @staticmethod
    def _severity_from_evidence(ring: ConfirmedRing) -> str:
        """Evidence-based severity."""
        if ring.confidence >= 0.65 and ring.core_member_count >= 4:
            if ring.ring_label in ("RingA_CardTesting", "RingB_MuleMerchant", "AccountTakeover"):
                return "CRITICAL"
            return "HIGH"
        elif ring.confidence >= 0.45 and ring.evidence_type_count >= 2:
            return "HIGH" if ring.ring_label != "UnknownSuspicious" else "MEDIUM"
        else:
            return "MEDIUM"

    @staticmethod
    def _risk_score_from_evidence(
        ring: ConfirmedRing, strengths: Dict[str, float],
    ) -> float:
        """Compute 0-1 risk score from evidence strengths and ring composition."""
        base_map = {
            "RingA_CardTesting": 0.8,
            "RingB_MuleMerchant": 0.75,
            "AccountTakeover": 0.85,
            "CoordinatedInfra": 0.6,
            "UnknownSuspicious": 0.5,
        }
        base = base_map.get(ring.ring_label, 0.4)
        evidence_avg = float(np.mean(list(strengths.values()))) if strengths else 0.0
        core_ratio = ring.core_member_count / max(ring.member_count, 1)
        return min(1.0, round(base * ring.confidence + evidence_avg * 0.15 + core_ratio * 0.1, 3))

    @staticmethod
    def _name_from_type(ring: ConfirmedRing) -> str:
        """Human-readable ring name."""
        type_names = {
            "RingA_CardTesting": "Card Testing Ring",
            "RingB_MuleMerchant": "Mule Merchant Ring",
            "AccountTakeover": "Account Takeover Ring",
            "CoordinatedInfra": "Coordinated Infrastructure Ring",
            "UnknownSuspicious": "Suspicious Cluster",
        }
        name = type_names.get(ring.ring_label, "Suspicious Cluster")
        return f"{name} ({ring.member_count} members, {ring.core_member_count} core)"
