"""
Feature engineering for fraud ring detection.

Computes per-user, per-device, per-merchant, and per-ring features
from raw transaction data using vectorized numpy/pandas operations.
"""

import numpy as np
import pandas as pd
from typing import List, Optional

from .schemas import RingCandidate, RingFeatureVector


class RingFeatureEngineer:
    """Derives features from transaction DataFrames for ring detection."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def derive_ip_features(self) -> None:
        """Parse ip_address -> ip_prefix_24 (first 3 octets), ip_prefix_16 (first 2 octets)."""
        if "ip_address" not in self.df.columns:
            self.df["ip_prefix_24"] = ""
            self.df["ip_prefix_16"] = ""
            return

        ip_col = self.df["ip_address"].fillna("").astype(str)

        def _parse_prefix(ip: str, octets: int) -> str:
            parts = ip.split(".")
            if len(parts) >= octets:
                return ".".join(parts[:octets])
            return ""

        self.df["ip_prefix_24"] = ip_col.apply(lambda x: _parse_prefix(x, 3))
        self.df["ip_prefix_16"] = ip_col.apply(lambda x: _parse_prefix(x, 2))

    def derive_email_domain(self) -> None:
        """Parse email -> email_domain."""
        if "email" not in self.df.columns:
            self.df["email_domain"] = ""
            return

        email_col = self.df["email"].fillna("").astype(str)
        self.df["email_domain"] = email_col.apply(
            lambda x: x.split("@")[1] if "@" in x else ""
        )

    def derive_card_bin(self) -> None:
        """Extract card_bin from card_number if not already present."""
        if "card_bin" in self.df.columns:
            self.df["card_bin"] = self.df["card_bin"].fillna("").astype(str)
            return
        if "card_number" in self.df.columns:
            self.df["card_bin"] = (
                self.df["card_number"].fillna("").astype(str).str[:6]
            )
        else:
            self.df["card_bin"] = ""

    def compute_per_user_features(self) -> pd.DataFrame:
        """Compute per-user aggregated features."""
        df = self.df
        if "user_id" not in df.columns:
            return pd.DataFrame()

        grouped = df.groupby("user_id")

        # Basic stats
        user_features = grouped.agg(
            txn_count=("user_id", "count"),
        ).reset_index()

        # Amount stats
        if "amount" in df.columns:
            amount_stats = grouped["amount"].agg(
                amount_mean="mean",
                amount_std="std",
                amount_max="max",
            ).reset_index()
            amount_stats["amount_std"] = amount_stats["amount_std"].fillna(0.0)
            user_features = user_features.merge(amount_stats, on="user_id", how="left")
        else:
            user_features["amount_mean"] = 0.0
            user_features["amount_std"] = 0.0
            user_features["amount_max"] = 0.0

        # Micro amount ratio (amount < 10)
        if "amount" in df.columns:
            micro = df.assign(is_micro=(df["amount"] < 10).astype(int))
            micro_ratio = micro.groupby("user_id")["is_micro"].mean().reset_index()
            micro_ratio.columns = ["user_id", "micro_amount_ratio"]
            user_features = user_features.merge(micro_ratio, on="user_id", how="left")
        else:
            user_features["micro_amount_ratio"] = 0.0

        # Threshold amount ratio (within +/-2 of common thresholds)
        thresholds = [49.99, 79.99, 99.99, 149.99, 199.99, 249.99]
        if "amount" in df.columns:
            def _is_near_threshold(amount):
                return any(abs(amount - t) <= 2.0 for t in thresholds)

            near_thresh = df.assign(
                is_threshold=df["amount"].apply(_is_near_threshold).astype(int)
            )
            thresh_ratio = near_thresh.groupby("user_id")["is_threshold"].mean().reset_index()
            thresh_ratio.columns = ["user_id", "threshold_amount_ratio"]
            user_features = user_features.merge(thresh_ratio, on="user_id", how="left")
        else:
            user_features["threshold_amount_ratio"] = 0.0

        # Merchant concentration HHI
        if "merchant_id" in df.columns:
            merchant_hhi = self._compute_hhi(df, "user_id", "merchant_id")
            merchant_hhi.columns = ["user_id", "merchant_concentration_hhi"]
            user_features = user_features.merge(merchant_hhi, on="user_id", how="left")

            merchant_gini = self._compute_gini(df, "user_id", "merchant_id")
            merchant_gini.columns = ["user_id", "merchant_concentration_gini"]
            user_features = user_features.merge(merchant_gini, on="user_id", how="left")
        else:
            user_features["merchant_concentration_hhi"] = 0.0
            user_features["merchant_concentration_gini"] = 0.0

        # Card BIN concentration HHI
        if "card_bin" in df.columns:
            bin_hhi = self._compute_hhi(df, "user_id", "card_bin")
            bin_hhi.columns = ["user_id", "bin_concentration"]
            user_features = user_features.merge(bin_hhi, on="user_id", how="left")
        else:
            user_features["bin_concentration"] = 0.0

        # Device sharing score
        if "device_fingerprint" in df.columns:
            device_sharing = self._compute_sharing_score(df, "user_id", "device_fingerprint")
            device_sharing.columns = ["user_id", "device_sharing_score"]
            user_features = user_features.merge(device_sharing, on="user_id", how="left")
        else:
            user_features["device_sharing_score"] = 0.0

        # Subnet sharing scores
        if "ip_prefix_24" in df.columns:
            subnet24 = self._compute_sharing_score(df, "user_id", "ip_prefix_24")
            subnet24.columns = ["user_id", "subnet_sharing_score_24"]
            user_features = user_features.merge(subnet24, on="user_id", how="left")
        else:
            user_features["subnet_sharing_score_24"] = 0.0

        if "ip_prefix_16" in df.columns:
            subnet16 = self._compute_sharing_score(df, "user_id", "ip_prefix_16")
            subnet16.columns = ["user_id", "subnet_sharing_score_16"]
            user_features = user_features.merge(subnet16, on="user_id", how="left")
        else:
            user_features["subnet_sharing_score_16"] = 0.0

        # Geo mismatch rate
        if "ip_country" in df.columns and "card_country" in df.columns:
            geo = df.assign(
                geo_mismatch=(
                    (df["ip_country"].fillna("") != df["card_country"].fillna(""))
                    & (df["ip_country"].fillna("") != "")
                    & (df["card_country"].fillna("") != "")
                ).astype(int)
            )
            geo_rate = geo.groupby("user_id")["geo_mismatch"].mean().reset_index()
            geo_rate.columns = ["user_id", "geo_mismatch_rate"]
            user_features = user_features.merge(geo_rate, on="user_id", how="left")
        else:
            user_features["geo_mismatch_rate"] = 0.0

        # Temporal features (burstiness, burst windows, mean inter-arrival)
        user_features = self._compute_temporal_features(df, user_features)

        # --- New features from previously unused columns ---

        # Account age
        if "account_age_days" in df.columns:
            acct_age = df.groupby("user_id")["account_age_days"].first().reset_index()
            acct_age.columns = ["user_id", "account_age_days"]
            user_features = user_features.merge(acct_age, on="user_id", how="left")
        else:
            user_features["account_age_days"] = 365.0

        # KYC level (numeric: none=0, basic=1, enhanced=2, full=3)
        if "kyc_level" in df.columns:
            kyc_map = {"none": 0, "basic": 1, "enhanced": 2, "full": 3}
            df_kyc = df[["user_id", "kyc_level"]].copy()
            df_kyc["_kyc_numeric"] = df_kyc["kyc_level"].map(kyc_map).fillna(1)
            kyc = df_kyc.groupby("user_id")["_kyc_numeric"].first().reset_index()
            kyc.columns = ["user_id", "kyc_level_numeric"]
            user_features = user_features.merge(kyc, on="user_id", how="left")
            kyc_str = df_kyc.groupby("user_id")["kyc_level"].first().reset_index()
            user_features = user_features.merge(kyc_str, on="user_id", how="left")
        else:
            user_features["kyc_level_numeric"] = 3.0
            user_features["kyc_level"] = "full"

        # Login failures (max per user)
        if "login_failures_24h" in df.columns:
            login = df.groupby("user_id")["login_failures_24h"].max().reset_index()
            login.columns = ["user_id", "login_failures_24h"]
            user_features = user_features.merge(login, on="user_id", how="left")
        else:
            user_features["login_failures_24h"] = 0.0

        # Password change
        if "password_change_7d" in df.columns:
            pwd = df.groupby("user_id")["password_change_7d"].max().reset_index()
            pwd.columns = ["user_id", "password_change_7d"]
            user_features = user_features.merge(pwd, on="user_id", how="left")
        else:
            user_features["password_change_7d"] = 0.0

        # Merchant risk (mean per user)
        if "merchant_risk" in df.columns:
            mr = df.groupby("user_id")["merchant_risk"].mean().reset_index()
            mr.columns = ["user_id", "merchant_risk_mean"]
            user_features = user_features.merge(mr, on="user_id", how="left")
        else:
            user_features["merchant_risk_mean"] = 0.0

        # Cross-border ratio (merchant_country != ip_country)
        if "merchant_country" in df.columns and "ip_country" in df.columns:
            cb = df.assign(
                is_cross_border=(
                    (df["merchant_country"].fillna("") != df["ip_country"].fillna(""))
                    & (df["merchant_country"].fillna("") != "")
                    & (df["ip_country"].fillna("") != "")
                ).astype(int)
            )
            cb_rate = cb.groupby("user_id")["is_cross_border"].mean().reset_index()
            cb_rate.columns = ["user_id", "cross_border_ratio"]
            user_features = user_features.merge(cb_rate, on="user_id", how="left")
        else:
            user_features["cross_border_ratio"] = 0.0

        # Unique merchant count per user (strong separating feature)
        if "merchant_id" in df.columns:
            n_merch = df.groupby("user_id")["merchant_id"].nunique().reset_index()
            n_merch.columns = ["user_id", "n_unique_merchants"]
            user_features = user_features.merge(n_merch, on="user_id", how="left")
        else:
            user_features["n_unique_merchants"] = 0.0

        # Unique BIN count per user (strong separating feature)
        if "card_bin" in df.columns:
            n_bins = df.groupby("user_id")["card_bin"].nunique().reset_index()
            n_bins.columns = ["user_id", "n_unique_bins"]
            user_features = user_features.merge(n_bins, on="user_id", how="left")
        else:
            user_features["n_unique_bins"] = 0.0

        # Fill remaining NaN with 0
        user_features = user_features.fillna(0.0)
        return user_features

    def compute_per_device_features(self) -> pd.DataFrame:
        """Compute per-device features."""
        df = self.df
        if "device_fingerprint" not in df.columns:
            return pd.DataFrame(columns=["device_fingerprint", "unique_user_count", "device_reuse_rate"])

        device_feats = df.groupby("device_fingerprint").agg(
            unique_user_count=("user_id", "nunique") if "user_id" in df.columns else ("device_fingerprint", "count"),
            total_txns=("device_fingerprint", "count"),
        ).reset_index()

        device_feats["device_reuse_rate"] = np.where(
            device_feats["total_txns"] > 0,
            device_feats["unique_user_count"] / device_feats["total_txns"],
            0.0,
        )
        return device_feats

    def compute_per_merchant_features(self) -> pd.DataFrame:
        """Compute per-merchant features."""
        df = self.df
        if "merchant_id" not in df.columns:
            return pd.DataFrame(columns=["merchant_id", "unique_user_count", "merchant_amount_mean", "merchant_amount_std"])

        agg_dict = {}
        if "user_id" in df.columns:
            agg_dict["unique_user_count"] = ("user_id", "nunique")
        else:
            agg_dict["unique_user_count"] = ("merchant_id", "count")

        merchant_feats = df.groupby("merchant_id").agg(**agg_dict).reset_index()

        if "amount" in df.columns:
            amount_stats = df.groupby("merchant_id")["amount"].agg(
                merchant_amount_mean="mean",
                merchant_amount_std="std",
            ).reset_index()
            amount_stats["merchant_amount_std"] = amount_stats["merchant_amount_std"].fillna(0.0)
            merchant_feats = merchant_feats.merge(amount_stats, on="merchant_id", how="left")
        else:
            merchant_feats["merchant_amount_mean"] = 0.0
            merchant_feats["merchant_amount_std"] = 0.0

        return merchant_feats

    def compute_per_ring_features(
        self,
        ring_candidates: List[RingCandidate],
        user_features: pd.DataFrame,
    ) -> List[RingFeatureVector]:
        """Aggregate member features per ring candidate."""
        result = []
        if user_features.empty:
            return result

        user_features_indexed = user_features.set_index("user_id") if "user_id" in user_features.columns else user_features

        for rc in ring_candidates:
            members_in_features = [
                uid for uid in rc.member_user_ids if uid in user_features_indexed.index
            ]
            if not members_in_features:
                rfv = RingFeatureVector(
                    ring_id=rc.ring_id,
                    size=rc.size,
                    density=rc.density,
                    shared_device_count=len(rc.shared_devices),
                    shared_ip_prefix_count=len(rc.shared_ip_prefixes),
                    shared_bin_count=len(rc.shared_bins),
                    shared_merchant_count=len(rc.shared_merchants),
                    shared_email_domain_count=len(rc.shared_email_domains),
                )
                result.append(rfv)
                continue

            member_df = user_features_indexed.loc[members_in_features]

            def _safe_mean(col_name):
                if col_name in member_df.columns:
                    return float(member_df[col_name].mean())
                return 0.0

            rfv = RingFeatureVector(
                ring_id=rc.ring_id,
                size=rc.size,
                density=rc.density,
                mean_micro_amount_ratio=_safe_mean("micro_amount_ratio"),
                mean_threshold_amount_ratio=_safe_mean("threshold_amount_ratio"),
                mean_merchant_hhi=_safe_mean("merchant_concentration_hhi"),
                mean_merchant_gini=_safe_mean("merchant_concentration_gini"),
                mean_bin_concentration=_safe_mean("bin_concentration"),
                mean_device_sharing=_safe_mean("device_sharing_score"),
                mean_subnet_sharing_24=_safe_mean("subnet_sharing_score_24"),
                mean_subnet_sharing_16=_safe_mean("subnet_sharing_score_16"),
                mean_geo_mismatch_rate=_safe_mean("geo_mismatch_rate"),
                mean_burstiness_cv=_safe_mean("burstiness_cv"),
                mean_burst_window_count=_safe_mean("burst_window_count"),
                mean_inter_arrival_sec=_safe_mean("mean_inter_arrival_sec"),
                mean_txn_count=_safe_mean("txn_count"),
                mean_amount_mean=_safe_mean("amount_mean"),
                mean_amount_std=_safe_mean("amount_std"),
                mean_amount_max=_safe_mean("amount_max"),
                shared_device_count=len(rc.shared_devices),
                shared_ip_prefix_count=len(rc.shared_ip_prefixes),
                shared_bin_count=len(rc.shared_bins),
                shared_merchant_count=len(rc.shared_merchants),
                shared_email_domain_count=len(rc.shared_email_domains),
            )
            result.append(rfv)
        return result

    def broadcast_user_features_to_transactions(
        self, user_features: pd.DataFrame
    ) -> pd.DataFrame:
        """Join user-level features back to transaction rows."""
        if user_features.empty or "user_id" not in self.df.columns:
            return self.df
        return self.df.merge(user_features, on="user_id", how="left", suffixes=("", "_user"))

    # ---- Private helpers ----

    @staticmethod
    def _compute_hhi(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
        """Herfindahl-Hirschman Index of value distribution per group."""
        filtered = df[[group_col, value_col]].dropna()
        if filtered.empty:
            return pd.DataFrame(columns=[group_col, "hhi"])

        counts = filtered.groupby([group_col, value_col]).size().reset_index(name="cnt")
        totals = counts.groupby(group_col)["cnt"].transform("sum")
        counts["share"] = counts["cnt"] / totals
        counts["share_sq"] = counts["share"] ** 2
        hhi = counts.groupby(group_col)["share_sq"].sum().reset_index()
        hhi.columns = [group_col, "hhi"]
        return hhi

    @staticmethod
    def _compute_gini(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
        """Gini coefficient of value distribution per group."""
        filtered = df[[group_col, value_col]].dropna()
        if filtered.empty:
            return pd.DataFrame(columns=[group_col, "gini"])

        counts = filtered.groupby([group_col, value_col]).size().reset_index(name="cnt")

        def _gini_for_group(group_counts):
            values = np.sort(group_counts.values.astype(float))
            n = len(values)
            if n == 0 or values.sum() == 0:
                return 0.0
            index = np.arange(1, n + 1)
            return float((2 * np.sum(index * values) - (n + 1) * np.sum(values)) / (n * np.sum(values)))

        gini_vals = counts.groupby(group_col)["cnt"].apply(_gini_for_group).reset_index()
        gini_vals.columns = [group_col, "gini"]
        return gini_vals

    @staticmethod
    def _compute_sharing_score(
        df: pd.DataFrame, user_col: str, resource_col: str
    ) -> pd.DataFrame:
        """Average number of OTHER users sharing this user's resources."""
        filtered = df[[user_col, resource_col]].dropna()
        filtered = filtered[filtered[resource_col].astype(str).str.strip() != ""]
        if filtered.empty:
            return pd.DataFrame(columns=[user_col, "sharing_score"])

        # Count unique users per resource
        resource_user_count = (
            filtered.groupby(resource_col)[user_col]
            .nunique()
            .reset_index(name="user_count")
        )

        # Join back to get count for each user-resource pair
        merged = filtered.drop_duplicates([user_col, resource_col]).merge(
            resource_user_count, on=resource_col, how="left"
        )
        # other users = total - 1
        merged["other_users"] = (merged["user_count"] - 1).clip(lower=0)

        # Average over all resources per user
        sharing = merged.groupby(user_col)["other_users"].mean().reset_index()
        sharing.columns = [user_col, "sharing_score"]
        return sharing

    def _compute_temporal_features(
        self, df: pd.DataFrame, user_features: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute burstiness_cv, burst_window_count, mean_inter_arrival_sec."""
        if "timestamp" not in df.columns and "transaction_date" not in df.columns:
            user_features["burstiness_cv"] = 0.0
            user_features["burst_window_count"] = 0
            user_features["mean_inter_arrival_sec"] = 0.0
            return user_features

        ts_col = "timestamp" if "timestamp" in df.columns else "transaction_date"
        temp = df[["user_id", ts_col]].copy()
        temp["_ts"] = pd.to_datetime(temp[ts_col], errors="coerce")
        temp = temp.dropna(subset=["_ts"]).sort_values(["user_id", "_ts"])

        # Inter-arrival times
        temp["_prev_ts"] = temp.groupby("user_id")["_ts"].shift(1)
        temp["_iat"] = (temp["_ts"] - temp["_prev_ts"]).dt.total_seconds()

        iat_stats = temp.dropna(subset=["_iat"]).groupby("user_id")["_iat"].agg(
            iat_mean="mean",
            iat_std="std",
        ).reset_index()
        iat_stats["iat_std"] = iat_stats["iat_std"].fillna(0.0)
        iat_stats["burstiness_cv"] = np.where(
            iat_stats["iat_mean"] > 0,
            iat_stats["iat_std"] / iat_stats["iat_mean"],
            0.0,
        )
        iat_stats["mean_inter_arrival_sec"] = iat_stats["iat_mean"].fillna(0.0)

        # Burst window count: number of 5-min windows with 3+ transactions
        temp["_window"] = temp["_ts"].dt.floor("5min")
        window_counts = temp.groupby(["user_id", "_window"]).size().reset_index(name="wcount")
        burst_windows = (
            window_counts[window_counts["wcount"] >= 3]
            .groupby("user_id")
            .size()
            .reset_index(name="burst_window_count")
        )

        user_features = user_features.merge(
            iat_stats[["user_id", "burstiness_cv", "mean_inter_arrival_sec"]],
            on="user_id",
            how="left",
        )
        user_features = user_features.merge(
            burst_windows, on="user_id", how="left"
        )
        user_features["burstiness_cv"] = user_features["burstiness_cv"].fillna(0.0)
        user_features["mean_inter_arrival_sec"] = user_features["mean_inter_arrival_sec"].fillna(0.0)
        user_features["burst_window_count"] = user_features["burst_window_count"].fillna(0).astype(int)

        return user_features
