"""Precipitation kinetics, natural washing recovery, and mud cementation risk hypothesis.

Treats natural washing as a non-linear threshold function:
- Trace rain (< 2.0 mm): Insufficient kinetic volume to flush particles; solubilizes salts.
- Moderate rain (2.0 - 10.0 mm): Partial wash (40% - 85% soiling recovery).
- Heavy rain (> 10.0 mm): Effective flush (> 90% soiling recovery).

Crucially, 'Mud Cementation' is treated as a scientific hypothesis and risk category
('HIGH', 'MODERATE', 'LOW'), acknowledging that actual cementation depends on module tilt,
water droplet evaporation rate, and dust mineralogy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RainWashingAnalysis:
    """Precipitation and wash effectiveness analysis."""

    precipitation_24h_mm: float
    rain_probability_48h: float
    days_since_rain: float
    wash_recovery_factor: float  # [0.0, 1.0] fraction of accumulated soiling washed away
    natural_cleaning_likely: bool
    mud_cementation_risk: str  # "HIGH", "MODERATE", "LOW", "NEGLIGIBLE" (Hypothesis-based)
    hypothesis_rationale: str


def evaluate_rain_washing(
    precipitation_mm: float,
    rain_probability_48h: float,
    days_since_rain: float,
    antecedent_dust_ug_m3: float = 40.0,
    current_soiling_loss_pct: float = 5.0,
) -> RainWashingAnalysis:
    """Evaluate natural washing potential and cementation risk hypothesis."""
    # Natural washing threshold curve (based on Kimber et al. & RdTools literature)
    if precipitation_mm >= 12.0:
        wash_recovery = 0.95
        cleaning_likely = True
    elif precipitation_mm >= 6.0:
        wash_recovery = 0.75
        cleaning_likely = True
    elif precipitation_mm >= 2.5:
        wash_recovery = 0.45
        cleaning_likely = (rain_probability_48h >= 70.0)
    else:
        # Trace rain < 2.5 mm provides negligible self-cleaning
        wash_recovery = 0.05 if precipitation_mm > 0.5 else 0.0
        cleaning_likely = False

    # Mud cementation hypothesis:
    # Occurs when light moisture is sufficient to wet surface dust into a slurry,
    # but lacks volume to wash it off the bottom frame, baking upon subsequent solar drying.
    if (0.2 <= precipitation_mm <= 3.0 or (precipitation_mm < 0.5 and rain_probability_48h > 60.0)) and (
        antecedent_dust_ug_m3 > 75.0 or current_soiling_loss_pct > 6.0
    ):
        cementation_risk = "HIGH"
        rationale = (
            "Hypothesis: Trace precipitation (< 3.0 mm) combined with heavy antecedent particulate "
            "exposure (> 75 ug/m3) creates a slurry that risks cementing upon rapid solar drying."
        )
    elif (0.5 <= precipitation_mm <= 4.0) and (antecedent_dust_ug_m3 > 40.0):
        cementation_risk = "MODERATE"
        rationale = (
            "Hypothesis: Marginal rain volume with moderate antecedent dust may form localized "
            "streaks along module lower frames without full rinse."
        )
    elif precipitation_mm > 5.0:
        cementation_risk = "LOW"
        rationale = "Adequate hydraulic volume to overcome surface tension and flush suspended particles off modules."
    else:
        cementation_risk = "NEGLIGIBLE"
        rationale = "Dry conditions or negligible rain volume; standard dry deposition kinetics apply."

    return RainWashingAnalysis(
        precipitation_24h_mm=round(precipitation_mm, 2),
        rain_probability_48h=round(rain_probability_48h, 1),
        days_since_rain=round(days_since_rain, 1),
        wash_recovery_factor=round(wash_recovery, 3),
        natural_cleaning_likely=cleaning_likely,
        mud_cementation_risk=cementation_risk,
        hypothesis_rationale=rationale,
    )
