"""Unit tests for Real Historical Case Corpus & Provenance-Tracked Retrieval."""

from __future__ import annotations

from rai.agent.query_agent import AgentQueryStatus, InvestigatorAgent
from rai.agent.tools import search_similar_cases
from rai.memory.library import cases_for
from rai.memory.real_corpus import REAL_RECORDS, RealEventClass
from rai.memory.retrieval import find_similar_cases
from rai.models.pipeline import build_evidence_packet
from rai.schemas import AssetType, HistoricalSourceType


def test_real_case_provenance_and_adjudication():
    """Verify that every real case in the corpus preserves complete source lineage."""
    assert len(REAL_RECORDS) >= 12, "Corpus must have at least 12 audited real cases"

    for rec in REAL_RECORDS:
        case = rec.to_case()
        assert case.source_type == HistoricalSourceType.EXTERNAL_REAL
        assert case.source_dataset, f"Missing source dataset for {case.case_id}"
        assert case.source_reference, f"Missing source reference for {case.case_id}"
        assert case.license, f"Missing license for {case.case_id}"
        assert case.event_class in [e.value for e in RealEventClass]
        assert case.evidence_quality, f"Missing evidence quality for {case.case_id}"
        assert len(case.limitations) > 0, f"Missing limitations for {case.case_id}"
        assert case.adjudication is not None
        assert "what_is_explicitly_known" in case.adjudication
        assert "what_source_proves" in case.adjudication
        assert "what_source_does_not_prove" in case.adjudication


def test_real_synthetic_partition_separation():
    """Verify clean partition separation between EXTERNAL_REAL and INTERNAL_SYNTHETIC."""
    # Real wind partition
    real_wind = cases_for(AssetType.WIND_TURBINE, partition="real")
    assert len(real_wind) > 0
    assert all(c.source_type == HistoricalSourceType.EXTERNAL_REAL for c in real_wind)
    assert not any(c.case_id.startswith("CASE-W-") for c in real_wind)

    # Synthetic wind partition
    synth_wind = cases_for(AssetType.WIND_TURBINE, partition="synthetic")
    assert len(synth_wind) > 0
    assert all(c.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC for c in synth_wind)
    assert all(c.case_id.startswith("CASE-W-") for c in synth_wind)

    # All partition contains both real and synthetic benchmark cases
    all_wind = cases_for(AssetType.WIND_TURBINE, partition="all")
    assert len(all_wind) >= len(real_wind) + len(synth_wind)
    assert all(c in all_wind for c in real_wind)
    assert all(c in all_wind for c in synth_wind)


def test_retrieval_partition_filtering():
    """find_similar_cases respects corpus_partition parameter."""
    packet = build_evidence_packet("WT-017")

    # Real partition retrieval
    real_matches = find_similar_cases(packet, k=5, corpus_partition="real")
    assert len(real_matches) > 0
    assert all(m.source_type == HistoricalSourceType.EXTERNAL_REAL for m in real_matches)

    # Synthetic partition retrieval
    synth_matches = find_similar_cases(packet, k=5, corpus_partition="synthetic")
    assert len(synth_matches) > 0
    assert all(m.source_type == HistoricalSourceType.INTERNAL_SYNTHETIC for m in synth_matches)


def test_retrieval_match_explanations():
    """Retrieved cases must include why_matched, what_is_different, and why_may_not_apply."""
    packet = build_evidence_packet("WT-017")
    matches = find_similar_cases(packet, k=3, corpus_partition="real")

    assert len(matches) > 0
    top = matches[0]
    assert len(top.why_matched) > 0, "why_matched must not be empty"
    assert top.what_is_different is not None
    assert len(top.why_may_not_apply) > 0, "why_may_not_apply must qualify limitations"


def test_anti_fabrication_boundary():
    """Operational events and environmental events must NOT be marked as equipment faults."""
    for rec in REAL_RECORDS:
        case = rec.to_case()
        if rec.event_class == RealEventClass.REAL_OPERATIONAL_EVENT:
            assert not case.equipment_fault, (
                f"Violation: Operational event {rec.case_id} was improperly upgraded to equipment failure"
            )
        elif rec.event_class == RealEventClass.ENVIRONMENTAL_EVENT:
            assert not case.equipment_fault, (
                f"Violation: Environmental event {rec.case_id} was improperly marked as equipment failure"
            )


def test_solar_real_case_retrieval():
    """Solar inverter retrieval returns real PVDAQ cases with provenance."""
    packet = build_evidence_packet("INV-001")
    matches = find_similar_cases(packet, k=3, corpus_partition="real")

    assert len(matches) > 0
    top = matches[0]
    assert top.case_id == "REAL-PVDAQ-034-OUTAGE"
    assert top.source_type == HistoricalSourceType.EXTERNAL_REAL
    assert "PVDAQ" in top.source


def test_agent_tool_search_similar_cases_partition():
    """search_similar_cases tool supports partition and preserves provenance."""
    res = search_similar_cases("WT-004", k=3, corpus_partition="real")
    assert res["count"] > 0
    assert res["corpus_partition"] == "real"
    for c in res["cases"]:
        assert c["source_type"] == "EXTERNAL_REAL"
        assert "why_matched" in c
        assert "what_is_different" in c
        assert "why_may_not_apply" in c


def test_agent_query_real_case_adjudication():
    """InvestigatorAgent retrieves real case and explicitly qualifies the match."""
    agent = InvestigatorAgent(force_deterministic=True)
    resp = agent.answer_query("Are there any real past cases similar to WT-017?", asset_id="WT-017")

    assert resp.status == AgentQueryStatus.ANSWERED
    assert len(resp.evidence_items) > 0
    assert any(item.source_type == "EXTERNAL_REAL" for item in resp.evidence_items)
    assert "REAL" in resp.answer.upper() or "EXTERNAL_REAL" in resp.answer
    assert "precedent" in resp.answer.lower() or "do not prove" in resp.answer.lower() or "context" in resp.answer.lower()
