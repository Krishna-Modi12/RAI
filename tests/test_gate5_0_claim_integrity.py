"""Unit and forensic validation tests for Gate 5.0 Claim Integrity & Provenance Audit.

Ensures that every performance claim, benchmark metric, and causal term
is classified into its proper evidentiary tier, and that no misleading
or unhedged claims exist in active code and documentation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GATE5_0_DIR = ROOT / "artifacts" / "evaluation" / "gate5_0"
DOCS_DIR = ROOT / "docs" / "evaluation"


@pytest.fixture
def audit_data() -> dict:
    json_path = GATE5_0_DIR / "claim_audit.json"
    assert json_path.exists(), f"Missing audit artifact: {json_path}"
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def test_gate5_0_artifacts_exist():
    """Verify that all required Gate 5.0 artifacts were generated."""
    assert (GATE5_0_DIR / "claim_audit.json").exists()
    assert (GATE5_0_DIR / "claim_audit.csv").exists()
    assert (GATE5_0_DIR / "summary.md").exists()
    assert (DOCS_DIR / "CLAIM_INTEGRITY_AUDIT.md").exists()

    summary_text = (GATE5_0_DIR / "summary.md").read_text(encoding="utf-8")
    assert "Gate 5.0: Claim Integrity" in summary_text
    assert "INTERNAL_SYNTHETIC" in summary_text
    assert "EXTERNAL_REAL" in summary_text


def test_evidentiary_tiers_populated(audit_data: dict):
    """Verify that all expected evidentiary tiers are populated."""
    tiers = audit_data.get("evidentiary_tier_summary", {})
    required_tiers = {
        "INTERNAL_SYNTHETIC",
        "EXTERNAL_REAL",
        "SIMULATED_OUTCOME",
        "HISTORICAL_AUDIT",
        "SOFTWARE_INVARIANT",
        "MODEL_COMPARISON",
    }
    for tier in required_tiers:
        assert tier in tiers, f"Tier {tier} missing from audit breakdown"
        assert tiers[tier] > 0, f"Tier {tier} has 0 recorded claims"


def test_no_unhedged_causality_claims():
    """Verify that active evaluation files do not claim 'causal proof'."""
    eval_doc = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    assert "proving genuine causal temporal alignment" not in eval_doc

    gate2_script = (ROOT / "scripts" / "evaluate_gate2.py").read_text(encoding="utf-8")
    assert "proving genuine causal temporal alignment" not in gate2_script


def test_care_tracking_vs_anomaly_separation(audit_data: dict):
    """Verify that power R^2=0.9943 is documented as tracking, not official CARE anomaly detection."""
    claims = audit_data.get("occurrences", [])
    r2_claims = [c for c in claims if c["category"].startswith("R")]
    assert len(r2_claims) > 0

    eval_doc = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    assert "External SCADA Zero-Shot Tracking" in eval_doc
    assert "Official CARE Anomaly Benchmark" in eval_doc
    assert "PENDING" in eval_doc


def test_false_alarm_rate_provenance(audit_data: dict):
    """Verify that both 0.19 and 0.09 false alarm claims have documented provenance."""
    claims = audit_data.get("occurrences", [])
    fa_019 = [c for c in claims if c["category"].startswith("0.19")]
    fa_009 = [c for c in claims if c["category"].startswith("0.09")]

    assert len(fa_019) > 0, "Expected occurrences of 0.19 in codebase"
    assert len(fa_009) > 0, "Expected occurrences of 0.09 in codebase"

    # Both must be present in docs/evaluation/CLAIM_INTEGRITY_AUDIT.md
    audit_md = (DOCS_DIR / "CLAIM_INTEGRITY_AUDIT.md").read_text(encoding="utf-8")
    assert "0.19 alerts / asset-year" in audit_md
    assert "0.09 alerts / asset-year" in audit_md
