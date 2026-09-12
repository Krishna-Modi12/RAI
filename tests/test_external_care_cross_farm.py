"""Cross-farm transfer tests use synthetic CARE-shaped frames for two "farms" with
deliberately different resolved-column sets, independent of whether the real archive is
present. The CARE score arithmetic itself is covered by `test_external_care_metrics.py`;
what is under test here is the feature-intersection logic and the never-refit-on-target
transfer orchestration.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from rai.eval.external.care import cross_farm as cf


def _synthetic_dataset(
    *, n_train: int, n_pred: int, asset: str, extra_columns: dict[str, float] | None = None
) -> pd.DataFrame:
    n = n_train + n_pred
    rng = np.random.default_rng(abs(hash((n_train, n_pred, asset, tuple((extra_columns or {}).keys())))) % (2**31))
    frame = pd.DataFrame(
        {
            "asset_id": [asset] * n,
            "care_id": np.arange(n),
            "care_train_test": ["train"] * n_train + ["prediction"] * n_pred,
            "care_status_type_id": [0] * n,
            "wind_speed_ms": rng.normal(8.0, 1.5, n),
            "power_kw": rng.normal(1200.0, 150.0, n),
        }
    )
    for col in extra_columns or {}:
        frame[col] = rng.normal(50.0, 5.0, n)
    return frame


def test_intersected_columns_is_only_columns_present_and_populated_in_every_frame():
    source = _synthetic_dataset(n_train=50, n_pred=0, asset="A-0", extra_columns={"gearbox_oil_temp_c": 1.0})
    target = _synthetic_dataset(n_train=50, n_pred=0, asset="B-0")  # no gearbox_oil_temp_c
    cols = cf._intersected_columns(source, target)
    assert set(cols) == {"wind_speed_ms", "power_kw"}


def test_intersected_columns_excludes_columns_that_are_all_null_in_one_frame():
    source = _synthetic_dataset(n_train=50, n_pred=0, asset="A-0")
    target = _synthetic_dataset(n_train=50, n_pred=0, asset="B-0")
    target["power_kw"] = np.nan  # unresolved on the "target farm"
    cols = cf._intersected_columns(source, target)
    assert cols == ["wind_speed_ms"]


def test_run_transfer_never_refits_and_uses_only_intersected_columns(monkeypatch):
    source_events = pd.DataFrame(
        [{"event_id": 1, "event_label": "normal", "event_description": ""}]
    )
    target_events = pd.DataFrame(
        [
            {"event_id": 2, "event_label": "anomaly", "event_start_id": 70, "event_end_id": 79, "event_description": "fault"},
            {"event_id": 3, "event_label": "normal", "event_description": ""},
        ]
    )
    source_frames = {1: _synthetic_dataset(n_train=200, n_pred=0, asset="A-0", extra_columns={"gearbox_oil_temp_c": 1.0})}
    target_frames = {
        2: _synthetic_dataset(n_train=60, n_pred=40, asset="B-0"),
        3: _synthetic_dataset(n_train=60, n_pred=40, asset="B-1"),
    }

    def fake_load_event_info(path):
        return source_events if "A" in str(path) else target_events

    def fake_load_dataset(farm_dir, eid):
        return source_frames[eid] if eid in source_frames else target_frames[eid]

    monkeypatch.setattr(cf, "load_event_info", fake_load_event_info)
    monkeypatch.setattr(cf, "_load_dataset", fake_load_dataset)

    fit_calls: list[list[str]] = []
    real_fit = cf.fit_zscore_threshold

    def _spy_fit(train_frame, **kwargs):
        fit_calls.append(sorted(train_frame.columns))
        return real_fit(train_frame, **kwargs)

    monkeypatch.setattr(cf, "fit_zscore_threshold", _spy_fit)

    result = cf.run_transfer(Path("Wind Farm A"), Path("Wind Farm B"), "zscore_threshold")

    assert result.status == "COMPUTED"
    assert set(result.feature_intersection) == {"wind_speed_ms", "power_kw"}
    assert len(fit_calls) == 1  # fit exactly once on the source, never refit per target dataset
    assert set(fit_calls[0]) == {"wind_speed_ms", "power_kw"}  # gearbox_oil_temp_c excluded
    assert result.n_target_anomaly_datasets == 1
    assert result.n_target_normal_datasets == 1


def test_run_transfer_marks_insufficient_data_when_no_feature_intersection(monkeypatch):
    source_events = pd.DataFrame([{"event_id": 1, "event_label": "normal", "event_description": ""}])
    target_events = pd.DataFrame([{"event_id": 2, "event_label": "normal", "event_description": ""}])
    source_frame = _synthetic_dataset(n_train=50, n_pred=0, asset="A-0")
    target_frame = _synthetic_dataset(n_train=50, n_pred=0, asset="B-0")
    target_frame["wind_speed_ms"] = np.nan
    target_frame["power_kw"] = np.nan

    def fake_load_event_info(path):
        return source_events if "A" in str(path) else target_events

    def fake_load_dataset(farm_dir, eid):
        return source_frame if eid == 1 else target_frame

    monkeypatch.setattr(cf, "load_event_info", fake_load_event_info)
    monkeypatch.setattr(cf, "_load_dataset", fake_load_dataset)

    result = cf.run_transfer(Path("Wind Farm A"), Path("Wind Farm B"), "zscore_threshold")

    assert result.status == "INSUFFICIENT_DATA"
    assert result.feature_intersection == ()
    assert result.care_score is None
