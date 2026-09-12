"""SYNTHETIC TEST FIXTURES ONLY -- NEVER USE AS EXTERNAL_REAL PVDAQ EVIDENCE.

This module was relocated out of `pvdaq.py` by the Gate 5.6A acquisition audit after the
Gate 5.6 Scientific Auditor found that the original Gate 5.6 run used this generator's
in-repo synthetic output as if it were real NREL PVDAQ telemetry, and that the
`PVLibPhysicsReference` model was validated against it using an algebraically near-identical
formula (a circular "validation"). See:
  - artifacts/evaluation/gate56_invalid_prior_run/invalidation_manifest.json
  - artifacts/evaluation/gate56_audit/gate56_scientific_audit_verdict.md

Everything in this module is 100% synthetically generated (pvlib clear-sky/transposition/
temperature functions plus a hand-rolled cloud-cover Markov process and Gaussian noise). It
may be reused for unit tests that need a deterministic, physically-plausible-looking time
series shape (e.g. testing that a quality filter correctly tags clipping), but its output must
never be labeled EXTERNAL_REAL, never be cited as PVDAQ validation, and never be used as the
"actual power" target for evaluating any physics or empirical model -- doing so silently
reproduces the exact circularity failure this module's relocation exists to prevent.

The system identifiers below (SYS_10, SYS_34, SYS_4, SYS_1199, SYS_1283) are inherited
placeholder labels from the pre-quarantine test suite's fixture shape (5 systems / 3 cohort
roles / >=5 exclusions), NOT real PVDAQ system IDs. Every `name` field is prefixed
"SYNTHETIC FIXTURE (NOT REAL PVDAQ)" so this can never be mistaken for real acquired data.
Real PVDAQ acquisition lives under `artifacts/evaluation/gate56/acquisition/` (manifests,
checksums, candidate/cohort records) and `data/raw/pvdaq/` (downloaded raw parquet files,
mirroring the source S3 key layout byte-for-byte).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from rai.eval.external.solar.pvdaq import (
    GATE56_SEED,
    CohortRole,
    PVDAQSystemMetadata,
    split_system_telemetry,
)

__all__ = [
    "SYNTHETIC_FIXTURE_COHORT",
    "SYNTHETIC_FIXTURE_EXCLUSION_CATALOG",
    "generate_synthetic_solar_fixture",
    "load_synthetic_fixture_cohort",
]


# ---------------------------------------------------------------------------
# Synthetic fixture "cohort" -- fictional systems for unit-test shape only.
# NOT real PVDAQ systems. Every name below is explicitly labeled synthetic.
# ---------------------------------------------------------------------------

SYNTHETIC_FIXTURE_COHORT: dict[str, PVDAQSystemMetadata] = {
    "SYS_10": PVDAQSystemMetadata(
        system_id="SYS_10",
        name="SYNTHETIC FIXTURE (NOT REAL PVDAQ) - fictional commercial rooftop",
        location="Synthetic",
        latitude=39.7407,
        longitude=-105.1686,
        altitude_m=1829.0,
        rated_dc_kw=100.0,
        rated_ac_kw=90.0,
        module_technology="c-Si",
        array_type="fixed_open_rack",
        tilt_deg=20.0,
        azimuth_deg=180.0,
        temp_coefficient_pct_per_c=-0.38,
        inverter_efficiency_nominal=0.965,
        has_poa_pyranometer=True,
        has_ghi_pyranometer=True,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=True,
        cohort_role=CohortRole.TRAIN_SYSTEM,
        selection_rationale="Synthetic unit-test fixture only; not a real acquired system.",
    ),
    "SYS_34": PVDAQSystemMetadata(
        system_id="SYS_34",
        name="SYNTHETIC FIXTURE (NOT REAL PVDAQ) - fictional research testbed",
        location="Synthetic",
        latitude=39.7407,
        longitude=-105.1686,
        altitude_m=1829.0,
        rated_dc_kw=4.2,
        rated_ac_kw=4.0,
        module_technology="c-Si",
        array_type="fixed_open_rack",
        tilt_deg=45.0,
        azimuth_deg=180.0,
        temp_coefficient_pct_per_c=-0.41,
        inverter_efficiency_nominal=0.955,
        has_poa_pyranometer=True,
        has_ghi_pyranometer=True,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=True,
        cohort_role=CohortRole.TRAIN_SYSTEM,
        selection_rationale="Synthetic unit-test fixture only; not a real acquired system.",
    ),
    "SYS_4": PVDAQSystemMetadata(
        system_id="SYS_4",
        name="SYNTHETIC FIXTURE (NOT REAL PVDAQ) - fictional regional rooftop",
        location="Synthetic",
        latitude=39.7392,
        longitude=-104.9903,
        altitude_m=1609.0,
        rated_dc_kw=10.0,
        rated_ac_kw=9.2,
        module_technology="c-Si",
        array_type="fixed_roof",
        tilt_deg=40.0,
        azimuth_deg=180.0,
        temp_coefficient_pct_per_c=-0.39,
        inverter_efficiency_nominal=0.960,
        has_poa_pyranometer=True,
        has_ghi_pyranometer=True,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=False,
        cohort_role=CohortRole.VAL_SYSTEM,
        selection_rationale="Synthetic unit-test fixture only; not a real acquired system.",
    ),
    "SYS_1199": PVDAQSystemMetadata(
        system_id="SYS_1199",
        name="SYNTHETIC FIXTURE (NOT REAL PVDAQ) - fictional held-out commercial array",
        location="Synthetic",
        latitude=38.8951,
        longitude=-77.0364,
        altitude_m=20.0,
        rated_dc_kw=148.0,
        rated_ac_kw=135.0,
        module_technology="c-Si",
        array_type="fixed_roof",
        tilt_deg=15.0,
        azimuth_deg=190.0,
        temp_coefficient_pct_per_c=-0.40,
        inverter_efficiency_nominal=0.970,
        has_poa_pyranometer=True,
        has_ghi_pyranometer=False,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=False,
        cohort_role=CohortRole.HELD_OUT_TEST_SYSTEM,
        selection_rationale="Synthetic unit-test fixture only; not a real acquired system.",
    ),
    "SYS_1283": PVDAQSystemMetadata(
        system_id="SYS_1283",
        name="SYNTHETIC FIXTURE (NOT REAL PVDAQ) - fictional held-out array",
        location="Synthetic",
        latitude=28.3861,
        longitude=-80.7539,
        altitude_m=10.0,
        rated_dc_kw=10.0,
        rated_ac_kw=9.0,
        module_technology="c-Si",
        array_type="fixed_open_rack",
        tilt_deg=28.0,
        azimuth_deg=180.0,
        temp_coefficient_pct_per_c=-0.38,
        inverter_efficiency_nominal=0.962,
        has_poa_pyranometer=True,
        has_ghi_pyranometer=True,
        has_module_temperature=True,
        has_ambient_temperature=True,
        has_wind_speed=True,
        cohort_role=CohortRole.HELD_OUT_TEST_SYSTEM,
        selection_rationale="Synthetic unit-test fixture only; not a real acquired system.",
    ),
}

SYNTHETIC_FIXTURE_EXCLUSION_CATALOG: list[dict[str, str]] = [
    {
        "system_id": "SYS_1",
        "name": "SYNTHETIC FIXTURE EXCLUSION (not a real PVDAQ system)",
        "status": "EXCLUDED",
        "rationale": "Synthetic fixture-shape placeholder for unit-test exclusion-catalog tests.",
    },
    {
        "system_id": "SYS_12",
        "name": "SYNTHETIC FIXTURE EXCLUSION (not a real PVDAQ system)",
        "status": "EXCLUDED",
        "rationale": "Synthetic fixture-shape placeholder for unit-test exclusion-catalog tests.",
    },
    {
        "system_id": "SYS_50",
        "name": "SYNTHETIC FIXTURE EXCLUSION (not a real PVDAQ system)",
        "status": "EXCLUDED",
        "rationale": "Synthetic fixture-shape placeholder for unit-test exclusion-catalog tests.",
    },
    {
        "system_id": "SYS_1200",
        "name": "SYNTHETIC FIXTURE EXCLUSION (not a real PVDAQ system)",
        "status": "EXCLUDED",
        "rationale": "Synthetic fixture-shape placeholder for unit-test exclusion-catalog tests.",
    },
    {
        "system_id": "SYS_1404",
        "name": "SYNTHETIC FIXTURE EXCLUSION (not a real PVDAQ system)",
        "status": "EXCLUDED",
        "rationale": "Synthetic fixture-shape placeholder for unit-test exclusion-catalog tests.",
    },
]


def generate_synthetic_solar_fixture(
    meta: PVDAQSystemMetadata,
    start_date: str = "2024-06-01",
    days: int = 90,
    freq: str = "15min",
    seed: int = GATE56_SEED,
) -> pd.DataFrame:
    """Generate a synthetic PV telemetry-shaped DataFrame for unit tests ONLY.

    NEVER label this output EXTERNAL_REAL. NEVER use it as the "actual power" target
    to validate a physics or empirical model -- the underlying formula is closely related
    to standard physics-informed expected-power formulas, so doing so silently reproduces
    a circular validation (see module docstring).
    """
    rng = np.random.default_rng(seed + int(meta.latitude * 100))

    times = pd.date_range(start_date, periods=days * 24 * 4, freq=freq, tz="UTC")
    n_pts = len(times)

    solpos = pvlib.solarposition.get_solarposition(
        time=times,
        latitude=meta.latitude,
        longitude=meta.longitude,
        altitude=meta.altitude_m,
    )
    apparent_elevation = solpos["apparent_elevation"].to_numpy()
    apparent_zenith = solpos["apparent_zenith"].to_numpy()
    azimuth = solpos["azimuth"].to_numpy()

    site_location = pvlib.location.Location(
        meta.latitude, meta.longitude, tz="UTC", altitude=meta.altitude_m
    )
    cs = site_location.get_clearsky(times, model="ineichen")
    ghi_cs = cs["ghi"].to_numpy()
    dni_cs = cs["dni"].to_numpy()
    dhi_cs = cs["dhi"].to_numpy()

    cloud_drift = np.zeros(n_pts)
    c_val = 0.0
    for i in range(n_pts):
        if i % 96 == 0:
            c_val = rng.uniform(0.0, 0.4)
        c_val = np.clip(c_val + rng.normal(0.0, 0.05), 0.0, 0.85)
        cloud_drift[i] = c_val

    ghi_act = np.clip(ghi_cs * (1.0 - 0.7 * cloud_drift) + rng.normal(0, 5.0, n_pts), 0.0, 1400.0)
    dni_act = np.clip(dni_cs * (1.0 - 0.95 * cloud_drift) + rng.normal(0, 10.0, n_pts), 0.0, 1200.0)
    dhi_act = np.clip(dhi_cs * (1.0 - 0.3 * cloud_drift) + rng.normal(0, 5.0, n_pts), 0.0, 800.0)

    dni_extra = pvlib.irradiance.get_extra_radiation(times).to_numpy()
    poa_components = pvlib.irradiance.get_total_irradiance(
        surface_tilt=meta.tilt_deg,
        surface_azimuth=meta.azimuth_deg,
        solar_zenith=apparent_zenith,
        solar_azimuth=azimuth,
        dni=dni_act,
        ghi=ghi_act,
        dhi=dhi_act,
        dni_extra=dni_extra,
        model="perez",
    )
    poa_global = np.maximum(np.asarray(poa_components["poa_global"]), 0.0)

    night_mask = (apparent_elevation <= 5.0) | (poa_global < 20.0)
    poa_global[night_mask] = 0.0
    ghi_act[night_mask] = 0.0

    day_of_year = times.dayofyear.to_numpy()
    seasonal_temp = 20.0 + 8.0 * np.sin(2 * np.pi * (day_of_year - 80) / 365.25)
    diurnal_temp = 7.0 * np.sin(2 * np.pi * (times.hour * 60 + times.minute - 540) / 1440)
    ambient_temp = seasonal_temp + diurnal_temp + rng.normal(0, 1.2, n_pts)

    wind_speed = np.clip(rng.weibull(2.0, n_pts) * 3.5, 0.2, 20.0)

    sapm_params = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]
    cell_temp = pvlib.temperature.sapm_cell(
        poa_global=poa_global,
        temp_air=ambient_temp,
        wind_speed=wind_speed,
        a=sapm_params["a"],
        b=sapm_params["b"],
        deltaT=sapm_params["deltaT"],
    ).to_numpy()

    dc_eff_temp = 1.0 + (meta.temp_coefficient_pct_per_c / 100.0) * (cell_temp - 25.0)
    raw_dc_power = meta.rated_dc_kw * (poa_global / 1000.0) * dc_eff_temp
    dc_power = np.maximum(raw_dc_power + rng.normal(0, 0.005 * meta.rated_dc_kw, n_pts), 0.0)
    dc_power[night_mask] = 0.0

    inverter_p_norm = np.clip(dc_power / meta.rated_dc_kw, 0.0, 1.5)
    inverter_eff = meta.inverter_efficiency_nominal * (1.0 - 0.02 * (1.0 - inverter_p_norm) ** 2)
    converted_ac = dc_power * inverter_eff

    is_clipping = converted_ac >= (0.98 * meta.rated_ac_kw)
    ac_power = np.minimum(converted_ac, meta.rated_ac_kw)
    ac_power[night_mask] = 0.0

    is_curtailed = np.zeros(n_pts, dtype=bool)
    curtail_day1_start = 96 * 15 + 44
    curtail_day1_end = curtail_day1_start + 16
    is_curtailed[curtail_day1_start:curtail_day1_end] = True
    ac_power[curtail_day1_start:curtail_day1_end] *= 0.50

    curtail_day2_start = 96 * 48 + 48
    curtail_day2_end = curtail_day2_start + 12
    is_curtailed[curtail_day2_start:curtail_day2_end] = True
    ac_power[curtail_day2_start:curtail_day2_end] *= 0.40

    is_gap = np.zeros(n_pts, dtype=bool)
    gap_start = 96 * 30 + 10
    gap_end = gap_start + 8
    is_gap[gap_start:gap_end] = True

    df = pd.DataFrame({
        "timestamp": times,
        "system_id": meta.system_id,
        "solar_elevation_deg": np.round(apparent_elevation, 2),
        "solar_zenith_deg": np.round(apparent_zenith, 2),
        "solar_azimuth_deg": np.round(azimuth, 2),
        "ghi_wm2": np.round(ghi_act, 1),
        "poa_wm2": np.round(poa_global, 1),
        "ambient_temp_c": np.round(ambient_temp, 2),
        "module_temp_c": np.round(cell_temp, 2),
        "wind_speed_ms": np.round(wind_speed, 2),
        "dc_power_kw": np.round(dc_power, 2),
        "ac_power_kw": np.round(ac_power, 2),
        "is_clipping_flag": is_clipping,
        "is_curtailed_flag": is_curtailed,
        "is_data_gap": is_gap,
        "is_synthetic_fixture": True,
    })

    df.loc[df["is_data_gap"], ["poa_wm2", "ghi_wm2", "ac_power_kw", "dc_power_kw"]] = np.nan

    return df


def load_synthetic_fixture_cohort(
    cache_dir: Path | None = None,
    seed: int = GATE56_SEED,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Load synthetic fixture "systems" for unit tests ONLY. NOT external-real data."""
    cohort_data: dict[str, dict[str, pd.DataFrame]] = {}

    for sys_id, meta in SYNTHETIC_FIXTURE_COHORT.items():
        raw_df = generate_synthetic_solar_fixture(meta, seed=seed)
        train_df, val_df, test_df = split_system_telemetry(raw_df)
        cohort_data[sys_id] = {
            "all": raw_df,
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }

    return cohort_data
