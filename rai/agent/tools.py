"""The agent's tool registry.

Nine tools. Eight are strictly read-only; the ninth proposes a ticket and cannot dispatch
one. The agent has no path to a physical control action by construction — there is no tool
that writes a setpoint, and adding one would require changing this file.

Each function is a plain callable first and a Needle tool second, so the whole registry is
unit-testable without a model present. Return values are small, flat and JSON-serialisable:
they land in a 256-token context window, so verbosity here directly costs reasoning budget.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from rai.agent.interfaces import (
    resolve_case_memory,
    resolve_economics,
    resolve_evidence_provider,
    resolve_knowledge,
)
from rai.config import ARTIFACTS, get_asset, tariff_for

log = logging.getLogger(__name__)

TICKET_LOG = ARTIFACTS / "tickets.jsonl"
AUDIT_LOG = ARTIFACTS / "agent_audit.jsonl"


def _unavailable(component: str, detail: str) -> dict[str, Any]:
    """Tools never raise into the model. They report unavailability as data."""
    return {"available": False, "component": component, "detail": detail}


def _round(value: Any, digits: int = 3) -> Any:
    return round(value, digits) if isinstance(value, int | float) else value


# --------------------------------------------------------------------------- read-only tools


def get_asset_evidence(asset_id: str) -> dict[str, Any]:
    """Get the computed anomaly and risk evidence for one renewable asset."""
    provider, detail = resolve_evidence_provider()
    if provider is None:
        return _unavailable("evidence", detail)
    try:
        packet = provider.build_evidence_packet(asset_id)
    except Exception as exc:  # noqa: BLE001
        return _unavailable("evidence", f"{type(exc).__name__}: {exc}")
    return packet.to_agent_dict()


def get_weather_context(asset_id: str) -> dict[str, Any]:
    """Check whether weather, curtailment or a faulty sensor explains the deviation."""
    provider, detail = resolve_evidence_provider()
    if provider is None:
        return _unavailable("evidence", detail)
    try:
        env = provider.build_evidence_packet(asset_id).environment
    except Exception as exc:  # noqa: BLE001
        return _unavailable("evidence", f"{type(exc).__name__}: {exc}")
    if env is None:
        return _unavailable("environment", "no environmental attribution computed")
    return {
        "verdict": env.verdict.value,
        "explains_fraction": _round(env.explains_fraction, 2),
        "curtailment_detected": env.curtailment_detected,
        "sensor_health": env.sensor_health.value,
        "operating_state": env.operating_state.value,
        "conditions": {k: _round(v, 2) for k, v in list(env.conditions.items())[:5]},
    }


def get_soiling_estimate(asset_id: str) -> dict[str, Any]:
    """Get the soiling loss estimate and rain outlook for a solar asset."""
    provider, detail = resolve_evidence_provider()
    if provider is None:
        return _unavailable("evidence", detail)
    try:
        soiling = provider.build_evidence_packet(asset_id).soiling
    except Exception as exc:  # noqa: BLE001
        return _unavailable("evidence", f"{type(exc).__name__}: {exc}")
    if soiling is None:
        return {"applicable": False, "reason": "not a solar asset or soiling not estimated"}
    return {
        "applicable": True,
        "soiling_loss_pct": _round(soiling.soiling_loss_pct, 2),
        "soiling_rate_pct_per_day": _round(soiling.soiling_rate_pct_per_day, 3),
        "days_since_rain": _round(soiling.days_since_rain, 1),
        "rain_probability_48h": _round(soiling.rain_probability_48h, 2),
        "method": soiling.method,
    }


def search_similar_cases(asset_id: str, k: int = 3) -> dict[str, Any]:
    """Find contextual historical cases; a match is not a confirmed diagnosis."""
    provider, ev_detail = resolve_evidence_provider()
    memory, mem_detail = resolve_case_memory()
    if provider is None:
        return _unavailable("evidence", ev_detail)
    if memory is None:
        return _unavailable("case_memory", mem_detail)
    try:
        packet = provider.build_evidence_packet(asset_id)
        cases = memory.find_similar_cases(packet, k=k)
    except Exception as exc:  # noqa: BLE001
        return _unavailable("case_memory", f"{type(exc).__name__}: {exc}")
    return {
        "count": len(cases),
        "cases": [
            {
                "case_id": c.case_id,
                "similarity": _round(c.similarity, 2),
                "component": c.component,
                "fault_mode": c.fault_mode,
                "outcome": c.outcome[:120],
                "lead_time_days": _round(c.lead_time_days, 1),
                "source": c.source,
                "source_type": c.source_type.value,
                "evidence_states": {key: state.value for key, state in c.evidence_states.items()},
                "why_matched": c.why_matched,
                "what_is_similar": c.what_is_similar,
                "what_is_different": c.what_is_different,
                "why_may_not_apply": c.why_may_not_apply,
            }
            for c in cases
        ],
    }


def get_case_details(case_id: str) -> dict[str, Any]:
    """Retrieve one provenance-labelled case without raw telemetry."""
    memory, detail = resolve_case_memory()
    if memory is None:
        return _unavailable("case_memory", detail)
    case = memory.get_case_details(case_id)
    if case is None:
        return {"available": True, "status": "INSUFFICIENT_EVIDENCE", "case_id": case_id}
    return {"available": True, "status": "RETRIEVED", "case": case.model_dump(mode="json")}


def compare_case(asset_id: str, case_id: str) -> dict[str, Any]:
    """Explain numerical match contributions while keeping the agent bounded to structured data."""
    provider, ev_detail = resolve_evidence_provider()
    memory, mem_detail = resolve_case_memory()
    if provider is None:
        return _unavailable("evidence", ev_detail)
    if memory is None:
        return _unavailable("case_memory", mem_detail)
    try:
        packet = provider.build_evidence_packet(asset_id)
        details = memory.get_case_details(case_id)
        if details is None:
            return {"available": True, "status": "INSUFFICIENT_EVIDENCE", "case_id": case_id}
        return {
            "available": True,
            "status": "RETRIEVED",
            "case_id": case_id,
            "feature_distances": memory.explain_match(packet, case_id),
            "source_type": details.source_type.value,
        }
    except Exception as exc:  # noqa: BLE001
        return _unavailable("case_memory", f"{type(exc).__name__}: {exc}")


def search_knowledge(query: str, k: int = 3) -> dict[str, Any]:
    """Search maintenance manuals, SOPs and incident reports for relevant procedure text."""
    index, detail = resolve_knowledge()
    if index is None:
        return _unavailable("knowledge", detail)
    try:
        hits = index.search(query, k=k)
    except Exception as exc:  # noqa: BLE001
        return _unavailable("knowledge", f"{type(exc).__name__}: {exc}")
    return {
        "count": len(hits),
        "results": [
            {
                "doc_id": h.doc_id,
                "title": h.title,
                "section": h.section,
                "snippet": h.snippet[:220],
            }
            for h in hits
        ],
    }


def estimate_economic_impact(asset_id: str, component: str = "gearbox") -> dict[str, Any]:
    """Cost the intervention options for an asset. All arithmetic happens here, not in the model."""
    provider, ev_detail = resolve_evidence_provider()
    econ, econ_detail = resolve_economics()
    if econ is None:
        return _unavailable("economics", econ_detail)
    failure_probability = 0.0
    window: tuple[int, int] | None = None
    if provider is not None:
        try:
            packet = provider.build_evidence_packet(asset_id)
            failure_probability = packet.risk.risk_score
            window = packet.risk.risk_window_days
        except Exception as exc:  # noqa: BLE001
            return _unavailable("evidence", f"{type(exc).__name__}: {exc}")
    else:
        return _unavailable("evidence", ev_detail)

    try:
        evidence = econ.evaluate_options(
            asset_id=asset_id,
            component=component,
            failure_probability=failure_probability,
            risk_window_days=window,
        )
    except Exception as exc:  # noqa: BLE001
        return _unavailable("economics", f"{type(exc).__name__}: {exc}")

    return {
        "tariff_inr_per_kwh": tariff_for(asset_id),
        "recommended_option_id": evidence.recommended_option_id,
        "avoidable_exposure_inr": _round(evidence.avoidable_exposure_inr, 0),
        "options": [
            {
                "option_id": o.option_id,
                "delay_days": o.delay_days,
                "expected_exposure_inr": _round(o.expected_exposure_inr, 0),
            }
            for o in evidence.options
        ],
    }


# --------------------------------------------------------------------------- the one write tool


def create_inspection_ticket(
    asset_id: str,
    component: str,
    action: str,
    deadline_hours: int = 72,
) -> dict[str, Any]:
    """Propose a maintenance inspection ticket for human approval. Does not dispatch work."""
    try:
        asset = get_asset(asset_id)
    except KeyError:
        return {"created": False, "reason": f"unknown asset_id {asset_id}"}

    now = datetime.now(UTC)
    ticket = {
        "ticket_id": f"TCK-{asset_id}-{now:%Y%m%dT%H%M%SZ}",
        "asset_id": asset_id,
        "asset_name": asset.name,
        "site": asset.site,
        "component": component,
        "action": action[:400],
        "deadline_hours": int(deadline_hours),
        "status": "proposed_awaiting_human_approval",
        "created_at": now.isoformat(),
        "created_by": "rai_agent",
    }
    TICKET_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TICKET_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ticket) + "\n")
    return {
        "created": True,
        "ticket_id": ticket["ticket_id"],
        "status": ticket["status"],
        "note": "Proposed only. A human must approve before any work is dispatched.",
    }


# --------------------------------------------------------------------------- canonical aliases

get_asset_status = get_asset_evidence
retrieve_historical_cases = search_similar_cases
get_economic_options = estimate_economic_impact

# --------------------------------------------------------------------------- registry


READ_ONLY_TOOLS = [
    get_asset_evidence,
    get_weather_context,
    get_soiling_estimate,
    search_similar_cases,
    get_case_details,
    compare_case,
    search_knowledge,
    estimate_economic_impact,
]

ALL_TOOLS = [*READ_ONLY_TOOLS, create_inspection_ticket]

TOOL_BY_NAME = {
    **{fn.__name__: fn for fn in ALL_TOOLS},
    "get_asset_status": get_asset_status,
    "retrieve_historical_cases": retrieve_historical_cases,
    "get_economic_options": get_economic_options,
}


def needle_tools(include_write: bool = True) -> list[Any]:
    """Return the registry decorated for Needle. Empty list if Needle is not importable."""
    try:
        import needle
    except Exception as exc:  # noqa: BLE001
        log.info("needle not importable, tool registry not decorated: %s", exc)
        return []
    selected = ALL_TOOLS if include_write else READ_ONLY_TOOLS
    return [needle.tool(fn) for fn in selected]


def audit(entry: dict[str, Any]) -> None:
    """Append-only audit record. Every agent decision is written here with its evidence."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {"at": datetime.now(UTC).isoformat(), **entry}
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")
