"""Kelmarsh event/behaviour benchmark.

This is deliberately not a failure classifier. Kelmarsh status rows are operational
records. The benchmark measures anomaly association around two explicitly named
operational classes and keeps environmental, electrical, standby, and unknown records
out of the event score.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from rai.eval.external.care.champion import fit_rai_champion

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / "data" / "raw" / "kelmarsh" / "Kelmarsh_SCADA_2019_3085.zip"
DATA_DIR = ROOT / "data" / "raw" / "kelmarsh" / "2019"
OUT_DIR = ROOT / "artifacts" / "evaluation" / "kelmarsh_event_behaviour"

SCADA_COLUMNS = {
    "timestamp": "# Date and time",
    "wind_speed_ms": "Wind speed (m/s)",
    "power_kw": "Power (kW)",
    "rotor_rpm": "Rotor speed (RPM)",
}
EVALUATED_CATEGORIES = ("Forced outage", "Scheduled Maintenance")
EXCLUDED_CATEGORIES = (
    "Out of Environmental Specification",
    "Out of Electrical Specification",
    "Technical Standby",
)
EVENT_RADIUS = pd.Timedelta(hours=6)
TRAIN_FRACTION = 0.60


@dataclass(frozen=True)
class Event:
    turbine_id: str
    category: str
    start: pd.Timestamp
    end: pd.Timestamp | None
    code: str
    message: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_scada(path: Path, turbine_id: str) -> pd.DataFrame:
    frame = pd.read_csv(path, skiprows=9, usecols=list(SCADA_COLUMNS.values()))
    frame = frame.rename(columns={v: k for k, v in SCADA_COLUMNS.items()})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    for column in ("wind_speed_ms", "power_kw", "rotor_rpm"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["turbine_id"] = turbine_id
    return frame.sort_values("timestamp").dropna(subset=["timestamp"]).reset_index(drop=True)


def _read_events(path: Path, turbine_id: str) -> pd.DataFrame:
    frame = pd.read_csv(path, skiprows=9)
    frame["start"] = pd.to_datetime(frame["Timestamp start"], utc=True, errors="coerce")
    frame["end"] = pd.to_datetime(frame["Timestamp end"], utc=True, errors="coerce")
    frame["category"] = frame["IEC category"].astype("string")
    frame["turbine_id"] = turbine_id
    return frame.dropna(subset=["start"]).sort_values("start")


def _discover() -> list[tuple[Path, Path, str]]:
    pairs = []
    for scada in sorted(DATA_DIR.glob("Turbine_Data*.csv")):
        turbine = scada.name.split("_")[3]
        status = next(DATA_DIR.glob(f"Status_Kelmarsh_{turbine}_*.csv"))
        pairs.append((scada, status, f"Kelmarsh-{turbine}"))
    if len(pairs) != 6:
        raise RuntimeError(f"Expected six Kelmarsh turbine pairs, found {len(pairs)}")
    return pairs


def _events(frame: pd.DataFrame) -> list[Event]:
    result: list[Event] = []
    for row in frame.loc[frame["category"].isin(EVALUATED_CATEGORIES)].itertuples():
        result.append(
            Event(
                turbine_id=str(row.turbine_id),
                category=str(row.category),
                start=row.start,
                end=None if pd.isna(row.end) else row.end,
                code=str(row.Code),
                message=str(row.Message),
            )
        )
    return result


def _fit_baselines(train: pd.DataFrame) -> dict[str, Any]:
    columns = ["wind_speed_ms", "power_kw", "rotor_rpm"]
    medians = {column: float(train[column].median()) for column in columns}
    matrix = train[columns].fillna(medians).to_numpy(dtype=float)
    forest = IsolationForest(
        n_estimators=100, contamination=0.01, random_state=20260913
    ).fit(matrix)
    means = train[columns].mean()
    stds = train[columns].std().replace(0, 1.0).fillna(1.0)
    return {"columns": columns, "medians": medians, "forest": forest, "means": means, "stds": stds}


def _predict(frame: pd.DataFrame, fitted: dict[str, Any], rai: Any) -> dict[str, np.ndarray]:
    columns = fitted["columns"]
    matrix = frame[columns].fillna(fitted["medians"]).to_numpy(dtype=float)
    iso = (fitted["forest"].predict(matrix) == -1).astype(int)
    z = np.max(
        np.abs(
            (frame[columns].to_numpy(dtype=float) - fitted["means"].to_numpy())
            / fitted["stds"].to_numpy()
        ),
        axis=1,
    )
    z_flags = (np.nan_to_num(z, nan=0.0) >= 3.0).astype(int)
    rai_flags = rai.predict(frame)
    return {"statistical_z": z_flags, "isolation_forest": iso, "rai_champion": rai_flags}


def _window_stats(predictions: dict[str, np.ndarray], timestamps: pd.Series, event: Event) -> dict[str, Any]:
    pre = (timestamps >= event.start - EVENT_RADIUS) & (timestamps < event.start)
    event_end = event.end if event.end is not None else event.start + pd.Timedelta(minutes=10)
    during = (timestamps >= event.start) & (timestamps < event_end)
    post_start = event_end
    post = (timestamps > post_start) & (timestamps <= post_start + EVENT_RADIUS)
    result: dict[str, Any] = {"pre_rows": int(pre.sum()), "event_rows": int(during.sum()), "post_rows": int(post.sum())}
    for name, flags in predictions.items():
        result[f"{name}_pre_rate"] = float(flags[pre].mean()) if pre.any() else None
        result[f"{name}_event_rate"] = float(flags[during].mean()) if during.any() else None
        result[f"{name}_post_rate"] = float(flags[post].mean()) if post.any() else None
        result[f"{name}_event_detected"] = bool(flags[during].any()) if during.any() else False
    return result


def run() -> dict[str, Any]:
    if not ARCHIVE.is_file() or _sha256(ARCHIVE) != "c2f11578b9a1678be198fd7883a7dfe1b923c5b0565f806bdda5dd9d0097f4dc":
        raise RuntimeError("Pinned Kelmarsh archive missing or checksum mismatch")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_events: list[Event] = []
    window_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for scada_path, status_path, turbine_id in _discover():
        scada = _read_scada(scada_path, turbine_id)
        split = int(len(scada) * TRAIN_FRACTION)
        train, test = scada.iloc[:split].copy(), scada.iloc[split:].copy()
        fitted = _fit_baselines(train)
        rai = fit_rai_champion(train, turbine_id, feature_policy="kelmarsh_common")
        predictions = _predict(test, fitted, rai)
        events = _events(_read_events(status_path, turbine_id))
        all_events.extend(events)
        for event in events:
            if event.start < test["timestamp"].min() or event.start > test["timestamp"].max():
                continue
            stats = _window_stats(predictions, test["timestamp"], event)
            window_rows.append({"turbine_id": turbine_id, "category": event.category, "start": event.start.isoformat(), "code": event.code, "message": event.message, **stats})
        event_mask = np.zeros(len(test), dtype=bool)
        for event in events:
            if test["timestamp"].min() <= event.start <= test["timestamp"].max():
                event_mask |= ((test["timestamp"] >= event.start - EVENT_RADIUS) & (test["timestamp"] <= event.start + EVENT_RADIUS)).to_numpy()
        clean = ~event_mask
        for name, flags in predictions.items():
            result_rows.append({"turbine_id": turbine_id, "model": name, "test_rows": len(test), "evaluated_events": sum(e.start >= test["timestamp"].min() for e in events), "event_coverage": float(np.mean([row[f"{name}_event_detected"] for row in window_rows if row["turbine_id"] == turbine_id])) if any(row["turbine_id"] == turbine_id for row in window_rows) else None, "false_alarm_rate_outside_event_windows": float(flags[clean].mean()) if clean.any() else None})
        audit_rows.append({"turbine_id": turbine_id, "rows": len(scada), "train_rows": len(train), "test_rows": len(test), "signals": list(SCADA_COLUMNS), "sampling_minutes": float(scada["timestamp"].diff().dt.total_seconds().div(60).median()), "missingness": {c: float(scada[c].isna().mean()) for c in SCADA_COLUMNS if c != "timestamp"}, "split": "chronological 60/40", "future_statistics_used": False, "event_labels_used_as_features": False, "turbine_identity_used_as_feature": False})

    excluded_counts: dict[str, int] = {}
    for _, status_path, turbine_id in _discover():
        counts = _read_events(status_path, turbine_id)["category"].value_counts().to_dict()
        for category, count in counts.items():
            excluded_counts[category] = excluded_counts.get(category, 0) + int(count)
    manifest = {"experiment_id": "RAI-WIND-002", "status": "PARTIAL", "claim_level": "EXTERNAL_REAL + MODEL_COMPARISON + HISTORICAL_AUDIT", "dataset": {"zenodo_record": "5841834", "archive": ARCHIVE.name, "sha256": _sha256(ARCHIVE), "turbines": 6, "year": 2019}, "event_policy": {"evaluated": list(EVALUATED_CATEGORIES), "excluded": list(EXCLUDED_CATEGORIES), "not_failure_labels": True}, "feature_policy": {"signals": list(SCADA_COLUMNS), "transformations": "numeric coercion only; no future rolling features", "units": {"wind_speed_ms": "m/s", "power_kw": "kW", "rotor_rpm": "RPM"}}, "leakage_controls": audit_rows, "event_category_counts_all_turbines": excluded_counts, "models": ["statistical_z", "isolation_forest", "rai_champion"], "window": "6h pre / documented event / 6h post", "limitation": "Operational event association only; no causal or failure-prediction claim."}
    (OUT_DIR / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(window_rows).to_csv(OUT_DIR / "event_windows.csv", index=False)
    pd.DataFrame(result_rows).to_csv(OUT_DIR / "model_results.csv", index=False)
    pd.DataFrame(audit_rows).to_json(OUT_DIR / "leakage_feature_audit.json", indent=2)
    summary = {"experiment_id": "RAI-WIND-002", "status": "PARTIAL", "events_total_evaluated_window_candidates": len(window_rows), "events_by_category": pd.Series([e.category for e in all_events]).value_counts().to_dict(), "models": result_rows, "claim": "RAI anomaly scores were associated with documented operational event windows; this is not failure validation or prediction.", "limitations": [manifest["limitation"]]}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
