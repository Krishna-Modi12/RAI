"""Cross-turbine (leave-one-turbine-out) tests use synthetic CARE-shaped frames, independent
of whether the real ~5.5GB archive is present - only the orchestration logic (turbine
grouping, fold construction, insufficient-data handling) is under test here; the CARE score
arithmetic itself is already covered by `test_external_care_metrics.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rai.eval.external.care import cross_turbine as ct
from rai.eval.external.care.metrics import CareDatasetLabel

_UNUSED_FARM_DIR = Path("unused")


def _synthetic_dataset(*, n_train: int, n_pred: int, asset: str) -> pd.DataFrame:
    n = n_train + n_pred
    rng = np.random.default_rng(abs(hash((n_train, n_pred, asset))) % (2**31))
    return pd.DataFrame(
        {
            "asset_id": [asset] * n,
            "care_id": np.arange(n),
            "care_train_test": ["train"] * n_train + ["prediction"] * n_pred,
            "care_status_type_id": [0] * n,
            "wind_speed_ms": rng.normal(8.0, 1.5, n),
            "power_kw": rng.normal(1200.0, 150.0, n),
        }
    )


@dataclass
class _StubBaseline:
    """Predicts 1 exactly on the rows the test wants flagged, by absolute position."""

    flagged_positions: frozenset[int]

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        idx = np.asarray(frame["care_id"])
        return np.isin(idx, list(self.flagged_positions)).astype(int)


def test_score_with_baseline_anomaly_event_scores_coverage_from_id_range():
    frame = _synthetic_dataset(n_train=50, n_pred=50, asset="CARE-WT-0")
    row = pd.Series(
        {
            "event_id": 1,
            "event_label": "anomaly",
            "event_start_id": 70,
            "event_end_id": 79,
            "event_description": "test fault",
        }
    )
    # Flag exactly the true event window (ids 70-79): perfect coverage.
    baseline = _StubBaseline(flagged_positions=frozenset(range(70, 80)))
    score, reliability_input = ct._score_with_baseline("Test Farm", row, frame, baseline)

    assert score.label == CareDatasetLabel.ANOMALY_EVENT.value
    assert score.coverage_fbeta == pytest.approx(1.0)
    assert score.accuracy is None  # accuracy is only defined for normal-behavior datasets
    assert score.earliness == pytest.approx(1.0)  # detected across the whole event window
    assert reliability_input.label is CareDatasetLabel.ANOMALY_EVENT


def test_score_with_baseline_normal_behavior_has_zero_ground_truth_and_defines_accuracy():
    frame = _synthetic_dataset(n_train=50, n_pred=50, asset="CARE-WT-0")
    row = pd.Series({"event_id": 2, "event_label": "normal", "event_description": ""})
    baseline = _StubBaseline(flagged_positions=frozenset())  # never flags -> perfect accuracy
    score, _ = ct._score_with_baseline("Test Farm", row, frame, baseline)

    assert score.label == CareDatasetLabel.NORMAL_BEHAVIOR.value
    assert score.coverage_fbeta is None
    assert score.earliness is None
    assert score.accuracy == pytest.approx(1.0)


def test_leave_one_turbine_out_marks_insufficient_data_when_fold_has_no_anomaly(monkeypatch):
    # Two turbines: WT-0 has one anomaly + one normal dataset; WT-1 has only normal datasets.
    frames = {
        1: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-0"),
        2: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-0"),
        3: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-1"),
        4: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-1"),
    }
    events = pd.DataFrame(
        [
            {"event_id": 1, "event_label": "anomaly", "event_start_id": 70, "event_end_id": 79, "event_description": "fault"},
            {"event_id": 2, "event_label": "normal", "event_description": ""},
            {"event_id": 3, "event_label": "normal", "event_description": ""},
            {"event_id": 4, "event_label": "normal", "event_description": ""},
        ]
    )

    monkeypatch.setattr(ct, "load_event_info", lambda _path: events)
    monkeypatch.setattr(ct, "_load_dataset", lambda _farm_dir, eid: frames[eid])

    results = ct.run_leave_one_turbine_out(_UNUSED_FARM_DIR, "zscore_threshold")

    by_turbine = {r.test_turbine: r for r in results}
    assert by_turbine["CARE-WT-1"].status == "INSUFFICIENT_DATA"
    assert by_turbine["CARE-WT-1"].care_score is None
    assert by_turbine["CARE-WT-1"].n_test_anomaly_datasets == 0

    assert by_turbine["CARE-WT-0"].status == "COMPUTED"
    assert by_turbine["CARE-WT-0"].care_score is not None
    assert by_turbine["CARE-WT-0"].train_turbines == ("CARE-WT-1",)


def test_leave_one_turbine_out_never_trains_on_the_held_out_turbines_own_rows(monkeypatch):
    """The pooled training frame for a fold must exclude every dataset from the held-out
    turbine - otherwise this collapses back into the in-turbine baseline `farm_a_runner.py`
    already reports, and the fold would not be testing generalization at all."""
    frames = {
        1: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-0"),
        2: _synthetic_dataset(n_train=60, n_pred=40, asset="CARE-WT-1"),
    }
    events = pd.DataFrame(
        [
            {"event_id": 1, "event_label": "anomaly", "event_start_id": 70, "event_end_id": 79, "event_description": "fault"},
            {"event_id": 2, "event_label": "normal", "event_description": ""},
        ]
    )
    monkeypatch.setattr(ct, "load_event_info", lambda _path: events)
    monkeypatch.setattr(ct, "_load_dataset", lambda _farm_dir, eid: frames[eid])

    seen_pooled_assets: list[set[str]] = []
    real_fit = ct._fit_baseline

    def _spy_fit(model_name, train_frame):
        # `asset_id` rides along in the pooled frame (it is dropped only when the feature
        # matrix is built inside fit_*), so it directly tells us which turbines fed this fit.
        seen_pooled_assets.append(set(train_frame["asset_id"].unique()))
        return real_fit(model_name, train_frame)

    monkeypatch.setattr(ct, "_fit_baseline", _spy_fit)
    results = ct.run_leave_one_turbine_out(_UNUSED_FARM_DIR, "zscore_threshold")

    assert len(seen_pooled_assets) == len(results) == 2  # one fit per held-out turbine
    for result, pooled_assets in zip(results, seen_pooled_assets, strict=True):
        assert result.test_turbine not in pooled_assets
