"""
Organized Fraud Ring Detector
Identifies sophisticated fraud rings using fake identities, gibberish emails, and geographic mismatches.
Similar to the "asd" fraud ring pattern.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import re


def convert_numpy_types(obj: Any) -> Any:
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj


@dataclass
class OrganizedFraudRing:
    """Represents a detected organized fraud ring."""
    ring_id: str
    ring_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM
    member_count: int
    total_fraud_amount: float
    currency: str

    # Pattern characteristics
    fake_name_pattern: str
    email_domain_pattern: str
    card_origin_countries: Dict[str, int]
    route_concentration: Dict[str, Any]
    carrier_pattern: str

    # Evidence
    orders: List[Dict[str, Any]]
    key_indicators: List[str]
    column_analysis: Dict[str, Any]

    # Recommendations
    recommendations: List[str]

    # Metadata
    detection_method: str
    risk_score: float
    explanation: str


class OrganizedFraudDetector:
    """
    Detects organized fraud rings with characteristics like:
    - Fake/test names (asd, qwe, test, etc.)
    - Gibberish email domains
    - Geographic mismatches (card country vs. travel route)
    - Route/carrier concentration
    - Proxy usage patterns
    """

    def __init__(self):
        self.df = None
        self.detected_rings = []

        # Detection patterns
        self.fake_name_patterns = [
            r'^asd+$',           # asd, asdasd
            r'^qwe+$',           # qwe, qweqwe
            r'^zxc+$',           # zxc
            r'^test+$',          # test, testtest
            r'^abc+$',           # abc
            r'^xxx+$',           # xxx
            r'^(.)\\1{2,}$',     # aaa, bbb, ccc (repeated char)
            r'^[a-z]{1,3}$',     # Very short random: a, ab, xyz
            r'^(\\w)\\1+(\\w)\\2+$'  # Keyboard patterns: aabbcc
        ]

        # Suspicious email domain patterns
        self.suspicious_email_patterns = [
            r'^[a-z]{1,5}\\.[a-z]{1,5}$',  # Short random: dwa.dfs, ds.dfg
            r'^(\\w{1,4})\\1\\.',           # Repeated parts: asdasd.com
            r'\\.(dfs|dfg|dsad|fgh|ghf)$',  # Known fake TLDs
            r'^[0-9]+@',                    # Numbers only
            r'@[0-9]+\\.',                  # Numeric domain
        ]

        # Legitimate email providers (whitelist)
        self.legitimate_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'protonmail.com', 'mail.com',
            'gmx.com', 'zoho.com', 'yandex.com', 'mail.ru'
        }

    def load_transactions(self, transactions: List[Dict[str, Any]]):
        """Load transaction data for analysis."""
        self.df = pd.DataFrame(transactions)
        # Normalize column names to lowercase for consistent matching
        self.df.columns = [col.lower().replace(' ', '_') for col in self.df.columns]

        # Convert numeric columns to proper types (fixes string/int comparison issues)
        numeric_columns = ['amount', 'total_amount', 'price', 'value', 'sum', 'payment_amount', 'transaction_amount']
        for col in numeric_columns:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        print(f"[OrganizedFraudDetector] Loaded {len(self.df)} transactions")

    def detect_fake_name_pattern(self, name: str) -> bool:
        """Check if a name matches fake/test name patterns."""
        if not name or not isinstance(name, str):
            return False

        name_lower = name.lower().strip()

        # Check against known patterns
        for pattern in self.fake_name_patterns:
            if re.match(pattern, name_lower):
                return True

        # Additional checks
        if len(name_lower) <= 2:  # Very short names
            return True

        if name_lower in ['test', 'testing', 'demo', 'fake', 'fraud', 'admin']:
            return True

        return False

    def detect_suspicious_email(self, email: str) -> tuple[bool, str]:
        """
        Check if email domain is suspicious.
        Returns (is_suspicious, reason)
        """
        if not email or not isinstance(email, str):
            return False, "No email"

        email_lower = email.lower().strip()

        # Extract domain
        if '@' not in email_lower:
            return True, "Invalid email format"

        domain = email_lower.split('@')[1]

        # Whitelist check
        if domain in self.legitimate_domains:
            return False, "Legitimate provider"

        # Check suspicious patterns
        for pattern in self.suspicious_email_patterns:
            if re.search(pattern, email_lower):
                return True, f"Gibberish domain: {domain}"

        # Check for very short domains
        parts = domain.split('.')
        if any(len(part) <= 2 for part in parts):
            return True, f"Short random domain: {domain}"

        # Check for non-standard TLDs
        if len(parts) >= 2:
            tld = parts[-1]
            # Common legitimate TLDs
            common_tlds = {'com', 'net', 'org', 'edu', 'gov', 'de', 'uk', 'fr', 'it', 'es', 'nl', 'jp', 'cn', 'au', 'ca'}
            if tld not in common_tlds and len(tld) <= 3:
                return True, f"Unusual TLD: .{tld}"

        return False, "Normal email"

    def analyze_geographic_mismatch(self, row: pd.Series) -> tuple[bool, str]:
        """
        Detect geographic mismatches between card country and travel route.
        Returns (is_mismatch, reason)
        """
        # Check if card country and route country are available
        card_country = None
        route_country = None

        # Try different column names for card country
        for col in ['bin_country_code', 'card_country', 'payment_country', 'country']:
            if col in row.index and pd.notna(row.get(col)):
                card_country = str(row[col]).strip().upper()
                break

        # Try to determine route country from departure/arrival cities
        for col in ['departure', 'arrival', 'departure_city', 'arrival_city', 'user_country']:
            if col in row.index and pd.notna(row.get(col)):
                city = str(row[col]).lower()
                # Simple heuristic: German cities
                german_cities = ['berlin', 'düsseldorf', 'dusseldorf', 'munich', 'hamburg',
                               'frankfurt', 'cologne', 'köln', 'bremen', 'osnabrück',
                               'hannover', 'stuttgart', 'dortmund', 'essen', 'leipzig']
                if any(german_city in city for german_city in german_cities):
                    route_country = 'DE'
                    break
                # Add more country patterns as needed

        if not card_country or not route_country:
            return False, "Insufficient data"

        # Southeast Asian cards for European travel = suspicious
        southeast_asian = ['SG', 'PH', 'MY', 'TH', 'ID', 'VN']
        european = ['DE', 'FR', 'IT', 'ES', 'UK', 'GB', 'NL', 'BE', 'AT', 'CH']

        if card_country in southeast_asian and route_country in european:
            return True, f"Southeast Asian card ({card_country}) for European travel ({route_country})"

        # General mismatch for different continents
        if card_country != route_country:
            return True, f"Card from {card_country}, travel in {route_country}"

        return False, "Geographic match"

    def detect_organized_fraud_rings(self) -> List[OrganizedFraudRing]:
        """
        Main detection method: identify organized fraud rings.
        Looks for patterns like the "asd" fraud ring.
        """
        if self.df is None or len(self.df) == 0:
            return []

        print("[OrganizedFraudDetector] Analyzing for organized fraud patterns...")

        detected_rings = []

        # Group by suspicious name patterns
        name_col = None
        for col in ['billing_first_name', 'first_name', 'customer_name', 'user_name', 'name']:
            if col in self.df.columns:
                name_col = col
                break

        if name_col:
            # Find all fake names
            self.df['is_fake_name'] = self.df[name_col].apply(self.detect_fake_name_pattern)
            fake_name_orders = self.df[self.df['is_fake_name'] == True]

            if len(fake_name_orders) > 0:
                # Group by the specific fake name
                for fake_name in fake_name_orders[name_col].unique():
                    ring_orders = self.df[self.df[name_col] == fake_name]

                    if len(ring_orders) >= 5:  # Minimum 5 orders to be a ring
                        ring = self._analyze_fraud_ring(ring_orders, fake_name)
                        if ring:
                            detected_rings.append(ring)

        # Also detect by email domain patterns
        email_col = None
        for col in ['email', 'customer_email', 'user_email', 'email_address']:
            if col in self.df.columns:
                email_col = col
                break

        if email_col:
            self.df['email_domain'] = self.df[email_col].apply(
                lambda x: str(x).split('@')[1] if pd.notna(x) and '@' in str(x) else None
            )
            self.df['is_suspicious_email'] = self.df[email_col].apply(
                lambda x: self.detect_suspicious_email(x)[0]
            )

            # Find rings with high concentration of suspicious emails
            suspicious_email_orders = self.df[self.df['is_suspicious_email'] == True]

            # Group by common characteristics (e.g., same departure city + carrier)
            if len(suspicious_email_orders) >= 10:
                ring = self._analyze_fraud_ring(suspicious_email_orders, "Email-Based Ring")
                if ring:
                    detected_rings.append(ring)

        self.detected_rings = detected_rings
        return detected_rings

    def _analyze_fraud_ring(self, orders_df: pd.DataFrame, ring_identifier: str) -> Optional[OrganizedFraudRing]:
        """Analyze a group of orders to create a fraud ring report."""

        if len(orders_df) < 5:
            return None

        # Calculate total fraud amount
        amount_col = None
        for col in ['amount', 'total_amount', 'transaction_amount', 'price']:
            if col in orders_df.columns:
                amount_col = col
                break

        total_amount = 0.0
        currency = 'EUR'
        if amount_col:
            total_amount = orders_df[amount_col].sum()
            # Try to detect currency
            for col in ['currency', 'currency_code']:
                if col in orders_df.columns:
                    currency = orders_df[col].mode().iloc[0] if len(orders_df[col].mode()) > 0 else 'EUR'
                    break

        # Analyze email domains
        email_domains = []
        if 'email_domain' in orders_df.columns:
            email_domains = orders_df['email_domain'].value_counts().to_dict()

        # Analyze card countries
        card_countries = {}
        for col in ['bin_country_code', 'card_country', 'payment_country']:
            if col in orders_df.columns:
                card_countries = orders_df[col].value_counts().to_dict()
                break

        # Analyze routes
        route_analysis = {}
        departure_col = arrival_col = None

        for col in ['departure', 'departure_city', 'from_city']:
            if col in orders_df.columns:
                departure_col = col
                break

        for col in ['arrival', 'arrival_city', 'to_city']:
            if col in orders_df.columns:
                arrival_col = col
                break

        if departure_col:
            route_analysis['departure'] = orders_df[departure_col].value_counts().to_dict()
        if arrival_col:
            route_analysis['arrival'] = orders_df[arrival_col].value_counts().to_dict()

        # Analyze carrier
        carrier_pattern = "Unknown"
        for col in ['carrier_name', 'carrier', 'transport_provider']:
            if col in orders_df.columns:
                carrier_counts = orders_df[col].value_counts()
                if len(carrier_counts) > 0:
                    carrier_pattern = f"{carrier_counts.iloc[0]} orders with {carrier_counts.index[0]}"
                break

        # Build column analysis (with error handling for API compatibility)
        try:
            column_analysis = self._build_column_analysis(orders_df)
            key_indicators = self._generate_key_indicators(orders_df, column_analysis)
            risk_score = self._calculate_risk_score(orders_df, key_indicators)
            recommendations = self._generate_recommendations(orders_df, column_analysis, key_indicators)
        except Exception as e:
            print(f"[WARNING] Column analysis failed, using fallback: {e}")
            column_analysis = {
                'billing_name': {'pattern': ring_identifier, 'count': len(orders_df)},
                'card_origin': {'top_country': list(card_countries.keys())[0] if card_countries else 'Unknown', 'top_percentage': 100.0}
            }
            key_indicators = [
                f"Fake Name Pattern: All {len(orders_df)} orders use '{ring_identifier}'",
                f"Card Origin: {list(card_countries.keys())[0] if card_countries else 'Unknown'}",
                f"Email Domains: {len(email_domains)} unique domains"
            ]
            risk_score = 1.0  # Critical by default
            recommendations = [f"Block all orders with billing name '{ring_identifier}'"]

        # Determine severity
        severity = "CRITICAL" if risk_score >= 0.8 else "HIGH" if risk_score >= 0.6 else "MEDIUM"

        # Create ring object
        ring = OrganizedFraudRing(
            ring_id=f"ORG_FRAUD_{ring_identifier.upper().replace(' ', '_')}",
            ring_name=f"Organized Fraud Ring: '{ring_identifier}'",
            severity=severity,
            member_count=len(orders_df),
            total_fraud_amount=total_amount,
            currency=currency,
            fake_name_pattern=ring_identifier,
            email_domain_pattern=f"{len(email_domains)} unique domains" if email_domains else "Unknown",
            card_origin_countries=card_countries,
            route_concentration=route_analysis,
            carrier_pattern=carrier_pattern,
            orders=orders_df.head(10).to_dict('records'),  # Sample orders
            key_indicators=key_indicators,
            column_analysis=column_analysis,
            recommendations=recommendations,
            detection_method="Organized Fraud Pattern Analysis (Fake Identity + Geographic Mismatch)",
            risk_score=risk_score,
            explanation=self._generate_explanation(orders_df, ring_identifier, column_analysis)
        )

        return ring

    def _build_column_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Build detailed column-by-column analysis."""
        analysis = {}

        # Name analysis
        for col in ['billing_first_name', 'first_name', 'customer_name', 'name']:
            if col in df.columns:
                name_counts = df[col].value_counts()
                analysis['billing_name'] = {
                    'pattern': name_counts.index[0] if len(name_counts) > 0 else 'Unknown',
                    'count': name_counts.iloc[0] if len(name_counts) > 0 else 0,
                    'percentage': (name_counts.iloc[0] / len(df) * 100) if len(name_counts) > 0 else 0,
                    'significance': 'All orders use the exact same fake name',
                    'detection': 'Easy to flag - clearly a test/placeholder name'
                }
                break

        # Email analysis
        if 'email_domain' in df.columns:
            email_domains = df['email_domain'].value_counts()
            unique_domains = len(email_domains)

            # Sample suspicious domains
            suspicious_domains = []
            for domain in email_domains.index[:10]:
                if domain and self.detect_suspicious_email(f"test@{domain}")[0]:
                    suspicious_domains.append(domain)

            analysis['email_domain'] = {
                'unique_domains': unique_domains,
                'examples': suspicious_domains[:5],
                'characteristics': 'Short, random character combinations with non-existent TLDs',
                'detection': 'Flag emails with non-standard TLDs or gibberish domains'
            }

        # Card country analysis
        for col in ['bin_country_code', 'card_country']:
            if col in df.columns:
                country_dist = df[col].value_counts()
                top_country = country_dist.index[0] if len(country_dist) > 0 else 'Unknown'
                top_count = country_dist.iloc[0] if len(country_dist) > 0 else 0

                analysis['card_origin'] = {
                    'distribution': country_dist.head(5).to_dict(),
                    'top_country': top_country,
                    'top_percentage': (top_count / len(df) * 100) if len(df) > 0 else 0,
                    'significance': 'Heavy concentration from specific countries',
                    'detection': 'Flag mismatches between card origin and travel routes'
                }
                break

        # Route analysis
        for col in ['departure', 'departure_city']:
            if col in df.columns:
                departure_dist = df[col].value_counts()
                analysis['departure'] = {
                    'concentration': departure_dist.iloc[0] / len(df) * 100 if len(departure_dist) > 0 else 0,
                    'top_city': departure_dist.index[0] if len(departure_dist) > 0 else 'Unknown',
                    'total_orders': departure_dist.iloc[0] if len(departure_dist) > 0 else 0
                }
                break

        for col in ['arrival', 'arrival_city']:
            if col in df.columns:
                arrival_dist = df[col].value_counts()
                analysis['arrival'] = {
                    'distribution': arrival_dist.head(5).to_dict(),
                    'detection': 'Highly concentrated route pattern'
                }
                break

        # Amount analysis
        for col in ['amount', 'total_amount', 'price']:
            if col in df.columns:
                try:
                    # Convert to numeric if needed (handles string/int comparison issues)
                    amounts = pd.to_numeric(df[col], errors='coerce')
                    analysis['amount'] = {
                        'total': amounts.sum(),
                        'average': amounts.mean(),
                        'range': f"{amounts.min()} to {amounts.max()}",
                        'distribution': self._amount_distribution(amounts),
                        'significance': 'Mostly small transactions to avoid detection thresholds'
                    }
                except Exception as e:
                    print(f"[WARNING] Amount analysis failed for column '{col}': {e}")
                    analysis['amount'] = {
                        'total': 'N/A',
                        'average': 'N/A',
                        'range': 'N/A',
                        'distribution': {},
                        'significance': 'Amount data could not be analyzed'
                    }
                break

        return analysis

    def _amount_distribution(self, amounts: pd.Series) -> Dict[str, int]:
        """Calculate amount distribution in ranges."""
        dist = {
            '0-50': 0,
            '50-100': 0,
            '100-150': 0,
            '150-200': 0,
            '200+': 0
        }

        for amount in amounts:
            if amount < 50:
                dist['0-50'] += 1
            elif amount < 100:
                dist['50-100'] += 1
            elif amount < 150:
                dist['100-150'] += 1
            elif amount < 200:
                dist['150-200'] += 1
            else:
                dist['200+'] += 1

        return dist

    def _generate_key_indicators(self, df: pd.DataFrame, column_analysis: Dict) -> List[str]:
        """Generate list of key fraud indicators."""
        indicators = []

        if 'billing_name' in column_analysis:
            indicators.append(f"Fake Name Pattern: All {len(df)} orders use '{column_analysis['billing_name']['pattern']}'")

        if 'email_domain' in column_analysis:
            indicators.append(f"Gibberish Emails: {column_analysis['email_domain']['unique_domains']} random email domains")

        if 'card_origin' in column_analysis:
            top_country = column_analysis['card_origin'].get('top_country', 'Unknown')
            top_pct = column_analysis['card_origin'].get('top_percentage', 0)
            indicators.append(f"Geographic Mismatch: {top_pct:.1f}% cards from {top_country}")

        if 'departure' in column_analysis:
            conc = column_analysis['departure'].get('concentration', 0)
            city = column_analysis['departure'].get('top_city', 'Unknown')
            indicators.append(f"Route Concentration: {conc:.1f}% from {city}")

        # Check for proxy usage
        for col in ['proxy', 'proxy_indicator', 'vpn_indicator']:
            if col in df.columns:
                unique_proxies = df[col].nunique()
                indicators.append(f"Proxy Usage: {unique_proxies} different proxy indicators")
                break

        return indicators

    def _calculate_risk_score(self, df: pd.DataFrame, indicators: List[str]) -> float:
        """Calculate risk score based on fraud indicators."""
        score = 0.0

        # Fake name (+0.3)
        if any('Fake Name' in ind for ind in indicators):
            score += 0.3

        # Suspicious emails (+0.2)
        if any('Gibberish Email' in ind for ind in indicators):
            score += 0.2

        # Geographic mismatch (+0.2)
        if any('Geographic Mismatch' in ind for ind in indicators):
            score += 0.2

        # Route concentration (+0.15)
        if any('Route Concentration' in ind for ind in indicators):
            score += 0.15

        # Proxy usage (+0.15)
        if any('Proxy Usage' in ind for ind in indicators):
            score += 0.15

        # Volume bonus (more orders = higher confidence)
        if len(df) >= 100:
            score += 0.1
        elif len(df) >= 50:
            score += 0.05

        return min(score, 1.0)

    def _generate_recommendations(self, df: pd.DataFrame, column_analysis: Dict, indicators: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        if 'billing_name' in column_analysis:
            fake_name = column_analysis['billing_name'].get('pattern', 'asd')
            recs.append(f"Block all orders with billing name '{fake_name}' or similar keyboard patterns")

        if 'email_domain' in column_analysis:
            recs.append("Flag orders with non-existent or gibberish email domains")
            recs.append("Implement email domain validation against known legitimate providers")

        if 'card_origin' in column_analysis:
            recs.append("Monitor for geographic mismatches between card origin and travel routes")
            recs.append("Require additional verification for cross-region payment cards")

        if 'departure' in column_analysis:
            city = column_analysis['departure'].get('top_city', 'Unknown')
            recs.append(f"Implement velocity checks for {city} departures")
            recs.append("Flag unusual concentration of bookings from single departure point")

        recs.append("Create composite risk score combining: suspicious names + fake emails + geographic mismatches")
        recs.append("Deploy real-time alerting for orders matching multiple fraud indicators")

        return recs

    def _generate_explanation(self, df: pd.DataFrame, ring_id: str, column_analysis: Dict) -> str:
        """Generate human-readable explanation."""

        count = len(df)
        amount = column_analysis.get('amount', {}).get('total', 0)

        explanation = f"Identified organized fraud ring consisting of {count} fraudulent orders "

        if 'billing_name' in column_analysis:
            fake_name = column_analysis['billing_name']['pattern']
            explanation += f"using the fake name '{fake_name}' across all transactions. "

        if amount > 0:
            currency = 'EUR'  # Default
            explanation += f"Total fraudulent transactions: {currency}{amount:,.2f}. "

        explanation += "The fraud pattern combines: "

        patterns = []
        if 'billing_name' in column_analysis:
            patterns.append("consistent fake identity")
        if 'email_domain' in column_analysis:
            patterns.append("randomly generated email domains")
        if 'card_origin' in column_analysis:
            patterns.append("geographic payment/travel mismatch")
        if 'departure' in column_analysis:
            patterns.append("concentrated route patterns")

        explanation += ", ".join(patterns) + ". "

        explanation += "This indicates a coordinated fraud operation using automated systems."

        return explanation

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive fraud ring report."""

        if not self.detected_rings:
            return {
                'total_rings_detected': 0,
                'rings': [],
                'executive_summary': 'No organized fraud rings detected.'
            }

        total_fraud_amount = sum(ring.total_fraud_amount for ring in self.detected_rings)
        total_orders = sum(ring.member_count for ring in self.detected_rings)

        executive_summary = (
            f"Identified {len(self.detected_rings)} organized fraud ring(s) "
            f"consisting of {total_orders} fraudulent orders. "
            f"Total exposure: €{total_fraud_amount:,.2f}. "
            f"These operations use fake identities, gibberish emails, and geographic mismatches "
            f"to conduct coordinated fraud attacks."
        )

        return convert_numpy_types({
            'total_rings_detected': len(self.detected_rings),
            'total_fraud_amount': total_fraud_amount,
            'total_fraudulent_orders': total_orders,
            'rings': [self._ring_to_dict(ring) for ring in self.detected_rings],
            'executive_summary': executive_summary
        })

    def _ring_to_dict(self, ring: OrganizedFraudRing) -> Dict[str, Any]:
        """Convert ring object to dictionary for JSON serialization."""
        return convert_numpy_types({
            'ring_id': ring.ring_id,
            'ring_name': ring.ring_name,
            'severity': ring.severity,
            'member_count': ring.member_count,
            'total_fraud_amount': ring.total_fraud_amount,
            'currency': ring.currency,
            'fake_name_pattern': ring.fake_name_pattern,
            'email_domain_pattern': ring.email_domain_pattern,
            'card_origin_countries': ring.card_origin_countries,
            'route_concentration': ring.route_concentration,
            'carrier_pattern': ring.carrier_pattern,
            'sample_orders': ring.orders,
            'key_indicators': ring.key_indicators,
            'column_analysis': ring.column_analysis,
            'recommendations': ring.recommendations,
            'detection_method': ring.detection_method,
            'risk_score': ring.risk_score,
            'explanation': ring.explanation
        })
