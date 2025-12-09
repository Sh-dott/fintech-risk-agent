"""
Test Organized Fraud Detector on Exercise 1 Data
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
from backend.app.services.analytics.organized_fraud_detector import OrganizedFraudDetector

print("=" * 80)
print("TESTING ORGANIZED FRAUD DETECTOR ON EXERCISE 1")
print("=" * 80)

# Load the CSV (saved from previous analysis)
df = pd.read_csv('fraud_exercise_1_data.csv')
print(f"\n[1/3] Loaded {len(df):,} transactions")

# Convert to list of dicts
transactions = df.to_dict('records')
print(f"[2/3] Converted to transactions format")

# Test organized fraud detector
print(f"\n[3/3] Running Organized Fraud Detector...")
detector = OrganizedFraudDetector()
detector.load_transactions(transactions)
detector.detect_organized_fraud_rings()
report = detector.generate_report()

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
print(f"\nTotal Rings Detected: {report['total_rings_detected']}")

if report['total_rings_detected'] > 0:
    print(f"\nRings found:")
    for ring in report['rings']:
        print(f"\n  - {ring['ring_name']}")
        print(f"    Members: {ring['member_count']}")
        print(f"    Severity: {ring['severity']}")
        print(f"    Total Amount: €{ring['total_fraud_amount']:,.2f}")
        print(f"    Pattern: {ring['fake_name_pattern']}")
else:
    print("\nNo fraud rings detected!")
    print("\nDEBUG: Checking for 'asd' name manually...")
    asd_count = df[df['billing_first_name'] == 'asd']
    print(f"Found {len(asd_count)} records with name 'asd'")

    # Check if detector is looking at right column
    print(f"\nAvailable columns: {list(df.columns)}")
    print(f"\nLooking for columns with 'name' in them...")
    name_cols = [col for col in df.columns if 'name' in col.lower()]
    print(f"Found: {name_cols}")

    # Test fake name detection manually
    print(f"\nTesting fake name detection on 'asd'...")
    is_fake = detector.detect_fake_name_pattern('asd')
    print(f"Is 'asd' detected as fake? {is_fake}")

print("\n" + "=" * 80)
