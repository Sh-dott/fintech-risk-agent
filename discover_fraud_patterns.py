"""
Fraud Pattern Discovery Script
Analyzes fraudTest.csv to discover actual fraud patterns and generate detection rules
"""

import pandas as pd
import numpy as np
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("FRAUD PATTERN DISCOVERY")
print("=" * 80)

# Load data
print("\n[1/5] Loading fraud data...")
df = pd.read_csv("C:/Users/Shai/Downloads/fraudTest.csv/fraudTest.csv")
print(f"   Total transactions: {len(df):,}")
print(f"   Fraud transactions: {df['is_fraud'].sum():,}")
print(f"   Fraud rate: {df['is_fraud'].mean()*100:.2f}%")

# Filter to fraud transactions only
fraud_df = df[df['is_fraud'] == 1].copy()
legit_df = df[df['is_fraud'] == 0].copy()

print(f"\n[2/5] Analyzing {len(fraud_df):,} fraud transactions...")

# Analysis storage
patterns = {}

# 1. MERCHANT ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 1: MERCHANT ANALYSIS")
print("=" * 80)

fraud_merchants = fraud_df['merchant'].value_counts()
legit_merchants = legit_df['merchant'].value_counts()

# Find merchants with high fraud concentration
merchant_fraud_rates = {}
for merchant in fraud_merchants.index[:50]:  # Top 50 fraud merchants
    total_txns = len(df[df['merchant'] == merchant])
    fraud_txns = len(fraud_df[fraud_df['merchant'] == merchant])
    fraud_rate = fraud_txns / total_txns if total_txns > 0 else 0
    merchant_fraud_rates[merchant] = {
        'fraud_txns': fraud_txns,
        'total_txns': total_txns,
        'fraud_rate': fraud_rate
    }

# Find merchants with 100% fraud rate
pure_fraud_merchants = {k: v for k, v in merchant_fraud_rates.items() if v['fraud_rate'] > 0.9 and v['fraud_txns'] >= 5}

print(f"\nMerchants with >90% fraud rate (min 5 txns): {len(pure_fraud_merchants)}")
if pure_fraud_merchants:
    print("\nTop Fraudulent Merchants:")
    for merchant, stats in sorted(pure_fraud_merchants.items(), key=lambda x: x[1]['fraud_txns'], reverse=True)[:10]:
        print(f"  {merchant[:50]:<50} | Fraud: {stats['fraud_txns']:>4} / {stats['total_txns']:>4} ({stats['fraud_rate']*100:.1f}%)")

patterns['merchants'] = pure_fraud_merchants

# 2. CATEGORY ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 2: CATEGORY ANALYSIS")
print("=" * 80)

fraud_categories = fraud_df['category'].value_counts()
legit_categories = legit_df['category'].value_counts()

print(f"\nFraud distribution by category:")
for cat in fraud_categories.index:
    fraud_count = fraud_categories[cat]
    total_count = len(df[df['category'] == cat])
    fraud_rate = fraud_count / total_count if total_count > 0 else 0
    print(f"  {cat:<20} | Fraud: {fraud_count:>5} / {total_count:>6} ({fraud_rate*100:.2f}%)")

patterns['categories'] = fraud_categories.to_dict()

# 3. AMOUNT ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 3: AMOUNT PATTERNS")
print("=" * 80)

print(f"\nFraud transaction amounts:")
print(f"  Mean: ${fraud_df['amt'].mean():.2f}")
print(f"  Median: ${fraud_df['amt'].median():.2f}")
print(f"  Min: ${fraud_df['amt'].min():.2f}")
print(f"  Max: ${fraud_df['amt'].max():.2f}")

print(f"\nLegitimate transaction amounts:")
print(f"  Mean: ${legit_df['amt'].mean():.2f}")
print(f"  Median: ${legit_df['amt'].median():.2f}")

# Amount distribution
fraud_df['amount_range'] = pd.cut(fraud_df['amt'], bins=[0, 50, 100, 200, 500, 1000, 10000], labels=['0-50', '50-100', '100-200', '200-500', '500-1000', '1000+'])
amount_dist = fraud_df['amount_range'].value_counts().sort_index()

print(f"\nFraud amount distribution:")
for range_label, count in amount_dist.items():
    pct = count / len(fraud_df) * 100
    print(f"  ${range_label:<12} | {count:>5} ({pct:>5.1f}%)")

patterns['amounts'] = {
    'mean': fraud_df['amt'].mean(),
    'median': fraud_df['amt'].median(),
    'distribution': amount_dist.to_dict()
}

# 4. GEOGRAPHIC ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 4: GEOGRAPHIC PATTERNS")
print("=" * 80)

fraud_states = fraud_df['state'].value_counts()
fraud_cities = fraud_df['city'].value_counts()

print(f"\nTop 10 fraud states:")
for state, count in fraud_states.head(10).items():
    total_state = len(df[df['state'] == state])
    fraud_rate = count / total_state * 100 if total_state > 0 else 0
    print(f"  {state:<5} | Fraud: {count:>5} / {total_state:>6} ({fraud_rate:.2f}%)")

print(f"\nTop 10 fraud cities:")
for city, count in fraud_cities.head(10).items():
    print(f"  {city[:30]:<30} | {count:>5}")

patterns['geography'] = {
    'states': fraud_states.head(10).to_dict(),
    'cities': fraud_cities.head(10).to_dict()
}

# 5. NAME ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 5: NAME PATTERNS")
print("=" * 80)

fraud_first_names = fraud_df['first'].value_counts()
fraud_last_names = fraud_df['last'].value_counts()

print(f"\nTop 10 first names in fraud:")
for name, count in fraud_first_names.head(10).items():
    print(f"  {name:<20} | {count:>5}")

print(f"\nTop 10 last names in fraud:")
for name, count in fraud_last_names.head(10).items():
    print(f"  {name:<20} | {count:>5}")

# Check for fake/test names
fake_patterns = ['test', 'fraud', 'fake', 'demo', 'asd', 'qwe', 'xxx']
fake_names = fraud_df[fraud_df['first'].str.lower().isin(fake_patterns) | fraud_df['last'].str.lower().isin(fake_patterns)]
print(f"\nFake/test names found: {len(fake_names)}")

patterns['names'] = {
    'first': fraud_first_names.head(20).to_dict(),
    'last': fraud_last_names.head(20).to_dict()
}

# 6. JOB ANALYSIS
print("\n" + "=" * 80)
print("PATTERN 6: JOB/OCCUPATION PATTERNS")
print("=" * 80)

fraud_jobs = fraud_df['job'].value_counts()

print(f"\nTop 10 jobs in fraud:")
for job, count in fraud_jobs.head(10).items():
    total_job = len(df[df['job'] == job])
    fraud_rate = count / total_job * 100 if total_job > 0 else 0
    print(f"  {job[:40]:<40} | Fraud: {count:>5} / {total_job:>6} ({fraud_rate:.2f}%)")

patterns['jobs'] = fraud_jobs.head(20).to_dict()

# 7. TIME PATTERNS
print("\n" + "=" * 80)
print("PATTERN 7: TEMPORAL PATTERNS")
print("=" * 80)

fraud_df['trans_datetime'] = pd.to_datetime(fraud_df['trans_date_trans_time'])
fraud_df['hour'] = fraud_df['trans_datetime'].dt.hour
fraud_df['day_of_week'] = fraud_df['trans_datetime'].dt.dayofweek

hour_dist = fraud_df['hour'].value_counts().sort_index()
dow_dist = fraud_df['day_of_week'].value_counts().sort_index()

print(f"\nFraud by hour of day:")
for hour, count in hour_dist.items():
    print(f"  {hour:02d}:00 | {'#' * int(count / 50)} ({count})")

print(f"\nFraud by day of week:")
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
for dow, count in dow_dist.items():
    print(f"  {days[dow]:<10} | {count:>5}")

patterns['temporal'] = {
    'hour': hour_dist.to_dict(),
    'day_of_week': dow_dist.to_dict()
}

# 8. VELOCITY ANALYSIS (same card in short time)
print("\n" + "=" * 80)
print("PATTERN 8: VELOCITY PATTERNS (Rapid Transactions)")
print("=" * 80)

fraud_df_sorted = fraud_df.sort_values(['cc_num', 'unix_time'])
fraud_df_sorted['time_diff'] = fraud_df_sorted.groupby('cc_num')['unix_time'].diff()

# Count cards with multiple transactions within 1 hour (3600 seconds)
rapid_txns = fraud_df_sorted[fraud_df_sorted['time_diff'] <= 3600]
rapid_cards = rapid_txns['cc_num'].nunique()

print(f"\nCards with transactions <1 hour apart: {rapid_cards}")
print(f"Total rapid fraud transactions: {len(rapid_txns)}")

# Cards with 5+ fraud transactions
fraud_per_card = fraud_df['cc_num'].value_counts()
high_velocity_cards = fraud_per_card[fraud_per_card >= 5]

print(f"\nCards with 5+ fraud transactions: {len(high_velocity_cards)}")
if len(high_velocity_cards) > 0:
    print(f"Top velocity cards:")
    for card, count in high_velocity_cards.head(10).items():
        print(f"  Card {card} | {count} fraud transactions")

patterns['velocity'] = {
    'rapid_cards': rapid_cards,
    'high_velocity_cards': len(high_velocity_cards)
}

# 9. DISTANCE ANALYSIS (card location vs merchant location)
print("\n" + "=" * 80)
print("PATTERN 9: GEOGRAPHIC DISTANCE PATTERNS")
print("=" * 80)

from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km

# Calculate distance for fraud transactions
fraud_sample = fraud_df.sample(min(1000, len(fraud_df)))  # Sample for speed
fraud_sample['distance_km'] = fraud_sample.apply(
    lambda row: haversine(row['long'], row['lat'], row['merch_long'], row['merch_lat']), axis=1
)

print(f"\nDistance between cardholder and merchant (km):")
print(f"  Mean: {fraud_sample['distance_km'].mean():.2f} km")
print(f"  Median: {fraud_sample['distance_km'].median():.2f} km")
print(f"  Max: {fraud_sample['distance_km'].max():.2f} km")

# Categorize distances
fraud_sample['distance_category'] = pd.cut(fraud_sample['distance_km'],
    bins=[0, 10, 50, 100, 500, 10000],
    labels=['<10km', '10-50km', '50-100km', '100-500km', '500+km'])

dist_dist = fraud_sample['distance_category'].value_counts().sort_index()
print(f"\nDistance distribution:")
for cat, count in dist_dist.items():
    pct = count / len(fraud_sample) * 100
    print(f"  {cat:<12} | {count:>4} ({pct:>5.1f}%)")

patterns['distance'] = {
    'mean': fraud_sample['distance_km'].mean(),
    'median': fraud_sample['distance_km'].median(),
    'distribution': dist_dist.to_dict()
}

# FINAL SUMMARY
print("\n" + "=" * 80)
print("FRAUD RING SUMMARY")
print("=" * 80)

print(f"\n1. **Merchant-Based Fraud Rings**: {len(pure_fraud_merchants)} merchants with >90% fraud rate")
print(f"2. **High-Risk Categories**: {len([c for c, cnt in fraud_categories.items() if cnt > 100])} categories with 100+ frauds")
print(f"3. **High Velocity Cards**: {len(high_velocity_cards)} cards with 5+ fraud transactions")
print(f"4. **Geographic Hotspots**: {len([s for s, cnt in fraud_states.items() if cnt > 100])} states with 100+ frauds")

print("\n" + "=" * 80)
print("RECOMMENDED DETECTION RULES:")
print("=" * 80)

print("\n1. **Block these merchants** (>90% fraud rate):")
for merchant in list(pure_fraud_merchants.keys())[:5]:
    print(f"   - {merchant}")

print("\n2. **Flag high-risk categories**:")
high_risk_cats = [cat for cat, cnt in fraud_categories.items() if cnt > 100]
for cat in high_risk_cats[:5]:
    print(f"   - {cat}")

print("\n3. **Velocity check**: Flag cards with 3+ transactions within 1 hour")

print("\n4. **Distance check**: Flag transactions >500km from cardholder location")

print("\n5. **Amount check**: Monitor transactions >$500 in high-risk categories")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)

# Save patterns for detector
import json
with open('fraud_patterns_discovered.json', 'w') as f:
    # Convert non-serializable types
    patterns_serializable = {}
    for key, value in patterns.items():
        if isinstance(value, dict):
            patterns_serializable[key] = {str(k): float(v) if isinstance(v, (np.int64, np.float64)) else v for k, v in value.items()}
        else:
            patterns_serializable[key] = value
    json.dump(patterns_serializable, f, indent=2, default=str)

print("\nPatterns saved to: fraud_patterns_discovered.json")
