"""Unit and integrity tests for Gate 3B-0 Multi-View Aggregation & Benchmark Interpretation."""

from __future__ import annotations

from pathlib import Path

import pytest

from rai.eval.gate3b0_aggregation import compute_multiview_aggregations


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    out = tmp_path / "gate3b0_test"
    out.mkdir()
    return out


def test_zero_positive_fold_handling(temp_output_dir: Path) -> None:
    """Ensure Fold 1 (0 events) returns None for PR-AUC rather than being coerced to 0.0."""
    result = compute_multiview_aggregations(temp_output_dir)
    folds = result["folds"]

    fold_1 = next(f for f in folds if f["fold_id"] == 1)
    assert fold_1["positive_events"] == 0
    assert fold_1["pr_auc"] is None
    assert fold_1["mcc"] is None
    assert fold_1["status"] == "NO_POSITIVE_EVENTS"
    assert "NO_POSITIVE_EVENTS" in fold_1["reason"] or "undefined" in fold_1["reason"]


def test_view_a_macro_valid_fold_average(temp_output_dir: Path) -> None:
    """Ensure View A averages only over valid folds with positive events (Folds 2, 3, 4)."""
    result = compute_multiview_aggregations(temp_output_dir)
    summary = result["summary"]

    assert summary["valid_fold_count"] == 3
    assert summary["total_fold_count"] == 4
    # Expected: (0.0833 + 0.2619 + 0.8306) / 3 = 0.3919
    assert pytest.approx(summary["macro_valid_prauc_mean"], abs=1e-3) == 0.3919
    assert pytest.approx(summary["macro_valid_prauc_std"], abs=1e-3) == 0.3188
    # Prior naive mean should be 0.2939
    assert pytest.approx(summary["naive_all_fold_prauc_mean"], abs=1e-3) == 0.2939


def test_view_b_micro_pooled_prauc(temp_output_dir: Path) -> None:
    """Ensure View B pools predictions across valid folds into a single PR curve."""
    result = compute_multiview_aggregations(temp_output_dir)
    summary = result["summary"]

    assert summary["pooled_micro_prauc"] > 0.50
    assert pytest.approx(summary["pooled_micro_prauc"], abs=1e-3) == 0.5488
    assert summary["pooled_positive_samples"] == 11
    assert summary["pooled_total_samples"] == 126


def test_view_c_event_level_alarm_system(temp_output_dir: Path) -> None:
    """Ensure View C evaluates independent physical failure episodes."""
    result = compute_multiview_aggregations(temp_output_dir)
    summary = result["summary"]

    assert summary["total_failure_episodes"] == 6
    assert summary["detected_failure_episodes"] == 5
    assert pytest.approx(summary["event_recall"], abs=1e-3) == 0.8333
    assert summary["median_lead_time_days"] == 5.0
    assert summary["iqr_lead_time_days"] == 1.0


def test_exploratory_event_weighted_prauc(temp_output_dir: Path) -> None:
    """Ensure event-weighted PR-AUC is reported as exploratory (0.5559)."""
    result = compute_multiview_aggregations(temp_output_dir)
    summary = result["summary"]

    assert pytest.approx(summary["exploratory_event_weighted_prauc"], abs=1e-3) == 0.5559


def test_fold_4_and_holdout_overlap_detection(temp_output_dir: Path) -> None:
    """Ensure Fold 4 and Locked Holdout are recognized as evaluating the exact same late period."""
    result = compute_multiview_aggregations(temp_output_dir)
    summary = result["summary"]

    assert summary["is_fold_4_holdout_overlap"] is True
    assert "Sep 06–12" in summary["overlap_note"] or "2026-09-06" in summary["fold_4_period"]
    assert "UNRESOLVED" in summary["temporal_generalization_status"]


def test_forbidden_claims_regression() -> None:
    """Guardrail test: ensure that no active document claims event weighting 'proves' or 'confirms' fold artifact."""
    docs_to_check = [
        Path("docs/evaluation/PHASE_3A1_TEMPORAL_DIAGNOSIS.md"),
        Path("docs/EVALUATION.md"),
    ]

    forbidden_phrases = [
        "confirms that the collapse is an evaluation fold artifact",
        "proves that the collapse is merely a fold artifact",
        "100% robust",
        "universal robustness",
    ]

    for doc_path in docs_to_check:
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            assert phrase.lower() not in text.lower(), (
                f"Forbidden phrase '{phrase}' found in {doc_path}!"
            )
