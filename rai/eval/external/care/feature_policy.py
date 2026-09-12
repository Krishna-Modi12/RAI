"""Gate 5.4 Phase 3: CARE_NARROW vs CARE_SEMANTIC - is ~0.53 CARE a model limit or a feature
limit?

Two explicitly frozen, named feature policies, evaluated with the exact same two baselines,
the exact same CARE scoring (`rai.eval.external.care.metrics`), and the exact same train/
prediction split logic as `farm_a_runner.py` - the *only* thing that differs is which raw
CARE columns `rai.ingest.care.load_care_csv` is allowed to resolve into canonical features:

* **CARE_NARROW** - `sensor_map=None`, i.e. exactly what `farm_a_runner.py` already does.
  Resolves to `wind_speed_ms` + `power_kw` (2 usable feature columns) on every farm.
* **CARE_SEMANTIC** - `sensor_map=feature_inventory.build_safe_sensor_map(...)`, i.e. CARE's
  own supplied `feature_description.csv` text is used to translate anonymised `sensor_N`
  columns before alias matching. Resolves to 9-13 usable feature columns depending on farm
  (see `docs/evaluation/EXTERNAL_GENERALIZATION.md` Gate 5.4 section for the exact list per
  farm - built by `feature_inventory.py`, not duplicated here).

No target labels, no event metadata, and no future prediction-period rows are ever used to
build or select either policy - both are fixed before any dataset is scored, from CARE's own
supplied metadata alone (`feature_inventory.build_safe_sensor_map`). Neither policy is tuned
after looking at a CARE score.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import numpy as np

from rai.eval.external.care.farm_a_runner import (
    CRITICALITY_THRESHOLD,
    MODEL_NAMES,
    DatasetScore,
    FarmModelResult,
    ModelName,
    _score_dataset,  # fits its own baseline on train rows internally; see farm_a_runner.py
)
from rai.eval.external.care.feature_inventory import (
    build_safe_sensor_map,
    load_feature_descriptions,
)
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    care_score,
    event_reliability_fbeta,
)
from rai.ingest.care import load_care_csv, load_event_info

FeaturePolicy = Literal["care_narrow", "care_semantic"]
POLICIES: tuple[FeaturePolicy, ...] = ("care_narrow", "care_semantic")


def _sensor_map_for(farm_dir: Path, policy: FeaturePolicy) -> dict[str, str] | None:
    if policy == "care_narrow":
        return None
    return build_safe_sensor_map(load_feature_descriptions(farm_dir))


def _load_dataset_with_policy(farm_dir: Path, event_id: int, sensor_map: dict[str, str] | None):
    csv_path = farm_dir / "datasets" / f"{event_id}.csv"
    frame, _res, rep = load_care_csv(
        csv_path,
        sensor_map=sensor_map,
        apply_quality_filter=True,
        drop_non_normal=False,
        drop_duplicate_ts=False,
        required_signals=(),
    )
    if rep is not None and rep.rows_in != rep.rows_out:
        raise AssertionError(
            f"{csv_path} lost rows ({rep.rows_in} -> {rep.rows_out}) under policy scoring; "
            "the id-based event join would silently misalign."
        )
    return frame


def run_farm_with_policy(farm_dir: Path, model_name: ModelName, policy: FeaturePolicy) -> FarmModelResult:
    """Same aggregation as `farm_a_runner.run_farm`, only the dataset loader differs."""
    sensor_map = _sensor_map_for(farm_dir, policy)
    events = load_event_info(farm_dir / "event_info.csv")
    dataset_scores: list[DatasetScore] = []
    reliability_inputs: list[DatasetReliabilityInput] = []
    any_anomaly_predicted = False

    for _, row in events.iterrows():
        frame = _load_dataset_with_policy(farm_dir, int(row["event_id"]), sensor_map)
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


def run_all(root: Path, farms: tuple[str, ...]) -> dict[str, FarmModelResult]:
    """Keys are f"{farm}|{model}|{policy}" so results never collide across the 3D grid."""
    results: dict[str, FarmModelResult] = {}
    for farm in farms:
        farm_dir = root / farm
        for policy in POLICIES:
            for model_name in MODEL_NAMES:
                key = f"{farm}|{model_name}|{policy}"
                results[key] = run_farm_with_policy(farm_dir, model_name, policy)
    return results


def write_comparison_csv(results: dict[str, FarmModelResult], out_path: Path) -> None:
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "farm",
                "model",
                "policy",
                "n_datasets",
                "n_anomaly_datasets",
                "n_normal_datasets",
                "care_score",
                "coverage",
                "earliness",
                "reliability",
                "accuracy",
            ]
        )
        for key, r in results.items():
            farm, model, policy = key.split("|")
            writer.writerow(
                [
                    farm,
                    model,
                    policy,
                    r.n_datasets,
                    r.n_anomaly_datasets,
                    r.n_normal_datasets,
                    f"{r.care_score:.4f}",
                    "" if r.mean_coverage_fbeta is None else f"{r.mean_coverage_fbeta:.4f}",
                    "" if r.mean_earliness_ws is None else f"{r.mean_earliness_ws:.4f}",
                    f"{r.event_reliability_fbeta:.4f}",
                    "" if r.mean_accuracy is None else f"{r.mean_accuracy:.4f}",
                ]
            )


def write_json(results: dict[str, FarmModelResult], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: asdict(r) for key, r in results.items()}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    from rai.ingest.care import CARE_ROOT

    results = run_all(CARE_ROOT, ("Wind Farm A", "Wind Farm B"))
    out_dir = Path("artifacts/evaluation/external_care")
    write_comparison_csv(results, out_dir / "feature_policy_comparison.csv")
    write_json(results, out_dir / "feature_policy_comparison.json")
    for key, r in results.items():
        print(f"{key}: CARE={r.care_score:.3f}")
    print(f"wrote {out_dir}")
