"""Gate 5.4 Phase 4: re-run the A->B / A->C cross-farm transfer under CARE_SEMANTIC.

`cross_farm.py` (Gate D, prior gate) fits and scores using `farm_a_runner._load_dataset`,
which never passes a `sensor_map` to `rai.ingest.care.load_care_csv` - so its feature
intersection across farms is always the CARE_NARROW pair (`wind_speed_ms`, `power_kw`). This
module is the same transfer protocol - fit once on the source farm's pooled TRAIN rows,
score unmodified on every target-farm dataset, never refit - but with each farm's dataset
loaded through its own CARE_SEMANTIC `sensor_map` (`feature_policy.build_safe_sensor_map`)
first. The feature intersection actually used per pair is computed from the loaded data
(`cross_farm._intersected_columns`), not assumed: whichever of the 14
`rai.eval.external.care.adapter.FEATURE_COLUMNS` resolve on *both* farms is what gets used,
which `feature_inventory.py` independently found to be the same 6 signals on all three farms
(`gearbox_oil_temp_c, pitch_angle_deg, power_kw, rotor_rpm, wind_direction_deg,
wind_speed_ms`).

Language discipline (binding for this module's outputs, per the Gate 5.4 brief): a higher or
lower CARE score for the transferred model relative to the target's own in-farm CARE_SEMANTIC
run (`feature_policy.py`) is reported as "observed under the implemented transfer protocol,"
never as "generalizes" or "robust" - matching semantic *category* across farms (e.g. both
farms have *a* gearbox-oil-temperature sensor) does not establish the two farms' sensors are
on a comparable physical scale (different turbine models, different gearbox designs).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from rai.eval.external.care.cross_farm import (
    CrossFarmResult,
    _fit_on_columns,
    _intersected_columns,
)
from rai.eval.external.care.cross_turbine import _score_with_baseline
from rai.eval.external.care.farm_a_runner import MODEL_NAMES, DatasetScore, ModelName
from rai.eval.external.care.feature_policy import _load_dataset_with_policy, _sensor_map_for
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    care_score,
    event_reliability_fbeta,
)
from rai.ingest.care import load_event_info


def _load_farm_semantic(farm_dir: Path) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    sensor_map = _sensor_map_for(farm_dir, "care_semantic")
    events = load_event_info(farm_dir / "event_info.csv")
    frames = {
        int(row["event_id"]): _load_dataset_with_policy(farm_dir, int(row["event_id"]), sensor_map)
        for _, row in events.iterrows()
    }
    return events, frames  # type: ignore[return-value]


def run_transfer_semantic(source_dir: Path, target_dir: Path, model_name: ModelName) -> CrossFarmResult:
    _source_events, source_frames = _load_farm_semantic(source_dir)
    target_events, target_frames = _load_farm_semantic(target_dir)

    source_train = pd.concat(
        [f.loc[f["care_train_test"] == "train"] for f in source_frames.values()], ignore_index=True
    )
    columns = _intersected_columns(source_train, next(iter(target_frames.values())))

    if not columns:
        return CrossFarmResult(
            source_farm=source_dir.name,
            target_farm=target_dir.name,
            model=model_name,
            feature_intersection=(),
            n_target_datasets=len(target_frames),
            n_target_anomaly_datasets=0,
            n_target_normal_datasets=0,
            mean_coverage_fbeta=None,
            mean_earliness_ws=None,
            event_reliability_fbeta=None,
            mean_accuracy=None,
            care_score=None,
            status="INSUFFICIENT_DATA",
            datasets=[],
        )

    baseline = _fit_on_columns(model_name, source_train, columns)

    dataset_scores: list[DatasetScore] = []
    reliability_inputs: list[DatasetReliabilityInput] = []
    any_anomaly_predicted = False
    for _, row in target_events.iterrows():
        eid = int(row["event_id"])
        score, reliability_input = _score_with_baseline(target_dir.name, row, target_frames[eid], baseline)
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
    reliability = event_reliability_fbeta(reliability_inputs) if n_anom > 0 else None

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

    return CrossFarmResult(
        source_farm=source_dir.name,
        target_farm=target_dir.name,
        model=model_name,
        feature_intersection=tuple(columns),
        n_target_datasets=len(dataset_scores),
        n_target_anomaly_datasets=n_anom,
        n_target_normal_datasets=n_norm,
        mean_coverage_fbeta=mean_coverage,
        mean_earliness_ws=mean_earliness,
        event_reliability_fbeta=reliability,
        mean_accuracy=mean_accuracy,
        care_score=final,
        status=status,
        datasets=dataset_scores,
    )


def run_all(root: Path, pairs: tuple[tuple[str, str], ...]) -> list[CrossFarmResult]:
    results: list[CrossFarmResult] = []
    for source, target in pairs:
        for model_name in MODEL_NAMES:
            results.append(run_transfer_semantic(root / source, root / target, model_name))
    return results


def write_artifacts(results: list[CrossFarmResult], out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir is not None else Path("artifacts/evaluation/external_care")
    out.mkdir(parents=True, exist_ok=True)
    payload = [asdict(r) for r in results]
    (out / "cross_farm_semantic_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Cross-farm transfer under CARE_SEMANTIC (Gate 5.4 Phase 4)",
        "",
        "Fit once on source farm's pooled TRAIN rows using CARE_SEMANTIC-resolved columns, "
        "score unmodified on every target-farm dataset, never refit. Feature intersection is "
        "computed from the loaded data, not assumed.",
        "",
    ]
    lines.append(
        "| model | source -> target | feature intersection | n datasets (anomaly/normal) | "
        "CARE | coverage | earliness | reliability | accuracy | status |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r.model} | {r.source_farm} -> {r.target_farm} | {', '.join(r.feature_intersection) or 'none'} | "
            f"{r.n_target_anomaly_datasets}/{r.n_target_normal_datasets} | "
            f"{'n/a' if r.care_score is None else f'{r.care_score:.3f}'} | "
            f"{'n/a' if r.mean_coverage_fbeta is None else f'{r.mean_coverage_fbeta:.3f}'} | "
            f"{'n/a' if r.mean_earliness_ws is None else f'{r.mean_earliness_ws:.3f}'} | "
            f"{'n/a' if r.event_reliability_fbeta is None else f'{r.event_reliability_fbeta:.3f}'} | "
            f"{'n/a' if r.mean_accuracy is None else f'{r.mean_accuracy:.3f}'} | {r.status} |"
        )
    (out / "cross_farm_semantic_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    from rai.ingest.care import CARE_ROOT

    pairs = (("Wind Farm A", "Wind Farm B"), ("Wind Farm A", "Wind Farm C"))
    results = run_all(CARE_ROOT, pairs)
    out_dir = write_artifacts(results)
    for r in results:
        care_str = "n/a" if r.care_score is None else f"{r.care_score:.3f}"
        print(f"{r.model} {r.source_farm}->{r.target_farm}: CARE={care_str} status={r.status} features={r.feature_intersection}")
    print(f"wrote {out_dir}")
