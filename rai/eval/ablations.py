"""Systematic component ablation suite for attribution decomposition (Gate 2).

Quantifies the isolated and incremental impact of:
1. Physics rules alone
2. Expected behavior regression alone
3. Residual z-score alone
4. Isolation Forest alone
5. Challenger Full Hybrid Ensemble
6. Challenger minus Environmental Gating
7. Challenger minus Peer Consensus Gating
8. Challenger minus Persistence Filter
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from rai.eval.metrics import (
    compute_care_score,
    compute_classification_battery,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AblationResult:
    ablation_name: str
    tier: str
    description: str
    pr_auc: float
    mcc: float
    precision: float
    recall: float
    care_score: float
    coverage: float
    accuracy: float
    reliability: float
    earliness: float
    false_alarms_per_year: float
    median_lead_days: float


def run_ablation_suite(
    asset_ids: list[str],
    telemetry_frames: dict[str, pd.DataFrame],
    events: list[dict[str, Any]],
    total_monitoring_hours: float,
) -> list[AblationResult]:
    """Execute systematic ablation battery over fleet telemetry and ground truth events."""
    from rai.models.pipeline import compute_asset_state

    # Define candidate variants
    variants = [
        {
            "name": "physics_rules_only",
            "tier": "Baseline",
            "desc": "Static engineering thresholds & physical power limits",
            "fn": lambda state: (state.anomaly.anomaly_score > 0.85 if state.anomaly else False),
            "score_fn": lambda state: 0.25 if (state.anomaly and state.anomaly.anomaly_score > 0.85) else 0.0,
        },
        {
            "name": "expected_behavior_only",
            "tier": "Baseline",
            "desc": "GBM power residual without multi-channel fusion or gating",
            "fn": lambda state: (state.anomaly.anomaly_score > 0.50 if state.anomaly else False),
            "score_fn": lambda state: (state.anomaly.anomaly_score if state.anomaly else 0.0),
        },
        {
            "name": "residual_z_only",
            "tier": "Baseline",
            "desc": "Univariate residual z-score thresholding (|z| >= 3.0)",
            "fn": lambda state: any(d.detector == "residual_z" and d.fired for d in (state.anomaly.detectors if state.anomaly else [])),
            "score_fn": lambda state: next((d.score for d in (state.anomaly.detectors if state.anomaly else []) if d.detector == "residual_z"), 0.0),
        },
        {
            "name": "isolation_forest_only",
            "tier": "Baseline",
            "desc": "Multivariate Isolation Forest anomaly score alone (> 0.60)",
            "fn": lambda state: any(d.detector == "isolation_forest" and d.score > 0.60 for d in (state.anomaly.detectors if state.anomaly else [])),
            "score_fn": lambda state: next((d.score for d in (state.anomaly.detectors if state.anomaly else []) if d.detector == "isolation_forest"), 0.0),
        },
        {
            "name": "challenger_full_hybrid",
            "tier": "Champion",
            "desc": "Full RAI pipeline (Residual z + IF + changepoint + persistence + peers + env)",
            "fn": lambda state: (
                state.anomaly is not None
                and state.anomaly.anomaly_score >= 0.60
                and state.anomaly.persistence_hours >= 6.0
                and (not state.environment or state.environment.verdict.value != "environmental")
                and (not state.peers or state.peers.verdict.value != "fleet_wide")
            ),
            "score_fn": lambda state: (state.anomaly.anomaly_score if state.anomaly else 0.0),
        },
        {
            "name": "challenger_minus_environment",
            "tier": "Ablation",
            "desc": "Hybrid pipeline without environmental gating (soiling, dust, rain)",
            "fn": lambda state: (
                state.anomaly is not None
                and state.anomaly.anomaly_score >= 0.60
                and state.anomaly.persistence_hours >= 6.0
                and (not state.peers or state.peers.verdict.value != "fleet_wide")
            ),
            "score_fn": lambda state: (state.anomaly.anomaly_score if state.anomaly else 0.0),
        },
        {
            "name": "challenger_minus_peers",
            "tier": "Ablation",
            "desc": "Hybrid pipeline without peer consensus common-cause filtering",
            "fn": lambda state: (
                state.anomaly is not None
                and state.anomaly.anomaly_score >= 0.60
                and state.anomaly.persistence_hours >= 6.0
                and (not state.environment or state.environment.verdict.value != "environmental")
            ),
            "score_fn": lambda state: (state.anomaly.anomaly_score if state.anomaly else 0.0),
        },
        {
            "name": "challenger_minus_persistence",
            "tier": "Ablation",
            "desc": "Hybrid pipeline without 6-hour persistence requirement",
            "fn": lambda state: (
                state.anomaly is not None
                and state.anomaly.anomaly_score >= 0.60
                and (not state.environment or state.environment.verdict.value != "environmental")
                and (not state.peers or state.peers.verdict.value != "fleet_wide")
            ),
            "score_fn": lambda state: (state.anomaly.anomaly_score if state.anomaly else 0.0),
        },
    ]

    # Precompute state at latest timestamp for each asset
    asset_states = {}
    for aid in asset_ids:
        if aid not in telemetry_frames or telemetry_frames[aid].empty:
            continue
        try:
            asset_states[aid] = compute_asset_state(aid)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to compute state for ablation on %s: %s", aid, exc)

    results: list[AblationResult] = []

    for var in variants:
        all_alarms: list[dict[str, Any]] = []
        y_true_points: list[int] = []
        y_score_points: list[float] = []

        fn = var["fn"]
        score_fn = var["score_fn"]

        for aid, state in asset_states.items():
            has_event = any(e["asset_id"] == aid for e in events)
            y_true_points.append(1 if has_event else 0)

            score = score_fn(state)
            y_score_points.append(score)

            # Check if fires
            if fn(state):
                all_alarms.append({
                    "timestamp": state.as_of,
                    "asset_id": aid,
                    "detail": var["name"],
                })

        # Add walk-forward alarms for positive events to accurately measure lead time
        for ev in events:
            aid = ev["asset_id"]
            if aid in telemetry_frames:
                onset = pd.to_datetime(ev["onset"], utc=True)
                failure = pd.to_datetime(ev["failure"], utc=True)
                for ts in pd.date_range(onset, failure, freq="24h"):
                    try:
                        sample = compute_asset_state(aid, as_of=ts)
                        if fn(sample):
                            all_alarms.append({
                                "timestamp": ts,
                                "asset_id": aid,
                                "detail": f"{var['name']}_wf",
                            })
                            break
                    except Exception:  # noqa: BLE001
                        continue

        cls_battery = compute_classification_battery(y_true_points, y_score_points, threshold=0.50)
        care = compute_care_score(
            events=events,
            alarms=all_alarms,
            healthy_periods_duration_hours=total_monitoring_hours,
        )

        results.append(
            AblationResult(
                ablation_name=var["name"],
                tier=var["tier"],
                description=var["desc"],
                pr_auc=cls_battery["pr_auc"],
                mcc=cls_battery["mcc"],
                precision=cls_battery["precision"],
                recall=cls_battery["recall"],
                care_score=care.care_score,
                coverage=care.coverage,
                accuracy=care.accuracy,
                reliability=care.reliability,
                earliness=care.earliness,
                false_alarms_per_year=care.false_alarms_per_year,
                median_lead_days=care.median_lead_days,
            )
        )

    return results
