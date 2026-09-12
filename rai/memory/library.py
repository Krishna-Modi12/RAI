"""The historical case library.

Every case is one past episode reduced to a **signature**: where the deviation showed up, how
fast it grew, whether the peers saw it, and whether the environment explained it. The
signature lives in the same space as `signature_from_packet`, so a live asset and a closed
case are directly comparable.

Two things about this library are deliberate and should not be quietly changed.

**It is labelled.** These are illustrative cases authored for this project from the incident
logs in `knowledge/incidents/`, not a customer's maintenance history. `HistoricalCase.source`
carries `synthetic_case_library` so the provenance travels with the evidence into the UI and
into the agent's citation list. A demo that passes off invented history as real history is the
one failure mode this project refuses.

**It contains failures of the monitoring process, not only failures of machines.** Four of the
fourteen cases closed with *no equipment fault found*: a drifting anemometer, a soiling
episode, a curtailment window and a frozen irradiance sensor. Those are the cases worth
retrieving. A library of nothing but confirmed gearbox failures teaches the retrieval layer
that every deviation is a gearbox failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- signal taxonomy

# Which physical channel a signal belongs to. The signature compares *channels*, not signal
# names, because a gearbox and an inverter never share a signal name but do share the fact
# that the heat channel moved while the power channel did not.
POWER_SIGNALS = {"power_kw", "ac_power_kw", "dc_power_kw", "performance_ratio"}
THERMAL_SIGNALS = {
    "gearbox_oil_temp_c",
    "generator_winding_temp_c",
    "main_bearing_temp_c",
    "nacelle_temp_c",
    "module_temp_c",
    "inverter_temp_c",
}
MECHANICAL_SIGNALS = {
    "drivetrain_vibration_mms",
    "rotor_rpm",
    "dc_current_a",
    "dc_voltage_v",
}

# Feature order for the signature vector. Changing this list invalidates every stored case.
FEATURES = (
    "power_z",        # signed, /5 and clipped: a deficit is negative, an excess positive
    "thermal_z",      # signed, /5 and clipped
    "mechanical_z",   # signed, /5 and clipped
    "peer_percentile",  # 0..1
    "env_explains",   # 0..1 — how much of the deficit the weather accounted for
    "persistence",    # 0..1, log-scaled over 30 days
    "growth_rate",    # 0..1 — sigma per day; separates a step from a slow ramp
    "step_change",    # 0/1 — changepoint fired
    "soiling_loss",   # 0..1, /20 pct
    "anomaly_score",  # 0..1
)

# Not every feature discriminates equally. Growth rate and the step flag are what separate a
# string outage from soiling; the environment fraction is what separates a fault from weather.
WEIGHTS: dict[str, float] = {
    "power_z": 1.30,
    "thermal_z": 1.30,
    "mechanical_z": 1.20,
    "peer_percentile": 0.70,
    "env_explains": 1.10,
    "persistence": 0.60,
    "growth_rate": 1.00,
    "step_change": 0.90,
    "soiling_loss": 0.80,
    "anomaly_score": 0.50,
}


@dataclass(frozen=True)
class Case:
    """A closed episode. `signature` is keyed by `FEATURES`; missing keys default to 0."""

    case_id: str
    asset_id: str
    asset_type: str  # "wind_turbine" | "solar_inverter"
    component: str
    fault_mode: str
    equipment_fault: bool
    observed_signature: list[str]
    outcome: str
    lead_time_days: float | None
    repair_cost_inr: float | None
    signature: dict[str, float] = field(default_factory=dict)
    source_doc: str | None = None
    closed_at: str | None = None

    def vector(self) -> list[float]:
        return [float(self.signature.get(name, 0.0)) for name in FEATURES]


# --------------------------------------------------------------------------- the library

WIND_CASES: list[Case] = [
    Case(
        case_id="CASE-W-001",
        asset_id="WT-006",
        asset_type="wind_turbine",
        component="gearbox",
        fault_mode="HSS bearing outer-race spalling",
        equipment_fault=True,
        observed_signature=[
            "gearbox oil temperature rising against modelled load",
            "drivetrain vibration trending up, BPFO order confirmed by envelope analysis",
            "Fe 68 ppm and rising in oil",
        ],
        outcome=(
            "Confirmed on borescope: outer-race spalling on the HSS rear bearing. Replaced "
            "up-tower in a planned 34 h outage. No secondary gear damage because the "
            "intervention came 22 days before the projected trip."
        ),
        lead_time_days=22.0,
        repair_cost_inr=1_180_000,
        signature={
            "power_z": -0.18,
            "thermal_z": 0.74,
            "mechanical_z": 0.66,
            "peer_percentile": 0.91,
            "env_explains": 0.08,
            "persistence": 0.72,
            "growth_rate": 0.34,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.88,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    Case(
        case_id="CASE-W-002",
        asset_id="WT-012",
        asset_type="wind_turbine",
        component="gearbox",
        fault_mode="planetary stage micropitting, early",
        equipment_fault=True,
        observed_signature=[
            "oil temperature residual +2.9 sigma, slow ramp over 5 weeks",
            "vibration within ISO zone B throughout",
            "particle count degraded two ISO 4406 codes",
        ],
        outcome=(
            "Borescope found micropitting on the planetary ring gear with no macro-scale "
            "distress. Oil changed to a higher-viscosity grade, filtration upgraded, asset "
            "kept on a 30-day re-inspection. No replacement needed."
        ),
        lead_time_days=41.0,
        repair_cost_inr=145_000,
        signature={
            "power_z": -0.10,
            "thermal_z": 0.58,
            "mechanical_z": 0.22,
            "peer_percentile": 0.79,
            "env_explains": 0.14,
            "persistence": 0.85,
            "growth_rate": 0.16,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.64,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    Case(
        case_id="CASE-W-003",
        asset_id="WT-003",
        asset_type="wind_turbine",
        component="generator",
        fault_mode="cooling-air filter blockage, winding overtemperature",
        equipment_fault=True,
        observed_signature=[
            "winding temperature residual +3.6 sigma at matched load and ambient",
            "short thermal time constant — the rise tracked load within the hour",
            "no vibration change",
        ],
        outcome=(
            "Cooling-air filters found 80% blinded by dust after a pre-monsoon dust event. "
            "Filters replaced, heat exchanger cleaned. Winding temperature returned to "
            "baseline within one operating day. No winding damage; insulation resistance "
            "and polarization index both normal."
        ),
        lead_time_days=9.0,
        repair_cost_inr=62_000,
        signature={
            "power_z": -0.06,
            "thermal_z": 0.86,
            "mechanical_z": 0.05,
            "peer_percentile": 0.88,
            "env_explains": 0.19,
            "persistence": 0.55,
            "growth_rate": 0.52,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.81,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    Case(
        case_id="CASE-W-004",
        asset_id="WT-009",
        asset_type="wind_turbine",
        component="pitch_system",
        fault_mode="blade pitch offset, one blade 3.1 deg out",
        equipment_fault=True,
        observed_signature=[
            "power residual -3.2 sigma concentrated in the 6-11 m/s band",
            "1P rotor-imbalance component in the tower-top accelerometer",
            "no thermal signature anywhere in the drivetrain",
        ],
        outcome=(
            "Pitch offset confirmed against blade-root markings. Encoder re-zeroed and the "
            "pitch controller re-calibrated during a 6 h outage. Power curve recovered to "
            "within 0.6% of the fleet reference."
        ),
        lead_time_days=16.0,
        repair_cost_inr=288_000,
        signature={
            "power_z": -0.64,
            "thermal_z": 0.04,
            "mechanical_z": 0.30,
            "peer_percentile": 0.86,
            "env_explains": 0.16,
            "persistence": 0.68,
            "growth_rate": 0.28,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.59,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    Case(
        case_id="CASE-W-005",
        asset_id="WT-016",
        asset_type="wind_turbine",
        component="yaw_system",
        fault_mode="static yaw misalignment, 11 deg",
        equipment_fault=True,
        observed_signature=[
            "power residual -2.4 sigma, stepped on at a single maintenance date",
            "changepoint detector fired on the conditioned residual",
            "nacelle vane offset unchanged in SCADA — the error was mechanical, not the vane",
        ],
        outcome=(
            "Spinner-anemometer survey measured 11 deg static yaw error introduced when the "
            "vane bracket was refitted after a scheduled service. Bracket re-indexed and the "
            "offset table corrected. Recovered roughly 1.8% of annual energy."
        ),
        lead_time_days=12.0,
        repair_cost_inr=54_000,
        signature={
            "power_z": -0.49,
            "thermal_z": 0.02,
            "mechanical_z": 0.08,
            "peer_percentile": 0.81,
            "env_explains": 0.20,
            "persistence": 0.62,
            "growth_rate": 0.44,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.52,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    Case(
        case_id="CASE-W-006",
        asset_id="WT-005",
        asset_type="wind_turbine",
        component="main_bearing",
        fault_mode="main bearing grease degradation, temperature drift",
        equipment_fault=True,
        observed_signature=[
            "main bearing temperature residual +3.1 sigma with a long time constant",
            "vibration elevated at low orders only",
            "grease sample showed oxidation and base-oil separation",
        ],
        outcome=(
            "Automatic lubricator line found partially blocked. Line cleared, bearing purged "
            "and re-greased. Temperature returned to baseline over four days as the new grease "
            "distributed. Bearing retained — no raceway damage on endoscopic inspection."
        ),
        lead_time_days=28.0,
        repair_cost_inr=96_000,
        signature={
            "power_z": -0.04,
            "thermal_z": 0.68,
            "mechanical_z": 0.34,
            "peer_percentile": 0.84,
            "env_explains": 0.11,
            "persistence": 0.78,
            "growth_rate": 0.20,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.71,
        },
        source_doc="incident-log-wind-gearbox",
    ),
    # ----------------------------------------------------------------- instructive non-faults
    Case(
        case_id="CASE-W-007",
        asset_id="WT-011",
        asset_type="wind_turbine",
        component="anemometer",
        fault_mode="anemometer calibration drift reading high",
        equipment_fault=False,
        observed_signature=[
            "apparent power deficit of 6% against the measured-wind power curve",
            "rotor-speed-implied wind disagreed with the anemometer by +13%",
            "no thermal, vibration or electrical signature of any kind",
        ],
        outcome=(
            "NO EQUIPMENT FAULT. The anemometer had drifted high, so the expected-power "
            "reference was inflated and a healthy machine looked like it was underperforming. "
            "A crew was dispatched for a gearbox inspection before the cross-check was run — "
            "a wasted truck roll. Anemometer replaced and recalibrated; the deficit vanished. "
            "This case is the reason sensor validation now precedes every equipment verdict."
        ),
        lead_time_days=None,
        repair_cost_inr=45_000,
        signature={
            "power_z": -0.52,
            "thermal_z": 0.03,
            "mechanical_z": 0.06,
            "peer_percentile": 0.74,
            "env_explains": 0.30,
            "persistence": 0.70,
            "growth_rate": 0.18,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.48,
        },
        source_doc="scada-sensor-validation-sop",
    ),
    Case(
        case_id="CASE-W-008",
        asset_id="WT-002",
        asset_type="wind_turbine",
        component="none",
        fault_mode="grid curtailment mistaken for a converter derate",
        equipment_fault=False,
        observed_signature=[
            "output capped well below the power curve for 9 h",
            "operating state logged as curtailed for the whole window",
            "all thermal and vibration channels nominal",
        ],
        outcome=(
            "NO EQUIPMENT FAULT. A state load-despatch curtailment instruction capped the "
            "farm. The cap was initially read as a converter power limit. Curtailed intervals "
            "are now excluded from availability and hard-suppress equipment risk."
        ),
        lead_time_days=None,
        repair_cost_inr=0.0,
        signature={
            "power_z": -0.70,
            "thermal_z": -0.12,
            "mechanical_z": -0.10,
            "peer_percentile": 0.55,
            "env_explains": 0.45,
            "persistence": 0.40,
            "growth_rate": 0.60,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.22,
        },
        source_doc="grid-curtailment-policy",
    ),
]

SOLAR_CASES: list[Case] = [
    Case(
        case_id="CASE-S-001",
        asset_id="INV-004",
        asset_type="solar_inverter",
        component="dc_string",
        fault_mode="string outage, blown combiner fuse",
        equipment_fault=True,
        observed_signature=[
            "DC current dropped ~5% in a single interval and stayed down",
            "DC voltage unchanged — the array still held its MPP window",
            "changepoint detector fired; the step was clean, not a ramp",
        ],
        outcome=(
            "One of twenty strings open at the combiner. Fuse had cleared on a ground fault "
            "traced to a chafed conductor at a cable-tray edge. Conductor repaired, fuse "
            "replaced, insulation resistance verified before re-energising."
        ),
        lead_time_days=2.0,
        repair_cost_inr=28_000,
        signature={
            "power_z": -0.46,
            "thermal_z": -0.05,
            "mechanical_z": -0.58,
            "peer_percentile": 0.89,
            "env_explains": 0.10,
            "persistence": 0.50,
            "growth_rate": 0.82,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.66,
        },
        source_doc="incident-log-solar-inverter",
    ),
    Case(
        case_id="CASE-S-002",
        asset_id="INV-018",
        asset_type="solar_inverter",
        component="inverter",
        fault_mode="thermal derate from a fouled heatsink",
        equipment_fault=True,
        observed_signature=[
            "heatsink temperature residual +3.8 sigma at matched POA and ambient",
            "AC output clipped below the DC-available curve on clear afternoons only",
            "cooling fan current normal — the airflow path was the restriction",
        ],
        outcome=(
            "Heatsink fins and intake filters heavily dust-fouled. Cleaned and filters "
            "replaced. Derate events stopped; heatsink temperature fell 14 K at matched "
            "conditions. Cleaning added to the pre-monsoon campaign."
        ),
        lead_time_days=11.0,
        repair_cost_inr=34_000,
        signature={
            "power_z": -0.30,
            "thermal_z": 0.78,
            "mechanical_z": -0.14,
            "peer_percentile": 0.90,
            "env_explains": 0.22,
            "persistence": 0.66,
            "growth_rate": 0.36,
            "step_change": 0.0,
            "soiling_loss": 0.02,
            "anomaly_score": 0.83,
        },
        source_doc="incident-log-solar-inverter",
    ),
    Case(
        case_id="CASE-S-003",
        asset_id="INV-009",
        asset_type="solar_inverter",
        component="inverter",
        fault_mode="DC bus capacitor ageing",
        equipment_fault=True,
        observed_signature=[
            "efficiency residual drifting down over six weeks",
            "internal temperature up at matched load",
            "DC bus ripple elevated on the service log",
        ],
        outcome=(
            "Capacitor bank ESR measured out of tolerance. Bank replaced under a planned "
            "outage before the unit tripped. Efficiency recovered to 98.1% European."
        ),
        lead_time_days=34.0,
        repair_cost_inr=165_000,
        signature={
            "power_z": -0.22,
            "thermal_z": 0.52,
            "mechanical_z": -0.08,
            "peer_percentile": 0.83,
            "env_explains": 0.15,
            "persistence": 0.88,
            "growth_rate": 0.12,
            "step_change": 0.0,
            "soiling_loss": 0.01,
            "anomaly_score": 0.61,
        },
        source_doc="incident-log-solar-inverter",
    ),
    Case(
        case_id="CASE-S-004",
        asset_id="INV-021",
        asset_type="solar_inverter",
        component="dc_string",
        fault_mode="potential induced degradation in two strings",
        equipment_fault=True,
        observed_signature=[
            "gradual DC power loss with reduced open-circuit voltage on I-V trace",
            "loss concentrated on the strings nearest the negative array pole",
            "no step, no thermal signature",
        ],
        outcome=(
            "I-V tracing confirmed PID: reduced Voc and fill factor on the affected strings. "
            "PID recovery unit fitted and the array grounding scheme corrected. Roughly 70% of "
            "the lost output recovered over three weeks of night-time regeneration."
        ),
        lead_time_days=46.0,
        repair_cost_inr=118_000,
        signature={
            "power_z": -0.38,
            "thermal_z": -0.02,
            "mechanical_z": -0.34,
            "peer_percentile": 0.80,
            "env_explains": 0.18,
            "persistence": 0.92,
            "growth_rate": 0.09,
            "step_change": 0.0,
            "soiling_loss": 0.06,
            "anomaly_score": 0.57,
        },
        source_doc="incident-log-solar-inverter",
    ),
    # ----------------------------------------------------------------- instructive non-faults
    Case(
        case_id="CASE-S-005",
        asset_id="INV-013",
        asset_type="solar_inverter",
        component="soiling",
        fault_mode="dry-season soiling accumulation",
        equipment_fault=False,
        observed_signature=[
            "performance ratio declining ~0.28%/day for 26 days with no rain",
            "DC current down, DC voltage and inverter temperature both unchanged",
            "the entire block declined together, not one unit",
        ],
        outcome=(
            "NO EQUIPMENT FAULT. Recoverable soiling loss of 7.1%. A cleaning campaign "
            "restored the performance ratio to within 0.4% of the post-monsoon reference. "
            "Because dirt attenuates photocurrent, it moves DC current and power exactly as a "
            "string outage does — voltage and inverter temperature are the channels that "
            "separate them, and the absence of a step is what separates soiling from an outage."
        ),
        lead_time_days=None,
        repair_cost_inr=42_000,
        signature={
            "power_z": -0.40,
            "thermal_z": -0.03,
            "mechanical_z": -0.36,
            "peer_percentile": 0.62,
            "env_explains": 0.34,
            "persistence": 0.90,
            "growth_rate": 0.10,
            "step_change": 0.0,
            "soiling_loss": 0.36,
            "anomaly_score": 0.54,
        },
        source_doc="solar-soiling-cleaning-sop",
    ),
    Case(
        case_id="CASE-S-006",
        asset_id="INV-002",
        asset_type="solar_inverter",
        component="none",
        fault_mode="irradiance sensor stuck, fleet-wide false alarm",
        equipment_fault=False,
        observed_signature=[
            "reference irradiance held a constant value through a partly cloudy day",
            "every inverter in the block appeared to underperform simultaneously",
            "no electrical or thermal residual on any unit",
        ],
        outcome=(
            "NO EQUIPMENT FAULT. The plane-of-array pyranometer had stuck. Because the "
            "expected-power model is driven by measured irradiance, a frozen sensor made 24 "
            "healthy inverters look faulty at once. A fleet-wide simultaneous deviation is now "
            "treated as evidence against an equipment cause, not for it. Sensor replaced."
        ),
        lead_time_days=None,
        repair_cost_inr=21_000,
        signature={
            "power_z": -0.56,
            "thermal_z": 0.0,
            "mechanical_z": -0.20,
            "peer_percentile": 0.50,
            "env_explains": 0.40,
            "persistence": 0.30,
            "growth_rate": 0.70,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.31,
        },
        source_doc="scada-sensor-validation-sop",
    ),
]

CASES: list[Case] = [*WIND_CASES, *SOLAR_CASES]

CASE_BY_ID: dict[str, Case] = {c.case_id: c for c in CASES}


def cases_for(asset_type: str) -> list[Case]:
    """Cases from the same asset family. Cross-family retrieval is never useful here."""
    return [c for c in CASES if c.asset_type == asset_type]
