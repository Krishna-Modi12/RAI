"""Frozen baseline metadata generator for Phase 3A-1.

Produces immutable baseline metadata tracking environment provenance,
dataset hashes, configuration hashes, feature schema hashes, and locked decision parameters.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import sklearn

log = logging.getLogger(__name__)


def _compute_file_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _get_git_sha() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_OR_UNTRACKED"


@dataclass
class BaselineMetadata:
    git_sha: str
    python_version: str
    sklearn_version: str
    platform: str
    production_decision_threshold: float
    calibration_method: str
    random_seed: int
    embargo_hours_enforced: float
    embargo_formula: str
    dataset_hashes: dict[str, str]
    configuration_hashes: dict[str, str]
    feature_schema_hashes: dict[str, str]
    model_artifact_hashes: dict[str, str]
    evaluation_command: str
    timestamp_utc: str


def record_frozen_baseline_metadata(output_dir: Path | str) -> dict[str, Any]:
    """Capture and write immutable baseline metadata for Gate 3A-1."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parents[2]

    dataset_files = {
        "events": root / "data" / "events.json",
        "wt017_telemetry": root / "data" / "telemetry" / "WT-017.parquet",
        "inv023_telemetry": root / "data" / "telemetry" / "INV-023.parquet",
    }
    dataset_hashes = {k: _compute_file_sha256(p) for k, p in dataset_files.items()}

    config_files = {
        "rai_config": root / "rai" / "config.py",
        "rai_schemas": root / "rai" / "schemas.py",
    }
    config_hashes = {k: _compute_file_sha256(p) for k, p in config_files.items()}

    schema_files = {
        "feature_build": root / "rai" / "features" / "build.py",
        "pipeline": root / "rai" / "models" / "pipeline.py",
    }
    schema_hashes = {k: _compute_file_sha256(p) for k, p in schema_files.items()}

    model_files = {
        "gate2_scorecard": root / "artifacts" / "evaluation" / "gate2" / "scorecard.json",
        "gate2_rolling": root / "artifacts" / "evaluation" / "gate2" / "rolling_origin.json",
    }
    model_hashes = {k: _compute_file_sha256(p) for k, p in model_files.items()}

    import pandas as pd

    meta = BaselineMetadata(
        git_sha=_get_git_sha(),
        python_version=platform.python_version(),
        sklearn_version=sklearn.__version__,
        platform=platform.platform(),
        production_decision_threshold=0.45,
        calibration_method="platt_scaling_and_isotonic_audit",
        random_seed=42,
        embargo_hours_enforced=342.0,
        embargo_formula="336.0h (14d lookback) + 6.0h (thermal inertia lag) = 342.0h",
        dataset_hashes=dataset_hashes,
        configuration_hashes=config_hashes,
        feature_schema_hashes=schema_hashes,
        model_artifact_hashes=model_hashes,
        evaluation_command="python scripts/evaluate_phase3a1.py",
        timestamp_utc=pd.Timestamp.now(tz="UTC").isoformat(),
    )

    out_file = out_dir / "metadata.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(asdict(meta), f, indent=2)

    log.info("Recorded frozen baseline metadata at %s (git=%s)", out_file, meta.git_sha[:8])
    return asdict(meta)
