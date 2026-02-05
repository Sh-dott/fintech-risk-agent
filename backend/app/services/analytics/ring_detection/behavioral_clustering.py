"""
Behavioral clustering discovery for fraud ring detection.

Uses HDBSCAN on user feature vectors to find groups of users with
similar anomalous behavior, regardless of shared infrastructure.
"""

import numpy as np
import pandas as pd
from typing import List

from .schemas import CandidateCluster


# Features used for clustering -- ordered by discriminative power
CLUSTERING_FEATURES = [
    "txn_count", "amount_mean", "amount_std", "amount_max",
    "micro_amount_ratio", "threshold_amount_ratio",
    "merchant_concentration_hhi", "merchant_concentration_gini",
    "burstiness_cv", "burst_window_count", "mean_inter_arrival_sec",
    "device_sharing_score", "subnet_sharing_score_24",
    "geo_mismatch_rate",
    # New features from previously unused columns
    "account_age_days", "kyc_level_numeric", "login_failures_24h",
    "merchant_risk_mean", "cross_border_ratio",
    "n_unique_merchants", "n_unique_bins",
]

# Features with highest separating power (used for anomaly scoring)
ANOMALY_FEATURES = [
    "txn_count", "n_unique_merchants", "n_unique_bins",
    "burstiness_cv", "micro_amount_ratio",
    "login_failures_24h", "merchant_risk_mean",
    "device_sharing_score", "geo_mismatch_rate",
]


class BehavioralClusterer:
    """Discovers candidate rings via behavioral feature similarity using HDBSCAN."""

    def __init__(
        self,
        min_cluster_size: int = 8,
        min_samples: int = 5,
        anomaly_percentile: float = 0.88,
    ):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.anomaly_percentile = anomaly_percentile

    def discover(self, user_features: pd.DataFrame) -> List[CandidateCluster]:
        """
        Run HDBSCAN on user feature vectors.

        Only clusters users whose anomaly score exceeds the anomaly_percentile
        threshold, to avoid clustering normal users together.
        """
        if user_features.empty or "user_id" not in user_features.columns:
            return []

        uf = user_features.set_index("user_id") if "user_id" in user_features.columns else user_features.copy()

        # Step 1: Compute anomaly scores and filter to anomalous users
        anomaly_scores = self._compute_anomaly_scores(uf)
        threshold = np.percentile(anomaly_scores, self.anomaly_percentile * 100)
        mask = anomaly_scores >= threshold

        anomalous_users = uf[mask].copy()
        anomalous_scores = anomaly_scores[mask]

        if len(anomalous_users) < self.min_cluster_size:
            print(f"[BehavioralClusterer] Only {len(anomalous_users)} anomalous users "
                  f"(need {self.min_cluster_size}). Skipping.")
            return []

        print(f"[BehavioralClusterer] {len(anomalous_users)} anomalous users "
              f"(top {(1 - self.anomaly_percentile)*100:.0f}%, threshold={threshold:.2f})")

        # Step 2: Build feature matrix, standardize
        X = self._build_feature_matrix(anomalous_users)
        if X.shape[1] == 0:
            return []

        from sklearn.preprocessing import StandardScaler
        X_scaled = StandardScaler().fit_transform(X)

        # Step 3: HDBSCAN clustering
        labels = self._run_hdbscan(X_scaled)
        if labels is None:
            return []

        # Step 4: Convert to CandidateClusters
        candidates = []
        user_ids = anomalous_users.index.tolist()
        for cluster_label in sorted(set(labels)):
            if cluster_label == -1:
                continue
            member_mask = labels == cluster_label
            members = [user_ids[i] for i in range(len(user_ids)) if member_mask[i]]
            if len(members) < self.min_cluster_size:
                continue

            cluster_score = float(np.mean(anomalous_scores[member_mask]))

            candidates.append(CandidateCluster(
                cluster_id=f"behav_{cluster_label:03d}",
                member_user_ids=members,
                size=len(members),
                discovery_method="behavioral_hdbscan",
                discovery_score=cluster_score,
                metadata={
                    "anomaly_score_mean": round(cluster_score, 4),
                    "anomaly_score_threshold": round(float(threshold), 4),
                    "n_features": X.shape[1],
                },
            ))

        print(f"[BehavioralClusterer] Found {len(candidates)} behavioral clusters")
        return candidates

    def _compute_anomaly_scores(self, user_features: pd.DataFrame) -> np.ndarray:
        """
        Composite anomaly score per user: sum of capped z-scores across key features.
        Higher = more anomalous.
        """
        scores = np.zeros(len(user_features))
        n_features_used = 0

        for col in ANOMALY_FEATURES:
            if col not in user_features.columns:
                continue
            vals = user_features[col].fillna(0).values.astype(float)
            mean = np.mean(vals)
            std = np.std(vals)
            if std > 0:
                z = np.abs((vals - mean) / std)
                scores += np.clip(z, 0, 3)
                n_features_used += 1

        if n_features_used > 0:
            scores /= n_features_used
        return scores

    def _build_feature_matrix(self, user_features: pd.DataFrame) -> np.ndarray:
        """Extract clustering features, impute missing."""
        available = [c for c in CLUSTERING_FEATURES if c in user_features.columns]
        if not available:
            return np.empty((len(user_features), 0))
        X = user_features[available].fillna(0).values.astype(float)
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    def _run_hdbscan(self, X: np.ndarray) -> np.ndarray:
        """Try HDBSCAN from hdbscan package, then sklearn, then fallback to KMeans."""
        # Try hdbscan package first
        try:
            from hdbscan import HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                metric="euclidean",
                cluster_selection_method="eom",
            )
            return clusterer.fit_predict(X)
        except ImportError:
            pass

        # Try sklearn HDBSCAN (sklearn >= 1.3)
        try:
            from sklearn.cluster import HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                metric="euclidean",
                cluster_selection_method="eom",
            )
            return clusterer.fit_predict(X)
        except (ImportError, TypeError):
            pass

        # Fallback: DBSCAN
        try:
            from sklearn.cluster import DBSCAN
            clusterer = DBSCAN(eps=1.5, min_samples=self.min_samples)
            print("[BehavioralClusterer] Falling back to DBSCAN")
            return clusterer.fit_predict(X)
        except ImportError:
            print("[BehavioralClusterer] No clustering algorithm available")
            return None
