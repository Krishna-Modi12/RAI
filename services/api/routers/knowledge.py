"""Knowledge search and documentation router complying with docs/API_CONTRACT.md."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from rai.rag.retrieve import get_document, list_documents, search

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search")
def search_knowledge(
    q: str = Query(..., description="Search query string"),
    k: int = Query(default=5),
    asset_type: str | None = Query(default=None),
) -> dict[str, Any]:
    citations = search(query=q, k=k, asset_type=asset_type)
    return {
        "query": q,
        "results": [c.model_dump(mode="json") for c in citations],
    }


@router.get("/docs")
def get_knowledge_docs() -> list[dict[str, Any]]:
    docs = list_documents()
    detailed = []
    for d in docs:
        doc = get_document(d["doc_id"])
        n_sec = len(doc["sections"]) if doc else 1
        detailed.append({
            "doc_id": d["doc_id"],
            "title": d["title"],
            "asset_type": d["asset_type"],
            "component": d["component"],
            "kind": d["kind"],
            "sections": n_sec,
            "source_note": "Illustrative sample document authored for this project",
        })
    return detailed
