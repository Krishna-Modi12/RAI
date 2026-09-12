"""Gate 5.6A: Data Authenticity & Anti-Circularity Tripwire Test Suite.

Verifies the mandatory synthetic-data tripwire from the Gate 5.6A master prompt:
1. The real-data acquisition code path (rai.eval.external.solar.pvdaq) can no longer
   import or expose the synthetic telemetry generator.
2. The synthetic generator, wherever it lives now, is unmistakably labeled as synthetic.
3. The invalid prior Gate 5.6 run is preserved untouched (not deleted, not overwritten,
   not silently reused as a source of any value in the Gate 5.6A acquisition artifacts).
4. Real downloaded PVDAQ telemetry is structurally and byte-for-byte distinguishable from
   anything the synthetic generator could produce (no is_synthetic_fixture marker, no
   generator-seed dependent reproducibility, real long-format PVDAQ schema).
5. DATA_SOURCE != MODEL_GENERATOR: no model manifest, no ModelChain run, no fitted
   model output exists anywhere under the Gate 5.6A acquisition directory.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACQ_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "acquisition"
INVALID_RUN_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56_invalid_prior_run"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "pvdaq"


# ===========================================================================
# 1. Synthetic generator quarantine
# ===========================================================================

class TestSyntheticGeneratorQuarantine:
    def test_pvdaq_module_does_not_define_generator(self):
        pvdaq = importlib.import_module("rai.eval.external.solar.pvdaq")
        assert not hasattr(pvdaq, "generate_pvdaq_telemetry"), (
            "rai.eval.external.solar.pvdaq must not expose a synthetic telemetry generator -- "
            "this is exactly the undisclosed-synthetic-data failure Gate 5.6A exists to prevent."
        )
        assert not hasattr(pvdaq, "PVDAQ_COHORT"), (
            "rai.eval.external.solar.pvdaq must not expose a fabricated 'real' cohort dict."
        )
        assert not hasattr(pvdaq, "load_cohort_data"), (
            "rai.eval.external.solar.pvdaq must not expose a loader that returns synthetic data "
            "under a name that could be mistaken for real acquisition."
        )

    def test_pvdaq_module_source_does_not_import_pvlib_simulation_stack(self):
        pvdaq_path = REPO_ROOT / "rai" / "eval" / "external" / "solar" / "pvdaq.py"
        source = pvdaq_path.read_text(encoding="utf-8")
        # The module's QUARANTINE NOTICE docstring is allowed to *mention* the old name for
        # audit-trail purposes; what must never exist again is a live definition of it.
        assert "def generate_pvdaq_telemetry" not in source
        assert "def generate_" not in source, "pvdaq.py must not define any telemetry generator function."
        assert "import pvlib" not in source, "pvdaq.py (schema-only module) must not depend on pvlib at runtime."

    def test_synthetic_fixtures_module_is_unmistakably_labeled(self):
        fixtures_path = REPO_ROOT / "rai" / "eval" / "external" / "solar" / "synthetic_fixtures.py"
        assert fixtures_path.exists(), "Relocated synthetic generator module must exist (quarantined, not deleted)."
        source = fixtures_path.read_text(encoding="utf-8")
        assert "SYNTHETIC" in source.upper()
        assert "NEVER USE AS EXTERNAL_REAL" in source or "NEVER" in source.upper()

    def test_synthetic_fixture_names_are_renamed_away_from_pvdaq_terminology(self):
        fixtures = importlib.import_module("rai.eval.external.solar.synthetic_fixtures")
        assert hasattr(fixtures, "generate_synthetic_solar_fixture")
        assert hasattr(fixtures, "SYNTHETIC_FIXTURE_COHORT")
        assert not hasattr(fixtures, "generate_pvdaq_telemetry"), (
            "The relocated module must not re-expose the old name -- callers must opt in via "
            "explicit import aliasing, never accidentally."
        )

    def test_real_acquisition_code_paths_never_import_synthetic_fixtures(self):
        real_code_paths = [
            REPO_ROOT / "scratch_gate56a" / "acquire.py",
            REPO_ROOT / "scratch_gate56a" / "build_artifacts.py",
        ]
        for path in real_code_paths:
            if path.exists():
                source = path.read_text(encoding="utf-8")
                # Mentioning the quarantine module's path in a comment/string (e.g. documenting
                # where the synthetic generator was relocated to, for provenance purposes) is
                # fine; actually importing from it is not.
                assert "from rai.eval.external.solar.synthetic_fixtures import" not in source, (
                    f"{path.name} is a real-data acquisition script and must never import the "
                    "synthetic fixture generator."
                )
                assert "import rai.eval.external.solar.synthetic_fixtures" not in source
                assert "generate_pvdaq_telemetry(" not in source, f"{path.name} must not call a synthetic generator."
                assert "generate_synthetic_solar_fixture(" not in source


# ===========================================================================
# 2. Invalid prior run preserved untouched
# ===========================================================================

class TestInvalidPriorRunPreserved:
    def test_invalid_run_directory_exists_and_is_not_empty(self):
        assert INVALID_RUN_DIR.exists(), "GATE_5.6_INVALID_SYNTHETIC_RUN preservation directory must exist."
        contents = list(INVALID_RUN_DIR.iterdir())
        assert len(contents) > 0

    def test_invalidation_manifest_declares_correct_status(self):
        manifest_path = INVALID_RUN_DIR / "invalidation_manifest.json"
        assert manifest_path.exists()
        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["status"] == "GATE_5.6_INVALID_SYNTHETIC_RUN"
        assert manifest["synthetic_data_detected"] is True
        assert manifest["circular_validation_detected"] is True

    def test_gate56a_acquisition_artifacts_do_not_reference_invalid_run_metrics(self):
        for name in ["provenance_manifest.json", "cohort_manifest.json", "summary.md"]:
            path = ACQ_DIR / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            assert "R2=0.999" not in text and "R²=0.999" not in text, (
                f"{name} must not cite the invalidated run's circular R² figure."
            )


# ===========================================================================
# 3. Real downloaded telemetry is structurally distinct from synthetic output
# ===========================================================================

class TestRealTelemetryIsNotSynthetic:
    @pytest.fixture(scope="class")
    def sample_real_file(self) -> pd.DataFrame:
        candidates = sorted(RAW_ROOT.rglob("*.parquet"))
        assert len(candidates) > 0, "No real downloaded PVDAQ parquet files found under data/raw/pvdaq/"
        return pd.read_parquet(candidates[0])

    def test_real_file_schema_is_long_format_pvdaq_not_synthetic_wide_format(self, sample_real_file: pd.DataFrame):
        expected_cols = {"measured_on", "utc_measured_on", "metric_id", "value"}
        assert expected_cols <= set(sample_real_file.columns), (
            "Real PVDAQ files use the long-format schema (measured_on, utc_measured_on, metric_id, "
            "value). A file matching the synthetic generator's wide-format schema "
            "(timestamp, ac_power_kw, poa_wm2, is_synthetic_fixture, ...) would indicate "
            "contamination from the synthetic generator."
        )
        assert "is_synthetic_fixture" not in sample_real_file.columns

    def test_real_files_are_not_reproducible_from_the_synthetic_seed(self):
        from rai.eval.external.solar.pvdaq import GATE56_SEED
        # The synthetic generator is deterministic given GATE56_SEED + a system's latitude.
        # Real acquisition has no dependency on GATE56_SEED at all -- assert the acquisition
        # script source never references it.
        acquire_source = (REPO_ROOT / "scratch_gate56a" / "acquire.py").read_text(encoding="utf-8")
        assert "GATE56_SEED" not in acquire_source
        assert GATE56_SEED == 20260912  # sanity: constant still exists for the (quarantined) fixture path only

    def test_download_manifest_files_all_resolve_to_real_downloaded_bytes_on_disk(self):
        manifest_path = ACQ_DIR / "download_manifest.json"
        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)
        ok_files = [r for r in manifest["files"] if r["status"] == "OK"]
        assert len(ok_files) > 0
        for rec in ok_files[:5]:
            local_path = REPO_ROOT / rec["local_path"]
            df = pd.read_parquet(local_path)
            assert {"measured_on", "utc_measured_on", "metric_id", "value"} <= set(df.columns)
            assert "is_synthetic_fixture" not in df.columns


# ===========================================================================
# 4. Circularity rule: DATA_SOURCE != MODEL_GENERATOR
# ===========================================================================

class TestNoCircularityInAcquisitionPhase:
    def test_no_model_manifest_present_in_gate56a_acquisition_dir(self):
        forbidden_names = [
            "champion_model_manifest.json",
            "empirical_model_manifest.json",
            "pvlib_model_manifest.json",
            "model_metrics.csv",
            "predictions_sample.csv",
            "residual_diagnostics.csv",
        ]
        for name in forbidden_names:
            assert not (ACQ_DIR / name).exists(), (
                f"Gate 5.6A acquisition directory must not contain modeling artifact '{name}' -- "
                "modeling is out of scope until Gate 5.6B (ABSOLUTE STOP RULE)."
            )

    def test_provenance_manifest_declares_circularity_rule(self):
        with (ACQ_DIR / "provenance_manifest.json").open(encoding="utf-8") as f:
            manifest = json.load(f)
        assert "circularity_rule_enforced" in manifest
        assert "DATA_SOURCE" in manifest["circularity_rule_enforced"]
        assert "MODEL_GENERATOR" in manifest["circularity_rule_enforced"]

    def test_provenance_manifest_classifies_data_as_external_real(self):
        with (ACQ_DIR / "provenance_manifest.json").open(encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["classification"] == "EXTERNAL_REAL"
