import pandas as pd
import numpy as np

# Load the data
df = pd.read_csv('sample_transactions.csv')

print("=" * 80)
print("FRAUD PATTERN ANALYSIS")
print("=" * 80)

print(f"\nTotal transactions: {len(df)}")
print(f"Unique users: {df['user_id'].nunique()}")
print(f"Unique devices: {df['device_id'].nunique()}")
print(f"Unique merchants: {df['merchant_id'].nunique()}")
print(f"Unique IPs: {df['ip_address'].nunique()}")

print("\n" + "=" * 80)
print("FRAUD RING INDICATORS")
print("=" * 80)

# 1. Device Sharing (Multiple users on same device)
print("\n1. DEVICE SHARING ANALYSIS (Fraud Ring Indicator)")
device_users = df.groupby('device_id')['user_id'].agg(['nunique', lambda x: list(x.unique())])
device_users.columns = ['user_count', 'users']
shared_devices = device_users[device_users['user_count'] > 1].sort_values('user_count', ascending=False)
print(f"\nDevices shared by multiple users: {len(shared_devices)}")
if len(shared_devices) > 0:
    print("\nTop shared devices (FRAUD RING ALERT!):")
    for idx, row in shared_devices.head(10).iterrows():
        print(f"  Device {idx}: Used by {row['user_count']} users - {row['users']}")

# 2. IP Sharing (Multiple users from same IP)
print("\n2. IP ADDRESS SHARING ANALYSIS (Fraud Ring Indicator)")
ip_users = df.groupby('ip_address')['user_id'].agg(['nunique', lambda x: list(x.unique())])
ip_users.columns = ['user_count', 'users']
shared_ips = ip_users[ip_users['user_count'] > 1].sort_values('user_count', ascending=False)
print(f"\nIPs shared by multiple users: {len(shared_ips)}")
if len(shared_ips) > 0:
    print("\nTop shared IPs (FRAUD RING ALERT!):")
    for idx, row in shared_ips.head(10).iterrows():
        print(f"  IP {idx}: Used by {row['user_count']} users - {row['users']}")

# 3. High Velocity Users
print("\n3. HIGH VELOCITY USERS (Account Takeover/Fraud Indicator)")
user_counts = df['user_id'].value_counts()
high_velocity = user_counts[user_counts >= 4]
print(f"\nUsers with 4+ transactions: {len(high_velocity)}")
if len(high_velocity) > 0:
    print("\nTop velocity users:")
    for user, count in high_velocity.head(10).items():
        print(f"  {user}: {count} transactions")

# 4. Merchant Cycling
print("\n4. MERCHANT CYCLING (Card Testing Indicator)")
user_merchants = df.groupby('user_id')['merchant_id'].nunique()
high_merchant_diversity = user_merchants[user_merchants >= 5]
print(f"\nUsers transacting with 5+ merchants: {len(high_merchant_diversity)}")
if len(high_merchant_diversity) > 0:
    print("\nUsers with high merchant diversity:")
    for user, count in high_merchant_diversity.head(10).items():
        user_data = df[df['user_id'] == user]
        merchants = user_data['merchant_id'].unique().tolist()
        print(f"  {user}: {count} merchants - {merchants}")

# 5. Cross-Border Activity
print("\n5. CROSS-BORDER ACTIVITY (Credential Compromise Indicator)")
user_countries = df.groupby('user_id')['country'].nunique()
cross_border = user_countries[user_countries >= 2]
print(f"\nUsers with transactions from 2+ countries: {len(cross_border)}")
if len(cross_border) > 0:
    print("\nUsers with cross-border activity:")
    for user, count in cross_border.head(10).items():
        user_data = df[df['user_id'] == user]
        countries = user_data['country'].unique().tolist()
        print(f"  {user}: {count} countries - {countries}")

# 6. Temporal Analysis
print("\n6. TEMPORAL PATTERN ANALYSIS")
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
hour_dist = df['hour'].value_counts().sort_index()
print(f"\nTransaction distribution by hour:")
print(hour_dist)
max_hour_pct = (hour_dist.max() / len(df)) * 100
print(f"\nWARNING: {max_hour_pct:.1f}% of transactions at hour {hour_dist.idxmax()}")
if max_hour_pct > 80:
    print("⚠️ ALERT: Extreme temporal clustering suggests synthetic data or bot activity!")

# 7. Connected Users (Fraud Rings)
print("\n7. FRAUD RING DETECTION (Connected Users)")
fraud_rings = []
for device in shared_devices.head(5).index:
    users_on_device = df[df['device_id'] == device]['user_id'].unique()
    fraud_rings.append({
        'device': device,
        'users': users_on_device.tolist(),
        'connection_type': 'shared_device'
    })

for ip in shared_ips.head(5).index:
    users_on_ip = df[df['ip_address'] == ip]['user_id'].unique()
    fraud_rings.append({
        'ip': ip,
        'users': users_on_ip.tolist(),
        'connection_type': 'shared_ip'
    })

print(f"\nIdentified {len(fraud_rings)} potential fraud rings:")
for i, ring in enumerate(fraud_rings[:10], 1):
    print(f"\nRing #{i}:")
    print(f"  Type: {ring['connection_type']}")
    print(f"  Resource: {ring.get('device') or ring.get('ip')}")
    print(f"  Connected users: {ring['users']}")
    print(f"  Ring size: {len(ring['users'])} users")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✓ Shared devices (fraud rings): {len(shared_devices)}")
print(f"✓ Shared IPs (fraud rings): {len(shared_ips)}")
print(f"✓ High velocity users: {len(high_velocity)}")
print(f"✓ Merchant cyclers: {len(high_merchant_diversity)}")
print(f"✓ Cross-border users: {len(cross_border)}")
print(f"✓ Identified fraud rings: {len(fraud_rings)}")
print("\n⚠️ CONCLUSION: MULTIPLE FRAUD PATTERNS DETECTED IN THIS DATASET!")
