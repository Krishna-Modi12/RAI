"""Gate 5.1 – Real CARE benchmark for Wind Farms B and C.

Methodology
-----------
Uses `run_farm` from `rai.eval.external.care.farm_a_runner` without
modification – the same function that produced the validated Farm A
results (isolation_forest CARE=0.535, zscore_threshold CARE=0.506).

Scope
-----
* Farms evaluated : A (reproduced for cross-farm table), B, C
* Models          : isolation_forest, zscore_threshold  (paper §4.2.1-4.2.2)
* CARE components : Coverage (F_0.5), Accuracy (specificity), Reliability
                    (cross-dataset event F_0.5), Earliness (weighted)
* Nothing here uses internal RAI models or synthetic fleet metrics.

Outputs  (artifacts/evaluation/gate5_1/)
----------------------------------------
farm_summary.json   – machine-readable, one row per (farm, model)
farm_summary.csv    – same content as CSV
event_results.csv   – per-dataset breakdown for every farm × model pair
missed_events.csv   – anomaly-event datasets where event_detected=False
false_alarms.csv    – normal-behavior datasets with n_predicted_anomalous>0
provenance.json     – git hash, timestamp, CARE_ROOT, farm dataset counts
summary.md          – human-readable gate report appended to
                      docs/evaluation/EXTERNAL_GENERALIZATION.md

Status decision rule (per farm)
--------------------------------
PASS             : CARE ≥ 0.55 for both models on a farm
PARTIAL          : ≥ 1 model CARE ≥ 0.45, no model null
INSUFFICIENT_DATA: n_datasets < 5  OR  n_anomaly_datasets == 0
UNRESOLVED       : does not fit the above (score obtained but low/mixed)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rai.eval.external.care.farm_a_runner import (  # noqa: E402
    MODEL_NAMES,
    FarmModelResult,
    run_farm,
)
from rai.ingest.care import CARE_ROOT  # noqa: E402

OUT_DIR = Path("artifacts/evaluation/gate5_1")
DOCS_PATH = Path("docs/evaluation/EXTERNAL_GENERALIZATION.md")

ALL_FARMS = ("Wind Farm A", "Wind Farm B", "Wind Farm C")


# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

def _classify_status(results_for_farm: list[FarmModelResult]) -> str:
    """Return a single status string for a farm across both models."""
    if not results_for_farm:
        return "INSUFFICIENT_DATA"
    r0 = results_for_farm[0]
    if r0.n_datasets < 5 or r0.n_anomaly_datasets == 0:
        return "INSUFFICIENT_DATA"
    scores = [r.care_score for r in results_for_farm]
    if all(s >= 0.55 for s in scores):
        return "PASS"
    if any(s >= 0.45 for s in scores):
        return "PARTIAL"
    return "UNRESOLVED"


# ---------------------------------------------------------------------------
# Provenance helper
# ---------------------------------------------------------------------------

def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _write_farm_summary(all_results: list[FarmModelResult], out_dir: Path) -> None:
    rows = []
    farms_seen: dict[str, list[FarmModelResult]] = {}
    for r in all_results:
        farms_seen.setdefault(r.farm, []).append(r)

    for _farm, res_list in farms_seen.items():
        status = _classify_status(res_list)
        for r in res_list:
            rows.append({
                "farm": r.farm,
                "model": r.model,
                "care_score": round(r.care_score, 4),
                "mean_coverage_fbeta": round(r.mean_coverage_fbeta, 4) if r.mean_coverage_fbeta is not None else None,
                "mean_earliness_ws": round(r.mean_earliness_ws, 4) if r.mean_earliness_ws is not None else None,
                "event_reliability_fbeta": round(r.event_reliability_fbeta, 4),
                "mean_accuracy": round(r.mean_accuracy, 4) if r.mean_accuracy is not None else None,
                "n_datasets": r.n_datasets,
                "n_anomaly_datasets": r.n_anomaly_datasets,
                "n_normal_datasets": r.n_normal_datasets,
                "any_anomaly_predicted": r.any_anomaly_predicted,
                "gate_status": status,
            })

    (out_dir / "farm_summary.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "farm_summary.csv", index=False)
    print(f"  Wrote farm_summary.json / farm_summary.csv  ({len(rows)} rows)")


def _write_event_results(all_results: list[FarmModelResult], out_dir: Path) -> None:
    rows = []
    for r in all_results:
        for ds in r.datasets:
            d = asdict(ds)
            d["model"] = r.model
            rows.append(d)
    if not rows:
        return
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "event_results.csv", index=False)
    print(f"  Wrote event_results.csv  ({len(rows)} rows)")


def _write_missed_events(all_results: list[FarmModelResult], out_dir: Path) -> None:
    rows = []
    for r in all_results:
        for ds in r.datasets:
            if ds.label == "anomaly_event" and not ds.event_detected:
                d = asdict(ds)
                d["model"] = r.model
                rows.append(d)
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    df.to_csv(out_dir / "missed_events.csv", index=False)
    print(f"  Wrote missed_events.csv  ({len(rows)} rows)")


def _write_false_alarms(all_results: list[FarmModelResult], out_dir: Path) -> None:
    rows = []
    for r in all_results:
        for ds in r.datasets:
            if ds.label == "normal_behavior" and ds.n_predicted_anomalous > 0:
                d = asdict(ds)
                d["model"] = r.model
                rows.append(d)
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    df.to_csv(out_dir / "false_alarms.csv", index=False)
    print(f"  Wrote false_alarms.csv  ({len(rows)} rows)")


def _write_provenance(out_dir: Path, dataset_counts: dict[str, int]) -> None:
    prov = {
        "gate": "5.1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_hash": _git_hash(),
        "care_root": str(CARE_ROOT),
        "farms": ALL_FARMS,
        "models": MODEL_NAMES,
        "dataset_counts": dataset_counts,
        "scoring_note": (
            "CARE components match Gück, Roelofs & Faulstich (2024) paper equations. "
            "Baselines mirror paper §4.2.1-4.2.2. "
            "No internal RAI model is used."
        ),
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(prov, indent=2), encoding="utf-8"
    )
    print("  Wrote provenance.json")


def _write_summary_md(all_results: list[FarmModelResult], out_dir: Path) -> str:
    """Return the gate-5.1 markdown block (also written to out_dir/summary.md)."""
    farms_seen: dict[str, list[FarmModelResult]] = {}
    for r in all_results:
        farms_seen.setdefault(r.farm, []).append(r)

    lines: list[str] = [
        "## Gate 5.1 – Multi-Farm CARE Benchmark",
        "",
        f"*Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "### Cross-Farm Summary",
        "",
        "| Farm | Model | CARE | Coverage | Earliness | Reliability | Accuracy | N datasets (A/N) | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for farm, res_list in farms_seen.items():
        status = _classify_status(res_list)
        for r in res_list:
            cov = f"{r.mean_coverage_fbeta:.3f}" if r.mean_coverage_fbeta is not None else "n/a"
            ear = f"{r.mean_earliness_ws:.3f}" if r.mean_earliness_ws is not None else "n/a"
            acc = f"{r.mean_accuracy:.3f}" if r.mean_accuracy is not None else "n/a"
            lines.append(
                f"| {farm} | {r.model} | {r.care_score:.3f} | {cov} | {ear} | "
                f"{r.event_reliability_fbeta:.3f} | {acc} | "
                f"{r.n_anomaly_datasets}/{r.n_normal_datasets} | {status} |"
            )
    lines.append("")

    # Per-farm detailed section
    for farm, res_list in farms_seen.items():
        status = _classify_status(res_list)
        lines += [
            f"### {farm} — Gate Status: {status}",
            "",
            "| event_id | label | description | model | coverage | earliness | max_crit | detected |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in res_list:
            for ds in r.datasets:
                cov = f"{ds.coverage_fbeta:.3f}" if ds.coverage_fbeta is not None else "n/a"
                ear = f"{ds.earliness:.3f}" if ds.earliness is not None else "n/a"
                lines.append(
                    f"| {ds.event_id} | {ds.label} | {ds.description[:40] if ds.description else ''} "
                    f"| {r.model} | {cov} | {ear} | {ds.max_criticality} | {ds.event_detected} |"
                )
        lines.append("")

    # Status legend
    lines += [
        "### Status Legend",
        "",
        "| Status | Criterion |",
        "|---|---|",
        "| PASS | CARE ≥ 0.55 for both models |",
        "| PARTIAL | ≥ 1 model CARE ≥ 0.45, no null |",
        "| INSUFFICIENT_DATA | < 5 datasets or no anomaly events |",
        "| UNRESOLVED | Score obtained but does not meet PARTIAL |",
        "",
        "---",
        "",
    ]

    md = "\n".join(lines)
    (out_dir / "summary.md").write_text(md, encoding="utf-8")
    return md


def _append_to_generalization_doc(md_block: str) -> None:
    """Idempotently append the Gate-5.1 block to EXTERNAL_GENERALIZATION.md."""
    marker = "## Gate 5.1 – Multi-Farm CARE Benchmark"
    if DOCS_PATH.exists():
        existing = DOCS_PATH.read_text(encoding="utf-8")
        if marker in existing:
            # Replace existing block from marker to next top-level heading
            before = existing[: existing.index(marker)]
            after_start = existing.index(marker) + len(marker)
            rest = existing[after_start:]
            # Find next ## heading after the marker
            import re
            m = re.search(r"\n## ", rest)
            after = rest[m.start():] if m else ""
            new_text = before + md_block + after
        else:
            new_text = existing.rstrip() + "\n\n" + md_block
    else:
        new_text = md_block

    DOCS_PATH.write_text(new_text, encoding="utf-8")
    print(f"  Updated {DOCS_PATH}")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results: list[FarmModelResult] = []
    dataset_counts: dict[str, int] = {}

    for farm_name in ALL_FARMS:
        farm_dir = CARE_ROOT / farm_name
        if not farm_dir.exists():
            print(f"[SKIP] {farm_name} – directory not found at {farm_dir}")
            continue

        ds_files = list((farm_dir / "datasets").glob("*.csv")) if (farm_dir / "datasets").exists() else []
        dataset_counts[farm_name] = len(ds_files)
        print(f"\n{'='*60}")
        print(f"Farm: {farm_name}  ({len(ds_files)} dataset files)")
        print(f"{'='*60}")

        for model in MODEL_NAMES:
            print(f"  -> running {model} ...", flush=True)
            try:
                result = run_farm(farm_dir, model)
                all_results.append(result)
                print(
                    f"    CARE={result.care_score:.4f}  "
                    f"cov={result.mean_coverage_fbeta}  "
                    f"rel={result.event_reliability_fbeta:.4f}  "
                    f"acc={result.mean_accuracy}  "
                    f"earl={result.mean_earliness_ws}"
                )
            except Exception as exc:
                print(f"    ERROR: {exc}", file=sys.stderr)

    # Write artifacts
    print(f"\nWriting artifacts to {OUT_DIR}/ …")
    _write_farm_summary(all_results, OUT_DIR)
    _write_event_results(all_results, OUT_DIR)
    _write_missed_events(all_results, OUT_DIR)
    _write_false_alarms(all_results, OUT_DIR)
    _write_provenance(OUT_DIR, dataset_counts)
    md_block = _write_summary_md(all_results, OUT_DIR)
    _append_to_generalization_doc(md_block)

    # Console summary
    print("\n" + "=" * 60)
    print("GATE 5.1 – FINAL SUMMARY")
    print("=" * 60)
    farms_seen: dict[str, list[FarmModelResult]] = {}
    for r in all_results:
        farms_seen.setdefault(r.farm, []).append(r)
    for farm, res_list in farms_seen.items():
        status = _classify_status(res_list)
        print(f"  {farm}  [{status}]")
        for r in res_list:
            print(f"    {r.model:22s}  CARE={r.care_score:.4f}")


if __name__ == "__main__":
    main()
