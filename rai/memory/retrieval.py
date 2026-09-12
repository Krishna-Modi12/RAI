"""Trajectory k-nearest-neighbour retrieval over the case library.

The question this layer answers is *"has the fleet seen this shape before?"* — not "has it
seen this asset before". So the signature is built from the **shape of the deviation**: which
channel moved, how far, how fast, whether the peers moved with it, and how much of it the
weather already explained.

Two design decisions are load-bearing:

**Growth rate is a feature.** A five-sigma residual that arrived in one interval and a
five-sigma residual that took four weeks to build are different faults with different
interventions, and a nearest-neighbour search that ignores the time axis will confuse them.
`growth_rate` is peak sigma per day; the step flag is the changepoint detector's verdict.

**Similarity is not confidence.** A returned case says the shape rhymes. It does not say the
diagnosis transfers. The agent is given the similarity score and the case outcome and must
weigh them against the direct evidence — which is why the non-fault cases are in the library
at all. `HistoricalCase.source` keeps the synthetic provenance attached all the way to the UI.
"""

from __future__ import annotations

import logging
import math

from rai.memory.library import (
    FEATURES,
    MECHANICAL_SIGNALS,
    POWER_SIGNALS,
    THERMAL_SIGNALS,
    WEIGHTS,
    Case,
    cases_for,
)
from rai.schemas import EvidencePacket, HistoricalCase

log = logging.getLogger(__name__)

Z_SCALE = 5.0          # sigma that maps to a full-scale feature value
PERSISTENCE_CAP_H = 720.0  # 30 days
GROWTH_SCALE = 4.0     # sigma/day that maps to a full-scale feature value
SOILING_SCALE = 20.0   # percent loss that maps to full scale

# Below this the "match" is noise. Returning a weak match with a confident-looking number is
# worse than returning nothing, so the retrieval reports fewer cases rather than padding.
MIN_SIMILARITY = 0.35

# A case whose equipment/non-equipment character contradicts the live environmental verdict is
# a poor neighbour however close its numbers land, so its distance is penalised rather than
# excluded — the agent still sees it, ranked below the honest matches.
CONTRADICTION_PENALTY = 0.55


def _channel_z(packet: EvidencePacket, channel: set[str]) -> float:
    """Largest-magnitude residual z among the signals belonging to one physical channel."""
    values = [
        s.z_score
        for s in packet.anomaly.signals
        if s.name in channel and s.z_score is not None
    ]
    if not values:
        return 0.0
    return max(values, key=abs)


def signature_from_packet(packet: EvidencePacket) -> dict[str, float]:
    """Reduce a live evidence packet to the case-library feature space."""
    anomaly = packet.anomaly

    peak_abs_z = max(
        (abs(s.z_score) for s in anomaly.signals if s.z_score is not None), default=0.0
    )
    persistence_h = max(float(anomaly.persistence_hours), 0.0)
    # Sigma per day. Guard the denominator: a deviation seen for six hours has not been
    # observed long enough for its rate to be meaningful, so treat it as a quarter-day.
    days = max(persistence_h / 24.0, 0.25)
    step = any(d.detector == "changepoint" and d.fired for d in anomaly.detectors)

    peer_pct = 0.5
    if packet.peers is not None and packet.peers.deviation_percentile is not None:
        peer_pct = float(packet.peers.deviation_percentile) / 100.0

    env_explains = 0.0
    if packet.environment is not None:
        env_explains = float(packet.environment.explains_fraction)

    soiling_loss = 0.0
    if packet.soiling is not None and packet.soiling.soiling_loss_pct is not None:
        soiling_loss = float(packet.soiling.soiling_loss_pct)

    def clip(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    return {
        "power_z": clip(_channel_z(packet, POWER_SIGNALS) / Z_SCALE, -1.0, 1.0),
        "thermal_z": clip(_channel_z(packet, THERMAL_SIGNALS) / Z_SCALE, -1.0, 1.0),
        "mechanical_z": clip(_channel_z(packet, MECHANICAL_SIGNALS) / Z_SCALE, -1.0, 1.0),
        "peer_percentile": clip(peer_pct, 0.0, 1.0),
        "env_explains": clip(env_explains, 0.0, 1.0),
        "persistence": clip(
            math.log1p(persistence_h) / math.log1p(PERSISTENCE_CAP_H), 0.0, 1.0
        ),
        "growth_rate": clip((peak_abs_z / days) / GROWTH_SCALE, 0.0, 1.0),
        "step_change": 1.0 if step else 0.0,
        "soiling_loss": clip(soiling_loss / SOILING_SCALE, 0.0, 1.0),
        "anomaly_score": clip(float(anomaly.anomaly_score), 0.0, 1.0),
    }


def _distance(live: dict[str, float], case: Case) -> float:
    """Weighted Euclidean distance, normalised so a perfect match is 0 and a worst case is ~1."""
    total = 0.0
    norm = 0.0
    for name in FEATURES:
        weight = WEIGHTS.get(name, 1.0)
        delta = live.get(name, 0.0) - case.signature.get(name, 0.0)
        total += weight * delta * delta
        # The per-feature range is 2.0 for the signed z features and 1.0 for the rest.
        span = 2.0 if name.endswith("_z") else 1.0
        norm += weight * span * span
    return math.sqrt(total / norm) if norm > 0 else 1.0


def _contradicts(packet: EvidencePacket, case: Case) -> bool:
    """True when the case's verdict runs against what the live evidence already established.

    Only the two directions we can be confident about are penalised: an equipment case when
    the environment layer has already explained the deviation, and a non-equipment case when a
    sensor is confirmed healthy and a large residual survived conditioning.
    """
    env = packet.environment
    if env is None:
        return False
    if case.equipment_fault and env.verdict.value == "environmental":
        return True
    return bool(
        not case.equipment_fault
        and env.verdict.value == "not_environmental"
        and env.sensor_health.value == "ok"
        and not env.curtailment_detected
    )


def find_similar_cases(packet: EvidencePacket, k: int = 5) -> list[HistoricalCase]:
    """Return up to `k` past episodes whose trajectory resembles this asset's, best first."""
    live = signature_from_packet(packet)
    candidates = cases_for(packet.asset_type.value)
    if not candidates:
        return []

    scored: list[tuple[float, Case]] = []
    for case in candidates:
        distance = _distance(live, case)
        if _contradicts(packet, case):
            distance = min(1.0, distance + CONTRADICTION_PENALTY)
        scored.append((distance, case))

    scored.sort(key=lambda pair: pair[0])

    out: list[HistoricalCase] = []
    for distance, case in scored[: max(k, 0)]:
        similarity = round(max(0.0, 1.0 - distance), 3)
        if similarity < MIN_SIMILARITY:
            continue
        out.append(
            HistoricalCase(
                case_id=case.case_id,
                similarity=similarity,
                asset_id=case.asset_id,
                component=case.component,
                fault_mode=case.fault_mode,
                observed_signature=list(case.observed_signature),
                outcome=case.outcome,
                lead_time_days=case.lead_time_days,
                repair_cost_inr=case.repair_cost_inr,
                source="synthetic_case_library",
            )
        )
    return out


def explain_match(packet: EvidencePacket, case_id: str) -> dict[str, float]:
    """Per-feature contribution to the match, for the UI's 'why this case' panel."""
    from rai.memory.library import CASE_BY_ID

    case = CASE_BY_ID.get(case_id)
    if case is None:
        return {}
    live = signature_from_packet(packet)
    return {
        name: round(
            WEIGHTS.get(name, 1.0) * (live.get(name, 0.0) - case.signature.get(name, 0.0)) ** 2,
            4,
        )
        for name in FEATURES
    }
