"""Gate 5.4: does RAI's CARE ingestion resolve two signals because CARE forces that, or
because RAI never wires `feature_description.csv` into `resolve_columns`'s `sensor_map`?

Covers, per the Gate 5.4 test list: feature-inventory completeness, semantic-metadata
parsing, feature-rejection-reason classification, CARE_NARROW vs CARE_SEMANTIC behaviour,
train/prediction isolation, event-metadata exclusion from features, and deterministic
feature resolution. `rai.eval.external.care.champion`/`published_if` and the official CARE
scorer's own correctness are covered by the concurrently-developed
`tests/test_gate52_care_scorer_audit.py` and `tests/test_gate52_baselines_and_champion.py`
(43 tests, re-run and confirmed passing as part of this gate) and are not duplicated here.

All fixtures are small, synthetic, on-disk CSVs built in `tmp_path` - independent of the
multi-gigabyte real archive, matching the existing convention in
`tests/test_external_care_cross_farm.py`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from rai.eval.external.care import cross_farm_semantic as cfs
from rai.eval.external.care import feature_inventory as fi
from rai.eval.external.care import feature_policy as fp


def _write_feature_description(farm_dir: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(farm_dir / "feature_description.csv", sep=";", index=False)


def _write_sample_dataset(farm_dir: Path, columns: dict[str, list[object]]) -> Path:
    (farm_dir / "datasets").mkdir(parents=True, exist_ok=True)
    path = farm_dir / "datasets" / "1.csv"
    pd.DataFrame(columns).to_csv(path, sep=";", index=False)
    return path


def _farm(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Semantic metadata parsing + the energy-counter safety fix
# ---------------------------------------------------------------------------


def test_build_safe_sensor_map_excludes_energy_counter_units_even_when_is_counter_is_false():
    """The bug this gate found: CARE's own `is_counter` flag is unreliable (a Wh cumulative
    counter can ship with `is_counter=False`) - the unit is what must gate exclusion."""
    desc = pd.DataFrame(
        [
            {"sensor_name": "sensor_50", "statistics_type": "avg", "description": "Total active power", "unit": "Wh", "is_angle": False, "is_counter": False},
            {"sensor_name": "sensor_52", "statistics_type": "avg", "description": "Rotor rpm", "unit": "rpm", "is_angle": False, "is_counter": False},
        ]
    )
    safe = fi.build_safe_sensor_map(desc)
    assert "sensor_50" not in safe  # cumulative Wh counter excluded despite is_counter=False
    assert safe["sensor_52"] == "Rotor rpm"


def test_build_safe_sensor_map_exclusion_is_case_and_whitespace_insensitive():
    desc = pd.DataFrame(
        [{"sensor_name": "sensor_1", "statistics_type": "avg", "description": "x", "unit": " kWh ", "is_angle": False, "is_counter": False}]
    )
    assert fi.build_safe_sensor_map(desc) == {}


# ---------------------------------------------------------------------------
# Feature inventory completeness + rejection-reason classification
# ---------------------------------------------------------------------------


@pytest.fixture
def toy_farm(tmp_path: Path) -> Path:
    farm_dir = _farm(tmp_path, "Wind Farm Toy")
    _write_feature_description(
        farm_dir,
        [
            {"sensor_name": "sensor_50", "statistics_type": "avg", "description": "Total active power", "unit": "Wh", "is_angle": False, "is_counter": False},
            {"sensor_name": "sensor_52", "statistics_type": "avg", "description": "Rotor rpm", "unit": "rpm", "is_angle": False, "is_counter": False},
            {"sensor_name": "sensor_99", "statistics_type": "avg", "description": "Unrecognizable widget flux", "unit": "widgets", "is_angle": False, "is_counter": False},
        ],
    )
    _write_sample_dataset(
        farm_dir,
        {
            "time_stamp": ["2020-01-01 00:00:00", "2020-01-01 00:10:00"],
            "id": [1, 2],
            "train_test": ["train", "prediction"],
            "status_type_id": [0, 0],
            "asset_id": [0, 0],
            "wind_speed_3_avg": [7.5, 8.1],
            "power_29_avg": [1200.0, 1300.0],
            "sensor_50_avg": [500000.0, 500100.0],
            "sensor_52_avg": [14.2, 14.5],
            "sensor_99_avg": [1.0, 2.0],
        },
    )
    return farm_dir


def test_feature_inventory_has_exactly_one_row_per_raw_column(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    raw_columns = pd.read_csv(sample, sep=";", nrows=1).columns
    rows = fi.build_feature_inventory(toy_farm, sample)
    assert len(rows) == len(raw_columns)
    assert {r.column_name for r in rows} == set(raw_columns)


def test_feature_inventory_marks_care_metadata_columns_correctly(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    rows = {r.column_name: r for r in fi.build_feature_inventory(toy_farm, sample)}
    for col in ("time_stamp", "id", "train_test", "status_type_id", "asset_id"):
        assert rows[col].is_metadata is True
        assert rows[col].is_sensor is False


def test_feature_inventory_recovers_power_and_rotor_via_semantic_sensor_map(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    rows = {r.column_name: r for r in fi.build_feature_inventory(toy_farm, sample)}
    # power_29_avg already resolves by name alone; sensor_52_avg only resolves once its
    # CARE-supplied description ("Rotor rpm") is fed through the safe sensor_map.
    assert rows["power_29_avg"].recognized_by_rai is True
    assert rows["sensor_52_avg"].recognized_by_rai is True
    assert rows["sensor_52_avg"].matched_canonical == "rotor_rpm"


def test_feature_inventory_rejects_energy_counter_with_exact_reason(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    rows = {r.column_name: r for r in fi.build_feature_inventory(toy_farm, sample)}
    assert rows["sensor_50_avg"].recognized_by_rai is False
    assert rows["sensor_50_avg"].rejection_reason == "excluded_cumulative_energy_counter"
    # and it must not have silently won the power_kw slot instead of power_29_avg
    assert rows["power_29_avg"].matched_canonical == "power_kw"


def test_feature_inventory_reports_no_canonical_slot_for_genuinely_unmatched_sensors(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    rows = {r.column_name: r for r in fi.build_feature_inventory(toy_farm, sample)}
    assert rows["sensor_99_avg"].recognized_by_rai is False
    assert rows["sensor_99_avg"].rejection_reason == "no_canonical_slot"


def test_feature_inventory_is_deterministic(toy_farm: Path):
    sample = fi._sample_csv_for(toy_farm)
    rows_a = [r.__dict__ for r in fi.build_feature_inventory(toy_farm, sample)]
    rows_b = [r.__dict__ for r in fi.build_feature_inventory(toy_farm, sample)]
    assert rows_a == rows_b


# ---------------------------------------------------------------------------
# CARE_NARROW vs CARE_SEMANTIC policy wiring
# ---------------------------------------------------------------------------


def test_sensor_map_for_narrow_policy_is_none_and_touches_no_file(tmp_path: Path):
    farm_dir = tmp_path / "Wind Farm Untouched"  # deliberately does not exist
    assert fp._sensor_map_for(farm_dir, "care_narrow") is None


def test_sensor_map_for_semantic_policy_uses_safe_sensor_map(toy_farm: Path):
    sensor_map = fp._sensor_map_for(toy_farm, "care_semantic")
    assert sensor_map is not None
    assert "sensor_50" not in sensor_map  # energy counter still excluded through this path
    assert sensor_map["sensor_52"] == "Rotor rpm"


def test_load_dataset_with_policy_never_drops_rows_for_the_id_based_join(toy_farm: Path):
    frame = fp._load_dataset_with_policy(toy_farm, 1, sensor_map=None)
    assert len(frame) == 2  # both rows preserved; the event join is positional on care_id


def test_load_dataset_with_policy_excludes_event_metadata_columns_from_the_feature_frame(toy_farm: Path):
    """Nothing in `event_info.csv` (event_id/event_label/event_start_id/event_end_id/
    event_description) is ever a column of the frame handed to a feature policy or a
    baseline - those labels are joined in by `_score_dataset` via `care_id`, never merged
    into the feature table itself."""
    frame = fp._load_dataset_with_policy(toy_farm, 1, sensor_map=None)
    leak_columns = {"event_id", "event_label", "event_start_id", "event_end_id", "event_description"}
    assert leak_columns.isdisjoint(frame.columns)


def test_run_farm_with_policy_selects_a_different_sensor_map_per_policy(toy_farm: Path, monkeypatch):
    """The only thing that may differ between CARE_NARROW and CARE_SEMANTIC is the
    sensor_map passed to the loader - spy on `_load_dataset_with_policy` to prove it."""
    seen_sensor_maps: list[dict[str, str] | None] = []
    real_loader = fp._load_dataset_with_policy

    def _spy(farm_dir, event_id, sensor_map):
        seen_sensor_maps.append(sensor_map)
        return real_loader(farm_dir, event_id, sensor_map)

    monkeypatch.setattr(fp, "_load_dataset_with_policy", _spy)

    events = pd.DataFrame([{"event_id": 1, "event_label": "normal", "event_description": ""}])
    monkeypatch.setattr(fp, "load_event_info", lambda _path: events)

    fp.run_farm_with_policy(toy_farm, "zscore_threshold", "care_narrow")
    fp.run_farm_with_policy(toy_farm, "zscore_threshold", "care_semantic")

    assert seen_sensor_maps[0] is None
    assert seen_sensor_maps[1] is not None and "sensor_52" in seen_sensor_maps[1]


# ---------------------------------------------------------------------------
# Cross-farm-semantic: never refits, uses the semantic sensor_map per farm
# ---------------------------------------------------------------------------


def test_cross_farm_semantic_loads_each_farm_with_its_own_sensor_map(toy_farm: Path, monkeypatch):
    calls: list[tuple[Path, dict[str, str] | None]] = []
    real_sensor_map_for = cfs._sensor_map_for

    def _spy(farm_dir, policy):
        result = real_sensor_map_for(farm_dir, policy)
        calls.append((farm_dir, result))
        return result

    monkeypatch.setattr(cfs, "_sensor_map_for", _spy)
    events = pd.DataFrame([{"event_id": 1, "event_label": "normal", "event_description": ""}])
    monkeypatch.setattr(cfs, "load_event_info", lambda _path: events)

    cfs._load_farm_semantic(toy_farm)

    assert len(calls) == 1
    farm_dir_seen, sensor_map_seen = calls[0]
    assert farm_dir_seen == toy_farm
    assert sensor_map_seen is not None and "sensor_52" in sensor_map_seen
