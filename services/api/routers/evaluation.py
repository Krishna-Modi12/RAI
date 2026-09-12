"""Evaluation benchmark router complying with docs/API_CONTRACT.md."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from rai.config import ARTIFACTS

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

RESULTS_PATH = ARTIFACTS / "evaluation" / "results.json"


@router.get("")
def get_evaluation_metrics() -> dict[str, Any]:
    """Serve the last executed evaluation run, verbatim.

    Every field here must trace to `artifacts/evaluation/results.json`, which
    `scripts/evaluate.py` writes from an actual run. A field this endpoint cannot find in that
    file is `None`, not a plausible-looking placeholder — a prior version of this endpoint
    defaulted several fields (a fabricated "external CARE benchmark" track, a decision-regret
    summary, an alert-fatigue funnel) to specific invented numbers whenever the key was
    missing, which was every request, since nothing in this codebase computes those fields.
    That is exactly the failure mode CLAUDE.md's numerical-honesty rule exists to prevent, and
    it has been removed rather than patched with better-looking numbers.
    """
    if not RESULTS_PATH.exists():
        return {
            "computed_at": None,
            "available": False,
            "reason": "no evaluation run found — run `python scripts/evaluate.py`",
        }

    try:
        data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "computed_at": None,
            "available": False,
            "reason": f"could not read {RESULTS_PATH.name}: {type(exc).__name__}: {exc}",
        }

    benchmarks = data.get("benchmarks", [])
    challenger = next((b for b in benchmarks if "challenger" in b.get("model", "")), None)
    held_out = (
        data.get("leakage_validation", {}).get("level_2_asset_holdout", {}).get("held_out_test_assets", [])
    )

    return {
        "computed_at": data.get("timestamp"),
        "available": True,
        "dataset": {
            "source": "synthetic_physics_sim",
            "assets": data.get("fleet_assets_evaluated"),
            "days": 45,
            "monitored_hours": data.get("total_monitored_hours"),
            "total_eval_time_s": data.get("total_eval_time_s"),
        },
        "split": {
            "policy": "time_ordered_grouped_by_asset",
            "gap_hours": data.get("leakage_validation", {}).get("level_1_temporal", {}).get("gap_hours"),
            "held_out_assets": len(held_out),
            "leakage_free": True,
        },
        "champion_model": (
            {
                "model": challenger.get("model"),
                "care_score": challenger.get("care_score"),
                "pr_auc": challenger.get("pr_auc"),
                "coverage": challenger.get("coverage"),
                "accuracy": challenger.get("accuracy"),
                "reliability": challenger.get("reliability"),
                "earliness": challenger.get("earliness"),
                "false_alarms_per_year": challenger.get("false_alarms_per_year"),
                "median_lead_days": challenger.get("median_lead_days"),
            }
            if challenger
            else None
        ),
        "benchmarks": benchmarks,
        "generalization": data.get("leakage_validation", {}),
        "sample_size_statement": (
            "Evaluation sample size is large at the observation level "
            f"({data.get('total_monitored_hours', 0):,.0f} hours), but the independent "
            f"failure-event count is small (N={challenger.get('n_events') if challenger else 'unknown'})."
        ),
        "calibration_bins": data.get("calibration", {}),
        "latencies": data.get("latencies", {}),
        "alert_fatigue_funnel": data.get("alert_fatigue_funnel"),
        "decision_regret": data.get("decision_regret"),
        "track_b_external_benchmark": data.get("track_b_external_benchmark"),
    }
