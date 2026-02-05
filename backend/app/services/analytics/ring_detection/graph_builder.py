"""
Graph-based fraud ring detection.

Builds a heterogeneous graph from transactions, projects to user-only graph,
and detects communities via Louvain (fallback to connected components).

Includes high-degree entity capping to prevent shared public infrastructure
from creating false communities.
"""

import networkx as nx
import pandas as pd
import math
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from .schemas import RingCandidate


# Entity types used for graph edges (strong coordination signals only).
# card_bin, email_domain, merchant_id are too widely shared to serve as
# graph edges; they are used as features for classification instead.
ENTITY_WEIGHTS = {
    "device_fingerprint": 3.0,
    "ip_prefix_24": 2.0,
}

# Maximum users an entity node can connect before it's considered "public"
# and gets downweighted or excluded from the projection.
MAX_ENTITY_DEGREE = {
    "device_fingerprint": 60,
    "ip_prefix_24": 60,
}

# Degree above which we start applying a discount factor
HIGH_DEGREE_SOFT_CAP = {
    "device_fingerprint": 10,
    "ip_prefix_24": 15,
}

# Minimum ring size (relaxed for permissive discovery; confirmation phase gates)
MIN_RING_SIZE = 4

# Minimum edge weight in projected graph to keep an edge.
# With only device (3.0) and IP (2.0) signals, a single shared device
# already meets this threshold. Two shared IPs = 4.0 also qualifies.
MIN_PROJECTED_EDGE_WEIGHT = 2.0

# Minimum ring quality thresholds (relaxed for discovery; confirmation gates later)
MIN_SHARED_STRONG_SIGNALS = 0   # allow graph-only communities
MIN_RING_SIZE_NO_INFRA = 8      # larger minimum when no shared infrastructure
MIN_RING_DENSITY_SMALL = 0.005  # for rings < 50 members
MIN_RING_DENSITY_LARGE = 0.001  # for rings >= 50 members

# Resolution parameter for Louvain
LOUVAIN_RESOLUTION = 1.0


class FraudRingGraphBuilder:
    """Builds transaction graphs and detects fraud ring communities."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.hetero_graph: nx.Graph = nx.Graph()
        self.user_graph: nx.Graph = nx.Graph()
        self._entity_user_counts: Dict[str, int] = {}

    def build_heterogeneous_graph(self) -> nx.Graph:
        """
        Create bipartite graph with user nodes and entity nodes.
        Uses vectorized pandas groupby instead of iterrows for performance.
        """
        G = nx.Graph()
        df = self.df

        for entity_col, weight in ENTITY_WEIGHTS.items():
            if entity_col not in df.columns:
                continue

            # Get unique (user_id, entity_val) pairs and their counts
            subset = df[["user_id", entity_col]].dropna()
            subset = subset[subset[entity_col].astype(str).str.strip() != ""]
            subset = subset[subset["user_id"].astype(str).str.strip() != ""]
            if subset.empty:
                continue

            subset["user_id"] = subset["user_id"].astype(str)
            subset[entity_col] = subset[entity_col].astype(str)

            # Count unique users per entity for degree capping
            entity_user_counts = subset.groupby(entity_col)["user_id"].nunique()
            hard_cap = MAX_ENTITY_DEGREE.get(entity_col, 200)
            valid_entities = set(entity_user_counts[entity_user_counts <= hard_cap].index)

            # Store counts for later use
            for ent_val, cnt in entity_user_counts.items():
                self._entity_user_counts[f"{entity_col}::{ent_val}"] = cnt

            # Filter to valid entities
            subset = subset[subset[entity_col].isin(valid_entities)]

            # Count edges (user, entity) -> weight * count
            edge_counts = subset.groupby(["user_id", entity_col]).size().reset_index(name="count")

            # Add nodes and edges to graph
            for _, row in edge_counts.iterrows():
                user_node = f"user::{row['user_id']}"
                entity_node = f"{entity_col}::{row[entity_col]}"

                if not G.has_node(user_node):
                    G.add_node(user_node, node_type="user_id", entity_id=row["user_id"])
                if not G.has_node(entity_node):
                    G.add_node(entity_node, node_type=entity_col, entity_id=row[entity_col])

                edge_weight = weight * row["count"]
                if G.has_edge(user_node, entity_node):
                    G[user_node][entity_node]["weight"] += edge_weight
                else:
                    G.add_edge(user_node, entity_node, weight=edge_weight)

        self.hetero_graph = G
        return G

    def _discount_weight(self, entity_type: str, n_users: int, base_weight: float) -> float:
        """Apply logarithmic discount for high-degree entity nodes."""
        soft_cap = HIGH_DEGREE_SOFT_CAP.get(entity_type, 20)
        if n_users <= soft_cap:
            return base_weight
        # Logarithmic decay: weight * soft_cap / (soft_cap + excess)
        excess = n_users - soft_cap
        discount = soft_cap / (soft_cap + excess)
        return base_weight * discount

    def project_user_graph(self) -> nx.Graph:
        """
        Project bipartite graph onto user-only nodes.
        Two users connected if they share any entity node.
        Edge weight = weighted count of shared entities, discounted by entity degree.
        Edges below MIN_PROJECTED_EDGE_WEIGHT are dropped.
        """
        G = self.hetero_graph
        user_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "user_id"]

        UG = nx.Graph()
        for un in user_nodes:
            UG.add_node(un, **G.nodes[un])

        # For each non-user node, connect all its user neighbors
        for node, data in G.nodes(data=True):
            if data.get("node_type") == "user_id":
                continue

            entity_type = data.get("node_type", "")
            base_weight = ENTITY_WEIGHTS.get(entity_type, 1.0)
            neighbors = [n for n in G.neighbors(node) if G.nodes[n].get("node_type") == "user_id"]

            n_users = len(neighbors)
            hard_cap = MAX_ENTITY_DEGREE.get(entity_type, 200)
            if n_users > hard_cap:
                continue

            discounted = self._discount_weight(entity_type, n_users, base_weight)

            # Only create clique edges if entity isn't too widely shared
            # For very high degree but below hard cap, still skip clique creation
            # if it would create too many edges (O(n^2))
            if n_users > 200:
                continue

            for i in range(len(neighbors)):
                for j in range(i + 1, len(neighbors)):
                    u, v = neighbors[i], neighbors[j]
                    if UG.has_edge(u, v):
                        UG[u][v]["weight"] += discounted
                        UG[u][v]["shared_entities"].append(node)
                    else:
                        UG.add_edge(u, v, weight=discounted, shared_entities=[node])

        # Prune weak edges
        weak_edges = [
            (u, v) for u, v, d in UG.edges(data=True)
            if d.get("weight", 0) < MIN_PROJECTED_EDGE_WEIGHT
        ]
        UG.remove_edges_from(weak_edges)

        # Remove isolated nodes after pruning
        isolates = list(nx.isolates(UG))
        UG.remove_nodes_from(isolates)

        self.user_graph = UG
        return UG

    def detect_communities_louvain(self, user_graph: nx.Graph) -> List[RingCandidate]:
        """
        Run Louvain community detection on the user graph.
        Filter to size >= MIN_RING_SIZE users with quality gates.
        """
        if user_graph.number_of_nodes() < MIN_RING_SIZE:
            return []

        try:
            # Use louvain_communities (fast Louvain algorithm) instead of
            # greedy_modularity_communities (CNM, much slower on large graphs)
            communities = list(
                nx.community.louvain_communities(
                    user_graph, weight="weight", resolution=LOUVAIN_RESOLUTION,
                    seed=42,
                )
            )
        except Exception:
            return []

        candidates = []
        for idx, community in enumerate(communities):
            members = [
                user_graph.nodes[n].get("entity_id", n.replace("user::", ""))
                for n in community
                if user_graph.nodes.get(n, {}).get("node_type") == "user_id"
            ]

            if len(members) < MIN_RING_SIZE:
                continue

            # Compute subgraph density
            subgraph = user_graph.subgraph(community)
            n_nodes = subgraph.number_of_nodes()
            n_edges = subgraph.number_of_edges()
            max_edges = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 1
            density = n_edges / max_edges if max_edges > 0 else 0.0

            # Quality gate: minimum density
            min_density = MIN_RING_DENSITY_SMALL if n_nodes < 50 else MIN_RING_DENSITY_LARGE
            if density < min_density:
                continue

            # Enumerate shared attributes from the heterogeneous graph
            shared = self._enumerate_shared_attributes(community)

            # Quality gate: if no shared infra, require larger community
            n_shared_devices = len(shared.get("device_fingerprint", []))
            n_shared_ips = len(shared.get("ip_prefix_24", []))
            total_shared = n_shared_devices + n_shared_ips
            if total_shared < MIN_SHARED_STRONG_SIGNALS:
                continue
            if total_shared == 0 and len(members) < MIN_RING_SIZE_NO_INFRA:
                continue

            candidate = RingCandidate(
                ring_id=f"ring_{idx:03d}",
                member_user_ids=members,
                size=len(members),
                density=round(density, 4),
                shared_devices=shared.get("device_fingerprint", []),
                shared_ip_prefixes=shared.get("ip_prefix_24", []),
                shared_bins=shared.get("card_bin", []),
                shared_merchants=shared.get("merchant_id", []),
                shared_email_domains=shared.get("email_domain", []),
                detection_method="louvain_modularity",
            )
            candidates.append(candidate)

        return candidates

    def detect_communities_connected_components(
        self, user_graph: nx.Graph
    ) -> List[RingCandidate]:
        """Fallback: use connected components."""
        if user_graph.number_of_nodes() < MIN_RING_SIZE:
            return []

        candidates = []
        for idx, component in enumerate(nx.connected_components(user_graph)):
            members = [
                user_graph.nodes[n].get("entity_id", n.replace("user::", ""))
                for n in component
                if user_graph.nodes.get(n, {}).get("node_type") == "user_id"
            ]

            if len(members) < MIN_RING_SIZE:
                continue

            subgraph = user_graph.subgraph(component)
            n_nodes = subgraph.number_of_nodes()
            n_edges = subgraph.number_of_edges()
            max_edges = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 1
            density = n_edges / max_edges if max_edges > 0 else 0.0

            shared = self._enumerate_shared_attributes(component)

            n_shared_devices = len(shared.get("device_fingerprint", []))
            n_shared_ips = len(shared.get("ip_prefix_24", []))
            if n_shared_devices + n_shared_ips < MIN_SHARED_STRONG_SIGNALS:
                continue

            candidate = RingCandidate(
                ring_id=f"ring_cc_{idx:03d}",
                member_user_ids=members,
                size=len(members),
                density=round(density, 4),
                shared_devices=shared.get("device_fingerprint", []),
                shared_ip_prefixes=shared.get("ip_prefix_24", []),
                shared_bins=shared.get("card_bin", []),
                shared_merchants=shared.get("merchant_id", []),
                shared_email_domains=shared.get("email_domain", []),
                detection_method="connected_components",
            )
            candidates.append(candidate)

        return candidates

    def build_and_detect(self) -> List[RingCandidate]:
        """Orchestrate: build graph -> project -> Louvain (fallback to CC)."""
        self.build_heterogeneous_graph()
        self.project_user_graph()

        candidates = self.detect_communities_louvain(self.user_graph)
        if not candidates:
            candidates = self.detect_communities_connected_components(self.user_graph)

        return candidates

    def _enumerate_shared_attributes(
        self, user_node_set: set
    ) -> Dict[str, List[str]]:
        """
        For a set of user nodes in the community, find entity nodes
        in the heterogeneous graph shared by 2+ community members.
        """
        G = self.hetero_graph
        shared: Dict[str, List[str]] = defaultdict(list)

        # Collect all entity neighbors of community user nodes
        entity_to_users: Dict[str, Set[str]] = defaultdict(set)
        for user_node in user_node_set:
            if user_node not in G:
                continue
            for neighbor in G.neighbors(user_node):
                ntype = G.nodes[neighbor].get("node_type", "")
                if ntype != "user_id":
                    entity_to_users[neighbor].add(user_node)

        for entity_node, users in entity_to_users.items():
            if len(users) >= 2:
                ntype = G.nodes[entity_node].get("node_type", "")
                entity_id = G.nodes[entity_node].get("entity_id", entity_node)
                shared[ntype].append(entity_id)

        return dict(shared)
