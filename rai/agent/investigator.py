"""Investigation orchestration.

Runs the evidence chain in a fixed order and records each step, because the order *is* the
argument: telemetry, then expected behaviour, then environment, then peers, then history,
then procedure, then economics, and only then a decision. The UI replays this timeline so an
operator can see that the conclusion was reached by elimination rather than asserted.

The deterministic reasoner always produces a verdict. When Needle is available it is layered
on top to author the explanation, and it can never overwrite a computed number.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from rai.agent import fallback
from rai.agent.interfaces import (
    resolve_case_memory,
    resolve_economics,
    resolve_evidence_provider,
    resolve_knowledge,
)
from rai.agent.runtime import NeedleRuntime, needle_available, verdict_from_needle
from rai.agent.tools import audit, needle_tools
from rai.config import settings
from rai.schemas import (
    AgentVerdict,
    EconomicEvidence,
    EvidencePacket,
    HistoricalCase,
    Investigation,
    InvestigationStep,
    KnowledgeCitation,
)

log = logging.getLogger(__name__)

_runtime: NeedleRuntime | None = None
_runtime_tried = False


def _get_runtime() -> NeedleRuntime | None:
    """Construct the Needle session at most once per process."""
    global _runtime, _runtime_tried
    if _runtime_tried:
        return _runtime
    _runtime_tried = True
    ok, detail = needle_available()
    if not ok:
        log.info("needle unavailable, deterministic reasoner active: %s", detail)
        return None
    try:
        _runtime = NeedleRuntime(tools=needle_tools())
    except Exception as exc:  # noqa: BLE001
        log.warning("needle runtime construction failed: %s", exc)
        _runtime = None
    return _runtime


class _Timeline:
    def __init__(self) -> None:
        self.steps: list[InvestigationStep] = []

    def add(self, stage: str, label: str, detail: str | None = None, status: str = "done") -> None:
        self.steps.append(
            InvestigationStep(
                at=datetime.now(UTC), stage=stage, label=label, detail=detail, status=status  # type: ignore[arg-type]
            )
        )


def investigate(asset_id: str, force_refresh: bool | None = False) -> Investigation:
    """Run a full investigation; pass None to disable the optional Needle runtime."""
    started = datetime.now(UTC)
    timeline = _Timeline()

    provider, detail = resolve_evidence_provider()
    if provider is None:
        raise RuntimeError(f"evidence provider unavailable: {detail}")

    packet: EvidencePacket = provider.build_evidence_packet(asset_id)
    timeline.add(
        "telemetry",
        "Evidence packet assembled",
        f"{len(packet.anomaly.signals)} signals, "
        f"{packet.anomaly.persistence_hours:.1f} h persistence",
    )
    timeline.add(
        "expected_behavior",
        "Expected-behaviour residuals computed",
        _describe_dominant(packet),
    )
    timeline.add("environment", *_describe_environment(packet))
    timeline.add("peers", *_describe_peers(packet))

    # First pass: the rule chain tells us which component to look up procedures for.
    provisional = fallback.diagnose(packet)

    cases = _load_cases(packet, timeline)
    citations = _load_citations(packet, provisional, timeline)
    economics = _load_economics(asset_id, provisional.component, packet, timeline)

    baseline = fallback.diagnose(packet, cases=cases, citations=citations, economics=economics)

    runtime = None if force_refresh is None else _get_runtime()
    verdict: AgentVerdict = baseline
    if runtime is not None:
        verdict = verdict_from_needle(
            runtime, packet, cases, citations, economics, baseline=baseline
        )

    gate = (
        "escalated for human review"
        if verdict.requires_human_review
        else f"confidence {verdict.confidence:.0%} above the {settings.needle_confidence_threshold:.0%} threshold"
    )
    timeline.add(
        "decision",
        "Recommendation generated" if not verdict.requires_human_review else "Escalated to human review",
        f"{verdict.likely_cause} ({verdict.model_used}); {gate}",
    )

    completed = datetime.now(UTC)
    investigation = Investigation(
        investigation_id=f"inv_{asset_id}_{started:%Y%m%dT%H%M%SZ}",
        asset_id=asset_id,
        started_at=started,
        completed_at=completed,
        packet=packet,
        verdict=verdict,
        timeline=timeline.steps,
    )

    audit(
        {
            "event": "investigation",
            "investigation_id": investigation.investigation_id,
            "asset_id": asset_id,
            "model_used": verdict.model_used,
            "fallback_used": verdict.fallback_used,
            "component": verdict.component,
            "severity": verdict.severity.value,
            "confidence": verdict.confidence,
            "requires_human_review": verdict.requires_human_review,
            "anomaly_score": packet.anomaly.anomaly_score,
            "risk_score": packet.risk.risk_score,
            "evidence": verdict.evidence_summary,
            "citations": [c.doc_id for c in verdict.citations],
            "cases": [c.case_id for c in verdict.historical_cases],
            "duration_ms": round((completed - started).total_seconds() * 1000, 1),
        }
    )
    return investigation


# --------------------------------------------------------------------------- step helpers


def _describe_dominant(packet: EvidencePacket) -> str:
    name = packet.anomaly.dominant_signal
    if name is None:
        return f"anomaly score {packet.anomaly.anomaly_score:.2f}"
    for s in packet.anomaly.signals:
        if s.name == name:
            parts = [name.replace("_", " ")]
            if s.residual_pct is not None:
                parts.append(f"{s.residual_pct:+.1f}%")
            if s.z_score is not None:
                parts.append(f"z={s.z_score:.1f}")
            return " ".join(parts)
    return f"anomaly score {packet.anomaly.anomaly_score:.2f}"


def _describe_environment(packet: EvidencePacket) -> tuple[str, str]:
    env = packet.environment
    if env is None:
        return "Environmental attribution unavailable", "no environment evidence computed"
    if env.curtailment_detected:
        return "Curtailment identified", "output is commanded down, not degraded"
    if env.sensor_health.value != "ok":
        return "Sensor health flagged", f"sensor validation: {env.sensor_health.value}"
    return (
        "Weather ruled out" if env.verdict.value == "not_environmental" else "Weather partially explains deviation",
        f"conditions account for {env.explains_fraction:.0%} of the deviation",
    )


def _describe_peers(packet: EvidencePacket) -> tuple[str, str]:
    peers = packet.peers
    if peers is None:
        return "Peer comparison unavailable", "no peer evidence computed"
    label = {
        "asset_specific": "Peer comparison isolates this asset",
        "fleet_wide": "Deviation is fleet-wide",
        "normal": "Peer comparison shows no deviation",
    }[peers.verdict.value]
    pct = f", {peers.deviation_percentile:.0f}th percentile" if peers.deviation_percentile is not None else ""
    return label, f"{peers.n_peers} peers in {peers.peer_group}{pct}"


def _load_cases(packet: EvidencePacket, timeline: _Timeline) -> list[HistoricalCase]:
    memory, detail = resolve_case_memory()
    if memory is None:
        timeline.add("history", "Historical memory unavailable", detail, status="skipped")
        return []
    try:
        cases = memory.find_similar_cases(packet, k=5)
    except Exception as exc:  # noqa: BLE001
        timeline.add("history", "Historical memory failed", str(exc)[:160], status="skipped")
        return []
    if not cases:
        timeline.add("history", "No similar historical episodes", "case library returned no match")
        return []
    best = max(cases, key=lambda c: c.similarity)
    timeline.add(
        "history",
        f"{len(cases)} similar historical episodes retrieved",
        f"closest {best.case_id} at {best.similarity:.0%} ({best.component})",
    )
    return cases


def _load_citations(
    packet: EvidencePacket, provisional: AgentVerdict, timeline: _Timeline
) -> list[KnowledgeCitation]:
    index, detail = resolve_knowledge()
    if index is None:
        timeline.add("knowledge", "Knowledge base unavailable", detail, status="skipped")
        return []
    query = f"{provisional.component} {provisional.likely_cause}"
    try:
        hits = index.search(
            query, k=3, asset_type=packet.asset_type.value, component=provisional.component
        )
    except Exception as exc:  # noqa: BLE001
        timeline.add("knowledge", "Knowledge retrieval failed", str(exc)[:160], status="skipped")
        return []
    if not hits:
        timeline.add("knowledge", "No matching procedure found", f"query: {query[:80]}")
        return []
    timeline.add(
        "knowledge",
        "Maintenance procedure retrieved",
        f"{hits[0].title} — {hits[0].section}",
    )
    return hits


def _load_economics(
    asset_id: str, component: str, packet: EvidencePacket, timeline: _Timeline
) -> EconomicEvidence | None:
    econ, detail = resolve_economics()
    if econ is None:
        timeline.add("economics", "Economic engine unavailable", detail, status="skipped")
        return None
    try:
        evidence = econ.evaluate_options(
            asset_id=asset_id,
            component=component,
            failure_probability=packet.risk.risk_score,
            risk_window_days=packet.risk.risk_window_days,
        )
    except Exception as exc:  # noqa: BLE001
        timeline.add("economics", "Economic evaluation failed", str(exc)[:160], status="skipped")
        return None
    detail_text = None
    if evidence.avoidable_exposure_inr is not None:
        detail_text = f"avoidable exposure ₹{evidence.avoidable_exposure_inr:,.0f}"
    timeline.add("economics", "Intervention options costed", detail_text)
    return evidence
