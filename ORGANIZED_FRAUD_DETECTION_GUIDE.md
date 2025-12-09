# Organized Fraud Ring Detection - Implementation Guide
**Detecting Fake Identity, Email Mismatch, and Geographic Fraud Patterns**

---

## Overview

Your system now includes **Organized Fraud Detection** - a sophisticated detector that identifies fraud rings using:
- Fake/test names (like "asd", "qwe", "test")
- Gibberish email domains
- Geographic mismatches (card country vs. travel route)
- Route concentration patterns
- Carrier targeting

This detector mimics real-world fraud analysis similar to the "asd fraud ring" example.

---

## The Detection Logic

### Pattern 1: Fake Name Detection

**What It Detects:**
- Keyboard pattern names: "asd", "qwe", "zxc"
- Test names: "test", "testing", "demo"
- Repeated characters: "aaa", "bbb", "xxx"
- Very short names: "a", "ab", "xyz"

**Implementation:**
```python
fake_name_patterns = [
    r'^asd+$',           # asd, asdasd
    r'^qwe+$',           # qwe, qweqwe
    r'^zxc+$',           # zxc
    r'^test+$',          # test, testtest
    r'^(.)\\1{2,}$',     # aaa, bbb (repeated char)
    r'^[a-z]{1,3}$',     # Very short: a, ab, xyz
]
```

**Example Detection:**
```
Input: BILLING_FIRST_NAME = "asd"
Result: ✅ Fake name detected
Pattern: All 272 orders use "asd"
Significance: Clearly a test/placeholder name indicating automated fraud
```

---

### Pattern 2: Gibberish Email Detection

**What It Detects:**
- Random domains: "dwa.dfs", "ds.dfg", "dsasd.dsad"
- Non-existent TLDs: ".dfs", ".dfg", ".fgh"
- Very short domains: Single/double letter parts
- Numeric-only patterns

**Whitelist (Legitimate Providers):**
- gmail.com, yahoo.com, hotmail.com, outlook.com
- icloud.com, protonmail.com, aol.com

**Implementation:**
```python
suspicious_email_patterns = [
    r'^[a-z]{1,5}\\.[a-z]{1,5}$',  # Short random: dwa.dfs
    r'\\.(dfs|dfg|dsad|fgh)$',     # Fake TLDs
    r'^[0-9]+@',                    # Numbers only
]
```

**Example Detection:**
```
Input: EMAIL_DOMAIN = "dwa.dfs", "ds.dfg", "ghf.fgh"
Result: ✅ Gibberish emails detected
Distribution: 131 unique random/gibberish domains
Characteristics: Non-existent TLDs, random character combinations
```

---

### Pattern 3: Geographic Mismatch Detection

**What It Detects:**
- Southeast Asian cards (SG, PH, MY) for European travel (DE, FR, UK)
- Card country ≠ Travel route country
- Impossible payment/travel combinations

**Implementation:**
```python
southeast_asian = ['SG', 'PH', 'MY', 'TH', 'ID', 'VN']
european = ['DE', 'FR', 'IT', 'ES', 'UK', 'GB', 'NL']

if card_country in southeast_asian and route_country in european:
    return True, "Geographic mismatch detected"
```

**Example Detection:**
```
Input:
- BIN_COUNTRY_CODE = "SG" (Singapore)
- DEPARTURE = "Düsseldorf" (Germany)
- ARRIVAL = "Berlin" (Germany)

Result: ✅ Geographic mismatch detected
Pattern: 239 orders (87.9%) use Singapore cards for German domestic travel
Significance: Heavy concentration from Southeast Asia for European routes
```

---

### Pattern 4: Route Concentration Detection

**What It Detects:**
- 100% of orders from single departure city
- Highly concentrated arrival patterns
- Targeting specific routes

**Example Detection:**
```
Input:
- DEPARTURE: Düsseldorf (272 orders, 100%)
- ARRIVAL: Berlin (178, 65.4%), Bremen (36, 13.2%), Cologne (25, 9.2%)

Result: ✅ Route concentration detected
Pattern: All orders departing from single city
Significance: Organized targeting of specific routes
```

---

### Pattern 5: Carrier Targeting

**What It Detects:**
- Exclusive use of single carrier
- Fraudsters focusing on one transport provider

**Example Detection:**
```
Input: CARRIER_NAME = "Deutsche Bahn" (272/272 orders, 100%)
Result: ✅ Carrier targeting detected
Significance: Exclusive focus indicates organized fraud operation
```

---

## Column-by-Column Analysis

The detector generates detailed analysis for each data column:

### 1. BILLING_FIRST_NAME Analysis

```json
{
  "pattern": "asd",
  "count": 272,
  "percentage": 100.0,
  "significance": "All orders use the exact same fake name",
  "detection": "Easy to flag - clearly a test/placeholder name"
}
```

### 2. EMAIL_DOMAIN Analysis

```json
{
  "unique_domains": 131,
  "examples": ["dwa.dfs", "ds.dfg", "dsasd.dsad", "ghf.fgh", "sdasd.dfs"],
  "characteristics": "Short, random character combinations with non-existent TLDs",
  "detection": "Flag emails with non-standard TLDs or gibberish domains"
}
```

### 3. BIN_COUNTRY_CODE Analysis

```json
{
  "distribution": {
    "SG": 239,  // Singapore: 87.9%
    "PH": 25,   // Philippines: 9.2%
    "MY": 4,    // Malaysia: 1.5%
    "LT": 4     // Lithuania: 1.5%
  },
  "top_country": "SG",
  "top_percentage": 87.9,
  "significance": "Heavy concentration from Southeast Asian payment cards",
  "detection": "Flag mismatches between card origin and travel routes"
}
```

### 4. DEPARTURE/ARRIVAL Analysis

```json
{
  "departure": {
    "concentration": 100.0,
    "top_city": "Düsseldorf",
    "total_orders": 272
  },
  "arrival": {
    "distribution": {
      "Berlin": 178,
      "Bremen": 36,
      "Cologne": 25,
      "Osnabrück": 23
    },
    "detection": "Highly concentrated route pattern"
  }
}
```

### 5. AMOUNT Analysis

```json
{
  "total": 14296.35,
  "average": 52.56,
  "range": "8.00 to 294.40",
  "distribution": {
    "0-50": 144,     // 52.9%
    "50-100": 111,   // 40.8%
    "100-150": 13,   // 4.8%
    "150-200": 3,    // 1.1%
    "200+": 1        // 0.4%
  },
  "significance": "Mostly small transactions to avoid detection thresholds"
}
```

---

## API Response Format

When organized fraud is detected, the API returns:

```json
{
  "organized_fraud": {
    "total_rings_detected": 1,
    "total_fraud_amount": 14296.35,
    "total_fraudulent_orders": 272,
    "executive_summary": "Identified 1 organized fraud ring consisting of 272 fraudulent orders...",
    "rings": [
      {
        "ring_id": "ORG_FRAUD_ASD",
        "ring_name": "Organized Fraud Ring: 'asd'",
        "severity": "CRITICAL",
        "member_count": 272,
        "total_fraud_amount": 14296.35,
        "currency": "EUR",

        "fake_name_pattern": "asd",
        "email_domain_pattern": "131 unique domains",

        "card_origin_countries": {
          "SG": 239,
          "PH": 25,
          "MY": 4,
          "LT": 4
        },

        "route_concentration": {
          "departure": {"Düsseldorf": 272},
          "arrival": {"Berlin": 178, "Bremen": 36, ...}
        },

        "carrier_pattern": "272 orders with Deutsche Bahn",

        "key_indicators": [
          "Fake Name Pattern: All 272 orders use 'asd'",
          "Gibberish Emails: 131 random email domains",
          "Geographic Mismatch: 87.9% cards from SG",
          "Route Concentration: 100.0% from Düsseldorf",
          "Proxy Usage: 248 different proxy indicators"
        ],

        "column_analysis": {
          "billing_name": {...},
          "email_domain": {...},
          "card_origin": {...},
          "departure": {...},
          "amount": {...}
        },

        "recommendations": [
          "Block all orders with billing name 'asd' or similar keyboard patterns",
          "Flag orders with non-existent email domains",
          "Implement velocity checks for Düsseldorf departures",
          "Monitor for geographic mismatches between card origin and travel routes",
          "Create composite risk score combining multiple fraud indicators"
        ],

        "detection_method": "Organized Fraud Pattern Analysis (Fake Identity + Geographic Mismatch)",
        "risk_score": 1.0,
        "explanation": "Identified organized fraud ring consisting of 272 fraudulent orders using the fake name 'asd' across all transactions. Total fraudulent transactions: EUR14,296.35. The fraud pattern combines: consistent fake identity, randomly generated email domains, geographic payment/travel mismatch, concentrated route patterns. This indicates a coordinated fraud operation using automated systems."
      }
    ]
  }
}
```

---

## Risk Score Calculation

The detector calculates risk scores based on multiple factors:

```python
risk_score = 0.0

# Fake name (+0.3)
if fake_name_detected:
    score += 0.3

# Suspicious emails (+0.2)
if gibberish_email_domains:
    score += 0.2

# Geographic mismatch (+0.2)
if card_country != route_country:
    score += 0.2

# Route concentration (+0.15)
if single_departure_city_100%:
    score += 0.15

# Proxy usage (+0.15)
if multiple_proxies_detected:
    score += 0.15

# Volume bonus
if orders >= 100:
    score += 0.1
elif orders >= 50:
    score += 0.05

# Final score: 0.0 - 1.0
```

---

## Integration with Existing System

The organized fraud detector runs alongside your existing 5 fraud ring detectors:

**Current Detection Capabilities:**
1. ✅ High Velocity Ring (5+ transactions/user)
2. ✅ Cross-Border Ring (3+ countries/user)
3. ✅ Merchant Cycling Ring (5+ merchants/user)
4. ✅ Temporal Clustering Ring (70%+ same timestamp)
5. ✅ High-Value Ring ($8,000+ spending)
6. ✅ **NEW: Organized Fraud Ring (fake identity + geo mismatch)**

---

## Data Column Requirements

The detector works with flexible column names:

**Name Column (any of):**
- `billing_first_name`
- `first_name`
- `customer_name`
- `user_name`
- `name`

**Email Column (any of):**
- `email`
- `customer_email`
- `user_email`
- `email_address`

**Card Country Column (any of):**
- `bin_country_code`
- `card_country`
- `payment_country`
- `country`

**Route Columns (any of):**
- `departure` / `departure_city` / `from_city`
- `arrival` / `arrival_city` / `to_city`

**Carrier Column (any of):**
- `carrier_name`
- `carrier`
- `transport_provider`

**Amount Column (any of):**
- `amount`
- `total_amount`
- `transaction_amount`
- `price`

---

## Example Use Case

**Scenario:** Travel booking fraud

**Data Uploaded:**
```csv
billing_first_name,email,bin_country_code,departure,arrival,carrier_name,amount
asd,user1@dwa.dfs,SG,Düsseldorf,Berlin,Deutsche Bahn,52.30
asd,user2@ds.dfg,SG,Düsseldorf,Berlin,Deutsche Bahn,48.90
asd,user3@ghf.fgh,PH,Düsseldorf,Bremen,Deutsche Bahn,65.20
...
```

**Detection Result:**
```
Organized Fraud Ring Detected: "asd"
- Severity: CRITICAL
- Orders: 272
- Total Fraud: €14,296.35
- Risk Score: 1.0

Key Indicators:
✓ Fake name "asd" (100% of orders)
✓ 131 gibberish email domains
✓ 87.9% cards from Singapore for German travel
✓ 100% departures from Düsseldorf
✓ Exclusive Deutsche Bahn targeting

Recommendations:
1. Block orders with name "asd" immediately
2. Flag gibberish email domains
3. Implement geo-mismatch checks
4. Add velocity limits for Düsseldorf
5. Deploy composite fraud scoring
```

---

## Testing the Detector

### Create Test Data

```python
import pandas as pd

# Create synthetic organized fraud data
data = []
for i in range(272):
    order = {
        'billing_first_name': 'asd',
        'email': f'user{i}@dwa.dfs',
        'bin_country_code': 'SG',
        'departure': 'Düsseldorf',
        'arrival': 'Berlin',
        'carrier_name': 'Deutsche Bahn',
        'amount': 52.56
    }
    data.append(order)

df = pd.DataFrame(data)
df.to_csv('organized_fraud_test.csv', index=False)
```

### Test via API

```bash
curl -X POST "http://localhost:8000/upload-and-analyze" \
  -F "file=@organized_fraud_test.csv" \
  | jq '.organized_fraud'
```

### Expected Output

```json
{
  "total_rings_detected": 1,
  "total_fraud_amount": 14295.92,
  "total_fraudulent_orders": 272,
  "rings": [
    {
      "ring_name": "Organized Fraud Ring: 'asd'",
      "severity": "CRITICAL",
      "risk_score": 1.0,
      ...
    }
  ]
}
```

---

## Customization

### Adjust Detection Thresholds

Edit `backend/app/services/analytics/organized_fraud_detector.py`:

```python
# Minimum orders to form a ring
if len(ring_orders) >= 5:  # Change to 10 for stricter detection
    ring = self._analyze_fraud_ring(ring_orders, fake_name)
```

### Add Custom Fake Name Patterns

```python
self.fake_name_patterns = [
    r'^asd+$',
    r'^qwe+$',
    r'^yourpattern$',  # Add your custom pattern
]
```

### Add Custom Email Domain Patterns

```python
self.suspicious_email_patterns = [
    r'^[a-z]{1,5}\\.[a-z]{1,5}$',
    r'@suspicious-domain\\.com$',  # Add your pattern
]
```

### Whitelist Your Email Domains

```python
self.legitimate_domains = {
    'gmail.com',
    'yahoo.com',
    'your-company-domain.com',  # Add your domain
}
```

---

## Production Deployment

### Immediate Actions

1. **Block Fake Names:**
   ```python
   if billing_name in ['asd', 'qwe', 'test', 'zxc']:
       return {"status": "blocked", "reason": "Fake name detected"}
   ```

2. **Email Validation:**
   ```python
   domain = email.split('@')[1]
   if domain not in legitimate_domains:
       flag_for_review(transaction)
   ```

3. **Geographic Checks:**
   ```python
   if card_country != route_country:
       require_additional_verification()
   ```

### Long-Term Monitoring

1. **Pattern Tracking:**
   - Monitor for new fake name patterns (qwe, zxc, abc)
   - Track emerging gibberish domain patterns
   - Watch for geographic mismatch trends

2. **Composite Scoring:**
   ```python
   risk_score = (
       0.3 * fake_name_score +
       0.2 * email_score +
       0.2 * geo_mismatch_score +
       0.15 * route_concentration_score +
       0.15 * proxy_score
   )
   ```

3. **Automated Alerts:**
   - Email notifications for CRITICAL rings
   - Slack/webhook integrations
   - Real-time dashboard updates

---

## Summary

Your fraud detection system now includes **6 major fraud ring detection methods**:

| Ring Type | Detection Method | Key Indicator |
|-----------|-----------------|---------------|
| High Velocity | Transaction frequency | 5+ transactions/user |
| Cross-Border | Geographic impossibility | 3+ countries/user |
| Merchant Cycling | Card testing | 5+ merchants/user |
| Temporal Clustering | Bot activity | 70%+ same timestamp |
| High-Value | Money laundering | $8,000+ spending |
| **Organized Fraud** | **Fake identity + geo mismatch** | **Fake names + gibberish emails** |

The Organized Fraud Detector specifically targets sophisticated fraud operations that use:
- Fake/test identities
- Random email generation
- Payment/travel geographic mismatches
- Concentrated targeting patterns

---

*Last Updated: 2025-12-08*
*System: Fraud Ring Detection Platform v1.1*
*Module: OrganizedFraudDetector*
