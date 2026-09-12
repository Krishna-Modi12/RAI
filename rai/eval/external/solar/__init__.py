"""Solar evaluation, expected-performance modeling, and data foundation package for RAI."""

from __future__ import annotations

from rai.eval.external.solar.filters import (
    QualityFilterResult,
    QualityState,
    apply_quality_filters,
    verify_clearsky_consistency,
)
from rai.eval.external.solar.metrics import (
    DailyEnergyMetricRecord,
    ModelMetricRecord,
    RegimeMetricRecord,
    ResidualDiagnosticsRecord,
    compute_daily_energy_metrics,
    compute_pointwise_metrics,
    compute_regime_metrics,
    compute_residual_diagnostics,
)
from rai.eval.external.solar.models import (
    ModelType,
    PVLibPhysicsReference,
    RAISolarChampion,
    SolarEmpiricalBaseline,
    SolarHealthEvidence,
)
from rai.eval.external.solar.pvdaq import (
    GATE56_SEED,
    CohortRole,
    PVDAQSystemMetadata,
    SplitType,
    split_system_telemetry,
)

__all__ = [
    "GATE56_SEED",
    "CohortRole",
    "DailyEnergyMetricRecord",
    "ModelMetricRecord",
    "ModelType",
    "PVDAQSystemMetadata",
    "PVLibPhysicsReference",
    "QualityFilterResult",
    "QualityState",
    "RAISolarChampion",
    "RegimeMetricRecord",
    "ResidualDiagnosticsRecord",
    "SolarEmpiricalBaseline",
    "SolarHealthEvidence",
    "SplitType",
    "apply_quality_filters",
    "compute_daily_energy_metrics",
    "compute_pointwise_metrics",
    "compute_regime_metrics",
    "compute_residual_diagnostics",
    "split_system_telemetry",
    "verify_clearsky_consistency",
]
