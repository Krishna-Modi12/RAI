"""Adapter tests use synthetic data shaped like a normalised CARE frame, independent of
whether the real ~5.5GB CARE archive is present on this machine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rai.eval.external.care.adapter import fit_isolation_forest, fit_zscore_threshold


def _synthetic_frame(n: int, seed: int, anomalous: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "wind_speed_ms": rng.normal(8.0, 1.5, n),
            "power_kw": rng.normal(1200.0, 150.0, n),
            "gearbox_oil_temp_c": rng.normal(55.0, 3.0, n),
            "main_bearing_temp_c": rng.normal(48.0, 2.0, n),
        }
    )
    if anomalous:
        # A clear thermal excursion in the back half of the frame.
        frame.loc[n // 2 :, "gearbox_oil_temp_c"] += 25.0
        frame.loc[n // 2 :, "main_bearing_temp_c"] += 15.0
    return frame


def test_isolation_forest_flags_more_on_anomalous_frame_than_normal():
    train = _synthetic_frame(500, seed=1)
    baseline = fit_isolation_forest(train, seed=20260912)

    normal_test = _synthetic_frame(100, seed=2, anomalous=False)
    anomalous_test = _synthetic_frame(100, seed=3, anomalous=True)

    normal_rate = baseline.predict(normal_test).mean()
    anomalous_rate = baseline.predict(anomalous_test).mean()
    assert anomalous_rate > normal_rate


def test_isolation_forest_raises_on_no_usable_columns():
    train = pd.DataFrame({"unrelated_column": [1, 2, 3]})
    with pytest.raises(ValueError):
        fit_isolation_forest(train)


def test_zscore_threshold_flags_the_injected_excursion():
    train = _synthetic_frame(500, seed=1)
    baseline = fit_zscore_threshold(train, z_threshold=3.0)

    normal_test = _synthetic_frame(100, seed=2, anomalous=False)
    anomalous_test = _synthetic_frame(100, seed=3, anomalous=True)

    normal_flags = baseline.predict(normal_test)
    anomalous_flags = baseline.predict(anomalous_test)
    # The excursion sits in the back half of the anomalous frame.
    assert anomalous_flags[50:].mean() > normal_flags.mean()


def test_zscore_threshold_handles_missing_columns_gracefully():
    train = _synthetic_frame(200, seed=1)
    baseline = fit_zscore_threshold(train)
    frame_missing_cols = pd.DataFrame({"wind_speed_ms": [8.0, 9.0, 100.0]})
    flags = baseline.predict(frame_missing_cols)
    assert len(flags) == 3
