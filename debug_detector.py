"""
Debug why OrganizedFraudDetector is not finding 'asd' pattern
"""

import sys
sys.path.insert(0, 'C:/Users/Shai/web-projects/fintech-risk-agent')

import pandas as pd
from backend.app.services.analytics.organized_fraud_detector import OrganizedFraudDetector

print("=" * 80)
print("DEBUGGING ORGANIZED FRAUD DETECTOR")
print("=" * 80)

# Load Excel file
file_path = r"C:\Users\Shai\Desktop\לסדר אחכ את כל הקבצים למיין וכו\Home assignments\Riskified TEST\Fraud_Exercise_-_1.xlsx"
print("\n[1] Loading Excel file...")
df = pd.read_excel(file_path)
print(f"    Loaded {len(df):,} transactions")

# Convert to transactions
transactions = df.to_dict('records')
print(f"\n[2] Converted to {len(transactions):,} transaction dicts")

# Show sample transaction
print(f"\n[3] Sample transaction structure:")
if transactions:
    sample = transactions[0]
    for key, value in sample.items():
        print(f"    {key}: {value} (type: {type(value).__name__})")

# Count 'asd' transactions manually
print(f"\n[4] Manual 'asd' detection:")
asd_count = 0
for t in transactions:
    name = t.get('BILLING_FIRST_NAME', '')
    if str(name).lower() == 'asd':
        asd_count += 1
print(f"    Found {asd_count} transactions with BILLING_FIRST_NAME = 'asd'")

# Test detector's fake name pattern detection
print(f"\n[5] Testing detector.detect_fake_name_pattern():")
detector = OrganizedFraudDetector()
test_names = ['asd', 'ASD', 'qwe', 'test', 'Christopher', 'Michael']
for name in test_names:
    is_fake = detector.detect_fake_name_pattern(name)
    print(f"    '{name}' -> {is_fake}")

# Load transactions into detector
print(f"\n[6] Loading transactions into detector...")
detector.load_transactions(transactions)
print(f"    Detector has {len(detector.df)} records in DataFrame")

# Check column names in detector
print(f"\n[7] Detector DataFrame columns:")
for col in detector.df.columns:
    print(f"    - {col}")

# Run detection
print(f"\n[8] Running detect_organized_fraud_rings()...")
detector.detect_organized_fraud_rings()

# Check results
report = detector.generate_report()
print(f"\n[9] Detection results:")
print(f"    Total rings detected: {report['total_rings_detected']}")

if report['total_rings_detected'] == 0:
    print(f"\n[DEBUG] No rings detected. Checking detector logic...")

    # Check if 'is_fake_name' column exists
    if 'is_fake_name' in detector.df.columns:
        fake_count = detector.df['is_fake_name'].sum()
        print(f"    - Transactions flagged as fake name: {fake_count}")

        if fake_count > 0:
            fake_names = detector.df[detector.df['is_fake_name'] == True]['billing_first_name'].value_counts()
            print(f"    - Fake names found:")
            for name, count in fake_names.head(10).items():
                print(f"      {name}: {count}")
    else:
        print(f"    - 'is_fake_name' column not found in DataFrame")

print("\n" + "=" * 80)
