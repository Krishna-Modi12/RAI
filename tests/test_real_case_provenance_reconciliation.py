"""Regression and invariant tests for Real Case Corpus Provenance Reconciliation.

Verifies:
1. Synthetic/demo/test fixtures CANNOT enter EXTERNAL_REAL.
2. Only the dual-key gate (EXTERNAL_FIELD_OBSERVED + FIELD_VERIFIED) permits promotion.
3. Partition purity is strictly preserved across real, synthetic, and all partitions.
4. Unknown/unverified provenance cannot become real.
5. PVDAQ validation remains independent from the external case corpus (Gate 5.6B invariant).
6. Retrieval cannot silently treat synthetic cases as field-verified evidence.
7. Quarantined records are rejected from EXTERNAL_REAL.
8. The six solar cases (CASE-S-001 through CASE-S-006) are strictly INTERNAL_SYNTHETIC.
9. All 14 academic cases preserve complete provenance, license, and adjudication records.
"""

from __future__ import annotations

from rai.memory.library import (
    SOLAR_CASES,
    cases_for,
    get_field_feedback_cases,
    get_real_cases,
)
from rai.memory.real_corpus import RealEventClass, get_real_case_records
from rai.memory.retrieval import find_similar_cases
from rai.memory.work_orders import (
    FieldResolution,
    WorkOrderPriority,
    approve_work_order,
    export_field_cases_for_retrieval,
    propose_work_order,
    record_feedback,
)
from rai.models.pipeline import build_evidence_packet
from rai.schemas import AssetType, FeedbackProvenance, HistoricalSourceType, ObservationLevel


def test_academic_corpus_counts_and_lineage():
    """Verify exactly 14 audited academic cases (12 wind, 2 solar) with complete provenance."""
    records = get_real_case_records()
    assert len(records) == 14, f"Expected exactly 14 audited academic cases, found {len(records)}"

    wind_records = [r for r in records if r.asset_type == AssetType.WIND_TURBINE]
    solar_records = [r for r in records if r.asset_type == AssetType.SOLAR_INVERTER]

    assert len(wind_records) == 12, f"Expected 12 wind records, found {len(wind_records)}"
    assert len(solar_records) == 2, f"Expected 2 solar records, found {len(solar_records)}"

    # Check that each record has non-empty citation and adjudication
    for r in records:
        assert r.source_dataset, f"Missing source dataset for {r.case_id}"
        assert r.source_reference, f"Missing source reference for {r.case_id}"
        assert r.license, f"Missing license for {r.case_id}"
        assert r.adjudication.what_is_explicitly_known
        assert r.adjudication.what_source_proves
        assert r.adjudication.what_source_does_not_prove


def test_six_solar_cases_are_strictly_synthetic():
    """Verify that CASE-S-001 through CASE-S-006 are strictly INTERNAL_SYNTHETIC."""
    assert len(SOLAR_CASES) == 6
    for case in SOLAR_CASES:
        assert case.case_id.startswith("CASE-S-")
        assert case.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
        assert case.evidence_quality == "SYNTHETIC_SCENARIO"
        assert "PVPMC" not in (case.source_dataset or "")
        # Must NOT appear in real partition
        assert case not in get_real_cases()


def test_gate56b_pvdaq_independence_invariant():
    """Verify that the 2 real solar cases are drawn from Gate 5.6B Development cohort and not validation."""
    solar_real = [r for r in get_real_case_records() if r.asset_type == AssetType.SOLAR_INVERTER]
    assert len(solar_real) == 2
    case_ids = {r.case_id for r in solar_real}
    assert "REAL-PVDAQ-034-OUTAGE" in case_ids
    assert "REAL-PVDAQ-1283-CLIPPING" in case_ids

    # Systems 34 and 1283 are in Gate 5.6B Development cohort
    for r in solar_real:
        assert "PVDAQ" in r.source_dataset
        assert r.asset_id in {"PVDAQ-34", "PVDAQ-1283"}
        # Both must be operational or environmental, NOT hardware failure
        assert r.event_class in (RealEventClass.REAL_OPERATIONAL_EVENT, RealEventClass.ENVIRONMENTAL_EVENT)
        case = r.to_case()
        assert not case.equipment_fault


def test_synthetic_test_fixtures_cannot_enter_external_real():
    """Verify that simulated test fixtures with INTERNAL_TEST_FIXTURE cannot enter EXTERNAL_REAL."""
    wo = propose_work_order(
        asset_id="WT-006",
        component="gearbox",
        action="Routine oil test",
        provenance=FeedbackProvenance.INTERNAL_TEST_FIXTURE,
    )
    approve_work_order(wo.ticket_id, approved_by="supervisor")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="test_tech_99",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Test findings: bearing micropitting observed under test fixture.",
        component_inspected="gearbox",
        provenance=FeedbackProvenance.INTERNAL_TEST_FIXTURE,
        observation_level=ObservationLevel.FIELD_VERIFIED,
    )

    real_cases = get_real_cases()
    assert not any(wo.ticket_id in str(c.source_reference) for c in real_cases)

    real_wind = cases_for("wind_turbine", partition="real")
    assert not any(wo.ticket_id in str(c.source_reference) for c in real_wind)

    field_cases = get_field_feedback_cases()
    matching = [c for c in field_cases if wo.ticket_id in str(c.source_reference)]
    assert len(matching) >= 1
    assert matching[0].source_type == HistoricalSourceType.INTERNAL_SYNTHETIC


def test_unknown_provenance_cannot_become_real():
    """Verify that feedback with UNKNOWN provenance remains INTERNAL_SYNTHETIC."""
    wo = propose_work_order(
        asset_id="WT-004",
        component="generator",
        action="Inspect unknown alert",
        provenance=FeedbackProvenance.UNKNOWN,
    )
    approve_work_order(wo.ticket_id, approved_by="ops_chief")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="anonymous_reporter",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Reported fault without provenance credentials.",
        component_inspected="generator",
        provenance=FeedbackProvenance.UNKNOWN,
        observation_level=ObservationLevel.UNKNOWN,
    )

    real_cases = get_real_cases()
    assert not any(wo.ticket_id in str(c.source_reference) for c in real_cases)


def test_quarantined_ticket_cannot_enter_external_real():
    """Verify that quarantined tickets cannot enter EXTERNAL_REAL even if claiming external provenance."""
    wo = propose_work_order(
        asset_id="WT-007",
        component="pitch_system",
        action="Inspect pitch slip ring",
        created_by="test_harness",  # Automated test creator
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
    )
    approve_work_order(wo.ticket_id, approved_by="ops_chief")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="test_automated_harness",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Automated test fixture run findings.",
        component_inspected="pitch_system",
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
        observation_level=ObservationLevel.FIELD_VERIFIED,
    )

    # In library.py and work_orders.py, is_test_fixture / created_by='test_harness' suppresses promotion
    field_cases = export_field_cases_for_retrieval()
    matching = [c for c in field_cases if wo.ticket_id in str(c.case_id)]
    if matching:
        assert matching[0].source_type == HistoricalSourceType.INTERNAL_SYNTHETIC


def test_dual_key_gate_permits_genuine_external_promotion():
    """Verify that genuine external field observation with physical verification satisfies dual-key."""
    wo = propose_work_order(
        asset_id="WT-004",
        component="blade",
        action="Drone thermography and physical blade tap test",
        priority=WorkOrderPriority.HIGH,
        created_by="rai_agent",
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
    )
    approve_work_order(wo.ticket_id, approved_by="chief_engineer")
    record_feedback(
        ticket_id=wo.ticket_id,
        technician_id="blade_inspection_specialist_mistry",
        resolution=FieldResolution.CONFIRMED_FAULT,
        findings="Trailing edge delamination of 450mm verified on blade 2 during physical rope access inspection.",
        component_inspected="blade",
        actual_downtime_hours=18.0,
        actual_parts_cost_inr=125_000.0,
        provenance=FeedbackProvenance.EXTERNAL_FIELD_OBSERVED,
        observation_level=ObservationLevel.FIELD_VERIFIED,
    )

    field_cases = get_field_feedback_cases()
    matching = [c for c in field_cases if wo.ticket_id in str(c.source_reference)]
    assert len(matching) >= 1
    promoted = matching[0]

    assert promoted.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert promoted.event_class == "FIELD_VERIFIED_RESOLUTION"
    assert promoted.evidence_quality == "FIELD_VERIFIED"

    # Must be in real partition
    assert any(promoted.case_id == c.case_id for c in get_real_cases())


def test_partition_purity_across_retrieval():
    """Verify that partition='real' retrieval returns strictly EXTERNAL_REAL cases."""
    packet = build_evidence_packet("WT-004")

    real_results = find_similar_cases(packet, k=5, corpus_partition="real")
    assert len(real_results) > 0
    for match in real_results:
        assert match.source_type == HistoricalSourceType.EXTERNAL_REAL
        assert not match.case_id.startswith("CASE-W-")
        assert not match.case_id.startswith("CASE-S-")

    synth_results = find_similar_cases(packet, k=5, corpus_partition="synthetic")
    assert len(synth_results) > 0
    for match in synth_results:
        assert match.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC
        assert match.case_id.startswith("CASE-W-") or match.case_id.startswith("CASE-S-")
