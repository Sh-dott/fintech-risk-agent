"""
Test the new advanced fraud ring detection system
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
import json
from backend.app.services.analytics.fraud_ring_detector import AdvancedFraudRingDetector
from backend.app.services.analytics.clustering_detector import HDBSCANFraudDetector
from backend.app.services.analytics.advanced_fraud_detection import AdvancedFraudDetectionEngine

# Load sample transactions
print("=" * 80)
print("TESTING ADVANCED FRAUD RING DETECTION SYSTEM")
print("=" * 80)

df = pd.read_csv('sample_transactions.csv')
transactions = df.to_dict('records')

print(f"\nLoaded {len(transactions)} transactions")
print(f"Unique users: {df['user_id'].nunique()}")
print(f"Unique devices: {df['device_id'].nunique()}")
print(f"Unique merchants: {df['merchant_id'].nunique()}")

# Test 1: Graph-based fraud ring detection
print("\n" + "=" * 80)
print("TEST 1: GRAPH-BASED FRAUD RING DETECTION")
print("=" * 80)

graph_detector = AdvancedFraudRingDetector()
graph_detector.load_transactions(transactions)
graph_report = graph_detector.detect_all()

print(f"\n[+] Total fraud rings detected: {graph_report['total_fraud_rings_detected']}")
print(f"[+] Critical rings: {graph_report['summary']['critical_rings']}")
print(f"[+] High-risk rings: {graph_report['summary']['high_risk_rings']}")
print(f"[+] Velocity violations: {graph_report['summary']['velocity_violations']}")
print(f"[+] Temporal anomalies: {graph_report['summary']['temporal_anomalies']}")
print(f"[+] Total users in rings: {graph_report['summary']['total_users_in_rings']}")

if graph_report['fraud_rings']:
    print("\nTop detected fraud rings:")
    for i, ring in enumerate(graph_report['fraud_rings'][:5], 1):
        print(f"\n  Ring #{i}:")
        print(f"    ID: {ring['ring_id']}")
        print(f"    Size: {ring['size']} members")
        print(f"    Risk Score: {ring['risk_score']:.2f}")
        print(f"    Detection Method: {ring['detection_method']}")
        print(f"    Members: {', '.join(ring['members'][:5])}")
        if ring['behavioral_signals']:
            print(f"    Signals: {', '.join(ring['behavioral_signals'])}")

# Test 2: HDBSCAN clustering detection
print("\n" + "=" * 80)
print("TEST 2: HDBSCAN CLUSTERING DETECTION")
print("=" * 80)

cluster_detector = HDBSCANFraudDetector(min_cluster_size=2, min_samples=2)
cluster_detector.load_transactions(transactions)
clusters = cluster_detector.detect_clusters()
cluster_report = cluster_detector.get_report()

print(f"\n[+] Total clusters detected: {cluster_report['total_clusters_detected']}")
print(f"[+] High-risk clusters: {cluster_report['summary']['high_risk_clusters']}")
print(f"[+] Medium-risk clusters: {cluster_report['summary']['medium_risk_clusters']}")
print(f"[+] Total users in clusters: {cluster_report['summary']['total_users_in_clusters']}")

if cluster_report['clusters']:
    print("\nTop detected behavioral clusters:")
    for i, cluster in enumerate(cluster_report['clusters'][:3], 1):
        print(f"\n  Cluster #{i}:")
        print(f"    ID: {cluster['cluster_id']}")
        print(f"    Size: {cluster['size']} members")
        print(f"    Risk Score: {cluster['risk_score']:.2f}")
        print(f"    Cohesion: {cluster['cohesion_score']:.2f}")
        print(f"    Members: {', '.join(cluster['members'][:5])}")

# Test 3: ML-based anomaly detection
print("\n" + "=" * 80)
print("TEST 3: ML-BASED ANOMALY DETECTION")
print("=" * 80)

ml_detector = AdvancedFraudDetectionEngine()
ml_detector.load_transactions(transactions)
ml_detector.detect_anomalies()
ml_detector.detect_fraud_networks()
ml_detector.detect_money_laundering_patterns()
ml_detector.calculate_comprehensive_risk_scores()

ml_report = ml_detector.generate_comprehensive_report()

print(f"\n[+] Anomalies detected: {ml_report['anomalies_detected']}")
print(f"[+] Money laundering patterns: {ml_report['summary']['potential_moneylaundering_cases']}")
print(f"[+] High-risk entities: {ml_report['summary']['high_risk_entities']}")
print(f"[+] Average risk score: {ml_report['summary']['avg_risk_score']:.4f}")

# Overall summary
print("\n" + "=" * 80)
print("OVERALL DETECTION SUMMARY")
print("=" * 80)

total_detections = (
    graph_report['total_fraud_rings_detected'] +
    cluster_report['total_clusters_detected'] +
    ml_report['anomalies_detected']
)

print(f"\n[+] Total detections across all methods: {total_detections}")
print(f"[+] Graph-based rings: {graph_report['total_fraud_rings_detected']}")
print(f"[+] Behavioral clusters: {cluster_report['total_clusters_detected']}")
print(f"[+] ML anomalies: {ml_report['anomalies_detected']}")

print("\n" + "=" * 80)
print("KEY RECOMMENDATIONS")
print("=" * 80)
for i, rec in enumerate(graph_report['recommendations'][:5], 1):
    print(f"{i}. {rec}")

# Check if the system now detects fraud
if total_detections > 0:
    print("\n" + "=" * 80)
    print("SUCCESS: FRAUD DETECTION SYSTEM IS NOW WORKING!")
    print("=" * 80)
    print(f"\nThe system detected {total_detections} fraud patterns that were previously missed.")
    print("The 'No Suspicious Behavior Detected' message should no longer appear.")
else:
    print("\n" + "=" * 80)
    print("WARNING: No fraud patterns detected")
    print("=" * 80)

# Save detailed report
output = {
    "graph_detection": graph_report,
    "cluster_detection": cluster_report,
    "ml_detection": ml_report
}

with open('fraud_detection_results.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)

print("\n[+] Detailed results saved to: fraud_detection_results.json")
