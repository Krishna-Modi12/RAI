"""NREL PVDAQ Cohort Schema & Chronological Split Utility.

Provides the reusable metadata schema (`PVDAQSystemMetadata`, `SplitType`, `CohortRole`) and
a generic chronological train/validation/test splitter for NREL PVDAQ systems (OEDI submission
4568 / DOI 10.25984/1846021).

QUARANTINE NOTICE (Gate 5.6A acquisition audit): this module previously also contained a
synthetic telemetry generator (`generate_pvdaq_telemetry`) and a fabricated "cohort" dict that
the Gate 5.6 Scientific Auditor found had been used, undisclosed, as if it were real PVDAQ data,
and that produced a circular validation of the physics-reference model. That code has been
relocated to `rai/eval/external/solar/synthetic_fixtures.py` under names that make its synthetic
nature unmistakable, and it must never be imported from here again. See
`artifacts/evaluation/gate56_invalid_prior_run/invalidation_manifest.json` for the full record.

Real acquired PVDAQ data (Gate 5.6A) lives under `data/raw/pvdaq/` (raw parquet files, mirroring
the source S3 key layout) with provenance/checksum manifests under
`artifacts/evaluation/gate56/acquisition/`.

Enforces strict temporal split ordering (Train / Validation / Test) and
system-level holdout isolation with zero lookahead leakage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

# Frozen reproducibility seed for Gate 5.6
GATE56_SEED = 20260912


class SplitType(str, Enum):
    """Chronological split type."""

    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


class CohortRole(str, Enum):
    """Role of the system within the evaluation cohort."""

    TRAIN_SYSTEM = "TRAIN_SYSTEM"
    VAL_SYSTEM = "VAL_SYSTEM"
    HELD_OUT_TEST_SYSTEM = "HELD_OUT_TEST_SYSTEM"


@dataclass(frozen=True)
class PVDAQSystemMetadata:
    """Design and instrumentation metadata for an NREL PVDAQ system."""

    system_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    altitude_m: float
    rated_dc_kw: float
    rated_ac_kw: float
    module_technology: str
    array_type: str  # "fixed_open_rack", "fixed_roof", "single_axis_tracker"
    tilt_deg: float
    azimuth_deg: float  # 180 = South in Northern Hemisphere
    temp_coefficient_pct_per_c: float  # e.g. -0.38 %/°C for c-Si
    inverter_efficiency_nominal: float  # e.g. 0.965
    has_poa_pyranometer: bool
    has_ghi_pyranometer: bool
    has_module_temperature: bool
    has_ambient_temperature: bool
    has_wind_speed: bool
    cohort_role: CohortRole
    selection_rationale: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cohort_role"] = self.cohort_role.value
        return d


def split_system_telemetry(
    df: pd.DataFrame,
    train_ratio: float = 0.60,
    val_ratio: float = 0.20,
    purge_gap_intervals: int = 4,  # 1 hour purge gap between splits
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strict chronological temporal split with purge gaps to prevent lookahead leakage."""
    n = len(df)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_end = n_train
    val_start = train_end + purge_gap_intervals
    val_end = val_start + n_val
    test_start = val_end + purge_gap_intervals

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df.iloc[val_start:val_end].copy().reset_index(drop=True)
    test_df = df.iloc[test_start:].copy().reset_index(drop=True)

    train_df["split"] = SplitType.TRAIN.value
    val_df["split"] = SplitType.VALIDATION.value
    test_df["split"] = SplitType.TEST.value

    return train_df, val_df, test_df
