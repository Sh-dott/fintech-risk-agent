"""
AML/Sanctions Rules Engine

Implements FATF compliance rules for:
- Sanctions list screening (UN, OFAC, EU, UK)
- PEP (Politically Exposed Person) checks
- Suspicious transaction reporting (STR)
- Entity risk scoring
"""

from typing import Dict, List, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import json


class SanctionsListType(Enum):
    """Supported sanctions lists."""
    OFAC = "ofac"  # US Office of Foreign Assets Control
    UN = "un"  # UN Security Council
    EU = "eu"  # EU consolidated list
    UK = "uk"  # UK consolidated list
    HMT = "hmt"  # UK HM Treasury


class PEPLevel(Enum):
    """PEP risk levels."""
    DIRECT = "direct"  # Direct PEP
    FAMILY = "family"  # Family member of PEP
    CLOSE_ASSOCIATE = "close_associate"  # Known close associate


@dataclass
class SanctionsHit:
    """Result of sanctions screening."""
    hit: bool
    list_type: SanctionsListType
    match_strength: float  # 0.0-1.0 confidence
    entity_name: str = ""
    reason: str = ""


@dataclass
class PEPMatch:
    """Result of PEP screening."""
    is_pep: bool
    pep_level: PEPLevel
    entity_name: str = ""
    match_strength: float = 0.0


class AMLRulesEngine:
    """
    AML/Sanctions rules and screening logic.

    In production: integrate with external providers (Compliance.ai, SanctionsList, etc.)
    """

    def __init__(self):
        """Initialize with mock sanctions/PEP lists."""
        # Mock sanctions lists (in production: external APIs/databases)
        self.sanctions_lists = {
            SanctionsListType.OFAC: ["North Korea Entity 1", "Iran Bank X"],
            SanctionsListType.UN: ["UN Sanctioned Individual"],
            SanctionsListType.EU: ["EU Listed Person"],
        }

        self.pep_database = {
            "Vladimir Putin": PEPLevel.DIRECT,
            "Xi Jinping": PEPLevel.DIRECT,
            "Putin Family Member": PEPLevel.FAMILY,
        }

    def screen_sanctions(
        self,
        entity_name: str,
        entity_country: str
    ) -> Tuple[float, List[str], List[SanctionsHit]]:
        """
        Screen entity against sanctions lists.

        Returns:
            risk_score: 0.0-1.0
            reason_codes: List of codes (e.g., "SANCTIONS_OFAC_HIT")
            hits: Detailed match information
        """
        risk_score = 0.0
        reason_codes = []
        hits = []

        # Simulate fuzzy matching against lists
        for list_type, entities in self.sanctions_lists.items():
            for sanctioned_entity in entities:
                # Simple substring match (in production: fuzzy matching + ML)
                if sanctioned_entity.lower() in entity_name.lower():
                    match_strength = 0.95
                    hits.append(SanctionsHit(
                        hit=True,
                        list_type=list_type,
                        match_strength=match_strength,
                        entity_name=entity_name,
                        reason=f"Match: {sanctioned_entity}"
                    ))
                    risk_score = max(risk_score, match_strength)
                    reason_codes.append(f"SANCTIONS_{list_type.value.upper()}_HIT")

        # Country-based screening (simple example)
        high_risk_countries = ["KP", "IR", "SY"]  # North Korea, Iran, Syria
        if entity_country in high_risk_countries:
            risk_score = max(risk_score, 0.85)
            reason_codes.append(f"HIGH_RISK_COUNTRY_{entity_country}")

        return risk_score, reason_codes, hits

    def screen_pep(self, entity_name: str) -> Tuple[float, List[str], List[PEPMatch]]:
        """
        Screen entity for PEP status.

        Returns:
            risk_score: 0.0-1.0
            reason_codes: List of codes (e.g., "PEP_DIRECT")
            matches: Detailed match information
        """
        risk_score = 0.0
        reason_codes = []
        matches = []

        # Check PEP database
        for pep_name, pep_level in self.pep_database.items():
            if pep_name.lower() in entity_name.lower():
                match = PEPMatch(
                    is_pep=True,
                    pep_level=pep_level,
                    entity_name=entity_name,
                    match_strength=0.95
                )
                matches.append(match)

                # Score based on PEP level
                if pep_level == PEPLevel.DIRECT:
                    risk_score = 0.95
                    reason_codes.append("PEP_DIRECT")
                elif pep_level == PEPLevel.FAMILY:
                    risk_score = 0.7
                    reason_codes.append("PEP_FAMILY")
                elif pep_level == PEPLevel.CLOSE_ASSOCIATE:
                    risk_score = 0.5
                    reason_codes.append("PEP_CLOSE_ASSOCIATE")

        return risk_score, reason_codes, matches

    def check_transaction_threshold(
        self,
        transaction_amount: float,
        transaction_currency: str,
        time_period_hours: int = 24
    ) -> Tuple[float, List[str]]:
        """
        Check if transaction exceeds reporting thresholds (FATF/FinCEN).

        Returns:
            risk_score: 0.0-1.0
            reason_codes: List of codes
        """
        risk_score = 0.0
        reason_codes = []

        # CTF (Counter-Terrorism Financing) threshold: $10,000+ USD equivalent
        ctf_threshold = 10000.0
        if transaction_amount >= ctf_threshold:
            risk_score += 0.2
            reason_codes.append(f"CTF_THRESHOLD_EXCEEDED_{transaction_amount}")

        # Unusual pattern: multiple small transactions below threshold (structuring)
        # This would be implemented at the account level
        # risk_score += structuring_check_result

        return min(risk_score, 1.0), reason_codes

    def check_transaction_risk(
        self,
        transaction: Dict[str, Any],
        entity_profile: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check transaction-level AML indicators.

        Red flags:
        - Unusual beneficiary
        - Cash-intensive business
        - Complex ownership structures
        - Rapid fund movement
        """
        risk_score = 0.0
        reason_codes = []

        # Check for unusual patterns
        transaction_amount = transaction.get("amount", 0)
        entity_avg_transaction = entity_profile.get("avg_transaction_amount", 1000)

        # Large deviation from average
        if transaction_amount > entity_avg_transaction * 10:
            risk_score += 0.15
            reason_codes.append("UNUSUAL_TRANSACTION_AMOUNT")

        # Check destination country
        destination_country = transaction.get("destination_country")
        high_risk_jurisdictions = ["KP", "IR", "SY", "CU"]
        if destination_country in high_risk_jurisdictions:
            risk_score += 0.3
            reason_codes.append(f"HIGH_RISK_DESTINATION_{destination_country}")

        # Check business type risk
        business_type = entity_profile.get("business_type", "")
        cash_intensive = ["GAMBLING", "CASH_ADVANCE", "CURRENCY_EXCHANGE"]
        if business_type in cash_intensive:
            risk_score += 0.1
            reason_codes.append(f"CASH_INTENSIVE_{business_type}")

        return min(risk_score, 1.0), reason_codes

    def generate_str(
        self,
        transaction_id: str,
        user_id: str,
        risk_indicators: List[str],
        risk_score: float
    ) -> Dict[str, Any]:
        """
        Generate Suspicious Transaction Report (STR) for filing.

        In production: submit to FinCEN, FCA, etc. as required.
        """
        return {
            "report_type": "STR",
            "transaction_id": transaction_id,
            "user_id": user_id,
            "risk_score": risk_score,
            "indicators": risk_indicators,
            "filing_required": risk_score > 0.7,
            "jurisdiction": "US"  # Would be determined dynamically
        }

    def check_velocity_abuse(
        self,
        user_id: str,
        transactions_24h: int,
        amount_24h: float
    ) -> Tuple[float, List[str]]:
        """
        Check for velocity abuse (structuring, rapid movement).

        FATF: Suspicious if many small txns that avoid reporting thresholds.
        """
        risk_score = 0.0
        reason_codes = []

        # High transaction count
        if transactions_24h > 50:
            risk_score += 0.25
            reason_codes.append(f"HIGH_TRANSACTION_VELOCITY_{transactions_24h}")

        # Rapid movement of funds
        if amount_24h > 100000:
            risk_score += 0.15
            reason_codes.append(f"RAPID_FUND_MOVEMENT_{amount_24h}")

        # Consistent pattern just below threshold (structuring)
        avg_per_txn = amount_24h / max(transactions_24h, 1)
        if 9000 < avg_per_txn < 9900:  # Just below $10k threshold
            risk_score += 0.4
            reason_codes.append("STRUCTURING_PATTERN_DETECTED")

        return min(risk_score, 1.0), reason_codes


class STRFilingQueue:
    """
    Queue for Suspicious Transaction Reports to be filed with authorities.

    In production: integrate with compliance team workflows and regulatory APIs.
    """

    def __init__(self):
        self.pending_strs: List[Dict[str, Any]] = []
        self.filed_strs: List[Dict[str, Any]] = []

    def enqueue_str(self, str_report: Dict[str, Any]) -> str:
        """Add STR to queue. Returns report ID."""
        report_id = f"str_{len(self.pending_strs):06d}"
        str_report["report_id"] = report_id
        str_report["status"] = "PENDING"
        self.pending_strs.append(str_report)
        return report_id

    def file_str(self, report_id: str) -> bool:
        """File STR with authorities (simulated)."""
        for i, str_report in enumerate(self.pending_strs):
            if str_report.get("report_id") == report_id:
                str_report["status"] = "FILED"
                self.filed_strs.append(str_report)
                self.pending_strs.pop(i)
                return True
        return False

    def get_pending_count(self) -> int:
        """Get count of pending STRs."""
        return len(self.pending_strs)


def main():
    """Demo AML rules engine."""
    engine = AMLRulesEngine()

    # Test sanctions screening
    print("=" * 60)
    print("SANCTIONS SCREENING TEST")
    print("=" * 60)

    risk, codes, hits = engine.screen_sanctions(
        entity_name="North Korea Entity 1",
        entity_country="KP"
    )
    print(f"Risk Score: {risk:.2f}")
    print(f"Reason Codes: {codes}")
    print(f"Hits: {[h.reason for h in hits]}\n")

    # Test PEP screening
    print("=" * 60)
    print("PEP SCREENING TEST")
    print("=" * 60)

    risk, codes, matches = engine.screen_pep(entity_name="Vladimir Putin")
    print(f"Risk Score: {risk:.2f}")
    print(f"Reason Codes: {codes}")
    print(f"Matches: {matches}\n")

    # Test velocity abuse
    print("=" * 60)
    print("VELOCITY ABUSE TEST")
    print("=" * 60)

    risk, codes = engine.check_velocity_abuse(
        user_id="usr_123",
        transactions_24h=75,
        amount_24h=225000
    )
    print(f"Risk Score: {risk:.2f}")
    print(f"Reason Codes: {codes}\n")


if __name__ == "__main__":
    main()
