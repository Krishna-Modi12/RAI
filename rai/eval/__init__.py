"""Evaluation harness, leakage guards, metrics, and generalization splits."""

from rai.eval.care import (
    ExternalCAREBenchmarkSpec,
    TwoTrackBenchmarkSummary,
    get_two_track_summary,
)
from rai.eval.leakage import DataLeakageError, assert_no_leakage, audit_split
from rai.eval.metrics import (
    AlertFatigueFunnel,
    CAREComponents,
    compute_abstention_metrics,
    compute_alert_fatigue_funnel,
    compute_calibration_report,
    compute_care_score,
    compute_classification_battery,
    compute_latency_summary,
)
from rai.eval.splits import (
    PartitionSplit,
    generate_ood_challenge_factors,
    split_asset_holdout,
    split_site_holdout,
    split_temporal,
)

__all__ = [
    "AlertFatigueFunnel",
    "CAREComponents",
    "DataLeakageError",
    "ExternalCAREBenchmarkSpec",
    "PartitionSplit",
    "TwoTrackBenchmarkSummary",
    "assert_no_leakage",
    "audit_split",
    "compute_abstention_metrics",
    "compute_alert_fatigue_funnel",
    "compute_calibration_report",
    "compute_care_score",
    "compute_classification_battery",
    "compute_latency_summary",
    "generate_ood_challenge_factors",
    "get_two_track_summary",
    "split_asset_holdout",
    "split_site_holdout",
    "split_temporal",
]

