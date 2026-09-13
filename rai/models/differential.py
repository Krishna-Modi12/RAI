"""Counterevidence and Differential Diagnosis Engine for RAI.

Formulates competing hypotheses for observed anomalies and systematically evaluates
active counterevidence to rule alternatives IN or OUT before asserting an equipment fault.

Diagnostic Invariants:
1. Never assert an isolated mechanical component fault if fleet-wide peer consensus or
   environmental transients explain the anomaly (rules out false positives).
2. Never attribute sudden step-changes to gradual environmental phenomena (e.g. soiling
   cannot cause an instantaneous step change; rules out soiling for string outages).
3. If counterevidence cannot decisively separate two competing explanations (e.g. bearing
   breakdown vs cooling loop failure), output COMPETING_HYPOTHESES and abstain from single
   diagnosis rather than guessing.
"""

from __future__ import annotations

from rai.schemas import (
    AssetType,
    DiagnosticHypothesis,
    DifferentialDiagnosisVerdict,
    DifferentialStatus,
    EvidencePacket,
    HypothesisStatus,
    OperatingState,
    PeerVerdict,
    SensorHealth,
)


def evaluate_differential_diagnosis(packet: EvidencePacket) -> DifferentialDiagnosisVerdict:
    """Evaluate competing hypotheses and active counterevidence for the provided evidence packet."""
    if packet.asset_type is AssetType.WIND_TURBINE:
        return _evaluate_wind_differential(packet)
    elif packet.asset_type is AssetType.SOLAR_INVERTER:
        return _evaluate_solar_differential(packet)
    else:
        return DifferentialDiagnosisVerdict(
            status=DifferentialStatus.NO_PLAUSIBLE_HYPOTHESIS,
            abstention_rationale="Unsupported asset type for differential diagnosis.",
        )


# ---------------------------------------------------------------------------
# Wind Turbine Differential Evaluation
# ---------------------------------------------------------------------------


def _evaluate_wind_differential(packet: EvidencePacket) -> DifferentialDiagnosisVerdict:
    hypotheses: list[DiagnosticHypothesis] = []
    counterevidence_summary: list[str] = []

    anomaly = packet.anomaly
    sig_map = {s.name: s for s in anomaly.signals}

    vib = sig_map.get("drivetrain_vibration_mms")
    oil_temp = sig_map.get("gearbox_oil_temp_c")
    gen_temp = sig_map.get("generator_winding_temp_c")
    main_bearing = sig_map.get("main_bearing_temp_c")
    power = sig_map.get("power_kw")
    rotor_rpm = sig_map.get("rotor_rpm")

    vib_z = vib.z_score if vib and vib.z_score is not None else 0.0
    oil_z = oil_temp.z_score if oil_temp and oil_temp.z_score is not None else 0.0
    gen_z = gen_temp.z_score if gen_temp and gen_temp.z_score is not None else 0.0
    mb_z = main_bearing.z_score if main_bearing and main_bearing.z_score is not None else 0.0
    power_z = power.z_score if power and power.z_score is not None else 0.0
    rpm_z = rotor_rpm.z_score if rotor_rpm and rotor_rpm.z_score is not None else 0.0

    step_change = any(d.detector == "changepoint" and d.fired for d in anomaly.detectors)
    env = packet.environment
    peers = packet.peers

    # --- Domain A: Drivetrain Thermal / Mechanical Cluster ---
    has_drivetrain_heat = oil_z > 1.8 or gen_z > 1.8 or mb_z > 1.8 or vib_z > 1.8

    if has_drivetrain_heat:
        # Hypothesis 1: Gearbox Bearing Mechanical Degradation
        gearbox_supp: list[str] = []
        gearbox_counter: list[str] = []
        gearbox_status = HypothesisStatus.CONTENDING

        if oil_z > 1.8:
            gearbox_supp.append(f"Gearbox oil temperature elevated (+{oil_z:.1f}σ)")
        if vib_z > 1.8:
            gearbox_supp.append(f"Drivetrain vibration corroborated (+{vib_z:.1f}σ)")

        # Counterevidence against isolated gearbox bearing
        if env and env.sensor_health is not None and env.sensor_health is not SensorHealth.OK:
            gearbox_counter.append(f"Sensor validation failed ({env.sensor_health.value}); telemetry deviation is a measurement artifact")
            gearbox_status = HypothesisStatus.RULED_OUT
        elif env and (env.curtailment_detected or env.operating_state is OperatingState.CURTAILED) and abs(vib_z) < 1.5:
            gearbox_counter.append("Operating in curtailed state without significant mechanical vibration")
            gearbox_status = HypothesisStatus.RULED_OUT
        elif vib is not None and abs(vib_z) < 0.8 and oil_z > 2.0:
            gearbox_counter.append(f"Drivetrain vibration normal ({vib_z:.2f}σ); isolated mechanical spalling typically induces vibration")
        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            gearbox_counter.append("Peer turbines show fleet-wide thermal elevation; asset-specific mechanical defect ruled out")
            gearbox_status = HypothesisStatus.RULED_OUT
        elif vib_z > 2.0 and oil_z > 2.0 and not (env and env.sensor_health is not None and env.sensor_health is not SensorHealth.OK):
            gearbox_status = HypothesisStatus.SUPPORTED
        elif oil_z > 2.0 and abs(vib_z) < 0.8 and gen_z > 2.0:
            gearbox_counter.append("Both gearbox and generator temperatures elevated symmetrically; points to cooling failure rather than isolated gearbox")
            gearbox_status = HypothesisStatus.RULED_OUT

        hypotheses.append(
            DiagnosticHypothesis(
                name="gearbox_bearing_degradation",
                component="gearbox",
                category="equipment_fault",
                description="Mechanical fatigue / spalling of high-speed shaft or planetary bearings",
                status=gearbox_status,
                supporting_evidence=gearbox_supp,
                counterevidence=gearbox_counter,
                confidence_delta=0.15 if gearbox_status is HypothesisStatus.SUPPORTED else (-0.20 if gearbox_status is HypothesisStatus.RULED_OUT else 0.0),
            )
        )

        # Hypothesis 2: Cooling Circuit / Radiator Restriction
        cooling_supp: list[str] = []
        cooling_counter: list[str] = []
        cooling_status = HypothesisStatus.CONTENDING

        if oil_z > 1.8 and gen_z > 1.8:
            cooling_supp.append(f"Multi-component thermal escalation (Gearbox +{oil_z:.1f}σ, Generator +{gen_z:.1f}σ)")
        if vib is not None and abs(vib_z) < 1.0:
            cooling_supp.append("Vibration normal, consistent with non-mechanical thermal dissipation failure")

        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            cooling_counter.append("Fleet-wide thermal elevation rules out isolated cooling circuit failure")
            cooling_status = HypothesisStatus.RULED_OUT
        elif oil_z > 2.5 and gen_z < 0.5:
            cooling_counter.append("Generator winding temperature is nominal; common cooling loop failure would affect both assemblies")
            cooling_status = HypothesisStatus.RULED_OUT
        elif vib_z > 2.5:
            cooling_counter.append("Severe vibration (+2.5σ) indicates active mechanical breakdown rather than pure cooling restriction")
            cooling_status = HypothesisStatus.RULED_OUT
        elif oil_z > 1.8 and gen_z > 1.8 and abs(vib_z) < 1.0:
            cooling_status = HypothesisStatus.SUPPORTED

        hypotheses.append(
            DiagnosticHypothesis(
                name="cooling_circuit_failure",
                component="cooling_system",
                category="equipment_fault",
                description="Radiator blockage, cooling fan failure, or heat exchanger valve fault",
                status=cooling_status,
                supporting_evidence=cooling_supp,
                counterevidence=cooling_counter,
                confidence_delta=0.12 if cooling_status is HypothesisStatus.SUPPORTED else (-0.15 if cooling_status is HypothesisStatus.RULED_OUT else 0.0),
            )
        )

        # Hypothesis 3: Ambient Heatwave / Atmospheric Thermal Load
        heat_supp: list[str] = []
        heat_counter: list[str] = []
        heat_status = HypothesisStatus.CONTENDING

        if env and env.explains_fraction > 0.60:
            heat_supp.append(f"Environment explains {env.explains_fraction:.0%} of thermal rise")
        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            heat_supp.append(f"Fleet-wide phenomenon across all {peers.n_peers} peers")
            heat_status = HypothesisStatus.SUPPORTED
        elif peers and peers.verdict is PeerVerdict.ASSET_SPECIFIC:
            heat_counter.append(f"Asset-specific anomaly ({peers.n_peers} peer turbines at same site operate with normal thermal levels)")
            heat_status = HypothesisStatus.RULED_OUT
        elif env and env.explains_fraction < 0.20:
            heat_counter.append(f"Weather accounts for only {env.explains_fraction:.0%} of thermal deviation")
            heat_status = HypothesisStatus.RULED_OUT
        elif env and env.explains_fraction > 0.60:
            heat_status = HypothesisStatus.SUPPORTED
        else:
            heat_status = HypothesisStatus.UNSUPPORTED

        hypotheses.append(
            DiagnosticHypothesis(
                name="ambient_heatwave",
                component="environment",
                category="environmental",
                description="Extreme ambient temperature elevating operating equilibrium",
                status=heat_status,
                supporting_evidence=heat_supp,
                counterevidence=heat_counter,
                confidence_delta=0.20 if heat_status is HypothesisStatus.SUPPORTED else -0.20,
            )
        )

    # --- Domain B: Aerodynamic / Power Deficit Cluster ---
    has_power_deficit = power_z < -1.8 or rpm_z < -1.8

    if has_power_deficit:
        # Hypothesis 4: Grid Curtailment / Dispatch Derate
        curtail_supp: list[str] = []
        curtail_counter: list[str] = []
        curtail_status = HypothesisStatus.CONTENDING

        if env and env.curtailment_detected:
            curtail_supp.append("Grid curtailment active flag confirmed by environment provider")
            curtail_status = HypothesisStatus.SUPPORTED
        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            curtail_supp.append("Fleet-wide power ceiling observed across peer turbines")
            curtail_status = HypothesisStatus.SUPPORTED

        if env and (env.curtailment_detected or env.operating_state is OperatingState.CURTAILED):
            curtail_supp.append("Grid curtailment active flag or curtailed operating state confirmed")
            curtail_status = HypothesisStatus.SUPPORTED
        elif env and not env.curtailment_detected and env.operating_state is not OperatingState.CURTAILED and peers and peers.verdict is PeerVerdict.ASSET_SPECIFIC:
            curtail_counter.append("Zero curtailment flag and peer turbines generating full unconstrained power")
            curtail_status = HypothesisStatus.RULED_OUT

        hypotheses.append(
            DiagnosticHypothesis(
                name="grid_curtailment",
                component="grid",
                category="operational_state",
                description="Utility dispatch setpoint limit or grid frequency regulation derating",
                status=curtail_status,
                supporting_evidence=curtail_supp,
                counterevidence=curtail_counter,
                confidence_delta=0.20 if curtail_status is HypothesisStatus.SUPPORTED else -0.20,
            )
        )

        # Hypothesis 5: Pitch System Calibration Drift / Actuator Misalignment
        pitch_supp: list[str] = []
        pitch_counter: list[str] = []
        pitch_status = HypothesisStatus.CONTENDING

        if power_z < -1.8 and not has_drivetrain_heat:
            pitch_supp.append("Aerodynamic shortfall in the absence of drivetrain thermal anomalies")
        if step_change:
            pitch_supp.append("Discrete step-change in power output indicates sudden control setpoint offset")

        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            pitch_counter.append("Fleet-wide deficit rules out isolated single-turbine pitch calibration drift")
            pitch_status = HypothesisStatus.RULED_OUT
        elif env and (env.curtailment_detected or env.operating_state is OperatingState.CURTAILED):
            pitch_counter.append("External curtailment accounts for aerodynamic derate")
            pitch_status = HypothesisStatus.RULED_OUT
        elif has_drivetrain_heat or (vib_z > 1.8 and oil_z > 1.8):
            pitch_counter.append(
                f"Drivetrain mechanical/thermal breakdown present (oil +{oil_z:.1f}σ, vib +{vib_z:.1f}σ); "
                f"power deficit is secondary to mechanical drag, not aerodynamic pitch error"
            )
            pitch_status = HypothesisStatus.RULED_OUT
        elif power_z < -1.8 and peers and peers.verdict is PeerVerdict.ASSET_SPECIFIC and not (env and env.curtailment_detected):
            pitch_status = HypothesisStatus.SUPPORTED

        hypotheses.append(
            DiagnosticHypothesis(
                name="pitch_system_misalignment",
                component="pitch_system",
                category="equipment_fault",
                description="Blade pitch angle calibration offset or actuator positioning error",
                status=pitch_status,
                supporting_evidence=pitch_supp,
                counterevidence=pitch_counter,
                confidence_delta=0.15 if pitch_status is HypothesisStatus.SUPPORTED else -0.15,
            )
        )

        # Hypothesis 6: Aerodynamic Blade Degradation / Severe Soiling
        blade_supp: list[str] = []
        blade_counter: list[str] = []
        blade_status = HypothesisStatus.CONTENDING

        if not step_change and anomaly.persistence_hours >= 48:
            blade_supp.append(f"Gradual persistent power deficit sustained over {anomaly.persistence_hours:.0f} hours")

        if peers and peers.verdict is PeerVerdict.FLEET_WIDE:
            blade_counter.append("Fleet-wide power ceiling rules out single-turbine blade surface fouling")
            blade_status = HypothesisStatus.RULED_OUT
        elif step_change:
            blade_counter.append("Step-change detected by changepoint detector; surface fouling/icing accumulates progressively, not instantaneously")
            blade_status = HypothesisStatus.RULED_OUT
        elif has_drivetrain_heat or (vib_z > 1.8 and oil_z > 1.8):
            blade_counter.append("Drivetrain mechanical breakdown accounts for power loss")
            blade_status = HypothesisStatus.RULED_OUT
        elif anomaly.persistence_hours < 24:
            blade_status = HypothesisStatus.UNSUPPORTED

        hypotheses.append(
            DiagnosticHypothesis(
                name="blade_surface_degradation",
                component="blades",
                category="equipment_fault",
                description="Surface roughness, insect accumulation, leading-edge erosion, or light icing",
                status=blade_status,
                supporting_evidence=blade_supp,
                counterevidence=blade_counter,
                confidence_delta=0.10 if blade_status is HypothesisStatus.SUPPORTED else -0.10,
            )
        )

    # Hypothesis 7: Anemometer / Sensor Instrument Fault
    sensor_counter: list[str] = []
    sensor_supp: list[str] = []
    if env and env.sensor_health is not None and env.sensor_health is not SensorHealth.OK:
        sensor_supp.append(f"Sensor health validation flagged {env.sensor_health.value}")
        sensor_status = HypothesisStatus.SUPPORTED
    else:
        sensor_counter.append("Sensor health verified normal")
        sensor_status = HypothesisStatus.RULED_OUT

    hypotheses.append(
        DiagnosticHypothesis(
            name="anemometer_sensor_fault",
            component="anemometer",
            category="sensor",
            description="Wind speed anemometer or telemetry sensor failure/drift",
            status=sensor_status,
            supporting_evidence=sensor_supp,
            counterevidence=sensor_counter,
            confidence_delta=0.20 if sensor_status is HypothesisStatus.SUPPORTED else -0.15,
        )
    )

    # Compile counterevidence summaries
    for h in hypotheses:
        for c in h.counterevidence:
            counterevidence_summary.append(f"[{h.name}] {c}")

    return _synthesize_verdict(hypotheses, counterevidence_summary)


# ---------------------------------------------------------------------------
# Solar Inverter Differential Evaluation
# ---------------------------------------------------------------------------


def _evaluate_solar_differential(packet: EvidencePacket) -> DifferentialDiagnosisVerdict:
    hypotheses: list[DiagnosticHypothesis] = []
    counterevidence_summary: list[str] = []

    anomaly = packet.anomaly
    sig_map = {s.name: s for s in anomaly.signals}

    ac_pwr = sig_map.get("ac_power_kw")
    dc_pwr = sig_map.get("dc_power_kw")
    dc_curr = sig_map.get("dc_current_a")
    dc_volt = sig_map.get("dc_voltage_v")
    inv_temp = sig_map.get("inverter_temp_c")
    soiling_pct = packet.soiling.soiling_loss_pct if packet.soiling else None

    ac_z = ac_pwr.z_score if ac_pwr and ac_pwr.z_score is not None else 0.0
    dc_curr_z = dc_curr.z_score if dc_curr and dc_curr.z_score is not None else 0.0
    dc_volt_z = dc_volt.z_score if dc_volt and dc_volt.z_score is not None else 0.0
    inv_temp_z = inv_temp.z_score if inv_temp and inv_temp.z_score is not None else 0.0

    step_change = any(d.detector == "changepoint" and d.fired for d in anomaly.detectors)
    env = packet.environment
    peers = packet.peers

    # Hypothesis 1: Inverter Hardware Thermal Derate / Bridge Fault
    inv_supp: list[str] = []
    inv_counter: list[str] = []
    inv_status = HypothesisStatus.CONTENDING

    if inv_temp_z > 2.0:
        inv_supp.append(f"Inverter heatsink temperature elevated (+{inv_temp_z:.1f}σ)")
    if ac_z < -1.8:
        inv_supp.append(f"AC power generation deficit (+{abs(ac_z):.1f}σ)")

    if inv_temp is not None and abs(inv_temp_z) < 0.8:
        inv_counter.append(f"Inverter temperature is nominal ({inv_temp_z:.2f}σ); thermal derate ruled out")
        inv_status = HypothesisStatus.RULED_OUT
    elif inv_temp_z > 2.0 and ac_z < -1.8:
        inv_status = HypothesisStatus.SUPPORTED
    elif inv_temp is not None and inv_temp_z < 1.0:
        inv_counter.append("Inverter temperature within normal range; thermal derate ruled out")
        inv_status = HypothesisStatus.RULED_OUT
    elif soiling_pct and soiling_pct >= 4.0 and abs(inv_temp_z) < 1.5:
        inv_counter.append("Performance deficit explained by optical soiling; inverter temperature normal")
        inv_status = HypothesisStatus.RULED_OUT
    else:
        inv_status = HypothesisStatus.CONTENDING

    hypotheses.append(
        DiagnosticHypothesis(
            name="inverter_thermal_derate",
            component="inverter",
            category="equipment_fault",
            description="Inverter bridge thermal protection limiting AC power injection",
            status=inv_status,
            supporting_evidence=inv_supp,
            counterevidence=inv_counter,
            confidence_delta=0.15 if inv_status is HypothesisStatus.SUPPORTED else -0.15,
        )
    )

    # Hypothesis 2: DC String Outage / Blown Fuse
    string_supp: list[str] = []
    string_counter: list[str] = []
    string_status = HypothesisStatus.CONTENDING

    if dc_curr_z < -1.8 or (dc_pwr and (dc_pwr.z_score or 0) < -1.8):
        string_supp.append(f"DC current/power deficit ({dc_curr_z:.1f}σ)")
    if step_change:
        string_supp.append("Discrete step-change detected, characteristic of string fuse or disconnect trip")
    if dc_volt and abs(dc_volt_z) < 1.0 and dc_curr_z < -1.8:
        string_supp.append(f"DC bus voltage maintained ({dc_volt_z:.1f}σ) while current drops, indicating parallel string loss")

    if not step_change and soiling_pct and soiling_pct > 5.0:
        string_counter.append("Absence of step-change with gradual degradation aligns with soiling rather than discrete string outage")
        string_status = HypothesisStatus.RULED_OUT
    elif soiling_pct and soiling_pct >= 4.0 and dc_curr_z >= -1.0:
        string_counter.append("DC current within normal baseline; deficit is optical soiling rather than string outage")
        string_status = HypothesisStatus.RULED_OUT
    elif step_change and (dc_curr_z < -1.8 or ac_z < -1.8):
        string_status = HypothesisStatus.SUPPORTED
    elif not step_change and dc_curr_z >= -1.0:
        string_status = HypothesisStatus.UNSUPPORTED

    hypotheses.append(
        DiagnosticHypothesis(
            name="dc_string_outage",
            component="dc_string",
            category="equipment_fault",
            description="Open-circuit string, blown combiner fuse, or defective bypass diode",
            status=string_status,
            supporting_evidence=string_supp,
            counterevidence=string_counter,
            confidence_delta=0.18 if string_status is HypothesisStatus.SUPPORTED else -0.15,
        )
    )

    # Hypothesis 3: Recoverable Module Soiling
    soiling_supp: list[str] = []
    soiling_counter: list[str] = []
    soiling_status = HypothesisStatus.CONTENDING

    if soiling_pct and soiling_pct >= 4.0:
        soiling_supp.append(f"Estimated soiling loss of {soiling_pct:.1f}%")
        if packet.soiling and packet.soiling.days_since_rain:
            soiling_supp.append(f"{packet.soiling.days_since_rain:.0f} days since last rainfall event")

    if soiling_pct is None or soiling_pct < 3.0:
        soiling_counter.append("Estimated soiling loss is negligible (<3.0%)")
        soiling_status = HypothesisStatus.RULED_OUT
    elif inv_temp_z > 2.0:
        soiling_counter.append("Dominant inverter temperature elevation cannot be caused by optical soiling")
        soiling_status = HypothesisStatus.RULED_OUT
    elif step_change and (dc_curr_z < -1.8 or (dc_pwr and (dc_pwr.z_score or 0) < -1.8)):
        soiling_counter.append("Instantaneous step change in DC generation detected; soiling is an accumulative process and cannot cause sudden current drops")
        soiling_status = HypothesisStatus.RULED_OUT
    elif soiling_pct and soiling_pct >= 4.0:
        soiling_status = HypothesisStatus.SUPPORTED

    hypotheses.append(
        DiagnosticHypothesis(
            name="photovoltaic_soiling",
            component="soiling",
            category="environmental",
            description="Accumulation of atmospheric dust/particulates on module glass",
            status=soiling_status,
            supporting_evidence=soiling_supp,
            counterevidence=soiling_counter,
            confidence_delta=0.15 if soiling_status is HypothesisStatus.SUPPORTED else -0.15,
        )
    )

    # Hypothesis 4: Pyranometer / Reference Sensor Calibration Drift
    sensor_supp: list[str] = []
    sensor_counter: list[str] = []
    sensor_status = HypothesisStatus.CONTENDING

    if env and env.sensor_health is not SensorHealth.OK:
        sensor_supp.append(f"Environmental sensor status flagged as {env.sensor_health.value}")
        sensor_status = HypothesisStatus.SUPPORTED
    elif env and env.sensor_health is SensorHealth.OK:
        sensor_counter.append("Pyranometer sensor health verified OK")
        sensor_status = HypothesisStatus.RULED_OUT
    elif peers and peers.verdict is PeerVerdict.ASSET_SPECIFIC:
        sensor_counter.append("Pyranometer sensor health verified OK and peers track clear-sky expectation")
        sensor_status = HypothesisStatus.RULED_OUT
    else:
        sensor_status = HypothesisStatus.UNSUPPORTED

    hypotheses.append(
        DiagnosticHypothesis(
            name="pyranometer_drift",
            component="sensor",
            category="sensor",
            description="Irradiance sensor drift or soiling producing false performance ratio deficit",
            status=sensor_status,
            supporting_evidence=sensor_supp,
            counterevidence=sensor_counter,
            confidence_delta=0.15 if sensor_status is HypothesisStatus.SUPPORTED else -0.15,
        )
    )

    for h in hypotheses:
        for c in h.counterevidence:
            counterevidence_summary.append(f"[{h.name}] {c}")

    return _synthesize_verdict(hypotheses, counterevidence_summary)


# ---------------------------------------------------------------------------
# Verdict Synthesis & Abstention Logic
# ---------------------------------------------------------------------------


def _synthesize_verdict(
    hypotheses: list[DiagnosticHypothesis],
    counterevidence_summary: list[str],
) -> DifferentialDiagnosisVerdict:
    supported = [h for h in hypotheses if h.status is HypothesisStatus.SUPPORTED]
    contending = [h for h in hypotheses if h.status is HypothesisStatus.CONTENDING]

    # Exactly one hypothesis supported and all primary competitors ruled out or unsupported
    if len(supported) == 1 and len(contending) == 0:
        single = supported[0]
        if single.category == "equipment_fault":
            status = DifferentialStatus.RESOLVED_SINGLE_FAULT
        elif single.category == "operational_state":
            status = DifferentialStatus.RESOLVED_OPERATIONAL
        elif single.category == "environmental":
            status = DifferentialStatus.RESOLVED_ENVIRONMENTAL
        elif single.category == "sensor":
            status = DifferentialStatus.RESOLVED_SENSOR_ANOMALY
        else:
            status = DifferentialStatus.RESOLVED_SINGLE_FAULT

        return DifferentialDiagnosisVerdict(
            dominant_hypothesis=single.name,
            status=status,
            hypotheses=hypotheses,
            counterevidence_summary=counterevidence_summary,
            abstention_rationale=None,
        )

    # Exactly one hypothesis supported, but other plausible alternatives remain contending
    if len(supported) == 1 and len(contending) > 0:
        single = supported[0]
        contending_names = ", ".join(h.name for h in contending)
        return DifferentialDiagnosisVerdict(
            dominant_hypothesis=single.name,
            status=DifferentialStatus.COMPETING_HYPOTHESES,
            hypotheses=hypotheses,
            counterevidence_summary=counterevidence_summary,
            abstention_rationale=(
                f"Primary hypothesis '{single.name}' is supported, but alternative explanations "
                f"({contending_names}) cannot be ruled out by available telemetry. On-site inspection recommended."
            ),
        )

    # Multiple hypotheses supported
    if len(supported) > 1:
        supported_names = ", ".join(h.name for h in supported)
        return DifferentialDiagnosisVerdict(
            dominant_hypothesis=supported[0].name,
            status=DifferentialStatus.COMPETING_HYPOTHESES,
            hypotheses=hypotheses,
            counterevidence_summary=counterevidence_summary,
            abstention_rationale=(
                f"Multiple competing explanations are supported ({supported_names}). "
                "Available sensor channels are insufficient to isolate a single root cause without visual/field inspection."
            ),
        )

    # Zero hypotheses supported, but some are contending
    if len(contending) > 0:
        contending_names = ", ".join(h.name for h in contending)
        return DifferentialDiagnosisVerdict(
            dominant_hypothesis=contending[0].name,
            status=DifferentialStatus.COMPETING_HYPOTHESES,
            hypotheses=hypotheses,
            counterevidence_summary=counterevidence_summary,
            abstention_rationale=(
                f"No single hypothesis is decisively supported. Plausible competing explanations: {contending_names}. "
                "Abstaining from definitive equipment fault declaration."
            ),
        )

    # Nothing plausible
    return DifferentialDiagnosisVerdict(
        dominant_hypothesis=None,
        status=DifferentialStatus.NO_PLAUSIBLE_HYPOTHESIS,
        hypotheses=hypotheses,
        counterevidence_summary=counterevidence_summary,
        abstention_rationale="Observed anomaly pattern does not conform to known physical fault or operational signatures.",
    )
