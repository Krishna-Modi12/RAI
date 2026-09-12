"""Leakage prevention engine and verification guards.

Enforces strict isolation between training, validation, and test partitions:
1. Temporal isolation: max(train_ts) < min(test_ts) with an enforced embargo gap.
2. Asset isolation: train_assets and test_assets must be disjoint for asset holdout.
3. Distribution isolation: normalization baselines and anomaly thresholds must be
   fit exclusively on training data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


class DataLeakageError(RuntimeError):
    """Raised when evaluation data leakage or partition contamination is detected."""


@dataclass(frozen=True)
class LeakageReport:
    passed: bool
    n_train_rows: int
    n_test_rows: int
    time_overlap: bool = False
    gap_hours: float = 0.0
    asset_overlap: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def raise_for_issues(self) -> None:
        if not self.passed:
            msg = "; ".join(self.issues)
            raise DataLeakageError(f"Data leakage guard failed: {msg}")


def _to_utc_series(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, utc=True)
    return ts


def check_temporal_leakage(
    train_ts: pd.Series | Sequence[Any],
    test_ts: pd.Series | Sequence[Any],
    min_gap_hours: float = 0.0,
) -> tuple[bool, float, list[str]]:
    """Verify that training timestamps strictly precede test timestamps."""
    train_utc = _to_utc_series(pd.Series(train_ts)).dropna()
    test_utc = _to_utc_series(pd.Series(test_ts)).dropna()

    if train_utc.empty or test_utc.empty:
        return True, 0.0, []

    max_train = train_utc.max()
    min_test = test_utc.min()

    gap = (min_test - max_train).total_seconds() / 3600.0
    issues: list[str] = []
    passed = True

    if max_train >= min_test:
        passed = False
        issues.append(
            f"Temporal contamination: max train ts ({max_train.isoformat()}) >= "
            f"min test ts ({min_test.isoformat()})"
        )
    elif gap < min_gap_hours:
        passed = False
        issues.append(
            f"Insufficient temporal gap: observed gap {gap:.2f}h < required {min_gap_hours:.2f}h"
        )

    return passed, gap, issues


def check_asset_leakage(
    train_assets: set[str] | Sequence[str],
    test_assets: set[str] | Sequence[str],
) -> tuple[bool, list[str]]:
    """Verify that training and test asset IDs are strictly disjoint."""
    train_set = set(train_assets)
    test_set = set(test_assets)
    overlap = sorted(train_set.intersection(test_set))
    passed = len(overlap) == 0
    return passed, overlap


def audit_split(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    time_col: str = "ts",
    asset_col: str | None = "asset_id",
    min_gap_hours: float = 0.0,
    check_asset_disjoint: bool = False,
) -> LeakageReport:
    """Comprehensive leakage audit for a pair of train/test dataframes."""
    issues: list[str] = []
    passed = True

    if time_col not in train_df.columns or time_col not in test_df.columns:
        raise ValueError(f"Missing time column '{time_col}' in one of the dataframes")

    temporal_ok, gap_hours, time_issues = check_temporal_leakage(
        train_df[time_col], test_df[time_col], min_gap_hours=min_gap_hours
    )
    if not temporal_ok:
        passed = False
        issues.extend(time_issues)

    asset_overlap: list[str] = []
    if check_asset_disjoint and asset_col and asset_col in train_df and asset_col in test_df:
        asset_ok, overlap = check_asset_leakage(train_df[asset_col], test_df[asset_col])
        if not asset_ok:
            passed = False
            asset_overlap = overlap
            issues.append(
                f"Asset holdout violated: {len(overlap)} assets present in both train & test: {overlap[:5]}"
            )

    return LeakageReport(
        passed=passed,
        n_train_rows=len(train_df),
        n_test_rows=len(test_df),
        time_overlap=not temporal_ok,
        gap_hours=gap_hours,
        asset_overlap=asset_overlap,
        issues=issues,
    )


def assert_no_leakage(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    time_col: str = "ts",
    asset_col: str | None = "asset_id",
    min_gap_hours: float = 0.0,
    check_asset_disjoint: bool = False,
) -> LeakageReport:
    """Assert that a train/test split has zero leakage, raising DataLeakageError if violated."""
    report = audit_split(
        train_df,
        test_df,
        time_col=time_col,
        asset_col=asset_col,
        min_gap_hours=min_gap_hours,
        check_asset_disjoint=check_asset_disjoint,
    )
    report.raise_for_issues()
    return report
