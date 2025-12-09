"""
Quick test of fraud ring detection on sample data
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
from backend.app.services.analytics.targeted_ring_detector import TargetedFraudRingDetector

print("=" * 80)
print("TESTING FRAUD RING DETECTION SYSTEM")
print("=" * 80)

# Load sample transactions
print("\n[1/4] Loading sample transactions...")
df = pd.read_csv('C:/Users/Shai/web-projects/fintech-risk-agent/sample_transactions.csv')
transactions = df.to_dict('records')
print(f"   [+] Loaded {len(transactions)} transactions")
print(f"   [+] Unique users: {df['user_id'].nunique()}")

# Initialize detector
print("\n[2/4] Initializing Targeted Fraud Ring Detector...")
detector = TargetedFraudRingDetector()
detector.load_transactions(transactions)
print("   [+] Detector initialized")

# Detect fraud rings
print("\n[3/4] Running all 5 fraud ring detection methods...")
report_obj = detector.detect_all_targeted_rings()
print(f"   [+] Detection complete!")

# Convert to dict for easier access
from dataclasses import asdict
report = asdict(report_obj)

# Display results
print("\n[4/4] RESULTS:")
print("=" * 80)
print(f"\nTotal Fraud Rings Detected: {report['total_rings_detected']}")
print(f"Critical Rings: {report['critical_count']}")
print(f"High Risk Rings: {report['high_count']}")
print(f"Medium Risk Rings: {report['medium_count']}")
print(f"Overall Risk Level: {report['overall_risk_level']}")

if report['rings']:
    print(f"\n{'='*80}")
    print("DETECTED FRAUD RINGS:")
    print('=' * 80)

    for i, ring in enumerate(report['rings'], 1):
        print(f"\n--- Ring #{i}: {ring['ring_name']} ---")
        print(f"Type: {ring['ring_type']}")
        print(f"Severity: {ring['severity']}")
        print(f"Members: {ring['member_count']}")
        print(f"Risk Score: {ring['risk_score']:.2f}")
        print(f"Detection Method: {ring['detection_method']}")
        print(f"Members List: {', '.join(ring['members'][:10])}{'...' if len(ring['members']) > 10 else ''}")
        print(f"\nExplanation: {ring['explanation'][:150]}...")

        # Show top 2 recommendations
        if ring['recommendations']:
            print(f"\nTop Recommendations:")
            for j, rec in enumerate(ring['recommendations'][:2], 1):
                print(f"  {j}. {rec}")

print(f"\n{'='*80}")
print("EXECUTIVE SUMMARY:")
print('=' * 80)
print(report['executive_summary'])

print(f"\n{'='*80}")
print("TEST COMPLETED SUCCESSFULLY!")
print('=' * 80)

# Test serialization to JSON (for API response)
print("\n[BONUS] Testing JSON serialization...")
import json
try:
    json_output = json.dumps(report, indent=2, default=str)
    print(f"   [+] Successfully serialized to JSON ({len(json_output)} bytes)")
    print(f"   [+] Sample JSON structure: {list(report.keys())}")
except Exception as e:
    print(f"   [!] Error serializing: {e}")
