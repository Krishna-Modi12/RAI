"""Cross-farm transfer: fit on one CARE farm, score on another, never refit (Gate D).

Farm A, B and C are anonymised independently (`docs/evaluation/EXTERNAL_CARE.md` §3), so
they do not share column names. `rai.ingest.care.resolve_columns` is what makes a common
feature layer possible at all: run against a raw header from each farm (verified directly,
not assumed), exactly three of the module's 15 canonical wind signals resolve on *every*
farm - `power_kw`, `wind_speed_ms`, and the non-feature `status_code` used only for the
paper's own normal/abnormal status split:

    Farm A: power_kw <- power_29_avg,  wind_speed_ms <- wind_speed_3_avg
    Farm B: power_kw <- power_58_avg,  wind_speed_ms <- wind_speed_59_avg
    Farm C: power_kw <- power_17_avg,  wind_speed_ms <- wind_speed_235_avg

So the honest common feature layer this benchmark's own sensor anonymisation supports is
`{power_kw, wind_speed_ms}` - not the wind_speed/active_power/rotor_speed triple sometimes
quoted for other cross-farm wind benchmarks (rotor_rpm does not resolve on any of the three
CARE farms from the source headers alone). This module fits a baseline on ALL of a source
farm's pooled TRAIN rows (using only those two intersected feature columns - see
`_intersected_columns`), then scores it - unmodified, never refit or adapted - against every
dataset in a target farm, exactly the same CARE metrics as `farm_a_runner.py`. Target labels
are used only to score the transferred model, never to adapt it: this is transfer
evaluation, not supervised target adaptation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from rai.eval.external.care.adapter import (
    FEATURE_COLUMNS,
    fit_isolation_forest,
    fit_zscore_threshold,
)
from rai.eval.external.care.cross_turbine import _score_with_baseline
from rai.eval.external.care.farm_a_runner import MODEL_NAMES, DatasetScore, ModelName, _load_dataset
from rai.eval.external.care.metrics import (
    CareDatasetLabel,
    DatasetReliabilityInput,
    care_score,
    event_reliability_fbeta,
)
from rai.ingest.care import load_event_info

_MIN_TRAIN_OBSERVATIONS = 10


def _intersected_columns(*frames: pd.DataFrame) -> list[str]:
    """Feature columns with enough non-null observations in EVERY given frame.

    This is the "feature intersection" the source and target farm actually share, computed
    from data rather than assumed from a signal name list - see the module docstring.
    """
    return [
        c
        for c in FEATURE_COLUMNS
        if all(c in f.columns and f[c].notna().sum() >= _MIN_TRAIN_OBSERVATIONS for f in frames)
    ]


def _fit_on_columns(model_name: ModelName, train_frame: pd.DataFrame, columns: list[str]):
    restricted = train_frame[columns] if columns else train_frame
    if model_name == "isolation_forest":
        return fit_isolation_forest(restricted)
    return fit_zscore_threshold(restricted)


@dataclass(frozen=True)
class CrossFarmResult:
    source_farm: str
    target_farm: str
    model: ModelName
    feature_intersection: tuple[str, ...]
    n_target_datasets: int
    n_target_anomaly_datasets: int
    n_target_normal_datasets: int
    mean_coverage_fbeta: float | None
    mean_earliness_ws: float | None
    event_reliability_fbeta: float | None
    mean_accuracy: float | None
    care_score: float | None
    status: str
    datasets: list[DatasetScore]


def _load_farm(farm_dir: Path) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    events = load_event_info(farm_dir / "event_info.csv")
    frames = {int(row["event_id"]): _load_dataset(farm_dir, int(row["event_id"])) for _, row in events.iterrows()}
    return events, frames  # type: ignore[return-value]


def run_transfer(
    source_dir: Path, target_dir: Path, model_name: ModelName
) -> CrossFarmResult:
    source_events, source_frames = _load_farm(source_dir)
    target_events, target_frames = _load_farm(target_dir)

    source_train = pd.concat(
        [f.loc[f["care_train_test"] == "train"] for f in source_frames.values()], ignore_index=True
    )
    # Any one target frame has the same resolved-column set as any other in the same farm
    # (one resolver run per farm, not per dataset) - probing the first is representative.
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
            results.append(run_transfer(root / source, root / target, model_name))
    return results


def write_artifacts(results: list[CrossFarmResult], out_dir: Path | None = None) -> Path:
    out = Path(out_dir) if out_dir is not None else Path("artifacts/evaluation/gate2/external_care")
    out.mkdir(parents=True, exist_ok=True)
    payload = [asdict(r) for r in results]
    (out / "cross_farm_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Cross-farm transfer (fit on source, score on target, never refit)", ""]
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
    (out / "cross_farm_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    from rai.ingest.care import CARE_ROOT

    pairs = (("Wind Farm A", "Wind Farm B"), ("Wind Farm A", "Wind Farm C"))
    results = run_all(CARE_ROOT, pairs)
    out_dir = write_artifacts(results)
    for r in results:
        care_str = "n/a" if r.care_score is None else f"{r.care_score:.3f}"
        print(f"{r.model} {r.source_farm}->{r.target_farm}: CARE={care_str} status={r.status}")
    print(f"wrote {out_dir}")
