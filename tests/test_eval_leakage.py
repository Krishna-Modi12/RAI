"""Tests for evaluation harness leakage guards, splits, and CARE metrics."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from rai.eval.leakage import (
    DataLeakageError,
    assert_no_leakage,
    check_asset_leakage,
    check_temporal_leakage,
)
from rai.eval.metrics import (
    compute_abstention_metrics,
    compute_calibration_report,
    compute_care_score,
    compute_classification_battery,
)
from rai.eval.splits import split_asset_holdout, split_temporal


def test_temporal_leakage_detection():
    t0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    t_train = [t0 + timedelta(hours=i) for i in range(10)]
    t_test_clean = [t0 + timedelta(hours=15 + i) for i in range(10)]
    t_test_leak = [t0 + timedelta(hours=5 + i) for i in range(10)]

    ok, gap, issues = check_temporal_leakage(t_train, t_test_clean, min_gap_hours=2.0)
    assert ok is True
    assert gap >= 5.0
    assert len(issues) == 0

    ok_leak, gap_leak, issues_leak = check_temporal_leakage(t_train, t_test_leak, min_gap_hours=1.0)
    assert ok_leak is False
    assert len(issues_leak) > 0


def test_asset_leakage_detection():
    train_assets = {"WT-001", "WT-002", "WT-003"}
    test_clean = {"WT-004", "WT-005"}
    test_leak = {"WT-003", "WT-004"}

    ok, overlap = check_asset_leakage(train_assets, test_clean)
    assert ok is True
    assert len(overlap) == 0

    ok_leak, overlap_leak = check_asset_leakage(train_assets, test_leak)
    assert ok_leak is False
    assert "WT-003" in overlap_leak


def test_assert_no_leakage_raises():
    t0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    df_train = pd.DataFrame({
        "ts": [t0 + timedelta(hours=i) for i in range(5)],
        "asset_id": ["WT-001"] * 5,
    })
    df_leak = pd.DataFrame({
        "ts": [t0 + timedelta(hours=2 + i) for i in range(5)],
        "asset_id": ["WT-002"] * 5,
    })

    with pytest.raises(DataLeakageError):
        assert_no_leakage(df_train, df_leak, time_col="ts", min_gap_hours=1.0)


def test_care_score_calculation():
    events = [
        {
            "asset_id": "WT-017",
            "onset": "2026-09-05T00:00:00Z",
            "failure": "2026-09-15T00:00:00Z",
        },
        {
            "asset_id": "INV-023",
            "onset": "2026-09-10T00:00:00Z",
            "failure": "2026-09-20T00:00:00Z",
        },
    ]
    # WT-017 detected 7 days before failure, INV-023 missed, plus 1 false alarm on WT-001
    alarms = [
        {"asset_id": "WT-017", "timestamp": "2026-09-08T00:00:00Z"},
        {"asset_id": "WT-001", "timestamp": "2026-09-02T00:00:00Z"},
    ]

    res = compute_care_score(
        events=events,
        alarms=alarms,
        healthy_periods_duration_hours=24.0 * 30.0 * 10,  # 10 turbine-months
        target_lead_days=14.0,
        fa_budget_per_year=12.0,
    )

    assert res.coverage == 0.50
    assert res.earliness > 0.0
    assert res.care_score > 0.0
    assert res.n_events == 2
    assert res.n_detected == 1


def test_calibration_and_abstention_metrics():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.25, 0.8, 0.85, 0.9])
    conf = np.array([0.9, 0.8, 0.75, 0.85, 0.9, 0.95])

    cal = compute_calibration_report(y_true, y_prob, n_bins=5)
    assert cal.brier_score >= 0.0
    assert cal.expected_calibration_error >= 0.0

    cls_bat = compute_classification_battery(y_true, y_prob, threshold=0.5)
    assert cls_bat["pr_auc"] > 0.8
    assert cls_bat["precision"] == 1.0
    assert cls_bat["recall"] == 1.0

    abst = compute_abstention_metrics(y_true, (y_prob >= 0.5).astype(int), conf, confidence_threshold=0.80)
    assert abst.coverage_pct > 0.0
    assert abst.high_conf_error_rate == 0.0


def test_split_temporal_and_asset():
    t0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    n_pts = 200
    df = pd.DataFrame({
        "ts": [t0 + timedelta(hours=i) for i in range(n_pts)],
        "asset_id": ["WT-001"] * 100 + ["WT-002"] * 100,
        "power_kw": np.random.uniform(500, 1500, n_pts),
    })

    temp_split = split_temporal(df, time_col="ts", train_frac=0.60, val_frac=0.20, gap_hours=4.0, enforce_embargo=False)
    assert len(temp_split.train) > 0
    assert len(temp_split.test) > 0
    assert temp_split.train["ts"].max() < temp_split.val["ts"].min()
    assert temp_split.val["ts"].max() < temp_split.test["ts"].min()

    asset_split = split_asset_holdout(df, asset_col="asset_id", test_frac=0.5)
    train_assets = set(asset_split.train["asset_id"].unique())
    test_assets = set(asset_split.test["asset_id"].unique())
    assert len(train_assets.intersection(test_assets)) == 0


def test_embargo_boundary_exact_enforcement():
    from rai.eval.splits import (
        compute_pipeline_embargo_hours,
        split_temporal,
        verify_embargo_boundary,
    )

    # 1. Verify exact mathematical formula: 336h lookback + 6h thermal lag = 342.0h
    derived_embargo = compute_pipeline_embargo_hours()
    assert derived_embargo == 342.0

    # 2. Boundary Test 1: gap = 341.99 -> FAIL (DataLeakageError)
    with pytest.raises(DataLeakageError, match="violates the physical backward reach invariant"):
        verify_embargo_boundary(341.99, min_embargo=342.0)

    # 3. Boundary Test 2: gap = 342.00 -> PASS
    assert verify_embargo_boundary(342.00, min_embargo=342.0) is True

    # 4. Boundary Test 3: gap = 342.01 -> PASS
    assert verify_embargo_boundary(342.01, min_embargo=342.0) is True

    # 5. Integration test on split_temporal
    t0 = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    long_df = pd.DataFrame({
        "ts": [t0 + timedelta(hours=i) for i in range(24 * 60)],
        "asset_id": ["WT-001"] * (24 * 60),
    })

    # Sub-boundary split must fail
    with pytest.raises(DataLeakageError):
        split_temporal(long_df, gap_hours=341.99, enforce_embargo=True)

    # Exact boundary split must pass
    valid_split = split_temporal(long_df, gap_hours=342.0, enforce_embargo=True)
    assert valid_split.metadata["gap_hours"] == 342.0


def test_derived_embargo_and_rolling_origin():
    from rai.eval.splits import compute_pipeline_embargo_hours, generate_rolling_origin_folds

    embargo_hours = compute_pipeline_embargo_hours()
    # Must be at least 14 days lookback (336h) + thermal lag (6h) = 342.0h
    assert embargo_hours >= 342.0

    t0 = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    df = pd.DataFrame({
        "ts": [t0 + timedelta(hours=i) for i in range(24 * 60)],
        "asset_id": ["WT-001"] * (24 * 60),
    })
    folds = generate_rolling_origin_folds(df, n_folds=3, embargo_hours=embargo_hours)
    assert len(folds) == 3
    for fold in folds:
        assert fold.train["ts"].max() < fold.test["ts"].min()
        actual_gap = (fold.test["ts"].min() - fold.train["ts"].max()).total_seconds() / 3600.0
        assert actual_gap >= embargo_hours


def test_rag_retrieval_temporal_cutoff_and_self_exclusion():
    from rai.memory.library import CASES
    from rai.memory.retrieval import find_similar_cases
    from rai.schemas import (
        AnomalyEvidence,
        AssetType,
        DetectorScore,
        EvidencePacket,
        OperatingState,
        RiskAssessment,
        RiskBand,
    )

    packet = EvidencePacket(
        asset_id="WT-017",
        asset_type=AssetType.WIND_TURBINE,
        generated_at=datetime.now(UTC),
        health_score=45.0,
        operating_state=OperatingState.NORMAL,
        anomaly=AnomalyEvidence(
            anomaly_score=0.82,
            confidence=0.90,
            detectors=[DetectorScore(detector="iforest", score=0.82)],
            persistence_hours=72.0,
            primary_driver="gearbox_oil_temp_c",
            signals=[],
        ),
        risk=RiskAssessment(
            risk_score=0.75,
            risk_band=RiskBand.HIGH,
            horizon_days=30,
            drivers={"gearbox_oil_temp_c": 0.8},
        ),
    )

    # Test self-retrieval exclusion: asset_id == WT-017 should never be returned
    cases = find_similar_cases(packet, k=10, exclude_asset_id="WT-017")
    assert not any(c.case_id.startswith("case-WT-017") for c in cases)

    # Test temporal knowledge cutoff: cases with closed_at > cutoff must be excluded
    cutoff_dt = pd.Timestamp("2026-08-01T00:00:00Z")
    cases_cutoff = find_similar_cases(packet, k=10, knowledge_cutoff=cutoff_dt)
    case_lookup = {c.case_id: c for c in CASES}
    for ret_c in cases_cutoff:
        orig = case_lookup.get(ret_c.case_id)
        if orig and orig.closed_at is not None:
            assert pd.to_datetime(orig.closed_at, utc=True) <= cutoff_dt


def test_adversarial_label_permutation_logic():
    from rai.eval.adversarial import run_label_permutation_test

    y_true = [0] * 36 + [1] * 6
    y_prob = [0.1] * 36 + [0.9] * 6

    res = run_label_permutation_test(y_true, y_prob, n_permutations=20, seed=42)
    assert res["passed"] is True
    # Permuted PR-AUC should be near base rate (6/42 ≈ 0.143)
    assert abs(res["mean_permuted_pr_auc"] - (6.0 / 42.0)) < 0.20
    assert abs(res["mean_permuted_mcc"]) < 0.20


def test_adversarial_future_sentinel_logic():
    from rai.eval.adversarial import run_future_sentinel_audit

    t0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    df = pd.DataFrame({
        "ts": [t0 + timedelta(hours=i) for i in range(100)],
        "power_kw": np.random.uniform(500, 1500, 100),
    })

    res = run_future_sentinel_audit(df, time_col="ts")
    assert res["passed"] is True
    assert res["sentinel_detected"] is True
