"""
Advanced Analytics Engine - Comprehensive transaction analysis and insights

Features:
- Detailed denial analysis with actionable explanations
- Real-time monitoring metrics and KPIs
- Pattern detection and trend analysis
- Customer segmentation and behavioral analysis
- Risk heat maps and correlation analysis
- Performance metrics and SLA tracking
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class DenialReason(Enum):
    """Comprehensive denial reason codes"""
    HIGH_RISK_SCORE = "high_risk_score"
    FRAUD_PATTERN_DETECTED = "fraud_pattern_detected"
    SANCTIONS_MATCH = "sanctions_match"
    PEP_MATCH = "pep_match"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    VELOCITY_EXCEEDED = "velocity_exceeded"
    NETWORK_RISK = "network_risk"
    UNUSUAL_GEOLOCATION = "unusual_geolocation"
    DEVICE_MISMATCH = "device_mismatch"
    ACCOUNT_COMPROMISE = "account_compromise"
    TESTING_MODE = "testing_mode"
    MANUAL_REVIEW = "manual_review"


@dataclass
class DenialAnalysis:
    """Detailed analysis of a denied transaction"""
    transaction_id: str
    primary_reason: str
    risk_score: float
    confidence_score: float
    contributing_factors: List[str] = field(default_factory=list)
    risk_signals: List[Dict[str, Any]] = field(default_factory=list)
    recommended_action: str = ""
    can_override: bool = False
    override_conditions: List[str] = field(default_factory=list)
    related_transactions: List[str] = field(default_factory=list)
    customer_history: Dict[str, Any] = field(default_factory=dict)
    explainability_score: float = 1.0
    severity_level: str = "high"


@dataclass
class TransactionMetrics:
    """Real-time transaction metrics"""
    total_transactions: int = 0
    approved_count: int = 0
    denied_count: int = 0
    review_count: int = 0
    approval_rate: float = 0.0
    denial_rate: float = 0.0
    review_rate: float = 0.0
    avg_transaction_amount: float = 0.0
    total_volume: float = 0.0
    avg_risk_score: float = 0.0
    p95_risk_score: float = 0.0
    p99_risk_score: float = 0.0
    max_risk_score: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class CustomerProfile:
    """Comprehensive customer behavioral profile"""
    customer_id: str
    total_transactions: int = 0
    approved_transactions: int = 0
    denied_transactions: int = 0
    review_transactions: int = 0
    total_spend: float = 0.0
    avg_transaction_amount: float = 0.0
    std_dev_amount: float = 0.0
    denial_rate: float = 0.0
    avg_risk_score: float = 0.0
    is_high_risk: bool = False
    devices_used: List[str] = field(default_factory=list)
    countries_used: List[str] = field(default_factory=list)


class AdvancedAnalyticsEngine:
    """Enterprise-grade analytics with comprehensive insights"""

    def __init__(self):
        self.transactions = []
        self.df = None
        self.denial_analyses: Dict[str, DenialAnalysis] = {}
        self.customer_profiles: Dict[str, CustomerProfile] = {}
        self.metrics = TransactionMetrics()
        self.patterns = defaultdict(int)
        self.denial_reasons_dist = Counter()

    def load_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        """Load and prepare transaction data"""
        self.transactions = transactions
        self.df = pd.DataFrame(transactions)
        self._enrich_data()
        self._compute_metrics()

    def _enrich_data(self) -> None:
        """Add derived features and enrichments"""
        if self.df.empty:
            return

        if 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
        else:
            self.df['timestamp'] = datetime.utcnow()

        self.df['hour'] = self.df['timestamp'].dt.hour
        self.df['day_of_week'] = self.df['timestamp'].dt.day_name()
        self.df['amount_log'] = np.log1p(pd.to_numeric(self.df['amount'], errors='coerce'))

        self.df['is_denied'] = self.df['decision'].str.lower() == 'block'
        self.df['is_approved'] = self.df['decision'].str.lower() == 'allow'
        self.df['is_review'] = self.df['decision'].str.lower() == 'review'

    def _compute_metrics(self) -> None:
        """Compute real-time transaction metrics"""
        if self.df.empty:
            return

        n = len(self.df)
        self.metrics.total_transactions = n
        self.metrics.approved_count = int(self.df['is_approved'].sum())
        self.metrics.denied_count = int(self.df['is_denied'].sum())
        self.metrics.review_count = int(self.df['is_review'].sum())

        self.metrics.approval_rate = (self.metrics.approved_count / n * 100) if n > 0 else 0.0
        self.metrics.denial_rate = (self.metrics.denied_count / n * 100) if n > 0 else 0.0
        self.metrics.review_rate = (self.metrics.review_count / n * 100) if n > 0 else 0.0

        self.metrics.avg_transaction_amount = float(pd.to_numeric(self.df['amount'], errors='coerce').mean())
        self.metrics.total_volume = float(pd.to_numeric(self.df['amount'], errors='coerce').sum())

        if 'risk_score' in self.df.columns:
            risk_scores = pd.to_numeric(self.df['risk_score'], errors='coerce')
            self.metrics.avg_risk_score = float(risk_scores.mean())
            self.metrics.p95_risk_score = float(risk_scores.quantile(0.95))
            self.metrics.p99_risk_score = float(risk_scores.quantile(0.99))
            self.metrics.max_risk_score = float(risk_scores.max())

    def analyze_denials(self) -> Dict[str, DenialAnalysis]:
        """Comprehensive analysis of denied transactions"""
        if self.df.empty:
            return {}

        denied_txns = self.df[self.df['is_denied']]

        for idx, txn in denied_txns.iterrows():
            analysis = self._analyze_single_denial(txn)
            self.denial_analyses[txn.get('transaction_id', str(idx))] = analysis
            self.denial_reasons_dist[analysis.primary_reason] += 1

        return self.denial_analyses

    def _analyze_single_denial(self, txn: pd.Series) -> DenialAnalysis:
        """Analyze a single denied transaction"""
        txn_id = str(txn.get('transaction_id', 'unknown'))
        risk_score = float(txn.get('risk_score', 0.0))

        primary_reason = self._determine_denial_reason(txn)
        contributing_factors = self._identify_contributing_factors(txn)
        risk_signals = self._extract_risk_signals(txn)
        related = self._find_related_transactions(txn)
        customer_hist = self._get_customer_history(txn.get('user_id'))
        can_override, conditions = self._check_override_possibility(txn, contributing_factors)
        recommended = self._get_recommended_action(primary_reason, risk_score)
        explainability = self._calculate_explainability(primary_reason, contributing_factors)
        severity = self._determine_severity(risk_score, primary_reason)

        return DenialAnalysis(
            transaction_id=txn_id,
            primary_reason=primary_reason,
            risk_score=risk_score,
            confidence_score=float(txn.get('confidence_score', 0.85)),
            contributing_factors=contributing_factors,
            risk_signals=risk_signals,
            recommended_action=recommended,
            can_override=can_override,
            override_conditions=conditions,
            related_transactions=related,
            customer_history=customer_hist,
            explainability_score=explainability,
            severity_level=severity
        )

    def _determine_denial_reason(self, txn: pd.Series) -> str:
        """Determine primary reason for denial"""
        risk_score = float(txn.get('risk_score', 0.0))

        if 'sanctions' in str(txn).lower():
            return DenialReason.SANCTIONS_MATCH.value
        if 'pep' in str(txn).lower():
            return DenialReason.PEP_MATCH.value
        if risk_score > 0.85:
            return DenialReason.HIGH_RISK_SCORE.value

        return DenialReason.FRAUD_PATTERN_DETECTED.value

    def _identify_contributing_factors(self, txn: pd.Series) -> List[str]:
        """Identify all factors contributing to denial"""
        factors = []

        amount = float(txn.get('amount', 0))
        if amount > 5000:
            factors.append("Large transaction amount")

        if str(txn.get('user_country', '')).lower() != 'us':
            factors.append("International transaction")

        if float(txn.get('risk_score', 0)) > 0.7:
            factors.append("High ML risk score")

        if 'anomaly' in str(txn).lower():
            factors.append("Statistical anomaly detected")

        return factors

    def _extract_risk_signals(self, txn: pd.Series) -> List[Dict[str, Any]]:
        """Extract detailed risk signals"""
        signals = []

        amount = float(txn.get('amount', 0))
        signals.append({
            "signal": "transaction_amount",
            "value": amount,
            "severity": "high" if amount > 5000 else "medium" if amount > 1000 else "low",
            "description": f"Transaction amount of ${amount:,.2f}"
        })

        risk = float(txn.get('risk_score', 0))
        signals.append({
            "signal": "risk_score",
            "value": risk,
            "severity": "high" if risk > 0.7 else "medium" if risk > 0.4 else "low",
            "description": f"ML model risk assessment: {risk:.1%}"
        })

        return signals

    def _find_related_transactions(self, txn: pd.Series) -> List[str]:
        """Find related transactions"""
        related = []

        user_id = txn.get('user_id')
        if user_id and not self.df.empty:
            user_txns = self.df[self.df.get('user_id') == user_id]
            related = user_txns['transaction_id'].head(5).tolist() if 'transaction_id' in user_txns else []

        return related

    def _get_customer_history(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Get customer's historical profile"""
        if not user_id or self.df.empty:
            return {}

        user_txns = self.df[self.df.get('user_id') == user_id]

        return {
            "total_transactions": len(user_txns),
            "total_approved": int(user_txns['is_approved'].sum()) if 'is_approved' in user_txns else 0,
            "total_denied": int(user_txns['is_denied'].sum()) if 'is_denied' in user_txns else 0,
            "denial_rate": float((user_txns['is_denied'].sum() / len(user_txns) * 100)) if len(user_txns) > 0 else 0.0,
            "avg_amount": float(pd.to_numeric(user_txns['amount'], errors='coerce').mean()) if 'amount' in user_txns else 0.0,
        }

    def _check_override_possibility(self, txn: pd.Series, factors: List[str]) -> Tuple[bool, List[str]]:
        """Check if transaction can be overridden"""
        risk_score = float(txn.get('risk_score', 0))

        can_override = risk_score < 0.95

        conditions = []
        if can_override:
            conditions.append("Manual review by compliance officer")
            conditions.append("Customer verification call")
            if risk_score > 0.7:
                conditions.append("3D Secure authentication required")

        return can_override, conditions

    def _get_recommended_action(self, reason: str, risk_score: float) -> str:
        """Get recommended action for denial"""
        if reason == DenialReason.SANCTIONS_MATCH.value:
            return "Contact compliance team immediately - potential sanctions violation"
        elif reason == DenialReason.PEP_MATCH.value:
            return "Enhanced due diligence required - PEP identified"
        elif risk_score > 0.85:
            return "Block transaction and request customer verification"
        elif risk_score > 0.7:
            return "Send to manual review queue"
        else:
            return "Flag for investigation but may proceed with additional verification"

    def _calculate_explainability(self, reason: str, factors: List[str]) -> float:
        """Calculate how explainable the denial is (0-1)"""
        base_score = 0.8

        if reason in [DenialReason.SANCTIONS_MATCH.value, DenialReason.PEP_MATCH.value]:
            base_score = 0.95

        base_score += len(factors) * 0.05

        return min(1.0, base_score)

    def _determine_severity(self, risk_score: float, reason: str) -> str:
        """Determine severity level of denial"""
        if reason in [DenialReason.SANCTIONS_MATCH.value, DenialReason.PEP_MATCH.value]:
            return "critical"
        elif risk_score > 0.85:
            return "high"
        elif risk_score > 0.6:
            return "medium"
        else:
            return "low"

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return asdict(self.metrics)

    def get_denial_summary(self) -> Dict[str, Any]:
        """Get denial analysis summary"""
        return {
            "total_denials": len(self.denial_analyses),
            "denial_reasons_distribution": dict(self.denial_reasons_dist),
            "avg_risk_score_denied": float(np.mean([d.risk_score for d in self.denial_analyses.values()])) if self.denial_analyses else 0.0,
            "override_eligible": sum(1 for d in self.denial_analyses.values() if d.can_override),
        }

    def get_customer_analytics(self) -> Dict[str, CustomerProfile]:
        """Generate customer analytics"""
        if self.df.empty:
            return {}

        for user_id in self.df['user_id'].unique():
            if pd.isna(user_id):
                continue

            user_txns = self.df[self.df['user_id'] == user_id]

            profile = CustomerProfile(
                customer_id=str(user_id),
                total_transactions=len(user_txns),
                approved_transactions=int(user_txns['is_approved'].sum()),
                denied_transactions=int(user_txns['is_denied'].sum()),
                review_transactions=int(user_txns['is_review'].sum()),
                total_spend=float(pd.to_numeric(user_txns['amount'], errors='coerce').sum()),
                avg_transaction_amount=float(pd.to_numeric(user_txns['amount'], errors='coerce').mean()),
                std_dev_amount=float(pd.to_numeric(user_txns['amount'], errors='coerce').std()),
                denial_rate=float((user_txns['is_denied'].sum() / len(user_txns) * 100)) if len(user_txns) > 0 else 0.0,
                avg_risk_score=float(pd.to_numeric(user_txns.get('risk_score', 0), errors='coerce').mean()),
                is_high_risk=bool(pd.to_numeric(user_txns.get('risk_score', 0), errors='coerce').mean() > 0.7),
            )

            self.customer_profiles[str(user_id)] = profile

        return self.customer_profiles

    def get_top_risk_customers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top risk customers"""
        if not self.customer_profiles:
            self.get_customer_analytics()

        sorted_customers = sorted(
            self.customer_profiles.values(),
            key=lambda x: x.avg_risk_score,
            reverse=True
        )

        return [asdict(c) for c in sorted_customers[:top_n]]

    def get_denial_insights(self) -> Dict[str, Any]:
        """Get comprehensive denial insights"""
        return {
            "total_denials": len(self.denial_analyses),
            "reasons_breakdown": dict(self.denial_reasons_dist),
            "override_eligible_count": sum(1 for d in self.denial_analyses.values() if d.can_override),
            "avg_explainability": float(np.mean([d.explainability_score for d in self.denial_analyses.values()])) if self.denial_analyses else 1.0,
        }
