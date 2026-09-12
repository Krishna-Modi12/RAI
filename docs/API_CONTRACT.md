# API Contract (frozen)

Single source of truth shared by `services/api/` and `web/`. Both sides implement this
independently; the integration step verifies them against each other. **Do not change a
shape here without updating both sides and `CHECKPOINT.md`.**

Base URL: `http://127.0.0.1:8000`. All endpoints under `/api`. All timestamps ISO-8601 UTC
with `Z`. Money in INR (plain numbers, no formatting). Power in kW. Energy in kWh.

Field values that have not been computed are `null` — never a placeholder number.
Frontend must render `null` as an explicit "not evaluated" state, never as `0`.

---

## Enumerations

```
asset_type      : "wind_turbine" | "solar_inverter"
risk_band       : "low" | "elevated" | "high" | "critical"
severity        : "informational" | "low" | "medium" | "high" | "critical"
operating_state : "normal" | "curtailed" | "derated" | "stopped" | "maintenance"
                | "below_cutin" | "above_cutout" | "night" | "unknown"
peer_verdict    : "asset_specific" | "fleet_wide" | "normal"
env_verdict     : "environmental" | "partial" | "not_environmental"
sensor_health   : "ok" | "suspect" | "failed"
```

---

## `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "data_as_of": "2026-09-12T06:40:00Z",
  "needle_available": false,
  "needle_detail": "weights not downloaded; deterministic reasoner active",
  "models_loaded": ["wind_expected_power", "solar_expected_power", "risk"],
  "assets": 42
}
```

## `GET /api/fleet`

```json
{
  "updated_at": "2026-09-12T06:40:00Z",
  "fleet_health": 87.4,
  "expected_yield_pct": 96.2,
  "assets_total": 42,
  "assets_at_risk": 3,
  "assets_offline": 1,
  "generation_kw": 21850.0,
  "expected_generation_kw": 22710.0,
  "availability_pct": 97.6,
  "revenue_at_risk_inr_per_day": 184000.0,
  "by_type": [
    {"asset_type": "wind_turbine",  "count": 18, "health": 86.1, "generation_kw": 19400.0},
    {"asset_type": "solar_inverter","count": 24, "health": 88.9, "generation_kw": 2450.0}
  ]
}
```

## `GET /api/fleet/priority`

Ranked action queue. Ordered by `revenue_at_risk_inr` × `risk_score`, descending.

```json
[
  {
    "asset_id": "WT-017",
    "name": "Turbine 17",
    "asset_type": "wind_turbine",
    "site": "Kutch Wind Farm",
    "headline": "Gearbox degradation signature",
    "component": "gearbox",
    "health_score": 58.2,
    "risk_score": 0.82,
    "risk_band": "high",
    "risk_window_days": [7, 21],
    "revenue_at_risk_inr": 155000.0,
    "recommended_action": "Inspect gearbox vibration and oil condition within 72 hours",
    "deadline_hours": 72,
    "requires_human_review": false,
    "dominant_signal": "drivetrain_vibration_mms"
  }
]
```

## `GET /api/assets`

```json
[
  {
    "asset_id": "WT-017", "name": "Turbine 17", "asset_type": "wind_turbine",
    "site": "Kutch Wind Farm", "peer_group": "kutch-row-b",
    "rated_power_kw": 2000.0,
    "health_score": 58.2, "risk_score": 0.82, "risk_band": "high",
    "anomaly_score": 0.91, "operating_state": "normal",
    "power_kw": 1284.0, "expected_power_kw": 1417.0, "capacity_factor": 0.64,
    "data_freshness_s": 14.0
  }
]
```

## `GET /api/assets/{asset_id}`

```json
{
  "asset": {
    "asset_id": "WT-017", "asset_type": "wind_turbine", "name": "Turbine 17",
    "site": "Kutch Wind Farm", "region": "Gujarat, India",
    "rated_power_kw": 2000.0, "commissioned": "2019-03-01",
    "peer_group": "kutch-row-b", "rotor_diameter_m": 92.0, "hub_height_m": 80.0
  },
  "state": {
    "as_of": "2026-09-12T06:40:00Z",
    "health_score": 58.2, "operating_state": "normal",
    "power_kw": 1284.0, "expected_power_kw": 1417.0, "capacity_factor": 0.64,
    "data_freshness_s": 14.0
  },
  "risk": {
    "risk_score": 0.82, "risk_band": "high", "horizon_days": 30,
    "risk_window_days": [7, 21], "calibration": "isotonic",
    "drivers": {"vibration_trend": 0.34, "thermal_residual": 0.27,
                "power_residual": 0.21, "persistence": 0.18}
  },
  "anomaly": {
    "anomaly_score": 0.91,
    "persistence_hours": 18.5,
    "first_seen": "2026-09-11T12:10:00Z",
    "change_point_at": "2026-09-11T11:40:00Z",
    "dominant_signal": "drivetrain_vibration_mms",
    "detectors": [
      {"detector": "residual_z", "score": 0.93, "threshold": 0.60, "fired": true,
       "detail": "gearbox_oil_temp_c z=4.1"},
      {"detector": "isolation_forest", "score": 0.78, "threshold": 0.60, "fired": true, "detail": null},
      {"detector": "changepoint", "score": 0.81, "threshold": 0.60, "fired": true,
       "detail": "step detected 2026-09-11T11:40Z"}
    ],
    "signals": [
      {"name": "drivetrain_vibration_mms", "unit": "mm/s", "actual": 4.62,
       "expected": 3.58, "residual": 1.04, "residual_pct": 29.1, "z_score": 3.4,
       "trend_per_day": 0.18, "trend_7d_per_day": 0.12, "baseline_sigma": 0.31}
    ]
  },
  "peers": {
    "peer_group": "kutch-row-b", "n_peers": 8,
    "asset_residual_pct": -9.4, "peer_median_residual_pct": -0.8,
    "deviation_percentile": 96.0, "verdict": "asset_specific",
    "note": "8 of 8 peers within normal band under identical wind conditions"
  },
  "environment": {
    "source": "simulated_site_met",
    "conditions": {"wind_speed_ms": 9.1, "wind_direction_deg": 248.0,
                   "ambient_temp_c": 31.2, "air_density": 1.161},
    "operating_state": "normal", "curtailment_detected": false,
    "sensor_health": "ok", "explains_fraction": 0.08,
    "verdict": "not_environmental",
    "note": "Wind conditions account for 8% of the observed deviation"
  },
  "soiling": null
}
```

For a solar asset, `soiling` is populated and wind-only signals are absent:

```json
{"soiling": {"soiling_ratio": 0.916, "soiling_loss_pct": 8.4,
             "soiling_rate_pct_per_day": 0.31, "days_since_cleaning": 27.0,
             "days_since_rain": 19.0, "rain_probability_48h": 0.23,
             "method": "kimber+pr_ratio"}}
```

## `GET /api/assets/{asset_id}/timeseries`

Query: `signal` (default `power_kw` / `ac_power_kw`), `hours` (default 168), `interval` optional.

```json
{
  "asset_id": "WT-017", "signal": "power_kw", "unit": "kW",
  "interval_min": 10,
  "points": [
    {"t": "2026-09-05T06:40:00Z", "actual": 1284.0, "expected": 1417.0,
     "lower": 1330.0, "upper": 1504.0, "residual_z": 3.4}
  ],
  "events": [
    {"t": "2026-09-11T11:40:00Z", "label": "Change point detected", "kind": "changepoint"},
    {"t": "2026-09-11T12:10:00Z", "label": "Anomaly threshold crossed", "kind": "alert"}
  ]
}
```

`kind` ∈ `"changepoint" | "alert" | "maintenance" | "curtailment" | "weather" | "repair"`.

## `GET /api/assets/{asset_id}/peers`

```json
{
  "peer_group": "kutch-row-b", "metric": "power_residual_pct", "window_hours": 24,
  "assets": [
    {"asset_id": "WT-017", "name": "Turbine 17", "value": -9.4, "is_subject": true,  "percentile": 96.0},
    {"asset_id": "WT-010", "name": "Turbine 10", "value": -1.2, "is_subject": false, "percentile": 41.0}
  ]
}
```

## `POST /api/assets/{asset_id}/investigate`

Body: `{"force_refresh": false}` (optional). Runs the agent loop. Response:

```json
{
  "investigation_id": "inv_WT-017_20260912T0640Z",
  "asset_id": "WT-017",
  "started_at": "2026-09-12T06:40:02Z",
  "completed_at": "2026-09-12T06:40:09Z",
  "verdict": {
    "likely_cause": "Progressive gearbox bearing degradation",
    "component": "gearbox",
    "severity": "high",
    "confidence": 0.87,
    "requires_human_review": false,
    "recommended_action": "Inspect gearbox vibration spectrum and oil particle count within 72 hours",
    "action_deadline_hours": 72,
    "evidence_summary": [
      "Drivetrain vibration 29% above expected for current load (z=3.4), rising 0.18 mm/s per day",
      "Gearbox oil temperature 7.8 °C above the load-matched baseline (z=4.1)",
      "All 8 peers in the same row are within normal band under identical wind conditions",
      "Wind conditions explain only 8% of the power deviation; no curtailment flag set",
      "Sustained for 18.5 hours with a step change at 2026-09-11T11:40Z"
    ],
    "model_used": "needle2",
    "fallback_used": false,
    "tool_calls": ["get_asset_evidence", "get_weather_context", "search_similar_cases",
                   "search_knowledge", "estimate_economic_impact"],
    "latency_ms": 6840.0
  },
  "timeline": [
    {"at": "2026-09-12T06:40:02Z", "stage": "telemetry", "label": "Evidence packet assembled",
     "detail": "7 signals, 18.5 h persistence", "status": "done"}
  ],
  "historical_cases": [
    {"case_id": "CASE-0031", "similarity": 0.93, "asset_id": "WT-004",
     "component": "gearbox", "fault_mode": "bearing_spalling",
     "observed_signature": ["vibration +31%", "oil temp +9 °C", "power -11%"],
     "outcome": "Planned bearing replacement at 14 days; secondary damage avoided",
     "lead_time_days": 11.0, "repair_cost_inr": 950000.0, "source": "synthetic_case_library"}
  ],
  "citations": [
    {"doc_id": "wind-gearbox-inspection-sop", "title": "Gearbox Inspection SOP",
     "section": "4.2 Vibration thresholds", "snippet": "Sustained drivetrain vibration above…",
     "score": 8.42, "retrieval": "fts5"}
  ],
  "economics": {
    "tariff_inr_per_kwh": 3.2,
    "recommended_option_id": "repair_now",
    "avoidable_exposure_inr": 107000.0,
    "options": [
      {"option_id": "repair_now", "label": "Inspect and repair now", "delay_days": 0,
       "intervention_cost_inr": 85000.0, "energy_loss_inr": 12400.0,
       "failure_escalation_inr": 0.0, "expected_exposure_inr": 48000.0,
       "failure_probability": 0.04,
       "assumptions": {"planned_downtime_hours": 36.0, "capacity_factor": 0.34}}
    ]
  }
}
```

Timeline `stage` values, in emission order:
`telemetry` → `expected_behavior` → `environment` → `peers` → `history` → `knowledge`
→ `economics` → `decision`.

## `GET /api/assets/{asset_id}/cases`

Array of `historical_cases` objects as above.

## `GET /api/assets/{asset_id}/economics`

The `economics` object as above. Query: `component` (optional override).

## `GET /api/soiling`

```json
{
  "site": "Charanka Solar Park", "updated_at": "2026-09-12T06:40:00Z",
  "site_soiling_loss_pct": 6.7, "dust_risk": "high",
  "rain_probability_48h": 0.23, "days_since_rain": 19.0,
  "cleaning_cost_inr": 42000.0,
  "recommendation": {"action": "wait", "wait_hours": 36,
    "rationale": "Rain probability 23% within 48 h; projected additional loss 0.6% is below cleaning cost threshold",
    "breakeven_days": 4.2},
  "zones": [
    {"zone": "block-2", "inverters": 12, "soiling_loss_pct": 8.4,
     "performance_ratio": 0.79, "status": "investigate",
     "worst_asset_id": "INV-023"}
  ]
}
```

`status` ∈ `"normal" | "watch" | "investigate"`; `dust_risk` ∈ `"low" | "moderate" | "high"`.

## `GET /api/knowledge/search`

Query: `q` (required), `k` (default 5), `asset_type` optional.

```json
{"query": "gearbox vibration threshold", "results": [ /* citation objects */ ]}
```

## `GET /api/knowledge/docs`

```json
[{"doc_id": "wind-gearbox-inspection-sop", "title": "Gearbox Inspection SOP",
  "asset_type": "wind_turbine", "component": "gearbox", "kind": "sop",
  "sections": 7, "source_note": "Illustrative sample document authored for this project"}]
```

## `GET /api/simulator/scenarios`

```json
[{"scenario": "gearbox_bearing_wear", "label": "Gearbox bearing wear",
  "asset_type": "wind_turbine", "component": "gearbox",
  "is_equipment_fault": true, "typical_onset_days": 14,
  "description": "Progressive vibration and thermal rise with mild power loss",
  "expected_detection": "Detected as asset-specific equipment fault"}]
```

Scenarios that must be present (the environmental-discrimination demo depends on the
last four being classified as *not* equipment faults):
`gearbox_bearing_wear`, `generator_overheating`, `pitch_misalignment`,
`yaw_misalignment`, `string_outage`, `inverter_derate`, `soiling_accumulation`,
`anemometer_drift`, `sensor_freeze`, `curtailment_window`, `cloud_transient`, `icing_event`.

## `POST /api/simulator/inject`

Body:

```json
{"asset_id": "WT-017", "scenario": "gearbox_bearing_wear",
 "severity": 0.7, "acceleration": 60, "duration_days": 14}
```

`acceleration` = simulated-time speed multiplier for the live demo. Response:

```json
{"run_id": "sim_20260912T0640Z", "asset_id": "WT-017",
 "scenario": "gearbox_bearing_wear", "severity": 0.7,
 "injected_at": "2026-09-12T06:40:00Z",
 "ground_truth": {"event_id": "EVT-0007", "onset": "2026-09-12T06:40:00Z",
   "detectable_from": "2026-09-12T07:10:00Z", "is_equipment_fault": true,
   "component": "gearbox"}}
```

## `POST /api/simulator/reset`

Body `{"asset_id": "WT-017"}` or `{}` for all. Returns `{"reset": ["WT-017"]}`.

## `GET /api/simulator/stream` (Server-Sent Events)

Query: `asset_id` optional. Each event is `data: <json>`:

```json
{"t": "2026-09-12T06:40:10Z", "asset_id": "WT-017", "power_kw": 1284.0,
 "expected_power_kw": 1417.0, "anomaly_score": 0.91, "health_score": 58.2,
 "risk_score": 0.82, "signals": {"drivetrain_vibration_mms": 4.62}}
```

Frontend must tolerate the stream being unavailable and fall back to polling
`/api/assets/{id}` every 5 s.

## `GET /api/evaluation`

Returns the measured evaluation report, or `null` fields where a metric has not been
computed. **Never invent values here.**

```json
{
  "computed_at": "2026-09-12T05:10:00Z",
  "dataset": {"source": "synthetic_physics_sim", "assets": 42, "days": 45,
              "rows": 205632, "injected_events": 24},
  "split": {"policy": "time_ordered_grouped_by_asset",
            "train": "2026-07-30..2026-08-26", "validation": "2026-08-27..2026-09-03",
            "test": "2026-09-04..2026-09-12"},
  "wind_expected_power": {"mae_kw": 41.2, "rmse_kw": 68.9, "r2": 0.991, "n_test": 18144},
  "solar_expected_power": {"mae_kw": 3.8, "rmse_kw": 6.1, "r2": 0.987, "n_test": 24192},
  "detection": {"event_recall": 0.88, "precision": 0.79,
                "median_lead_time_days": 6.4,
                "false_alarms_per_asset_month": 0.6,
                "equipment_vs_environment_accuracy": 0.94},
  "risk_model": {"brier_score": 0.071, "roc_auc": 0.93, "calibration": "isotonic"},
  "agent": {"schema_valid_rate": 1.0, "unsupported_claim_rate": 0.0,
            "escalation_rate": 0.17, "median_latency_ms": 1840.0}
}
```

---

## Error shape

Any 4xx/5xx returns:

```json
{"detail": "unknown asset_id 'WT-999'", "code": "asset_not_found"}
```

Codes: `asset_not_found`, `signal_not_found`, `scenario_not_found`,
`model_not_trained`, `index_not_built`, `agent_unavailable`.
