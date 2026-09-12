"""Computed-state cache: AssetState and JSON artifacts on disk under `artifacts/`.

The pipeline computes an `AssetState` per asset; the API and UI read it back without
recomputing. Every write goes through a temp file + atomic replace, because the API process
reads these files while the pipeline process rewrites them.
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from rai import config
from rai.schemas import AssetState
from rai.store.telemetry import DataUnavailable

log = logging.getLogger(__name__)

STATE_DIRNAME = "state"

_artifact_root: Path = config.ARTIFACTS


def set_artifact_root(root: Path | str) -> None:
    """Point the state cache at a different artifacts root (used by tests)."""
    global _artifact_root
    _artifact_root = Path(root)


def artifact_root() -> Path:
    return _artifact_root


def state_dir() -> Path:
    return _artifact_root / STATE_DIRNAME


# ---------------------------------------------------------------------------
# JSON encoding
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat().replace("+00:00", "Z")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    # numpy scalars and anything else exposing .item()
    item = getattr(obj, "item", None)
    if callable(item):
        value = item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    raise TypeError(f"object of type {type(obj).__name__} is not JSON serialisable")


def _atomic_write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
# AssetState cache
# ---------------------------------------------------------------------------


def asset_state_path(asset_id: str) -> Path:
    return state_dir() / f"{_safe_name(asset_id)}.json"


def save_asset_state(state: AssetState) -> Path:
    return _atomic_write_text(
        asset_state_path(state.asset_id),
        state.model_dump_json(indent=2),
    )


def load_asset_state(asset_id: str) -> AssetState | None:
    """Cached state for one asset, or None when it has not been computed yet."""
    path = asset_state_path(asset_id)
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    try:
        return AssetState.model_validate_json(raw)
    except ValidationError as exc:
        raise DataUnavailable(
            f"cached state for {asset_id!r} does not match AssetState; recompute it",
            code="state_invalid",
            path=path,
        ) from exc
    except ValueError as exc:  # malformed JSON
        raise DataUnavailable(
            f"cached state for {asset_id!r} is not valid JSON; recompute it",
            code="state_corrupt",
            path=path,
        ) from exc


def load_all_asset_states() -> list[AssetState]:
    """Every cached state, fleet-registry order. Unreadable files are skipped and logged."""
    directory = state_dir()
    if not directory.is_dir():
        return []
    by_id: dict[str, AssetState] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            by_id[path.stem] = AssetState.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, ValueError) as exc:
            log.warning("skipping unreadable asset state %s: %s", path, exc)
    ordered = [by_id[a.asset_id] for a in config.FLEET if a.asset_id in by_id]
    extras = [by_id[k] for k in sorted(set(by_id) - {a.asset_id for a in config.FLEET})]
    return ordered + extras


def list_cached_states() -> list[str]:
    directory = state_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def clear_asset_states() -> int:
    """Delete every cached state. Returns how many files were removed."""
    directory = state_dir()
    if not directory.is_dir():
        return 0
    removed = 0
    for path in directory.glob("*.json"):
        path.unlink()
        removed += 1
    return removed


# ---------------------------------------------------------------------------
# Generic JSON artifacts (evaluation reports, model metadata, indexes)
# ---------------------------------------------------------------------------


def artifact_path(name: str) -> Path:
    """Resolve an artifact name to a path under `artifacts/`. Rejects escapes from the root."""
    cleaned = name.strip().replace("\\", "/").lstrip("/")
    if not cleaned:
        raise ValueError("artifact name must not be empty")
    parts = [p for p in cleaned.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"artifact name {name!r} must stay inside the artifacts root")
    parts = [_safe_name(p) for p in parts]
    if not parts[-1].endswith(".json"):
        parts[-1] = parts[-1] + ".json"
    return _artifact_root.joinpath(*parts)


def save_json_artifact(name: str, obj: object) -> Path:
    """Write any JSON-serialisable object (dict, list, pydantic model) to `artifacts/`."""
    payload = obj.model_dump(mode="json") if isinstance(obj, BaseModel) else obj
    text = json.dumps(payload, indent=2, default=_json_default, allow_nan=False)
    return _atomic_write_text(artifact_path(name), text)


def load_json_artifact(name: str) -> dict | None:
    """Read a JSON artifact, or None when it has not been produced yet."""
    path = artifact_path(name)
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataUnavailable(
            f"artifact {name!r} is not valid JSON; regenerate it",
            code="artifact_corrupt",
            path=path,
        ) from exc
    if not isinstance(loaded, dict):
        raise TypeError(f"artifact {name!r} holds a {type(loaded).__name__}, not a JSON object")
    return loaded


def _safe_name(value: str) -> str:
    """Keep file names to characters that are legal on Windows and POSIX."""
    keep = {"-", "_", ".", "+"}
    cleaned = "".join(c if (c.isalnum() or c in keep) else "_" for c in value.strip())
    if not cleaned or set(cleaned) <= {"."}:
        raise ValueError(f"cannot derive a file name from {value!r}")
    return cleaned
