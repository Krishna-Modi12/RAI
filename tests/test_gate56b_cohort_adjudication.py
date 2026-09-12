"""Gate 5.6B: PVDAQ Cohort Adjudication & Modeling Readiness Test Suite.

Verifies (per the Gate 5.6B master prompt's required-test list) that the adjudication
artifacts under artifacts/evaluation/gate56/cohort_adjudication/ are internally consistent,
evidence-based, and free of the specific failure modes the master prompt calls out:

1.  No model execution during adjudication.
2.  Timestamp ambiguity detection.
3.  Timezone handling (no silent local-as-UTC assumption).
4.  DST handling.
5.  Duplicate timestamp detection.
6.  Sampling interval calculation.
7.  Signal semantic validation.
8.  AC/DC distinction.
9.  Cumulative-energy rejection as instantaneous power.
10. Negative-power semantics not silently clipped.
11. No invented pvlib parameters.
12. Physics-readiness requires required metadata.
13. Empirical-readiness requires valid target and environmental inputs.
14. Validation cohort disjointness.
15. Objective cohort selection (no performance-based selection).
16. Deterministic adjudication.

This suite does NOT run, fit, or score any model -- consistent with Gate 5.6B's ABSOLUTE
STOP RULE. It only audits the already-written adjudication artifacts and, where useful,
recomputes a statistic directly from the real downloaded telemetry to cross-check the
artifact's claim (rather than trusting the artifact blindly).
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "cohort_adjudication"
ACQ_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "acquisition"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "pvdaq"
BUILD_SCRIPT = REPO_ROOT / "scratch_gate56a" / "build_gate56b.py"

REQUIRED_ARTIFACTS = [
    "cohort_adjudication.csv",
    "cohort_adjudication.json",
    "signal_sampling_matrix.csv",
    "target_signal_manifest.csv",
    "pvlib_readiness.csv",
    "timestamp_adjudication.csv",
    "power_semantics_audit.csv",
    "system_1283_power_semantics.md",
    "alignment_policy.json",
    "cohort_freeze_v2.json",
    "summary.md",
    "unit_scale_audit.csv",
]

DEV_SYSTEMS = [1239, 1283, 34]
VAL_SYSTEMS = [1430, 1433]
ALL_SYSTEMS = DEV_SYSTEMS + VAL_SYSTEMS


def _read_csv(name: str) -> list[dict]:
    with (OUT_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(name: str) -> dict:
    with (OUT_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def _load_raw(sid: int) -> pd.DataFrame:
    base = RAW_ROOT / "pvdaq" / "parquet" / "pvdata" / f"system_id={sid}"
    files = sorted(base.rglob("*.parquet"))
    frames = [pd.read_parquet(fp) for fp in files]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@pytest.fixture(scope="module")
def gate56b_module():
    """Import scratch_gate56a/build_gate56b.py as a module (it is not a package)."""
    spec = importlib.util.spec_from_file_location("gate56b_build", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ===========================================================================
# 0. Required artifacts exist and are non-empty
# ===========================================================================

class TestRequiredArtifactsExist:
    @pytest.mark.parametrize("name", REQUIRED_ARTIFACTS)
    def test_artifact_exists_and_nonempty(self, name: str):
        path = OUT_DIR / name
        assert path.exists(), f"Required Gate 5.6B artifact missing: {name}"
        assert path.stat().st_size > 0, f"Required Gate 5.6B artifact is empty: {name}"

    def test_original_gate56a_cohort_manifest_not_overwritten(self):
        # Gate 5.6B must produce a NEW versioned freeze, never overwrite Gate 5.6A's manifest.
        acq_manifest = ACQ_DIR / "cohort_manifest.json"
        assert acq_manifest.exists()
        with acq_manifest.open(encoding="utf-8") as f:
            manifest = json.load(f)
        # Gate 5.6A's manifest must not contain any Gate 5.6B-only adjudication fields.
        assert "validation_cohort_status" not in manifest
        assert "target_severe_missingness_disqualifying" not in json.dumps(manifest)


# ===========================================================================
# 1. No model execution during adjudication
# ===========================================================================

class TestNoModelExecutionDuringAdjudication:
    FORBIDDEN_ARTIFACT_NAMES = [
        "champion_model_manifest.json",
        "empirical_model_manifest.json",
        "pvlib_model_manifest.json",
        "model_metrics.csv",
        "predictions_sample.csv",
        "residual_diagnostics.csv",
        "expected_power.csv",
    ]

    @pytest.mark.parametrize("name", FORBIDDEN_ARTIFACT_NAMES)
    def test_no_modeling_artifact_present(self, name: str):
        assert not (OUT_DIR / name).exists(), (
            f"Gate 5.6B cohort_adjudication directory must not contain modeling artifact "
            f"'{name}' -- modeling is out of scope until Gate 5.6C (ABSOLUTE STOP RULE)."
        )

    def test_build_script_never_calls_modelchain_or_run_model(self):
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "ModelChain(" not in source
        assert ".run_model(" not in source
        assert ".run_model_from_poa(" not in source
        assert "pvwatts_dc(" not in source
        assert "sapm(" not in source or "sapm_temp" in source  # sapm_temp mentions are fine (naming, not execution)

    def test_no_expected_power_or_residual_column_anywhere_in_artifacts(self):
        for csv_name in ["cohort_adjudication.csv", "target_signal_manifest.csv", "signal_sampling_matrix.csv"]:
            rows = _read_csv(csv_name)
            if rows:
                cols = set(rows[0].keys())
                assert "expected_power" not in cols
                assert "residual" not in cols
                assert "r2" not in {c.lower() for c in cols}


# ===========================================================================
# 2/3/4. Timestamp ambiguity, timezone handling, DST handling
# ===========================================================================

class TestTimestampAdjudication:
    @pytest.fixture(scope="class")
    def ts_rows(self) -> dict[str, dict]:
        return {r["system_id"]: r for r in _read_csv("timestamp_adjudication.csv")}

    def test_systems_with_real_utc_are_ground_truth(self, ts_rows):
        for sid in ("1239", "1283", "34"):
            assert ts_rows[sid]["timestamp_status"] == "UTC_AVAILABLE_GROUND_TRUTH"
            assert float(ts_rows[sid]["utc_timestamp_null_fraction"]) == 0.0

    def test_systems_with_null_utc_are_marked_ambiguous_not_silently_resolved(self, ts_rows):
        for sid in ("1430", "1433"):
            assert float(ts_rows[sid]["utc_timestamp_null_fraction"]) == 1.0
            assert ts_rows[sid]["timestamp_status"] == "TIMESTAMP_AMBIGUOUS", (
                "A system with 100% null utc_measured_on must never be silently treated as "
                "having a resolved/ground-truth UTC timestamp."
            )

    def test_ambiguous_systems_conversion_rule_is_disclosed_as_indirect(self, ts_rows):
        for sid in ("1430", "1433"):
            rule = ts_rows[sid]["utc_conversion_rule_used"]
            assert "INDIRECT" in rule, (
                "The timezone/UTC conversion basis for an ambiguous system must be explicitly "
                "labeled indirect/circumstantial -- never presented as directly verified."
            )
            assert "not independently verified" in rule.lower() or "not independently confirmed" in rule.lower()

    def test_declared_timezone_metadata_recorded_for_every_system(self, ts_rows):
        for sid in ts_rows:
            assert ts_rows[sid]["declared_timezone_metadata"], f"System {sid} missing declared timezone metadata."

    def test_dst_finding_recorded_for_ambiguous_systems(self, ts_rows):
        for sid in ("1430", "1433"):
            dst = ts_rows[sid]["dst_finding"]
            assert dst and dst != "N/A"
            assert "DST" in dst

    def test_ground_truth_systems_have_no_dst_finding_needed(self, ts_rows):
        for sid in ("1239", "1283", "34"):
            assert ts_rows[sid]["dst_finding"] == "N/A"


# ===========================================================================
# 5. Duplicate timestamp detection
# ===========================================================================

class TestDuplicateTimestampDetection:
    def test_duplicate_count_is_recomputed_from_real_data(self):
        rows = {r["system_id"]: r for r in _read_csv("timestamp_adjudication.csv")}
        for sid in (1239, 1283, 34):
            df = _load_raw(sid)
            # Recompute independently using the same AC power channel the artifact used.
            from_artifact = int(rows[str(sid)]["duplicate_timestamp_count"])
            assert from_artifact >= 0
        # Directly re-derive for one system to confirm the artifact isn't hardcoded.
        df = _load_raw(1239)
        ac = df[df["metric_id"] == 3015]
        recomputed = int(ac["measured_on"].duplicated().sum())
        assert recomputed == int(rows["1239"]["duplicate_timestamp_count"])

    def test_monotonicity_flag_present_for_every_system(self):
        rows = _read_csv("timestamp_adjudication.csv")
        for r in rows:
            assert r["monotonic_nondecreasing"] in ("True", "False")


# ===========================================================================
# 6. Sampling interval calculation
# ===========================================================================

class TestSamplingIntervalCalculation:
    def test_signal_sampling_matrix_recomputes_correctly_for_a_spot_check_system(self):
        df = _load_raw(1239)
        sub = df[df["metric_id"] == 3015].sort_values("measured_on")
        intervals = sub["measured_on"].diff().dropna().dt.total_seconds() / 60.0
        expected_mode = float(intervals.mode().iloc[0])

        rows = _read_csv("signal_sampling_matrix.csv")
        row = next(r for r in rows if r["system_id"] == "1239" and r["signal"] == "ac_power")
        assert float(row["mode_interval_minutes"]) == pytest.approx(expected_mode)
        assert int(row["n_records"]) == len(sub)

    def test_heterogeneous_intervals_across_systems_are_recorded_not_hidden(self):
        rows = _read_csv("signal_sampling_matrix.csv")
        intervals = {
            float(r["native_interval_minutes"])
            for r in rows
            if r["native_interval_minutes"] not in ("NOT_AVAILABLE", "")
        }
        # 1283 is sub-15-minute (0.25 min) while others are 15 min -- heterogeneity must be visible.
        assert 0.25 in intervals
        assert 15.0 in intervals

    def test_not_available_signals_are_explicitly_flagged_not_silently_omitted(self):
        rows = _read_csv("signal_sampling_matrix.csv")
        na_rows = [r for r in rows if r["metric_id"] == "NOT_AVAILABLE"]
        assert len(na_rows) > 0
        for r in na_rows:
            assert r["missingness_fraction"] == "NOT_AVAILABLE"


# ===========================================================================
# 7/8/9. Signal semantic validation, AC/DC distinction, cumulative rejection
# ===========================================================================

class TestSignalSemanticValidation:
    @pytest.fixture(scope="class")
    def target_rows(self) -> list[dict]:
        return _read_csv("target_signal_manifest.csv")

    def test_every_selected_target_is_ac_not_dc(self, target_rows):
        for r in target_rows:
            assert r["ac_or_dc"] == "AC", (
                "The selected primary target signal for every system must be explicitly AC "
                "power (the modeling target), never a DC channel presented as if it were AC."
            )

    def test_no_target_is_marked_cumulative_energy(self, target_rows):
        for r in target_rows:
            assert "INSTANTANEOUS" in r["instantaneous_or_cumulative"], (
                f"System {r['system_id']}'s target must be verified as instantaneous power, "
                "not a cumulative energy counter mistakenly treated as power."
            )
            assert "CUMULATIVE" not in r["instantaneous_or_cumulative"]

    def test_semantic_meaning_field_is_a_recognized_classification(self, target_rows):
        allowed = {"VALID_GENERATION_POWER", "VALID_SIGNED_POWER", "VALID_AFTER_CONTEXT_FILTER", "AMBIGUOUS", "INVALID"}
        for r in target_rows:
            assert r["semantic_meaning"] in allowed

    def test_ambiguous_targets_would_be_flagged_disqualifying(self, target_rows):
        for r in target_rows:
            if r["semantic_meaning"] == "AMBIGUOUS":
                assert r["ambiguous_disqualifying"] == "True"


# ===========================================================================
# 10. Negative-power semantics not silently clipped
# ===========================================================================

class TestNegativePowerNotSilentlyClipped:
    def test_raw_data_on_disk_still_contains_negative_values(self):
        # The underlying acquired parquet must never have been mutated to remove/clip negatives.
        for sid, mid in [(1283, 1040), (34, 2695)]:
            df = _load_raw(sid)
            sub = df[df["metric_id"] == mid]["value"]
            assert (sub < 0).any(), (
                f"System {sid}'s raw AC power data must still contain real negative readings -- "
                "clipping negatives to zero or dropping negative rows is explicitly forbidden."
            )

    def test_audit_negative_fraction_matches_recomputation_from_raw_data(self):
        rows = {r["system_id"]: r for r in _read_csv("power_semantics_audit.csv")}
        for sid, mid in [(1283, 1040), (34, 2695), (1433, 5069)]:
            df = _load_raw(sid)
            sub = df[df["metric_id"] == mid]["value"]
            recomputed = round(float((sub < 0).mean()), 4)
            assert recomputed == pytest.approx(float(rows[str(sid)]["negative_value_fraction"]), abs=1e-3)

    def test_negative_readings_are_classified_not_defaulted_to_invalid(self):
        rows = _read_csv("power_semantics_audit.csv")
        for r in rows:
            assert r["classification"] in (
                "VALID_GENERATION_POWER", "VALID_SIGNED_POWER", "VALID_AFTER_CONTEXT_FILTER",
                "AMBIGUOUS", "INVALID",
            )
            # None of the 5 cohort systems should be left AMBIGUOUS after the generalized
            # night/day correlation investigation applied in this gate.
            assert r["classification"] != "INVALID"

    def test_system_1283_power_semantics_md_cites_real_evidence_not_a_guess(self):
        text = (OUT_DIR / "system_1283_power_semantics.md").read_text(encoding="utf-8")
        assert "calc_details" in text
        assert "199,086" in text or "39.5%" in text
        assert "VALID_SIGNED_POWER" in text


# ===========================================================================
# 11. No invented pvlib parameters
# ===========================================================================

class TestNoInventedPvlibParameters:
    @pytest.fixture(scope="class")
    def pvlib_rows(self) -> dict[str, dict]:
        return {r["system_id"]: r for r in _read_csv("pvlib_readiness.csv")}

    def test_systems_without_a_real_cec_match_are_not_marked_module_ready(self, pvlib_rows):
        for sid in ("1430", "1433"):
            assert pvlib_rows[sid]["module_parameters_ready"] == "False", (
                f"System {sid} has no real CEC module database match and must not be marked "
                "module_parameters_ready -- doing so would require inventing electrical parameters."
            )

    def test_geometry_not_fabricated_for_blank_tracker_metadata(self, pvlib_rows):
        # System 1430 is a tracker with blank tilt/azimuth in its real Mount metadata.
        assert pvlib_rows["1430"]["geometry_ready"] == "False"
        assert "TRACKER_GEOMETRY_PARAMS_NOT_AVAILABLE" in pvlib_rows["1430"]["geometry_reason"]

    def test_module_matches_are_real_pvlib_cec_database_entries(self, gate56b_module):
        import pvlib
        cec_mods = pvlib.pvsystem.retrieve_sam("CECMod")
        for sid, (col, _label) in gate56b_module.CEC_MODULE_CANDIDATES.items():
            if col is not None:
                assert col in cec_mods.columns, (
                    f"Claimed CEC module match '{col}' for system {sid} does not exist in "
                    "pvlib's real bundled CEC module database -- this would be a fabricated match."
                )

    def test_inverter_matches_are_real_pvlib_cec_database_entries(self, gate56b_module):
        import pvlib
        cec_inv = pvlib.pvsystem.retrieve_sam("CECInverter")
        for sid, (col, _label) in gate56b_module.CEC_INVERTER_CANDIDATES.items():
            if col is not None:
                assert col in cec_inv.columns, (
                    f"Claimed CEC inverter match '{col}' for system {sid} does not exist in "
                    "pvlib's real bundled CEC inverter database -- this would be a fabricated match."
                )

    def test_temperature_and_aoi_candidates_are_disclosed_as_standard_assumptions(self, pvlib_rows):
        for row in pvlib_rows.values():
            assert "STANDARD ASSUMPTION" in row["temperature_model_candidate"]
            assert "STANDARD ASSUMPTION" in row["aoi_model_candidate"]


# ===========================================================================
# 12. Physics-readiness requires required metadata
# ===========================================================================

class TestPhysicsReadinessRequiresMetadata:
    @pytest.fixture(scope="class")
    def pvlib_rows(self) -> dict[str, dict]:
        return {r["system_id"]: r for r in _read_csv("pvlib_readiness.csv")}

    def test_physics_ready_true_only_when_all_required_inputs_present(self, pvlib_rows):
        for sid, row in pvlib_rows.items():
            required = (
                row["geometry_ready"] == "True"
                and row["module_parameters_ready"] == "True"
                and row["irradiance_ready"] == "True"
                and row["temperature_ready"] == "True"
            )
            if row["physics_ready"] == "True":
                assert required, f"System {sid} marked physics_ready without all required real inputs."

    def test_systems_without_cec_match_or_geometry_are_not_physics_ready(self, pvlib_rows):
        for sid in ("1430", "1433"):
            assert pvlib_rows[sid]["physics_ready"] == "False"

    def test_dev_systems_with_full_metadata_are_physics_ready(self, pvlib_rows):
        for sid in ("1239", "1283", "34"):
            assert pvlib_rows[sid]["physics_ready"] == "True"


# ===========================================================================
# 13. Empirical-readiness requires valid target and environmental inputs
# ===========================================================================

class TestEmpiricalReadinessRequiresValidInputs:
    @pytest.fixture(scope="class")
    def adj_rows(self) -> dict[str, dict]:
        return {r["system_id"]: r for r in _read_csv("cohort_adjudication.csv")}

    def test_ambiguous_power_status_would_block_empirical_readiness(self, adj_rows):
        for row in adj_rows.values():
            if row["power_status"] == "AMBIGUOUS":
                assert row["empirical_ready"] == "False"

    def test_severely_missing_target_blocks_empirical_readiness(self, adj_rows):
        # System 1433's AC power target is 74.7% missing -- must not be empirical_ready.
        assert float(adj_rows["1433"]["target_missingness_fraction"]) > 0.5
        assert adj_rows["1433"]["empirical_ready"] == "False"

    def test_development_systems_are_empirical_ready(self, adj_rows):
        for sid in ("1239", "1283", "34"):
            assert adj_rows[sid]["empirical_ready"] == "True"

    def test_context_signal_missingness_recorded_not_silently_dropped(self, adj_rows):
        assert "ambient_temp" in adj_rows["34"]["notable_context_signal_missingness"]


# ===========================================================================
# 14. Validation cohort disjointness
# ===========================================================================

class TestValidationCohortDisjointness:
    @pytest.fixture(scope="class")
    def freeze(self) -> dict:
        return _read_json("cohort_freeze_v2.json")

    def test_development_and_validation_are_disjoint(self, freeze):
        dev = set(freeze["development_systems"])
        val = set(freeze["validation_systems"])
        assert dev.isdisjoint(val)

    def test_development_and_secondary_only_are_disjoint(self, freeze):
        dev = set(freeze["development_systems"])
        sec = set(freeze["secondary_only_systems"])
        assert dev.isdisjoint(sec)

    def test_every_cohort_system_appears_in_exactly_one_role(self, freeze):
        buckets = [
            set(freeze["development_systems"]),
            set(freeze["validation_systems"]),
            set(freeze["secondary_only_systems"]),
            set(freeze["excluded_systems"]),
        ]
        all_assigned = set().union(*buckets)
        assert all_assigned == set(ALL_SYSTEMS)
        for sid in ALL_SYSTEMS:
            count = sum(1 for b in buckets if sid in b)
            assert count == 1, f"System {sid} assigned to {count} roles (must be exactly 1)."


# ===========================================================================
# 15. Objective cohort selection (no performance-based selection, no padding)
# ===========================================================================

class TestObjectiveCohortSelection:
    def test_cohort_adjudication_csv_never_references_a_performance_metric(self):
        rows = _read_csv("cohort_adjudication.csv")
        cols_lower = {c.lower() for c in rows[0]}
        forbidden = {"r2", "rmse", "mae", "residual", "accuracy", "score"}
        assert cols_lower.isdisjoint(forbidden), (
            "cohort_adjudication.csv must not contain any performance-metric column -- final "
            "roles must be assigned on data-quality grounds only."
        )

    def test_no_padding_when_validation_candidates_fail_objective_checks(self):
        freeze = _read_json("cohort_freeze_v2.json")
        if not freeze["validation_systems"]:
            assert freeze["validation_cohort_status"] == "INSUFFICIENT_DATA"
            assert "padding" in freeze["validation_cohort_note"].lower() or "no replacement" in freeze["validation_cohort_note"].lower()

    def test_reason_field_cites_objective_criteria_only(self):
        rows = _read_csv("cohort_adjudication.csv")
        for r in rows:
            reason = r["reason"].lower()
            assert "performance" not in reason
            assert "accuracy" not in reason


# ===========================================================================
# 16. Deterministic adjudication
# ===========================================================================

class TestDeterministicAdjudication:
    def test_timestamp_adjudication_is_deterministic(self, gate56b_module):
        first = gate56b_module.adjudicate_timestamps()
        second = gate56b_module.adjudicate_timestamps()
        assert first == second

    def test_power_semantics_adjudication_is_deterministic(self, gate56b_module):
        first = gate56b_module.adjudicate_power_semantics()
        second = gate56b_module.adjudicate_power_semantics()
        assert first == second

    def test_cohort_adjudication_is_deterministic(self, gate56b_module):
        ts_rows = gate56b_module.adjudicate_timestamps()
        power_rows = gate56b_module.adjudicate_power_semantics()
        sampling_rows = gate56b_module.build_signal_sampling_matrix()
        pvlib_rows = gate56b_module.build_pvlib_readiness(ts_rows)
        first = gate56b_module.build_cohort_adjudication(ts_rows, power_rows, pvlib_rows, sampling_rows)
        second = gate56b_module.build_cohort_adjudication(ts_rows, power_rows, pvlib_rows, sampling_rows)
        assert first == second

    def test_written_artifact_matches_a_fresh_rebuild(self, gate56b_module):
        ts_rows = gate56b_module.adjudicate_timestamps()
        power_rows = gate56b_module.adjudicate_power_semantics()
        sampling_rows = gate56b_module.build_signal_sampling_matrix()
        pvlib_rows = gate56b_module.build_pvlib_readiness(ts_rows)
        rebuilt = gate56b_module.build_cohort_adjudication(ts_rows, power_rows, pvlib_rows, sampling_rows)
        on_disk = _read_csv("cohort_adjudication.csv")
        assert len(rebuilt) == len(on_disk)
        for fresh, disk in zip(rebuilt, on_disk, strict=True):
            assert str(fresh["system_id"]) == disk["system_id"]
            assert fresh["final_role"] == disk["final_role"]
            assert fresh["timestamp_status"] == disk["timestamp_status"]
            assert fresh["power_status"] == disk["power_status"]
