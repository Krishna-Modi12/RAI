"""Interfaces the agent layer depends on.

These signatures are the contract between the agent layer and the intelligence layer.
The agent layer is written against them; `rai/models`, `rai/memory` and `rai/economics`
implement them. Resolution is lazy and failure is explicit, so the agent degrades to a
clearly-labelled reduced mode instead of crashing when a component is not yet trained.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rai.schemas import (
    AssetState,
    EconomicEvidence,
    EvidencePacket,
    HistoricalCase,
    KnowledgeCitation,
)


class ComponentUnavailable(RuntimeError):
    """A required intelligence component is not built or not trained yet."""

    def __init__(self, component: str, detail: str) -> None:
        super().__init__(f"{component} unavailable: {detail}")
        self.component = component
        self.detail = detail


# --------------------------------------------------------------------------- protocols


class EvidenceProvider(Protocol):
    def build_evidence_packet(self, asset_id: str, as_of: object | None = None) -> EvidencePacket: ...

    def compute_asset_state(self, asset_id: str, as_of: object | None = None) -> AssetState: ...


class CaseMemory(Protocol):
    def find_similar_cases(self, packet: EvidencePacket, k: int = 5) -> list[HistoricalCase]: ...


class EconomicsEngine(Protocol):
    def evaluate_options(
        self,
        asset_id: str,
        component: str,
        failure_probability: float,
        risk_window_days: tuple[int, int] | None = None,
    ) -> EconomicEvidence: ...


class KnowledgeIndex(Protocol):
    def search(
        self,
        query: str,
        k: int = 5,
        asset_type: str | None = None,
        component: str | None = None,
    ) -> list[KnowledgeCitation]: ...


# --------------------------------------------------------------------------- resolution


@dataclass(frozen=True)
class Capabilities:
    """What is actually wired up right now. Surfaced by GET /api/health."""

    evidence: bool
    cases: bool
    economics: bool
    knowledge: bool
    needle: bool
    detail: dict[str, str]

    @property
    def degraded(self) -> bool:
        return not all((self.evidence, self.cases, self.economics, self.knowledge))


def _try(label: str, fn) -> tuple[object | None, str]:
    try:
        return fn(), "ok"
    except Exception as exc:  # noqa: BLE001 - capability probe, any failure is informative
        return None, f"{type(exc).__name__}: {exc}"


def resolve_evidence_provider() -> tuple[EvidenceProvider | None, str]:
    def load():
        from rai.models import pipeline

        for name in ("build_evidence_packet", "compute_asset_state"):
            if not hasattr(pipeline, name):
                raise AttributeError(f"rai.models.pipeline.{name} missing")
        return pipeline

    return _try("evidence", load)  # type: ignore[return-value]


def resolve_case_memory() -> tuple[CaseMemory | None, str]:
    def load():
        from rai.memory import retrieval

        if not hasattr(retrieval, "find_similar_cases"):
            raise AttributeError("rai.memory.retrieval.find_similar_cases missing")
        return retrieval

    return _try("cases", load)  # type: ignore[return-value]


def resolve_economics() -> tuple[EconomicsEngine | None, str]:
    def load():
        from rai.economics import engine

        if not hasattr(engine, "evaluate_options"):
            raise AttributeError("rai.economics.engine.evaluate_options missing")
        return engine

    return _try("economics", load)  # type: ignore[return-value]


def resolve_knowledge() -> tuple[KnowledgeIndex | None, str]:
    def load():
        from rai.rag import retrieve

        if not hasattr(retrieve, "search"):
            raise AttributeError("rai.rag.retrieve.search missing")
        return retrieve

    return _try("knowledge", load)  # type: ignore[return-value]


def probe_capabilities() -> Capabilities:
    from rai.agent.runtime import needle_available

    evidence, ev_detail = resolve_evidence_provider()
    cases, case_detail = resolve_case_memory()
    econ, econ_detail = resolve_economics()
    know, know_detail = resolve_knowledge()
    needle_ok, needle_detail = needle_available()

    return Capabilities(
        evidence=evidence is not None,
        cases=cases is not None,
        economics=econ is not None,
        knowledge=know is not None,
        needle=needle_ok,
        detail={
            "evidence": ev_detail,
            "cases": case_detail,
            "economics": econ_detail,
            "knowledge": know_detail,
            "needle": needle_detail,
        },
    )
