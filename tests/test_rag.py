"""Unit tests for SQLite FTS5 RAG retrieval engine."""

from __future__ import annotations

from rai.agent.interfaces import probe_capabilities, resolve_knowledge
from rai.rag.retrieve import get_document, list_documents, search


def test_capabilities_knowledge_resolved():
    know, detail = resolve_knowledge()
    assert know is not None
    assert detail == "ok"

    cap = probe_capabilities()
    assert cap.knowledge is True
    assert not cap.degraded


def test_search_soiling():
    results = search("soiling cleaning module rain", k=3)
    assert len(results) > 0
    assert any("soiling" in r.title.lower() or "soiling" in r.section.lower() for r in results)
    assert results[0].score > 0.0
    assert len(results[0].snippet) > 0
    assert results[0].retrieval == "fts5"


def test_search_with_filter():
    results = search("gearbox oil inspection", k=3, asset_type="wind_turbine", component="gearbox")
    assert len(results) > 0
    assert all("gearbox" in r.title.lower() or "wind" in r.title.lower() for r in results)


def test_list_and_get_document():
    docs = list_documents()
    assert len(docs) == 19
    doc_ids = {d["doc_id"] for d in docs}
    assert "solar-soiling-cleaning-sop" in doc_ids

    doc = get_document("solar-soiling-cleaning-sop")
    assert doc is not None
    assert doc["doc_id"] == "solar-soiling-cleaning-sop"
    assert len(doc["sections"]) > 0
    assert any("Scope and applicability" in s["section"] for s in doc["sections"])
