import numpy as np
import pandas as pd

from rai.eval.external.kelmarsh.benchmark import (
    EVALUATED_CATEGORIES,
    EXCLUDED_CATEGORIES,
    Event,
    _window_stats,
)


def test_kelmarsh_taxonomy_does_not_call_events_failures() -> None:
    assert EVALUATED_CATEGORIES == ("Forced outage", "Scheduled Maintenance")
    assert "Out of Environmental Specification" in EXCLUDED_CATEGORIES
    assert "Out of Electrical Specification" in EXCLUDED_CATEGORIES


def test_missing_event_end_is_one_sampling_interval_not_the_rest_of_series() -> None:
    timestamps = pd.date_range("2019-01-01", periods=20, freq="10min", tz="UTC").to_series(index=range(20))
    flags = np.zeros(len(timestamps), dtype=int)
    flags[6] = 1
    result = _window_stats({"model": flags}, timestamps, Event("K-1", "Forced outage", timestamps.iloc[6], None, "1", "event"))
    assert result["event_rows"] == 1
    assert result["model_event_detected"] is True
