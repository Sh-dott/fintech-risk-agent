"""
Real-Time Risk & Insights Agent - Decision Engine

Orchestrates transaction scoring, risk assessment, and real-time decision-making
with <100ms end-to-end latency and compliance logging.
"""

import time
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict


class DecisionType(Enum):
    """Authorization decision types."""
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class RiskLevel(Enum):
    """Risk classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DecisionReason:
    """Single reason/signal contributing to risk score."""
    signal_id: str
    signal_name: str
    weight: float  # Contribution to risk score
    value: Any  # Actual observed value
    threshold: Optional[float] = None
    category: str = "unknown"  # e.g., "velocity", "device", "behavior"


@dataclass
class RiskDecision:
    """Complete risk decision output."""
    decision: DecisionType
    risk_score: float  # [0.0, 1.0]
    risk_level: RiskLevel
    reasons: List[DecisionReason]
    reason_codes: List[str]  # Human-readable codes (e.g., "HIGH_VELOCITY")
    next_actions: List[str]  # Recommended escalations (e.g., "SCA_STEP_UP")
    compliance_log_id: str  # Audit trail reference
    latency_ms: float
    timestamp: str
    model_version: str
    explanation: str  # Researcher-friendly summary


class RiskDecisionEngine:
    """
    Main orchestrator for real-time risk scoring and decision-making.

    Flow:
    1. Enrich transaction with features (feature_store, graph)
    2. Score with ML model + rules engine
    3. Apply decision policy
    4. Log compliance & metrics
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize decision engine with configuration."""
        self.config = self._load_config(config_path)
        self.model_version = "v1.0.0"

        # Thresholds for decision making
        self.high_risk_threshold = self.config.get("high_risk_threshold", 0.8)
        self.low_risk_threshold = self.config.get("low_risk_threshold", 0.3)
        self.max_latency_ms = self.config.get("max_latency_ms", 100)

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML or return defaults."""
        if config_path:
            try:
                import yaml
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

        # Default configuration
        return {
            "high_risk_threshold": 0.8,
            "low_risk_threshold": 0.3,
            "max_latency_ms": 100,
            "enable_aml_screening": True,
            "enable_graph_analysis": True,
            "model_weights": {
                "ml_score": 0.7,
                "rules_score": 0.3
            }
        }

    def score_transaction(
        self,
        transaction: Dict[str, Any],
        context: Dict[str, Any],
        user_profile: Optional[Dict] = None,
        device_profile: Optional[Dict] = None,
        merchant_profile: Optional[Dict] = None
    ) -> RiskDecision:
        """
        Score a single transaction in real-time.

        Args:
            transaction: Transaction details (id, amount, currency, merchant_id, user_id)
            context: Additional context (device_id, ip_address, user_country, timestamp)
            user_profile: User KYC/KYB and historical behavior
            device_profile: Device reputation and binding history
            merchant_profile: Merchant details, MCC, chargeback history

        Returns:
            RiskDecision with decision, score, reasons, and next actions
        """
        start_time = time.time()
        compliance_log_id = f"clog_{uuid.uuid4().hex[:8]}"

        try:
            # 1. Enrich features (simulated)
            enriched_features = self._enrich_features(
                transaction, context, user_profile, device_profile, merchant_profile
            )

            # 2. Score with ML + Rules
            ml_score, ml_reasons = self._score_ml_model(enriched_features)
            rules_score, rules_reasons = self._evaluate_rules(enriched_features)

            # 3. Combine scores
            combined_score, all_reasons = self._combine_scores(
                ml_score, ml_reasons, rules_score, rules_reasons
            )

            # 4. Check AML/Sanctions (if enabled)
            aml_reasons = []
            if self.config.get("enable_aml_screening"):
                aml_score, aml_reasons = self._check_aml(enriched_features)
                combined_score = max(combined_score, aml_score)
                all_reasons.extend(aml_reasons)

            # 5. Graph analysis for rings/mules (if enabled)
            graph_reasons = []
            if self.config.get("enable_graph_analysis"):
                graph_score, graph_reasons = self._analyze_entity_graph(enriched_features)
                combined_score = max(combined_score, graph_score)
                all_reasons.extend(graph_reasons)

            # 6. Apply decision policy
            decision, risk_level, reason_codes, next_actions = self._apply_decision_policy(
                combined_score, all_reasons, enriched_features
            )

            # 7. Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # 8. Check latency SLA
            if latency_ms > self.max_latency_ms:
                print(f"Warning: Decision latency {latency_ms:.1f}ms exceeds SLA of {self.max_latency_ms}ms")

            # Create decision object
            decision_obj = RiskDecision(
                decision=decision,
                risk_score=combined_score,
                risk_level=risk_level,
                reasons=all_reasons,
                reason_codes=reason_codes,
                next_actions=next_actions,
                compliance_log_id=compliance_log_id,
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat(),
                model_version=self.model_version,
                explanation=self._generate_explanation(all_reasons, reason_codes)
            )

            # 9. Log compliance & metrics
            self._log_compliance(decision_obj, transaction, context)

            return decision_obj

        except Exception as e:
            print(f"Error in decision engine: {e}")
            # Fail-safe: escalate to review
            return RiskDecision(
                decision=DecisionType.REVIEW,
                risk_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                reasons=[],
                reason_codes=["ENGINE_ERROR"],
                next_actions=["MANUAL_REVIEW"],
                compliance_log_id=compliance_log_id,
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow().isoformat(),
                model_version=self.model_version,
                explanation=f"Decision engine error: {str(e)}"
            )

    def _enrich_features(
        self,
        transaction: Dict,
        context: Dict,
        user_profile: Optional[Dict],
        device_profile: Optional[Dict],
        merchant_profile: Optional[Dict]
    ) -> Dict[str, Any]:
        """Enrich transaction with features from store, graph, and profiles."""
        enriched = {
            "transaction": transaction,
            "context": context,
            "user_profile": user_profile or {},
            "device_profile": device_profile or {},
            "merchant_profile": merchant_profile or {},
        }

        # Simulated feature store lookups
        enriched["velocity_features"] = {
            "user_txn_count_1h": 2,
            "user_txn_amount_24h": 450.00,
            "device_txn_count_1h": 1,
            "merchant_txn_count_1h": 15
        }

        enriched["behavior_features"] = {
            "avg_transaction_amount": 75.00,
            "avg_time_between_txns_hours": 12.5,
            "account_age_days": 365,
            "device_binding_age_days": 30
        }

        enriched["device_features"] = {
            "device_reputation": 0.95,
            "ip_reputation": 0.92,
            "is_vpn": False,
            "is_proxy": False,
            "device_mismatch": False
        }

        return enriched

    def _score_ml_model(self, features: Dict[str, Any]) -> Tuple[float, List[DecisionReason]]:
        """Score with ML model (DNN/GBDT). Simulated for demo."""
        # Simulated ML model inference
        score = 0.15  # Low fraud risk

        reasons = [
            DecisionReason(
                signal_id="ml_velocity_ok",
                signal_name="Normal Velocity",
                weight=0.05,
                value=2,
                threshold=5,
                category="velocity"
            ),
            DecisionReason(
                signal_id="ml_device_trusted",
                signal_name="Trusted Device",
                weight=0.03,
                value=0.95,
                threshold=0.80,
                category="device"
            ),
            DecisionReason(
                signal_id="ml_behavior_normal",
                signal_name="Normal Behavior Pattern",
                weight=0.07,
                value=1.0,
                threshold=0.5,
                category="behavior"
            )
        ]

        return score, reasons

    def _evaluate_rules(self, features: Dict[str, Any]) -> Tuple[float, List[DecisionReason]]:
        """Evaluate business rules and thresholds."""
        score = 0.1
        reasons = [
            DecisionReason(
                signal_id="rule_amount_under_limit",
                signal_name="Amount Under Limit",
                weight=0.05,
                value=100.00,
                threshold=5000.00,
                category="rules"
            ),
            DecisionReason(
                signal_id="rule_merchant_tier_good",
                signal_name="Good Merchant Tier",
                weight=0.05,
                value="tier_1",
                threshold=None,
                category="merchant"
            )
        ]

        return score, reasons

    def _check_aml(self, features: Dict[str, Any]) -> Tuple[float, List[DecisionReason]]:
        """Check AML/sanctions lists. Returns high score if match found."""
        # Simulated AML check
        score = 0.0
        reasons = []

        # In production: check PEP lists, sanctions databases, etc.
        # For now, assume clean
        reasons.append(DecisionReason(
            signal_id="aml_sanctions_clear",
            signal_name="No Sanctions Hit",
            weight=0.0,
            value="CLEAR",
            category="aml"
        ))

        return score, reasons

    def _analyze_entity_graph(self, features: Dict[str, Any]) -> Tuple[float, List[DecisionReason]]:
        """Analyze entity graph for fraud rings, mule networks, etc."""
        # Simulated graph analysis
        score = 0.0
        reasons = [
            DecisionReason(
                signal_id="graph_no_mule_pattern",
                signal_name="No Mule Network Detected",
                weight=0.0,
                value="isolated",
                category="graph"
            )
        ]

        return score, reasons

    def _combine_scores(
        self,
        ml_score: float,
        ml_reasons: List[DecisionReason],
        rules_score: float,
        rules_reasons: List[DecisionReason]
    ) -> Tuple[float, List[DecisionReason]]:
        """Combine ML and rules scores with configured weights."""
        weights = self.config.get("model_weights", {"ml_score": 0.7, "rules_score": 0.3})

        combined_score = (
            weights["ml_score"] * ml_score +
            weights["rules_score"] * rules_score
        )

        all_reasons = ml_reasons + rules_reasons
        all_reasons.sort(key=lambda x: x.weight, reverse=True)

        return combined_score, all_reasons

    def _apply_decision_policy(
        self,
        risk_score: float,
        reasons: List[DecisionReason],
        features: Dict
    ) -> Tuple[DecisionType, RiskLevel, List[str], List[str]]:
        """Apply decision policy: high-risk → block, low-risk → allow, else → review."""

        reason_codes = []
        next_actions = []

        # Determine risk level
        if risk_score >= self.high_risk_threshold:
            decision = DecisionType.BLOCK
            risk_level = RiskLevel.HIGH
            reason_codes = ["HIGH_RISK_SCORE", self._extract_reason_codes(reasons)[:3]]
            next_actions = ["BLOCK", "ESCALATE_TO_COMPLIANCE", "STORE_FOR_INVESTIGATION"]
        elif risk_score <= self.low_risk_threshold:
            decision = DecisionType.ALLOW
            risk_level = RiskLevel.LOW
            reason_codes = ["LOW_RISK"]
            next_actions = ["APPROVE", "MONITOR"]
        else:
            decision = DecisionType.REVIEW
            risk_level = RiskLevel.MEDIUM
            reason_codes = ["MEDIUM_RISK", self._extract_reason_codes(reasons)[:2]]
            next_actions = ["MANUAL_REVIEW", "REQUEST_ADDITIONAL_VERIFICATION"]

        # Check for step-up/additional auth
        if features.get("context", {}).get("user_country") != "US":
            next_actions.append("SCA_STEP_UP")  # PSD2 requirement for cross-border

        # Flatten reason codes
        reason_codes = [code for codes in reason_codes for code in (codes if isinstance(codes, list) else [codes])]

        return decision, risk_level, reason_codes, next_actions

    def _extract_reason_codes(self, reasons: List[DecisionReason], top_n: int = 3) -> List[str]:
        """Extract top reason codes from reasons list."""
        codes = []
        for reason in reasons[:top_n]:
            code = reason.signal_name.upper().replace(" ", "_")
            codes.append(code)
        return codes

    def _generate_explanation(self, reasons: List[DecisionReason], reason_codes: List[str]) -> str:
        """Generate researcher-friendly explanation."""
        top_reasons = reasons[:3] if reasons else []

        explanation = f"Decision based on {len(reason_codes)} key signals: "
        explanation += "; ".join([f"{r.signal_name} ({r.weight:.2f})" for r in top_reasons])

        return explanation

    def _log_compliance(
        self,
        decision: RiskDecision,
        transaction: Dict,
        context: Dict
    ) -> None:
        """Log decision to compliance/audit trail (non-blocking)."""
        log_entry = {
            "compliance_log_id": decision.compliance_log_id,
            "timestamp": decision.timestamp,
            "transaction_id": transaction.get("id"),
            "decision": decision.decision.value,
            "risk_score": decision.risk_score,
            "reason_codes": decision.reason_codes,
            "latency_ms": decision.latency_ms,
            "user_id": transaction.get("user_id"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency")
        }

        # In production: send to secure audit log, data lake, etc.
        # For now, just print
        # print(f"[COMPLIANCE LOG] {json.dumps(log_entry, indent=2)}")


def main():
    """Demo the decision engine."""
    engine = RiskDecisionEngine()

    # Example transaction
    decision = engine.score_transaction(
        transaction={
            "id": "txn_abc123",
            "amount": 100.00,
            "currency": "USD",
            "merchant_id": "mch_456",
            "user_id": "usr_789"
        },
        context={
            "device_id": "dev_xyz",
            "ip_address": "192.168.1.1",
            "user_country": "US",
            "timestamp": datetime.utcnow().isoformat()
        },
        user_profile={
            "account_age_days": 365,
            "kyc_verified": True,
            "kyc_risk_level": "low"
        },
        device_profile={
            "device_age_days": 30,
            "is_trusted": True
        },
        merchant_profile={
            "merchant_name": "Example Merchant",
            "mcc": "5411",
            "chargeback_rate": 0.001,
            "risk_tier": "tier_1"
        }
    )

    print("\n" + "=" * 80)
    print("RISK DECISION RESULT")
    print("=" * 80)
    print(f"Decision: {decision.decision.value.upper()}")
    print(f"Risk Score: {decision.risk_score:.4f} ({decision.risk_level.value.upper()})")
    print(f"Reason Codes: {', '.join(decision.reason_codes)}")
    print(f"Next Actions: {', '.join(decision.next_actions)}")
    print(f"Explanation: {decision.explanation}")
    print(f"Latency: {decision.latency_ms:.2f}ms")
    print(f"Compliance Log ID: {decision.compliance_log_id}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
