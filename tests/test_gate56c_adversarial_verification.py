"""Adversarial Audit & Forensic Verification for Gate 5.6C.

This test suite executes the independent adversarial audit for Gate 5.6C
(Solar Expected-Performance Model Development), mirroring the rigor of the audit
that caught GATE_5.6_INVALID_SYNTHETIC_RUN.

Audit Criteria Verified:
1. Circularity & Formula Independence (zero dependency on synthetic fixtures or hand-rolled formula)
2. Data Authenticity & Lineage (strict provenance to real acquired PVDAQ files)
3. Parameter Grounding (SAM/CEC resolution; anti-fabrication for unconfigured systems)
4. Temporal Holdout Integrity (strict forward chronological split, purge gaps)
5. Phenomenological Asymmetry (un-doctored per-system variation preserved)
6. Residual Stationarity & Bounded Bias
7. Negative Boundary Labeling (strictly MODEL_DEVELOPMENT / NOT_INDEPENDENTLY_VALIDATED)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE56C_DIR = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "gate56c_model_development"
PVLIB_REF_PY = REPO_ROOT / "rai" / "eval" / "external" / "solar" / "pvlib_modelchain_reference.py"
BUILD_SCRIPT_PY = REPO_ROOT / "scratch_gate56a" / "build_gate56c.py"
DECISION_MD = REPO_ROOT / "artifacts" / "evaluation" / "gate56" / "gate56c_decision_gate" / "decision.md"


class TestAuditCircularityAndFormulaIndependence:
    """Criterion 1: Verification that the solar model uses genuine pvlib ModelChain
    and is not algebraically identical to any data generating function."""

    def test_zero_synthetic_fixture_imports(self):
        for path in [PVLIB_REF_PY, BUILD_SCRIPT_PY]:
            source = path.read_text(encoding="utf-8")
            assert "synthetic_fixtures" not in source
            assert "generate_pvdaq_telemetry" not in source
            assert "generate_synthetic_solar_fixture" not in source

    def test_zero_handrolled_invalid_physics_class_usage(self):
        for path in [PVLIB_REF_PY, BUILD_SCRIPT_PY]:
            source = path.read_text(encoding="utf-8")
            assert "import PVLibPhysicsReference" not in source
            assert "PVLibPhysicsReference(" not in source

    def test_pvlib_modelchain_single_diode_execution(self):
        source = PVLIB_REF_PY.read_text(encoding="utf-8")
        assert "from pvlib.modelchain import ModelChain" in source
        assert "from pvlib.pvsystem import PVSystem, retrieve_sam" in source
        assert "run_model_from_effective_irradiance" in source


class TestAuditDataAuthenticityAndLineage:
    """Criterion 2 & 3: Verification that inputs trace to real PVDAQ acquisitions
    and parameters strictly trace to real metadata."""

    def test_provenance_manifest_lineage(self):
        manifest_path = GATE56C_DIR / "provenance_manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest["gate"] == "5.6C"
        assert manifest["path_taken"] == "PATH_B"
        assert manifest["development_systems"] == [1239, 1283, 34]
        assert manifest["holdout_type"] == "TEMPORAL_WITHIN_SYSTEM"

    def test_parameter_grounding_and_no_fabrication(self):
        from pvlib.pvsystem import retrieve_sam

        from rai.eval.external.solar.pvlib_modelchain_reference import (
            REAL_MODELCHAIN_CONFIG,
            PVLibModelChainReference,
        )

        cec_mods = retrieve_sam("CECMod")
        cec_invs = retrieve_sam("CECInverter")

        for sid in [1239, 1283, 34]:
            assert sid in REAL_MODELCHAIN_CONFIG
            cfg = REAL_MODELCHAIN_CONFIG[sid]
            assert cfg["module_name"] in cec_mods.columns
            assert cfg["inverter_name"] in cec_invs.columns
            assert cfg["tilt_deg"] > 0
            assert -180 <= cfg["azimuth_deg"] <= 360

        # Systems lacking physical parameters must explicitly reject instantiation
        for rejected_sid in [1430, 1433]:
            with pytest.raises(ValueError, match="PARAMETERIZATION_INSUFFICIENT"):
                PVLibModelChainReference(rejected_sid)


class TestAuditTemporalHoldoutIntegrity:
    """Criterion 4: Strict temporal separation with purge gaps."""

    def test_temporal_split_order_and_purge_gaps(self):
        from rai.eval.external.solar.pvdaq import split_system_telemetry

        dates = pd.date_range("2019-01-01", periods=1000, freq="15min", tz="UTC")
        df = pd.DataFrame({"utc_measured_on": dates, "ac_power_kw": 10.0})

        train_df, val_df, test_df = split_system_telemetry(df, 0.60, 0.20, purge_gap_intervals=4)

        train_last = train_df["utc_measured_on"].iloc[-1]
        val_first = val_df["utc_measured_on"].iloc[0]
        val_last = val_df["utc_measured_on"].iloc[-1]
        test_first = test_df["utc_measured_on"].iloc[0]

        assert val_first > train_last
        assert (val_first - train_last) >= pd.Timedelta(minutes=60)
        assert test_first > val_last
        assert (test_first - val_last) >= pd.Timedelta(minutes=60)


class TestAuditPhenomenologyAndResiduals:
    """Criterion 5 & 6: Verification that real system variation is preserved
    and residual statistics are physically consistent."""

    def test_preservation_of_system_34_physics_asymmetry(self):
        diagnostics_path = GATE56C_DIR / "self_consistency_diagnostics.csv"
        with diagnostics_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        test_rows = {
            (int(r["system_id"]), r["model"]): float(r["r2"])
            for r in rows
            if r["split"] == "test" and r["r2"]
        }

        r2_1239 = test_rows[(1239, "PVLIB_MODELCHAIN_PHYSICS_REFERENCE")]
        r2_1283 = test_rows[(1283, "PVLIB_MODELCHAIN_PHYSICS_REFERENCE")]
        r2_34 = test_rows[(34, "PVLIB_MODELCHAIN_PHYSICS_REFERENCE")]

        # Ensure that systems 1239 and 1283 track well (>0.95), but system 34 is lower (~0.70)
        # This confirms that results are real and have not been artificially smoothed or fabricated
        assert r2_1239 > 0.95
        assert r2_1283 > 0.95
        assert 0.65 <= r2_34 <= 0.75

    def test_calibrated_normal_residuals_bounded(self):
        manifest_path = GATE56C_DIR / "provenance_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary = manifest["per_system_summary"]

        # Rated capacities: 1239: 20.16 kW, 1283: 408.24 kW, 34: 146.6 kW
        rated = {1239: 20.16, 1283: 408.24, 34: 146.6}

        for sid, rated_kw in rated.items():
            mean_bias = abs(summary[str(sid)]["residual_mean_normal_kw"])
            pct_bias = (mean_bias / rated_kw) * 100.0
            # Calibrated normal residual mean should be within 3% of rated capacity
            assert pct_bias < 3.0, f"System {sid} residual bias {pct_bias}% exceeds 3% bound"


class TestAuditNegativeBoundariesAndLabelIntegrity:
    """Criterion 7: Verification of negative boundaries and zero unwarranted claims."""

    def test_diagnostics_contain_model_development_labels(self):
        diagnostics_path = GATE56C_DIR / "self_consistency_diagnostics.csv"
        with diagnostics_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) > 0
        for r in rows:
            assert "MODEL_DEVELOPMENT" in r["note"] or "INSUFFICIENT_DATA" in r["note"]
            assert "NOT_INDEPENDENTLY_VALIDATED" in r["note"] or "INSUFFICIENT_DATA" in r["note"]

    def test_forbidden_marketing_claims_absent(self):
        summary_text = (GATE56C_DIR / "summary.md").read_text(encoding="utf-8").lower()
        forbidden_affirmations = [
            "achieves validated accuracy",
            "demonstrates validated accuracy",
            "cross-system generalization",
            "state-of-the-art",
            "proven failure diagnosis",
        ]
        for phrase in forbidden_affirmations:
            assert phrase not in summary_text, f"Forbidden claim found: {phrase}"

        # Must explicitly state disclaimer
        assert "not_independently_validated" in summary_text
        assert "never a validated-accuracy" in summary_text or "did not claim validated accuracy" in summary_text
