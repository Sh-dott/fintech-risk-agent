"""
AI-Powered Insights Engine

Analyzes transaction data with machine learning to provide:
- Business intelligence & trends
- Fraud pattern insights
- User behavior analysis
- Risk mitigation recommendations
- Market intelligence
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from collections import Counter
import statistics
from datetime import datetime, timedelta


@dataclass
class TransactionInsight:
    """Business insight from transaction data."""
    title: str
    description: str
    severity: str  # "info", "warning", "critical"
    impact: str  # Business impact
    recommendation: str  # What to do
    metrics: Dict[str, Any]


class AIInsightsEngine:
    """Generate AI/ML-powered business insights from transaction data."""

    def __init__(self):
        self.transactions = []
        self.insights = []

    def load_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        """Load transaction data for analysis."""
        self.transactions = transactions

    def analyze(self) -> List[TransactionInsight]:
        """Run all analyses and generate insights."""
        self.insights = []

        if not self.transactions:
            return self.insights

        # Run different analysis types
        self._analyze_fraud_patterns()
        self._analyze_spending_behavior()
        self._analyze_risk_distribution()
        self._analyze_merchant_patterns()
        self._analyze_user_patterns()
        self._analyze_geographic_patterns()
        self._analyze_velocity_patterns()
        self._analyze_recommendations()

        return self.insights

    def _analyze_fraud_patterns(self) -> None:
        """Detect and analyze fraud patterns."""
        high_risk = [t for t in self.transactions if t.get("risk_score", 0) > 0.7]
        blocked = [t for t in self.transactions if t.get("decision") == "block"]

        if high_risk:
            fraud_rate = len(high_risk) / len(self.transactions) * 100

            if fraud_rate > 10:
                self.insights.append(TransactionInsight(
                    title="High Fraud Alert",
                    description=f"Detected {len(high_risk)} high-risk transactions ({fraud_rate:.1f}% of total)",
                    severity="critical",
                    impact="Significant fraud risk detected. Immediate review recommended.",
                    recommendation="Enable enhanced verification for high-risk transactions. Review merchant whitelisting.",
                    metrics={
                        "high_risk_count": len(high_risk),
                        "fraud_rate_percent": fraud_rate,
                        "avg_fraud_amount": sum(t.get("amount", 0) for t in high_risk) / len(high_risk) if high_risk else 0
                    }
                ))
            elif fraud_rate > 5:
                self.insights.append(TransactionInsight(
                    title="Moderate Fraud Risk",
                    description=f"Detected {len(high_risk)} high-risk transactions ({fraud_rate:.1f}%)",
                    severity="warning",
                    impact="Elevated fraud risk requires monitoring.",
                    recommendation="Increase monitoring frequency. Review blocked transactions for patterns.",
                    metrics={
                        "high_risk_count": len(high_risk),
                        "fraud_rate_percent": fraud_rate
                    }
                ))

        if blocked:
            self.insights.append(TransactionInsight(
                title="Blocked Transactions Summary",
                description=f"Blocked {len(blocked)} transactions",
                severity="info",
                impact="These transactions were rejected by risk engine.",
                recommendation="Review blocked transactions quarterly. Adjust thresholds if too many legitimate transactions blocked.",
                metrics={
                    "blocked_count": len(blocked),
                    "total_blocked_amount": sum(t.get("amount", 0) for t in blocked),
                    "avg_blocked_amount": sum(t.get("amount", 0) for t in blocked) / len(blocked) if blocked else 0
                }
            ))

    def _analyze_spending_behavior(self) -> None:
        """Analyze spending patterns and outliers."""
        if not self.transactions:
            return

        amounts = [t.get("amount", 0) for t in self.transactions]

        if amounts:
            avg_amount = statistics.mean(amounts)
            median_amount = statistics.median(amounts)
            max_amount = max(amounts)

            # Find unusual spending
            threshold = avg_amount * 2.5
            unusual = [t for t in self.transactions if t.get("amount", 0) > threshold]

            if unusual:
                self.insights.append(TransactionInsight(
                    title="Unusual Spending Detected",
                    description=f"{len(unusual)} transactions exceed normal spending patterns",
                    severity="warning",
                    impact="Potential fraud or legitimate high-value purchases.",
                    recommendation="Review high-value transactions. Consider requiring additional verification.",
                    metrics={
                        "unusual_count": len(unusual),
                        "threshold_amount": threshold,
                        "avg_transaction": avg_amount,
                        "median_transaction": median_amount,
                        "max_transaction": max_amount
                    }
                ))

    def _analyze_risk_distribution(self) -> None:
        """Analyze distribution of risk scores."""
        decisions = Counter(t.get("decision") for t in self.transactions if t.get("decision"))

        allow_pct = (decisions.get("allow", 0) / len(self.transactions) * 100) if self.transactions else 0
        block_pct = (decisions.get("block", 0) / len(self.transactions) * 100) if self.transactions else 0
        review_pct = (decisions.get("review", 0) / len(self.transactions) * 100) if self.transactions else 0

        self.insights.append(TransactionInsight(
            title="Decision Distribution",
            description=f"Approval rate: {allow_pct:.1f}%, Rejection: {block_pct:.1f}%, Review: {review_pct:.1f}%",
            severity="info",
            impact="Shows overall system risk posture.",
            recommendation="If approval rate < 85%, may be too strict. If > 95%, may be too lenient.",
            metrics={
                "approval_rate": allow_pct,
                "block_rate": block_pct,
                "review_rate": review_pct,
                "total_transactions": len(self.transactions)
            }
        ))

    def _analyze_merchant_patterns(self) -> None:
        """Analyze transaction patterns by merchant."""
        merchant_data = {}

        for t in self.transactions:
            merchant_id = t.get("merchant_id", "unknown")
            if merchant_id not in merchant_data:
                merchant_data[merchant_id] = {
                    "count": 0,
                    "total_amount": 0,
                    "high_risk_count": 0,
                    "blocked_count": 0
                }

            merchant_data[merchant_id]["count"] += 1
            merchant_data[merchant_id]["total_amount"] += t.get("amount", 0)

            if t.get("risk_score", 0) > 0.7:
                merchant_data[merchant_id]["high_risk_count"] += 1
            if t.get("decision") == "block":
                merchant_data[merchant_id]["blocked_count"] += 1

        # Find problematic merchants
        problematic = {
            m: d for m, d in merchant_data.items()
            if d["high_risk_count"] / d["count"] > 0.3  # >30% high risk
        }

        if problematic:
            worst_merchant = max(problematic.items(),
                                key=lambda x: x[1]["high_risk_count"] / x[1]["count"])

            self.insights.append(TransactionInsight(
                title="High-Risk Merchant Detected",
                description=f"Merchant {worst_merchant[0]} has {worst_merchant[1]['high_risk_count']} high-risk transactions",
                severity="warning",
                impact="Merchant may be associated with fraudulent activity.",
                recommendation="Flag merchant for review. Consider temporary suspension or enhanced verification.",
                metrics={
                    "merchant_id": worst_merchant[0],
                    "high_risk_transactions": worst_merchant[1]["high_risk_count"],
                    "total_transactions": worst_merchant[1]["count"],
                    "high_risk_rate": worst_merchant[1]["high_risk_count"] / worst_merchant[1]["count"] * 100
                }
            ))

    def _analyze_user_patterns(self) -> None:
        """Analyze transaction patterns by user."""
        user_data = {}

        for t in self.transactions:
            user_id = t.get("user_id", "unknown")
            if user_id not in user_data:
                user_data[user_id] = {
                    "count": 0,
                    "total_amount": 0,
                    "merchants": set(),
                    "devices": set(),
                    "countries": set(),
                    "blocked_count": 0
                }

            user_data[user_id]["count"] += 1
            user_data[user_id]["total_amount"] += t.get("amount", 0)
            user_data[user_id]["merchants"].add(t.get("merchant_id", "unknown"))
            user_data[user_id]["devices"].add(t.get("device_id", "unknown"))
            user_data[user_id]["countries"].add(t.get("user_country", "unknown"))

            if t.get("decision") == "block":
                user_data[user_id]["blocked_count"] += 1

        # Find suspicious users (many countries/devices)
        suspicious = {
            u: d for u, d in user_data.items()
            if len(d["countries"]) > 3 or len(d["devices"]) > 5
        }

        if suspicious:
            most_suspicious = max(suspicious.items(),
                                 key=lambda x: len(x[1]["countries"]) + len(x[1]["devices"]))

            self.insights.append(TransactionInsight(
                title="Account Takeover Risk",
                description=f"User {most_suspicious[0]} showing suspicious patterns across multiple devices/locations",
                severity="warning",
                impact="Potential account compromise or fraud.",
                recommendation="Contact user for verification. Review recent activity. Consider requiring password reset.",
                metrics={
                    "user_id": most_suspicious[0],
                    "unique_countries": len(most_suspicious[1]["countries"]),
                    "unique_devices": len(most_suspicious[1]["devices"]),
                    "unique_merchants": len(most_suspicious[1]["merchants"]),
                    "total_transactions": most_suspicious[1]["count"]
                }
            ))

    def _analyze_geographic_patterns(self) -> None:
        """Analyze geographic transaction patterns."""
        country_counts = Counter(t.get("user_country", "unknown")
                                for t in self.transactions)
        country_risks = {}

        for country in country_counts:
            country_txns = [t for t in self.transactions
                           if t.get("user_country") == country]
            high_risk = len([t for t in country_txns
                           if t.get("risk_score", 0) > 0.7])

            country_risks[country] = {
                "count": len(country_txns),
                "high_risk_count": high_risk,
                "high_risk_rate": high_risk / len(country_txns) if country_txns else 0
            }

        # Find high-risk regions
        high_risk_countries = {
            c: d for c, d in country_risks.items()
            if d["high_risk_rate"] > 0.4  # >40% high risk
        }

        if high_risk_countries:
            worst_country = max(high_risk_countries.items(),
                               key=lambda x: x[1]["high_risk_rate"])

            self.insights.append(TransactionInsight(
                title="Geographic Risk Pattern",
                description=f"High fraud rate detected from {worst_country[0]}",
                severity="warning",
                impact="Transactions from specific regions show elevated risk.",
                recommendation="Review country risk settings. Consider additional verification for high-risk regions.",
                metrics={
                    "country": worst_country[0],
                    "high_risk_transactions": worst_country[1]["high_risk_count"],
                    "total_from_country": worst_country[1]["count"],
                    "high_risk_rate_percent": worst_country[1]["high_risk_rate"] * 100
                }
            ))

    def _analyze_velocity_patterns(self) -> None:
        """Analyze transaction velocity (frequency over time)."""
        # Simple velocity check - transactions per hour per user
        user_velocities = {}

        for t in self.transactions:
            user_id = t.get("user_id", "unknown")
            if user_id not in user_velocities:
                user_velocities[user_id] = 0
            user_velocities[user_id] += 1

        # Find high-velocity users
        high_velocity = {u: v for u, v in user_velocities.items() if v > 10}

        if high_velocity:
            worst_user = max(high_velocity.items(), key=lambda x: x[1])

            self.insights.append(TransactionInsight(
                title="High Transaction Velocity",
                description=f"User {worst_user[0]} made {worst_user[1]} transactions in short timeframe",
                severity="warning",
                impact="Unusually high frequency may indicate automation or fraud.",
                recommendation="Review user for bot activity. Check for card testing or account compromise.",
                metrics={
                    "user_id": worst_user[0],
                    "transaction_count": worst_user[1],
                    "avg_user_transactions": sum(user_velocities.values()) / len(user_velocities)
                }
            ))

    def _analyze_recommendations(self) -> None:
        """Generate strategic recommendations based on all data."""
        if not self.transactions:
            return

        total = len(self.transactions)

        # Check approval rate
        approved = len([t for t in self.transactions if t.get("decision") == "allow"])
        approval_rate = approved / total * 100

        recommendations = []

        if approval_rate < 85:
            recommendations.append({
                "action": "Relax Thresholds",
                "reason": f"Low approval rate ({approval_rate:.1f}%)",
                "impact": "Improve customer experience"
            })

        if approval_rate > 95:
            recommendations.append({
                "action": "Tighten Thresholds",
                "reason": f"High approval rate ({approval_rate:.1f}%) may miss fraud",
                "impact": "Improve fraud detection"
            })

        # Check blocked vs reviewed
        blocked = len([t for t in self.transactions if t.get("decision") == "block"])
        reviewed = len([t for t in self.transactions if t.get("decision") == "review"])

        if reviewed / total > 0.2:
            recommendations.append({
                "action": "Reduce Review Queue",
                "reason": f"High review rate ({reviewed / total * 100:.1f}%)",
                "impact": "Reduce manual review workload"
            })

        if recommendations:
            self.insights.append(TransactionInsight(
                title="Strategic Recommendations",
                description=f"Based on {total} transactions analyzed",
                severity="info",
                impact="Optimize risk engine performance and user experience",
                recommendation="; ".join([f"{r['action']}: {r['reason']}" for r in recommendations]),
                metrics={
                    "recommendations_count": len(recommendations),
                    "approval_rate": approval_rate,
                    "blocked_rate": blocked / total * 100,
                    "review_rate": reviewed / total * 100
                }
            ))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all insights."""
        return {
            "total_insights": len(self.insights),
            "critical": len([i for i in self.insights if i.severity == "critical"]),
            "warning": len([i for i in self.insights if i.severity == "warning"]),
            "info": len([i for i in self.insights if i.severity == "info"]),
            "insights": [
                {
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "impact": i.impact,
                    "recommendation": i.recommendation,
                    "metrics": i.metrics
                }
                for i in self.insights
            ]
        }
