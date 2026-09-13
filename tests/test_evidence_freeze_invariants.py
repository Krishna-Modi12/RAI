"""Scientific Evidence Freeze Invariant Tests.

Guarantees the strict boundaries established in the Scientific Evidence Freeze:
1. EXTERNAL_REAL never means live commercial field deployment.
2. Synthetic cases cannot be represented as field observations.
3. PVDAQ Validation=[] remains frozen with INSUFFICIENT_DATA.
4. Gate 5.6C cannot be described as independently validated.
5. Projected economics cannot be labelled realized savings or guaranteed ROI.
6. Operational events cannot automatically become component failures.
7. Agent evaluation cannot be labelled production validation.
8. Closed-loop demo/test data cannot become external field evidence.
9. Evidence freeze registry, claims, and matrix maintain 100% relational integrity.
"""

from __future__ import annotations

import json
from pathlib import Path

from rai.memory.library import cases_for, get_field_feedback_cases, get_real_cases
from rai.memory.real_corpus import RealEventClass, get_real_case_records
from rai.memory.work_orders import (
    FeedbackProvenance,
    FieldResolution,
    ObservationLevel,
    WorkOrderPriority,
    approve_work_order,
    propose_work_order,
    record_feedback,
)
from rai.schemas import AssetType, HistoricalSourceType

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_external_real_never_means_live_field_deployment():
    """Guarantee that EXTERNAL_REAL cases strictly trace to academic/open data, never live utility sites."""
    real_cases = get_real_cases()
    assert len(real_cases) == 14, "Audited external real pool must contain exactly 14 cases"

    for case in real_cases:
        assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
        source_str = f"{case.source_dataset or ''} {case.source_reference or ''} {case.source_doc or ''}".upper()
        assert any(
            benchmark in source_str
            for benchmark in ["CARE", "ZENODO", "KELMARSH", "PVDAQ", "NREL"]
        ), f"Case {case.case_id} has non-academic source: {source_str}"

        # No live commercial utility fleet claim
        assert "LIVE_DEPLOYMENT" not in source_str
        assert "COMMERCIAL_UTILITY_FEED" not in source_str


def test_synthetic_cases_cannot_be_represented_as_field_observations():
    """Guarantee that synthetic scenario cases remain INTERNAL_SYNTHETIC."""
    synth_wind = cases_for(AssetType.WIND_TURBINE, partition="synthetic")
    synth_solar = cases_for(AssetType.SOLAR_INVERTER, partition="synthetic")

    assert len(synth_wind) == 8, "Must have 8 synthetic wind reference scenarios"
    assert len(synth_solar) == 6, "Must have 6 synthetic solar reference scenarios"

    for case in synth_wind + synth_solar:
        assert case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
        assert case.source_dataset is None


def test_pvdaq_validation_cohort_remains_frozen_empty():
    """Guarantee that Gate 5.6B cohort adjudication has Validation=[] and INSUFFICIENT_DATA."""
    cohort_freeze_path = (
        REPO_ROOT
        / "artifacts"
        / "evaluation"
        / "gate56"
        / "cohort_adjudication"
        / "cohort_freeze_v2.json"
    )
    assert cohort_freeze_path.exists(), "cohort_freeze_v2.json must exist"

    with open(cohort_freeze_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["gate"] == "5.6B"
    assert data["development_systems"] == [1239, 1283, 34]
    assert data["validation_systems"] == [], "Validation cohort MUST be empty"
    assert data["validation_cohort_status"] == "INSUFFICIENT_DATA"


def test_gate56c_cannot_be_described_as_validated():
    """Guarantee that Gate 5.6C is marked NOT_INDEPENDENTLY_VALIDATED in docs and claims."""
    claims_path = REPO_ROOT / "docs" / "CLAIMS.md"
    assert claims_path.exists()
    content = claims_path.read_text(encoding="utf-8")

    # The claim for solar model independent validation must be explicitly negated
    assert "Not yet true — do not claim this" in content or "NOT_INDEPENDENTLY_VALIDATED" in content

    # Gate 5.6C verification document must label results as MODEL_DEVELOPMENT
    verif_doc = REPO_ROOT / "docs" / "evaluation" / "GATE56C_VERIFICATION.md"
    assert verif_doc.exists()
    verif_text = verif_doc.read_text(encoding="utf-8")
    assert "MODEL_DEVELOPMENT" in verif_text
    assert "NOT_INDEPENDENTLY_VALIDATED" in verif_text


def test_projected_economics_cannot_be_labelled_realized_savings():
    """Guarantee that economic models describe projected exposure, not realized savings."""
    from rai.economics.decision_support import evaluate_decision_support

    result = evaluate_decision_support(
        asset_id="WT-001",
        component="gearbox",
        risk_score=0.85,
        risk_calibration="calibrated",
        risk_window_days=(7, 14),
    )

    # Ensure field names and attributes reflect projected risk / waiting consequences
    assert hasattr(result, "expected_waiting_consequence_inr")
    assert hasattr(result, "intervention_cost_inr")
    assert not hasattr(result, "realized_savings_inr")
    assert not hasattr(result, "guaranteed_roi")


def test_operational_events_cannot_automatically_become_component_failures():
    """Guarantee that Kelmarsh operational events are NOT classified as confirmed failures."""
    records = get_real_case_records()
    kelmarsh_records = [r for r in records if "REAL-KEL-" in r.case_id]

    assert len(kelmarsh_records) == 4, "Must have exactly 4 Kelmarsh records"
    for r in kelmarsh_records:
        assert r.event_class in {
            RealEventClass.REAL_OPERATIONAL_EVENT,
            RealEventClass.REAL_MAINTENANCE_EVENT,
            RealEventClass.ENVIRONMENTAL_EVENT,
        }
        case = r.to_case()
        assert case.equipment_fault is False, (
            f"Kelmarsh record {r.case_id} must have equipment_fault=False"
        )
        assert r.event_class != RealEventClass.REAL_VERIFIED_EVENT


def test_agent_evaluation_cannot_be_labelled_production_validation():
    """Guarantee that local agent evaluation is bounded to internal synthetic fixtures."""
    agent_eval_doc = REPO_ROOT / "docs" / "evaluation" / "LOCAL_AGENT_EVALUATION.md"
    assert agent_eval_doc.exists()
    text = agent_eval_doc.read_text(encoding="utf-8")

    assert "INTERNAL_SYNTHETIC" in text
    assert "failure validation" in text.lower()
    assert "not" in text.lower()


def test_closed_loop_demo_data_cannot_become_external_field_evidence(tmp_path, monkeypatch):
    """Guarantee that simulated/test work orders can never enter EXTERNAL_REAL."""
    test_log = tmp_path / "test_freeze_tickets.jsonl"
    monkeypatch.setenv("RAI_TICKET_LOG", str(test_log))

    # Propose, approve, and record feedback as DEMO_SIMULATION
    t = propose_work_order(
        asset_id="WT-004",
        component="pitch_system",
        action="Inspect pitch motor",
        priority=WorkOrderPriority.HIGH,
        created_by="demo_operator",
        provenance=FeedbackProvenance.DEMO_SIMULATION,
    )
    t = approve_work_order(t.ticket_id, approved_by="supervisor")
    record_feedback(
        ticket_id=t.ticket_id,
        technician_id="TECH-1",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Motor coil insulation failure confirmed",
        component_inspected="pitch_system",
        actual_downtime_hours=3.5,
        actual_parts_cost_inr=15000.0,
        provenance=FeedbackProvenance.DEMO_SIMULATION,
        observation_level=ObservationLevel.FIELD_VERIFIED,
    )

    field_cases = get_field_feedback_cases()
    # It must be exported
    assert len(field_cases) >= 1
    demo_case = field_cases[0]

    # Must NOT be EXTERNAL_REAL
    assert demo_case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC

    # Retrieval 'real' pool must not include it
    real_cases = get_real_cases()
    assert all(c.case_id != demo_case.case_id for c in real_cases)


def test_evidence_freeze_artifacts_consistency():
    """Verify relational integrity across the generated Scientific Evidence Freeze artifacts."""
    freeze_dir = REPO_ROOT / "artifacts" / "evaluation" / "evidence_freeze"
    assert (freeze_dir / "evidence_registry.json").exists()
    assert (freeze_dir / "evidence_registry.csv").exists()
    assert (freeze_dir / "claim_to_evidence.csv").exists()
    assert (freeze_dir / "unsupported_claims.csv").exists()
    assert (freeze_dir / "freeze_summary.md").exists()
    assert (freeze_dir / "evidence_matrix.md").exists()

    with open(freeze_dir / "evidence_registry.json", encoding="utf-8") as f:
        registry = json.load(f)

    capability_names = {c["capability"] for c in registry["capabilities"]}
    assert len(capability_names) == 18, "Registry must contain exactly 18 audited capabilities"

    required_fields = {
        "capability",
        "evidence_source",
        "dataset_or_fixture",
        "real_or_synthetic",
        "external_or_internal",
        "metric_or_result",
        "artifact",
        "what_the_evidence_actually_proves",
        "what_it_does_NOT_prove",
        "final_status",
    }
    for c in registry["capabilities"]:
        assert required_fields.issubset(c.keys()), f"Capability {c.get('capability')} missing required fields"
        assert c["final_status"] in {
            "VALIDATED",
            "DEMONSTRATED",
            "ARCHITECTURALLY_SUPPORTED",
            "NOT_VALIDATED",
        }

    # Verify claim_to_evidence references valid capabilities
    import csv

    with open(freeze_dir / "claim_to_evidence.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert row["capability"] in capability_names, (
                f"Claim {row['claim_id']} points to unknown capability {row['capability']}"
            )
            assert row["capability_level"] in {
                "VALIDATED",
                "DEMONSTRATED",
                "ARCHITECTURALLY_SUPPORTED",
                "NOT_VALIDATED",
            }


def test_real_corpus_evidence_quality_never_conflated_with_field_verified():
    """Guarantee historical benchmark cases (real_corpus.py) never claim the ObservationLevel.FIELD_VERIFIED
    provenance tier reserved for the technician-feedback dual-key promotion gate — these are two distinct
    provenance vocabularies and must never be merged."""
    for rec in get_real_case_records():
        assert rec.evidence_quality != ObservationLevel.FIELD_VERIFIED.value
        assert rec.evidence_quality != "FIELD_VERIFIED"


def test_registry_never_upgrades_frozen_downgraded_capabilities():
    """Guarantee the evidence-freeze registry keeps its most safety-critical statuses frozen:
    the solar physics layer (Gate 5.6C) stays NOT_VALIDATED, and historical case retrieval stays
    at DEMONSTRATED (not VALIDATED) because its P@1/R@3 metrics are self-graded against
    developer-authored relevance judgments, not an independent benchmark."""
    freeze_dir = REPO_ROOT / "artifacts" / "evaluation" / "evidence_freeze"
    with open(freeze_dir / "evidence_registry.json", encoding="utf-8") as f:
        registry = json.load(f)

    by_name = {c["capability"]: c for c in registry["capabilities"]}

    assert by_name["Solar physics layer"]["final_status"] == "NOT_VALIDATED"
    assert by_name["Historical case retrieval"]["final_status"] != "VALIDATED"
    assert by_name["Kelmarsh benchmark"]["final_status"] == "VALIDATED"
    assert "not hardware-failure" in by_name["Kelmarsh benchmark"]["what_it_does_NOT_prove"].lower() or (
        "failure detection" in by_name["Kelmarsh benchmark"]["what_it_does_NOT_prove"].lower()
    )

    for cap_name in ("Dispatch optimization", "Weather-aware scheduling"):
        limitation = by_name[cap_name]["what_it_does_NOT_prove"].lower()
        assert "certified" in limitation, f"{cap_name} must explicitly disclaim a certified safety guarantee"

    econ = by_name["Economic consequence analysis"]
    assert "realized" in econ["what_it_does_NOT_prove"].lower() or "savings" in econ["what_it_does_NOT_prove"].lower()

    closed_loop = by_name["Closed-loop learning"]
    assert "live utility field data" in closed_loop["what_it_does_NOT_prove"].lower() or (
        "commercial utility" in closed_loop["what_it_does_NOT_prove"].lower()
    )
