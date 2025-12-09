"""
Show all detected fraud rings from Exercise 1
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
from backend.app.services.analytics.organized_fraud_detector import OrganizedFraudDetector

print("=" * 80)
print("FRAUD RING DETECTION RESULTS - EXERCISE 1")
print("=" * 80)

# Load Excel file
file_path = r"C:\Users\Shai\Desktop\לסדר אחכ את כל הקבצים למיין וכו\Home assignments\Riskified TEST\Fraud_Exercise_-_1.xlsx"
df = pd.read_excel(file_path)
transactions = df.to_dict('records')

# Run detector
detector = OrganizedFraudDetector()
detector.load_transactions(transactions)
detector.detect_organized_fraud_rings()
report = detector.generate_report()

print(f"\nTotal Rings Detected: {report['total_rings_detected']}")
if 'overall_risk_level' in report:
    print(f"Overall Risk Level: {report['overall_risk_level']}")
if 'executive_summary' in report:
    print(f"\n{report['executive_summary']}")

print("\n" + "=" * 80)
print("DETECTED FRAUD RINGS:")
print("=" * 80)

for i, ring in enumerate(report['rings'], 1):
    print(f"\n[{i}] {ring['ring_name']}")
    print(f"    Severity: {ring['severity']}")
    print(f"    Members: {ring['member_count']}")
    print(f"    Total Amount: {ring['currency']} {ring['total_fraud_amount']:,.2f}")
    print(f"    Risk Score: {ring['risk_score']:.2f}")
    print(f"    Pattern: {ring['fake_name_pattern']}")

    # Show sample of key indicators
    if ring['key_indicators']:
        print(f"    Key Indicators:")
        for indicator in ring['key_indicators'][:3]:
            print(f"      - {indicator}")

    # Show top card countries
    if ring['card_origin_countries']:
        top_countries = sorted(ring['card_origin_countries'].items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"    Top Card Countries:")
        for country, count in top_countries:
            print(f"      {country}: {count}")

print("\n" + "=" * 80)
print("SUCCESS - Fraud rings detected and ready for display!")
print("=" * 80)
