# Real-Time Risk & Insights Agent

A fintech payments fraud & AML detection platform with <100ms end-to-end latency, PCI DSS / PSD2 compliance, and explainable ML-driven decisions.

## Overview

This agent processes live transaction streams, enriches with identity/behavior/merchant signals, scores for fraud/AML risk, and provides actionable reason codes—all within strict latency and regulatory constraints.

### Key Features

- **Real-Time Scoring**: <100ms p95 end-to-end decision latency
- **Fraud & AML Detection**: ML-driven (DNN/GBDT) + rules-based hybrid approach
- **Explainability**: Top-N feature importance, rule IDs, graph hints
- **Compliance**: PCI DSS, PSD2/SCA, FATF AML alignment
- **Continuous Learning**: A/B testing, drift monitoring, safe online updates
- **Entity Graphs**: Detect fraud rings, mule networks, related accounts
- **Playbooks**: LLM-driven investigation & researcher guidance

## Architecture

```
transactions_stream → Enrichment → Scoring → Decision → Actions → Monitoring
                     (feature_store)  (model)   (rules)   (block/allow/review)
                                      (graph)
```

### Components

- **Feature Store**: Low-latency online lookups (KYC, velocity, device reputation)
- **ML Model**: Fraud scoring DNN/GBDT (<50ms p95)
- **Graph DB**: Entity relationships & mule network detection
- **Rules Engine**: AML red-flags, business rules, velocity thresholds
- **LLM RAG**: Playbooks, investigations, explainability (async)
- **Actions Service**: Block/Allow/Review decisions + escalation
- **Monitoring**: Drift detection, bias monitoring, metrics logging

## Project Structure

```
fintech-risk-agent/
├── src/
│   ├── core/
│   │   ├── decision_engine.py     # Main risk scoring orchestrator
│   │   ├── feature_enrichment.py  # Feature store lookups & enrichment
│   │   └── model_scorer.py        # ML model inference
│   ├── graph/
│   │   └── entity_graph.py        # Entity relationships & ring detection
│   ├── rules/
│   │   ├── aml_rules.py           # AML/sanctions rules
│   │   └── business_rules.py      # Custom thresholds & policies
│   ├── actions/
│   │   └── decision_actions.py    # Block/Allow/Review + escalation
│   ├── monitoring/
│   │   ├── metrics.py             # KPI logging & drift detection
│   │   └── compliance_log.py      # Audit trail & FATF traceability
│   └── api/
│       └── transaction_handler.py # REST/gRPC endpoints
├── config/
│   ├── model_config.yaml          # Model thresholds, weights
│   └── rules_config.yaml          # AML/business rule definitions
├── tests/
│   ├── test_decision_engine.py
│   └── test_compliance.py
├── notebooks/
│   └── analysis.ipynb             # Monitoring & drift analysis
├── requirements.txt
├── package.json
└── README.md
```

## Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
npm install
```

### 2. Run Decision Engine

```python
from src.core.decision_engine import RiskDecisionEngine

engine = RiskDecisionEngine(config_path='config/model_config.yaml')
decision = engine.score_transaction(
    transaction={
        'id': 'txn_123',
        'amount': 100.00,
        'currency': 'USD',
        'merchant_id': 'mch_456',
        'user_id': 'usr_789'
    },
    context={
        'device_id': 'dev_abc',
        'ip_address': '192.168.1.1',
        'user_country': 'US'
    }
)

print(decision)
# {
#   'decision': 'allow',
#   'risk_score': 0.12,
#   'reasons': [
#     {'signal': 'velocity_ok', 'weight': 0.05},
#     {'signal': 'trusted_device', 'weight': 0.03}
#   ],
#   'compliance_log_id': 'clog_xyz'
# }
```

## Decision Policy

1. **Enrich**: Fetch features from store & entity graph
2. **Score**: ML model + rules engine evaluation
3. **Decide**:
   - **High-risk** (>0.8): Block + reason codes
   - **Low-risk** (<0.3): Allow + monitor
   - **Medium-risk**: Review queue + escalation
4. **Log**: Compliance, metrics, reason codes

## Compliance

- **PCI DSS**: No raw card data in logs; encryption in transit/at rest
- **PSD2**: SCA step-up for high-risk; proper authentication trails
- **AML/FATF**: Sanctions screening, transaction reporting, entity monitoring
- **GDPR**: Right to explanation via reason codes; data retention policies

## Monitoring & Metrics

- Fraud detection rate (TPR/FPR)
- Authorization approval rate
- Feature drift detection
- Bias monitoring (geographic, demographic)
- Latency percentiles (p50, p95, p99)
- Compliance violations & escalations

## A/B Testing

Control group gets baseline rules; treatment gets new model variant. Track approval lift, fraud catch rate, and user friction.

## Playbooks (LLM-Driven)

- "High-velocity small-amounts" → Mule network detection
- "Cross-border geovelocity" → SCA/3DS step-up
- "Sanctions/PEP hit" → Immediate freeze & compliance escalation

## Contributing

1. Create feature branch
2. Add tests
3. Ensure latency <100ms and compliance checks pass
4. Submit PR with reason codes & monitoring impact

## License

Proprietary – Fintech Risk & Insights Agent
