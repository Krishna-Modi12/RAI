"""Gate 5.6C: Model Development Circularity Tripwire & Sanity Test Suite.

Mirrors tests/test_gate56a_data_authenticity.py's pattern: verifies the mandatory
anti-circularity and anti-fabrication rules the Gate 5.6C decision gate (PATH B,
artifacts/evaluation/gate56/gate56c_decision_gate/decision.md) imposes on the new real
pvlib.modelchain.ModelChain physics reference:

1. The new physics reference never imports the synthetic fixture generator or the
   invalid hand-rolled PVLibPhysicsReference formula that caused
   GATE_5.6_INVALID_SYNTHETIC_RUN.
2. It is a genuine pvlib ModelChain computation (temperature/irradiance-sensitive),
   not a trivial proportional pass-through that could reproduce the original defect.
3. No parameters are invented for PARAMETERIZATION_INSUFFICIENT systems (1430, 1433):
   constructing a reference for them raises rather than fabricating config.
4. Gate 5.6C artifacts, once built, are labeled MODEL_DEVELOPMENT /
   NOT_INDEPENDENTLY_VALIDATED everywhere a metric is reported.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NEW_MODULE_PATH = REPO_ROOT / "rai" / "eval" / "external" / "solar" / "pvlib_modelchain_reference.py"
BUILD_SCRIPT_PATH = REPO_ROOT / "scratch_gate56a" / "build_gate56c.py"
GATE56C_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "gate56c_model_development"
READINESS_CSV = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "cohort_adjudication" / "pvlib_readiness.csv"


class TestNoSyntheticOrInvalidFormulaDependency:
    def test_new_physics_module_does_not_import_synthetic_fixtures(self):
        source = NEW_MODULE_PATH.read_text(encoding="utf-8")
        assert "synthetic_fixtures" not in source
        assert "generate_pvdaq_telemetry" not in source
        assert "generate_synthetic_solar_fixture" not in source

    def test_new_physics_module_does_not_import_invalid_hand_rolled_class(self):
        source = NEW_MODULE_PATH.read_text(encoding="utf-8")
        assert "import PVLibPhysicsReference" not in source
        assert "models import" not in source or "PVLibPhysicsReference" not in source

    def test_build_script_does_not_import_synthetic_fixtures_or_invalid_class(self):
        source = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
        assert "synthetic_fixtures" not in source
        assert "import PVLibPhysicsReference" not in source, (
            "Gate 5.6C build script must use PVLibModelChainReference only -- the invalid "
            "hand-rolled PVLibPhysicsReference must never be imported into new modeling code."
        )
        assert "PVLibPhysicsReference(" not in source, (
            "Gate 5.6C build script must never instantiate the invalid hand-rolled physics model."
        )

    def test_new_physics_module_actually_uses_pvlib_modelchain(self):
        source = NEW_MODULE_PATH.read_text(encoding="utf-8")
        assert "from pvlib.modelchain import ModelChain" in source
        assert "run_model_from_effective_irradiance" in source
        assert "retrieve_sam" in source, "Module/inverter parameters must come from pvlib's real reference database."


class TestNoInventedParameters:
    def test_only_physics_ready_systems_from_pvlib_readiness_csv_are_configured(self):
        from rai.eval.external.solar.pvlib_modelchain_reference import REAL_MODELCHAIN_CONFIG

        ready_systems = set()
        with READINESS_CSV.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["physics_ready"] == "True":
                    ready_systems.add(int(row["system_id"]))

        assert set(REAL_MODELCHAIN_CONFIG.keys()) == ready_systems, (
            "REAL_MODELCHAIN_CONFIG must exactly match the systems Gate 5.6B classified "
            "physics_ready=True -- no more (invented), no fewer (undocumented drop)."
        )
        assert 1430 not in REAL_MODELCHAIN_CONFIG
        assert 1433 not in REAL_MODELCHAIN_CONFIG

    def test_constructing_reference_for_unconfigured_system_raises(self):
        from rai.eval.external.solar.pvlib_modelchain_reference import PVLibModelChainReference

        with pytest.raises(ValueError, match="PARAMETERIZATION_INSUFFICIENT"):
            PVLibModelChainReference(1430)
        with pytest.raises(ValueError, match="PARAMETERIZATION_INSUFFICIENT"):
            PVLibModelChainReference(1433)

    def test_module_and_inverter_names_resolve_in_real_pvlib_database(self):
        from pvlib.pvsystem import retrieve_sam

        from rai.eval.external.solar.pvlib_modelchain_reference import REAL_MODELCHAIN_CONFIG

        cec_mods = retrieve_sam("CECMod")
        cec_invs = retrieve_sam("CECInverter")
        for sid, cfg in REAL_MODELCHAIN_CONFIG.items():
            assert cfg["module_name"] in cec_mods.columns, f"System {sid}: module not in real CEC database."
            assert cfg["inverter_name"] in cec_invs.columns, f"System {sid}: inverter not in real CEC database."


class TestGenuinePhysicsNotProportionalPassThrough:
    """The original invalidation's defect was formula-identity to the data generator.
    A real ModelChain must be irradiance- AND temperature-sensitive -- a simple
    proportional pass-through (P = k * POA) would not distinguish these two cases."""

    @pytest.mark.parametrize("system_id", [1239, 1283, 34])
    def test_prediction_is_temperature_sensitive(self, system_id):
        from rai.eval.external.solar.pvlib_modelchain_reference import PVLibModelChainReference

        ref = PVLibModelChainReference(system_id)
        idx = pd.date_range("2019-07-01 16:00", periods=3, freq="15min", tz="UTC")
        base = pd.DataFrame(
            {
                "timestamp_utc": idx,
                "poa_wm2": [700.0, 700.0, 700.0],
                "ambient_temp_c": [20.0, 20.0, 20.0],
                "module_temp_c": [20.0, 20.0, 20.0],
                "solar_elevation_deg": [40.0, 40.0, 40.0],
                "wind_speed_ms": [2.0, 2.0, 2.0],
            }
        )
        hot = base.copy()
        hot["ambient_temp_c"] = 45.0

        cool_pred = ref.predict(base)
        hot_pred = ref.predict(hot)
        assert not np.allclose(cool_pred, hot_pred), (
            "A real pvlib ModelChain must show temperature derating; identical output "
            "under different temperatures would indicate a broken or trivial pass-through."
        )
        assert np.all(hot_pred <= cool_pred + 1e-6), "Higher module temperature must not increase expected AC power."

    def test_prediction_is_not_a_simple_linear_multiple_of_poa(self):
        from rai.eval.external.solar.pvlib_modelchain_reference import PVLibModelChainReference

        ref = PVLibModelChainReference(1239)
        idx = pd.date_range("2019-07-01 16:00", periods=2, freq="15min", tz="UTC")
        df = pd.DataFrame(
            {
                "timestamp_utc": idx,
                "poa_wm2": [200.0, 800.0],
                "ambient_temp_c": [20.0, 20.0],
                "module_temp_c": [20.0, 20.0],
                "solar_elevation_deg": [40.0, 40.0],
            }
        )
        pred = ref.predict(df)
        ratio_low = pred[0] / 200.0
        ratio_high = pred[1] / 800.0
        assert abs(ratio_low - ratio_high) > 1e-3, (
            "A single-diode CEC model + Sandia inverter model is not perfectly linear in "
            "irradiance (inverter Pso/efficiency-curve nonlinearity); identical ratios at "
            "very different irradiance levels would suggest a degenerate/trivial formula."
        )


@pytest.mark.skipif(not GATE56C_DIR.exists(), reason="Gate 5.6C build has not been run yet.")
class TestArtifactLabeling:
    def test_provenance_manifest_declares_model_development_not_validated(self):
        manifest = json.loads((GATE56C_DIR / "provenance_manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "MODEL_DEVELOPMENT"
        assert manifest["validation_status"] == "NOT_INDEPENDENTLY_VALIDATED"
        assert manifest["holdout_type"] == "TEMPORAL_WITHIN_SYSTEM"
        assert manifest["path_taken"] == "PATH_B"

    def test_self_consistency_diagnostics_all_labeled_as_diagnostic_only(self):
        path = GATE56C_DIR / "self_consistency_diagnostics.csv"
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) > 0
        for row in rows:
            assert "MODEL_DEVELOPMENT" in row["note"] or "INSUFFICIENT_DATA" in row["note"]

    def test_summary_never_claims_validated_or_generalization(self):
        text = (GATE56C_DIR / "summary.md").read_text(encoding="utf-8").lower()
        forbidden = ["achieves validated accuracy", "generalizes", "generalization to", "state of the art"]
        for phrase in forbidden:
            assert phrase not in text, f"summary.md must not claim: {phrase!r}"
        # The disclaimer is required to explicitly DENY these claims, not merely omit them.
        assert "never a validated-accuracy" in text or "not a validated-accuracy" in text
        assert "never cross-system generalization" in text or "never described as generalization" in text
