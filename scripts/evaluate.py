"""Run the reproducible local evaluation and write machine-readable results.

The report intentionally contains only metrics computed during this invocation. It combines
expected-behaviour model metrics from the time-ordered training routine with a scenario-level
check of the deterministic evidence reasoner against simulator ground truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

from rai.config import ARTIFACTS, MODELS

OUTPUT_DIR = ARTIFACTS / "evaluation"


def _ensure_data() -> None:
    from rai.store import telemetry_available

    if not telemetry_available():
        from rai.sim.generate import generate_fleet

        generate_fleet()


def _model_report(retrain: bool) -> dict[str, Any]:
    from rai.models.expected import train_all

    if retrain or not (MODELS / "metadata.json").is_file():
        return train_all()
    metadata = json.loads((MODELS / "metadata.json").read_text())
    return metadata.get("report", {})


def _scenario_report() -> dict[str, Any]:
    from rai.agent.fallback import diagnose
    from rai.models.pipeline import build_evidence_packet
    from rai.store import load_events

    rows: list[dict[str, Any]] = []
    for event in load_events():
        packet = build_evidence_packet(event.asset_id)
        verdict = diagnose(packet)
        predicted_equipment = verdict.component not in {"none", "anemometer", "soiling"}
        rows.append(
            {
                "asset_id": event.asset_id,
                "scenario": event.scenario,
                "expected_equipment_fault": event.is_equipment_fault,
                "predicted_equipment_fault": predicted_equipment,
                "component": verdict.component,
                "requires_human_review": verdict.requires_human_review,
                "confidence": verdict.confidence,
            }
        )

    correct = sum(r["expected_equipment_fault"] == r["predicted_equipment_fault"] for r in rows)
    return {
        "definition": "scenario-level equipment-vs-non-equipment agreement against simulator flags",
        "n_scenarios": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows) if rows else None,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the local RAI pipeline")
    parser.add_argument("--retrain", action="store_true", help="retrain expected-behaviour models")
    args = parser.parse_args()

    _ensure_data()
    models = _model_report(args.retrain)
    scenarios = _scenario_report()
    report = {
        "computed_at": datetime.now(UTC).isoformat(),
        "data": {
            "source": "synthetic_physics_sim",
            "events": scenarios["n_scenarios"],
            "telemetry_root": "data/synthetic",
        },
        "model_metrics": models.get("models", {}),
        "splits": models.get("splits", {}),
        "scenario_discrimination": scenarios,
        "limitations": [
            "Scenario agreement is not validation on real SCADA.",
            "The deterministic reasoner confidence is an evidence-agreement score, not a calibrated probability.",
            "No public external dataset is included in this run.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    summary = [
        "# RAI Evaluation Summary",
        "",
        f"Computed: `{report['computed_at']}`",
        "",
        "This report is generated from the local synthetic simulator. It is not a claim of real-world performance.",
        "",
        "## Expected-behaviour models",
        "",
        "| Model | MAE | RMSE | R² | Test rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, metrics in report["model_metrics"].items():
        summary.append(
            f"| `{name}` | {metrics.get('mae')} | {metrics.get('rmse')} | "
            f"{metrics.get('r2')} | {metrics.get('n_test')} |"
        )
    summary.extend(
        [
            "",
            "## Scenario discrimination",
            "",
            f"- Definition: {scenarios['definition']}",
            f"- Correct: `{scenarios['correct']}/{scenarios['n_scenarios']}`",
            f"- Agreement: `{scenarios['accuracy']}`",
            "",
            "See `results.json` for per-scenario evidence and provenance.",
        ]
    )
    (OUTPUT_DIR / "summary.md").write_text("\n".join(summary) + "\n")
    print(f"wrote {OUTPUT_DIR / 'results.json'}")
    print(f"wrote {OUTPUT_DIR / 'summary.md'}")
    print(f"scenario agreement: {scenarios['correct']}/{scenarios['n_scenarios']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
