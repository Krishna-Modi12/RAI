"""Deterministic evidence reasoner.

Produces the same `AgentVerdict` contract as the Needle path, using explicit clinical rules
over the evidence packet. It exists for two reasons:

1. The demo must never depend on a model download. Needle 2 fetches weights from the
   HuggingFace Hub on first construction, which is unavailable in some environments.
2. Diagnosis is a decision problem with a small, well-understood rule set. Encoding it
   explicitly makes it auditable, and gives the language model something to explain rather
   than something to invent.

The ordering of the rules is the substance of the system: an equipment fault is only ever
asserted **after** weather, curtailment, sensor health and fleet-wide behaviour have been
ruled out. That ordering is what stops the system crying wolf on a cloudy afternoon.

`confidence` here is a rule-based evidence-agreement score, NOT a learned calibrated
probability. It is reported as such (`model_used="deterministic_reasoner"`) so it is never
mistaken for Needle's calibrated confidence head.
"""

from __future__ import annotations

from dataclasses import dataclass

from rai.config import settings
from rai.models.differential import evaluate_differential_diagnosis
from rai.schemas import (
    AgentVerdict,
    AssetType,
    DifferentialDiagnosisVerdict,
    DifferentialStatus,
    EconomicEvidence,
    EnvironmentVerdict,
    EvidencePacket,
    HistoricalCase,
    KnowledgeCitation,
    PeerVerdict,
    RiskBand,
    SensorHealth,
    Severity,
)

# --------------------------------------------------------------------------- diagnosis map

# Dominant residual signal -> (component, fault description, knowledge query)
SIGNAL_DIAGNOSIS: dict[str, tuple[str, str, str]] = {
    "drivetrain_vibration_mms": (
        "gearbox",
        "Progressive gearbox bearing degradation",
        "gearbox vibration threshold inspection",
    ),
    "gearbox_oil_temp_c": (
        "gearbox",
        "Gearbox thermal anomaly consistent with bearing or lubrication degradation",
        "gearbox oil temperature threshold lubrication",
    ),
    "generator_winding_temp_c": (
        "generator",
        "Generator winding overheating",
        "generator winding temperature cooling",
    ),
    "main_bearing_temp_c": (
        "main_bearing",
        "Main bearing thermal degradation",
        "main bearing temperature inspection",
    ),
    "rotor_rpm": (
        "pitch_system",
        "Rotor speed control deviation consistent with pitch system misbehaviour",
        "pitch system calibration",
    ),
    "power_kw": (
        "pitch_system",
        "Aerodynamic underperformance with no thermal signature",
        "power curve underperformance pitch yaw",
    ),
    "dc_current_a": (
        "dc_string",
        "DC-side current loss consistent with a string or diode failure",
        "string fault isolation dc current",
    ),
    "dc_power_kw": (
        "dc_string",
        "DC-side power loss consistent with a string outage",
        "string fault isolation dc power",
    ),
    "dc_voltage_v": (
        "dc_string",
        "DC voltage deviation consistent with a module or string fault",
        "dc voltage string fault",
    ),
    "inverter_temp_c": (
        "inverter",
        "Inverter thermal derating",
        "inverter thermal derate service",
    ),
    "ac_power_kw": (
        "inverter",
        "AC output shortfall against the irradiance-matched expectation",
        "inverter output shortfall",
    ),
    "performance_ratio": (
        "soiling",
        "Performance-ratio decline consistent with soiling accumulation",
        "module cleaning soiling performance ratio",
    ),
}

SEVERITY_BY_BAND = {
    RiskBand.LOW: Severity.LOW,
    RiskBand.ELEVATED: Severity.MEDIUM,
    RiskBand.HIGH: Severity.HIGH,
    RiskBand.CRITICAL: Severity.CRITICAL,
}

DEADLINE_BY_SEVERITY = {
    Severity.CRITICAL: 24,
    Severity.HIGH: 72,
    Severity.MEDIUM: 168,
    Severity.LOW: 336,
    Severity.INFORMATIONAL: None,
}


@dataclass
class _Diagnosis:
    likely_cause: str
    component: str
    is_equipment_fault: bool
    knowledge_query: str
    severity: Severity
    confidence: float
    reasons: list[str]
    human_review: bool = False


# --------------------------------------------------------------------------- rule chain


def _fmt_signal(packet: EvidencePacket, name: str) -> str | None:
    for s in packet.anomaly.signals:
        if s.name == name:
            bits = []
            if s.residual_pct is not None:
                bits.append(f"{s.residual_pct:+.1f}% vs expected")
            elif s.residual is not None:
                bits.append(f"{s.residual:+.2f} {s.unit} vs expected")
            if s.z_score is not None:
                bits.append(f"z={s.z_score:.1f}")
            if s.trend_per_day:
                bits.append(f"trending {s.trend_per_day:+.2f} {s.unit}/day")
            return f"{name.replace('_', ' ')}: " + ", ".join(bits) if bits else None
    return None


def _environmental_ruling(packet: EvidencePacket) -> _Diagnosis | None:
    """Gate 1. Anything explained by the environment is not an equipment fault."""
    env = packet.environment
    if env is None:
        return None

    if env.curtailment_detected:
        return _Diagnosis(
            likely_cause="Output reduced by grid curtailment instruction, not by asset condition",
            component="none",
            is_equipment_fault=False,
            knowledge_query="curtailment operating state validation",
            severity=Severity.INFORMATIONAL,
            confidence=0.94,
            reasons=[
                "Curtailment flag is set for this interval, so reduced output is commanded rather than faulty",
                f"Operating state reported as {env.operating_state.value}",
            ],
        )

    if env.sensor_health is SensorHealth.FAILED:
        return _Diagnosis(
            likely_cause="Instrumentation fault: the measuring sensor is unreliable, not the asset",
            component="anemometer",
            is_equipment_fault=False,
            knowledge_query="sensor validation frozen drift anemometer",
            severity=Severity.MEDIUM,
            confidence=0.88,
            reasons=[
                "Sensor validation failed, so the apparent deviation is a measurement artifact",
                "Equipment condition cannot be assessed until the sensor is replaced or recalibrated",
            ],
        )

    if env.sensor_health is SensorHealth.SUSPECT:
        return _Diagnosis(
            likely_cause="Suspected sensor drift; equipment condition not confirmed",
            component="anemometer",
            is_equipment_fault=False,
            knowledge_query="sensor validation drift cross-check nacelle",
            severity=Severity.LOW,
            confidence=0.72,
            reasons=[
                "Sensor cross-check flagged the input as suspect, which can mimic underperformance",
                "Recommend sensor validation before any drivetrain intervention",
            ],
            human_review=True,
        )

    if env.verdict is EnvironmentVerdict.ENVIRONMENTAL or env.explains_fraction >= 0.60:
        return _Diagnosis(
            likely_cause="Deviation explained by environmental conditions",
            component="none",
            is_equipment_fault=False,
            knowledge_query="environmental derate irradiance wind conditions",
            severity=Severity.INFORMATIONAL,
            confidence=0.85,
            reasons=[
                f"Environmental conditions account for {env.explains_fraction:.0%} of the observed deviation",
                "No asset-specific signature after conditioning on the environment",
            ],
        )
    return None


def _peer_ruling(packet: EvidencePacket) -> _Diagnosis | None:
    """Gate 2. If the whole peer group moved together, it is not this asset's fault."""
    peers = packet.peers
    if peers is None or peers.verdict is not PeerVerdict.FLEET_WIDE:
        return None
    return _Diagnosis(
        likely_cause="Fleet-wide deviation: a site or grid-level cause, not an asset defect",
        component="none",
        is_equipment_fault=False,
        knowledge_query="site wide underperformance grid event",
        severity=Severity.LOW,
        confidence=0.80,
        reasons=[
            f"All {peers.n_peers} peers in {peers.peer_group} deviate together",
            "An asset-specific defect would not move the peer group with it",
        ],
        human_review=True,
    )


def _soiling_ruling(packet: EvidencePacket) -> _Diagnosis | None:
    """Gate 3. Solar-specific: dirt is recoverable loss, not a defect.

    Soiling accumulates over days. A step change in output is not dirt — it is a string
    dropping offline or an inverter derating — and the performance-ratio estimator cannot
    tell them apart on magnitude alone. Gradualness is the discriminator, so a detected
    change point disqualifies the soiling explanation entirely.
    """
    s = packet.soiling
    if packet.asset_type is not AssetType.SOLAR_INVERTER or s is None:
        return None
    if s.soiling_loss_pct is None or s.soiling_loss_pct < 4.0:
        return None

    step_detected = any(d.detector == "changepoint" and d.fired for d in packet.anomaly.detectors)
    if step_detected and packet.anomaly.dominant_signal != "performance_ratio":
        return None

    # Dirt attenuates photocurrent, so it shows in DC power and current just as an outage
    # does. Voltage and inverter temperature are the channels dirt cannot move: a deviation
    # led by either of those is hardware.
    if packet.anomaly.dominant_signal in {"dc_voltage_v", "inverter_temp_c"}:
        return None
    reasons = [f"Estimated soiling loss {s.soiling_loss_pct:.1f}% ({s.method or 'soiling model'})"]
    if s.days_since_rain is not None:
        reasons.append(f"{s.days_since_rain:.0f} days since the last rain event")
    if s.soiling_rate_pct_per_day:
        reasons.append(f"Accumulating at {s.soiling_rate_pct_per_day:.2f}%/day")
    return _Diagnosis(
        likely_cause="Recoverable soiling loss rather than equipment degradation",
        component="soiling",
        is_equipment_fault=False,
        knowledge_query="module cleaning soiling threshold economics",
        severity=Severity.MEDIUM if s.soiling_loss_pct >= 7.0 else Severity.LOW,
        confidence=0.86,
        reasons=reasons,
    )


def _equipment_ruling(packet: EvidencePacket) -> _Diagnosis:
    """Gate 4. Only reached once the environment, peers and soiling are ruled out."""
    anomaly = packet.anomaly
    dominant = anomaly.dominant_signal
    if dominant is None and anomaly.signals:
        dominant = max(
            anomaly.signals,
            key=lambda s: abs(s.z_score or 0.0),
        ).name

    component, cause, query = SIGNAL_DIAGNOSIS.get(
        dominant or "",
        ("gearbox", "Unattributed asset-specific deviation", "asset underperformance diagnosis"),
    )

    # A thermal signature alongside vibration is the classic drivetrain-wear pattern.
    names = {s.name: s for s in anomaly.signals}
    vib = names.get("drivetrain_vibration_mms")
    oil = names.get("gearbox_oil_temp_c")
    if vib and oil and (vib.z_score or 0) > 2.0 and (oil.z_score or 0) > 2.0:
        component, cause = "gearbox", "Progressive gearbox bearing degradation"
        query = "gearbox vibration oil temperature threshold inspection"

    severity = SEVERITY_BY_BAND.get(packet.risk.risk_band, Severity.MEDIUM)
    if anomaly.persistence_hours < settings.min_persistence_hours:
        # Not yet sustained: real degradation persists, transients do not.
        severity = Severity.LOW if severity in (Severity.HIGH, Severity.CRITICAL) else severity

    reasons: list[str] = []
    for name in (dominant, "gearbox_oil_temp_c", "drivetrain_vibration_mms", "power_kw"):
        if name and (line := _fmt_signal(packet, name)) and line not in reasons:
            reasons.append(line)
        if len(reasons) >= 3:
            break

    if packet.peers and packet.peers.verdict is PeerVerdict.ASSET_SPECIFIC:
        pct = packet.peers.deviation_percentile
        reasons.append(
            f"Asset-specific: {packet.peers.n_peers} peers in {packet.peers.peer_group} remain normal"
            + (f" (deviation at the {pct:.0f}th percentile)" if pct is not None else "")
        )
    if packet.environment:
        reasons.append(
            f"Environment explains only {packet.environment.explains_fraction:.0%} of the deviation"
            + ("; no curtailment flag set" if not packet.environment.curtailment_detected else "")
        )
    if anomaly.persistence_hours:
        detail = f"Sustained for {anomaly.persistence_hours:.1f} hours"
        if anomaly.change_point_at:
            detail += f" with a step change at {anomaly.change_point_at:%Y-%m-%d %H:%M}Z"
        reasons.append(detail)

    fired = [d for d in anomaly.detectors if d.fired]
    if len(fired) > 1:
        reasons.append(
            f"{len(fired)} independent detectors agree ({', '.join(d.detector for d in fired)})"
        )

    return _Diagnosis(
        likely_cause=cause,
        component=component,
        is_equipment_fault=True,
        knowledge_query=query,
        severity=severity,
        confidence=_confidence(packet, fired_count=len(fired)),
        reasons=reasons,
        human_review=(dominant not in SIGNAL_DIAGNOSIS or not packet.peers or not packet.environment),
    )


def _confidence(packet: EvidencePacket, fired_count: int) -> float:
    """Evidence-agreement score. Explicitly a heuristic, not a learned probability.

    Starts from a deliberately low base and earns confidence from independent
    corroboration, so a single noisy signal cannot produce a confident diagnosis.
    """
    score = 0.20
    score += min(fired_count, 3) * 0.08  # independent detectors agreeing

    if packet.peers:
        if packet.peers.verdict is PeerVerdict.ASSET_SPECIFIC:
            score += 0.14
        elif packet.peers.verdict is PeerVerdict.FLEET_WIDE:
            score -= 0.10
    else:
        score -= 0.15

    if packet.environment:
        if packet.environment.verdict is EnvironmentVerdict.NOT_ENVIRONMENTAL:
            score += 0.12
        elif packet.environment.verdict is EnvironmentVerdict.PARTIAL:
            score -= 0.06
        if packet.environment.sensor_health is not SensorHealth.OK:
            score -= 0.18
    else:
        score -= 0.15

    if packet.anomaly.persistence_hours >= 24:
        score += 0.10
    elif packet.anomaly.persistence_hours >= settings.min_persistence_hours:
        score += 0.05
    else:
        score -= 0.15

    strong = [s for s in packet.anomaly.signals if abs(s.z_score or 0) >= 3.0]
    score += min(len(strong), 2) * 0.05

    return round(max(0.05, min(0.92, score)), 3)


# --------------------------------------------------------------------------- entry point


def diagnose(
    packet: EvidencePacket,
    cases: list[HistoricalCase] | None = None,
    citations: list[KnowledgeCitation] | None = None,
    economics: EconomicEvidence | None = None,
) -> AgentVerdict:
    """Run the rule chain and assemble a verdict. Never raises on well-formed input."""
    cases = cases or []
    citations = citations or []

    diagnosis = (
        _environmental_ruling(packet)
        or _peer_ruling(packet)
        or _soiling_ruling(packet)
        or _equipment_ruling(packet)
    )

    confidence = diagnosis.confidence
    reasons = list(diagnosis.reasons)

    # Historical corroboration adjusts confidence, and only ever modestly.
    if cases:
        best = max(cases, key=lambda c: c.similarity)
        if best.similarity >= 0.80:
            agrees = best.component == diagnosis.component
            confidence = min(0.97, confidence + (0.08 if agrees else -0.05))
            st = getattr(best, "source_type", None)
            st_val = getattr(st, "value", str(st)) if st else ""
            if st_val.upper() in {"EXTERNAL_REAL", "REAL_EXTERNAL", "HISTORICAL_REAL"}:
                dataset_label = best.source_dataset or "Real operational dataset"
                ev_cls = getattr(best, "event_class", None)
                class_str = getattr(ev_cls, "value", str(ev_cls)) if ev_cls else "REAL_EVENT"
                diff_str = f" [What differs: {', '.join(best.what_is_different[:2])}]" if best.what_is_different else ""
                reasons.insert(
                    0,
                    f"Audited real case {best.case_id} ({dataset_label}, {best.similarity:.0%} match, "
                    f"{best.component}) recorded as {class_str}: '{best.outcome}'"
                    + (f"; detected {best.lead_time_days:.0f} days ahead" if best.lead_time_days else "")
                    + diff_str,
                )
            else:
                reasons.insert(
                    0,
                    f"Closest historical episode {best.case_id} ({best.similarity:.0%} similar, "
                    f"{best.component}) resolved as: {best.outcome}"
                    + (f"; detected {best.lead_time_days:.0f} days ahead" if best.lead_time_days else ""),
                )

    if citations:
        top = citations[0]
        reasons.append(f"Procedure reference: {top.title} — {top.section}")

    # Differential Diagnosis: evaluate competing hypotheses and active counterevidence
    differential = evaluate_differential_diagnosis(packet)
    if diagnosis.is_equipment_fault:
        if differential.status is DifferentialStatus.COMPETING_HYPOTHESES:
            confidence = max(0.20, confidence - 0.12)
            if differential.abstention_rationale:
                reasons.append(f"Differential: {differential.abstention_rationale}")
        elif differential.status in {
            DifferentialStatus.RESOLVED_SINGLE_FAULT,
            DifferentialStatus.RESOLVED_OPERATIONAL,
            DifferentialStatus.RESOLVED_ENVIRONMENTAL,
            DifferentialStatus.RESOLVED_SENSOR_ANOMALY,
        }:
            confidence = min(0.98, confidence + 0.04)
            if differential.counterevidence_summary:
                reasons.append(f"Counterevidence: {differential.counterevidence_summary[0]}")
    elif differential.counterevidence_summary:
        reasons.append(f"Counterevidence: {differential.counterevidence_summary[0]}")

    requires_review = (
        diagnosis.human_review
        or confidence < settings.needle_confidence_threshold
        or diagnosis.severity is Severity.CRITICAL
        or (diagnosis.is_equipment_fault and differential.status is DifferentialStatus.COMPETING_HYPOTHESES)
    )

    action = _recommend_action(diagnosis, packet, economics, differential)
    deadline = DEADLINE_BY_SEVERITY.get(diagnosis.severity)

    return AgentVerdict(
        asset_id=packet.asset_id,
        likely_cause=diagnosis.likely_cause,
        component=diagnosis.component,
        severity=diagnosis.severity,
        confidence=round(confidence, 3),
        requires_human_review=requires_review,
        recommended_action=action,
        action_deadline_hours=deadline,
        evidence_summary=reasons[:6],
        historical_cases=cases[:5],
        citations=citations[:3],
        economics=economics,
        differential=differential,
        model_used="deterministic_reasoner",
        fallback_used=True,
    )


def _recommend_action(
    diagnosis: _Diagnosis,
    packet: EvidencePacket,
    economics: EconomicEvidence | None,
    differential: DifferentialDiagnosisVerdict | None = None,
) -> str:
    if not diagnosis.is_equipment_fault:
        if diagnosis.component == "soiling":
            if economics and economics.recommended_option_id:
                chosen = next(
                    (o for o in economics.options if o.option_id == economics.recommended_option_id),
                    None,
                )
                if chosen:
                    return f"{chosen.label} — lowest expected exposure of the evaluated options"
            return "Schedule a module cleaning campaign once the rain forecast is ruled out"
        if diagnosis.component in {"anemometer"}:
            return "Validate and recalibrate the affected sensor before assessing drivetrain condition"
        return "No maintenance action required; continue monitoring"

    if (
        differential
        and differential.status is DifferentialStatus.COMPETING_HYPOTHESES
        and differential.abstention_rationale
    ):
        return f"Inspect first to resolve competing explanations ({differential.dominant_hypothesis or 'unattributed'})."

    if economics and economics.recommended_option_id:
        chosen = next(
            (o for o in economics.options if o.option_id == economics.recommended_option_id), None
        )
        if chosen:
            return f"{chosen.label} — lowest expected exposure of the evaluated options"

    window = ""
    if packet.risk.risk_window_days:
        lo, hi = packet.risk.risk_window_days
        window = f" Projected failure window {lo}-{hi} days."
    verb = {
        "gearbox": "Inspect gearbox vibration spectrum and oil particle count",
        "main_bearing": "Inspect main bearing temperature trend and lubrication",
        "generator": "Inspect generator cooling circuit and winding insulation",
        "pitch_system": "Verify pitch calibration against the reference curve",
        "yaw_system": "Verify yaw alignment against the nacelle reference",
        "dc_string": "Isolate and test the affected DC strings",
        "inverter": "Service the inverter cooling path and review derate logs",
    }.get(diagnosis.component, "Inspect the affected subsystem")
    hours = DEADLINE_BY_SEVERITY.get(diagnosis.severity) or 336
    return f"{verb} within {hours} hours.{window}".strip()
