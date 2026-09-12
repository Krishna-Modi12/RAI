"""Orchestrates the real external CARE benchmark against the full downloaded Farm-A archive.

Named distinctly from `runner.py` in this package (which drives a separate, fixture-based
multi-track/5-baseline harness) to avoid two independently-developed benchmark drivers
fighting over one filename during this hackathon's concurrent Gate-2 work - see
`docs/evaluation/EXTERNAL_CARE.md` §0 for how that collision happened and why this file is
the one carrying the real full-archive run.

For every dataset CSV in a farm (`data/raw/care/<farm>/datasets/<event_id>.csv`), against the
farm's own `event_info.csv` labels:

1. Load the dataset through the (now sep=";"-fixed) `rai.ingest.care` loader, keeping every
   original row - `apply_quality_filter=True` still nulls out-of-range/frozen-sensor values,
   but `drop_non_normal=False, drop_duplicate_ts=False, required_signals=()` disable every
   row-dropping step, because the labelled event window is located by the dataset's own `id`
   column (`event_start_id`/`event_end_id` in event_info.csv) and any row drop would break
   that positional join. See docs/evaluation/EXTERNAL_CARE.md for why timestamp-based joining
   is unsafe here (the archive's per-dataset year-shift anonymisation).
2. Split on `care_train_test` ("train" fits the baseline, "prediction" is scored - never the
   reverse).
3. Build ground truth for the "prediction" split: 1 where `care_id` falls inside
   [event_start_id, event_end_id] on an anomaly-event dataset, 0 everywhere else (including
   the whole of a normal-behavior dataset - it has no anomaly by definition).
4. Fit one of the two paper-methodology baselines (`rai.eval.external.care.adapter`) on the
   dataset's own "train" rows, predict on "prediction" rows.
5. Score with `rai.eval.external.care.metrics`, exactly as published (Coverage/Accuracy per
   dataset, Reliability across all datasets at once, Earliness on each event's own window),
   then combine into the final CARE score.

Nothing here is fit to, or tuned against, any RAI model or synthetic result.

`run_farm` takes a farm directory as a parameter and has no Farm-A-specific logic; it is
reused as-is (not copied) for Farm B and Farm C in `docs/evaluation/EXTERNAL_GENERALIZATION.md`.
`run_all`/`FARMS`/the CLI entrypoint below remain Farm-A-only by design - this file's own
established default behavior is left unchanged; the multi-farm and cross-turbine/cross-farm
orchestration lives in the sibling `cross_turbine.py` and `cross_farm.py` modules instead.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from rai.eval.external.care.adapter import fit_isolation_forest, fit_zscore_threshold
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    accuracy_score,
    care_score,
    coverage_fbeta,
    criticality_series,
    event_reliability_fbeta,
    weighted_earliness_score,
)
from rai.ingest.care import CARE_ROOT, load_care_csv, load_event_info

ModelName = Literal["isolation_forest", "zscore_threshold"]
MODEL_NAMES: tuple[ModelName, ...] = ("isolation_forest", "zscore_threshold")

#: Farms attempted this round. Farm A only - see docs/evaluation/EXTERNAL_CARE.md for why
#: Farm B (257 columns) and Farm C (957 columns) are honestly scoped out rather than rushed.
FARMS: tuple[str, ...] = ("Wind Farm A",)

CRITICALITY_THRESHOLD = 72.0  # paper default: ~12h of consecutive detections at 10-min cadence


@dataclass(frozen=True)
class DatasetScore:
    farm: str
    event_id: int
    label: str
    description: str
    n_rows: int
    n_train: int
    n_prediction: int
    n_event_window_rows: int
    n_predicted_anomalous: int
    coverage_fbeta: float | None
    accuracy: float | None
    earliness: float | None
    max_criticality: int
    event_detected: bool


@dataclass(frozen=True)
class FarmModelResult:
    farm: str
    model: ModelName
    n_datasets: int
    n_anomaly_datasets: int
    n_normal_datasets: int
    mean_coverage_fbeta: float | None
    mean_earliness_ws: float | None
    event_reliability_fbeta: float
    mean_accuracy: float | None
    any_anomaly_predicted: bool
    care_score: float
    datasets: list[DatasetScore]


def _load_dataset(farm_dir: Path, event_id: int) -> pd.DataFrame:
    csv_path = farm_dir / "datasets" / f"{event_id}.csv"
    frame, _res, rep = load_care_csv(
        csv_path,
        apply_quality_filter=True,
        drop_non_normal=False,
        drop_duplicate_ts=False,
        required_signals=(),
    )
    if rep is not None and rep.rows_in != rep.rows_out:
        raise AssertionError(
            f"{csv_path} lost rows ({rep.rows_in} -> {rep.rows_out}); the id-based event "
            "join would silently misalign. This must not happen with the row-preserving "
            "quality_filter arguments this runner passes."
        )
    return frame


def _fit_baseline(model_name: ModelName, train_frame: pd.DataFrame):
    if model_name == "isolation_forest":
        return fit_isolation_forest(train_frame)
    return fit_zscore_threshold(train_frame)


def _score_dataset(
    farm: str, event_row: pd.Series, frame: pd.DataFrame, model_name: ModelName
) -> tuple[DatasetScore, DatasetReliabilityInput]:
    event_id = int(event_row["event_id"])
    label = (
        CareDatasetLabel.ANOMALY_EVENT
        if event_row["event_label"] == "anomaly"
        else CareDatasetLabel.NORMAL_BEHAVIOR
    )

    train_frame = frame.loc[frame["care_train_test"] == "train"]
    pred_frame = frame.loc[frame["care_train_test"] == "prediction"].sort_values("care_id")

    baseline = _fit_baseline(model_name, train_frame)
    prediction = baseline.predict(pred_frame)
    status_normal = (pred_frame["care_status_type_id"].to_numpy() == 0)
    care_ids = pred_frame["care_id"].to_numpy()

    if label is CareDatasetLabel.ANOMALY_EVENT:
        ground_truth = (care_ids >= int(event_row["event_start_id"])) & (
            care_ids <= int(event_row["event_end_id"])
        )
    else:
        ground_truth = np.zeros(len(pred_frame), dtype=bool)

    cov = (
        coverage_fbeta(ground_truth, prediction, status_normal)
        if label is CareDatasetLabel.ANOMALY_EVENT
        else None
    )
    acc = (
        accuracy_score(prediction, status_normal)
        if label is CareDatasetLabel.NORMAL_BEHAVIOR
        else None
    )
    if label is CareDatasetLabel.ANOMALY_EVENT and ground_truth.any():
        earliness = weighted_earliness_score(prediction[ground_truth])
    else:
        earliness = None

    crit = criticality_series(status_normal, prediction)
    max_crit = int(crit.max(initial=0))

    score = DatasetScore(
        farm=farm,
        event_id=event_id,
        label=label.value,
        description=str(event_row["event_description"]) if label is CareDatasetLabel.ANOMALY_EVENT else "",
        n_rows=len(frame),
        n_train=len(train_frame),
        n_prediction=len(pred_frame),
        n_event_window_rows=int(ground_truth.sum()),
        n_predicted_anomalous=int(prediction.sum()),
        coverage_fbeta=cov,
        accuracy=acc,
        earliness=earliness,
        max_criticality=max_crit,
        event_detected=max_crit >= CRITICALITY_THRESHOLD,
    )
    reliability_input = DatasetReliabilityInput(
        label=label, status_normal=status_normal, prediction=prediction
    )
    return score, reliability_input


def run_farm(farm_dir: Path, model_name: ModelName) -> FarmModelResult:
    events = load_event_info(farm_dir / "event_info.csv")
    dataset_scores: list[DatasetScore] = []
    reliability_inputs: list[DatasetReliabilityInput] = []
    any_anomaly_predicted = False

    for _, row in events.iterrows():
        frame = _load_dataset(farm_dir, int(row["event_id"]))
        score, reliability_input = _score_dataset(farm_dir.name, row, frame, model_name)
        dataset_scores.append(score)
        reliability_inputs.append(reliability_input)
        any_anomaly_predicted |= score.n_predicted_anomalous > 0

    coverages = [s.coverage_fbeta for s in dataset_scores if s.coverage_fbeta is not None]
    earlinesses = [s.earliness for s in dataset_scores if s.earliness is not None]
    accuracies = [s.accuracy for s in dataset_scores if s.accuracy is not None]

    mean_coverage = float(np.mean(coverages)) if coverages else None
    mean_earliness = float(np.mean(earlinesses)) if earlinesses else None
    mean_accuracy = float(np.mean(accuracies)) if accuracies else None
    reliability = event_reliability_fbeta(reliability_inputs, criticality_threshold=CRITICALITY_THRESHOLD)

    final = care_score(
        mean_coverage_fbeta=mean_coverage or 0.0,
        mean_earliness_ws=mean_earliness or 0.0,
        event_reliability=reliability,
        mean_accuracy=mean_accuracy if mean_accuracy is not None else 0.0,
        any_anomaly_predicted=any_anomaly_predicted,
    )

    return FarmModelResult(
        farm=farm_dir.name,
        model=model_name,
        n_datasets=len(dataset_scores),
        n_anomaly_datasets=sum(1 for s in dataset_scores if s.label == CareDatasetLabel.ANOMALY_EVENT.value),
        n_normal_datasets=sum(1 for s in dataset_scores if s.label == CareDatasetLabel.NORMAL_BEHAVIOR.value),
        mean_coverage_fbeta=mean_coverage,
        mean_earliness_ws=mean_earliness,
        event_reliability_fbeta=reliability,
        mean_accuracy=mean_accuracy,
        any_anomaly_predicted=any_anomaly_predicted,
        care_score=final,
        datasets=dataset_scores,
    )


def run_all(root: Path | None = None) -> list[FarmModelResult]:
    base = Path(root) if root is not None else CARE_ROOT
    results: list[FarmModelResult] = []
    for farm in FARMS:
        farm_dir = base / farm
        if not farm_dir.exists():
            raise FileNotFoundError(f"{farm_dir} not found - run discover() first")
        for model_name in MODEL_NAMES:
            results.append(run_farm(farm_dir, model_name))
    return results


def write_artifacts(results: list[FarmModelResult], out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir is not None else Path("artifacts/evaluation/gate2/external_care")
    out.mkdir(parents=True, exist_ok=True)

    payload = [asdict(r) for r in results]
    (out / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# External CARE benchmark - real results", ""]
    lines.append("| farm | model | CARE | coverage | earliness | reliability | accuracy | n datasets (anomaly/normal) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r.farm} | {r.model} | {r.care_score:.3f} | "
            f"{'n/a' if r.mean_coverage_fbeta is None else f'{r.mean_coverage_fbeta:.3f}'} | "
            f"{'n/a' if r.mean_earliness_ws is None else f'{r.mean_earliness_ws:.3f}'} | "
            f"{r.event_reliability_fbeta:.3f} | "
            f"{'n/a' if r.mean_accuracy is None else f'{r.mean_accuracy:.3f}'} | "
            f"{r.n_anomaly_datasets}/{r.n_normal_datasets} |"
        )
    lines.append("")
    for r in results:
        lines.append(f"## {r.farm} / {r.model} - per-dataset detail")
        lines.append("")
        lines.append("| event_id | label | description | coverage | earliness | max criticality | detected |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in r.datasets:
            lines.append(
                f"| {s.event_id} | {s.label} | {s.description} | "
                f"{'n/a' if s.coverage_fbeta is None else f'{s.coverage_fbeta:.3f}'} | "
                f"{'n/a' if s.earliness is None else f'{s.earliness:.3f}'} | "
                f"{s.max_criticality} | {s.event_detected} |"
            )
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    results = run_all()
    out_dir = write_artifacts(results)
    for r in results:
        print(f"{r.farm}/{r.model}: CARE={r.care_score:.3f} (n_datasets={r.n_datasets})")
    print(f"wrote {out_dir}")
