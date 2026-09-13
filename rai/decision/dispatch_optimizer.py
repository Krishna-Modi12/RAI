"""Fleet Crew Dispatch and Safe-Weather-Window Optimizer for RAI.

Balances technician crew capacity, economic loss avoidance, and site-level
meteorological safety windows:
- Wind turbine tower climb safety: sustained wind < 12.0 m/s, gusts < 18.0 m/s, no heavy rain.
- Solar inverter enclosure safety: no precipitation (rain = 0 mm/h), ambient temp < 45°C.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from rai.environment.weather_provider import get_weather_provider
from rai.memory.work_orders import (
    WorkOrderPriority,
    WorkOrderRecord,
    WorkOrderStatus,
    list_work_orders,
)

# CONFIGURED OPERATIONAL CONSTRAINTS (Site Dispatch Heuristics)
# ---------------------------------------------------------------------------
# NOTE: These values represent site-configurable operational dispatch assumptions,
# NOT universal OEM engineering standards or statutory laws.
# In production environments, operators must configure these thresholds to match
# plant-specific safety manuals (e.g., turbine OEM climb limits, OSHA/CEA electrical codes).
CONFIGURED_WIND_CLIMB_SPEED_LIMIT_MS = 12.0
CONFIGURED_WIND_GUST_LIMIT_MS = 18.0
CONFIGURED_WIND_RAIN_PROB_LIMIT_PCT = 35.0

CONFIGURED_SOLAR_RAIN_PROB_LIMIT_PCT = 25.0
CONFIGURED_SOLAR_HEAT_LIMIT_C = 45.0

# Backward compatibility aliases
WIND_CLIMB_SPEED_LIMIT_MS = CONFIGURED_WIND_CLIMB_SPEED_LIMIT_MS
WIND_GUST_LIMIT_MS = CONFIGURED_WIND_GUST_LIMIT_MS
WIND_RAIN_PROB_LIMIT_PCT = CONFIGURED_WIND_RAIN_PROB_LIMIT_PCT
SOLAR_RAIN_PROB_LIMIT_PCT = CONFIGURED_SOLAR_RAIN_PROB_LIMIT_PCT
SOLAR_HEAT_LIMIT_C = CONFIGURED_SOLAR_HEAT_LIMIT_C

ESTIMATED_DURATION_HOURS: dict[str, float] = {
    "gearbox": 6.0,
    "generator": 5.0,
    "main_bearing": 6.0,
    "pitch_system": 3.5,
    "yaw_drive": 4.0,
    "inverter": 3.0,
    "pv_strings": 2.5,
    "combiner_box": 2.0,
    "transformer": 4.5,
    "general": 2.0,
}

# MODELLED COMPONENT OUTAGE EXPOSURE ESTIMATES (INR)
# ---------------------------------------------------------------------------
# PROVENANCE & UNCERTAINTY NOTE:
# These figures represent heuristic operational priorities based on estimated
# component replacement costs and modelled 48-hour lost generation exposure.
# They are MODELLED / PROJECTED consequence estimates used for dispatch sorting;
# they are NOT realized cash savings or observed financial outcomes.
COMPONENT_PROJECTED_EXPOSURE_INR: dict[str, float] = {
    "gearbox": 1_250_000.0,
    "generator": 850_000.0,
    "main_bearing": 1_100_000.0,
    "pitch_system": 350_000.0,
    "yaw_drive": 400_000.0,
    "inverter": 280_000.0,
    "pv_strings": 120_000.0,
    "combiner_box": 65_000.0,
    "transformer": 750_000.0,
    "general": 85_000.0,
}

# Backward compatibility alias
COMPONENT_AVOIDED_LOSS_INR = COMPONENT_PROJECTED_EXPOSURE_INR


class WeatherSafetyStatus(str, Enum):
    SAFE = "SAFE"
    MARGINAL = "MARGINAL"
    UNSAFE = "UNSAFE"


@dataclass(frozen=True)
class SiteWeatherWindow:
    site: str
    asset_type: str
    current_wind_speed_ms: float
    current_ambient_temp_c: float
    current_rain_probability_pct: float
    climb_safe: bool
    electrical_safe: bool
    status: WeatherSafetyStatus
    safety_rationale: str
    safe_window_hours: float
    is_live_weather: bool = True
    weather_source: str = "open_meteo_cams"
    threshold_provenance: str = "CONFIGURED_OPERATIONAL_CONSTRAINT"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass(frozen=True)
class CrewAssignment:
    assignment_id: str
    crew_id: str
    site: str
    ticket_id: str
    asset_id: str
    component: str
    priority: str
    action: str
    estimated_duration_hours: float
    scheduled_start_hour_offset: float
    weather_status: str
    projected_avoided_loss_inr: float
    dispatch_readiness: str  # "READY_IMMEDIATE" | "AWAITING_WEATHER_WINDOW" | "PENDING_APPROVAL"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FleetDispatchPlan:
    generated_at: str
    site_windows: dict[str, SiteWeatherWindow]
    assignments: list[CrewAssignment]
    unassigned_orders: list[dict[str, Any]]
    active_crews_count: int
    total_avoided_loss_inr: float
    total_scheduled_hours: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "site_windows": {k: v.to_dict() for k, v in self.site_windows.items()},
            "assignments": [a.to_dict() for a in self.assignments],
            "unassigned_orders": self.unassigned_orders,
            "active_crews_count": self.active_crews_count,
            "total_avoided_loss_inr": self.total_avoided_loss_inr,
            "total_scheduled_hours": self.total_scheduled_hours,
        }


def evaluate_site_weather(site: str) -> SiteWeatherWindow:
    """Evaluate current meteorological safety for a specific plant site."""
    provider = get_weather_provider()
    cond = provider.get_current_conditions(site)

    if "wind" in site.lower():
        asset_type = "wind_turbine"
        climb_safe = (
            cond.wind_speed_ms <= WIND_CLIMB_SPEED_LIMIT_MS
            and cond.rain_probability_pct <= WIND_RAIN_PROB_LIMIT_PCT
        )
        electrical_safe = cond.rain_probability_pct <= WIND_RAIN_PROB_LIMIT_PCT

        if climb_safe:
            status = WeatherSafetyStatus.SAFE
            rationale = (
                f"Sustained wind {cond.wind_speed_ms:.1f} m/s <= {WIND_CLIMB_SPEED_LIMIT_MS} m/s; "
                f"rain prob {cond.rain_probability_pct:.0f}% <= {WIND_RAIN_PROB_LIMIT_PCT}%. Tower climb approved."
            )
            safe_hours = 24.0
        elif cond.wind_speed_ms <= WIND_GUST_LIMIT_MS:
            status = WeatherSafetyStatus.MARGINAL
            rationale = (
                f"Marginal winds {cond.wind_speed_ms:.1f} m/s approaching climb limit. Ground maintenance only."
            )
            safe_hours = 6.0
        else:
            status = WeatherSafetyStatus.UNSAFE
            rationale = (
                f"High winds {cond.wind_speed_ms:.1f} m/s exceed nacelle climb safety limits. Tower climb locked out."
            )
            safe_hours = 0.0
    else:
        asset_type = "solar_inverter"
        climb_safe = True
        electrical_safe = (
            cond.rain_probability_pct <= SOLAR_RAIN_PROB_LIMIT_PCT
            and cond.precipitation_mm <= 0.1
        )

        if not electrical_safe:
            status = WeatherSafetyStatus.UNSAFE
            rationale = (
                f"Rain probability {cond.rain_probability_pct:.0f}% / {cond.precipitation_mm:.1f} mm precip. "
                f"High-voltage electrical lockout active."
            )
            safe_hours = 0.0
        elif cond.ambient_temp_c >= SOLAR_HEAT_LIMIT_C:
            status = WeatherSafetyStatus.MARGINAL
            rationale = (
                f"Ambient heat {cond.ambient_temp_c:.1f}°C exceeds heat threshold. Heavy exertion restricted."
            )
            safe_hours = 4.0
        else:
            status = WeatherSafetyStatus.SAFE
            rationale = (
                f"Clear dry conditions: temp {cond.ambient_temp_c:.1f}°C, rain prob {cond.rain_probability_pct:.0f}%. "
                f"Open enclosure maintenance approved."
            )
            safe_hours = 36.0

    return SiteWeatherWindow(
        site=site,
        asset_type=asset_type,
        current_wind_speed_ms=round(cond.wind_speed_ms, 1),
        current_ambient_temp_c=round(cond.ambient_temp_c, 1),
        current_rain_probability_pct=round(cond.rain_probability_pct, 1),
        climb_safe=climb_safe,
        electrical_safe=electrical_safe,
        status=status,
        safety_rationale=rationale,
        safe_window_hours=safe_hours,
        is_live_weather=getattr(cond, "is_live", True),
        weather_source=getattr(cond, "source_detail", "open_meteo_cams"),
    )


def generate_fleet_dispatch_plan(
    orders: list[WorkOrderRecord] | None = None,
    crews_per_site: int = 2,
) -> FleetDispatchPlan:
    """Generate an optimized crew dispatch plan balancing priority and weather safety."""
    if orders is None:
        orders = list_work_orders(limit=100)

    # 1. Site weather evaluation
    kutch_window = evaluate_site_weather("kutch-wind")
    charanka_window = evaluate_site_weather("charanka-solar")
    site_windows = {
        "kutch-wind": kutch_window,
        "charanka-solar": charanka_window,
    }

    # 2. Filter active candidates (not rejected or completed)
    active_statuses = {
        WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value,
        WorkOrderStatus.APPROVED.value,
        WorkOrderStatus.IN_PROGRESS.value,
    }
    candidates = [
        o for o in orders
        if (o.status.value if isinstance(o.status, WorkOrderStatus) else str(o.status)) in active_statuses
    ]

    # 3. Sort by priority, then deadline
    prio_weights = {
        WorkOrderPriority.EMERGENCY.value: 4,
        WorkOrderPriority.HIGH.value: 3,
        WorkOrderPriority.MEDIUM.value: 2,
        WorkOrderPriority.LOW.value: 1,
    }

    def _score(ord_rec: WorkOrderRecord) -> tuple[int, int, float]:
        prio_val = ord_rec.priority.value if isinstance(ord_rec.priority, WorkOrderPriority) else str(ord_rec.priority)
        prio_score = prio_weights.get(prio_val, 1)
        deadline = ord_rec.deadline_hours if ord_rec.deadline_hours is not None else 168
        loss = COMPONENT_AVOIDED_LOSS_INR.get(ord_rec.component.lower(), 50_000.0)
        return (-prio_score, deadline, -loss)

    candidates.sort(key=_score)

    # 4. Schedule across available crews
    assignments: list[CrewAssignment] = []
    unassigned: list[dict[str, Any]] = []
    crew_time_offsets: dict[str, float] = {}

    for ord_rec in candidates:
        site_key = "kutch-wind" if ord_rec.asset_id.startswith("WT") else "charanka-solar"
        window = site_windows.get(site_key, kutch_window)
        comp = ord_rec.component.lower()
        duration = ESTIMATED_DURATION_HOURS.get(comp, 2.5)
        avoided = COMPONENT_AVOIDED_LOSS_INR.get(comp, 75_000.0)

        # Determine available crew index
        crew_prefix = "Kutch-Crew" if "wind" in site_key else "Charanka-Crew"
        crew_indices = [f"{crew_prefix}-{i+1}" for i in range(crews_per_site)]

        # Find crew with earliest availability
        best_crew = min(crew_indices, key=lambda c: crew_time_offsets.get(c, 0.0))
        start_offset = crew_time_offsets.get(best_crew, 0.0)

        # Check weather readiness
        if window.status == WeatherSafetyStatus.UNSAFE:
            readiness = "AWAITING_WEATHER_WINDOW"
            w_status = f"UNSAFE ({window.safety_rationale})"
        elif (
            ord_rec.status == WorkOrderStatus.PROPOSED_AWAITING_APPROVAL
            or (isinstance(ord_rec.status, str) and ord_rec.status == WorkOrderStatus.PROPOSED_AWAITING_APPROVAL.value)
        ):
            readiness = "PENDING_APPROVAL"
            w_status = f"{window.status.value} (Awaiting Authorization)"
        else:
            readiness = "READY_IMMEDIATE"
            w_status = f"{window.status.value} (Approved for Dispatch)"

        if len(assignments) < (crews_per_site * 3):  # Cap total schedule horizon
            asgn = CrewAssignment(
                assignment_id=f"DISP-{len(assignments)+1:03d}",
                crew_id=best_crew,
                site=site_key,
                ticket_id=ord_rec.ticket_id,
                asset_id=ord_rec.asset_id,
                component=ord_rec.component,
                priority=ord_rec.priority.value if isinstance(ord_rec.priority, WorkOrderPriority) else str(ord_rec.priority),
                action=ord_rec.action,
                estimated_duration_hours=duration,
                scheduled_start_hour_offset=round(start_offset, 1),
                weather_status=w_status,
                projected_avoided_loss_inr=avoided,
                dispatch_readiness=readiness,
            )
            assignments.append(asgn)
            crew_time_offsets[best_crew] = start_offset + duration
        else:
            unassigned.append({
                "ticket_id": ord_rec.ticket_id,
                "asset_id": ord_rec.asset_id,
                "component": ord_rec.component,
                "priority": ord_rec.priority.value if isinstance(ord_rec.priority, WorkOrderPriority) else str(ord_rec.priority),
                "reason": "Crew capacity threshold reached for active shift",
            })

    total_loss = sum(a.projected_avoided_loss_inr for a in assignments)
    total_hours = sum(a.estimated_duration_hours for a in assignments)

    return FleetDispatchPlan(
        generated_at=datetime.now(UTC).isoformat(),
        site_windows=site_windows,
        assignments=assignments,
        unassigned_orders=unassigned,
        active_crews_count=crews_per_site * 2,
        total_avoided_loss_inr=total_loss,
        total_scheduled_hours=total_hours,
    )
