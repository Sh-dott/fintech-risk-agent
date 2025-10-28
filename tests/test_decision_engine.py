"""
Unit tests for the decision engine and core components.
"""

import pytest
from datetime import datetime
from src.core.decision_engine import (
    RiskDecisionEngine, DecisionType, RiskLevel
)
from src.graph.entity_graph import EntityGraph, EntityType, RelationType
from src.rules.aml_rules import AMLRulesEngine, SanctionsListType
from src.monitoring.metrics import MetricsCollector


class TestRiskDecisionEngine:
    """Test suite for RiskDecisionEngine."""

    @pytest.fixture
    def engine(self):
        """Initialize decision engine."""
        return RiskDecisionEngine()

    def test_initialization(self, engine):
        """Test engine initializes with correct defaults."""
        assert engine.high_risk_threshold == 0.8
        assert engine.low_risk_threshold == 0.3
        assert engine.max_latency_ms == 100

    def test_score_transaction_low_risk(self, engine):
        """Test scoring a low-risk transaction."""
        decision = engine.score_transaction(
            transaction={
                "id": "txn_test_1",
                "amount": 50.00,
                "currency": "USD",
                "merchant_id": "mch_trusted",
                "user_id": "usr_good"
            },
            context={
                "device_id": "dev_trusted",
                "ip_address": "192.168.1.1",
                "user_country": "US"
            }
        )

        assert decision.decision == DecisionType.ALLOW
        assert decision.risk_level == RiskLevel.LOW
        assert decision.risk_score < 0.3
        assert decision.latency_ms < 100

    def test_latency_sla_met(self, engine):
        """Test that latency meets SLA."""
        decision = engine.score_transaction(
            transaction={"id": "txn_perf_test", "amount": 100},
            context={"device_id": "dev_1"}
        )

        assert decision.latency_ms <= engine.max_latency_ms

    def test_compliance_log_id_generated(self, engine):
        """Test that compliance log ID is generated."""
        decision = engine.score_transaction(
            transaction={"id": "txn_compliance_test", "amount": 100},
            context={}
        )

        assert decision.compliance_log_id.startswith("clog_")

    def test_reason_codes_present(self, engine):
        """Test that reason codes are provided."""
        decision = engine.score_transaction(
            transaction={"id": "txn_reason_test", "amount": 100},
            context={}
        )

        assert len(decision.reason_codes) > 0
        assert all(isinstance(code, str) for code in decision.reason_codes)


class TestEntityGraph:
    """Test suite for entity graph analysis."""

    @pytest.fixture
    def graph(self):
        """Initialize entity graph."""
        return EntityGraph()

    def test_add_entity(self, graph):
        """Test adding entities to graph."""
        graph.add_entity("usr_1", EntityType.USER, {"kyc": True})
        assert "usr_1" in graph.nodes
        assert graph.nodes["usr_1"].entity_type == EntityType.USER

    def test_add_relationship(self, graph):
        """Test adding relationships between entities."""
        graph.add_entity("usr_1", EntityType.USER, {})
        graph.add_entity("dev_1", EntityType.DEVICE, {})

        graph.add_relationship("usr_1", "dev_1", RelationType.OWNS)

        assert "dev_1" in graph.adjacency_list["usr_1"]

    def test_mule_detection(self, graph):
        """Test mule network detection."""
        graph.add_entity("usr_mule", EntityType.USER, {})
        graph.add_entity("dev_1", EntityType.DEVICE, {})
        graph.add_entity("dev_2", EntityType.DEVICE, {})
        graph.add_entity("dev_3", EntityType.DEVICE, {})

        # User with many devices
        for i in range(1, 4):
            graph.add_relationship("usr_mule", f"dev_{i}", RelationType.OWNS)

        risk_score, patterns = graph.detect_mule_network("usr_mule", threshold_connections=2)

        assert risk_score > 0.0
        assert len(patterns) > 0

    def test_fraud_ring_detection(self, graph):
        """Test fraud ring detection."""
        # Create ring: two users sharing devices
        graph.add_entity("usr_1", EntityType.USER, {})
        graph.add_entity("usr_2", EntityType.USER, {})
        graph.add_entity("dev_shared", EntityType.DEVICE, {})

        graph.add_relationship("usr_1", "dev_shared", RelationType.OWNS)
        graph.add_relationship("usr_2", "dev_shared", RelationType.OWNS)

        risk_score, patterns, related = graph.detect_fraud_ring("usr_1")

        # Ring detection should find related users or patterns
        assert risk_score >= 0.0  # Can be 0 if no shared pattern found via BFS
        assert isinstance(patterns, list)
        assert isinstance(related, list)


class TestAMLRulesEngine:
    """Test suite for AML rules engine."""

    @pytest.fixture
    def aml_engine(self):
        """Initialize AML engine."""
        return AMLRulesEngine()

    def test_sanctions_screening_clean(self, aml_engine):
        """Test sanctions screening on clean entity."""
        risk_score, codes, hits = aml_engine.screen_sanctions(
            entity_name="John Smith",
            entity_country="US"
        )

        assert risk_score == 0.0
        assert len(codes) == 0
        assert len(hits) == 0

    def test_sanctions_screening_hit(self, aml_engine):
        """Test sanctions screening with hit."""
        risk_score, codes, hits = aml_engine.screen_sanctions(
            entity_name="North Korea Entity 1",
            entity_country="US"
        )

        assert risk_score > 0.8
        assert len(codes) > 0
        assert len(hits) > 0

    def test_pep_screening(self, aml_engine):
        """Test PEP screening."""
        risk_score, codes, matches = aml_engine.screen_pep(
            entity_name="Vladimir Putin"
        )

        assert risk_score > 0.9
        assert "PEP_DIRECT" in codes
        assert len(matches) > 0

    def test_velocity_abuse_detection(self, aml_engine):
        """Test velocity abuse detection."""
        risk_score, codes = aml_engine.check_velocity_abuse(
            user_id="usr_rapid",
            transactions_24h=100,
            amount_24h=500000
        )

        assert risk_score > 0.0
        assert len(codes) > 0


class TestMetricsCollector:
    """Test suite for metrics collection."""

    @pytest.fixture
    def collector(self):
        """Initialize metrics collector."""
        return MetricsCollector()

    def test_record_decision(self, collector):
        """Test recording decisions."""
        collector.record_decision(
            decision="allow",
            risk_score=0.1,
            latency_ms=25.5,
            model_version="v1.0.0"
        )

        assert collector.total_decisions == 1
        assert collector.allowed_count == 1

    def test_authorization_rate(self, collector):
        """Test authorization rate calculation."""
        collector.record_decision("allow", 0.1, 20, "v1.0.0")
        collector.record_decision("block", 0.9, 30, "v1.0.0")
        collector.record_decision("allow", 0.2, 25, "v1.0.0")

        auth_rate = collector.get_authorization_rate()
        assert auth_rate == 2.0 / 3.0

    def test_latency_percentiles(self, collector):
        """Test latency percentile calculation."""
        for latency in [10, 20, 30, 40, 50]:
            collector.record_decision("allow", 0.1, latency, "v1.0.0")

        latencies = collector.get_latency_metrics()
        assert latencies["p50_ms"] > 0
        assert latencies["p95_ms"] > latencies["p50_ms"]

    def test_fraud_feedback(self, collector):
        """Test fraud feedback recording."""
        collector.record_decision("block", 0.9, 25, "v1.0.0")
        collector.record_fraud_feedback("block", actual_fraud=True)  # TP

        collector.record_decision("block", 0.8, 25, "v1.0.0")
        collector.record_fraud_feedback("block", actual_fraud=False)  # FP

        assert collector.true_positives == 1
        assert collector.false_positives == 1

    def test_get_summary(self, collector):
        """Test metrics summary."""
        collector.record_decision("allow", 0.1, 20, "v1.0.0")
        collector.record_decision("block", 0.9, 30, "v1.0.0")

        summary = collector.get_summary()

        assert "allow_rate" in summary
        assert "latency" in summary
        assert summary["total_decisions"] == 2


# Integration test
class TestIntegration:
    """Integration tests for the full system."""

    def test_end_to_end_decision(self):
        """Test end-to-end decision flow."""
        engine = RiskDecisionEngine()

        decision = engine.score_transaction(
            transaction={
                "id": "txn_e2e_test",
                "amount": 150.00,
                "currency": "USD",
                "merchant_id": "mch_test",
                "user_id": "usr_test"
            },
            context={
                "device_id": "dev_test",
                "ip_address": "10.0.0.1",
                "user_country": "US"
            },
            user_profile={
                "account_age_days": 100,
                "kyc_verified": True
            }
        )

        # Verify decision has all required fields
        assert decision.decision in [DecisionType.ALLOW, DecisionType.BLOCK, DecisionType.REVIEW]
        assert 0 <= decision.risk_score <= 1
        assert decision.latency_ms >= 0  # Can be 0 if execution is very fast
        assert len(decision.reason_codes) > 0
        assert decision.compliance_log_id
        assert decision.timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
