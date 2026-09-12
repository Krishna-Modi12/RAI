"""Leave-one-turbine-out evaluation within a single CARE farm (Gate C).

Farm A's 22 datasets come from 5 distinct turbines (`asset_id` 0, 10, 11, 13, 21), each
contributing 4-5 datasets (a mix of anomaly-event and normal-behavior periods - see
`docs/evaluation/EXTERNAL_GENERALIZATION.md` for the exact per-turbine table). This module
asks a different question than `farm_a_runner.py`: not "how do these two baselines do on
Farm A overall", but "does a baseline fit on turbines {B,C,D,E} detect a fault on unseen
turbine A, or did the per-dataset baseline in `farm_a_runner.py` only work (to the modest
extent it did) because it was fit on that same turbine's own earlier data?"

For each held-out turbine, one baseline is fit on the pooled TRAIN rows of every OTHER
turbine in the farm, then scored against the held-out turbine's own datasets using the exact
same CARE metrics as `farm_a_runner.py` (imported, not reimplemented). This is a genuinely
different fit per fold - it is reported next to (never averaged with) `farm_a_runner.py`'s
own per-dataset, in-turbine numbers in `docs/evaluation/EXTERNAL_GENERALIZATION.md`.

Every turbine in Farm A has at least one real anomaly-event dataset (minimum: turbine 11,
with exactly 1), so a per-turbine CARE-style aggregate is always computable when anomaly
datasets exist in the held-out fold - but sample sizes are small (4-5 datasets per fold).
A fold with zero anomaly-event datasets in its held-out set is marked
`status="INSUFFICIENT_DATA"` with `care_score=None`, never a fabricated number.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from rai.eval.external.care.farm_a_runner import (
    MODEL_NAMES,
    DatasetScore,
    ModelName,
    _fit_baseline,
    _load_dataset,
)
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
from rai.ingest.care import load_event_info

CRITICALITY_THRESHOLD = 72.0


@dataclass(frozen=True)
class TurbineFoldResult:
    farm: str
    model: ModelName
    test_turbine: str
    train_turbines: tuple[str, ...]
    n_test_datasets: int
    n_test_anomaly_datasets: int
    n_test_normal_datasets: int
    mean_coverage_fbeta: float | None
    mean_earliness_ws: float | None
    event_reliability_fbeta: float | None
    mean_accuracy: float | None
    care_score: float | None
    status: str
    datasets: list[DatasetScore]


def _turbine_of(frame: pd.DataFrame) -> str:
    return str(frame["asset_id"].iloc[0])


def _score_with_baseline(
    farm: str, event_row: pd.Series, frame: pd.DataFrame, baseline: object
) -> tuple[DatasetScore, DatasetReliabilityInput]:
    event_id = int(event_row["event_id"])
    label = (
        CareDatasetLabel.ANOMALY_EVENT
        if event_row["event_label"] == "anomaly"
        else CareDatasetLabel.NORMAL_BEHAVIOR
    )
    pred_frame = frame.loc[frame["care_train_test"] == "prediction"].sort_values("care_id")
    prediction = baseline.predict(pred_frame)  # type: ignore[attr-defined]
    status_normal = pred_frame["care_status_type_id"].to_numpy() == 0
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
    earliness = (
        weighted_earliness_score(prediction[ground_truth])
        if label is CareDatasetLabel.ANOMALY_EVENT and ground_truth.any()
        else None
    )
    crit = criticality_series(status_normal, prediction)
    max_crit = int(crit.max(initial=0))

    score = DatasetScore(
        farm=farm,
        event_id=event_id,
        label=label.value,
        description=str(event_row["event_description"]) if label is CareDatasetLabel.ANOMALY_EVENT else "",
        n_rows=len(frame),
        n_train=int((frame["care_train_test"] == "train").sum()),
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


def run_leave_one_turbine_out(farm_dir: Path, model_name: ModelName) -> list[TurbineFoldResult]:
    """One fold per turbine present in `farm_dir`: fit on every OTHER turbine's train rows."""
    events = load_event_info(farm_dir / "event_info.csv")
    frames: dict[int, pd.DataFrame] = {}
    turbine_of: dict[int, str] = {}
    for _, row in events.iterrows():
        eid = int(row["event_id"])
        frame = _load_dataset(farm_dir, eid)
        frames[eid] = frame
        turbine_of[eid] = _turbine_of(frame)

    turbines = sorted(set(turbine_of.values()))
    results: list[TurbineFoldResult] = []

    for test_turbine in turbines:
        train_event_ids = [eid for eid, t in turbine_of.items() if t != test_turbine]
        test_event_ids = [eid for eid, t in turbine_of.items() if t == test_turbine]
        train_turbines = tuple(sorted({turbine_of[eid] for eid in train_event_ids}))

        pooled_train = pd.concat(
            [frames[eid].loc[frames[eid]["care_train_test"] == "train"] for eid in train_event_ids],
            ignore_index=True,
        )
        baseline = _fit_baseline(model_name, pooled_train)

        dataset_scores: list[DatasetScore] = []
        reliability_inputs: list[DatasetReliabilityInput] = []
        any_anomaly_predicted = False
        for eid in sorted(test_event_ids):
            row = events.loc[events["event_id"] == eid].iloc[0]
            score, reliability_input = _score_with_baseline(farm_dir.name, row, frames[eid], baseline)
            dataset_scores.append(score)
            reliability_inputs.append(reliability_input)
            any_anomaly_predicted |= score.n_predicted_anomalous > 0

        n_anom = sum(1 for s in dataset_scores if s.label == CareDatasetLabel.ANOMALY_EVENT.value)
        n_norm = sum(1 for s in dataset_scores if s.label == CareDatasetLabel.NORMAL_BEHAVIOR.value)
        coverages = [s.coverage_fbeta for s in dataset_scores if s.coverage_fbeta is not None]
        earlinesses = [s.earliness for s in dataset_scores if s.earliness is not None]
        accuracies = [s.accuracy for s in dataset_scores if s.accuracy is not None]

        mean_coverage = float(np.mean(coverages)) if coverages else None
        mean_earliness = float(np.mean(earlinesses)) if earlinesses else None
        mean_accuracy = float(np.mean(accuracies)) if accuracies else None
        reliability = (
            event_reliability_fbeta(reliability_inputs, criticality_threshold=CRITICALITY_THRESHOLD)
            if n_anom > 0
            else None
        )

        if n_anom == 0:
            status = "INSUFFICIENT_DATA"
            final = None
        else:
            status = "COMPUTED"
            final = care_score(
                mean_coverage_fbeta=mean_coverage or 0.0,
                mean_earliness_ws=mean_earliness or 0.0,
                event_reliability=reliability or 0.0,
                mean_accuracy=mean_accuracy if mean_accuracy is not None else 0.0,
                any_anomaly_predicted=any_anomaly_predicted,
            )

        results.append(
            TurbineFoldResult(
                farm=farm_dir.name,
                model=model_name,
                test_turbine=test_turbine,
                train_turbines=train_turbines,
                n_test_datasets=len(dataset_scores),
                n_test_anomaly_datasets=n_anom,
                n_test_normal_datasets=n_norm,
                mean_coverage_fbeta=mean_coverage,
                mean_earliness_ws=mean_earliness,
                event_reliability_fbeta=reliability,
                mean_accuracy=mean_accuracy,
                care_score=final,
                status=status,
                datasets=dataset_scores,
            )
        )
    return results


def run_all(farm_dir: Path) -> list[TurbineFoldResult]:
    out: list[TurbineFoldResult] = []
    for model_name in MODEL_NAMES:
        out.extend(run_leave_one_turbine_out(farm_dir, model_name))
    return out


def write_artifacts(results: list[TurbineFoldResult], out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir is not None else Path("artifacts/evaluation/gate2/external_care")
    out.mkdir(parents=True, exist_ok=True)
    payload = [asdict(r) for r in results]
    (out / "cross_turbine_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Cross-turbine (leave-one-turbine-out) - Wind Farm A", ""]
    lines.append(
        "| model | held-out turbine | n train turbines | n datasets (anomaly/normal) | "
        "CARE | coverage | earliness | reliability | accuracy | status |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r.model} | {r.test_turbine} | {len(r.train_turbines)} | "
            f"{r.n_test_anomaly_datasets}/{r.n_test_normal_datasets} | "
            f"{'n/a' if r.care_score is None else f'{r.care_score:.3f}'} | "
            f"{'n/a' if r.mean_coverage_fbeta is None else f'{r.mean_coverage_fbeta:.3f}'} | "
            f"{'n/a' if r.mean_earliness_ws is None else f'{r.mean_earliness_ws:.3f}'} | "
            f"{'n/a' if r.event_reliability_fbeta is None else f'{r.event_reliability_fbeta:.3f}'} | "
            f"{'n/a' if r.mean_accuracy is None else f'{r.mean_accuracy:.3f}'} | {r.status} |"
        )
    (out / "cross_turbine_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    from rai.ingest.care import CARE_ROOT

    results = run_all(CARE_ROOT / "Wind Farm A")
    out_dir = write_artifacts(results)
    for r in results:
        care_str = "n/a" if r.care_score is None else f"{r.care_score:.3f}"
        print(f"{r.model} held-out={r.test_turbine}: CARE={care_str} status={r.status}")
    print(f"wrote {out_dir}")
