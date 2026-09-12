"""Modular Environmental Intelligence Package for RAI.

Decomposes environmental and meteorological modeling into:
- weather_provider: CAMS aerosol and Open-Meteo weather integration with local cache.
- dust: Desert dust aerosol exposure memory, cumulative integrals, and deposition priors.
- rain: Precipitation kinetics, natural wash probability, and mud cementation risk hypothesis.
- clearsky: pvlib-backed clear-sky POA normalization and cloud stability filtering.
- soiling: Kimber and RdTools SRR/CODS soiling state estimation with confidence intervals.
- attribution: Model-based loss attribution (cloud, soiling, thermal, curtailment, equipment, unexplained).
- cleaning_optimizer: Probabilistic dynamic cleaning opportunity window with weather scenarios.
"""

from __future__ import annotations

from .attribution import (
    AdditiveLossDecomposition,
    ModelBasedLossAttribution,
    decompose_pv_power_loss,
)
from .cleaning_optimizer import (
    CleaningOpportunity,
    CleaningScenario,
    optimize_cleaning_schedule,
)
from .clearsky import (
    ClearSkyBaseline,
    compute_clearsky_poa,
    filter_cloud_unstable_intervals,
)
from .dust import (
    CumulativeDustExposure,
    DustStormRisk,
    compute_dust_exposure_memory,
    detect_dust_storm_risk,
    estimate_deposition_prior,
)
from .rain import (
    RainWashingAnalysis,
    evaluate_rain_washing,
)
from .soiling import (
    SolarSoilingState,
    estimate_soiling_state,
)
from .weather_provider import (
    SITE_COORDINATES,
    AtmosphericConditions,
    WeatherProvider,
    get_weather_provider,
)

__all__ = [
    "AdditiveLossDecomposition",
    "AtmosphericConditions",
    "CleaningOpportunity",
    "CleaningScenario",
    "ClearSkyBaseline",
    "CumulativeDustExposure",
    "DustStormRisk",
    "ModelBasedLossAttribution",
    "RainWashingAnalysis",
    "SITE_COORDINATES",
    "SolarSoilingState",
    "WeatherProvider",
    "compute_clearsky_poa",
    "compute_dust_exposure_memory",
    "decompose_pv_power_loss",
    "detect_dust_storm_risk",
    "estimate_deposition_prior",
    "estimate_soiling_state",
    "evaluate_rain_washing",
    "filter_cloud_unstable_intervals",
    "get_weather_provider",
    "optimize_cleaning_schedule",
]
