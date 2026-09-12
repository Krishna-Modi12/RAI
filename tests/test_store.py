"""Tests for the storage/access layer.

The fixture writes its own parquet files into tmp_path, so these tests never depend on the
simulator having run.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from rai.schemas import AssetState, AssetType, InjectedEvent, OperatingState
from rai.store import events as events_store
from rai.store import state as state_store
from rai.store import telemetry as telemetry_store
from rai.store.telemetry import DataUnavailable

WIND_ASSET = "WT-001"
SOLAR_ASSET = "INV-001"
ORPHAN_ASSET = "WT-999"
T0 = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
WIND_ROWS = 144  # 24 h at 10 min
SOLAR_ROWS = 96  # 24 h at 15 min


def _wind_frame(asset_id: str, rows: int = WIND_ROWS, start: datetime = T0) -> pd.DataFrame:
    ts = pd.date_range(start=start, periods=rows, freq="10min", tz="UTC")
    i = pd.Series(range(rows), dtype="float64")
    return pd.DataFrame(
        {
            "ts": ts,
            "asset_id": asset_id,
            "wind_speed_ms": 6.0 + (i % 12) * 0.25,
            "wind_direction_deg": 250.0 + (i % 20),
            "ambient_temp_c": 30.0 + (i % 8) * 0.1,
            "pressure_hpa": 1008.0,
            "humidity_pct": 45.0,
            "air_density": 1.16,
            "power_kw": 800.0 + i * 2.0,
            "rotor_rpm": 13.0,
            "pitch_angle_deg": 1.5,
            "nacelle_temp_c": 38.0,
            "gearbox_oil_temp_c": 62.0 + i * 0.01,
            "generator_winding_temp_c": 95.0,
            "main_bearing_temp_c": 55.0,
            "drivetrain_vibration_mms": 3.2,
            "status_code": 1,
            "operating_state": OperatingState.NORMAL.value,
        }
    )


def _solar_frame(asset_id: str, rows: int = SOLAR_ROWS, start: datetime = T0) -> pd.DataFrame:
    ts = pd.date_range(start=start, periods=rows, freq="15min", tz="UTC")
    i = pd.Series(range(rows), dtype="float64")
    return pd.DataFrame(
        {
            "ts": ts,
            "asset_id": asset_id,
            "ghi_wm2": 400.0 + i,
            "poa_wm2": 450.0 + i,
            "ambient_temp_c": 31.0,
            "module_temp_c": 48.0,
            "wind_speed_ms": 2.5,
            "ac_power_kw": 180.0 + i * 0.1,
            "dc_power_kw": 190.0 + i * 0.1,
            "dc_voltage_v": 620.0,
            "dc_current_a": 305.0,
            "inverter_temp_c": 52.0,
            "performance_ratio": 0.81,
            "soiling_ratio": 0.94,
            "status_code": 1,
            "operating_state": OperatingState.NORMAL.value,
        }
    )


def _site_met_frame() -> pd.DataFrame:
    ts = pd.date_range(start=T0, periods=48, freq="30min", tz="UTC")
    rows = []
    for site in ("kutch-wind", "charanka-solar"):
        rows.append(
            pd.DataFrame(
                {
                    "ts": ts,
                    "site": site,
                    "wind_speed_ms": 7.0,
                    "wind_direction_deg": 248.0,
                    "ambient_temp_c": 30.5,
                    "pressure_hpa": 1008.0,
                    "humidity_pct": 44.0,
                    "ghi_wm2": 500.0,
                    "dni_wm2": 620.0,
                    "dhi_wm2": 110.0,
                    "precip_mm": 0.0,
                    "dust_aod": 0.35,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def _events() -> list[InjectedEvent]:
    return [
        InjectedEvent(
            event_id="EVT-0001",
            asset_id=WIND_ASSET,
            scenario="gearbox_bearing_wear",
            component="gearbox",
            is_equipment_fault=True,
            onset=T0 + timedelta(hours=2),
            detectable_from=T0 + timedelta(hours=5),
            end=None,
            severity_final=0.7,
            description="Progressive gearbox bearing wear",
        ),
        InjectedEvent(
            event_id="EVT-0002",
            asset_id=SOLAR_ASSET,
            scenario="soiling_accumulation",
            component="soiling",
            is_equipment_fault=False,
            onset=T0 + timedelta(hours=1),
            detectable_from=T0 + timedelta(hours=3),
            end=T0 + timedelta(hours=12),
            severity_final=0.4,
            description="Dust accumulation between rain events",
        ),
    ]


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the store at an isolated data root and artifacts root, with data written."""
    data_root = tmp_path / "synthetic"
    (data_root / "telemetry").mkdir(parents=True)
    telemetry_store.set_data_root(data_root)
    state_store.set_artifact_root(tmp_path / "artifacts")

    telemetry_store.write_telemetry(WIND_ASSET, _wind_frame(WIND_ASSET))
    telemetry_store.write_telemetry(SOLAR_ASSET, _solar_frame(SOLAR_ASSET))
    telemetry_store.write_site_met(_site_met_frame())
    events_store.write_events(_events())

    yield data_root

    telemetry_store.reset_connection()
    telemetry_store.set_data_root(telemetry_store.config.SYNTHETIC)
    state_store.set_artifact_root(state_store.config.ARTIFACTS)


@pytest.fixture
def empty_store(tmp_path):
    """A data root with no files at all — the state before the simulator has run."""
    data_root = tmp_path / "empty"
    data_root.mkdir()
    telemetry_store.set_data_root(data_root)
    state_store.set_artifact_root(tmp_path / "artifacts")
    yield data_root
    telemetry_store.reset_connection()
    telemetry_store.set_data_root(telemetry_store.config.SYNTHETIC)
    state_store.set_artifact_root(state_store.config.ARTIFACTS)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_list_assets_with_data_uses_fleet_order(store):
    assert telemetry_store.list_assets_with_data() == [WIND_ASSET, SOLAR_ASSET]
    assert telemetry_store.telemetry_available() is True
    assert telemetry_store.telemetry_available(WIND_ASSET) is True
    assert telemetry_store.telemetry_available(ORPHAN_ASSET) is False


def test_available_columns_matches_canonical_schema(store):
    cols = telemetry_store.available_columns(WIND_ASSET)
    assert cols[:2] == ["ts", "asset_id"]
    for expected in ("gearbox_oil_temp_c", "drivetrain_vibration_mms", "operating_state"):
        assert expected in cols
    assert "poa_wm2" in telemetry_store.available_columns(SOLAR_ASSET)


def test_row_count(store):
    assert telemetry_store.row_count(WIND_ASSET) == WIND_ROWS
    assert telemetry_store.row_count(SOLAR_ASSET) == SOLAR_ROWS


# ---------------------------------------------------------------------------
# Telemetry reads
# ---------------------------------------------------------------------------


def test_load_telemetry_returns_tz_aware_sorted_frame(store):
    df = telemetry_store.load_telemetry(WIND_ASSET)
    assert len(df) == WIND_ROWS
    assert str(df["ts"].dt.tz) == "UTC"
    assert df["ts"].is_monotonic_increasing
    assert df["asset_id"].unique().tolist() == [WIND_ASSET]


def test_load_telemetry_respects_time_filter(store):
    start = T0 + timedelta(hours=4)
    end = T0 + timedelta(hours=6)
    df = telemetry_store.load_telemetry(WIND_ASSET, start=start, end=end)

    # Inclusive on both ends: 10-min cadence over 2 h -> 13 rows.
    assert len(df) == 13
    assert df["ts"].min() == pd.Timestamp(start)
    assert df["ts"].max() == pd.Timestamp(end)

    full = telemetry_store.load_telemetry(WIND_ASSET)
    assert len(df) < len(full)

    # A window beyond the data is empty, not an error.
    future = telemetry_store.load_telemetry(WIND_ASSET, start=T0 + timedelta(days=30))
    assert future.empty


def test_load_telemetry_column_subset_always_includes_ts(store):
    df = telemetry_store.load_telemetry(WIND_ASSET, columns=["power_kw", "gearbox_oil_temp_c"])
    assert list(df.columns) == ["ts", "power_kw", "gearbox_oil_temp_c"]


def test_load_telemetry_unknown_column_raises_keyerror(store):
    with pytest.raises(KeyError, match="not present"):
        telemetry_store.load_telemetry(WIND_ASSET, columns=["ac_power_kw"])


def test_load_window(store):
    end = T0 + timedelta(hours=23)
    df = telemetry_store.load_window(WIND_ASSET, end=end, hours=6)
    assert df["ts"].min() == pd.Timestamp(end - timedelta(hours=6))
    assert df["ts"].max() == pd.Timestamp(end)
    with pytest.raises(ValueError):
        telemetry_store.load_window(WIND_ASSET, end=end, hours=0)


def test_load_window_accepts_naive_datetime_as_utc(store):
    end_naive = datetime(2026, 9, 1, 12, 0)  # noqa: DTZ001
    df = telemetry_store.load_window(WIND_ASSET, end=end_naive, hours=1)
    assert df["ts"].max() == pd.Timestamp("2026-09-01T12:00:00Z")


def test_latest_row(store):
    row = telemetry_store.latest_row(WIND_ASSET)
    assert row is not None
    assert row["ts"] == pd.Timestamp(T0 + timedelta(minutes=10 * (WIND_ROWS - 1)))
    assert row["asset_id"] == WIND_ASSET


def test_latest_row_returns_none_for_empty_file(store):
    telemetry_store.write_telemetry(ORPHAN_ASSET, _wind_frame(ORPHAN_ASSET).iloc[0:0])
    assert telemetry_store.latest_row(ORPHAN_ASSET) is None


def test_load_fleet_latest_one_row_per_asset_union_schema(store):
    df = telemetry_store.load_fleet_latest()
    assert len(df) == 2
    assert set(df["asset_id"]) == {WIND_ASSET, SOLAR_ASSET}
    assert str(df["ts"].dt.tz) == "UTC"

    # Wind and solar columns coexist; the other type's columns are null.
    assert {"power_kw", "ac_power_kw", "poa_wm2", "gearbox_oil_temp_c"} <= set(df.columns)
    wind = df[df["asset_id"] == WIND_ASSET].iloc[0]
    assert wind["ts"] == pd.Timestamp(T0 + timedelta(minutes=10 * (WIND_ROWS - 1)))
    assert pd.isna(wind["ac_power_kw"])

    solar = df[df["asset_id"] == SOLAR_ASSET].iloc[0]
    assert solar["ts"] == pd.Timestamp(T0 + timedelta(minutes=15 * (SOLAR_ROWS - 1)))
    assert pd.isna(solar["power_kw"])


def test_data_extent(store):
    extent = telemetry_store.data_extent()
    assert extent is not None
    first, last = extent
    assert first == T0
    assert last == T0 + timedelta(minutes=10 * (WIND_ROWS - 1))
    assert first.tzinfo is not None and last.tzinfo is not None


def test_load_site_met(store):
    df = telemetry_store.load_site_met("kutch-wind")
    assert len(df) == 48
    assert df["site"].unique().tolist() == ["kutch-wind"]
    assert "dust_aod" in df.columns

    windowed = telemetry_store.load_site_met(
        "charanka-solar", start=T0, end=T0 + timedelta(hours=2)
    )
    assert len(windowed) == 5  # 30-min cadence, inclusive ends

    assert telemetry_store.load_site_met("no-such-site").empty


# ---------------------------------------------------------------------------
# Missing data
# ---------------------------------------------------------------------------


def test_data_unavailable_for_missing_asset(store):
    with pytest.raises(DataUnavailable) as excinfo:
        telemetry_store.load_telemetry(ORPHAN_ASSET)
    assert excinfo.value.code == "telemetry_missing"
    assert ORPHAN_ASSET in excinfo.value.message
    assert excinfo.value.path is not None


def test_empty_store_degrades_cleanly(empty_store):
    assert telemetry_store.list_assets_with_data() == []
    assert telemetry_store.telemetry_available() is False
    assert telemetry_store.data_extent() is None

    with pytest.raises(DataUnavailable) as fleet_err:
        telemetry_store.load_fleet_latest()
    assert fleet_err.value.code == "telemetry_missing"

    with pytest.raises(DataUnavailable) as met_err:
        telemetry_store.load_site_met("kutch-wind")
    assert met_err.value.code == "site_met_missing"

    with pytest.raises(DataUnavailable):
        telemetry_store.latest_row(WIND_ASSET)

    # Ground truth is optional: absent means empty, unless the caller demands it.
    assert events_store.events_available() is False
    assert events_store.load_events() == []
    with pytest.raises(DataUnavailable) as ev_err:
        events_store.load_events(required=True)
    assert ev_err.value.code == "events_missing"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_load_events_roundtrip(store):
    assert events_store.events_available() is True
    all_events = events_store.load_events()
    assert [e.event_id for e in all_events] == ["EVT-0002", "EVT-0001"]  # ordered by onset

    wind_events = events_store.load_events(WIND_ASSET)
    assert len(wind_events) == 1
    event = wind_events[0]
    assert isinstance(event, InjectedEvent)
    assert event.is_equipment_fault is True
    assert event.end is None  # NaT becomes None, not a fabricated timestamp
    assert event.onset == T0 + timedelta(hours=2)
    assert event.onset.tzinfo is not None

    solar_event = events_store.load_events(SOLAR_ASSET)[0]
    assert solar_event.end == T0 + timedelta(hours=12)
    assert solar_event.is_equipment_fault is False


def test_events_in_window(store):
    early = events_store.events_in_window(T0, T0 + timedelta(hours=1, minutes=30))
    assert [e.event_id for e in early] == ["EVT-0002"]

    late = events_store.events_in_window(T0 + timedelta(hours=20), T0 + timedelta(hours=24))
    assert [e.event_id for e in late] == ["EVT-0001"]  # open-ended event still active

    assert events_store.events_in_window(T0, T0 + timedelta(hours=24), asset_id=SOLAR_ASSET) == [
        e for e in events_store.load_events(SOLAR_ASSET)
    ]


def test_load_events_df(store):
    df = events_store.load_events_df()
    assert len(df) == 2
    assert str(df["onset"].dt.tz) == "UTC"


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def test_resample_hourly_mean(store):
    df = telemetry_store.load_telemetry(WIND_ASSET, end=T0 + timedelta(hours=2) - timedelta(minutes=10))
    out = telemetry_store.resample(df, 60, "mean")

    assert len(out) == 2
    assert out["ts"].tolist() == [pd.Timestamp(T0), pd.Timestamp(T0 + timedelta(hours=1))]
    first_hour = df[df["ts"] < T0 + timedelta(hours=1)]["power_kw"].mean()
    assert out["power_kw"].iloc[0] == pytest.approx(first_hour)
    # Id/categorical columns are carried, not averaged.
    assert out["asset_id"].iloc[0] == WIND_ASSET
    assert out["operating_state"].iloc[0] == OperatingState.NORMAL.value
    assert out["status_code"].iloc[0] == 1


def test_resample_drops_empty_bins(store):
    df = telemetry_store.load_telemetry(WIND_ASSET)
    gapped = pd.concat(
        [df[df["ts"] < T0 + timedelta(hours=1)], df[df["ts"] >= T0 + timedelta(hours=3)]],
        ignore_index=True,
    )
    out = telemetry_store.resample(gapped, 60, "mean")
    assert pd.Timestamp(T0 + timedelta(hours=1)) not in set(out["ts"])
    assert pd.Timestamp(T0 + timedelta(hours=3)) in set(out["ts"])


def test_resample_per_column_overrides_and_validation(store):
    df = telemetry_store.load_telemetry(WIND_ASSET, end=T0 + timedelta(minutes=50))
    out = telemetry_store.resample(df, 60, {"power_kw": "max", "wind_speed_ms": "min"})
    assert out["power_kw"].iloc[0] == df["power_kw"].max()
    assert out["wind_speed_ms"].iloc[0] == df["wind_speed_ms"].min()
    # Unlisted numeric columns fall back to mean.
    assert out["gearbox_oil_temp_c"].iloc[0] == pytest.approx(df["gearbox_oil_temp_c"].mean())

    with pytest.raises(ValueError):
        telemetry_store.resample(df, 0, "mean")
    with pytest.raises(ValueError):
        telemetry_store.resample(df, 60, "nonsense")
    with pytest.raises(ValueError):
        telemetry_store.resample(df.drop(columns=["ts"]), 60, "mean")


def test_resample_empty_frame(store):
    df = telemetry_store.load_telemetry(WIND_ASSET).iloc[0:0]
    assert telemetry_store.resample(df, 60, "mean").empty


# ---------------------------------------------------------------------------
# State cache
# ---------------------------------------------------------------------------


def _asset_state(asset_id: str = WIND_ASSET, health: float = 58.2) -> AssetState:
    return AssetState(
        asset_id=asset_id,
        asset_type=AssetType.WIND_TURBINE,
        name="Turbine 01",
        site="kutch-wind",
        as_of=T0 + timedelta(hours=23),
        health_score=health,
        operating_state=OperatingState.NORMAL,
        power_kw=1284.0,
        expected_power_kw=1417.0,
        capacity_factor=0.64,
        data_freshness_s=14.0,
    )


def test_asset_state_roundtrip(store):
    assert state_store.load_asset_state(WIND_ASSET) is None

    path = state_store.save_asset_state(_asset_state())
    assert path.is_file()

    loaded = state_store.load_asset_state(WIND_ASSET)
    assert loaded is not None
    assert loaded.health_score == pytest.approx(58.2)
    assert loaded.as_of == T0 + timedelta(hours=23)
    assert loaded.operating_state is OperatingState.NORMAL
    assert loaded.anomaly is None  # not computed stays null, never a placeholder

    state_store.save_asset_state(_asset_state(health=61.0))
    assert state_store.load_asset_state(WIND_ASSET).health_score == pytest.approx(61.0)


def test_load_all_asset_states_and_clear(store):
    state_store.save_asset_state(_asset_state(WIND_ASSET))
    state_store.save_asset_state(_asset_state(SOLAR_ASSET))
    states = state_store.load_all_asset_states()
    assert [s.asset_id for s in states] == [WIND_ASSET, SOLAR_ASSET]  # fleet order
    assert state_store.list_cached_states() == sorted([WIND_ASSET, SOLAR_ASSET])

    (state_store.state_dir() / "broken.json").write_text("{not json", encoding="utf-8")
    assert len(state_store.load_all_asset_states()) == 2  # unreadable file skipped

    assert state_store.clear_asset_states() == 3
    assert state_store.load_all_asset_states() == []


def test_load_asset_state_rejects_corrupt_cache(store):
    state_store.state_dir().mkdir(parents=True, exist_ok=True)
    state_store.asset_state_path(WIND_ASSET).write_text('{"asset_id": "WT-001"}', encoding="utf-8")
    with pytest.raises(DataUnavailable) as excinfo:
        state_store.load_asset_state(WIND_ASSET)
    assert excinfo.value.code == "state_invalid"


# ---------------------------------------------------------------------------
# JSON artifacts
# ---------------------------------------------------------------------------


def test_json_artifact_roundtrip(store):
    assert state_store.load_json_artifact("evaluation") is None

    payload = {
        "computed_at": T0,
        "assets": 42,
        "detection": {"event_recall": 0.88, "median_lead_time_days": 6.4},
        "not_evaluated": None,
    }
    path = state_store.save_json_artifact("evaluation", payload)
    assert path == state_store.artifact_root() / "evaluation.json"

    loaded = state_store.load_json_artifact("evaluation")
    assert loaded is not None
    assert loaded["assets"] == 42
    assert loaded["computed_at"] == "2026-09-01T00:00:00Z"
    assert loaded["not_evaluated"] is None
    assert json.loads(path.read_text(encoding="utf-8"))["detection"]["event_recall"] == 0.88


def test_json_artifact_nested_name_and_pydantic_model(store):
    state_store.save_json_artifact("models/wind_expected_power.json", _asset_state())
    loaded = state_store.load_json_artifact("models/wind_expected_power")
    assert loaded is not None
    assert loaded["asset_id"] == WIND_ASSET
    assert loaded["asset_type"] == "wind_turbine"


def test_json_artifact_rejects_path_escape(store):
    with pytest.raises(ValueError):
        state_store.artifact_path("../../evil")
    with pytest.raises(ValueError):
        state_store.artifact_path("   ")


def test_json_artifact_rejects_non_object(store):
    state_store.save_json_artifact("alist", [1, 2, 3])
    with pytest.raises(TypeError, match="not a JSON object"):
        state_store.load_json_artifact("alist")


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_load_fleet_latest_is_fast_for_full_fleet(tmp_path, capsys):
    """42 assets, one query. Target is ~250 ms; the assert is loose to avoid CI flakiness."""
    data_root = tmp_path / "fleet"
    (data_root / "telemetry").mkdir(parents=True)
    telemetry_store.set_data_root(data_root)
    try:
        from rai.config import FLEET

        for asset in FLEET:
            if asset.asset_type is AssetType.WIND_TURBINE:
                frame = _wind_frame(asset.asset_id, rows=1008)  # 7 days at 10 min
            else:
                frame = _solar_frame(asset.asset_id, rows=672)  # 7 days at 15 min
            telemetry_store.write_telemetry(asset.asset_id, frame)

        telemetry_store.load_fleet_latest()  # warm the connection
        timings = []
        for _ in range(3):
            t0 = time.perf_counter()
            df = telemetry_store.load_fleet_latest()
            timings.append((time.perf_counter() - t0) * 1000.0)

        assert len(df) == len(FLEET)
        best = min(timings)
        with capsys.disabled():
            print(
                f"\nload_fleet_latest: {len(FLEET)} assets, "
                f"{sum(len(_wind_frame('x', rows=0)) for _ in [0])}"
                f"{42} files; timings ms = "
                + ", ".join(f"{t:.1f}" for t in timings)
            )
        assert best < 2000.0
    finally:
        telemetry_store.reset_connection()
        telemetry_store.set_data_root(telemetry_store.config.SYNTHETIC)
