"""
Gate 5.1 - Run CARE baselines for Farm B and Farm C, then produce
a combined multi-farm results JSON + summary markdown.

Farm A results are loaded from the existing artifacts/evaluation/gate2/external_care/results.json
and are NOT re-computed (they are the verified canonical results).

Farm B and Farm C are scored here using the same run_farm() function.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from rai.eval.external.care.farm_a_runner import (
    MODEL_NAMES,
    FarmModelResult,
    run_farm,
)
from rai.ingest.care import CARE_ROOT

OUT_DIR = Path("artifacts/evaluation/gate51/external_care")

def load_farm_a_results() -> list[FarmModelResult]:
    """Load the canonically verified Farm A results from disk (do NOT rerun)."""
    p = Path("artifacts/evaluation/gate2/external_care/results.json")
    raw = json.loads(p.read_text())
    # Reconstruct as plain dicts - write_artifacts accepts dataclass OR dict
    # We convert back to FarmModelResult via the dataclass
    from rai.eval.external.care.farm_a_runner import DatasetScore

    results = []
    for r in raw:
        datasets = [DatasetScore(**ds) for ds in r["datasets"]]
        results.append(FarmModelResult(
            farm=r["farm"],
            model=r["model"],
            n_datasets=r["n_datasets"],
            n_anomaly_datasets=r["n_anomaly_datasets"],
            n_normal_datasets=r["n_normal_datasets"],
            mean_coverage_fbeta=r["mean_coverage_fbeta"],
            mean_earliness_ws=r["mean_earliness_ws"],
            event_reliability_fbeta=r["event_reliability_fbeta"],
            mean_accuracy=r["mean_accuracy"],
            any_anomaly_predicted=r["any_anomaly_predicted"],
            care_score=r["care_score"],
            datasets=datasets,
        ))
    return results


def run_farm_b_and_c() -> list[FarmModelResult]:
    results = []
    for farm_name in ("Wind Farm B", "Wind Farm C"):
        farm_dir = CARE_ROOT / farm_name
        if not farm_dir.exists():
            print(f"[SKIP] {farm_name}: directory not found at {farm_dir}")
            continue
        for model_name in MODEL_NAMES:
            t0 = time.perf_counter()
            print(f"[RUN]  {farm_name} / {model_name} ...", flush=True)
            result = run_farm(farm_dir, model_name)
            elapsed = time.perf_counter() - t0
            print(
                f"[DONE] {farm_name} / {model_name}: "
                f"CARE={result.care_score:.3f}  "
                f"n={result.n_datasets}  "
                f"anomaly={result.n_anomaly_datasets}  "
                f"normal={result.n_normal_datasets}  "
                f"({elapsed:.1f}s)",
                flush=True,
            )
            results.append(result)
    return results


def write_combined(all_results: list[FarmModelResult]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Raw JSON
    payload = [asdict(r) for r in all_results]
    (OUT_DIR / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Summary table
    lines = [
        "# Gate 5.1 — External CARE Multi-Farm Scorecard",
        "",
        "Farm A results are the pre-verified canonical baseline (IF=0.535, Z-score=0.506).",
        "Farm B and C are scored here for the first time.",
        "",
        "| Farm | Model | CARE | Coverage | Earliness | Reliability | Accuracy | Datasets (A/N) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in all_results:
        cov = "n/a" if r.mean_coverage_fbeta is None else f"{r.mean_coverage_fbeta:.3f}"
        ear = "n/a" if r.mean_earliness_ws is None else f"{r.mean_earliness_ws:.3f}"
        acc = "n/a" if r.mean_accuracy is None else f"{r.mean_accuracy:.3f}"
        lines.append(
            f"| {r.farm} | {r.model} | {r.care_score:.3f} | "
            f"{cov} | {ear} | {r.event_reliability_fbeta:.3f} | "
            f"{acc} | {r.n_anomaly_datasets}/{r.n_normal_datasets} |"
        )
    lines.append("")

    # Per-farm per-dataset detail
    for r in all_results:
        lines.append(f"## {r.farm} / {r.model}")
        lines.append("")
        lines.append("| event_id | label | coverage | earliness | max_crit | detected |")
        lines.append("|---|---|---|---|---|---|")
        for s in r.datasets:
            cov = "n/a" if s.coverage_fbeta is None else f"{s.coverage_fbeta:.3f}"
            ear = "n/a" if s.earliness is None else f"{s.earliness:.3f}"
            lines.append(
                f"| {s.event_id} | {s.label} | {cov} | {ear} | "
                f"{s.max_criticality} | {s.event_detected} |"
            )
        lines.append("")

    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[ARTIFACTS] written to {OUT_DIR}")


def main():
    print("=== Gate 5.1: External CARE Multi-Farm Benchmark ===\n")

    print("[LOAD] Farm A (pre-verified, not re-run)...")
    farm_a = load_farm_a_results()
    for r in farm_a:
        print(f"  {r.farm} / {r.model}: CARE={r.care_score:.3f}")

    print("\n[RUN] Farm B and Farm C baselines...")
    farm_bc = run_farm_b_and_c()

    all_results = farm_a + farm_bc
    write_combined(all_results)

    print("\n=== Final Scorecard ===")
    for r in all_results:
        cov = "n/a" if r.mean_coverage_fbeta is None else f"{r.mean_coverage_fbeta:.3f}"
        ear = "n/a" if r.mean_earliness_ws is None else f"{r.mean_earliness_ws:.3f}"
        print(
            f"  {r.farm:<18} | {r.model:<20} | "
            f"CARE={r.care_score:.3f}  cov={cov}  ear={ear}  "
            f"rel={r.event_reliability_fbeta:.3f}  "
            f"n={r.n_datasets}(A={r.n_anomaly_datasets},N={r.n_normal_datasets})"
        )


if __name__ == "__main__":
    main()
