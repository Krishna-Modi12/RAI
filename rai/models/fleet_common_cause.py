"""Fleet-wide common-cause event detection and false-alarm suppression.

Distinguishes asset-specific equipment faults from plant-wide common-cause events:
- 1 asset abnormal while peers are healthy -> Asset-specific equipment suspicion.
- Multiple assets abnormal simultaneously -> Environmental or grid event (e.g. dust storm,
  cloud front, grid curtailment, wind calm).

Prevents erroneous control-room dispatches by automatically classifying common-cause signals.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FleetCommonCauseResult:
    is_common_cause: bool
    affected_asset_count: int
    total_peer_count: int
    affected_fraction: float
    common_cause_type: str  # "none", "sandstorm_dust", "cloud_transient", "grid_curtailment", "wind_regime"
    suppression_factor: float  # [0.0, 1.0] multiplier on equipment alarm urgency
    rationale: str


def detect_fleet_common_cause(
    asset_id: str,
    asset_class: str,  # "wind_turbine" or "solar_inverter"
    peer_anomaly_scores: Sequence[float],
    site_environmental_score: float = 0.0,
    grid_curtailment_active: bool = False,
    threshold_fraction: float = 0.30,
) -> FleetCommonCauseResult:
    """Evaluate whether an observed anomaly is isolated or part of a fleet-wide common cause."""
    total_peers = len(peer_anomaly_scores)
    if total_peers == 0:
        return FleetCommonCauseResult(
            is_common_cause=False,
            affected_asset_count=0,
            total_peer_count=0,
            affected_fraction=0.0,
            common_cause_type="none",
            suppression_factor=1.0,
            rationale="No peer fleet data available; evaluating asset in isolation.",
        )

    # An asset is considered deviating if anomaly score >= 0.40
    anomalous_peers = sum(1 for s in peer_anomaly_scores if s >= 0.40)
    affected_fraction = anomalous_peers / float(total_peers)

    # Check for grid curtailment
    if grid_curtailment_active:
        return FleetCommonCauseResult(
            is_common_cause=True,
            affected_asset_count=anomalous_peers,
            total_peer_count=total_peers,
            affected_fraction=round(affected_fraction, 3),
            common_cause_type="grid_curtailment",
            suppression_factor=0.05,
            rationale="Grid curtailment setpoint active across site; individual deficits are non-fault.",
        )

    if affected_fraction >= threshold_fraction:
        # Common cause event across fleet
        if asset_class in {"solar", "solar_inverter", "inverter"}:
            cause = "sandstorm_dust" if site_environmental_score >= 0.50 else "cloud_transient"
            suppression = 0.10 if cause == "sandstorm_dust" else 0.20
            rat = (
                f"Fleet common cause detected: {anomalous_peers}/{total_peers} inverters ({affected_fraction:.0%}) "
                f"exhibit concurrent generation drop. Attributed to plant-wide {cause}."
            )
        else:
            cause = "wind_regime"
            suppression = 0.15
            rat = (
                f"Fleet common cause detected: {anomalous_peers}/{total_peers} turbines ({affected_fraction:.0%}) "
                f"experience synchronized output deviation. Attributed to regional wind regime / wake dynamics."
            )

        return FleetCommonCauseResult(
            is_common_cause=True,
            affected_asset_count=anomalous_peers,
            total_peer_count=total_peers,
            affected_fraction=round(affected_fraction, 3),
            common_cause_type=cause,
            suppression_factor=suppression,
            rationale=rat,
        )

    # Isolated anomaly
    return FleetCommonCauseResult(
        is_common_cause=False,
        affected_asset_count=anomalous_peers,
        total_peer_count=total_peers,
        affected_fraction=round(affected_fraction, 3),
        common_cause_type="none",
        suppression_factor=1.0,
        rationale=(
            f"Isolated anomaly confirmed: only {anomalous_peers}/{total_peers} peers affected "
            f"({affected_fraction:.0%} < {threshold_fraction:.0%}). High asset-specific fault suspicion."
        ),
    )
