"""
HDBSCAN-Based Fraud Ring Detection
====================================

Implements density-based clustering using HDBSCAN to identify fraud rings
based on behavioral similarity and transaction patterns.

HDBSCAN advantages:
- Finds clusters of varying densities
- Robust to parameter selection
- Hierarchical structure reveals nested fraud rings
- Single intuitive parameter: min_cluster_size
- Automatically identifies noise/outliers

Based on 2024-2025 research from industry leaders (NVIDIA, Neo4j, academic papers)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


@dataclass
class FraudCluster:
    """Represents a fraud cluster detected by HDBSCAN."""
    cluster_id: int
    members: List[str]
    size: int
    risk_score: float
    cohesion_score: float  # How tightly clustered
    detection_method: str
    behavioral_profile: Dict[str, float]
    outlier_scores: List[float]


class HDBSCANFraudDetector:
    """
    Density-based fraud ring detection using HDBSCAN clustering.

    Clusters users based on behavioral features:
    - Transaction patterns
    - Amount distributions
    - Temporal behavior
    - Merchant preferences
    - Geographic patterns
    """

    def __init__(self, min_cluster_size: int = 3, min_samples: int = 2):
        """
        Initialize HDBSCAN detector.

        Args:
            min_cluster_size: Minimum fraud ring size (default: 3 users)
            min_samples: Minimum evidence threshold (default: 2)
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.df = None
        self.user_features = None
        self.clusters = []
        self.hdbscan_available = False

        # Try to import HDBSCAN
        try:
            import hdbscan
            self.hdbscan = hdbscan
            self.hdbscan_available = True
        except ImportError:
            # Fallback to scikit-learn if available
            try:
                from sklearn.cluster import HDBSCAN
                self.hdbscan = HDBSCAN
                self.hdbscan_available = True
            except ImportError:
                pass

    def load_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        """Load and prepare transaction data."""
        self.df = pd.DataFrame(transactions)

        if not self.df.empty:
            # Convert timestamp
            if 'timestamp' in self.df.columns:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
            # Ensure numeric amount
            if 'amount' in self.df.columns:
                self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')

    def detect_clusters(self) -> List[FraudCluster]:
        """
        Detect fraud rings using HDBSCAN clustering.

        Returns:
            List of detected fraud clusters
        """
        if self.df is None or self.df.empty:
            return []

        if 'user_id' not in self.df.columns:
            return []

        # Extract user-level features
        self.user_features = self._extract_user_features()

        if self.user_features.empty or len(self.user_features) < self.min_cluster_size:
            return []

        # Perform clustering
        if self.hdbscan_available:
            clusters = self._cluster_with_hdbscan()
        else:
            # Fallback to simple distance-based clustering
            clusters = self._cluster_fallback()

        self.clusters = clusters
        return clusters

    def _extract_user_features(self) -> pd.DataFrame:
        """
        Extract behavioral features for each user.

        Features include:
        - Transaction count and frequency
        - Amount statistics (mean, std, max, min)
        - Merchant diversity
        - Geographic diversity
        - Temporal patterns
        - Velocity metrics
        """
        if 'user_id' not in self.df.columns:
            return pd.DataFrame()

        user_features = []

        for user_id in self.df['user_id'].unique():
            user_txns = self.df[self.df['user_id'] == user_id]

            features = {
                'user_id': user_id,
                'transaction_count': len(user_txns),
            }

            # Amount features
            if 'amount' in user_txns.columns:
                amounts = user_txns['amount'].dropna()
                if len(amounts) > 0:
                    features['amount_mean'] = amounts.mean()
                    features['amount_std'] = amounts.std() if len(amounts) > 1 else 0
                    features['amount_max'] = amounts.max()
                    features['amount_min'] = amounts.min()
                    features['amount_range'] = amounts.max() - amounts.min()
                    features['amount_cv'] = (amounts.std() / amounts.mean()) if amounts.mean() > 0 else 0
                else:
                    features.update({
                        'amount_mean': 0, 'amount_std': 0, 'amount_max': 0,
                        'amount_min': 0, 'amount_range': 0, 'amount_cv': 0
                    })
            else:
                features.update({
                    'amount_mean': 0, 'amount_std': 0, 'amount_max': 0,
                    'amount_min': 0, 'amount_range': 0, 'amount_cv': 0
                })

            # Merchant diversity
            if 'merchant_id' in user_txns.columns:
                features['merchant_count'] = user_txns['merchant_id'].nunique()
                features['merchant_diversity'] = features['merchant_count'] / len(user_txns)
            else:
                features['merchant_count'] = 0
                features['merchant_diversity'] = 0

            # Geographic features
            if 'country' in user_txns.columns:
                features['country_count'] = user_txns['country'].nunique()
            else:
                features['country_count'] = 0

            # Device features
            if 'device_id' in user_txns.columns:
                features['device_count'] = user_txns['device_id'].nunique()
            else:
                features['device_count'] = 0

            # Temporal features
            if 'timestamp' in user_txns.columns and user_txns['timestamp'].notna().any():
                timestamps = user_txns['timestamp'].dropna()
                if len(timestamps) > 1:
                    # Transaction frequency (transactions per hour)
                    time_span = (timestamps.max() - timestamps.min()).total_seconds() / 3600
                    features['txn_frequency'] = len(timestamps) / max(time_span, 1)

                    # Hour of day patterns
                    hours = timestamps.dt.hour
                    features['hour_mean'] = hours.mean()
                    features['hour_std'] = hours.std()
                else:
                    features['txn_frequency'] = 0
                    features['hour_mean'] = 12
                    features['hour_std'] = 0
            else:
                features['txn_frequency'] = 0
                features['hour_mean'] = 12
                features['hour_std'] = 0

            # Velocity score (transactions in short bursts)
            features['velocity_score'] = min(1.0, len(user_txns) / 10)

            user_features.append(features)

        df_features = pd.DataFrame(user_features)
        df_features = df_features.set_index('user_id')

        # Fill any remaining NaN values
        df_features = df_features.fillna(0)

        return df_features

    def _cluster_with_hdbscan(self) -> List[FraudCluster]:
        """Perform HDBSCAN clustering on user features."""
        if self.user_features.empty:
            return []

        # Prepare feature matrix
        X = self.user_features.values

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Optional: Reduce dimensionality if many features
        if X_scaled.shape[1] > 10:
            pca = PCA(n_components=min(10, X_scaled.shape[1]))
            X_scaled = pca.fit_transform(X_scaled)

        # Fit HDBSCAN
        try:
            if hasattr(self.hdbscan, 'HDBSCAN'):
                # scikit-learn HDBSCAN
                clusterer = self.hdbscan.HDBSCAN(
                    min_cluster_size=self.min_cluster_size,
                    min_samples=self.min_samples,
                    cluster_selection_epsilon=0.0,
                    metric='euclidean'
                )
                labels = clusterer.fit_predict(X_scaled)
                probabilities = getattr(clusterer, 'probabilities_', np.ones(len(labels)))
            else:
                # hdbscan library
                clusterer = self.hdbscan.HDBSCAN(
                    min_cluster_size=self.min_cluster_size,
                    min_samples=self.min_samples,
                    cluster_selection_epsilon=0.5,
                    metric='euclidean'
                )
                labels = clusterer.fit_predict(X_scaled)
                probabilities = clusterer.probabilities_

        except Exception as e:
            return []

        # Extract clusters
        clusters = []
        unique_labels = set(labels)

        for label in unique_labels:
            if label == -1:  # Noise points
                continue

            cluster_mask = labels == label
            cluster_members = self.user_features.index[cluster_mask].tolist()
            cluster_probs = probabilities[cluster_mask]

            if len(cluster_members) < self.min_cluster_size:
                continue

            # Calculate cluster metrics
            cohesion_score = float(np.mean(cluster_probs))

            # Risk score based on behavioral profile
            cluster_features = self.user_features.loc[cluster_members]
            behavioral_profile = self._calculate_behavioral_profile(cluster_features)
            risk_score = self._calculate_cluster_risk(behavioral_profile, cohesion_score)

            cluster = FraudCluster(
                cluster_id=int(label),
                members=[str(m) for m in cluster_members],
                size=len(cluster_members),
                risk_score=risk_score,
                cohesion_score=cohesion_score,
                detection_method="HDBSCAN Density Clustering",
                behavioral_profile=behavioral_profile,
                outlier_scores=cluster_probs.tolist()
            )

            clusters.append(cluster)

        # Sort by risk score
        clusters.sort(key=lambda x: x.risk_score, reverse=True)

        return clusters

    def _cluster_fallback(self) -> List[FraudCluster]:
        """
        Fallback clustering method using simple distance-based grouping.

        Used when HDBSCAN is not available.
        """
        from sklearn.cluster import DBSCAN

        if self.user_features.empty:
            return []

        # Prepare feature matrix
        X = self.user_features.values

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Use DBSCAN as fallback
        clusterer = DBSCAN(eps=0.5, min_samples=self.min_samples)
        labels = clusterer.fit_predict(X_scaled)

        # Extract clusters
        clusters = []
        unique_labels = set(labels)

        for label in unique_labels:
            if label == -1:  # Noise
                continue

            cluster_mask = labels == label
            cluster_members = self.user_features.index[cluster_mask].tolist()

            if len(cluster_members) < self.min_cluster_size:
                continue

            # Calculate metrics
            cluster_features = self.user_features.loc[cluster_members]
            behavioral_profile = self._calculate_behavioral_profile(cluster_features)
            risk_score = self._calculate_cluster_risk(behavioral_profile, 0.7)

            cluster = FraudCluster(
                cluster_id=int(label),
                members=[str(m) for m in cluster_members],
                size=len(cluster_members),
                risk_score=risk_score,
                cohesion_score=0.7,
                detection_method="DBSCAN Clustering (Fallback)",
                behavioral_profile=behavioral_profile,
                outlier_scores=[]
            )

            clusters.append(cluster)

        return clusters

    def _calculate_behavioral_profile(self, cluster_features: pd.DataFrame) -> Dict[str, float]:
        """Calculate aggregate behavioral profile for a cluster."""
        profile = {}

        for col in cluster_features.columns:
            if cluster_features[col].dtype in [np.float64, np.int64]:
                profile[f'{col}_mean'] = float(cluster_features[col].mean())
                profile[f'{col}_std'] = float(cluster_features[col].std())

        return profile

    def _calculate_cluster_risk(self, behavioral_profile: Dict[str, float], cohesion: float) -> float:
        """
        Calculate risk score for a cluster based on its behavioral profile.

        High risk indicators:
        - High transaction velocity
        - High merchant diversity (card testing)
        - High geographic diversity (credential sharing)
        - Low cohesion (diverse but coordinated)
        - High transaction counts
        """
        risk = 0.0

        # Transaction velocity
        velocity = behavioral_profile.get('txn_frequency_mean', 0)
        if velocity > 5:  # More than 5 transactions per hour
            risk += 0.2

        # Merchant diversity (card testing)
        merchant_diversity = behavioral_profile.get('merchant_diversity_mean', 0)
        if merchant_diversity > 0.5:  # High diversity
            risk += 0.2

        # Geographic diversity
        country_count = behavioral_profile.get('country_count_mean', 0)
        if country_count > 2:
            risk += 0.15

        # Transaction count
        txn_count = behavioral_profile.get('transaction_count_mean', 0)
        if txn_count > 5:
            risk += 0.15

        # Device diversity
        device_count = behavioral_profile.get('device_count_mean', 0)
        if device_count > 2:
            risk += 0.15

        # Cohesion score (tight clustering = more suspicious)
        if cohesion > 0.8:
            risk += 0.15

        return min(1.0, risk)

    def get_report(self) -> Dict[str, Any]:
        """Generate comprehensive clustering report."""
        if not self.clusters:
            return {
                'detection_method': 'HDBSCAN Clustering',
                'total_clusters_detected': 0,
                'clusters': [],
                'summary': {
                    'high_risk_clusters': 0,
                    'medium_risk_clusters': 0,
                    'low_risk_clusters': 0,
                    'total_users_in_clusters': 0
                }
            }

        high_risk = [c for c in self.clusters if c.risk_score > 0.7]
        medium_risk = [c for c in self.clusters if 0.5 < c.risk_score <= 0.7]
        low_risk = [c for c in self.clusters if c.risk_score <= 0.5]

        return {
            'detection_method': 'HDBSCAN Clustering',
            'total_clusters_detected': len(self.clusters),
            'clusters': [{
                'cluster_id': c.cluster_id,
                'members': c.members,
                'size': c.size,
                'risk_score': c.risk_score,
                'cohesion_score': c.cohesion_score,
                'detection_method': c.detection_method,
                'behavioral_profile': c.behavioral_profile,
                'severity': 'HIGH' if c.risk_score > 0.7 else 'MEDIUM' if c.risk_score > 0.5 else 'LOW'
            } for c in self.clusters],
            'summary': {
                'high_risk_clusters': len(high_risk),
                'medium_risk_clusters': len(medium_risk),
                'low_risk_clusters': len(low_risk),
                'total_users_in_clusters': len(set(user for c in self.clusters for user in c.members)),
                'avg_cluster_size': np.mean([c.size for c in self.clusters]) if self.clusters else 0,
                'avg_risk_score': np.mean([c.risk_score for c in self.clusters]) if self.clusters else 0
            }
        }
