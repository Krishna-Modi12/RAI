"""Ground-truth event access.

`data/synthetic/events.parquet` records exactly what the simulator injected. It exists so
detection can be scored honestly (recall, lead time) — it is never shown as a model output.

Ground truth is optional at runtime: the dashboard works without it. So `load_events`
returns an empty list and logs a warning when the file is absent, and callers that genuinely
need it (the evaluation pass) pass `required=True` to get a `DataUnavailable` instead.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from rai.schemas import InjectedEvent
from rai.store.telemetry import DataUnavailable, events_path, reset_connection

log = logging.getLogger(__name__)

_TIME_FIELDS = ("onset", "detectable_from", "end")


def events_available() -> bool:
    return events_path().is_file()


def load_events_df(asset_id: str | None = None, *, required: bool = False) -> pd.DataFrame:
    """Raw ground-truth frame, timestamps tz-aware UTC, ordered by onset."""
    path = events_path()
    if not path.is_file():
        if required:
            raise DataUnavailable(
                "ground-truth events file not found; run the simulator first",
                code="events_missing",
                path=path,
            )
        log.warning("ground-truth events file not found at %s", path)
        return pd.DataFrame(columns=list(InjectedEvent.model_fields))

    try:
        df = pd.read_parquet(path)
    except OSError as exc:
        raise DataUnavailable(
            f"ground-truth events file could not be read: {exc}",
            code="events_unreadable",
            path=path,
        ) from exc

    if asset_id is not None and "asset_id" in df.columns:
        df = df[df["asset_id"] == asset_id]
    for field in _TIME_FIELDS:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], utc=True)
    if "onset" in df.columns:
        df = df.sort_values("onset", kind="stable")
    return df.reset_index(drop=True)


def load_events(asset_id: str | None = None, *, required: bool = False) -> list[InjectedEvent]:
    """Ground-truth events, optionally filtered to one asset."""
    df = load_events_df(asset_id, required=required)
    events: list[InjectedEvent] = []
    for position, row in enumerate(df.to_dict(orient="records")):
        payload = {k: (None if _is_null(v) else v) for k, v in row.items()}
        try:
            events.append(InjectedEvent.model_validate(payload))
        except ValidationError as exc:
            raise ValueError(
                f"row {position} of {events_path()} does not match InjectedEvent: {exc}"
            ) from exc
    return events


def events_in_window(
    start: datetime,
    end: datetime,
    asset_id: str | None = None,
) -> list[InjectedEvent]:
    """Events whose active span overlaps [start, end]. An open-ended event has no `end`."""
    lo = pd.Timestamp(start)
    hi = pd.Timestamp(end)
    lo = lo.tz_localize("UTC") if lo.tzinfo is None else lo.tz_convert("UTC")
    hi = hi.tz_localize("UTC") if hi.tzinfo is None else hi.tz_convert("UTC")
    out: list[InjectedEvent] = []
    for event in load_events(asset_id):
        onset = pd.Timestamp(event.onset)
        finish = pd.Timestamp(event.end) if event.end is not None else None
        if onset > hi:
            continue
        if finish is not None and finish < lo:
            continue
        out.append(event)
    return out


def write_events(events: list[InjectedEvent] | pd.DataFrame) -> Path:
    """Persist ground truth. Written via temp + replace so readers never see a partial file."""
    if isinstance(events, pd.DataFrame):
        df = events.copy()
    else:
        df = pd.DataFrame([e.model_dump() for e in events], columns=list(InjectedEvent.model_fields))
    for field in _TIME_FIELDS:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], utc=True)
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    reset_connection()
    return path


def _is_null(value: object) -> bool:
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False
