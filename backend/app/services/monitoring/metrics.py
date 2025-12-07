"""
Monitoring & Metrics - KPI Tracking and Drift Detection

Tracks authorization rates, fraud catch rates, latency, bias, and feature drift
to ensure model quality and compliance with SLAs.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import statistics


class MetricType(Enum):
    """Types of metrics we track."""
    AUTHORIZATION_RATE = "authorization_rate"
    FRAUD_DETECTION_RATE = "fraud_detection_rate"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_NEGATIVE_RATE = "false_negative_rate"
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    AML_HITS = "aml_hits"
    REVIEW_RATE = "review_rate"
    FEATURE_DRIFT = "feature_drift"
    BIAS_SCORE = "bias_score"


@dataclass
class Metric:
    """A single metric data point."""
    metric_type: MetricType
    value: float
    timestamp: str
    context: Dict = field(default_factory=dict)  # e.g., {"model_version": "v1.0"}


@dataclass
class LatencyBucket:
    """Histogram bucket for latency percentiles."""
    latencies: List[float] = field(default_factory=list)

    def add(self, latency_ms: float) -> None:
        self.latencies.append(latency_ms)

    def p50(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)

    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


class MetricsCollector:
    """
    Collects and aggregates metrics across all decisions.

    In production: export to Prometheus, DataDog, CloudWatch, etc.
    """

    def __init__(self, window_minutes: int = 60):
        """Initialize metrics collector."""
        self.window_minutes = window_minutes
        self.metrics: List[Metric] = []

        # Counters for current window
        self.allowed_count = 0
        self.blocked_count = 0
        self.review_count = 0
        self.total_decisions = 0

        # For fraud metrics (requires ground truth)
        self.true_positives = 0  # Fraud correctly identified
        self.false_positives = 0  # Non-fraud incorrectly flagged
        self.false_negatives = 0  # Fraud missed
        self.true_negatives = 0  # Non-fraud correctly allowed

        # Latency tracking
        self.latency_bucket = LatencyBucket()

        # Feature tracking for drift detection
        self.feature_values: Dict[str, List[float]] = defaultdict(list)

        # Bias tracking
        self.decisions_by_country: Dict[str, Dict[str, int]] = defaultdict(lambda: {"allow": 0, "block": 0})
        self.decisions_by_demographic: Dict[str, Dict[str, int]] = defaultdict(lambda: {"allow": 0, "block": 0})

    def record_decision(
        self,
        decision: str,
        risk_score: float,
        latency_ms: float,
        model_version: str,
        context: Optional[Dict] = None
    ) -> None:
        """Record a single decision."""
        context = context or {}

        self.total_decisions += 1

        if decision == "allow":
            self.allowed_count += 1
        elif decision == "block":
            self.blocked_count += 1
        elif decision == "review":
            self.review_count += 1

        # Record latency
        self.latency_bucket.add(latency_ms)

        # Store metric
        self.metrics.append(Metric(
            metric_type=MetricType.AUTHORIZATION_RATE,
            value=1.0 if decision == "allow" else 0.0,
            timestamp=datetime.utcnow().isoformat(),
            context={"model_version": model_version, **context}
        ))

        # Track bias dimensions
        if "country" in context:
            self.decisions_by_country[context["country"]][decision] += 1
        if "demographic_segment" in context:
            self.decisions_by_demographic[context["demographic_segment"]][decision] += 1

    def record_feature(self, feature_name: str, feature_value: float) -> None:
        """Record a feature value for drift detection."""
        self.feature_values[feature_name].append(feature_value)

    def record_fraud_feedback(
        self,
        decision: str,
        actual_fraud: bool
    ) -> None:
        """Record ground truth feedback (used offline for model evaluation)."""
        if decision == "block" and actual_fraud:
            self.true_positives += 1
        elif decision == "block" and not actual_fraud:
            self.false_positives += 1
        elif decision == "allow" and actual_fraud:
            self.false_negatives += 1
        elif decision == "allow" and not actual_fraud:
            self.true_negatives += 1

    def get_authorization_rate(self) -> float:
        """Get current allow rate."""
        if self.total_decisions == 0:
            return 0.0
        return self.allowed_count / self.total_decisions

    def get_fraud_detection_rate(self) -> float:
        """Get TPR (True Positive Rate) / Sensitivity."""
        positives = self.true_positives + self.false_negatives
        if positives == 0:
            return 0.0
        return self.true_positives / positives

    def get_false_positive_rate(self) -> float:
        """Get FPR (False Positive Rate)."""
        negatives = self.false_positives + self.true_negatives
        if negatives == 0:
            return 0.0
        return self.false_positives / negatives

    def get_latency_metrics(self) -> Dict[str, float]:
        """Get latency percentiles."""
        return {
            "p50_ms": self.latency_bucket.p50(),
            "p95_ms": self.latency_bucket.p95(),
            "p99_ms": self.latency_bucket.p99(),
        }

    def detect_feature_drift(self, feature_name: str, baseline_mean: float, threshold: float = 2.0) -> bool:
        """
        Detect drift in a feature using Z-score.

        Returns True if feature has drifted significantly.
        """
        if feature_name not in self.feature_values or len(self.feature_values[feature_name]) < 10:
            return False

        values = self.feature_values[feature_name]
        current_mean = statistics.mean(values[-10:])  # Last 10 values
        current_std = statistics.stdev(values[-10:]) if len(values[-10:]) > 1 else 1.0

        if current_std == 0:
            current_std = 1.0

        z_score = abs((current_mean - baseline_mean) / current_std)
        return z_score > threshold

    def detect_bias(self, dimension: str) -> Dict[str, float]:
        """
        Detect approval rate bias across a dimension (e.g., country).

        Returns approval rate by segment.
        """
        if dimension == "country":
            bias_map = self.decisions_by_country
        elif dimension == "demographic":
            bias_map = self.decisions_by_demographic
        else:
            return {}

        approval_rates = {}
        for segment, decisions in bias_map.items():
            total = decisions.get("allow", 0) + decisions.get("block", 0)
            if total > 0:
                approval_rates[segment] = decisions.get("allow", 0) / total

        return approval_rates

    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary."""
        return {
            "total_decisions": self.total_decisions,
            "allow_rate": self.get_authorization_rate(),
            "block_rate": self.blocked_count / max(self.total_decisions, 1),
            "review_rate": self.review_count / max(self.total_decisions, 1),
            "fraud_detection_rate": self.get_fraud_detection_rate(),
            "false_positive_rate": self.get_false_positive_rate(),
            "latency": self.get_latency_metrics(),
            "bias_by_country": self.detect_bias("country"),
        }


class DriftMonitor:
    """
    Monitors for data/concept drift and triggers alerts.

    Metrics tracked:
    - Feature distribution changes
    - Model performance degradation
    - Decision distribution changes
    """

    def __init__(self, baseline_version: str = "v1.0.0"):
        self.baseline_version = baseline_version
        self.drift_events: List[Dict] = []

    def check_model_performance_drift(
        self,
        current_tpr: float,
        current_fpr: float,
        baseline_tpr: float = 0.92,
        baseline_fpr: float = 0.05
    ) -> bool:
        """
        Check if model performance has degraded.

        Triggers alert if TPR drops >5% or FPR increases >2%.
        """
        tpr_degradation = baseline_tpr - current_tpr
        fpr_increase = current_fpr - baseline_fpr

        if tpr_degradation > 0.05 or fpr_increase > 0.02:
            self.drift_events.append({
                "type": "PERFORMANCE_DRIFT",
                "current_tpr": current_tpr,
                "baseline_tpr": baseline_tpr,
                "current_fpr": current_fpr,
                "baseline_fpr": baseline_fpr,
                "timestamp": datetime.utcnow().isoformat()
            })
            return True

        return False

    def get_drift_events(self) -> List[Dict]:
        """Get list of detected drift events."""
        return self.drift_events


def main():
    """Demo metrics collection."""
    collector = MetricsCollector()

    # Simulate decisions
    import random

    for i in range(100):
        decision = random.choice(["allow", "block", "review"])
        latency = random.gauss(25, 5)  # Mean 25ms, std 5ms
        risk_score = random.random()

        collector.record_decision(
            decision=decision,
            risk_score=risk_score,
            latency_ms=max(latency, 5),
            model_version="v1.0.0",
            context={"country": random.choice(["US", "EU", "ASIA"])}
        )

        # Record some fraud feedback
        if random.random() > 0.8:
            collector.record_fraud_feedback(decision, decision == "block")

    # Get summary
    summary = collector.get_summary()
    print("=" * 60)
    print("METRICS SUMMARY")
    print("=" * 60)
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v:.4f}")
        else:
            print(f"{key}: {value:.4f}")


if __name__ == "__main__":
    main()
