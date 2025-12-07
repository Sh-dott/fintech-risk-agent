"""
Entity Graph Analysis - Fraud Ring & Mule Network Detection

Maintains relationships between users, devices, merchants, and payment methods
to identify suspicious patterns indicative of organized fraud.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class EntityType(Enum):
    """Entity node types in the graph."""
    USER = "user"
    DEVICE = "device"
    IP_ADDRESS = "ip_address"
    PAYMENT_METHOD = "payment_method"
    MERCHANT = "merchant"
    PHONE = "phone"
    EMAIL = "email"


class RelationType(Enum):
    """Edge relationship types."""
    OWNS = "owns"  # user owns device, payment method
    USES = "uses"  # user uses IP, merchant
    SHARED_WITH = "shared_with"  # device shared with other users
    CONNECTED_TO = "connected_to"  # transaction between entities
    LINKED_TO = "linked_to"  # KYC verification link


@dataclass
class EntityNode:
    """Represents an entity in the graph."""
    entity_id: str
    entity_type: EntityType
    attributes: Dict
    risk_score: float = 0.0
    last_seen: str = ""


@dataclass
class EntityEdge:
    """Represents a relationship between entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0  # Strength of connection
    created_at: str = ""
    transaction_count: int = 0


class EntityGraph:
    """
    In-memory entity graph for fraud ring and mule network detection.

    In production: use Neo4j, ArangoDB, or Cosmos DB for scalability.
    """

    def __init__(self):
        """Initialize the graph structure."""
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[EntityEdge] = []
        self.adjacency_list: Dict[str, List[str]] = {}

    def add_entity(self, entity_id: str, entity_type: EntityType, attributes: Dict) -> None:
        """Add a node to the graph."""
        self.nodes[entity_id] = EntityNode(
            entity_id=entity_id,
            entity_type=entity_type,
            attributes=attributes
        )
        if entity_id not in self.adjacency_list:
            self.adjacency_list[entity_id] = []

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        transaction_count: int = 0
    ) -> None:
        """Add an edge between two entities."""
        # Ensure nodes exist
        if source_id not in self.nodes:
            self.add_entity(source_id, EntityType.USER, {})
        if target_id not in self.nodes:
            self.add_entity(target_id, EntityType.DEVICE, {})

        # Add edge
        self.edges.append(EntityEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            transaction_count=transaction_count
        ))

        # Update adjacency list
        self.adjacency_list[source_id].append(target_id)

    def detect_mule_network(
        self,
        user_id: str,
        threshold_connections: int = 5
    ) -> Tuple[float, List[str]]:
        """
        Detect if a user is part of a mule network.

        Indicators:
        - Many devices used from different locations (geovelocity)
        - Many payment methods linked to account
        - Rapid cross-merchant transactions
        - Account newly created
        """
        risk_score = 0.0
        suspicious_patterns = []

        if user_id not in self.nodes:
            return risk_score, suspicious_patterns

        # Get all connected entities
        connected = self._bfs_neighbors(user_id, max_depth=2)

        # Count entities by type
        device_count = sum(
            1 for eid in connected if eid in self.nodes
            and self.nodes[eid].entity_type == EntityType.DEVICE
        )
        payment_method_count = sum(
            1 for eid in connected if eid in self.nodes
            and self.nodes[eid].entity_type == EntityType.PAYMENT_METHOD
        )

        # Mule indicators
        if device_count > threshold_connections:
            risk_score += 0.3
            suspicious_patterns.append(f"HIGH_DEVICE_COUNT_{device_count}")

        if payment_method_count > 3:
            risk_score += 0.2
            suspicious_patterns.append(f"MULTIPLE_PAYMENT_METHODS_{payment_method_count}")

        # Check for shared devices (account takeover or ring)
        shared_devices = self._find_shared_devices(user_id)
        if shared_devices:
            risk_score += 0.25
            suspicious_patterns.append(f"SHARED_DEVICES_{len(shared_devices)}")

        return min(risk_score, 1.0), suspicious_patterns

    def detect_fraud_ring(
        self,
        user_id: str,
        depth: int = 3
    ) -> Tuple[float, List[str], List[str]]:
        """
        Detect organized fraud rings (coordinated account abuse).

        Red flags:
        - Multiple users sharing devices
        - Rapid device switching + merchant changes
        - Users linking same payment methods
        - Accounts created in sequence from same IP
        """
        risk_score = 0.0
        suspicious_patterns = []
        related_users = []

        if user_id not in self.nodes:
            return risk_score, suspicious_patterns, related_users

        # BFS to find connected users
        all_connected = self._bfs_neighbors(user_id, max_depth=depth)
        users_in_network = [
            eid for eid in all_connected
            if eid in self.nodes and self.nodes[eid].entity_type == EntityType.USER
        ]
        related_users = users_in_network

        # Ring indicators
        shared_devices = self._find_shared_resources(users_in_network, EntityType.DEVICE)
        if len(shared_devices) > 1:
            risk_score += 0.35
            suspicious_patterns.append(f"SHARED_DEVICES_RING_{len(shared_devices)}")

        shared_payment_methods = self._find_shared_resources(
            users_in_network, EntityType.PAYMENT_METHOD
        )
        if len(shared_payment_methods) > 0:
            risk_score += 0.25
            suspicious_patterns.append(f"SHARED_PAYMENTS_{len(shared_payment_methods)}")

        shared_ips = self._find_shared_resources(users_in_network, EntityType.IP_ADDRESS)
        if len(shared_ips) > 1:
            risk_score += 0.20
            suspicious_patterns.append(f"SHARED_IPS_{len(shared_ips)}")

        return min(risk_score, 1.0), suspicious_patterns, related_users

    def find_related_transactions(
        self,
        user_id: str,
        relation_types: Optional[List[RelationType]] = None
    ) -> List[Tuple[str, str, RelationType, int]]:
        """
        Find all transactions involving a user and related entities.

        Returns: List of (source_id, target_id, relation_type, count)
        """
        results = []

        for edge in self.edges:
            if (edge.source_id == user_id or edge.target_id == user_id):
                if relation_types is None or edge.relation_type in relation_types:
                    results.append((
                        edge.source_id,
                        edge.target_id,
                        edge.relation_type,
                        edge.transaction_count
                    ))

        return results

    def _bfs_neighbors(self, start_id: str, max_depth: int = 2) -> Set[str]:
        """BFS to find all neighbors up to max_depth."""
        visited = set()
        queue = [(start_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            if current_id in self.adjacency_list:
                for neighbor_id in self.adjacency_list[current_id]:
                    if neighbor_id not in visited and depth + 1 <= max_depth:
                        queue.append((neighbor_id, depth + 1))

        return visited

    def _find_shared_devices(self, user_id: str) -> List[str]:
        """Find devices used by multiple users (shared account indicator)."""
        shared = []

        for edge in self.edges:
            if edge.source_id == user_id and edge.relation_type == RelationType.OWNS:
                device_id = edge.target_id
                # Count how many users own this device
                owner_count = sum(
                    1 for e in self.edges
                    if e.target_id == device_id and e.relation_type == RelationType.OWNS
                )
                if owner_count > 1:
                    shared.append(device_id)

        return shared

    def _find_shared_resources(
        self,
        user_ids: List[str],
        resource_type: EntityType
    ) -> List[str]:
        """Find resources (devices, payment methods, IPs) shared by multiple users."""
        resource_map: Dict[str, int] = {}

        for user_id in user_ids:
            for edge in self.edges:
                if edge.source_id == user_id and edge.relation_type == RelationType.OWNS:
                    resource_id = edge.target_id
                    if resource_id in self.nodes and self.nodes[resource_id].entity_type == resource_type:
                        resource_map[resource_id] = resource_map.get(resource_id, 0) + 1

        # Return resources owned by 2+ users
        return [rid for rid, count in resource_map.items() if count > 1]

    def get_risk_factors(self, entity_id: str) -> Dict[str, float]:
        """Get risk factors for an entity based on graph structure."""
        factors = {}

        if entity_id not in self.nodes:
            return factors

        node = self.nodes[entity_id]

        # Degree centrality (how connected is this entity)
        connections = len([e for e in self.edges if e.source_id == entity_id])
        factors["connection_count"] = min(connections / 10.0, 1.0)

        # Based on entity type, compute risk
        if node.entity_type == EntityType.DEVICE:
            # High-risk if used by many users
            user_count = sum(
                1 for e in self.edges
                if e.target_id == entity_id and e.relation_type == RelationType.OWNS
            )
            factors["shared_by_users"] = min(user_count / 5.0, 1.0)

        elif node.entity_type == EntityType.IP_ADDRESS:
            # High-risk if spawning many accounts
            created_accounts = sum(
                1 for e in self.edges
                if e.source_id == entity_id and e.relation_type == RelationType.LINKED_TO
            )
            factors["account_creation_velocity"] = min(created_accounts / 20.0, 1.0)

        return factors


def main():
    """Demo graph analysis."""
    graph = EntityGraph()

    # Build a simple ring structure
    graph.add_entity("usr_1", EntityType.USER, {"kyc": True})
    graph.add_entity("usr_2", EntityType.USER, {"kyc": True})
    graph.add_entity("dev_1", EntityType.DEVICE, {"model": "iPhone"})
    graph.add_entity("dev_2", EntityType.DEVICE, {"model": "Android"})
    graph.add_entity("pm_1", EntityType.PAYMENT_METHOD, {"type": "card"})

    # Create relationships (ring)
    graph.add_relationship("usr_1", "dev_1", RelationType.OWNS)
    graph.add_relationship("usr_2", "dev_1", RelationType.OWNS)  # Shared device!
    graph.add_relationship("usr_1", "dev_2", RelationType.OWNS)
    graph.add_relationship("usr_1", "pm_1", RelationType.OWNS)
    graph.add_relationship("usr_2", "pm_1", RelationType.OWNS)  # Shared payment!

    # Check for mule network
    mule_risk, mule_patterns = graph.detect_mule_network("usr_1")
    print(f"Mule Risk (usr_1): {mule_risk:.2f}")
    print(f"Patterns: {mule_patterns}")

    # Check for fraud ring
    ring_risk, ring_patterns, related = graph.detect_fraud_ring("usr_1")
    print(f"\nFraud Ring Risk (usr_1): {ring_risk:.2f}")
    print(f"Patterns: {ring_patterns}")
    print(f"Related Users: {related}")


if __name__ == "__main__":
    main()
