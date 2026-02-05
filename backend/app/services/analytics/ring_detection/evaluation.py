"""
Evaluation module for fraud ring detection.

Provides:
- Ring-level precision/recall/F1 using Jaccard overlap matching
- Account-level precision/recall/F1
- Per-ring-type confusion table
- ROC-AUC/PR-AUC for transaction scoring
- Self-consistency metrics
- Reporting artifacts (flagged_accounts.json, report_math_checks.json)
"""

import numpy as np
import pandas as pd
import json
import os
import argparse
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict

from .schemas import (
    PipelineOutput, TransactionScore, ClassifiedRing,
    ConfirmedRing, MembershipRole,
)


class RingDetectionEvaluator:
    """Evaluates ring detection and transaction scoring quality."""

    def evaluate_ring_discovery(
        self,
        predicted_rings: List[ClassifiedRing],
        ground_truth_rings: List[Dict[str, Any]],
        jaccard_threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Ring-level and account-level precision/recall using best Jaccard match.

        For each predicted ring, find the ground-truth ring with max Jaccard.
        A predicted ring counts as a true positive if its best Jaccard >= threshold.
        A GT ring counts as recalled if at least one predicted ring matches it.

        ground_truth_rings: list of dicts with keys:
            'ring_id', 'ring_type', 'members' (list of user_ids)
        """
        empty_result = {
            "ring_level": {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                           "matched": 0, "predicted": 0, "ground_truth": 0},
            "account_level": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
            "match_details": [],
            "by_type": {},
        }

        if not predicted_rings and not ground_truth_rings:
            return empty_result
        if not predicted_rings:
            empty_result["ring_level"]["ground_truth"] = len(ground_truth_rings)
            return empty_result
        if not ground_truth_rings:
            empty_result["ring_level"]["predicted"] = len(predicted_rings)
            return empty_result

        pred_sets = [set(r.members) for r in predicted_rings]
        gt_sets = [set(r["members"]) for r in ground_truth_rings]
        gt_ids = [r["ring_id"] for r in ground_truth_rings]
        gt_types = [r.get("ring_type", "unknown") for r in ground_truth_rings]

        # For each predicted ring, compute best matching GT ring
        match_details = []
        pred_best_gt = {}   # pred_idx -> (gt_idx, jaccard)

        for i, ps in enumerate(pred_sets):
            best_j, best_jaccard = -1, 0.0
            for j, gs in enumerate(gt_sets):
                intersection = len(ps & gs)
                union_size = len(ps | gs)
                if union_size == 0:
                    continue
                jaccard = intersection / union_size
                if jaccard > best_jaccard:
                    best_jaccard = jaccard
                    best_j = j

            detail = {
                "predicted_ring_id": predicted_rings[i].ring_id,
                "predicted_label": predicted_rings[i].ring_label,
                "predicted_size": predicted_rings[i].member_count,
                "best_gt_ring_id": gt_ids[best_j] if best_j >= 0 else None,
                "best_gt_type": gt_types[best_j] if best_j >= 0 else None,
                "best_jaccard": round(best_jaccard, 4),
                "is_match": best_jaccard >= jaccard_threshold,
            }

            if best_j >= 0 and best_jaccard >= jaccard_threshold:
                overlap = pred_sets[i] & gt_sets[best_j]
                detail["overlap_size"] = len(overlap)
                detail["gt_size"] = len(gt_sets[best_j])
                detail["recall_of_gt"] = round(len(overlap) / len(gt_sets[best_j]), 4) if gt_sets[best_j] else 0
                detail["precision_of_pred"] = round(len(overlap) / len(pred_sets[i]), 4) if pred_sets[i] else 0
                pred_best_gt[i] = (best_j, best_jaccard)

            match_details.append(detail)

        # Ring-level metrics
        # A GT ring is "recalled" if at least one pred ring matched it
        recalled_gt = set()
        for gt_idx, _ in pred_best_gt.values():
            recalled_gt.add(gt_idx)

        matched_pred = set(pred_best_gt.keys())
        ring_precision = len(matched_pred) / len(pred_sets) if pred_sets else 0.0
        ring_recall = len(recalled_gt) / len(gt_sets) if gt_sets else 0.0
        ring_f1 = (2 * ring_precision * ring_recall / (ring_precision + ring_recall)
                   if (ring_precision + ring_recall) > 0 else 0.0)

        # Account-level metrics
        all_pred_members = set()
        for ps in pred_sets:
            all_pred_members.update(ps)

        all_gt_members = set()
        for gs in gt_sets:
            all_gt_members.update(gs)

        tp_accounts = all_pred_members & all_gt_members
        fp_accounts = all_pred_members - all_gt_members
        fn_accounts = all_gt_members - all_pred_members

        acct_precision = len(tp_accounts) / len(all_pred_members) if all_pred_members else 0.0
        acct_recall = len(tp_accounts) / len(all_gt_members) if all_gt_members else 0.0
        acct_f1 = (2 * acct_precision * acct_recall / (acct_precision + acct_recall)
                   if (acct_precision + acct_recall) > 0 else 0.0)

        # Per-ring-type confusion table
        by_type = self._confusion_by_ring_type(
            predicted_rings, pred_best_gt, ground_truth_rings, recalled_gt
        )

        return {
            "ring_level": {
                "precision": round(ring_precision, 4),
                "recall": round(ring_recall, 4),
                "f1": round(ring_f1, 4),
                "matched_pred": len(matched_pred),
                "predicted_count": len(predicted_rings),
                "recalled_gt": len(recalled_gt),
                "ground_truth_count": len(ground_truth_rings),
            },
            "account_level": {
                "precision": round(acct_precision, 4),
                "recall": round(acct_recall, 4),
                "f1": round(acct_f1, 4),
                "true_positives": len(tp_accounts),
                "false_positives": len(fp_accounts),
                "false_negatives": len(fn_accounts),
                "total_predicted_accounts": len(all_pred_members),
                "total_gt_accounts": len(all_gt_members),
            },
            "match_details": match_details,
            "by_type": by_type,
        }

    def _confusion_by_ring_type(
        self,
        predicted_rings: List[ClassifiedRing],
        pred_best_gt: Dict[int, Tuple[int, float]],
        ground_truth_rings: List[Dict[str, Any]],
        recalled_gt: Set[int],
    ) -> Dict[str, Any]:
        """Build confusion table grouped by ring_type."""
        # Group GT rings by type
        gt_by_type: Dict[str, List[int]] = defaultdict(list)
        for j, gtr in enumerate(ground_truth_rings):
            gt_by_type[gtr.get("ring_type", "unknown")].append(j)

        result = {}
        for rtype, gt_indices in gt_by_type.items():
            n_gt = len(gt_indices)
            n_recalled = sum(1 for j in gt_indices if j in recalled_gt)

            # Which predicted rings matched this type?
            matched_preds = []
            for pi, (gj, jacc) in pred_best_gt.items():
                if gj in gt_indices:
                    matched_preds.append({
                        "pred_ring_id": predicted_rings[pi].ring_id,
                        "pred_label": predicted_rings[pi].ring_label,
                        "pred_size": predicted_rings[pi].member_count,
                        "gt_ring_id": ground_truth_rings[gj]["ring_id"],
                        "jaccard": round(jacc, 4),
                    })

            result[rtype] = {
                "gt_count": n_gt,
                "recalled": n_recalled,
                "recall": round(n_recalled / n_gt, 4) if n_gt > 0 else 0.0,
                "matched_predictions": matched_preds,
            }

        return result

    def evaluate_by_membership_role(
        self,
        confirmed_rings: List[ConfirmedRing],
        ground_truth_rings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate precision/recall stratified by membership role."""
        all_gt_members = set()
        for gtr in ground_truth_rings:
            all_gt_members.update(gtr["members"])

        role_stats = {}
        for role in MembershipRole:
            role_members = set()
            for ring in confirmed_rings:
                for me in ring.members:
                    if me.role == role.value and not me.is_trimmed:
                        role_members.add(me.user_id)

            tp = len(role_members & all_gt_members)
            fp = len(role_members - all_gt_members)
            precision = tp / max(len(role_members), 1)
            recall_contribution = tp / max(len(all_gt_members), 1)

            role_stats[role.value] = {
                "count": len(role_members),
                "true_positives": tp,
                "false_positives": fp,
                "precision": round(precision, 4),
                "recall_contribution": round(recall_contribution, 4),
            }

        return role_stats

    def evaluate_discovery_methods(
        self,
        confirmed_rings: List[ConfirmedRing],
        ground_truth_rings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate which discovery methods contributed most to recall."""
        all_gt_members = set()
        for gtr in ground_truth_rings:
            all_gt_members.update(gtr["members"])

        method_stats: Dict[str, Dict] = defaultdict(
            lambda: {"rings": 0, "members": set()}
        )
        for ring in confirmed_rings:
            for method in ring.discovery_methods:
                method_stats[method]["rings"] += 1
                for me in ring.members:
                    if not me.is_trimmed:
                        method_stats[method]["members"].add(me.user_id)

        result = {}
        for method, stats in method_stats.items():
            tp = len(stats["members"] & all_gt_members)
            result[method] = {
                "rings_contributed": stats["rings"],
                "unique_members": len(stats["members"]),
                "true_positives": tp,
                "precision": round(tp / max(len(stats["members"]), 1), 4),
            }
        return result

    def evaluate_transaction_scoring(
        self,
        scores: List[TransactionScore],
        ground_truth_labels: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        ROC-AUC, PR-AUC for transaction-level scoring.
        ground_truth_labels: dict mapping transaction_id -> 0 (legit) or 1 (fraud).
        """
        if not scores or not ground_truth_labels:
            return {"roc_auc": None, "pr_auc": None, "n_scored": len(scores)}

        y_true = []
        y_score = []
        for s in scores:
            if s.transaction_id in ground_truth_labels:
                y_true.append(ground_truth_labels[s.transaction_id])
                y_score.append(s.risk_score / 100.0)

        if len(y_true) < 2 or len(set(y_true)) < 2:
            return {"roc_auc": None, "pr_auc": None, "n_scored": len(y_true)}

        try:
            from sklearn.metrics import roc_auc_score, average_precision_score

            roc = roc_auc_score(y_true, y_score)
            pr = average_precision_score(y_true, y_score)
            return {
                "roc_auc": round(float(roc), 4),
                "pr_auc": round(float(pr), 4),
                "n_scored": len(y_true),
            }
        except Exception:
            return {"roc_auc": None, "pr_auc": None, "n_scored": len(y_true)}

    def confusion_matrix(
        self,
        scores: List[TransactionScore],
        ground_truth_labels: Dict[str, int],
        threshold: float = 50.0,
    ) -> Dict[str, Any]:
        """Full confusion matrix at given risk score threshold."""
        if not scores or not ground_truth_labels:
            return {"tp": 0, "fp": 0, "tn": 0, "fn": 0}

        tp = fp = tn = fn = 0
        for s in scores:
            if s.transaction_id not in ground_truth_labels:
                continue
            actual = ground_truth_labels[s.transaction_id]
            predicted = 1 if s.risk_score >= threshold else 0

            if actual == 1 and predicted == 1:
                tp += 1
            elif actual == 0 and predicted == 1:
                fp += 1
            elif actual == 0 and predicted == 0:
                tn += 1
            elif actual == 1 and predicted == 0:
                fn += 1

        return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}

    def generate_reporting_artifacts(
        self,
        pipeline_output: PipelineOutput,
        output_dir: str,
        evaluation_results: Optional[Dict[str, Any]] = None,
        merge_log: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate reporting artifacts:
        1. flagged_accounts.json - per-user reasons
        2. report_math_checks.json - consistency checks
        """
        os.makedirs(output_dir, exist_ok=True)
        rings = pipeline_output.rings

        # --- flagged_accounts.json ---
        all_ring_members: Set[str] = set()
        user_ring_info: Dict[str, List[Dict]] = defaultdict(list)
        for ring in rings:
            for member in ring.members:
                all_ring_members.add(member)
                user_ring_info[member].append({
                    "ring_id": ring.ring_id,
                    "ring_label": ring.ring_label,
                    "ring_confidence": ring.confidence,
                    "ring_risk_score": ring.risk_score,
                    "ring_severity": ring.severity,
                })

        flagged_accounts = {}
        for uid in sorted(all_ring_members):
            rings_for_user = user_ring_info[uid]
            max_confidence = max(r["ring_confidence"] for r in rings_for_user)
            max_risk = max(r["ring_risk_score"] for r in rings_for_user)
            worst_severity = "LOW"
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if any(r["ring_severity"] == sev for r in rings_for_user):
                    worst_severity = sev
                    break

            flagged_accounts[uid] = {
                "max_ring_confidence": round(max_confidence, 4),
                "max_risk_score": round(max_risk, 4),
                "worst_severity": worst_severity,
                "ring_memberships": rings_for_user,
                "active_signals": [],  # filled below if tx scores available
            }

        # Enrich with transaction score info
        if pipeline_output.transaction_scores:
            user_scores: Dict[str, List[float]] = defaultdict(list)
            for ts in pipeline_output.transaction_scores:
                if ts.user_id in all_ring_members:
                    user_scores[ts.user_id].append(ts.risk_score)
            for uid in flagged_accounts:
                scores = user_scores.get(uid, [])
                if scores:
                    flagged_accounts[uid]["mean_tx_risk_score"] = round(float(np.mean(scores)), 2)
                    flagged_accounts[uid]["max_tx_risk_score"] = round(float(max(scores)), 2)

        flagged_path = os.path.join(output_dir, "flagged_accounts.json")
        with open(flagged_path, "w") as f:
            json.dump(flagged_accounts, f, indent=2, default=str)

        # --- report_math_checks.json ---
        unique_ring_members = len(all_ring_members)

        # Severity distribution
        severity_dist = Counter(r.severity for r in rings)
        label_dist = Counter(r.ring_label for r in rings)
        size_dist = [r.member_count for r in rings]

        math_checks = {
            "unique_ring_members": unique_ring_members,
            "flagged_accounts_count": len(flagged_accounts),
            "total_rings": len(rings),
            "severity_distribution": dict(severity_dist),
            "label_distribution": dict(label_dist),
            "ring_sizes": {
                "min": min(size_dist) if size_dist else 0,
                "max": max(size_dist) if size_dist else 0,
                "mean": round(float(np.mean(size_dist)), 1) if size_dist else 0,
                "median": round(float(np.median(size_dist)), 1) if size_dist else 0,
            },
            "members_equals_flagged": unique_ring_members == len(flagged_accounts),
        }

        if merge_log:
            math_checks["merge_log"] = merge_log

        if evaluation_results:
            math_checks["evaluation"] = evaluation_results

        # Consistency check
        consistency_ok = True
        issues = []

        if unique_ring_members != len(flagged_accounts):
            consistency_ok = False
            issues.append(
                f"unique_ring_members ({unique_ring_members}) != "
                f"flagged_accounts ({len(flagged_accounts)})"
            )

        reported_total = pipeline_output.total_rings_detected
        actual_total = len(rings)
        if reported_total != actual_total:
            consistency_ok = False
            issues.append(
                f"reported total_rings_detected ({reported_total}) != "
                f"actual ring count ({actual_total})"
            )

        math_checks["consistency_ok"] = consistency_ok
        math_checks["consistency_issues"] = issues

        checks_path = os.path.join(output_dir, "report_math_checks.json")
        with open(checks_path, "w") as f:
            json.dump(math_checks, f, indent=2, default=str)

        return {
            "flagged_accounts_path": flagged_path,
            "math_checks_path": checks_path,
            "unique_ring_members": unique_ring_members,
            "flagged_accounts_count": len(flagged_accounts),
            "consistency_ok": consistency_ok,
        }

    def run_full_evaluation(
        self,
        pipeline_output: PipelineOutput,
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run both ring and transaction evaluation if ground truth available.
        Otherwise reports self-consistency metrics.
        """
        result = {}

        # Self-consistency metrics (always available)
        result["self_consistency"] = self._self_consistency_metrics(pipeline_output)

        if ground_truth:
            # Ring-level evaluation
            if "rings" in ground_truth:
                result["ring_discovery"] = self.evaluate_ring_discovery(
                    pipeline_output.rings, ground_truth["rings"]
                )

            # Transaction-level evaluation
            if "transaction_labels" in ground_truth:
                result["transaction_scoring"] = self.evaluate_transaction_scoring(
                    pipeline_output.transaction_scores,
                    ground_truth["transaction_labels"],
                )
                result["confusion_matrix"] = self.confusion_matrix(
                    pipeline_output.transaction_scores,
                    ground_truth["transaction_labels"],
                )

        return result

    def _self_consistency_metrics(
        self, output: PipelineOutput
    ) -> Dict[str, Any]:
        """Report confidence distribution, label distribution, ring overlap."""
        label_counts = Counter(r.ring_label for r in output.rings)

        confidences = [r.confidence for r in output.rings]
        conf_stats = {}
        if confidences:
            conf_stats = {
                "mean": round(float(np.mean(confidences)), 3),
                "std": round(float(np.std(confidences)), 3),
                "min": round(float(np.min(confidences)), 3),
                "max": round(float(np.max(confidences)), 3),
            }

        all_members = []
        for r in output.rings:
            all_members.extend(r.members)
        member_counts = Counter(all_members)
        overlap_users = [u for u, c in member_counts.items() if c > 1]

        score_stats = {}
        if output.transaction_scores:
            risk_scores = [s.risk_score for s in output.transaction_scores]
            score_stats = {
                "mean": round(float(np.mean(risk_scores)), 2),
                "std": round(float(np.std(risk_scores)), 2),
                "min": round(float(np.min(risk_scores)), 2),
                "max": round(float(np.max(risk_scores)), 2),
                "pct_above_50": round(
                    float(np.mean(np.array(risk_scores) > 50)) * 100, 1
                ),
            }
            tx_label_counts = Counter(s.label for s in output.transaction_scores)
            score_stats["label_distribution"] = dict(tx_label_counts)

        return {
            "ring_label_distribution": dict(label_counts),
            "confidence_stats": conf_stats,
            "overlap_users": len(overlap_users),
            "total_unique_members": len(set(all_members)),
            "transaction_score_stats": score_stats,
        }


def load_ground_truth_from_csv(gt_csv_path: str) -> Dict[str, Any]:
    """
    Load ground truth from the synthetic CSV format:
      tx_id, user_id, is_fraud, ring_id, ring_type

    Returns dict with:
      'rings': list of {'ring_id', 'ring_type', 'members'} (excluding SINGLETON/empty)
      'transaction_labels': dict of tx_id -> 0/1
    """
    gt_df = pd.read_csv(gt_csv_path)

    # Build ring member sets (exclude SINGLETON and empty ring_ids)
    ring_members: Dict[str, Set[str]] = defaultdict(set)
    ring_types: Dict[str, str] = {}

    for _, row in gt_df.iterrows():
        rid = row.get("ring_id")
        if pd.isna(rid) or str(rid).strip() == "" or str(rid) == "SINGLETON":
            continue
        rid = str(rid).strip()
        uid = str(row["user_id"]).strip()
        ring_members[rid].add(uid)
        if rid not in ring_types:
            ring_types[rid] = str(row.get("ring_type", "unknown")).strip()

    rings = []
    for rid in sorted(ring_members.keys()):
        rings.append({
            "ring_id": rid,
            "ring_type": ring_types.get(rid, "unknown"),
            "members": sorted(ring_members[rid]),
        })

    # Transaction labels
    tx_labels = {}
    for _, row in gt_df.iterrows():
        tx_id = str(row.get("tx_id", row.get("transaction_id", ""))).strip()
        is_fraud = int(row.get("is_fraud", 0))
        tx_labels[tx_id] = is_fraud

    return {
        "rings": rings,
        "transaction_labels": tx_labels,
    }


def main():
    """CLI entry point for evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate ring detection results")
    parser.add_argument("--predictions", required=True, help="Path to rings.json")
    parser.add_argument("--ground-truth", default=None, help="Path to ground truth CSV or JSON")
    args = parser.parse_args()

    with open(args.predictions) as f:
        pred_data = json.load(f)

    from .schemas import ClassifiedRing, TransactionScore

    rings = []
    for r in pred_data.get("rings", []):
        rings.append(ClassifiedRing(**{
            k: v for k, v in r.items()
            if k in ClassifiedRing.__dataclass_fields__
        }))

    output = PipelineOutput(
        total_rings_detected=pred_data.get("total_rings_detected", 0),
        critical_count=pred_data.get("critical_count", 0),
        high_count=pred_data.get("high_count", 0),
        medium_count=pred_data.get("medium_count", 0),
        rings=rings,
        overall_risk_level=pred_data.get("overall_risk_level", "LOW"),
        executive_summary=pred_data.get("executive_summary", ""),
        detection_timestamp=pred_data.get("detection_timestamp", ""),
    )

    ground_truth = None
    if args.ground_truth:
        if args.ground_truth.endswith(".csv"):
            ground_truth = load_ground_truth_from_csv(args.ground_truth)
        else:
            with open(args.ground_truth) as f:
                ground_truth = json.load(f)

    evaluator = RingDetectionEvaluator()
    results = evaluator.run_full_evaluation(output, ground_truth)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
