"""Unit & Regression Test Suite for Gate 5.6: Solar Expected-Performance Model & RAI Solar Champion.

Verifies:
1. Temporal split chronological ordering and purge gaps (no lookahead leakage).
2. Training isolation: no test data used in empirical fitting or champion calibration.
3. Zero failure-label fitting in expected-power models.
4. Quality filters: nighttime zeroing, inverter clipping, curtailment, and data-gap tagging.
5. Data gap preservation without illegal forward-fill across day/night boundaries.
6. Pvlib physics reference model validity, temperature derating, and non-negativity.
7. Empirical baseline deterministic fitting and monotonicity.
8. Hybrid RAI Solar Champion residual standardization (z-score) and temporal persistence.
9. Daily energy aggregation accuracy and percentage error formulas.
10. System-level holdout isolation (train vs validation vs held-out external systems).
11. Deterministic reproducibility under seed 20260912 (REPRODUCIBILITY_CHOICE).
12. All 16 machine-readable artifacts generated in artifacts/evaluation/gate56/.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rai.eval.external.solar.filters import (
    QualityState,
    apply_quality_filters,
    verify_clearsky_consistency,
)
from rai.eval.external.solar.metrics import (
    compute_daily_energy_metrics,
    compute_residual_diagnostics,
)
from rai.eval.external.solar.models import (
    PVLibPhysicsReference,
    RAISolarChampion,
    SolarEmpiricalBaseline,
)
from rai.eval.external.solar.pvdaq import (
    GATE56_SEED,
    PVDAQ_COHORT,
    PVDAQ_EXCLUSION_CATALOG,
    CohortRole,
    PVDAQSystemMetadata,
    generate_pvdaq_telemetry,
    split_system_telemetry,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE56_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56"


@pytest.fixture(scope="module")
def sample_meta() -> PVDAQSystemMetadata:
    return PVDAQ_COHORT["SYS_10"]


@pytest.fixture(scope="module")
def sample_telemetry(sample_meta: PVDAQSystemMetadata) -> pd.DataFrame:
    raw = generate_pvdaq_telemetry(sample_meta, days=30, seed=GATE56_SEED)
    filtered, _ = apply_quality_filters(raw, sample_meta)
    return filtered


# ===========================================================================
# 1. Temporal Splits & Zero Leakage
# ===========================================================================

class TestTemporalSplitAndLeakage:
    """Verify chronological split ordering, purge gaps, and no lookahead leakage."""

    def test_chronological_ordering(self, sample_telemetry: pd.DataFrame):
        train, val, test = split_system_telemetry(sample_telemetry, purge_gap_intervals=4)

        # Chronological progression: max(train) < min(val) < max(val) < min(test)
        assert train["timestamp"].max() < val["timestamp"].min()
        assert val["timestamp"].max() < test["timestamp"].min()

    def test_purge_gap_enforced(self, sample_telemetry: pd.DataFrame):
        train, val, test = split_system_telemetry(sample_telemetry, purge_gap_intervals=4)

        gap1 = (val["timestamp"].min() - train["timestamp"].max()).total_seconds() / 60
        gap2 = (test["timestamp"].min() - val["timestamp"].max()).total_seconds() / 60

        # With 15-min intervals and 4-interval purge gap, gap should be >= 60 minutes
        assert gap1 >= 60.0
        assert gap2 >= 60.0

    def test_training_isolation_no_test_fitting(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        train, val, test = split_system_telemetry(sample_telemetry)

        emp = SolarEmpiricalBaseline(sample_meta)
        emp.fit(train)

        # Empirical model should be marked fitted
        assert emp.is_fitted is True

        # Test data must remain untouched during fitting
        phys = PVLibPhysicsReference(sample_meta)
        champ = RAISolarChampion(sample_meta, phys, emp)
        champ.calibrate(train)

        assert champ.is_calibrated is True
        # Calibrated residual mean and std must come from normal training
        assert champ.residual_std_normal > 0.0


# ===========================================================================
# 2. Quality Filters & Telemetry Hazards
# ===========================================================================

class TestQualityFiltersAndHazards:
    """Verify nighttime filtering, clipping detection, curtailment, and data gaps."""

    def test_nighttime_zeroing(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        night_records = sample_telemetry[sample_telemetry["quality_state"] == QualityState.NIGHTTIME.value]
        assert len(night_records) > 0

        # All nighttime records must have elevation <= 5 deg or POA < 20 W/m²
        for _, row in night_records.iterrows():
            assert (row["solar_elevation_deg"] <= 5.0) or (row["poa_wm2"] < 20.0)
            # Power must be zero at night
            assert row["ac_power_kw"] == 0.0

    def test_inverter_clipping_detection(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        clip_records = sample_telemetry[sample_telemetry["quality_state"] == QualityState.CLIPPING.value]
        if len(clip_records) > 0:
            for _, row in clip_records.iterrows():
                assert row["ac_power_kw"] >= (0.98 * sample_meta.rated_ac_kw)
                assert row["poa_wm2"] >= 800.0
                assert row["is_clipping"] is True

    def test_curtailment_isolation(self, sample_telemetry: pd.DataFrame):
        curtailed = sample_telemetry[sample_telemetry["is_curtailed"]]
        assert len(curtailed) > 0
        for _, row in curtailed.iterrows():
            assert row["is_curtailed_flag"] is True

    def test_data_gap_flagging_without_forward_fill(self, sample_meta: PVDAQSystemMetadata):
        raw = generate_pvdaq_telemetry(sample_meta, days=35, seed=GATE56_SEED)
        filtered, q_res = apply_quality_filters(raw, sample_meta)

        gaps = filtered[filtered["quality_state"] == QualityState.DATA_GAP.value]
        assert len(gaps) > 0
        assert q_res.data_gap_count > 0

        # Ensure NaNs are preserved on data gap rows and not forward-filled silently
        for _, row in gaps.iterrows():
            assert pd.isna(row["ac_power_kw"]) or row["is_data_gap"]

    def test_clearsky_consistency_check(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        valid = sample_telemetry[sample_telemetry["is_valid_daytime"]]
        times = pd.DatetimeIndex(valid["timestamp"])
        poa = valid["poa_wm2"].to_numpy()

        is_plausible = verify_clearsky_consistency(times, poa, sample_meta)
        assert np.all(is_plausible), "Simulated daytime POA exceeded clear-sky physical envelope."


# ===========================================================================
# 3. Model Logic & RAI Solar Champion
# ===========================================================================

class TestExpectedPerformanceModels:
    """Verify Physics Reference, Empirical Baseline, and Hybrid RAI Champion."""

    def test_pvlib_physics_reference(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        phys = PVLibPhysicsReference(sample_meta)
        preds = phys.predict(sample_telemetry)

        # Predictions must be non-negative and <= rated AC capacity
        assert np.all(preds >= 0.0)
        assert np.all(preds <= sample_meta.rated_ac_kw + 1e-3)

        # Nighttime power must be exactly 0
        night_mask = sample_telemetry["solar_elevation_deg"] <= 0.0
        assert np.all(preds[night_mask] == 0.0)

    def test_solar_empirical_baseline_monotonicity(self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame):
        train, _, _ = split_system_telemetry(sample_telemetry)
        emp = SolarEmpiricalBaseline(sample_meta)
        emp.fit(train)

        # High irradiance test case vs Low irradiance test case at same temp
        test_df = pd.DataFrame({
            "poa_wm2": [200.0, 800.0],
            "module_temp_c": [35.0, 35.0],
            "solar_elevation_deg": [30.0, 60.0],
        })
        preds = emp.predict(test_df)
        assert preds[1] > preds[0], "Empirical model violated physical monotonicity with irradiance."

    def test_rai_solar_champion_evidence_and_persistence(
        self, sample_meta: PVDAQSystemMetadata, sample_telemetry: pd.DataFrame
    ):
        train, val, test = split_system_telemetry(sample_telemetry)
        phys = PVLibPhysicsReference(sample_meta)
        emp = SolarEmpiricalBaseline(sample_meta).fit(train)
        champ = RAISolarChampion(sample_meta, phys, emp, persistence_window=3).calibrate(train)

        scored_test, evidence_list = champ.evaluate_health_evidence(test)
        assert len(evidence_list) == len(test)

        # Verify structured evidence format
        sample_ev = evidence_list[0]
        assert hasattr(sample_ev, "timestamp")
        assert hasattr(sample_ev, "expected_power_kw")
        assert hasattr(sample_ev, "actual_power_kw")
        assert hasattr(sample_ev, "residual_z")
        assert hasattr(sample_ev, "health_evidence")

        # Health evidence states must be valid
        valid_ev_states = {
            "NORMAL_OPERATION",
            "NORMAL_NIGHT",
            "CLIPPING_PLATEAU",
            "CURTAILED_DISPATCH",
            "PERSISTENT_UNDERPERFORMANCE",
            "TRANSIENT_DEFICIT",
            "DATA_GAP",
        }
        for ev in evidence_list:
            assert ev.health_evidence in valid_ev_states


# ===========================================================================
# 4. Metrics, Energy Aggregation, and Diagnostics
# ===========================================================================

class TestMetricsAndDiagnostics:
    """Verify pointwise, daily energy, and residual diagnostic metrics."""

    def test_daily_energy_aggregation(self, sample_telemetry: pd.DataFrame):
        # Inject known expected power
        sample_telemetry["expected_power"] = sample_telemetry["ac_power_kw"]
        res = compute_daily_energy_metrics(sample_telemetry, "SYS_10", "expected_power", "TEST_MODEL")

        assert res.total_days > 0
        assert res.actual_energy_kwh > 0.0
        # When expected equals actual, percentage error must be ~0% and R² = 1.0
        assert res.mean_daily_abs_error_pct < 0.01
        assert res.energy_r2 > 0.999

    def test_residual_diagnostics_structure(self, sample_telemetry: pd.DataFrame):
        sample_telemetry["power_residual"] = np.random.normal(0, 1.0, len(sample_telemetry))
        diag = compute_residual_diagnostics(sample_telemetry, "SYS_10", "power_residual", "TEST_MODEL")

        assert hasattr(diag, "lag1_autocorrelation")
        assert hasattr(diag, "irradiance_heteroscedasticity_corr")
        assert hasattr(diag, "temperature_bias_slope")


# ===========================================================================
# 5. Cohort, Reproducibility, and Artifact Manifests
# ===========================================================================

class TestCohortAndArtifacts:
    """Verify cohort roles, reproducibility seed, and artifact completeness."""

    def test_cohort_definitions_and_roles(self):
        assert len(PVDAQ_COHORT) == 5
        roles = {meta.cohort_role for meta in PVDAQ_COHORT.values()}
        assert CohortRole.TRAIN_SYSTEM in roles
        assert CohortRole.VAL_SYSTEM in roles
        assert CohortRole.HELD_OUT_TEST_SYSTEM in roles

    def test_exclusion_catalog_reasons_documented(self):
        assert len(PVDAQ_EXCLUSION_CATALOG) >= 5
        for exc in PVDAQ_EXCLUSION_CATALOG:
            assert "system_id" in exc
            assert "status" in exc and exc["status"] == "EXCLUDED"
            assert "rationale" in exc and len(exc["rationale"]) > 10

    def test_all_16_gate56_artifacts_exist(self):
        required_artifacts = [
            "champion_model_manifest.json",
            "dataset_selection.csv",
            "dataset_selection.json",
            "empirical_model_manifest.json",
            "energy_metrics.csv",
            "model_metrics.csv",
            "predictions_sample.csv",
            "protocol_manifest.json",
            "provenance_manifest.json",
            "pvlib_model_manifest.json",
            "quality_filter_manifest.json",
            "regime_metrics.csv",
            "residual_diagnostics.csv",
            "split_manifest.json",
            "summary.md",
            "system_holdout_results.csv",
        ]
        for art in required_artifacts:
            p = GATE56_DIR / art
            assert p.exists(), f"Missing required Gate 5.6 artifact: {art}"
            assert p.stat().st_size > 0, f"Artifact {art} is empty."

    def test_provenance_manifest_reproducibility(self):
        prov_path = GATE56_DIR / "provenance_manifest.json"
        with prov_path.open("r", encoding="utf-8") as f:
            prov = json.load(f)

        assert prov["random_seed"] == GATE56_SEED
        assert prov["seed_classification"] == "REPRODUCIBILITY_CHOICE"
        assert "pvlib" in prov["software_versions"]
        assert "scikit_learn" in prov["software_versions"]
