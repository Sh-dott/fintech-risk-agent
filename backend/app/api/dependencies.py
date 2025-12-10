"""
Dependency injection and metrics tracking for Risk Decision Engine API
"""

from datetime import datetime
from app.core.decision_engine import RiskDecisionEngine

# Initialize decision engine (lazy loaded to avoid startup delays)
engine = None

def get_engine():
    """Get or initialize the decision engine lazily."""
    global engine
    if engine is None:
        try:
            engine = RiskDecisionEngine(config_path="backend/config/model_config.yaml")
        except Exception as e:
            print(f"[WARNING] Could not load RiskDecisionEngine: {e}")
            engine = None
    return engine


class APIMetrics:
    """Track API metrics for monitoring and analytics."""

    def __init__(self):
        self.total_requests = 0
        self.total_decisions = 0
        self.allow_count = 0
        self.block_count = 0
        self.review_count = 0
        self.risk_scores = []
        self.latencies = []
        self.start_time = datetime.utcnow()
        self.transaction_history = {}

    def record_decision(self, decision_str: str, risk_score: float, latency: float):
        """Record a decision result and metrics."""
        self.total_requests += 1
        self.total_decisions += 1
        self.risk_scores.append(risk_score)
        self.latencies.append(latency)

        if decision_str == "allow":
            self.allow_count += 1
        elif decision_str == "block":
            self.block_count += 1
        elif decision_str == "review":
            self.review_count += 1

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def get_avg_risk_score(self) -> float:
        """Get average risk score."""
        return sum(self.risk_scores) / len(self.risk_scores) if self.risk_scores else 0.0

    def get_p95_latency(self) -> float:
        """Get 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    def get_approval_rate(self) -> float:
        """Get approval rate percentage."""
        total = self.total_decisions
        return (self.allow_count / total * 100) if total > 0 else 0.0


# Global metrics instance
metrics = APIMetrics()
