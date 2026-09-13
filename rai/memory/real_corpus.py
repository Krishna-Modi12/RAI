"""Audited real-world historical cases with explicit provenance and eligibility taxonomy.

Every case in this library originates from a real external dataset:
- CARE to Compare (Zenodo 10.5281/zenodo.14006163 / 10958775; Wind Farms A, B, C)
- Kelmarsh Wind Farm (Zenodo 10.5281/zenodo.5841834; Senvion MM92 SCADA & Greenbyte status)
- NREL PVDAQ (OEDI Open Data Lake; Systems 34 and 1283)

CRITICAL TAXONOMY RULES:
1. REAL_VERIFIED_EVENT: Component failure/breakdown confirmed by independent event log or work order.
2. REAL_OPERATIONAL_EVENT: Operational shutdown, curtailment, or control trip WITHOUT proven hardware damage.
   Do NOT convert an operational event into a component failure!
3. REAL_MAINTENANCE_EVENT: Planned or manual on-site maintenance intervention.
4. ENVIRONMENTAL_EVENT: Weather-induced standstill, curtailment, or clipping (e.g. low wind, high heat).
5. UNKNOWN: Event with ambiguous root cause.
6. EXCLUDED: Corrupt timestamps, missing key channels, or lack of provenance.

Unknown fields MUST remain UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from rai.memory.library import Case
from rai.schemas import AssetType, HistoricalSourceType


class RealEventClass(str, Enum):
    """Eligibility classification for historical cases."""

    REAL_VERIFIED_EVENT = "REAL_VERIFIED_EVENT"
    REAL_OPERATIONAL_EVENT = "REAL_OPERATIONAL_EVENT"
    REAL_MAINTENANCE_EVENT = "REAL_MAINTENANCE_EVENT"
    ENVIRONMENTAL_EVENT = "ENVIRONMENTAL_EVENT"
    UNKNOWN = "UNKNOWN"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True)
class RealCaseAdjudication:
    """Rigorous audit record of what a real case proves and what it does NOT prove."""

    what_is_explicitly_known: str
    what_is_inferred: str
    what_remains_unknown: str
    what_source_proves: str
    what_source_does_not_prove: str


@dataclass(frozen=True)
class RealHistoricalRecord:
    """Full-fidelity real historical record before reduction to case signature."""

    case_id: str
    source_dataset: str
    source_reference: str
    license: str
    asset_id: str
    asset_type: AssetType
    event_class: RealEventClass
    component: str
    fault_mode: str
    timestamp: str
    closed_at: str
    observed_pattern: str
    expected_behavior: str
    maintenance_action: str
    outcome: str
    lead_time_days: float | None
    repair_cost_inr: float | None
    evidence_quality: str
    limitations: list[str]
    adjudication: RealCaseAdjudication
    signals: dict[str, float | str | None] = field(default_factory=dict)
    operating_regime: dict[str, float | str | None] = field(default_factory=dict)
    environment: dict[str, float | str | None] = field(default_factory=dict)
    residuals: dict[str, float | None] = field(default_factory=dict)
    signature: dict[str, float] = field(default_factory=dict)

    def to_case(self) -> Case:
        """Convert to the standard Case representation used by the retrieval KNN engine."""
        return Case(
            case_id=self.case_id,
            asset_id=self.asset_id,
            asset_type=self.asset_type.value,
            component=self.component,
            fault_mode=self.fault_mode,
            equipment_fault=(self.event_class == RealEventClass.REAL_VERIFIED_EVENT),
            observed_signature=[self.observed_pattern],
            outcome=self.outcome,
            lead_time_days=self.lead_time_days,
            repair_cost_inr=self.repair_cost_inr,
            signature=dict(self.signature),
            source_doc=self.source_reference,
            closed_at=self.closed_at,
            source_type=HistoricalSourceType.EXTERNAL_REAL,
            event_class=self.event_class.value,
            source_dataset=self.source_dataset,
            source_reference=self.source_reference,
            license=self.license,
            evidence_quality=self.evidence_quality,
            limitations=list(self.limitations),
            signals=dict(self.signals),
            operating_regime=dict(self.operating_regime),
            environment=dict(self.environment),
            expected_behavior=self.expected_behavior,
            maintenance_action=self.maintenance_action,
            adjudication={
                "what_is_explicitly_known": self.adjudication.what_is_explicitly_known,
                "what_is_inferred": self.adjudication.what_is_inferred,
                "what_remains_unknown": self.adjudication.what_remains_unknown,
                "what_source_proves": self.adjudication.what_source_proves,
                "what_source_does_not_prove": self.adjudication.what_source_does_not_prove,
            },
        )


# ---------------------------------------------------------------------------
# Adjudicated Real Case Inventory (14 Cases)
# ---------------------------------------------------------------------------

REAL_RECORDS: list[RealHistoricalRecord] = [
    # 1. CARE Farm A: Gearbox Failure (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-A-072",
        source_dataset="CARE to Compare — Wind Farm A",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 72",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-A01",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="gearbox",
        fault_mode="Gearbox high-speed shaft bearing thermal escalation",
        timestamp="2021-10-09T08:40:00+00:00",
        closed_at="2021-10-16T08:40:00+00:00",
        observed_pattern="High-speed shaft bearing temperature rose from 51.3°C baseline to 66.0°C; gearbox oil temperature reached 58.0°C; active power degraded by 14.8% prior to trip.",
        expected_behavior="HSS bearing temperature below 55°C and gearbox oil temperature below 50°C under nominal 8-10 m/s wind speed.",
        maintenance_action="Gearbox replacement and up-tower overhaul documented in benchmark event log.",
        outcome="Confirmed gearbox component failure; turbine stopped and repaired during 7-day outage.",
        lead_time_days=7.0,
        repair_cost_inr=1_350_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=[
            "Anonymised turbine ID in Farm A.",
            "10-minute averaged SCADA only; vibration spectral envelope not available.",
            "Historical repair cost is estimated based on component class, not customer invoice.",
        ],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Event window timestamps, SCADA temperature channels (sensor_11_avg, sensor_12_avg), active power, and author label 'Gearbox failure'.",
            what_is_inferred="Residual z-scores against normal operating baseline intervals.",
            what_remains_unknown="Exact metallurgical failure mechanism (spalling vs micropitting vs cage fracture).",
            what_source_proves="A real catastrophic gearbox failure occurred requiring equipment replacement.",
            what_source_does_not_prove="Does not prove high-frequency vibration would have given earlier warning.",
        ),
        signals={
            "hss_bearing_temp_c": 66.0,
            "gearbox_oil_temp_c": 58.0,
            "power_kw": 1720.0,
            "wind_speed_ms": 8.5,
        },
        operating_regime={"rated_power_kw": 2050.0, "wind_speed_ms": 8.5},
        environment={"ambient_temp_c": 14.2},
        residuals={"thermal_z": 3.1, "power_z": -1.2, "mechanical_z": None},
        signature={
            "power_z": -0.42,
            "thermal_z": 0.82,
            "mechanical_z": 0.0,
            "peer_percentile": 0.94,
            "env_explains": 0.05,
            "persistence": 0.65,
            "growth_rate": 0.35,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.89,
        },
    ),
    # 2. CARE Farm A: Generator Bearing Failure (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-A-000",
        source_dataset="CARE to Compare — Wind Farm A",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 0",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-A02",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="generator",
        fault_mode="Generator drive-end bearing thermal breakdown",
        timestamp="2022-08-05T06:10:00+00:00",
        closed_at="2022-08-19T06:10:00+00:00",
        observed_pattern="Generator Bearing 2 (drive end) temperature rose from 46.5°C mean to 94.0°C; Bearing 1 reached 86.0°C; severe thermal excursion triggering emergency shutdown.",
        expected_behavior="Generator bearing temperatures balanced and below 60°C under full load.",
        maintenance_action="Generator bearing replacement and shaft alignment.",
        outcome="Confirmed generator bearing failure; turbine halted for 14-day replacement outage.",
        lead_time_days=5.0,
        repair_cost_inr=520_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=[
            "Anonymised turbine ID in Farm A.",
            "High-frequency vibration spectra unavailable in 10-minute SCADA.",
        ],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Bearing temperatures (sensor_13_avg, sensor_14_avg), timestamps, label 'Generator bearing failure'.",
            what_is_inferred="Thermal residual z-score (+4.8 sigma).",
            what_remains_unknown="Lubricant contamination level prior to seizure.",
            what_source_proves="Real physical failure of the generator bearing assembly.",
            what_source_does_not_prove="Does not prove whether grease starvation or electrical discharge machining caused the failure.",
        ),
        signals={"gen_bearing_de_temp_c": 94.0, "gen_bearing_nde_temp_c": 86.0, "power_kw": 1850.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 19.5},
        residuals={"thermal_z": 4.8, "power_z": -0.8, "mechanical_z": None},
        signature={
            "power_z": -0.25,
            "thermal_z": 0.95,
            "mechanical_z": 0.0,
            "peer_percentile": 0.98,
            "env_explains": 0.04,
            "persistence": 0.58,
            "growth_rate": 0.55,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.94,
        },
    ),
    # 3. CARE Farm A: Transformer Failure (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-A-068",
        source_dataset="CARE to Compare — Wind Farm A",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 68",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-A03",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="transformer",
        fault_mode="High-voltage transformer phase L3 overheating and breakdown",
        timestamp="2015-07-29T13:20:00+00:00",
        closed_at="2015-08-12T13:10:00+00:00",
        observed_pattern="Phase L3 temperature rose to 125.0°C; Phase L2 reached 117.0°C; extreme 3-phase thermal unbalance followed by protective trip.",
        expected_behavior="Symmetrical phase temperatures below 85°C in pad-mount HV transformer.",
        maintenance_action="High-voltage transformer unit replacement.",
        outcome="Confirmed transformer failure; 14-day complete shutdown.",
        lead_time_days=8.0,
        repair_cost_inr=1_850_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Transformer DGA gas analysis not logged in SCADA."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Transformer phase temperatures (sensor_38_avg, 39_avg, 40_avg), timestamps, label 'Transformer failure'.",
            what_is_inferred="Severe inter-phase imbalance residual.",
            what_remains_unknown="Specific winding turn-to-turn fault location.",
            what_source_proves="Real catastrophic transformer failure requiring unit swap.",
            what_source_does_not_prove="Does not prove partial discharge onset timing.",
        ),
        signals={"trans_l1_temp_c": 94.0, "trans_l2_temp_c": 117.0, "trans_l3_temp_c": 125.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 22.1},
        residuals={"thermal_z": 4.2, "power_z": -1.8, "mechanical_z": None},
        signature={
            "power_z": -0.40,
            "thermal_z": 0.90,
            "mechanical_z": 0.0,
            "peer_percentile": 0.95,
            "env_explains": 0.06,
            "persistence": 0.62,
            "growth_rate": 0.48,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.91,
        },
    ),
    # 4. CARE Farm A: Hydraulic Group Failure (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-A-022",
        source_dataset="CARE to Compare — Wind Farm A",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 22",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-A04",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="hydraulic_group",
        fault_mode="Hydraulic pump / oil overheating and pressure loss",
        timestamp="2021-08-11T09:50:00+00:00",
        closed_at="2021-08-18T10:00:00+00:00",
        observed_pattern="Hydraulic oil temperature (sensor_41_avg) rose from 35.9°C to 49.0°C with persistent pressure loss alarms.",
        expected_behavior="Hydraulic oil temperature stable at 30-38°C under continuous pitch duty.",
        maintenance_action="Hydraulic pump service, seal replacement, and oil top-up.",
        outcome="Confirmed hydraulic system failure; restored to service in 7 days.",
        lead_time_days=4.0,
        repair_cost_inr=320_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Specific valve/accumulator part numbers not listed in CARE metadata."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Hydraulic oil temp (sensor_41_avg), timestamps, label 'Hydraulic group'.",
            what_is_inferred="Thermal residual on auxiliary hydraulic loop.",
            what_remains_unknown="Exact leak volume or internal bypass rate.",
            what_source_proves="Real hydraulic group failure requiring maintenance intervention.",
            what_source_does_not_prove="Does not prove whether proportional valve or pump wore out first.",
        ),
        signals={"hydraulic_oil_temp_c": 49.0, "ambient_temp_c": 18.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 18.0},
        residuals={"thermal_z": 2.2, "power_z": -0.6, "mechanical_z": None},
        signature={
            "power_z": -0.15,
            "thermal_z": 0.52,
            "mechanical_z": 0.0,
            "peer_percentile": 0.82,
            "env_explains": 0.12,
            "persistence": 0.50,
            "growth_rate": 0.30,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.68,
        },
    ),
    # 5. CARE Farm B: Rotor Bearing Damage (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-B-053",
        source_dataset="CARE to Compare — Wind Farm B",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 53",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-B01",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="rotor_bearing",
        fault_mode="Main rotor shaft bearing 2 mechanical damage",
        timestamp="2019-12-27T16:40:00+00:00",
        closed_at="2020-02-07T16:30:00+00:00",
        observed_pattern="Persistent abnormal thermal friction on main rotor bearing 2 leading to emergency standstill.",
        expected_behavior="Rotor bearing temperature in thermal equilibrium with ambient wind stream.",
        maintenance_action="Main bearing replacement requiring mobile crane mobilization.",
        outcome="Confirmed bearing damage; extended 42-day standstill.",
        lead_time_days=18.0,
        repair_cost_inr=2_100_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Farm B sensor channels are anonymised IDs; year timestamps are shifted."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Timestamps, author label 'Rotor Bearing 2 - Damage', standstill duration.",
            what_is_inferred="Long-term thermal creep on slow-speed shaft bearing.",
            what_remains_unknown="Raw vibration velocity measurements.",
            what_source_proves="Real catastrophic main rotor bearing failure.",
            what_source_does_not_prove="Does not prove raceway spall depth before trip.",
        ),
        signals={"rotor_speed_rpm": 9.2, "bearing_temp_c": 64.0},
        operating_regime={"rated_power_kw": 2000.0},
        environment={"ambient_temp_c": 5.0},
        residuals={"thermal_z": 3.6, "power_z": -2.1, "mechanical_z": None},
        signature={
            "power_z": -0.55,
            "thermal_z": 0.78,
            "mechanical_z": 0.45,
            "peer_percentile": 0.96,
            "env_explains": 0.02,
            "persistence": 0.88,
            "growth_rate": 0.22,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.92,
        },
    ),
    # 6. CARE Farm C: Converter Fuse Failure (Confirmed)
    RealHistoricalRecord(
        case_id="REAL-CARE-C-081",
        source_dataset="CARE to Compare — Wind Farm C",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 81",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-C01",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_VERIFIED_EVENT,
        component="power_converter",
        fault_mode="Converter filter supply fuse failure",
        timestamp="2019-11-17T01:30:00+00:00",
        closed_at="2019-11-19T14:00:00+00:00",
        observed_pattern="Immediate step drop in active generation from 1850 kW to 0 kW despite 9.2 m/s steady wind; converter disconnected.",
        expected_behavior="Continuous power generation matching wind speed power curve.",
        maintenance_action="Fuse filter supply replacement in converter cabinet.",
        outcome="Confirmed electrical component failure; turbine returned to production in 2 days.",
        lead_time_days=0.5,
        repair_cost_inr=85_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Farm C has 957 columns; anonymised sensor labels."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Timestamps, author label 'Converter Failure: Fuse Filter Supply', active power drop.",
            what_is_inferred="Step changepoint detection firing instantly on generation residual.",
            what_remains_unknown="Oscilloscope waveform of electrical transient causing fuse to blow.",
            what_source_proves="Real converter component failure (blown fuse).",
            what_source_does_not_prove="Does not prove whether grid voltage spike triggered the fuse blow.",
        ),
        signals={"power_kw": 0.0, "wind_speed_ms": 9.2},
        operating_regime={"rated_power_kw": 2000.0},
        environment={"ambient_temp_c": 8.0},
        residuals={"thermal_z": 0.05, "power_z": -4.5, "mechanical_z": None},
        signature={
            "power_z": -0.92,
            "thermal_z": 0.05,
            "mechanical_z": 0.0,
            "peer_percentile": 0.90,
            "env_explains": 0.0,
            "persistence": 0.25,
            "growth_rate": 0.85,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.88,
        },
    ),
    # 7. Kelmarsh: Operational Converter Trip (Code 3000)
    RealHistoricalRecord(
        case_id="REAL-KEL-1-FORCED-3000",
        source_dataset="Kelmarsh Wind Farm 2019",
        source_reference="Zenodo 10.5281/zenodo.5841834, Status_Kelmarsh_1 line 634",
        license="CC-BY-4.0",
        asset_id="Kelmarsh-1",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_OPERATIONAL_EVENT,
        component="power_converter",
        fault_mode="Operational trip: Frequency converter not ready (Code 3000)",
        timestamp="2019-11-05T15:58:41+00:00",
        closed_at="2019-11-05T16:02:41+00:00",
        observed_pattern="4-minute operational stop; power dropped to 0 kW while wind was 7.8 m/s; zero thermal anomaly.",
        expected_behavior="Continuous grid synchronization.",
        maintenance_action="Automated control reset; zero technician intervention or hardware replacement.",
        outcome="Restored automatically to Full Performance in 4 minutes without hardware replacement.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="SCADA_STATUS_LOG_GREENBYTE",
        limitations=[
            "Status event only, NOT a component failure.",
            "Greenbyte status log does not record inverter gate driver internal telemetry.",
        ],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Greenbyte status code 3000, 4-minute duration, timestamp, turbine ID Kelmarsh-1.",
            what_is_inferred="Operational state transition from SCADA.",
            what_remains_unknown="Specific electrical grid transient causing temporary unreadiness.",
            what_source_proves="An operational forced outage occurred.",
            what_source_does_not_prove="Does NOT prove component failure or hardware degradation. Must remain OPERATIONAL_EVENT!",
        ),
        signals={"power_kw": 0.0, "wind_speed_ms": 7.8, "rotor_rpm": 0.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 9.4},
        residuals={"thermal_z": 0.0, "power_z": -3.8, "mechanical_z": -2.5},
        signature={
            "power_z": -0.75,
            "thermal_z": 0.0,
            "mechanical_z": -0.30,
            "peer_percentile": 0.65,
            "env_explains": 0.05,
            "persistence": 0.08,
            "growth_rate": 0.80,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.52,
        },
    ),
    # 8. Kelmarsh: Operational Fan Overload (Code 2550)
    RealHistoricalRecord(
        case_id="REAL-KEL-1-FORCED-2550",
        source_dataset="Kelmarsh Wind Farm 2019",
        source_reference="Zenodo 10.5281/zenodo.5841834, Status_Kelmarsh_1 line 1240",
        license="CC-BY-4.0",
        asset_id="Kelmarsh-1",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_OPERATIONAL_EVENT,
        component="cooling_system",
        fault_mode="Auxiliary overload: Generator cooling fan 1 thermal protection trip (Code 2550)",
        timestamp="2019-11-11T14:31:32+00:00",
        closed_at="2019-11-11T14:45:32+00:00",
        observed_pattern="Generator fan current overload trip during high wind run; 14-minute forced cooldown stop.",
        expected_behavior="Auxiliary fan continuous ventilation within rated current.",
        maintenance_action="Protective thermal reset; returned to operation upon thermal recovery.",
        outcome="Operational protection trip cleared; full operation resumed.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="SCADA_STATUS_LOG_GREENBYTE",
        limitations=["Protection trip only; no permanent hardware damage occurred; not a component failure."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Greenbyte code 2550, duration 14 minutes, message 'Overload generator fan 1'.",
            what_is_inferred="Moderate thermal accumulation in generator compartment.",
            what_remains_unknown="Whether air filter had partial dust loading.",
            what_source_proves="An operational thermal protection stop occurred.",
            what_source_does_not_prove="Does not prove generator or fan motor failure.",
        ),
        signals={"power_kw": 0.0, "wind_speed_ms": 11.2, "generator_temp_c": 72.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 8.1},
        residuals={"thermal_z": 2.4, "power_z": -2.8, "mechanical_z": 0.1},
        signature={
            "power_z": -0.58,
            "thermal_z": 0.48,
            "mechanical_z": 0.0,
            "peer_percentile": 0.75,
            "env_explains": 0.10,
            "persistence": 0.15,
            "growth_rate": 0.60,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.62,
        },
    ),
    # 9. Kelmarsh: Scheduled Maintenance On-Site (Code 20)
    RealHistoricalRecord(
        case_id="REAL-KEL-1-MAINT-0020",
        source_dataset="Kelmarsh Wind Farm 2019",
        source_reference="Zenodo 10.5281/zenodo.5841834, Status_Kelmarsh_1 line 1225",
        license="CC-BY-4.0",
        asset_id="Kelmarsh-1",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_MAINTENANCE_EVENT,
        component="general_turbine",
        fault_mode="Scheduled on-site maintenance / service stop (Code 20)",
        timestamp="2019-11-11T12:50:59+00:00",
        closed_at="2019-11-11T13:18:59+00:00",
        observed_pattern="Planned on-site manual stop; blade pitching to 90 degrees; zero generation for 28 minutes while wind speed was 8.2 m/s.",
        expected_behavior="Normal automatic operation.",
        maintenance_action="On-site technician inspection / scheduled maintenance protocol.",
        outcome="Maintenance completed; returned to service.",
        lead_time_days=None,
        repair_cost_inr=25_000,
        evidence_quality="SCADA_STATUS_LOG_GREENBYTE",
        limitations=["Specific technician service report details not contained in Greenbyte export."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Greenbyte code 20, IEC category 'Scheduled Maintenance', duration 28 minutes.",
            what_is_inferred="Routine scheduled inspection stop.",
            what_remains_unknown="Tasks executed by technicians during the 28-minute interval.",
            what_source_proves="A scheduled maintenance event took place.",
            what_source_does_not_prove="Does not prove any fault or defect was present.",
        ),
        signals={"power_kw": 0.0, "pitch_angle_deg": 90.0, "rotor_rpm": 0.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 7.5},
        residuals={"thermal_z": -0.5, "power_z": -3.5, "mechanical_z": -3.0},
        signature={
            "power_z": -0.70,
            "thermal_z": -0.10,
            "mechanical_z": -0.60,
            "peer_percentile": 0.70,
            "env_explains": 0.0,
            "persistence": 0.18,
            "growth_rate": 0.75,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.45,
        },
    ),
    # 10. Kelmarsh: Out of Environmental Spec Low Wind (Code 10)
    RealHistoricalRecord(
        case_id="REAL-KEL-1-ENV-0010",
        source_dataset="Kelmarsh Wind Farm 2019",
        source_reference="Zenodo 10.5281/zenodo.5841834, Status_Kelmarsh_1 line 23",
        license="CC-BY-4.0",
        asset_id="Kelmarsh-1",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.ENVIRONMENTAL_EVENT,
        component="environment",
        fault_mode="Atmospheric standstill: Wind speed below cut-in (Code 10)",
        timestamp="2019-01-02T11:41:32+00:00",
        closed_at="2019-01-02T11:42:20+00:00",
        observed_pattern="Zero generation during calm weather window (wind speed 2.1 m/s < cut-in threshold 3.0 m/s); peer turbines all idling.",
        expected_behavior="Standby / idling when wind < cut-in threshold.",
        maintenance_action="None (automated atmospheric control logic).",
        outcome="Automatic restart upon wind speed recovery.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="SCADA_STATUS_LOG_GREENBYTE",
        limitations=["Purely environmental event, zero equipment degradation."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Greenbyte code 10, IEC category 'Out of Environmental Specification', wind speed 2.1 m/s.",
            what_is_inferred="Normal cut-in control policy.",
            what_remains_unknown="Micro-scale turbulence intensity.",
            what_source_proves="An environmental standstill occurred due to low wind.",
            what_source_does_not_prove="Does NOT prove any machine defect.",
        ),
        signals={"power_kw": 0.0, "wind_speed_ms": 2.1, "rotor_rpm": 0.0},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"wind_speed_ms": 2.1, "ambient_temp_c": 4.2},
        residuals={"thermal_z": 0.0, "power_z": 0.0, "mechanical_z": 0.0},
        signature={
            "power_z": 0.0,
            "thermal_z": 0.0,
            "mechanical_z": 0.0,
            "peer_percentile": 0.50,
            "env_explains": 0.98,
            "persistence": 0.10,
            "growth_rate": 0.05,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.05,
        },
    ),
    # 11. PVDAQ System 34: Midday Inverter Operational Outage
    RealHistoricalRecord(
        case_id="REAL-PVDAQ-034-OUTAGE",
        source_dataset="NREL PVDAQ OEDI — System 34",
        source_reference="NREL OEDI PVDAQ System 34 (Andre Agassi Bldg A, Las Vegas NV)",
        license="Public Domain / NREL OEDI",
        asset_id="PVDAQ-34",
        asset_type=AssetType.SOLAR_INVERTER,
        event_class=RealEventClass.REAL_OPERATIONAL_EVENT,
        component="inverter",
        fault_mode="Operational inverter trip during midday solar peak",
        timestamp="2019-06-14T12:30:00+00:00",
        closed_at="2019-06-14T15:30:00+00:00",
        observed_pattern="Midday generation drop to 0.0 kW while plane-of-array irradiance was 852.4 W/m² and module temperature was 54.1°C; 3-hour outage.",
        expected_behavior="AC generation proportional to POA irradiance (~180 kW).",
        maintenance_action="UNKNOWN (inverter breaker trip / grid interface trip reset).",
        outcome="Reconnected and resumed normal tracking at 15:30 UTC.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="PRIMARY_PVDAQ_OEDI_SCADA",
        limitations=[
            "No utility or technician work order available in public PVDAQ release.",
            "Classified OPERATIONAL_EVENT, NOT component failure.",
        ],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="POA irradiance 852 W/m², AC power 0.0 kW, module temp 54°C, 3h duration.",
            what_is_inferred="Inverter disconnection or protection trip.",
            what_remains_unknown="Exact trip code or whether manual breaker reset was required.",
            what_source_proves="A real solar generation outage occurred during peak irradiance.",
            what_source_does_not_prove="Does not prove permanent inverter damage or component failure.",
        ),
        signals={"poa_wm2": 852.4, "ac_power_kw": 0.0, "module_temp_c": 54.1},
        operating_regime={"dc_capacity_kw": 240.0},
        environment={"poa_wm2": 852.4, "ambient_temp_c": 38.0},
        residuals={"power_z": -4.2, "thermal_z": 0.15, "mechanical_z": None},
        signature={
            "power_z": -0.84,
            "thermal_z": 0.15,
            "mechanical_z": 0.0,
            "peer_percentile": 0.92,
            "env_explains": 0.02,
            "persistence": 0.32,
            "growth_rate": 0.70,
            "step_change": 1.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.82,
        },
    ),
    # 12. PVDAQ System 1283: Inverter Saturation / Clipping
    RealHistoricalRecord(
        case_id="REAL-PVDAQ-1283-CLIPPING",
        source_dataset="NREL PVDAQ OEDI — System 1283",
        source_reference="NREL OEDI PVDAQ System 1283 (NREL RSF II, Golden CO)",
        license="Public Domain / NREL OEDI",
        asset_id="PVDAQ-1283",
        asset_type=AssetType.SOLAR_INVERTER,
        event_class=RealEventClass.ENVIRONMENTAL_EVENT,
        component="inverter",
        fault_mode="Inverter saturation / power clipping under clear-sky summer peak",
        timestamp="2019-07-10T12:00:00+00:00",
        closed_at="2019-07-10T14:00:00+00:00",
        observed_pattern="Flat power output plateau at inverter nameplate capacity while POA irradiance rose above 980 W/m².",
        expected_behavior="Designed saturation behavior where DC array capacity exceeds inverter rating.",
        maintenance_action="None (designed operational behavior).",
        outcome="Normal operation; generation returned to tracking slope once irradiance decreased.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="PRIMARY_PVDAQ_OEDI_SCADA",
        limitations=["System 1283 has net-meter semantics; clipping is designed behaviour, not a fault."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="POA irradiance >980 W/m², AC power clipped at inverter threshold, module temp 58°C.",
            what_is_inferred="Normal inverter clipping curve.",
            what_remains_unknown="DC string-level currents (channel degenerate in 1283).",
            what_source_proves="Designed inverter clipping occurred under peak irradiance.",
            what_source_does_not_prove="Does NOT prove derating or equipment fault.",
        ),
        signals={"poa_wm2": 985.0, "ac_power_kw": 405.0, "module_temp_c": 58.2},
        operating_regime={"dc_capacity_kw": 498.0},
        environment={"poa_wm2": 985.0, "ambient_temp_c": 31.0},
        residuals={"power_z": -0.8, "thermal_z": 0.4, "mechanical_z": None},
        signature={
            "power_z": -0.16,
            "thermal_z": 0.12,
            "mechanical_z": 0.0,
            "peer_percentile": 0.55,
            "env_explains": 0.85,
            "persistence": 0.20,
            "growth_rate": 0.10,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.22,
        },
    ),
    # 13. CARE Farm C: Cooling Water Valve Misposition (Human error / maintenance)
    RealHistoricalRecord(
        case_id="REAL-CARE-C-044",
        source_dataset="CARE to Compare — Wind Farm C",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 44",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-C02",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_MAINTENANCE_EVENT,
        component="cooling_system",
        fault_mode="Post-service human error: Cooling water valve left in wrong position",
        timestamp="2016-08-03T14:00:00+00:00",
        closed_at="2016-10-08T02:20:00+00:00",
        observed_pattern="Gradual thermal elevation in water cooling loop following maintenance intervention on 2016-08-05.",
        expected_behavior="Nominal differential temperature across heat exchanger.",
        maintenance_action="Manual correction of cooling valve position.",
        outcome="Resolved immediately upon manual correction of cooling valve.",
        lead_time_days=65.0,
        repair_cost_inr=15_000,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Maintenance human error, not an equipment wear failure."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="Author note: 'Valve in water cooling system was left in wrong position after maintenance actions'.",
            what_is_inferred="Slow thermal accumulation due to restricted coolant flow.",
            what_remains_unknown="Exact flow rate through secondary bypass.",
            what_source_proves="A maintenance-induced operational anomaly occurred.",
            what_source_does_not_prove="Does NOT prove component wear or degradation.",
        ),
        signals={"cooling_water_temp_c": 52.0, "ambient_temp_c": 21.0},
        operating_regime={"rated_power_kw": 2000.0},
        environment={"ambient_temp_c": 21.0},
        residuals={"thermal_z": 2.9, "power_z": -1.1, "mechanical_z": 0.0},
        signature={
            "power_z": -0.22,
            "thermal_z": 0.65,
            "mechanical_z": 0.0,
            "peer_percentile": 0.84,
            "env_explains": 0.10,
            "persistence": 0.78,
            "growth_rate": 0.18,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.71,
        },
    ),
    # 14. CARE Farm A: Labelled Healthy Baseline Period (Event 25)
    RealHistoricalRecord(
        case_id="REAL-CARE-A-025-NORM",
        source_dataset="CARE to Compare — Wind Farm A",
        source_reference="Zenodo 10.5281/zenodo.14006163, event_info.csv ID 25",
        license="CC-BY-SA-4.0",
        asset_id="CARE-WT-A05",
        asset_type=AssetType.WIND_TURBINE,
        event_class=RealEventClass.REAL_OPERATIONAL_EVENT,
        component="general_turbine",
        fault_mode="Labelled healthy baseline reference period",
        timestamp="2023-05-22T06:50:00+00:00",
        closed_at="2023-06-04T02:30:00+00:00",
        observed_pattern="Nominal SCADA tracking; thermal residuals within +/-0.3 sigma; power tracking reference power curve.",
        expected_behavior="Full Performance across all operating states.",
        maintenance_action="None (routine operation).",
        outcome="Healthy baseline operation without maintenance intervention.",
        lead_time_days=None,
        repair_cost_inr=0,
        evidence_quality="PRIMARY_CARE_BENCHMARK_EVENT",
        limitations=["Benchmark healthy reference period."],
        adjudication=RealCaseAdjudication(
            what_is_explicitly_known="CARE label 'normal', start/end timestamps, normal SCADA values.",
            what_is_inferred="Normal baseline distribution.",
            what_remains_unknown="Sub-threshold micro-disturbances.",
            what_source_proves="Normal commercial production was observed.",
            what_source_does_not_prove="Does not prove absence of future faults.",
        ),
        signals={"power_kw": 1820.0, "wind_speed_ms": 8.8, "hss_bearing_temp_c": 50.5},
        operating_regime={"rated_power_kw": 2050.0},
        environment={"ambient_temp_c": 15.0},
        residuals={"thermal_z": 0.1, "power_z": 0.0, "mechanical_z": 0.0},
        signature={
            "power_z": 0.02,
            "thermal_z": 0.04,
            "mechanical_z": 0.01,
            "peer_percentile": 0.48,
            "env_explains": 0.0,
            "persistence": 0.0,
            "growth_rate": 0.0,
            "step_change": 0.0,
            "soiling_loss": 0.0,
            "anomaly_score": 0.06,
        },
    ),
]


def get_real_cases() -> list[Case]:
    """Return all adjudicated real cases converted to Case dataclass format."""
    return [rec.to_case() for rec in REAL_RECORDS]


REAL_CASES = get_real_cases()


def get_real_case_records() -> list[RealHistoricalRecord]:
    """Return raw high-fidelity real historical records."""
    return list(REAL_RECORDS)
