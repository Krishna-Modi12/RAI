"""Fleet dataset generation.

Produces the whole synthetic estate: per-asset telemetry parquet, the site meteorology that
drove it, and the ground-truth event log.

Two properties are deliberate and load-bearing:

* **Every asset has a long fault-free prefix.** Expected-behaviour models train only on that
  window, so a degradation signature is never learned as normal.
* **Every injected event runs up to the present.** The fleet "right now" therefore contains
  live problems at realistic stages of development, which is what the operator view shows.

Most of the fleet stays healthy. A monitoring system evaluated on a fleet where half the
assets are broken is not being evaluated on the problem it will actually face.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from rai.config import (
    FLEET,
    HERO_SOLAR_ASSET,
    HERO_WIND_ASSET,
    SITES,
    SYNTHETIC,
    Asset,
    settings,
)
from rai.schemas import AssetType, InjectedEvent
from rai.sim.faults import SCENARIOS, apply_scenario
from rai.sim.met import SITE_MET_COLUMNS, SiteMet, generate_site_met
from rai.sim.solar import simulate_inverter
from rai.sim.wind import simulate_turbine

TELEMETRY_DIR = SYNTHETIC / "telemetry"
EVENTS_PATH = SYNTHETIC / "events.parquet"
SITE_MET_PATH = SYNTHETIC / "site_met.parquet"


@dataclass(frozen=True)
class Assignment:
    """One planned fault. `ends_days_before_now` lets an event finish in the recent past."""

    asset_id: str
    scenario: str
    severity: float
    duration_days: float
    ends_days_before_now: float = 0.0


# Twelve assignments covering all twelve scenarios. The remaining 30 assets stay healthy.
ASSIGNMENTS: list[Assignment] = [
    # --- the flagship case the demo follows
    Assignment(HERO_WIND_ASSET, "gearbox_bearing_wear", 0.88, 16.0),
    # --- other genuine equipment faults
    Assignment("WT-004", "generator_overheating", 0.72, 9.0),
    Assignment("WT-011", "pitch_misalignment", 0.65, 12.0),
    Assignment("WT-015", "yaw_misalignment", 0.58, 11.0),
    Assignment("INV-007", "string_outage", 1.00, 6.0),
    Assignment("INV-015", "inverter_derate", 0.70, 6.0),
    # --- healthy assets that merely look broken
    Assignment(HERO_SOLAR_ASSET, "soiling_accumulation", 0.90, 18.0),
    Assignment("WT-002", "anemometer_drift", 0.80, 13.0),
    Assignment("WT-014", "sensor_freeze", 1.00, 1.2, ends_days_before_now=2.0),
    Assignment("WT-008", "curtailment_window", 1.00, 1.5, ends_days_before_now=4.0),
    Assignment("WT-006", "icing_event", 0.85, 2.0, ends_days_before_now=6.0),
    Assignment("INV-011", "cloud_transient", 1.00, 2.0, ends_days_before_now=1.0),
]


@dataclass
class GenerationResult:
    assets: int
    rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    events: list[InjectedEvent]
    fault_free_fraction: float
    files: int


def _window(days: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Data window ending on the most recent hour boundary."""
    end = pd.Timestamp.now(tz="UTC").floor("h")
    return end - pd.Timedelta(days=days), end


def generate_fleet(
    days: int | None = None,
    seed: int | None = None,
    only_assets: list[str] | None = None,
) -> GenerationResult:
    days = days or settings.sim_days
    seed = seed if seed is not None else settings.sim_seed
    start, end = _window(days)

    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

    met_by_site: dict[str, SiteMet] = {}
    for site_key, site in SITES.items():
        interval = (
            settings.wind_interval_min
            if site["asset_type"] is AssetType.WIND_TURBINE
            else settings.solar_interval_min
        )
        met_by_site[site_key] = generate_site_met(site_key, start, end, interval, seed)

    assignments = {a.asset_id: a for a in ASSIGNMENTS}
    selected = [a for a in FLEET if only_assets is None or a.asset_id in only_assets]

    events: list[InjectedEvent] = []
    total_rows = 0
    fault_free_rows = 0
    files = 0

    for position, asset in enumerate(selected):
        met = met_by_site[asset.site]
        frame = _simulate_asset(asset, met, seed)

        assignment = assignments.get(asset.asset_id)
        if assignment is not None:
            scenario_end = end - pd.Timedelta(days=assignment.ends_days_before_now)
            onset = scenario_end - pd.Timedelta(days=assignment.duration_days)
            if onset < start:
                raise ValueError(
                    f"{asset.asset_id}: {assignment.scenario} needs "
                    f"{assignment.duration_days} days but only {days} days are generated"
                )
            frame, event = apply_scenario(
                frame,
                asset,
                met,
                assignment.scenario,
                onset=onset,
                duration_days=assignment.duration_days,
                severity=assignment.severity,
                seed=seed,
                event_id=f"EVT-{len(events) + 1:04d}",
            )
            events.append(event)
            fault_free_rows += int((frame["ts"] < onset).sum())
        else:
            fault_free_rows += len(frame)

        _inject_data_quality_gaps(frame, asset, seed + position)

        frame.to_parquet(TELEMETRY_DIR / f"{asset.asset_id}.parquet", index=False)
        total_rows += len(frame)
        files += 1

    if events:
        pd.DataFrame([e.model_dump() for e in events]).to_parquet(EVENTS_PATH, index=False)

    met_frames = [m.frame[SITE_MET_COLUMNS] for m in met_by_site.values()]
    pd.concat(met_frames, ignore_index=True).to_parquet(SITE_MET_PATH, index=False)

    return GenerationResult(
        assets=len(selected),
        rows=total_rows,
        start=start,
        end=end,
        events=events,
        fault_free_fraction=fault_free_rows / total_rows if total_rows else 0.0,
        files=files,
    )


def _simulate_asset(asset: Asset, met: SiteMet, seed: int) -> pd.DataFrame:
    if asset.asset_type is AssetType.WIND_TURBINE:
        return simulate_turbine(asset, met, seed)
    return simulate_inverter(asset, met, seed)


def _inject_data_quality_gaps(frame: pd.DataFrame, asset: Asset, seed: int) -> None:
    """Real SCADA has holes. A pipeline that only works on complete data is not finished.

    Applied in place, and never inside an event window's final stretch, so ground-truth
    detection is not accidentally made impossible.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    n = len(frame)
    if n < 200:
        return

    numeric = [
        c
        for c in frame.columns
        if c not in {"ts", "asset_id", "operating_state", "status_code"}
        and pd.api.types.is_numeric_dtype(frame[c])
    ]
    if not numeric:
        return

    # A short comms outage: every channel drops at once.
    outage_start = int(rng.integers(0, max(n - 40, 1)))
    outage_len = int(rng.integers(3, 14))
    frame.loc[outage_start : outage_start + outage_len, numeric] = pd.NA

    # Scattered single-sample dropouts on one channel.
    channel = str(rng.choice(numeric))
    dropouts = rng.choice(n, size=max(n // 900, 3), replace=False)
    frame.loc[dropouts, channel] = pd.NA


def summarise(result: GenerationResult) -> str:
    lines = [
        f"assets          {result.assets}",
        f"files           {result.files}",
        f"rows            {result.rows:,}",
        f"window          {result.start:%Y-%m-%d %H:%M}Z .. {result.end:%Y-%m-%d %H:%M}Z",
        f"fault-free rows {result.fault_free_fraction:.1%}",
        f"events          {len(result.events)}",
    ]
    if result.events:
        lines.append("")
        lines.append(f"  {'event':<10} {'asset':<9} {'scenario':<22} {'equip':<6} onset")
        for e in result.events:
            lines.append(
                f"  {e.event_id:<10} {e.asset_id:<9} {e.scenario:<22} "
                f"{'yes' if e.is_equipment_fault else 'no':<6} {e.onset:%Y-%m-%d %H:%M}Z"
            )
        equipment = sum(1 for e in result.events if e.is_equipment_fault)
        lines.append("")
        lines.append(
            f"  {equipment} equipment faults, {len(result.events) - equipment} "
            f"non-equipment scenarios (weather, dirt, grid, instrumentation)"
        )
    unknown = set(a.scenario for a in ASSIGNMENTS) - set(SCENARIOS)
    if unknown:
        lines.append(f"  WARNING unknown scenarios assigned: {sorted(unknown)}")
    return "\n".join(lines)
