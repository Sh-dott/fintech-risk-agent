"""
Direct test of OrganizedFraudDetector on Exercise 1 Excel file
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
from backend.app.services.analytics.organized_fraud_detector import OrganizedFraudDetector

print("=" * 80)
print("TESTING ORGANIZED FRAUD DETECTOR ON EXERCISE 1 (Direct from Excel)")
print("=" * 80)

# Load Excel file directly
file_path = r"C:\Users\Shai\Desktop\לסדר אחכ את כל הקבצים למיין וכו\Home assignments\Riskified TEST\Fraud_Exercise_-_1.xlsx"
print(f"\n[1/4] Loading Excel file...")
df = pd.read_excel(file_path)
print(f"      Loaded {len(df):,} transactions")

# Convert to list of dicts
print(f"\n[2/4] Converting to transactions format...")
transactions = df.to_dict('records')
print(f"      Converted {len(transactions):,} transactions")

# Test organized fraud detector
print(f"\n[3/4] Running Organized Fraud Detector...")
detector = OrganizedFraudDetector()
detector.load_transactions(transactions)
detector.detect_organized_fraud_rings()

# Generate report
print(f"\n[4/4] Generating report...")
report = detector.generate_report()

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
print(f"\nTotal Rings Detected: {report['total_rings_detected']}")

if report['total_rings_detected'] > 0:
    print(f"\n✓ SUCCESS! Fraud rings detected:\n")
    for ring in report['rings']:
        print(f"  - {ring['ring_name']}")
        print(f"    Members: {ring['member_count']}")
        print(f"    Severity: {ring['severity']}")
        print(f"    Total Amount: €{ring['total_fraud_amount']:,.2f}")
        print(f"    Pattern: {ring['fake_name_pattern']}")
        print()
else:
    print(f"\n✗ PROBLEM: No fraud rings detected!")
    print(f"\n   Debugging information:")

    # Check if 'asd' exists in the data
    asd_count = sum(1 for t in transactions if str(t.get('BILLING_FIRST_NAME', '')).lower() == 'asd')
    print(f"   - Found {asd_count} transactions with name 'asd'")

    # Test fake name detection manually
    is_fake = detector.detect_fake_name_pattern('asd')
    print(f"   - Is 'asd' detected as fake? {is_fake}")

    # Show available columns
    if transactions:
        print(f"   - Available columns: {list(transactions[0].keys())}")

print("\n" + "=" * 80)
