"""Telemetry storage and access: DuckDB over parquet, no server, zero setup.

Every other component reads telemetry through this module. Two rules shape the design:

1. The parquet files may not exist yet (the simulator writes them). A missing store is
   reported as a typed `DataUnavailable`, never as a silently empty frame.
2. Timestamps leave this module tz-aware UTC, always. The DuckDB session is pinned to UTC
   so that any naive timestamp that slips into a parquet file is interpreted as UTC rather
   than as the machine's local time.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from rai import config

log = logging.getLogger(__name__)

TS_COLUMN = "ts"
ASSET_COLUMN = "asset_id"

# Columns that must never be numerically averaged when resampling.
CATEGORICAL_COLUMNS = frozenset({"asset_id", "site", "operating_state", "status_code"})

_AGG_FUNCS = frozenset({"mean", "median", "last", "first", "min", "max", "sum", "std", "count"})

# DuckDB errors that mean "the file is missing, truncated, or being written right now".
_MISSING_DATA_ERRORS = (duckdb.IOException, duckdb.InvalidInputException)


class DataUnavailable(RuntimeError):
    """The requested data store does not exist (yet) or cannot be read.

    The API layer maps this to a 503-style response, so it carries a machine-readable
    `code` alongside the human-readable message.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "data_unavailable",
        path: Path | str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.path = str(path) if path is not None else None

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.path:
            return f"{self.message} (path: {self.path})"
        return self.message


# ---------------------------------------------------------------------------
# Paths — overridable so tests and alternate datasets do not need the real tree
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_conn: duckdb.DuckDBPyConnection | None = None
_data_root: Path = config.SYNTHETIC


def set_data_root(root: Path | str) -> None:
    """Point the store at a different synthetic-data root (used by tests)."""
    global _data_root
    with _lock:
        _data_root = Path(root)
        reset_connection()


def data_root() -> Path:
    return _data_root


def telemetry_dir() -> Path:
    return _data_root / "telemetry"


def asset_parquet_path(asset_id: str) -> Path:
    return telemetry_dir() / f"{asset_id}.parquet"


def events_path() -> Path:
    return _data_root / "events.parquet"


def site_met_path() -> Path:
    return _data_root / "site_met.parquet"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connection() -> duckdb.DuckDBPyConnection:
    """Cached in-memory DuckDB connection, pinned to UTC.

    Reused across calls so repeated fleet queries do not pay connection setup. Guard every
    use with `_lock`: one DuckDB connection is not safe for concurrent statements.
    """
    global _conn
    with _lock:
        if _conn is None:
            conn = duckdb.connect(database=":memory:")
            conn.execute("SET TimeZone='UTC'")
            _conn = conn
        return _conn


def reset_connection() -> None:
    """Drop the cached connection. Call after data files are rewritten."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:  # pragma: no cover - close is best effort
                log.debug("duckdb connection close failed", exc_info=True)
            _conn = None


def _query(sql: str, params: Sequence[object] | None = None) -> pd.DataFrame:
    conn = connection()
    with _lock:
        try:
            return conn.execute(sql, list(params) if params else []).df()
        except _MISSING_DATA_ERRORS as exc:
            raise DataUnavailable(
                f"telemetry store could not be read: {exc}",
                code="data_unavailable",
                path=telemetry_dir(),
            ) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sql_literal(path: Path | str) -> str:
    return "'" + str(Path(path).as_posix()).replace("'", "''") + "'"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _as_utc(value: datetime) -> datetime:
    """Naive datetimes are interpreted as UTC; the project has no other timezone."""
    if value.tzinfo is None:
        log.debug("naive datetime %s interpreted as UTC", value)
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if TS_COLUMN in df.columns:
        ts = pd.to_datetime(df[TS_COLUMN], utc=True)
        df = df.assign(**{TS_COLUMN: ts}).sort_values(TS_COLUMN, kind="stable")
    return df.reset_index(drop=True)


def _telemetry_glob() -> str:
    return (telemetry_dir() / "*.parquet").as_posix()


def _telemetry_files() -> list[Path]:
    directory = telemetry_dir()
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.parquet") if p.is_file())


def _require_asset_file(asset_id: str) -> Path:
    path = asset_parquet_path(asset_id)
    if not path.is_file():
        raise DataUnavailable(
            f"no telemetry parquet for asset {asset_id!r}; run the simulator first",
            code="telemetry_missing",
            path=path,
        )
    return path


def _time_clause(start: datetime | None, end: datetime | None) -> tuple[str, list[object]]:
    """Inclusive on both ends: [start, end]."""
    clauses: list[str] = []
    params: list[object] = []
    if start is not None:
        clauses.append(f"{_quote_ident(TS_COLUMN)} >= ?")
        params.append(_as_utc(start))
    if end is not None:
        clauses.append(f"{_quote_ident(TS_COLUMN)} <= ?")
        params.append(_as_utc(end))
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------


def telemetry_available(asset_id: str | None = None) -> bool:
    """True if there is telemetry to read. Lets callers avoid catching DataUnavailable."""
    if asset_id is None:
        return bool(_telemetry_files())
    return asset_parquet_path(asset_id).is_file()


def list_assets_with_data() -> list[str]:
    """Asset ids that have a telemetry file, ordered as the fleet registry orders them.

    Derived from file names (`{asset_id}.parquet`), so it costs one directory listing and
    does not open any parquet file.
    """
    found = {p.stem for p in _telemetry_files()}
    ordered = [a.asset_id for a in config.FLEET if a.asset_id in found]
    extras = sorted(found - set(ordered))
    return ordered + extras


def available_columns(asset_id: str) -> list[str]:
    """Column names of one asset's telemetry file, in file order."""
    path = _require_asset_file(asset_id)
    conn = connection()
    with _lock:
        try:
            cur = conn.execute(f"SELECT * FROM read_parquet({_sql_literal(path)}) LIMIT 0")
            return [d[0] for d in cur.description or []]
        except _MISSING_DATA_ERRORS as exc:
            raise DataUnavailable(
                f"telemetry for {asset_id!r} could not be read: {exc}",
                code="telemetry_unreadable",
                path=path,
            ) from exc


def load_telemetry(
    asset_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """All telemetry for one asset in [start, end], ordered by ts.

    `columns` selects a subset; `ts` is always included and comes first. An empty result is
    a legitimate answer when the time window simply contains no rows — a *missing file*
    raises `DataUnavailable` instead.
    """
    path = _require_asset_file(asset_id)

    if columns is None:
        select = "*"
    else:
        present = available_columns(asset_id)
        wanted: list[str] = [TS_COLUMN]
        for col in columns:
            if col not in present:
                raise KeyError(
                    f"column {col!r} not present in telemetry for {asset_id!r}; "
                    f"available: {present}"
                )
            if col not in wanted:
                wanted.append(col)
        select = ", ".join(_quote_ident(c) for c in wanted)

    where, params = _time_clause(start, end)
    sql = (
        f"SELECT {select} FROM read_parquet({_sql_literal(path)})"
        f"{where} ORDER BY {_quote_ident(TS_COLUMN)}"
    )
    return _normalize_frame(_query(sql, params))


def load_window(asset_id: str, end: datetime, hours: float) -> pd.DataFrame:
    """Telemetry for the `hours` ending at `end`, inclusive of both endpoints."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    end_utc = _as_utc(end)
    return load_telemetry(asset_id, start=end_utc - timedelta(hours=hours), end=end_utc)


def latest_row(asset_id: str) -> pd.Series | None:
    """Most recent telemetry row, or None if the file exists but holds no rows."""
    path = _require_asset_file(asset_id)
    sql = (
        f"SELECT * FROM read_parquet({_sql_literal(path)}) "
        f"ORDER BY {_quote_ident(TS_COLUMN)} DESC LIMIT 1"
    )
    df = _normalize_frame(_query(sql))
    if df.empty:
        return None
    return df.iloc[0]


def load_fleet_latest() -> pd.DataFrame:
    """One most-recent row per asset, for the fleet view. Single DuckDB query.

    Wind and solar schemas differ, so columns are unioned by name and the absent ones are
    null for the other asset type.
    """
    if not _telemetry_files():
        raise DataUnavailable(
            "no telemetry files found; run the simulator first",
            code="telemetry_missing",
            path=telemetry_dir(),
        )
    sql = f"""
        SELECT * EXCLUDE (_rn) FROM (
            SELECT *, row_number() OVER (
                PARTITION BY {_quote_ident(ASSET_COLUMN)}
                ORDER BY {_quote_ident(TS_COLUMN)} DESC
            ) AS _rn
            FROM read_parquet({_sql_literal(_telemetry_glob())}, union_by_name=true)
        ) WHERE _rn = 1
        ORDER BY {_quote_ident(ASSET_COLUMN)}
    """
    df = _query(sql)
    if TS_COLUMN in df.columns:
        df = df.assign(**{TS_COLUMN: pd.to_datetime(df[TS_COLUMN], utc=True)})
    return df.reset_index(drop=True)


def load_site_met(
    site: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    """Site meteorology rows for one site key (e.g. "kutch-wind") in [start, end].

    An unknown site key yields an empty frame; a missing file raises `DataUnavailable`.
    """
    path = site_met_path()
    if not path.is_file():
        raise DataUnavailable(
            "site meteorology file not found; run the simulator first",
            code="site_met_missing",
            path=path,
        )
    where, params = _time_clause(start, end)
    where = (where + " AND " if where else " WHERE ") + '"site" = ?'
    params = [*params, site]
    sql = (
        f"SELECT * FROM read_parquet({_sql_literal(path)})"
        f"{where} ORDER BY {_quote_ident(TS_COLUMN)}"
    )
    return _normalize_frame(_query(sql, params))


def data_extent() -> tuple[datetime, datetime] | None:
    """(first_ts, last_ts) across all telemetry, or None when there is no data."""
    if not _telemetry_files():
        return None
    sql = (
        f"SELECT min({_quote_ident(TS_COLUMN)}) AS lo, max({_quote_ident(TS_COLUMN)}) AS hi "
        f"FROM read_parquet({_sql_literal(_telemetry_glob())}, union_by_name=true)"
    )
    df = _query(sql)
    if df.empty:
        return None
    lo, hi = df.iloc[0]["lo"], df.iloc[0]["hi"]
    if pd.isna(lo) or pd.isna(hi):
        return None
    lo_ts = pd.Timestamp(lo)
    hi_ts = pd.Timestamp(hi)
    lo_ts = lo_ts.tz_localize("UTC") if lo_ts.tzinfo is None else lo_ts.tz_convert("UTC")
    hi_ts = hi_ts.tz_localize("UTC") if hi_ts.tzinfo is None else hi_ts.tz_convert("UTC")
    return lo_ts.to_pydatetime(), hi_ts.to_pydatetime()


def row_count(asset_id: str) -> int:
    path = _require_asset_file(asset_id)
    df = _query(f"SELECT count(*) AS n FROM read_parquet({_sql_literal(path)})")
    return int(df.iloc[0]["n"])


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def resample(
    df: pd.DataFrame,
    interval_min: int,
    how: str | dict[str, str] = "mean",
) -> pd.DataFrame:
    """Downsample a telemetry frame to a fixed interval, keeping `ts` as a column.

    Numeric columns use `how`; id/categorical columns (`asset_id`, `operating_state`,
    `status_code`, `site`) use "last" because averaging a code is meaningless. Pass a dict
    to override any column. Empty bins are dropped, so gaps stay gaps instead of becoming
    rows of NaN that downstream detectors would read as data.
    """
    if interval_min <= 0:
        raise ValueError("interval_min must be positive")
    if isinstance(how, str) and how not in _AGG_FUNCS:
        raise ValueError(f"unsupported aggregation {how!r}; expected one of {sorted(_AGG_FUNCS)}")

    if TS_COLUMN in df.columns:
        frame = df.copy()
        frame[TS_COLUMN] = pd.to_datetime(frame[TS_COLUMN], utc=True)
        frame = frame.set_index(TS_COLUMN)
    elif isinstance(df.index, pd.DatetimeIndex):
        frame = df.copy()
    else:
        raise ValueError("resample needs a 'ts' column or a DatetimeIndex")

    if frame.empty:
        return df.iloc[0:0].copy()

    frame = frame.sort_index()
    overrides = how if isinstance(how, dict) else {}
    default = "mean" if isinstance(how, dict) else how

    agg: dict[str, str] = {}
    for col in frame.columns:
        if col in overrides:
            agg[col] = overrides[col]
        elif col in CATEGORICAL_COLUMNS or not pd.api.types.is_numeric_dtype(frame[col]):
            agg[col] = "last"
        else:
            agg[col] = default

    rule = f"{int(interval_min)}min"
    resampler = frame.resample(rule, label="left", closed="left")
    out = resampler.agg(agg)
    sizes = resampler.size()
    out = out[sizes.reindex(out.index, fill_value=0) > 0]
    return out.reset_index().rename(columns={"index": TS_COLUMN})


# ---------------------------------------------------------------------------
# Write API — used by the simulator and the ingest adapters
# ---------------------------------------------------------------------------


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> Path:
    """Write via a temp file + replace so readers never see a half-written parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    reset_connection()
    return path


def write_telemetry(asset_id: str, df: pd.DataFrame) -> Path:
    """Persist one asset's telemetry. `ts` is coerced to tz-aware UTC and sorted."""
    if TS_COLUMN not in df.columns:
        raise ValueError(f"telemetry frame for {asset_id!r} has no {TS_COLUMN!r} column")
    out = df.copy()
    out[TS_COLUMN] = pd.to_datetime(out[TS_COLUMN], utc=True)
    if ASSET_COLUMN not in out.columns:
        out[ASSET_COLUMN] = asset_id
    out = out.sort_values(TS_COLUMN, kind="stable").reset_index(drop=True)
    return _atomic_write_parquet(out, asset_parquet_path(asset_id))


def write_site_met(df: pd.DataFrame) -> Path:
    if TS_COLUMN not in df.columns or "site" not in df.columns:
        raise ValueError("site_met frame needs 'ts' and 'site' columns")
    out = df.copy()
    out[TS_COLUMN] = pd.to_datetime(out[TS_COLUMN], utc=True)
    out = out.sort_values(["site", TS_COLUMN], kind="stable").reset_index(drop=True)
    return _atomic_write_parquet(out, site_met_path())
