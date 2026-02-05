"""
End-to-end evaluation runner for the two-phase detection pipeline (v2).

Loads the synthetic 120K dataset, runs the detection pipeline,
evaluates against ground truth, and produces reporting artifacts
+ a markdown summary report.
"""

import sys
import os
import json
import time
import pandas as pd
import numpy as np
from dataclasses import asdict
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.analytics.ring_detection.pipeline import RingDetectionPipeline, _convert_for_json
from app.services.analytics.ring_detection.evaluation import (
    RingDetectionEvaluator,
    load_ground_truth_from_csv,
)


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    tx_path = os.path.join(data_dir, "fraud_rings_synthetic_transactions.csv")
    gt_path = os.path.join(data_dir, "fraud_rings_synthetic_ground_truth.csv")
    out_dir = os.path.join(os.path.dirname(__file__), "out_eval")
    os.makedirs(out_dir, exist_ok=True)

    # --- 1. Load data ---
    print("=" * 70)
    print("FRAUD RING DETECTION v2 - TWO-PHASE EVALUATION RUN")
    print("=" * 70)
    print(f"\n[1/6] Loading data from {tx_path}...")
    df = pd.read_csv(tx_path)
    print(f"  Loaded {len(df)} transactions, {df['user_id'].nunique()} unique users")

    # --- 2. Load ground truth ---
    print(f"\n[2/6] Loading ground truth from {gt_path}...")
    ground_truth = load_ground_truth_from_csv(gt_path)
    gt_rings = ground_truth["rings"]
    print(f"  {len(gt_rings)} ground-truth rings (excluding SINGLETON)")
    for gtr in gt_rings:
        print(f"    {gtr['ring_id']} ({gtr['ring_type']}): {len(gtr['members'])} users")

    # --- 3. Run pipeline ---
    print(f"\n[3/6] Running two-phase detection pipeline...")
    t0 = time.time()
    pipeline = RingDetectionPipeline(
        confidence_threshold=0.45,
        enable_behavioral_clustering=True,
        enable_temporal_analysis=True,
        min_evidence_types=2,
    )
    result = pipeline.run(df, return_transaction_scores=False)
    elapsed = time.time() - t0
    print(f"\n  Pipeline completed in {elapsed:.1f}s")
    print(f"  Detected {result.total_rings_detected} rings")
    print(f"  Risk level: {result.overall_risk_level}")
    print(f"  Phase 1 candidates: {result.phase1_candidate_count}")
    print(f"  Phase 2 confirmed: {result.phase2_confirmed_count}")

    # Print ring summary
    all_members = set()
    for r in result.rings:
        all_members.update(r.members)
        evidence_types = r.evidence.get("evidence_types", [])
        print(f"    {r.ring_id}: {r.ring_label} ({r.member_count} members, "
              f"conf={r.confidence:.3f}, sev={r.severity}, "
              f"evidence={evidence_types})")
    print(f"  Total unique flagged accounts: {len(all_members)}")

    # --- 4. Diagnostics ---
    print(f"\n[4/6] Self-diagnostics...")
    if result.diagnostics:
        diag = result.diagnostics
        print(f"  Health: {'HEALTHY' if diag.is_healthy else 'ISSUES DETECTED'}")
        print(f"  Checks passed: {diag.checks_passed}, failed: {diag.checks_failed}")
        for w in diag.warnings:
            print(f"  WARNING: {w}")
        for e in diag.errors:
            print(f"  ERROR: {e}")
        if diag.metrics:
            print(f"  Metrics: {json.dumps(diag.metrics, indent=4, default=str)}")
    else:
        print("  No diagnostics available")

    # --- 5. Evaluate ---
    print(f"\n[5/6] Evaluating against ground truth...")
    evaluator = RingDetectionEvaluator()
    eval_results = evaluator.evaluate_ring_discovery(
        result.rings, gt_rings, jaccard_threshold=0.005
    )

    # Ring-level metrics
    rl = eval_results["ring_level"]
    print(f"\n  RING-LEVEL METRICS:")
    print(f"    Precision: {rl['precision']:.4f}")
    print(f"    Recall:    {rl['recall']:.4f}")
    print(f"    F1:        {rl['f1']:.4f}")
    print(f"    Matched pred:  {rl['matched_pred']}/{rl['predicted_count']}")
    print(f"    Recalled GT:   {rl['recalled_gt']}/{rl['ground_truth_count']}")

    # Account-level metrics
    al = eval_results["account_level"]
    print(f"\n  ACCOUNT-LEVEL METRICS:")
    print(f"    Precision: {al['precision']:.4f}")
    print(f"    Recall:    {al['recall']:.4f}")
    print(f"    F1:        {al['f1']:.4f}")
    print(f"    TP: {al['true_positives']}, FP: {al['false_positives']}, FN: {al['false_negatives']}")

    # By-type confusion
    print(f"\n  BY RING TYPE:")
    for rtype, info in eval_results["by_type"].items():
        print(f"    {rtype}: {info['recalled']}/{info['gt_count']} recalled "
              f"(recall={info['recall']:.4f})")

    # Match details
    print(f"\n  MATCH DETAILS:")
    for md in eval_results["match_details"]:
        status = "MATCH" if md["is_match"] else "NO MATCH"
        gt_info = f"-> {md['best_gt_ring_id']} ({md['best_gt_type']})" if md["best_gt_ring_id"] else "-> none"
        print(f"    {md['predicted_ring_id']} ({md['predicted_label']}, "
              f"size={md['predicted_size']}): J={md['best_jaccard']:.4f} {gt_info} [{status}]")

    # Detection funnel
    print(f"\n  DETECTION FUNNEL:")
    print(f"    Phase 1 candidates: {result.phase1_candidate_count}")
    print(f"    Phase 2 confirmed:  {result.phase2_confirmed_count}")
    if result.phase1_candidate_count > 0:
        rate = result.phase2_confirmed_count / result.phase1_candidate_count
        print(f"    Confirmation rate:  {rate:.1%}")

    # Confirmation log
    if pipeline.merge_log:
        print(f"\n  CONFIRMATION LOG ({len(pipeline.merge_log)} entries):")
        for entry in pipeline.merge_log[:10]:
            print(f"    {entry}")

    # --- 6. Generate artifacts ---
    print(f"\n[6/6] Generating reporting artifacts to {out_dir}...")
    artifact_results = evaluator.generate_reporting_artifacts(
        result, out_dir,
        evaluation_results=eval_results,
        merge_log=pipeline.merge_log,
    )
    print(f"  flagged_accounts.json: {artifact_results['flagged_accounts_count']} accounts")
    print(f"  report_math_checks.json: consistency_ok={artifact_results['consistency_ok']}")

    # Save evaluation results
    eval_path = os.path.join(out_dir, "evaluation_results.json")
    with open(eval_path, "w") as f:
        json.dump(eval_results, f, indent=2, default=str)

    # Save rings output
    result_dict = _convert_for_json(asdict(result))
    rings_output = {k: v for k, v in result_dict.items() if k != "transaction_scores"}
    rings_path = os.path.join(out_dir, "rings.json")
    with open(rings_path, "w") as f:
        json.dump(rings_output, f, indent=2, default=str)

    # Save diagnostics
    if result.diagnostics:
        diag_path = os.path.join(out_dir, "diagnostics.json")
        diag_dict = _convert_for_json(asdict(result.diagnostics))
        with open(diag_path, "w") as f:
            json.dump(diag_dict, f, indent=2, default=str)

    # Generate markdown report
    report = generate_markdown_report(result, eval_results, artifact_results, elapsed, pipeline)
    report_path = os.path.join(out_dir, "evaluation_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n{'=' * 70}")
    print(f"EVALUATION COMPLETE - all artifacts in {out_dir}/")
    print(f"{'=' * 70}")


def generate_markdown_report(result, eval_results, artifact_results, elapsed, pipeline):
    """Generate a concise markdown evaluation report."""
    lines = []
    lines.append("# Fraud Ring Detection v2 - Evaluation Report")
    lines.append(f"\nGenerated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"Pipeline runtime: {elapsed:.1f}s")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- **Detected rings:** {result.total_rings_detected}")
    all_members = set()
    for r in result.rings:
        all_members.update(r.members)
    lines.append(f"- **Unique flagged accounts:** {len(all_members)}")
    lines.append(f"- **Ground truth rings:** {eval_results['ring_level']['ground_truth_count']}")
    lines.append(f"- **Overall risk level:** {result.overall_risk_level}")
    lines.append(f"- **Phase 1 candidates:** {result.phase1_candidate_count}")
    lines.append(f"- **Phase 2 confirmed:** {result.phase2_confirmed_count}")
    if result.phase1_candidate_count > 0:
        lines.append(f"- **Confirmation rate:** {result.phase2_confirmed_count / result.phase1_candidate_count:.1%}")
    lines.append("")

    # Detection funnel
    lines.append("## Detection Funnel")
    lines.append(f"1. Phase 1 Discovery: {result.phase1_candidate_count} candidate clusters")
    lines.append(f"2. Phase 2 Confirmation: {result.phase2_confirmed_count} confirmed rings")
    lines.append(f"3. Final output: {result.total_rings_detected} classified rings")
    lines.append("")

    # Diagnostics
    if result.diagnostics:
        lines.append("## Self-Diagnostics")
        diag = result.diagnostics
        lines.append(f"- Health: **{'HEALTHY' if diag.is_healthy else 'ISSUES DETECTED'}**")
        lines.append(f"- Checks passed: {diag.checks_passed}, failed: {diag.checks_failed}")
        if diag.warnings:
            for w in diag.warnings:
                lines.append(f"- WARNING: {w}")
        if diag.errors:
            for e in diag.errors:
                lines.append(f"- ERROR: {e}")
        if diag.metrics:
            for k, v in diag.metrics.items():
                lines.append(f"- {k}: {v}")
        lines.append("")

    # Ring-level metrics
    rl = eval_results["ring_level"]
    lines.append("## Ring-Level Metrics")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Precision | {rl['precision']:.4f} |")
    lines.append(f"| Recall | {rl['recall']:.4f} |")
    lines.append(f"| F1 | {rl['f1']:.4f} |")
    lines.append(f"| Matched predictions | {rl['matched_pred']}/{rl['predicted_count']} |")
    lines.append(f"| Recalled GT rings | {rl['recalled_gt']}/{rl['ground_truth_count']} |")
    lines.append("")

    # Account-level metrics
    al = eval_results["account_level"]
    lines.append("## Account-Level Metrics")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Precision | {al['precision']:.4f} |")
    lines.append(f"| Recall | {al['recall']:.4f} |")
    lines.append(f"| F1 | {al['f1']:.4f} |")
    lines.append(f"| True Positives | {al['true_positives']} |")
    lines.append(f"| False Positives | {al['false_positives']} |")
    lines.append(f"| False Negatives | {al['false_negatives']} |")
    lines.append("")

    # By type
    lines.append("## Detection by Ring Type")
    lines.append("| Ring Type | GT Count | Recalled | Recall |")
    lines.append("|-----------|----------|----------|--------|")
    for rtype, info in eval_results["by_type"].items():
        lines.append(f"| {rtype} | {info['gt_count']} | {info['recalled']} | {info['recall']:.4f} |")
    lines.append("")

    # Detected rings table
    lines.append("## Detected Rings")
    lines.append("| Ring ID | Label | Size | Confidence | Severity | Best GT Match | Jaccard |")
    lines.append("|---------|-------|------|------------|----------|---------------|---------|")
    for md in eval_results["match_details"]:
        gt_match = md.get("best_gt_ring_id", "-") or "-"
        sev = "-"
        for r in result.rings:
            if r.ring_id == md["predicted_ring_id"]:
                sev = r.severity
                break
        lines.append(
            f"| {md['predicted_ring_id']} | {md['predicted_label']} | "
            f"{md['predicted_size']} | {md['best_jaccard']:.4f} | {sev} | "
            f"{gt_match} | {md['best_jaccard']:.4f} |"
        )
    lines.append("")

    # Confirmation log
    if pipeline.merge_log:
        lines.append("## Confirmation Log")
        lines.append(f"Total entries: {len(pipeline.merge_log)}")
        for entry in pipeline.merge_log[:20]:
            lines.append(f"- {entry}")
        lines.append("")

    # Consistency checks
    lines.append("## Consistency Checks")
    lines.append(f"- Members == Flagged: {artifact_results['unique_ring_members']} == {artifact_results['flagged_accounts_count']}")
    lines.append(f"- Consistency OK: {artifact_results['consistency_ok']}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
