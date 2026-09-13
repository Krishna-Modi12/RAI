"""Needle 2 runtime.

Needle 2 (`cactus-needle`, Apache-2.0) is a 45M-parameter tool-calling model that ships as a
~14 MB binary and runs a session in ~28 MB of RAM — small enough to live on an edge gateway
next to the SCADA historian, which is the whole point of keeping this local.

Verified API surface (inspected from the installed package):
    needle.Needle(tools=None, system=None, weights=None, tool_index_path=None, buffer_size=65536)
    Needle.run(query="", max_steps=8, max_new_tokens=256, ..., strict=True) -> dict
    needle.extract(text, schema, system=None, max_new_tokens=256, weights=None, strict=True)
    @needle.tool  decorator over a typed function with a docstring

The native library and weights are fetched from the HuggingFace Hub on first construction.
Where the Hub is unreachable, `available()` reports False with the reason and every caller
falls through to `rai.agent.fallback`. Run `python scripts/warmup_needle.py` once on an
unrestricted network to cache them.

Division of labour, deliberately: Needle decides and explains. Python computes. Every number
in the verdict originates from a tool return value, never from the model's own arithmetic.
"""

from __future__ import annotations

import contextlib
import json
import logging
import threading
import time
from typing import Any

from rai.config import settings
from rai.schemas import (
    AgentVerdict,
    EconomicEvidence,
    EvidencePacket,
    HistoricalCase,
    KnowledgeCitation,
    Severity,
)

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a renewable-asset maintenance analyst. Use the tools to gather evidence before "
    "answering. Rules: never assert an equipment fault until weather, curtailment, peer "
    "behaviour and sensor health have been checked; never compute numbers yourself, use the "
    "values the tools return; if the evidence is contradictory or thin, say a human must "
    "review it."
)

_probe: tuple[bool, str] | None = None


def needle_available() -> tuple[bool, str]:
    """Probe once whether a Needle session can actually be constructed.

    Cached for the process lifetime: construction attempts a network fetch, so repeating it
    on every request would make a degraded environment slow as well as degraded.
    """
    global _probe
    if _probe is not None:
        return _probe

    try:
        import needle
    except Exception as exc:  # noqa: BLE001
        _probe = (False, f"cactus-needle not importable: {type(exc).__name__}: {exc}")
        return _probe

    try:
        needle.Needle(system="probe")
        _probe = (True, "needle 2 session constructed")
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).splitlines()[-1] if str(exc) else type(exc).__name__
        _probe = (False, f"weights unavailable ({type(exc).__name__}: {detail[:160]})")
    return _probe


VERDICT_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "likely_cause": {"type": "string"},
        "component": {"type": "string"},
        "severity": {
            "type": "string",
            "enum": ["informational", "low", "medium", "high", "critical"],
        },
        "is_equipment_fault": {"type": "boolean"},
        "recommended_action": {"type": "string"},
    },
    "required": ["likely_cause", "component", "severity", "is_equipment_fault", "recommended_action"],
}


class NeedleRuntime:
    """Thin wrapper that keeps one Needle session alive across investigations.

    The underlying `needle.Needle` session is a single native inference session shared
    across every request this process handles. Concurrent `/investigate` calls invoking
    `.run()`/`.extract()` on it simultaneously from different threads (FastAPI runs sync
    routes in a thread pool) reliably crashed the API process -- reproduced by firing just
    4 concurrent investigate requests twice in a row. A single lock serializes access: one
    investigation uses the native session at a time, the rest queue briefly instead of
    corrupting shared native state.
    """

    def __init__(self, tools: list[Any] | None = None) -> None:
        import needle

        self._needle = needle
        self._agent = needle.Needle(tools=tools or [], system=SYSTEM_PROMPT)
        self._tools = tools or []
        self._lock = threading.Lock()

    def run_investigation(self, packet: EvidencePacket) -> tuple[dict[str, Any], list[str]]:
        """Let the model drive tool calls. Returns (raw result, tool names invoked)."""
        query = (
            f"Investigate asset {packet.asset_id}. Its risk band is "
            f"{packet.risk.risk_band.value} with anomaly score "
            f"{packet.anomaly.anomaly_score:.2f}. Gather evidence and diagnose the cause."
        )
        with self._lock:
            result = self._agent.run(
                query,
                max_steps=settings.agent_max_tools_per_turn + 3,
                max_new_tokens=256,
                strict=True,
            )
        return result, _extract_tool_names(result)

    def extract_verdict(self, packet: EvidencePacket, digest: str) -> dict[str, Any]:
        """Constrained-decode the decision fields from the evidence digest."""
        with self._lock:
            out = self._needle.extract(
                digest,
                VERDICT_EXTRACTION_SCHEMA,
                system=SYSTEM_PROMPT,
                max_new_tokens=256,
                strict=True,
            )
        if isinstance(out, str):
            out = json.loads(out)
        if hasattr(out, "model_dump"):
            out = out.model_dump()
        return dict(out)

    def confidence_of(self, result: dict[str, Any]) -> float | None:
        for key in ("confidence", "score", "calibrated_confidence"):
            value = result.get(key)
            if isinstance(value, int | float):
                return float(value)
        return None


def _extract_tool_names(result: dict[str, Any]) -> list[str]:
    """Pull invoked tool names out of Needle's result dict, tolerating shape differences."""
    names: list[str] = []
    for key in ("tool_calls", "calls", "steps", "trace"):
        entries = result.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, str):
                names.append(entry)
            elif isinstance(entry, dict):
                for nk in ("name", "tool", "tool_name", "function"):
                    if isinstance(entry.get(nk), str):
                        names.append(entry[nk])
                        break
    seen: set[str] = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def build_digest(
    packet: EvidencePacket,
    cases: list[HistoricalCase],
    citations: list[KnowledgeCitation],
    economics: EconomicEvidence | None,
) -> str:
    """Compact text digest for constrained extraction.

    Needle 2 operates in a 256-token sliding window, so this is deliberately terse and
    contains only computed evidence — never raw telemetry.
    """
    lines = [json.dumps(packet.to_agent_dict(), separators=(",", ":"))]
    if cases:
        best = max(cases, key=lambda c: c.similarity)
        lines.append(
            f"closest_case={best.case_id} sim={best.similarity:.2f} "
            f"component={best.component} outcome={best.outcome[:80]}"
        )
    if citations:
        lines.append(f"procedure={citations[0].title}|{citations[0].section}")
    if economics and economics.recommended_option_id:
        lines.append(f"economics_recommends={economics.recommended_option_id}")
    return "\n".join(lines)


def verdict_from_needle(
    runtime: NeedleRuntime,
    packet: EvidencePacket,
    cases: list[HistoricalCase],
    citations: list[KnowledgeCitation],
    economics: EconomicEvidence | None,
    baseline: AgentVerdict,
) -> AgentVerdict:
    """Produce a Needle-authored verdict, keeping every number from Python.

    `baseline` is the deterministic verdict. Where Needle's output is missing, unparseable or
    low-confidence, the baseline field wins — so the model can improve the explanation but
    cannot degrade correctness.
    """
    started = time.perf_counter()
    tool_names: list[str] = []
    try:
        raw, tool_names = runtime.run_investigation(packet)
        digest = build_digest(packet, cases, citations, economics)
        fields = runtime.extract_verdict(packet, digest)
        model_confidence = runtime.confidence_of(raw)
    except Exception as exc:  # noqa: BLE001 - any runtime failure must degrade, not crash
        log.warning("needle investigation failed for %s: %s", packet.asset_id, exc)
        return baseline.model_copy(
            update={
                "model_used": "deterministic_reasoner",
                "fallback_used": True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "tool_calls": tool_names,
            }
        )

    severity = baseline.severity
    if raw_sev := fields.get("severity"):
        with contextlib.suppress(ValueError):
            severity = Severity(raw_sev)

    confidence = model_confidence if model_confidence is not None else baseline.confidence
    # A model-authored equipment claim that contradicts the rule chain is not trusted silently.
    contradicts = bool(fields.get("is_equipment_fault")) and baseline.component == "none"
    requires_review = (
        contradicts
        or confidence < settings.needle_confidence_threshold
        or baseline.requires_human_review
    )

    return AgentVerdict(
        asset_id=packet.asset_id,
        likely_cause=str(fields.get("likely_cause") or baseline.likely_cause),
        component=str(fields.get("component") or baseline.component),
        severity=severity,
        confidence=round(float(confidence), 3),
        requires_human_review=requires_review,
        recommended_action=str(fields.get("recommended_action") or baseline.recommended_action),
        action_deadline_hours=baseline.action_deadline_hours,
        evidence_summary=baseline.evidence_summary,
        historical_cases=cases[:5],
        citations=citations[:3],
        economics=economics,
        model_used="needle2",
        fallback_used=False,
        tool_calls=tool_names,
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
    )
