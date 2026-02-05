"""
Rule-based seed label generation for ring classification.

Produces synthetic labels from known ring pattern signatures
to bootstrap the ML classifier.
"""

import numpy as np
from typing import List

from .schemas import RingFeatureVector

# Label constants
LABEL_CARD_TESTING = 0
LABEL_MULE_MERCHANT = 1
LABEL_LEGIT = 2
LABEL_UNKNOWN_SUSPICIOUS = 3

LABEL_NAMES = {
    LABEL_CARD_TESTING: "RingA_CardTesting",
    LABEL_MULE_MERCHANT: "RingB_MuleMerchant",
    LABEL_LEGIT: "Legit",
    LABEL_UNKNOWN_SUSPICIOUS: "UnknownSuspicious",
}


class SyntheticLabelGenerator:
    """Generates seed labels for ring feature vectors using rule-based heuristics."""

    @staticmethod
    def label_rings(ring_features: List[RingFeatureVector]) -> np.ndarray:
        """
        Assign synthetic labels based on ring pattern signatures.

        RingA_CardTesting (0): high micro_amount_ratio OR high threshold_amount_ratio,
            high burstiness_cv, shared devices >= 1
        RingB_MuleMerchant (1): high merchant_hhi, high device_sharing,
            shared IP prefixes >= 2
        Legit (2): low sharing scores, no shared devices
        UnknownSuspicious (3): fallback
        """
        labels = np.full(len(ring_features), LABEL_UNKNOWN_SUSPICIOUS, dtype=int)

        for i, rf in enumerate(ring_features):
            # Check CardTesting pattern
            is_card_testing = (
                (rf.mean_micro_amount_ratio > 0.3 or rf.mean_threshold_amount_ratio > 0.2)
                and rf.mean_burstiness_cv > 0.5
                and rf.shared_device_count >= 1
            )

            # Check MuleMerchant pattern
            is_mule_merchant = (
                rf.mean_merchant_hhi > 0.5
                and rf.mean_device_sharing > 0.5
                and rf.shared_ip_prefix_count >= 2
            )

            # Check Legit pattern
            is_legit = (
                rf.mean_device_sharing < 0.1
                and rf.mean_subnet_sharing_24 < 0.1
                and rf.mean_subnet_sharing_16 < 0.1
                and rf.shared_device_count == 0
                and rf.mean_burstiness_cv < 0.3
            )

            if is_card_testing:
                labels[i] = LABEL_CARD_TESTING
            elif is_mule_merchant:
                labels[i] = LABEL_MULE_MERCHANT
            elif is_legit:
                labels[i] = LABEL_LEGIT
            # else: remains LABEL_UNKNOWN_SUSPICIOUS

        return labels
