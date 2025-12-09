"""
Fraud Intelligence Engine

This module provides realistic fraud detection patterns similar to commercial
fraud platforms (Riskified, Stripe Radar, Sift).

Each detector:
- Uses clear, explainable logic
- Returns human-readable findings
- Explains WHY patterns are suspicious
- Provides evidence (sample transactions)

Detection Categories:
1. Velocity-based (rapid transactions, bursts)
2. Behavioral (merchant cycling, amount anomalies)
3. Geographic (cross-border inconsistencies)
4. ML-based (multivariate anomalies)
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest


@dataclass
class FraudPattern:
    """Structured fraud pattern finding"""
    pattern_id: str
    title: str
    severity: str  # LOW, MEDIUM, HIGH
    explanation: str
    affected_entities: List[str]
    affected_count: int
    sample_transactions: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class FraudInsightsEngine:
    """
    Main fraud intelligence engine.

    Analyzes transaction datasets to detect suspicious patterns
    using both rule-based logic and ML anomaly detection.
    """

    def __init__(self, transactions: List[Dict[str, Any]]):
        """
        Initialize with transaction data.

        Args:
            transactions: List of transaction dictionaries
        """
        self.df = pd.DataFrame(transactions)
        self.patterns: List[FraudPattern] = []

        # Prepare data
        if not self.df.empty:
            if 'timestamp' in self.df.columns:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
            if 'amount' in self.df.columns:
                self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')

    def analyze(self) -> Dict[str, Any]:
        """
        Run all fraud detectors and return comprehensive insights.

        Returns:
            Dictionary with fraud insights summary and detailed patterns
        """
        if self.df.empty:
            return {
                "total_patterns": 0,
                "high_severity_count": 0,
                "medium_severity_count": 0,
                "low_severity_count": 0,
                "patterns": []
            }

        # Run all detectors
        self._detect_high_velocity_users()
        self._detect_merchant_cycling()
        self._detect_cross_border_activity()
        self._detect_temporal_anomalies()
        self._detect_amount_outliers()
        self._detect_ml_anomalies()

        # Summarize findings
        severity_counts = {
            'HIGH': sum(1 for p in self.patterns if p.severity == 'HIGH'),
            'MEDIUM': sum(1 for p in self.patterns if p.severity == 'MEDIUM'),
            'LOW': sum(1 for p in self.patterns if p.severity == 'LOW')
        }

        return {
            "total_patterns": len(self.patterns),
            "high_severity_count": severity_counts['HIGH'],
            "medium_severity_count": severity_counts['MEDIUM'],
            "low_severity_count": severity_counts['LOW'],
            "patterns": [self._pattern_to_dict(p) for p in self.patterns]
        }

    def _detect_high_velocity_users(self):
        """
        Detect users with unusually high transaction velocity.

        WHY SUSPICIOUS:
        - Legitimate users rarely make 5+ transactions in short periods
        - High velocity indicates:
          * Account takeover (fraudster rushing to extract value)
          * Carding (testing multiple stolen cards)
          * Money laundering (structuring/layering)
          * Bot/automated fraud
        """
        if 'user_id' not in self.df.columns:
            return

        user_counts = self.df.groupby('user_id').size()

        # Thresholds
        MEDIUM_THRESHOLD = 4  # 4-5 transactions
        HIGH_THRESHOLD = 6    # 6+ transactions

        for user_id, count in user_counts.items():
            if count >= MEDIUM_THRESHOLD:
                severity = 'HIGH' if count >= HIGH_THRESHOLD else 'MEDIUM'

                # Get user's transactions
                user_txns = self.df[self.df['user_id'] == user_id]
                sample_txns = user_txns.head(3).to_dict('records')

                # Calculate risk multiplier
                avg_count = user_counts.mean()
                risk_multiplier = count / avg_count if avg_count > 0 else 1

                explanation = (
                    f"User {user_id} completed {count} transactions within the analyzed period. "
                    f"This velocity is {risk_multiplier:.1f}x above average ({avg_count:.1f}) "
                    f"and may indicate automated bot activity, account takeover, or rapid fund "
                    f"movement typical of money laundering structuring. Legitimate users typically "
                    f"make 1-3 transactions in similar timeframes."
                )

                pattern = FraudPattern(
                    pattern_id="HIGH_VELOCITY_USER",
                    title="High Transaction Velocity Detected",
                    severity=severity,
                    explanation=explanation,
                    affected_entities=[str(user_id)],
                    affected_count=int(count),
                    sample_transactions=sample_txns,
                    metadata={
                        "threshold": MEDIUM_THRESHOLD,
                        "actual_value": int(count),
                        "risk_multiplier": float(risk_multiplier),
                        "average_velocity": float(avg_count)
                    }
                )
                self.patterns.append(pattern)

    def _detect_merchant_cycling(self):
        """
        Detect users transacting with unusually many different merchants.

        WHY SUSPICIOUS:
        - Legitimate users have 1-3 preferred merchants
        - High merchant diversity indicates:
          * Card testing (validating stolen cards across merchants)
          * Merchant hopping (avoiding fraud detection thresholds)
          * Account takeover (fraudster exploring spending options)
          * Gift card/refund fraud schemes
        """
        if 'user_id' not in self.df.columns or 'merchant_id' not in self.df.columns:
            return

        user_merchants = self.df.groupby('user_id')['merchant_id'].nunique()

        THRESHOLD = 5  # 5+ different merchants

        for user_id, merchant_count in user_merchants.items():
            if merchant_count >= THRESHOLD:
                user_txns = self.df[self.df['user_id'] == user_id]
                sample_txns = user_txns.head(3).to_dict('records')

                merchants = user_txns['merchant_id'].unique().tolist()

                explanation = (
                    f"User {user_id} transacted with {merchant_count} different merchants "
                    f"({', '.join(map(str, merchants[:5]))}{'...' if len(merchants) > 5 else ''}). "
                    f"This behavior resembles card testing where fraudsters validate stolen credentials "
                    f"across multiple merchant accounts before making larger purchases, or 'merchant hopping' "
                    f"to stay under individual merchant fraud thresholds."
                )

                pattern = FraudPattern(
                    pattern_id="MERCHANT_CYCLING",
                    title="Suspicious Merchant Diversity",
                    severity="MEDIUM",
                    explanation=explanation,
                    affected_entities=[str(user_id)],
                    affected_count=int(merchant_count),
                    sample_transactions=sample_txns,
                    metadata={
                        "threshold": THRESHOLD,
                        "merchant_count": int(merchant_count),
                        "merchants": merchants
                    }
                )
                self.patterns.append(pattern)

    def _detect_cross_border_activity(self):
        """
        Detect users with transactions from multiple countries.

        WHY SUSPICIOUS:
        - Same user in 3+ countries suggests:
          * Account compromise (fraudster using VPN/proxies)
          * Credential sharing (account being used by multiple people)
          * Organized fraud rings (coordinated international activity)
          * Geographic impossibility (transactions too far apart in time)
        """
        if 'user_id' not in self.df.columns or 'country' not in self.df.columns:
            return

        user_countries = self.df.groupby('user_id')['country'].nunique()

        MEDIUM_THRESHOLD = 2  # 2 countries
        HIGH_THRESHOLD = 3    # 3+ countries

        for user_id, country_count in user_countries.items():
            if country_count >= MEDIUM_THRESHOLD:
                severity = 'HIGH' if country_count >= HIGH_THRESHOLD else 'MEDIUM'

                user_txns = self.df[self.df['user_id'] == user_id]
                countries = user_txns['country'].unique().tolist()
                sample_txns = user_txns.head(3).to_dict('records')

                explanation = (
                    f"User {user_id} made transactions from {country_count} different countries "
                    f"({', '.join(countries)}). This geographic inconsistency may indicate compromised "
                    f"credentials being used from multiple locations, typical of organized fraud rings. "
                    f"Legitimate users rarely transact from multiple countries in short periods unless "
                    f"they're frequent travelers with documented travel patterns."
                )

                pattern = FraudPattern(
                    pattern_id="CROSS_BORDER_ACTIVITY",
                    title="Multi-Country Transaction Activity",
                    severity=severity,
                    explanation=explanation,
                    affected_entities=[str(user_id)],
                    affected_count=int(country_count),
                    sample_transactions=sample_txns,
                    metadata={
                        "threshold": MEDIUM_THRESHOLD,
                        "country_count": int(country_count),
                        "countries": countries
                    }
                )
                self.patterns.append(pattern)

    def _detect_temporal_anomalies(self):
        """
        Detect unnatural temporal patterns in the dataset.

        WHY SUSPICIOUS:
        - Perfect clustering at specific times indicates:
          * Bot/automated fraud (scheduled attacks)
          * Synthetic/test data (not real transactions)
          * Coordinated fraud campaigns
        - Real transaction data shows natural time distribution
        """
        if 'timestamp' not in self.df.columns or self.df['timestamp'].isna().all():
            return

        # Check hour distribution
        self.df['hour'] = self.df['timestamp'].dt.hour
        hour_counts = self.df['hour'].value_counts()

        # If >80% of transactions at same hour, flag it
        if len(hour_counts) > 0:
            max_hour_pct = (hour_counts.iloc[0] / len(self.df)) * 100

            if max_hour_pct > 80:
                dominant_hour = hour_counts.index[0]

                explanation = (
                    f"{max_hour_pct:.0f}% of all transactions occurred at hour {dominant_hour}:00. "
                    f"This extreme temporal clustering is statistically impossible in organic traffic "
                    f"and suggests either synthetic/test data or coordinated bot activity. Real transaction "
                    f"patterns show natural variance across hours. This uniformity indicates automated "
                    f"systems or scripted fraud attempts."
                )

                pattern = FraudPattern(
                    pattern_id="TEMPORAL_CLUSTERING",
                    title="Suspicious Temporal Uniformity",
                    severity="LOW",  # Dataset-level issue
                    explanation=explanation,
                    affected_entities=["DATASET"],
                    affected_count=int(hour_counts.iloc[0]),
                    sample_transactions=[],
                    metadata={
                        "dominant_hour": int(dominant_hour),
                        "concentration_pct": float(max_hour_pct),
                        "hour_distribution": hour_counts.to_dict()
                    }
                )
                self.patterns.append(pattern)

    def _detect_amount_outliers(self):
        """
        Detect transactions with unusual amounts.

        WHY SUSPICIOUS:
        - Extreme amounts deviate from user's normal behavior
        - Indicates:
          * Account takeover (fraudster maximizing value before detection)
          * Testing limits (seeing how much they can steal)
          * Money laundering (structuring to avoid reporting thresholds)
        """
        if 'amount' not in self.df.columns or 'user_id' not in self.df.columns:
            return

        # Per-user outlier detection
        for user_id in self.df['user_id'].unique():
            user_txns = self.df[self.df['user_id'] == user_id]

            if len(user_txns) < 3:  # Need at least 3 transactions
                continue

            user_mean = user_txns['amount'].mean()
            user_std = user_txns['amount'].std()

            if user_std == 0:  # All amounts the same
                continue

            # Find outliers (>2.5 std from user's mean)
            outliers = user_txns[
                abs(user_txns['amount'] - user_mean) > 2.5 * user_std
            ]

            for _, txn in outliers.iterrows():
                deviation_pct = ((txn['amount'] - user_mean) / user_mean) * 100

                explanation = (
                    f"Transaction {txn['transaction_id']} (${txn['amount']:.2f}) deviates "
                    f"{abs(deviation_pct):.0f}% from user {user_id}'s average (${user_mean:.2f}). "
                    f"This spike in transaction value often indicates account takeover where fraudsters "
                    f"attempt to extract maximum value before the account is frozen, or testing "
                    f"transaction limits to understand account capabilities."
                )

                pattern = FraudPattern(
                    pattern_id="AMOUNT_OUTLIER",
                    title="Unusual Transaction Amount",
                    severity="MEDIUM",
                    explanation=explanation,
                    affected_entities=[str(user_id)],
                    affected_count=1,
                    sample_transactions=[txn.to_dict()],
                    metadata={
                        "transaction_id": str(txn['transaction_id']),
                        "amount": float(txn['amount']),
                        "user_average": float(user_mean),
                        "deviation_pct": float(deviation_pct),
                        "std_deviations": float(abs(txn['amount'] - user_mean) / user_std)
                    }
                )
                self.patterns.append(pattern)

    def _detect_ml_anomalies(self):
        """
        Use ML (Isolation Forest) to detect multivariate behavioral anomalies.

        WHY SUSPICIOUS:
        - ML catches complex patterns humans might miss
        - Combinations of factors that collectively look suspicious:
          * High velocity + diverse merchants + unusual amounts
          * Cross-border + rapid transactions + outlier values
        - Complements rule-based detectors
        """
        required_cols = ['user_id', 'amount']
        if not all(col in self.df.columns for col in required_cols):
            return

        # Build feature matrix per user
        user_features = []
        user_ids = []

        for user_id in self.df['user_id'].unique():
            user_txns = self.df[self.df['user_id'] == user_id]

            features = {
                'txn_count': len(user_txns),
                'amount_mean': user_txns['amount'].mean(),
                'amount_std': user_txns['amount'].std() if len(user_txns) > 1 else 0,
                'merchant_diversity': user_txns['merchant_id'].nunique() if 'merchant_id' in self.df.columns else 0,
                'country_diversity': user_txns['country'].nunique() if 'country' in self.df.columns else 0
            }

            user_features.append(list(features.values()))
            user_ids.append(user_id)

        if len(user_features) < 5:  # Need enough data for ML
            return

        # Train Isolation Forest
        X = np.array(user_features)
        clf = IsolationForest(contamination=0.1, random_state=42)
        predictions = clf.fit_predict(X)

        # Flag anomalies (-1 = anomaly)
        for i, pred in enumerate(predictions):
            if pred == -1:
                user_id = user_ids[i]
                user_txns = self.df[self.df['user_id'] == user_id]
                sample_txns = user_txns.head(3).to_dict('records')

                features = user_features[i]

                explanation = (
                    f"User {user_id}'s transaction pattern shows unusual combinations of behavioral signals. "
                    f"ML analysis detected: {int(features[0])} transactions, "
                    f"${features[1]:.2f} average amount, "
                    f"{int(features[3])} merchants, "
                    f"{int(features[4])} countries. "
                    f"While each factor alone may be normal, this combination is statistically atypical "
                    f"and warrants manual review. This pattern often appears in sophisticated fraud "
                    f"that evades simple rule-based detection."
                )

                pattern = FraudPattern(
                    pattern_id="ML_ANOMALY",
                    title="ML-Detected Behavioral Anomaly",
                    severity="MEDIUM",
                    explanation=explanation,
                    affected_entities=[str(user_id)],
                    affected_count=int(features[0]),
                    sample_transactions=sample_txns,
                    metadata={
                        "txn_count": int(features[0]),
                        "amount_mean": float(features[1]),
                        "amount_std": float(features[2]),
                        "merchant_diversity": int(features[3]),
                        "country_diversity": int(features[4])
                    }
                )
                self.patterns.append(pattern)

    def _pattern_to_dict(self, pattern: FraudPattern) -> Dict[str, Any]:
        """Convert FraudPattern dataclass to dictionary"""
        return {
            "pattern_id": pattern.pattern_id,
            "title": pattern.title,
            "severity": pattern.severity,
            "explanation": pattern.explanation,
            "affected_entities": pattern.affected_entities,
            "affected_count": pattern.affected_count,
            "sample_transactions": pattern.sample_transactions[:3],  # Limit samples
            "metadata": pattern.metadata
        }
