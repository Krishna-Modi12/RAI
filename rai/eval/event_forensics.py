"""Event-level forensics module for Phase 3A.

Treats independent failure episodes as the primary unit of analysis rather than
individual correlated time rows. Computes event recall, lead times, false alarms per event,
and produces artifacts/evaluation/gate3/events.csv.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rai.config import FLEET
from rai.models.pipeline import compute_asset_state
from rai.store import load_telemetry
from rai.store.events import load_events

log = logging.getLogger(__name__)


@dataclass
class EventForensicRecord:
    event_id: str
    asset_id: str
    site: str
    modality: str
    failure_family: str
    scenario: str
    onset: str
    failure: str
    first_valid_alarm: str | None
    lead_time_days: float
    alarm_count: int
    status: str  # DETECTED or MISSED
    false_alarms_before_event: int
    detector_confidence: float


@dataclass
class EventSummaryMetrics:
    total_events: int
    detected_events: int
    missed_events: int
    event_recall: float
    detected_event_fraction: float
    median_lead_time_days: float
    iqr_lead_time_days: float
    mean_lead_time_days: float
    min_lead_time_days: float
    max_lead_time_days: float
    total_false_alarms: int
    false_alarms_per_event: float


def evaluate_event_level_forensics(
    output_dir: Path | str,
    threshold: float = 0.45,
    persistence_hours: float = 6.0,
) -> dict[str, Any]:
    """Evaluate each independent failure event across the fleet and produce events.csv."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    injected = load_events()
    equipment_events = [e for e in injected if e.is_equipment_fault]
    asset_lookup = {a.asset_id: a for a in FLEET}

    records: list[EventForensicRecord] = []

    # Map assets to alarms by scanning operational snapshots or walk-forward
    log.info("Computing event-level alarms for %d equipment failure episodes...", len(equipment_events))

    all_alarms: list[dict[str, Any]] = []

    # Faulted asset IDs
    fault_aids = {e.asset_id for e in equipment_events}

    for asset in FLEET:
        aid = asset.asset_id
        telemetry = load_telemetry(aid)
        if telemetry.empty:
            continue

        ts_min = pd.to_datetime(telemetry["ts"].min(), utc=True)
        ts_max = pd.to_datetime(telemetry["ts"].max(), utc=True)

        if aid in fault_aids:
            # For faulted assets, evaluate throughout pre-failure window with 24h resolution
            asset_ev = next(e for e in equipment_events if e.asset_id == aid)
            ev_onset = pd.to_datetime(asset_ev.onset, utc=True)
            ev_fail = pd.to_datetime(asset_ev.end or (ev_onset + pd.Timedelta(days=14)), utc=True)
            scan_start = max(ts_min + pd.Timedelta(days=14), ev_onset - pd.Timedelta(days=2))
            sample_points = pd.date_range(scan_start, min(ev_fail, ts_max), freq="24h")
        else:
            # For healthy assets, sample across operational checkpoints
            sample_points = pd.date_range(ts_min + pd.Timedelta(days=14), ts_max, freq="72h")

        for sample_ts in sample_points:
            try:
                state = compute_asset_state(aid, as_of=sample_ts)
                if (
                    state.anomaly
                    and state.anomaly.anomaly_score >= threshold
                    and state.anomaly.persistence_hours >= persistence_hours
                ):
                    env_verdict = state.environment.verdict.value if state.environment else "not_environmental"
                    peer_verdict = state.peers.verdict.value if state.peers else "asset_specific"
                    if env_verdict != "environmental" and peer_verdict != "fleet_wide":
                        all_alarms.append({
                            "timestamp": sample_ts,
                            "asset_id": aid,
                            "score": state.anomaly.anomaly_score,
                            "risk": state.risk.risk_score if state.risk else state.anomaly.anomaly_score,
                        })
            except Exception as exc:
                log.debug("Sampling exception for %s at %s: %s", aid, sample_ts, exc)
                continue

    log.info("Total alarms fired across fleet during sweep: %d", len(all_alarms))

    total_false_alarms = 0
    lead_times: list[float] = []

    for ev in equipment_events:
        aid = ev.asset_id
        meta = asset_lookup.get(aid)
        site = meta.site if meta else ("Kutch Wind Farm" if "WT" in aid else "Charanka Solar Park")
        modality = "wind" if "WT" in aid else "solar"
        family = ev.component

        onset_dt = pd.to_datetime(ev.onset, utc=True)
        fail_dt = pd.to_datetime(ev.end or (onset_dt + pd.Timedelta(days=14)), utc=True)

        # Alarms on this asset
        asset_alarms = [a for a in all_alarms if a["asset_id"] == aid]

        # Alarms strictly before onset
        fa_before = [a for a in asset_alarms if pd.to_datetime(a["timestamp"], utc=True) < onset_dt]
        total_false_alarms += len(fa_before)

        # Valid alarms in [onset, failure]
        valid_alarms = [
            a for a in asset_alarms
            if onset_dt <= pd.to_datetime(a["timestamp"], utc=True) <= fail_dt
        ]

        if valid_alarms:
            first_alarm = min(valid_alarms, key=lambda a: pd.to_datetime(a["timestamp"], utc=True))
            first_alarm_ts = pd.to_datetime(first_alarm["timestamp"], utc=True)
            lead_days = max(0.0, (fail_dt - first_alarm_ts).total_seconds() / 86400.0)
            lead_times.append(lead_days)
            status = "DETECTED"
            conf = float(first_alarm.get("score", 0.0))
            first_alarm_str = str(first_alarm_ts)
        else:
            first_alarm_str = None
            lead_days = 0.0
            status = "MISSED"
            conf = 0.0

        rec = EventForensicRecord(
            event_id=ev.event_id,
            asset_id=aid,
            site=site,
            modality=modality,
            failure_family=family,
            scenario=ev.scenario,
            onset=str(onset_dt),
            failure=str(fail_dt),
            first_valid_alarm=first_alarm_str,
            lead_time_days=round(lead_days, 2),
            alarm_count=len(valid_alarms),
            status=status,
            false_alarms_before_event=len(fa_before),
            detector_confidence=round(conf, 3),
        )
        records.append(rec)

    # Calculate summary metrics
    n_total = len(records)
    n_det = sum(1 for r in records if r.status == "DETECTED")
    n_miss = n_total - n_det
    recall = n_det / max(n_total, 1)

    med_lead = float(np.median(lead_times)) if lead_times else 0.0
    mean_lead = float(np.mean(lead_times)) if lead_times else 0.0
    min_lead = float(np.min(lead_times)) if lead_times else 0.0
    max_lead = float(np.max(lead_times)) if lead_times else 0.0
    if len(lead_times) > 1:
        q75, q25 = np.percentile(lead_times, [75, 25])
        iqr_lead = float(q75 - q25)
    else:
        iqr_lead = 0.0

    fa_per_event = total_false_alarms / max(n_total, 1)

    summary = EventSummaryMetrics(
        total_events=n_total,
        detected_events=n_det,
        missed_events=n_miss,
        event_recall=round(recall, 4),
        detected_event_fraction=round(recall, 4),
        median_lead_time_days=round(med_lead, 2),
        iqr_lead_time_days=round(iqr_lead, 2),
        mean_lead_time_days=round(mean_lead, 2),
        min_lead_time_days=round(min_lead, 2),
        max_lead_time_days=round(max_lead, 2),
        total_false_alarms=total_false_alarms,
        false_alarms_per_event=round(fa_per_event, 2),
    )

    # Write events.csv
    events_csv_path = out_dir / "events.csv"
    pd.DataFrame([asdict(r) for r in records]).to_csv(events_csv_path, index=False)

    # Write event_summary.json
    summary_json_path = out_dir / "event_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)

    log.info(
        "Event forensics complete: %d/%d detected (recall=%.3f), median lead=%.2fd, IQR=%.2fd",
        n_det, n_total, recall, med_lead, iqr_lead
    )

    return {
        "records": [asdict(r) for r in records],
        "summary": asdict(summary),
        "events_csv": str(events_csv_path),
        "event_summary_json": str(summary_json_path),
    }
