"""Solar Environmental Risk Intelligence & Soiling Kinetics Engine.

DEPRECATION NOTE:
This module has been modularized into `rai.environment.*`.
For new development, import directly from:
- `rai.environment.dust` (Dust storm risk, cumulative exposure memory)
- `rai.environment.rain` (Precipitation kinetics, cementation hypothesis)
- `rai.environment.clearsky` (pvlib clear-sky irradiance and cloud filtering)
- `rai.environment.soiling` (Kimber, RdTools SRR, and weather-conditioned soiling)
- `rai.environment.attribution` (Model-based loss attribution)
- `rai.environment.cleaning_optimizer` (Dynamic opportunity window and weather scenarios)

All public classes and functions are preserved here for full backward compatibility.
"""

from __future__ import annotations

from rai.environment.attribution import (
    AdditiveLossDecomposition,
    ModelBasedLossAttribution,
    decompose_pv_power_loss,
    decompose_solar_losses,
)
from rai.environment.cleaning_optimizer import (
    CleaningOpportunity,
    CleaningScenario,
    optimize_cleaning_schedule,
)
from rai.environment.clearsky import (
    ClearSkyBaseline,
    compute_clear_sky_poa,
    compute_clearsky_poa,
    filter_cloud_unstable_intervals,
)
from rai.environment.dust import (
    CumulativeDustExposure,
    DustStormRisk,
    compute_dust_exposure_memory,
    detect_dust_storm_risk,
    estimate_deposition_prior,
)
from rai.environment.rain import (
    RainWashingAnalysis,
    evaluate_rain_washing,
)
from rai.environment.soiling import (
    SolarSoilingState,
    assess_soiling_kinetics,
    estimate_soiling_state,
)

# Backwards-compatible convenience alias
evaluate_rain_wash_economics = optimize_cleaning_schedule

__all__ = [
    "AdditiveLossDecomposition",
    "CleaningOpportunity",
    "CleaningScenario",
    "ClearSkyBaseline",
    "CumulativeDustExposure",
    "DustStormRisk",
    "ModelBasedLossAttribution",
    "RainWashingAnalysis",
    "SolarSoilingState",
    "assess_soiling_kinetics",
    "compute_clear_sky_poa",
    "compute_clearsky_poa",
    "compute_dust_exposure_memory",
    "decompose_pv_power_loss",
    "decompose_solar_losses",
    "detect_dust_storm_risk",
    "estimate_deposition_prior",
    "estimate_soiling_state",
    "evaluate_rain_wash_economics",
    "evaluate_rain_washing",
    "filter_cloud_unstable_intervals",
    "optimize_cleaning_schedule",
]
