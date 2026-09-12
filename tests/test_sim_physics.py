"""Physical plausibility tests for the simulator.

These run against the generated dataset when it exists and skip cleanly when it does not,
so the suite stays green on a fresh clone. They check the properties a domain reviewer would
check first: does the power curve have the right shape, are capacity factors believable, is
night dark, and — most importantly — is each injected fault actually present in the data
*after conditioning on the weather that produced it*.

Raw before/after means are confounded by wind conditions and prove nothing. Every degradation
assertion here is condition-matched, which is the same discipline the detection models use.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rai.config import get_asset
from rai.sim.wind import expected_power_reference
from rai.store import DataUnavailable, load_events, load_telemetry

pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")


def _telemetry(asset_id: str) -> pd.DataFrame:
    try:
        return load_telemetry(asset_id)
    except (DataUnavailable, FileNotFoundError):
        pytest.skip("synthetic dataset not generated; run scripts/generate_data.py")


def _event(asset_id: str):
    events = [e for e in load_events(asset_id)]
    if not events:
        pytest.skip(f"no injected event for {asset_id}")
    return events[0]


# --------------------------------------------------------------------------- wind physics


def test_power_curve_has_the_right_shape():
    df = _telemetry("WT-001")
    run = df[(df.operating_state == "normal") & df.power_kw.notna() & df.wind_speed_ms.notna()]
    binned = run.groupby(
        pd.cut(run.wind_speed_ms, [3, 5, 7, 9, 11, 13, 16, 20]), observed=True
    ).power_kw.mean()

    # Rising through the cubic region.
    rising = binned.loc[binned.index[:4]]
    assert rising.is_monotonic_increasing, f"power should rise below rated:\n{binned}"

    # Flat plateau from rated to cut-out: the controller pitches to hold rated power.
    plateau = binned.loc[binned.index[-2:]]
    assert plateau.min() > 1800, f"plateau should sit near rated 2000 kW:\n{binned}"
    assert plateau.max() <= 2050


def test_wind_capacity_factors_are_believable():
    factors = []
    for i in range(1, 19):
        df = _telemetry(f"WT-{i:03d}")
        factors.append(df.power_kw.mean() / get_asset(f"WT-{i:03d}").rated_power_kw)
    arr = np.array(factors)
    assert 0.20 < np.median(arr) < 0.50, f"median wind CF {np.median(arr):.3f} is implausible"
    assert arr.min() > 0.10


def test_wake_makes_row_b_yield_less_than_row_a():
    def mean_cf(ids):
        return np.mean([_telemetry(a).power_kw.mean() / 2000.0 for a in ids])

    row_a = mean_cf([f"WT-{i:03d}" for i in range(1, 10)])
    row_b = mean_cf([f"WT-{i:03d}" for i in (10, 12, 13, 16, 18)])  # healthy row-b only
    assert row_b < row_a, "downstream row should sit in the wake and yield less"


def test_component_temperatures_exceed_ambient_under_load():
    df = _telemetry("WT-001")
    loaded = df[(df.power_kw > 1000) & df.gearbox_oil_temp_c.notna()]
    assert (loaded.gearbox_oil_temp_c > loaded.ambient_temp_c).mean() > 0.98
    assert (loaded.generator_winding_temp_c > loaded.gearbox_oil_temp_c).mean() > 0.80


# --------------------------------------------------------------------------- solar physics


def test_solar_is_dark_at_night_and_peaks_near_noon():
    df = _telemetry("INV-001")
    local_hour = df.ts.dt.tz_convert("Asia/Kolkata").dt.hour
    profile = df.groupby(local_hour).ac_power_kw.mean()
    assert profile.loc[[0, 1, 2, 3, 22, 23]].max() == 0.0, "plant must be dark at night"
    assert 10 <= int(profile.idxmax()) <= 14, f"peak at {profile.idxmax()}h is not near noon"


def test_solar_capacity_factors_are_believable():
    factors = [_telemetry(f"INV-{i:03d}").ac_power_kw.mean() / 250.0 for i in range(1, 25)]
    arr = np.array(factors)
    assert 0.12 < np.median(arr) < 0.30, f"median solar CF {np.median(arr):.3f} is implausible"


def test_dc_power_is_consistent_with_voltage_and_current():
    df = _telemetry("INV-001")
    day = df[(df.dc_power_kw > 10) & (df.dc_voltage_v > 100)].copy()
    implied_kw = day.dc_voltage_v * day.dc_current_a / 1000.0
    relative_error = ((implied_kw - day.dc_power_kw).abs() / day.dc_power_kw).median()
    assert relative_error < 0.02, f"V*I should reconstruct P, median error {relative_error:.3%}"


# ------------------------------------------------- fault presence, condition-matched


def test_gearbox_wear_is_present_after_conditioning_on_load():
    """WT-017's flagship fault must show in vibration once load is matched."""
    df = _telemetry("WT-017")
    event = _event("WT-017")
    onset = pd.Timestamp(event.onset)
    assert event.scenario == "gearbox_bearing_wear"

    run = df[(df.operating_state == "normal") & df.power_kw.notna()].copy()
    run["load_bin"] = pd.cut(run.power_kw, [0, 400, 800, 1200, 1600, 2100])
    healthy = run[run.ts < onset]
    faulted = run[run.ts >= run.ts.max() - pd.Timedelta(days=4)]

    compared = 0
    for load_bin in healthy.load_bin.cat.categories:
        h = healthy[healthy.load_bin == load_bin]
        f = faulted[faulted.load_bin == load_bin]
        if len(h) < 30 or len(f) < 10:
            continue
        compared += 1
        assert f.drivetrain_vibration_mms.mean() > h.drivetrain_vibration_mms.mean(), (
            f"vibration should be elevated at matched load {load_bin}"
        )
    assert compared >= 2, "not enough matched load bins to compare"


def test_gearbox_wear_raises_oil_temperature_above_ambient_matched_baseline():
    df = _telemetry("WT-017")
    onset = pd.Timestamp(_event("WT-017").onset)
    run = df[(df.operating_state == "normal") & df.gearbox_oil_temp_c.notna()].copy()
    run["rise"] = run.gearbox_oil_temp_c - run.ambient_temp_c
    run["load_bin"] = pd.cut(run.power_kw, [0, 500, 1000, 1500, 2100])

    healthy = run[run.ts < onset]
    faulted = run[run.ts >= run.ts.max() - pd.Timedelta(days=4)]
    for load_bin in healthy.load_bin.cat.categories:
        h, f = healthy[healthy.load_bin == load_bin], faulted[faulted.load_bin == load_bin]
        if len(h) < 30 or len(f) < 10:
            continue
        assert f.rise.mean() > h.rise.mean(), f"oil temperature rise elevated at {load_bin}"


def test_anemometer_drift_creates_apparent_underperformance_only():
    """The sensor lies; the machine is fine. That gap is what the system must detect.

    Measured wind reads high, so power falls short of what that wind implies — while the
    mechanical channels stay healthy. A naive monitor raises a drivetrain alarm here.
    """
    df = _telemetry("WT-002")
    event = _event("WT-002")
    assert event.scenario == "anemometer_drift"
    assert event.is_equipment_fault is False

    asset = get_asset("WT-002")
    run = df[(df.operating_state == "normal") & df.power_kw.notna() & df.wind_speed_ms.notna()].copy()
    run["expected_kw"] = expected_power_reference(
        run.wind_speed_ms.to_numpy(), run.air_density.to_numpy(), asset
    )
    run = run[run.expected_kw > 100]
    run["ratio"] = run.power_kw / run.expected_kw

    healthy = run[run.ts < pd.Timestamp(event.onset)]
    drifted = run[run.ts >= run.ts.max() - pd.Timedelta(days=2)]

    assert drifted.ratio.mean() < healthy.ratio.mean() - 0.05, (
        "drifted sensor should make the turbine look like it is underperforming"
    )
    # ...while vibration stays normal, which is the evidence that exonerates the drivetrain.
    assert drifted.drivetrain_vibration_mms.mean() < healthy.drivetrain_vibration_mms.mean() * 1.15


def test_soiling_accumulates_and_depresses_performance_ratio():
    df = _telemetry("INV-023")
    event = _event("INV-023")
    assert event.scenario == "soiling_accumulation"
    day = df[df.poa_wm2 > 100]
    early, late = day.iloc[:300], day.iloc[-300:]
    assert late.soiling_ratio.mean() < early.soiling_ratio.mean() - 0.03
    assert late.performance_ratio.mean() < early.performance_ratio.mean()


def test_string_outage_is_a_step_change_in_dc_current():
    df = _telemetry("INV-007")
    onset = pd.Timestamp(_event("INV-007").onset)
    day = df[(df.poa_wm2 > 300) & df.dc_current_a.notna()]
    before = day[day.ts < onset]
    after = day[day.ts >= onset]
    assert after.dc_current_a.mean() < before.dc_current_a.mean() * 0.97


def test_curtailment_is_flagged_in_operating_state():
    df = _telemetry("WT-008")
    assert (df.operating_state == "curtailed").any(), "curtailment must be visible in state"


# --------------------------------------------------------------------------- ground truth


def test_every_scenario_is_represented_exactly_once():
    events = load_events()
    scenarios = [e.scenario for e in events]
    assert len(scenarios) == len(set(scenarios)), "each scenario should appear once"
    assert len(events) == 12
    equipment = [e for e in events if e.is_equipment_fault]
    assert len(equipment) == 6, "six equipment faults and six non-equipment scenarios"


def test_ground_truth_timestamps_are_ordered_and_timezone_aware():
    for event in load_events():
        assert event.onset.tzinfo is not None
        assert event.onset <= event.detectable_from
        if event.end is not None:
            assert event.detectable_from <= event.end


def test_most_of_the_fleet_is_healthy():
    faulted = {e.asset_id for e in load_events()}
    assert len(faulted) == 12
    assert len(faulted) / 42 < 0.35, "a fleet where most assets are broken is not realistic"


def test_data_has_realistic_gaps():
    df = _telemetry("WT-001")
    missing = df.isna().any(axis=1).mean()
    assert 0.0 < missing < 0.05, f"expected sparse gaps, got {missing:.3%}"
