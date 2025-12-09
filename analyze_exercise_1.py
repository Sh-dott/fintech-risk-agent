"""
Analyze Fraud Exercise 1 - Discover actual fraud patterns in YOUR data
"""

import pandas as pd
import numpy as np
from collections import Counter

print("=" * 80)
print("ANALYZING FRAUD EXERCISE 1")
print("=" * 80)

# Load the Excel file
file_path = r"C:\Users\Shai\Desktop\לסדר אחכ את כל הקבצים למיין וכו\Home assignments\Riskified TEST\Fraud_Exercise_-_1.xlsx"

print(f"\n[1/3] Loading file: {file_path}")
df = pd.read_excel(file_path)

print(f"\n[2/3] Data Overview:")
print(f"   Total Records: {len(df):,}")
print(f"   Columns: {list(df.columns)}")
print(f"\nFirst 5 rows:")
print(df.head())

print(f"\n[3/3] Column Details:")
for col in df.columns:
    print(f"\n{col}:")
    print(f"   Type: {df[col].dtype}")
    print(f"   Unique values: {df[col].nunique()}")
    print(f"   Sample values: {df[col].head(5).tolist()}")

    # Show value counts for categorical columns
    if df[col].nunique() < 50:
        print(f"   Distribution:")
        for val, count in df[col].value_counts().items():
            print(f"      {val}: {count}")

# Look for patterns
print("\n" + "=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)

# Check for common fraud indicators
for col in df.columns:
    col_lower = str(col).lower()

    # Look for name columns
    if 'name' in col_lower or 'first' in col_lower or 'last' in col_lower:
        print(f"\nNAME COLUMN: {col}")
        name_counts = df[col].value_counts()
        print(f"   Most common values:")
        for name, count in name_counts.head(10).items():
            pct = count / len(df) * 100
            print(f"      {name}: {count} ({pct:.1f}%)")

    # Look for email columns
    if 'email' in col_lower or 'mail' in col_lower:
        print(f"\nEMAIL COLUMN: {col}")
        email_counts = df[col].value_counts()
        print(f"   Most common emails:")
        for email, count in email_counts.head(10).items():
            print(f"      {email}: {count}")

        # Extract domains
        if df[col].dtype == 'object':
            domains = df[col].str.split('@').str[1] if df[col].str.contains('@').any() else []
            if len(domains) > 0:
                domain_counts = domains.value_counts()
                print(f"   Most common domains:")
                for domain, count in domain_counts.head(10).items():
                    print(f"      {domain}: {count}")

    # Look for country/location columns
    if 'country' in col_lower or 'state' in col_lower or 'city' in col_lower:
        print(f"\nLOCATION COLUMN: {col}")
        loc_counts = df[col].value_counts()
        print(f"   Distribution:")
        for loc, count in loc_counts.head(10).items():
            print(f"      {loc}: {count}")

    # Look for amount columns
    if 'amount' in col_lower or 'price' in col_lower or 'total' in col_lower:
        print(f"\nAMOUNT COLUMN: {col}")
        if df[col].dtype in ['int64', 'float64']:
            print(f"   Mean: {df[col].mean():.2f}")
            print(f"   Median: {df[col].median():.2f}")
            print(f"   Min: {df[col].min():.2f}")
            print(f"   Max: {df[col].max():.2f}")
            print(f"   Std Dev: {df[col].std():.2f}")

# Save to CSV for easier analysis
csv_path = "fraud_exercise_1_data.csv"
df.to_csv(csv_path, index=False)
print(f"\n\nData saved to: {csv_path}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE - Review the output above to find fraud patterns!")
print("=" * 80)
