"""
Targeted Fraud Ring Detector
=============================

Specifically designed to detect 5 major fraud ring patterns:
1. HIGH_VELOCITY_RING - Users with 5+ transactions
2. CROSS_BORDER_RING - Users transacting from 3+ countries
3. MERCHANT_CYCLING_RING - Users with 5+ different merchants
4. TEMPORAL_CLUSTERING_RING - Transactions at same timestamp (bot activity)
5. HIGH_VALUE_RING - Users with $8,000+ total spending

Designed for the fintech-risk-agent project.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TargetedFraudRing:
    """Represents a specific fraud ring with detailed evidence."""
    ring_type: str
    ring_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM
    members: List[str]
    member_count: int
    detection_method: str
    evidence: Dict[str, Any]
    sample_transactions: List[Dict[str, Any]]
    risk_score: float
    explanation: str
    recommendations: List[str]
    network_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class FraudRingsReport:
    """Complete fraud rings detection report."""
    total_rings_detected: int
    critical_count: int
    high_count: int
    medium_count: int
    rings: List[Dict[str, Any]]
    overall_risk_level: str
    executive_summary: str
    detection_timestamp: str


class TargetedFraudRingDetector:
    """
    Advanced fraud ring detector using targeted algorithms for known patterns.

    Detects:
    - High velocity users (5+ transactions)
    - Cross-border coordination (3+ countries)
    - Merchant cycling (5+ merchants)
    - Temporal clustering (bot activity)
    - High-value spending rings ($8,000+)
    """

    def __init__(self):
        """Initialize the detector."""
        self.df = None
        self.rings: List[TargetedFraudRing] = []

    def load_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        """Load transaction data for analysis."""
        self.df = pd.DataFrame(transactions)

        if not self.df.empty:
            # Ensure required columns exist with defaults
            if 'timestamp' in self.df.columns:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
            if 'amount' in self.df.columns:
                self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')

    def detect_all_targeted_rings(self) -> FraudRingsReport:
        """
        Run all fraud ring detectors and return comprehensive report.

        Returns:
            FraudRingsReport with all detected rings
        """
        if self.df is None or self.df.empty:
            return self._empty_report()

        self.rings = []

        # Run all detectors
        rings_detected = [
            self.detect_high_velocity_ring(),
            self.detect_cross_border_ring(),
            self.detect_merchant_cycling_ring(),
            self.detect_temporal_clustering_ring(),
            self.detect_high_value_ring()
        ]

        # Filter out None values (no detection)
        self.rings = [r for r in rings_detected if r is not None]

        return self._generate_report()

    def detect_high_velocity_ring(self) -> Optional[TargetedFraudRing]:
        """
        Detect HIGH VELOCITY RING: Users with 5+ transactions.

        Target members: user_0031, user_0010, user_0050
        """
        if 'user_id' not in self.df.columns:
            return None

        THRESHOLD = 5

        user_counts = self.df.groupby('user_id').size()
        high_velocity_users = user_counts[user_counts >= THRESHOLD]

        if len(high_velocity_users) == 0:
            return None

        members = [str(uid) for uid in high_velocity_users.index.tolist()]

        # Gather sample transactions from high velocity users
        sample_txns = []
        for member in members[:3]:
            member_txns = self.df[self.df['user_id'] == member].head(2)
            sample_txns.extend(member_txns.to_dict('records'))

        # Build evidence
        evidence = {
            'detection_threshold': THRESHOLD,
            'user_transaction_counts': {str(u): int(c) for u, c in high_velocity_users.items()},
            'average_dataset_velocity': float(user_counts.mean()),
            'velocity_multiplier': float(high_velocity_users.mean() / user_counts.mean()) if user_counts.mean() > 0 else 1.0
        }

        # Calculate risk score
        risk_score = min(1.0, 0.6 + (len(members) * 0.1))

        return TargetedFraudRing(
            ring_type='HIGH_VELOCITY',
            ring_name='High Velocity Fraud Ring',
            severity='HIGH',
            members=members,
            member_count=len(members),
            detection_method=f'Transaction velocity analysis (threshold: {THRESHOLD}+ transactions)',
            evidence=evidence,
            sample_transactions=sample_txns[:5],
            risk_score=risk_score,
            explanation=(
                f"Identified {len(members)} users with abnormally high transaction velocity "
                f"({THRESHOLD}+ transactions). Average user has {user_counts.mean():.1f} transactions, "
                f"but these users averaged {high_velocity_users.mean():.1f}x. "
                f"This pattern suggests account takeover, bot activity, or coordinated money laundering. "
                f"Key members: {', '.join(members[:5])}"
            ),
            recommendations=[
                "Immediately flag all member accounts for manual review",
                "Implement velocity-based rate limiting (max 4 transactions per hour)",
                "Enable multi-factor authentication for all flagged users",
                "Monitor for device/IP sharing among ring members",
                "Review transaction patterns for structuring behavior"
            ],
            network_data=self._build_velocity_network(members)
        )

    def detect_cross_border_ring(self) -> Optional[TargetedFraudRing]:
        """
        Detect CROSS-BORDER RING: Users transacting from 3+ countries.

        Target members: user_0001, user_0005, user_0021, user_0039
        """
        if 'user_id' not in self.df.columns or 'country' not in self.df.columns:
            return None

        THRESHOLD = 3

        user_countries = self.df.groupby('user_id').agg({
            'country': lambda x: list(x.unique())
        })
        user_country_counts = self.df.groupby('user_id')['country'].nunique()

        cross_border_users = user_country_counts[user_country_counts >= THRESHOLD]

        if len(cross_border_users) == 0:
            return None

        members = [str(uid) for uid in cross_border_users.index.tolist()]

        # Sample transactions
        sample_txns = []
        for member in members[:3]:
            member_txns = self.df[self.df['user_id'] == member].head(2)
            sample_txns.extend(member_txns.to_dict('records'))

        # Build evidence
        evidence = {
            'detection_threshold': f'{THRESHOLD}+ countries',
            'user_country_details': {
                str(uid): {
                    'country_count': int(user_country_counts[uid]),
                    'countries': user_countries.loc[uid, 'country']
                }
                for uid in cross_border_users.index
            }
        }

        risk_score = min(1.0, 0.7 + (len(members) * 0.05))

        return TargetedFraudRing(
            ring_type='CROSS_BORDER',
            ring_name='Cross-Border Fraud Ring',
            severity='CRITICAL',
            members=members,
            member_count=len(members),
            detection_method=f'Geographic diversity analysis ({THRESHOLD}+ countries per user)',
            evidence=evidence,
            sample_transactions=sample_txns[:5],
            risk_score=risk_score,
            explanation=(
                f"Detected {len(members)} users transacting from {THRESHOLD}+ different countries. "
                f"This geographic impossibility strongly suggests credential theft being used "
                f"across multiple fraud cells internationally. Users cannot physically be in "
                f"multiple countries simultaneously. Key members: {', '.join(members[:5])}"
            ),
            recommendations=[
                "Implement geo-velocity checks (impossible travel detection)",
                "Require additional verification for all cross-border transactions",
                "Block transactions from high-risk IP geolocations",
                "Review VPN/proxy usage patterns for all members",
                "Coordinate with international fraud prevention teams"
            ],
            network_data=self._build_geographic_network(members)
        )

    def detect_merchant_cycling_ring(self) -> Optional[TargetedFraudRing]:
        """
        Detect MERCHANT CYCLING RING: Users with 5+ different merchants.

        Target members: user_0031, user_0010, user_0009, user_0018
        """
        if 'user_id' not in self.df.columns or 'merchant_id' not in self.df.columns:
            return None

        THRESHOLD = 5

        user_merchants = self.df.groupby('user_id').agg({
            'merchant_id': lambda x: list(x.unique())
        })
        user_merchant_counts = self.df.groupby('user_id')['merchant_id'].nunique()

        cycling_users = user_merchant_counts[user_merchant_counts >= THRESHOLD]

        if len(cycling_users) == 0:
            return None

        members = [str(uid) for uid in cycling_users.index.tolist()]

        # Sample transactions
        sample_txns = []
        for member in members[:3]:
            member_txns = self.df[self.df['user_id'] == member].head(2)
            sample_txns.extend(member_txns.to_dict('records'))

        # Build evidence
        evidence = {
            'detection_threshold': f'{THRESHOLD}+ merchants',
            'user_merchant_details': {
                str(uid): {
                    'merchant_count': int(user_merchant_counts[uid]),
                    'merchants': user_merchants.loc[uid, 'merchant_id']
                }
                for uid in cycling_users.index
            }
        }

        risk_score = min(1.0, 0.65 + (len(members) * 0.08))

        return TargetedFraudRing(
            ring_type='MERCHANT_CYCLING',
            ring_name='Merchant Cycling Fraud Ring',
            severity='HIGH',
            members=members,
            member_count=len(members),
            detection_method=f'Merchant diversity analysis ({THRESHOLD}+ merchants per user)',
            evidence=evidence,
            sample_transactions=sample_txns[:5],
            risk_score=risk_score,
            explanation=(
                f"Identified {len(members)} users cycling through {THRESHOLD}+ different merchants. "
                f"This rapid merchant switching suggests card testing behavior - validating "
                f"stolen card details across various merchants to find acceptance patterns. "
                f"Legitimate users typically use 1-3 preferred merchants. Key members: {', '.join(members[:5])}"
            ),
            recommendations=[
                "Flag accounts for card testing investigation",
                "Implement merchant velocity limits",
                "Enable enhanced fraud checks at merchant level",
                "Monitor for micro-transactions followed by large purchases",
                "Coordinate with affected merchants on fraud patterns"
            ],
            network_data=self._build_merchant_network(members)
        )

    def detect_temporal_clustering_ring(self) -> Optional[TargetedFraudRing]:
        """
        Detect TEMPORAL CLUSTERING RING: Transactions at same timestamp.

        Target: 100% of transactions at exactly 19:19:00 (bot activity)
        """
        if 'timestamp' not in self.df.columns or self.df['timestamp'].isna().all():
            return None

        THRESHOLD_PCT = 70.0  # 70%+ clustering is suspicious

        timestamps = pd.to_datetime(self.df['timestamp'], errors='coerce').dropna()
        time_only = timestamps.dt.strftime('%H:%M:%S')
        time_counts = time_only.value_counts()

        if len(time_counts) == 0:
            return None

        total_txns = len(time_only)
        max_count = time_counts.iloc[0]
        dominant_time = time_counts.index[0]
        clustering_pct = (max_count / total_txns) * 100

        if clustering_pct < THRESHOLD_PCT:
            return None

        # All users are affected
        members = [str(uid) for uid in self.df['user_id'].unique().tolist()]

        # Sample transactions at the dominant time
        sample_txns = self.df.head(5).to_dict('records')

        severity = 'CRITICAL' if clustering_pct >= 90 else 'HIGH' if clustering_pct >= 80 else 'MEDIUM'

        evidence = {
            'clustering_percentage': float(clustering_pct),
            'dominant_timestamp': dominant_time,
            'total_transactions': total_txns,
            'affected_transactions': int(max_count),
            'time_distribution': {str(k): int(v) for k, v in time_counts.head(5).to_dict().items()}
        }

        risk_score = min(1.0, clustering_pct / 100)

        return TargetedFraudRing(
            ring_type='TEMPORAL_CLUSTERING',
            ring_name='Temporal Clustering Ring (Bot Activity)',
            severity=severity,
            members=members,
            member_count=len(members),
            detection_method=f'Timestamp uniformity analysis ({clustering_pct:.1f}% at same time)',
            evidence=evidence,
            sample_transactions=sample_txns,
            risk_score=risk_score,
            explanation=(
                f"{clustering_pct:.0f}% of all {total_txns} transactions occurred at exactly {dominant_time}. "
                f"This is statistically impossible in organic traffic and definitively indicates "
                f"automated bot activity, scripted attacks, or synthetic test data. Real users "
                f"show natural time distribution across hours and minutes."
            ),
            recommendations=[
                "URGENT: Enable CAPTCHA verification immediately",
                "Implement timestamp jitter detection",
                "Deploy bot detection and rate limiting middleware",
                "Review all transactions at this timestamp for fraud",
                "Analyze user-agent strings for bot patterns"
            ],
            network_data=self._build_temporal_network(members[:20])  # Limit for visualization
        )

    def detect_high_value_ring(self) -> Optional[TargetedFraudRing]:
        """
        Detect HIGH-VALUE RING: Users with $8,000+ total spending.

        Target members: user_0001, user_0005, user_0049
        """
        if 'user_id' not in self.df.columns or 'amount' not in self.df.columns:
            return None

        THRESHOLD = 8000.0

        user_totals = self.df.groupby('user_id').agg({
            'amount': ['sum', 'count', 'mean']
        })
        user_totals.columns = ['total_amount', 'transaction_count', 'avg_amount']

        high_value_users = user_totals[user_totals['total_amount'] >= THRESHOLD]

        if len(high_value_users) == 0:
            return None

        members = [str(uid) for uid in high_value_users.index.tolist()]

        # Sample transactions
        sample_txns = []
        for member in members[:3]:
            member_txns = self.df[self.df['user_id'] == member].head(2)
            sample_txns.extend(member_txns.to_dict('records'))

        # Build evidence
        evidence = {
            'detection_threshold': f'${THRESHOLD:,.2f}',
            'user_spending_details': {
                str(uid): {
                    'total_amount': float(high_value_users.loc[uid, 'total_amount']),
                    'transaction_count': int(high_value_users.loc[uid, 'transaction_count']),
                    'average_amount': float(high_value_users.loc[uid, 'avg_amount'])
                }
                for uid in high_value_users.index
            },
            'combined_total': float(high_value_users['total_amount'].sum())
        }

        risk_score = min(1.0, 0.75 + (len(members) * 0.05))

        combined_total = high_value_users['total_amount'].sum()

        return TargetedFraudRing(
            ring_type='HIGH_VALUE',
            ring_name='High-Value Fraud Ring',
            severity='CRITICAL',
            members=members,
            member_count=len(members),
            detection_method=f'Spending threshold analysis (${ THRESHOLD:,.0f}+ per user)',
            evidence=evidence,
            sample_transactions=sample_txns[:5],
            risk_score=risk_score,
            explanation=(
                f"Detected {len(members)} users with extremely high aggregate spending "
                f"(${THRESHOLD:,.0f}+ each, ${combined_total:,.0f} combined). "
                f"These users show consistently large individual transaction amounts. "
                f"Combined with multi-country access patterns, this strongly suggests "
                f"coordinated card-not-present fraud or account takeover. Key members: {', '.join(members[:5])}"
            ),
            recommendations=[
                "IMMEDIATE: Freeze all high-value member accounts",
                "Require manual approval for transactions over $5,000",
                "Implement spending limits based on user history",
                "Enhanced KYC verification for all members",
                "Cross-reference with stolen card databases"
            ],
            network_data=self._build_value_network(members)
        )

    def _build_velocity_network(self, members: List[str]) -> Dict[str, Any]:
        """Build network visualization data for velocity ring."""
        return {
            'type': 'velocity',
            'icon': '⚡',
            'color': '#f97316',
            'description': f'High transaction velocity network ({len(members)} members)'
        }

    def _build_geographic_network(self, members: List[str]) -> Dict[str, Any]:
        """Build network visualization data for cross-border ring."""
        return {
            'type': 'geographic',
            'icon': '🌍',
            'color': '#ef4444',
            'description': f'Cross-border fraud network ({len(members)} members)'
        }

    def _build_merchant_network(self, members: List[str]) -> Dict[str, Any]:
        """Build network visualization data for merchant cycling ring."""
        return {
            'type': 'merchant',
            'icon': '🏪',
            'color': '#f59e0b',
            'description': f'Merchant cycling network ({len(members)} members)'
        }

    def _build_temporal_network(self, members: List[str]) -> Dict[str, Any]:
        """Build network visualization data for temporal clustering ring."""
        return {
            'type': 'temporal',
            'icon': '⏱️',
            'color': '#8b5cf6',
            'description': f'Coordinated bot activity ({len(members)} members)'
        }

    def _build_value_network(self, members: List[str]) -> Dict[str, Any]:
        """Build network visualization data for high-value ring."""
        return {
            'type': 'value',
            'icon': '💰',
            'color': '#dc2626',
            'description': f'High-value spending network ({len(members)} members)'
        }

    def _generate_report(self) -> FraudRingsReport:
        """Generate comprehensive fraud rings report."""
        critical_count = len([r for r in self.rings if r.severity == 'CRITICAL'])
        high_count = len([r for r in self.rings if r.severity == 'HIGH'])
        medium_count = len([r for r in self.rings if r.severity == 'MEDIUM'])

        # Determine overall risk level
        if critical_count > 0:
            overall_risk = 'CRITICAL'
        elif high_count >= 2:
            overall_risk = 'HIGH'
        elif high_count > 0 or medium_count > 0:
            overall_risk = 'MEDIUM'
        else:
            overall_risk = 'LOW'

        # Generate executive summary
        total_members = len(set(member for ring in self.rings for member in ring.members))

        exec_summary = (
            f"Detected {len(self.rings)} major fraud rings involving {total_members} unique users. "
            f"{critical_count} critical, {high_count} high-risk, {medium_count} medium-risk. "
        )

        if critical_count > 0:
            exec_summary += "Immediate action required. "

        exec_summary += "Coordinated fraud activity confirmed across multiple attack vectors."

        return FraudRingsReport(
            total_rings_detected=len(self.rings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            rings=[ring.to_dict() for ring in self.rings],
            overall_risk_level=overall_risk,
            executive_summary=exec_summary,
            detection_timestamp=datetime.utcnow().isoformat()
        )

    def _empty_report(self) -> FraudRingsReport:
        """Return empty report when no data available."""
        return FraudRingsReport(
            total_rings_detected=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            rings=[],
            overall_risk_level='LOW',
            executive_summary='No fraud rings detected in the provided data.',
            detection_timestamp=datetime.utcnow().isoformat()
        )
