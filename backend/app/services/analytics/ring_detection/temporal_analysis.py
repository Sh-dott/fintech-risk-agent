"""
Temporal co-occurrence detection for fraud ring discovery.

Finds groups of users who transact in the same narrow time windows
at rates significantly above statistical expectation (lift-based).
"""

import numpy as np
import pandas as pd
import networkx as nx
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from .schemas import CandidateCluster


class TemporalAnalyzer:
    """Detects temporal co-occurrence patterns between users."""

    def __init__(
        self,
        window_minutes: int = 10,
        min_cooccurrences: int = 3,
        min_lift: float = 3.0,
        min_cluster_size: int = 5,
        max_window_users: int = 100,
    ):
        self.window_minutes = window_minutes
        self.min_cooccurrences = min_cooccurrences
        self.min_lift = min_lift
        self.min_cluster_size = min_cluster_size
        self.max_window_users = max_window_users

    def discover_temporal_clusters(
        self, df: pd.DataFrame
    ) -> List[CandidateCluster]:
        """
        Discover user groups with statistically significant temporal co-occurrence.

        1. Bin all transactions into time windows
        2. Record which users are active in each window
        3. Count pairwise user co-occurrence across windows
        4. Filter pairs with co-occurrence significantly above chance (lift)
        5. Build co-occurrence graph, find connected components
        """
        ts_col = None
        for col in ("timestamp", "timestamp_utc"):
            if col in df.columns:
                ts_col = col
                break
        if ts_col is None or "user_id" not in df.columns:
            return []

        temp = df[["user_id", ts_col]].copy()
        temp["_ts"] = pd.to_datetime(temp[ts_col], errors="coerce")
        temp = temp.dropna(subset=["_ts"])
        if temp.empty:
            return []

        temp["user_id"] = temp["user_id"].astype(str)
        temp["_window"] = temp["_ts"].dt.floor(f"{self.window_minutes}min")

        # Users per window
        window_users = temp.groupby("_window")["user_id"].apply(set).to_dict()
        total_windows = len(window_users)
        if total_windows < 2:
            return []

        # Count how many windows each user appears in
        user_window_counts: Dict[str, int] = defaultdict(int)
        for users in window_users.values():
            for u in users:
                user_window_counts[u] += 1

        # Pairwise co-occurrence (skip windows with too many users -- noise)
        cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        for users in window_users.values():
            if len(users) < 2 or len(users) > self.max_window_users:
                continue
            user_list = sorted(users)
            for i in range(len(user_list)):
                for j in range(i + 1, len(user_list)):
                    cooccurrence[(user_list[i], user_list[j])] += 1

        # Filter to statistically significant pairs
        significant_edges = []
        for (u1, u2), count in cooccurrence.items():
            if count < self.min_cooccurrences:
                continue
            p1 = user_window_counts[u1] / total_windows
            p2 = user_window_counts[u2] / total_windows
            expected = p1 * p2 * total_windows
            if expected <= 0:
                continue
            lift = count / expected
            if lift >= self.min_lift:
                significant_edges.append((u1, u2, count, lift))

        if not significant_edges:
            return []

        # Build graph from significant edges, find components
        G = nx.Graph()
        for u1, u2, count, lift in significant_edges:
            G.add_edge(u1, u2, weight=lift, cooccurrence=count)

        candidates = []
        for idx, component in enumerate(nx.connected_components(G)):
            if len(component) < self.min_cluster_size:
                continue
            members = sorted(component)
            subgraph = G.subgraph(component)
            avg_lift = float(np.mean(
                [d["weight"] for _, _, d in subgraph.edges(data=True)]
            ))

            candidates.append(CandidateCluster(
                cluster_id=f"temporal_{idx:03d}",
                member_user_ids=members,
                size=len(members),
                discovery_method="temporal_cooccurrence",
                discovery_score=avg_lift,
                metadata={
                    "avg_lift": round(avg_lift, 2),
                    "n_significant_edges": subgraph.number_of_edges(),
                    "window_minutes": self.window_minutes,
                },
            ))

        print(f"[TemporalAnalyzer] Found {len(candidates)} temporal clusters "
              f"from {len(significant_edges)} significant co-occurrence pairs")
        return candidates

    def compute_pairwise_overlaps(
        self, df: pd.DataFrame, user_set: Set[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        For evidence collection: compute pairwise temporal overlap scores
        for a specific set of users.

        Returns: {user_id: {other_user_id: overlap_score}}
        """
        ts_col = None
        for col in ("timestamp", "timestamp_utc"):
            if col in df.columns:
                ts_col = col
                break
        if ts_col is None:
            return {}

        temp = df[df["user_id"].astype(str).isin(user_set)][["user_id", ts_col]].copy()
        temp["_ts"] = pd.to_datetime(temp[ts_col], errors="coerce")
        temp = temp.dropna(subset=["_ts"])
        if temp.empty:
            return {}

        temp["user_id"] = temp["user_id"].astype(str)
        temp["_window"] = temp["_ts"].dt.floor(f"{self.window_minutes}min")

        # Users per window (only considering our user_set)
        window_users = temp.groupby("_window")["user_id"].apply(set).to_dict()
        total_windows = len(window_users)
        if total_windows < 1:
            return {}

        user_window_counts: Dict[str, int] = defaultdict(int)
        for users in window_users.values():
            for u in users:
                user_window_counts[u] += 1

        # Pairwise co-occurrence
        cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        for users in window_users.values():
            filtered = sorted(users & user_set)
            if len(filtered) < 2:
                continue
            for i in range(len(filtered)):
                for j in range(i + 1, len(filtered)):
                    cooccurrence[(filtered[i], filtered[j])] += 1

        # Compute normalised overlap scores
        result: Dict[str, Dict[str, float]] = defaultdict(dict)
        for (u1, u2), count in cooccurrence.items():
            if count < 2:
                continue
            p1 = user_window_counts.get(u1, 1) / total_windows
            p2 = user_window_counts.get(u2, 1) / total_windows
            expected = max(p1 * p2 * total_windows, 0.01)
            score = min(1.0, count / (expected * self.min_lift))
            if score > 0.1:
                result[u1][u2] = round(score, 3)
                result[u2][u1] = round(score, 3)

        return dict(result)
