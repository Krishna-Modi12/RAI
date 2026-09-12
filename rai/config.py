"""Central configuration: fleet registry, physical constants, economic assumptions.

No magic numbers in model code — everything tunable lives here. Economic figures are
order-of-magnitude estimates for Indian utility-scale sites and are labelled as
assumptions wherever they surface in the UI.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from rai.schemas import Asset, AssetType

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
SYNTHETIC = DATA / "synthetic"
ARTIFACTS = ROOT / "artifacts"
MODELS = ARTIFACTS / "models"
INDEX = ARTIFACTS / "index"
KNOWLEDGE = ROOT / "knowledge"

for _p in (RAW, INTERIM, PROCESSED, SYNTHETIC, MODELS, INDEX):
    _p.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAI_", env_file=".env", extra="ignore")

    # Simulation
    sim_seed: int = 20260912
    sim_days: int = 45
    wind_interval_min: int = 10
    solar_interval_min: int = 15

    # Anomaly thresholds (selected on validation, frozen before test — see EVALUATION.md)
    residual_z_alert: float = 3.0
    anomaly_score_alert: float = 0.60
    min_persistence_hours: float = 6.0
    false_alarm_budget_per_asset_month: float = 1.0

    # Agent
    needle_confidence_threshold: float = 0.80
    agent_max_tools_per_turn: int = 5
    agent_timeout_s: float = 30.0

    # Economics
    tariff_wind_inr_per_kwh: float = 3.20
    tariff_solar_inr_per_kwh: float = 2.45
    discount_rate_annual: float = 0.10

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000


settings = Settings()

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

AIR_GAS_CONSTANT = 287.058  # J/(kg·K) dry air
STANDARD_AIR_DENSITY = 1.225  # kg/m³ at 15 °C, sea level
STC_IRRADIANCE = 1000.0  # W/m²
STC_CELL_TEMP = 25.0  # °C
PV_TEMP_COEFF_PMAX = -0.0040  # per K, typical c-Si
MODULE_NOCT = 45.0  # °C

# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

SITES = {
    "kutch-wind": {
        "name": "Kutch Wind Farm",
        "region": "Gujarat, India",
        "latitude": 23.25,
        "longitude": 69.67,
        "elevation_m": 25.0,
        "asset_type": AssetType.WIND_TURBINE,
        "prevailing_direction_deg": 250.0,
        "weibull_scale": 8.4,
        "weibull_shape": 2.05,
    },
    "charanka-solar": {
        "name": "Charanka Solar Park",
        "region": "Gujarat, India",
        "latitude": 23.90,
        "longitude": 71.20,
        "elevation_m": 90.0,
        "asset_type": AssetType.SOLAR_INVERTER,
        "tilt_deg": 24.0,
        "azimuth_deg": 180.0,
    },
}

# ---------------------------------------------------------------------------
# Fleet registry
# ---------------------------------------------------------------------------

WIND_TURBINE_COUNT = 18
SOLAR_INVERTER_COUNT = 24


def _build_wind_fleet() -> list[Asset]:
    site = SITES["kutch-wind"]
    fleet: list[Asset] = []
    for i in range(1, WIND_TURBINE_COUNT + 1):
        fleet.append(
            Asset(
                asset_id=f"WT-{i:03d}",
                asset_type=AssetType.WIND_TURBINE,
                name=f"Turbine {i:02d}",
                site="kutch-wind",
                rated_power_kw=2000.0,
                commissioned="2019-03-01",
                # Two rows of turbines — row B sits in row A's partial wake.
                peer_group="kutch-row-a" if i <= 9 else "kutch-row-b",
                rotor_diameter_m=92.0,
                hub_height_m=80.0,
                cut_in_ms=3.0,
                rated_ms=12.5,
                cut_out_ms=25.0,
                latitude=site["latitude"],
                longitude=site["longitude"],
            )
        )
    return fleet


def _build_solar_fleet() -> list[Asset]:
    site = SITES["charanka-solar"]
    fleet: list[Asset] = []
    for i in range(1, SOLAR_INVERTER_COUNT + 1):
        block = "block-1" if i <= 12 else "block-2"
        fleet.append(
            Asset(
                asset_id=f"INV-{i:03d}",
                asset_type=AssetType.SOLAR_INVERTER,
                name=f"Inverter {i:02d}",
                site="charanka-solar",
                rated_power_kw=250.0,
                dc_capacity_kw=312.5,  # 1.25 DC/AC ratio
                n_strings=20,
                commissioned="2021-06-15",
                peer_group=f"charanka-{block}",
                tilt_deg=site["tilt_deg"],
                azimuth_deg=site["azimuth_deg"],
                latitude=site["latitude"],
                longitude=site["longitude"],
            )
        )
    return fleet


FLEET: list[Asset] = _build_wind_fleet() + _build_solar_fleet()
FLEET_BY_ID: dict[str, Asset] = {a.asset_id: a for a in FLEET}

# The two assets the demo narrative follows.
HERO_WIND_ASSET = "WT-017"
HERO_SOLAR_ASSET = "INV-023"


def get_asset(asset_id: str) -> Asset:
    if asset_id not in FLEET_BY_ID:
        raise KeyError(f"unknown asset_id {asset_id!r}")
    return FLEET_BY_ID[asset_id]


def peers_of(asset_id: str) -> list[Asset]:
    asset = get_asset(asset_id)
    return [a for a in FLEET if a.peer_group == asset.peer_group and a.asset_id != asset_id]


def tariff_for(asset_id: str) -> float:
    asset = get_asset(asset_id)
    return (
        settings.tariff_wind_inr_per_kwh
        if asset.asset_type is AssetType.WIND_TURBINE
        else settings.tariff_solar_inr_per_kwh
    )


# ---------------------------------------------------------------------------
# Maintenance economics — INR. Assumptions, surfaced as such in the UI.
# ---------------------------------------------------------------------------

COMPONENT_ECONOMICS: dict[str, dict[str, float]] = {
    "gearbox": {
        "inspection_cost": 85_000,
        "planned_repair_cost": 1_250_000,
        "unplanned_failure_cost": 4_500_000,
        "planned_downtime_hours": 36.0,
        "unplanned_downtime_hours": 288.0,
        "secondary_damage_multiplier": 1.9,
    },
    "main_bearing": {
        "inspection_cost": 65_000,
        "planned_repair_cost": 950_000,
        "unplanned_failure_cost": 2_800_000,
        "planned_downtime_hours": 30.0,
        "unplanned_downtime_hours": 216.0,
        "secondary_damage_multiplier": 1.6,
    },
    "generator": {
        "inspection_cost": 55_000,
        "planned_repair_cost": 780_000,
        "unplanned_failure_cost": 2_100_000,
        "planned_downtime_hours": 24.0,
        "unplanned_downtime_hours": 168.0,
        "secondary_damage_multiplier": 1.5,
    },
    "pitch_system": {
        "inspection_cost": 40_000,
        "planned_repair_cost": 310_000,
        "unplanned_failure_cost": 850_000,
        "planned_downtime_hours": 12.0,
        "unplanned_downtime_hours": 72.0,
        "secondary_damage_multiplier": 1.3,
    },
    "yaw_system": {
        "inspection_cost": 35_000,
        "planned_repair_cost": 260_000,
        "unplanned_failure_cost": 640_000,
        "planned_downtime_hours": 10.0,
        "unplanned_downtime_hours": 60.0,
        "secondary_damage_multiplier": 1.25,
    },
    "anemometer": {
        "inspection_cost": 12_000,
        "planned_repair_cost": 45_000,
        "unplanned_failure_cost": 120_000,
        "planned_downtime_hours": 3.0,
        "unplanned_downtime_hours": 8.0,
        "secondary_damage_multiplier": 1.0,
    },
    "inverter": {
        "inspection_cost": 18_000,
        "planned_repair_cost": 180_000,
        "unplanned_failure_cost": 520_000,
        "planned_downtime_hours": 8.0,
        "unplanned_downtime_hours": 72.0,
        "secondary_damage_multiplier": 1.4,
    },
    "dc_string": {
        "inspection_cost": 8_000,
        "planned_repair_cost": 25_000,
        "unplanned_failure_cost": 60_000,
        "planned_downtime_hours": 4.0,
        "unplanned_downtime_hours": 24.0,
        "secondary_damage_multiplier": 1.1,
    },
    "soiling": {
        "inspection_cost": 0,
        "planned_repair_cost": 42_000,  # module cleaning campaign per inverter block
        "unplanned_failure_cost": 42_000,
        "planned_downtime_hours": 2.0,
        "unplanned_downtime_hours": 2.0,
        "secondary_damage_multiplier": 1.0,
    },
}

DEFAULT_COMPONENT = "gearbox"


def economics_for(component: str) -> dict[str, float]:
    return COMPONENT_ECONOMICS.get(component, COMPONENT_ECONOMICS[DEFAULT_COMPONENT])


# ---------------------------------------------------------------------------
# Monitored signals per asset type — drives feature engineering and the UI
# ---------------------------------------------------------------------------

WIND_SIGNALS = [
    ("power_kw", "kW"),
    ("gearbox_oil_temp_c", "°C"),
    ("generator_winding_temp_c", "°C"),
    ("main_bearing_temp_c", "°C"),
    ("drivetrain_vibration_mms", "mm/s"),
    ("rotor_rpm", "rpm"),
    ("nacelle_temp_c", "°C"),
]

SOLAR_SIGNALS = [
    ("ac_power_kw", "kW"),
    ("dc_power_kw", "kW"),
    ("dc_voltage_v", "V"),
    ("dc_current_a", "A"),
    ("module_temp_c", "°C"),
    ("inverter_temp_c", "°C"),
    ("performance_ratio", "ratio"),
]
