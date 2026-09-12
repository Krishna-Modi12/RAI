"""Controlled out-of-distribution (OOD) perturbation suite.

CLAUDE.md's numerical-honesty rule and the Gate-2 scientific-validation plan (see
`docs/evaluation/OOD.md`) are explicit: an OOD score may only be reported if a real
perturb-and-rescore experiment actually ran. Earlier iterations of this project reported an
OOD generalization PR-AUC (0.902) that traced to no code at all; that number was withdrawn
in `docs/AUDIT_REPORT.md`. This module is what makes an honest OOD number possible.

Design constraints, both load-bearing:

1. Every perturbation and its severities are declared in `PERTURBATIONS` below, fixed before
   this module was ever run against real results. Nothing here was tuned after looking at an
   output number - that would silently turn a stress test into a demonstration.
2. Perturbations corrupt sensor *observations* only. They never touch the ground-truth event
   list, so scoring afterwards is still measuring "does the detector survive corrupted
   telemetry", not "did we relabel the problem".

Usage: `python -m rai.eval.ood` or `run_ood_suite()` from a script. Each run re-executes
`rai.eval.benchmarks.run_benchmark_suite` once per (perturbation, severity) pair against a
deep copy of the real fleet telemetry, so the unperturbed baseline is recomputed in the same
process rather than trusted from a possibly-stale `artifacts/evaluation/results.json`.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from collections.abc import Callable, Generator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

import numpy as np
import pandas as pd

from rai.config import ARTIFACTS, FLEET
from rai.eval.benchmarks import run_benchmark_suite
from rai.store import load_events, load_telemetry

log = logging.getLogger(__name__)


def _windowed_loader(telemetry: dict[str, pd.DataFrame]) -> Callable[[str, Any, float], pd.DataFrame]:
    """Build a `load_window(asset_id, end, hours)` replacement backed by in-memory frames.

    The champion candidate (`ChallengerHybridEnsemble`) does not read the `frame` argument
    `run_benchmark_suite` hands every candidate - it calls `compute_asset_state`, which reads
    fresh from `rai.store.load_window` internally (see `rai/models/pipeline.py::_load` and
    `rai/models/peers.py::compare`). Left unpatched, every "perturbed" run would silently
    re-score the real, unperturbed store data for the champion only, while the four baseline
    candidates correctly saw the perturbation - producing a false "champion is perfectly
    robust" result. This loader is patched into both modules for the duration of one
    `run_benchmark_suite` call so the champion's entire evidence pipeline (its own signal,
    peer comparison) sees the same perturbed telemetry the baselines do.
    """

    def _load(asset_id: str, end: Any, hours: float) -> pd.DataFrame:
        frame = telemetry.get(asset_id)
        if frame is None or frame.empty:
            from rai.store import load_window as _real

            return _real(asset_id, end=end, hours=hours)
        end_ts = pd.Timestamp(end)
        end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
        start_ts = end_ts - pd.Timedelta(hours=hours)
        mask = (frame["ts"] >= start_ts) & (frame["ts"] <= end_ts)
        return frame.loc[mask].reset_index(drop=True)

    return _load


@contextlib.contextmanager
def _store_serving(telemetry: dict[str, pd.DataFrame]) -> Generator[None]:
    """Make `rai.models.pipeline` and `rai.models.peers` read `telemetry` for this block.

    Also clears the asset-state/evidence-packet cache before and after, since both are keyed
    only by `(asset_id, as_of)` - without this, a second run for the same asset/timestamp
    would silently return the *first* run's cached state regardless of what data was served.
    """
    import rai.models.peers as peers_mod
    import rai.models.pipeline as pipeline_mod

    loader = _windowed_loader(telemetry)
    pipeline_mod.clear_cache()
    with mock.patch.object(pipeline_mod, "load_window", loader), mock.patch.object(peers_mod, "load_window", loader):
        try:
            yield
        finally:
            pipeline_mod.clear_cache()

# Column-name substrings, not exact names, because wind (WT-###) and solar (INV-###) assets
# carry different schemas. A perturbation applies to whichever of its target families exist
# on a given asset's frame.
_TEMPERATURE_COLS = ("temp",)
_VIBRATION_COLS = ("vibration",)
_WEATHER_COLS = ("wind_speed", "wind_direction", "ambient_temp", "pressure_hpa", "humidity", "air_density", "irradiance")

_EXCLUDE_FROM_NOISE = ("ts", "asset_id", "status_code", "operating_state")


def _numeric_cols(frame: pd.DataFrame, substrings: tuple[str, ...] | None = None) -> list[str]:
    cols = [c for c in frame.select_dtypes(include=["float64", "float32"]).columns]
    if substrings is None:
        return [c for c in cols if c not in _EXCLUDE_FROM_NOISE]
    return [c for c in cols if any(s in c for s in substrings)]


@dataclass(frozen=True)
class PerturbationSpec:
    name: str
    category: str  # one of: sensor_noise, missingness, drift, extreme_weather, degradation_magnitude, weather_permutation
    description: str
    severity_label: str
    severity_value: float
    seed: int
    affected_columns_hint: str
    expected_physical_consequence: str
    fn: Callable[[pd.DataFrame, float, int], pd.DataFrame] = field(repr=False)


def _apply_sensor_noise(frame: pd.DataFrame, severity: float, seed: int) -> pd.DataFrame:
    """Add Gaussian noise scaled to `severity` * each column's own std."""
    out = frame.copy()
    rng = np.random.default_rng(seed)
    for col in _numeric_cols(out):
        std = out[col].std(skipna=True)
        if not np.isfinite(std) or std == 0:
            continue
        noise = rng.normal(0.0, severity * std, size=len(out))
        out[col] = out[col].to_numpy() + noise
    return out


def _apply_missingness(frame: pd.DataFrame, severity: float, seed: int) -> pd.DataFrame:
    """Null out a `severity` fraction of cells per numeric column, missing-completely-at-random."""
    out = frame.copy()
    rng = np.random.default_rng(seed)
    for col in _numeric_cols(out):
        mask = rng.random(len(out)) < severity
        out.loc[mask, col] = np.nan
    return out


def _apply_drift(frame: pd.DataFrame, severity: float, _seed: int) -> pd.DataFrame:
    """Ramp an additive offset from 0 to `severity` * std across the frame's time span.

    Simulates a slowly-miscalibrating sensor (the failure mode a fixed-threshold rule is
    least likely to be robust to) on every temperature channel present.
    """
    out = frame.copy()
    n = len(out)
    ramp = np.linspace(0.0, 1.0, n)
    for col in _numeric_cols(out, _TEMPERATURE_COLS):
        std = out[col].std(skipna=True)
        if not np.isfinite(std) or std == 0:
            continue
        out[col] = out[col].to_numpy() + ramp * severity * std
    return out


def _apply_extreme_weather(frame: pd.DataFrame, severity: float, seed: int) -> pd.DataFrame:
    """Force weather-family columns to an extreme percentile for a contiguous block of rows.

    `severity` is the fraction of the frame's length turned extreme (e.g. 0.10 = a contiguous
    10% window). Alternates high/low extremes per column so the perturbation is not a single
    directional shift that a rule could special-case.
    """
    out = frame.copy()
    n = len(out)
    block = max(1, int(n * severity))
    rng = np.random.default_rng(seed)
    start = int(rng.integers(0, max(1, n - block)))
    idx = out.index[start : start + block]
    for i, col in enumerate(_numeric_cols(out, _WEATHER_COLS)):
        q = 0.99 if i % 2 == 0 else 0.01
        extreme_value = out[col].quantile(q)
        out.loc[idx, col] = extreme_value
    return out


def _apply_degradation_magnitude(frame: pd.DataFrame, severity: float, _seed: int) -> pd.DataFrame:
    """Scale temperature/vibration columns by `severity` across the whole frame.

    severity < 1.0 makes any real fault signal weaker (harder to see against baseline
    variance); severity > 1.0 makes it stronger. Applied uniformly rather than only inside
    known event windows, so it also stress-tests the false-alarm rate on healthy periods.
    """
    out = frame.copy()
    for col in _numeric_cols(out, _TEMPERATURE_COLS + _VIBRATION_COLS):
        baseline = out[col].median(skipna=True)
        if not np.isfinite(baseline):
            continue
        out[col] = baseline + (out[col].to_numpy() - baseline) * severity
    return out


def _apply_weather_permutation(frame: pd.DataFrame, severity: float, seed: int) -> pd.DataFrame:
    """Shuffle a `severity` fraction of weather-column rows within the same asset's frame.

    Breaks the true time-correlation between weather and the asset's operating point without
    changing any individual weather reading's marginal distribution - a detector that is
    actually reading environment-vs-power coupling (rather than raw thermal/vibration
    channels) should degrade; one that is not should be roughly unaffected.
    """
    out = frame.copy()
    n = len(out)
    rng = np.random.default_rng(seed)
    k = max(1, int(n * severity))
    rows = rng.choice(n, size=k, replace=False)
    shuffled = rng.permutation(rows)
    for col in _numeric_cols(out, _WEATHER_COLS):
        values = out[col].to_numpy(copy=True)
        values[rows] = values[shuffled]
        out[col] = values
    return out


PERTURBATIONS: tuple[PerturbationSpec, ...] = (
    PerturbationSpec(
        name="sensor_noise_moderate", category="sensor_noise",
        description="Gaussian noise added to every numeric sensor channel, sigma = 0.5x the channel's own std.",
        severity_label="moderate", severity_value=0.5, seed=20260912_01,
        affected_columns_hint="all numeric sensor columns",
        expected_physical_consequence="Residual-based detectors lose some sensitivity; a well-calibrated threshold should not collapse.",
        fn=_apply_sensor_noise,
    ),
    PerturbationSpec(
        name="sensor_noise_severe", category="sensor_noise",
        description="Gaussian noise added to every numeric sensor channel, sigma = 1.5x the channel's own std.",
        severity_label="severe", severity_value=1.5, seed=20260912_02,
        affected_columns_hint="all numeric sensor columns",
        expected_physical_consequence="Signal-to-noise ratio degraded enough that most residual-threshold detectors should show reduced PR-AUC.",
        fn=_apply_sensor_noise,
    ),
    PerturbationSpec(
        name="missingness_moderate", category="missingness",
        description="5% of cells per numeric column set to null (missing completely at random).",
        severity_label="moderate", severity_value=0.05, seed=20260912_03,
        affected_columns_hint="all numeric sensor columns",
        expected_physical_consequence="Small, roughly uniform effect; a detector relying on unbroken windows may show more variance.",
        fn=_apply_missingness,
    ),
    PerturbationSpec(
        name="missingness_severe", category="missingness",
        description="20% of cells per numeric column set to null (missing completely at random).",
        severity_label="severe", severity_value=0.20, seed=20260912_04,
        affected_columns_hint="all numeric sensor columns",
        expected_physical_consequence="Materially degraded input completeness; detectors with no explicit missing-data handling should lose recall or gain false alarms.",
        fn=_apply_missingness,
    ),
    PerturbationSpec(
        name="drift_moderate", category="drift",
        description="Linear additive drift on all temperature channels, ramping 0 -> 1.0x channel std across the series.",
        severity_label="moderate", severity_value=1.0, seed=20260912_05,
        affected_columns_hint="*_temp_c columns",
        expected_physical_consequence="Simulates slow thermocouple miscalibration; a fixed physical-threshold baseline should degrade faster than a peer/residual-relative one.",
        fn=_apply_drift,
    ),
    PerturbationSpec(
        name="drift_severe", category="drift",
        description="Linear additive drift on all temperature channels, ramping 0 -> 3.0x channel std across the series.",
        severity_label="severe", severity_value=3.0, seed=20260912_06,
        affected_columns_hint="*_temp_c columns",
        expected_physical_consequence="Drift comparable to or larger than the fault signal itself; expect a clear drop in specificity (rising false alarms) for threshold-based candidates.",
        fn=_apply_drift,
    ),
    PerturbationSpec(
        name="extreme_weather_moderate", category="extreme_weather",
        description="A contiguous 10% block of the series forced to the 1st/99th percentile of each weather column.",
        severity_label="moderate", severity_value=0.10, seed=20260912_07,
        affected_columns_hint="wind_speed_ms, ambient_temp_c, pressure_hpa, humidity_pct, air_density, irradiance_wm2 (whichever are present)",
        expected_physical_consequence="Tests whether environmental extremes get misread as equipment anomalies (a false-alarm risk), not whether coverage improves.",
        fn=_apply_extreme_weather,
    ),
    PerturbationSpec(
        name="extreme_weather_severe", category="extreme_weather",
        description="A contiguous 30% block of the series forced to the 1st/99th percentile of each weather column.",
        severity_label="severe", severity_value=0.30, seed=20260912_08,
        affected_columns_hint="wind_speed_ms, ambient_temp_c, pressure_hpa, humidity_pct, air_density, irradiance_wm2 (whichever are present)",
        expected_physical_consequence="A third of the series in extreme weather; a detector without environmental gating should show a materially higher false-alarm rate.",
        fn=_apply_extreme_weather,
    ),
    PerturbationSpec(
        name="degradation_weaker", category="degradation_magnitude",
        description="Temperature/vibration channels compressed toward their own median by 0.6x.",
        severity_label="weaker_signal", severity_value=0.6, seed=20260912_09,
        affected_columns_hint="*_temp_c, drivetrain_vibration_mms",
        expected_physical_consequence="A subtler fault signal; coverage/recall should drop for every candidate, champion included.",
        fn=_apply_degradation_magnitude,
    ),
    PerturbationSpec(
        name="degradation_stronger", category="degradation_magnitude",
        description="Temperature/vibration channels expanded away from their own median by 1.6x.",
        severity_label="stronger_signal", severity_value=1.6, seed=20260912_10,
        affected_columns_hint="*_temp_c, drivetrain_vibration_mms",
        expected_physical_consequence="An easier fault signal; coverage/recall should rise or stay flat, a sanity check that the harness responds in the expected direction.",
        fn=_apply_degradation_magnitude,
    ),
    PerturbationSpec(
        name="weather_permutation_partial", category="weather_permutation",
        description="30% of rows have weather-column values shuffled against the asset's own timeline.",
        severity_label="partial", severity_value=0.30, seed=20260912_11,
        affected_columns_hint="wind_speed_ms, ambient_temp_c, pressure_hpa, humidity_pct, air_density, irradiance_wm2 (whichever are present)",
        expected_physical_consequence="Breaks weather-vs-output coupling on a minority of rows; a detector reading thermal/vibration channels directly should be largely unaffected.",
        fn=_apply_weather_permutation,
    ),
    PerturbationSpec(
        name="weather_permutation_full", category="weather_permutation",
        description="100% of rows have weather-column values shuffled against the asset's own timeline.",
        severity_label="full", severity_value=1.0, seed=20260912_12,
        affected_columns_hint="wind_speed_ms, ambient_temp_c, pressure_hpa, humidity_pct, air_density, irradiance_wm2 (whichever are present)",
        expected_physical_consequence="Environmental context is now pure noise relative to asset behaviour; any detector leaning on weather-conditioned expected-power models should show its largest single degradation here.",
        fn=_apply_weather_permutation,
    ),
)


@dataclass(frozen=True)
class OODRunResult:
    perturbation: str
    category: str
    severity_label: str
    severity_value: float
    seed: int
    affected_columns_hint: str
    expected_physical_consequence: str
    model_name: str
    care_score: float
    coverage: float
    accuracy: float
    reliability: float
    earliness: float
    n_events: int
    n_detected: int
    false_alarms_per_year: float
    median_lead_days: float
    pr_auc: float
    mcc: float
    delta_care_vs_baseline: float
    delta_pr_auc_vs_baseline: float


def _load_fleet() -> tuple[list[str], dict[str, pd.DataFrame], list[dict[str, Any]], float]:
    injected_events = load_events()
    events = [
        {
            "event_id": e.event_id,
            "asset_id": e.asset_id,
            "scenario": e.scenario,
            "component": e.component,
            "is_equipment_fault": e.is_equipment_fault,
            "onset": e.onset,
            "failure": e.end if e.end is not None else e.onset + pd.Timedelta(days=14),
        }
        for e in injected_events
        if e.is_equipment_fault
    ]
    asset_ids = [a.asset_id for a in FLEET]
    telemetry = {aid: load_telemetry(aid) for aid in asset_ids}
    total_hours = sum(len(df) * (10.0 if "WT" in aid else 15.0) / 60.0 for aid, df in telemetry.items())
    return asset_ids, telemetry, events, total_hours


def _classification_metrics(scored_assets: list[tuple[str, int, float]]) -> dict[str, float]:
    from rai.eval.metrics import compute_classification_battery

    y_true = [s[1] for s in scored_assets]
    y_prob = [s[2] for s in scored_assets]
    return compute_classification_battery(y_true=y_true, y_prob=y_prob, threshold=0.50)


def run_ood_suite(model_filter: tuple[str, ...] = ("challenger_hybrid_ensemble", "baseline_4_isolation_forest")) -> dict[str, Any]:
    """Run the full perturbation registry once, plus one unperturbed baseline.

    Returns a JSON-serialisable dict with the baseline run, every perturbed run, and deltas.
    `model_filter` restricts which of the five benchmark candidates get perturbation results
    (all five still run inside `run_benchmark_suite`, since it does not support subsetting;
    this only controls what is reported, to keep the artifact focused on the champion and its
    strongest baseline rather than five candidates x twelve perturbations of noise).
    """
    started = time.perf_counter()
    asset_ids, telemetry, events, total_hours = _load_fleet()

    with _store_serving(telemetry):
        baseline_results = run_benchmark_suite(asset_ids, telemetry, events, total_hours)
    baseline_by_model = {b.model_name: b for b in baseline_results}
    baseline_cls = {name: _classification_metrics(b.scored_assets) for name, b in baseline_by_model.items()}

    baseline_report = [
        {
            "model_name": b.model_name,
            "care_score": b.care.care_score,
            "coverage": b.care.coverage,
            "accuracy": b.care.accuracy,
            "reliability": b.care.reliability,
            "earliness": b.care.earliness,
            "n_events": b.care.n_events,
            "n_detected": b.care.n_detected,
            "false_alarms_per_year": b.care.false_alarms_per_year,
            "median_lead_days": b.care.median_lead_days,
            "pr_auc": baseline_cls[b.model_name]["pr_auc"],
            "mcc": baseline_cls[b.model_name]["mcc"],
        }
        for b in baseline_results
        if b.model_name in model_filter
    ]

    runs: list[OODRunResult] = []
    for spec in PERTURBATIONS:
        perturbed_telemetry = {aid: spec.fn(df, spec.severity_value, spec.seed + i) for i, (aid, df) in enumerate(telemetry.items())}
        with _store_serving(perturbed_telemetry):
            results = run_benchmark_suite(asset_ids, perturbed_telemetry, events, total_hours)
        for b in results:
            if b.model_name not in model_filter:
                continue
            cls = _classification_metrics(b.scored_assets)
            base = baseline_by_model[b.model_name]
            base_cls = baseline_cls[b.model_name]
            runs.append(
                OODRunResult(
                    perturbation=spec.name,
                    category=spec.category,
                    severity_label=spec.severity_label,
                    severity_value=spec.severity_value,
                    seed=spec.seed,
                    affected_columns_hint=spec.affected_columns_hint,
                    expected_physical_consequence=spec.expected_physical_consequence,
                    model_name=b.model_name,
                    care_score=b.care.care_score,
                    coverage=b.care.coverage,
                    accuracy=b.care.accuracy,
                    reliability=b.care.reliability,
                    earliness=b.care.earliness,
                    n_events=b.care.n_events,
                    n_detected=b.care.n_detected,
                    false_alarms_per_year=b.care.false_alarms_per_year,
                    median_lead_days=b.care.median_lead_days,
                    pr_auc=cls["pr_auc"],
                    mcc=cls["mcc"],
                    delta_care_vs_baseline=b.care.care_score - base.care.care_score,
                    delta_pr_auc_vs_baseline=cls["pr_auc"] - base_cls["pr_auc"],
                )
            )
        log.info("OOD perturbation %s complete", spec.name)

    elapsed_s = time.perf_counter() - started
    return {
        "methodology": (
            "Every perturbation is applied to real synthetic-fleet telemetry (never to labels), "
            "with severities and seeds fixed in rai/eval/ood.py before this run. The baseline is "
            "recomputed in this same process run (not read from a possibly-concurrent "
            "artifacts/evaluation/results.json) so deltas are internally consistent."
        ),
        "n_assets": len(asset_ids),
        "n_events": len(events),
        "n_perturbations": len(PERTURBATIONS),
        "elapsed_seconds": round(elapsed_s, 1),
        "baseline": baseline_report,
        "runs": [asdict(r) for r in runs],
    }


def write_ood_artifacts(out_dir: Path | None = None) -> Path:
    out = out_dir or (ARTIFACTS / "evaluation" / "gate2" / "ood")
    out.mkdir(parents=True, exist_ok=True)
    report = run_ood_suite()
    (out / "results.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    lines = ["# OOD Perturbation Suite — Results", "", report["methodology"], "", f"Assets: {report['n_assets']}, events: {report['n_events']}, perturbations: {report['n_perturbations']}, elapsed: {report['elapsed_seconds']}s", ""]
    lines.append("## Baseline (unperturbed)")
    lines.append("")
    lines.append("| model | CARE | PR-AUC | MCC | FA/yr | median lead (d) |")
    lines.append("|---|---|---|---|---|---|")
    for b in report["baseline"]:
        lines.append(f"| {b['model_name']} | {b['care_score']:.3f} | {b['pr_auc']:.3f} | {b['mcc']:.3f} | {b['false_alarms_per_year']:.2f} | {b['median_lead_days']:.1f} |")
    lines.append("")
    lines.append("## Perturbed runs")
    lines.append("")
    lines.append("| perturbation | severity | model | CARE | ΔCARE | PR-AUC | ΔPR-AUC | FA/yr | median lead (d) |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in report["runs"]:
        lines.append(
            f"| {r['perturbation']} | {r['severity_label']} | {r['model_name']} | "
            f"{r['care_score']:.3f} | {r['delta_care_vs_baseline']:+.3f} | {r['pr_auc']:.3f} | "
            f"{r['delta_pr_auc_vs_baseline']:+.3f} | {r['false_alarms_per_year']:.2f} | {r['median_lead_days']:.1f} |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("OOD artifacts written to %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_ood_artifacts()
