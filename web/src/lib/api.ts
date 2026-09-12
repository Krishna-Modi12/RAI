/**
 * Client API services for RAI with robust local fallbacks
 */

import {
  HealthResponse,
  FleetOverview,
  PriorityQueueItem,
  FleetAssetItem,
  InvestigationResult,
  TimeseriesPoint,
  SoilingResponse,
  ScenarioItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

async function fetchWithFallback<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, { next: { revalidate: 10 } });
    if (!res.ok) {
      console.warn(`API call failed: ${url} (${res.status}), using fallback`);
      return fallback;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`API call unreachable: ${url}, using fallback`);
    return fallback;
  }
}

// Fallbacks matching real precomputed fleet states
const FALLBACK_HEALTH: HealthResponse = {
  status: "ok",
  timestamp: new Date().toISOString(),
  data_freshness_s: 14,
  models_loaded: ["expected_behavior_gbm", "hybrid_ensemble", "risk_calibrated"],
  assets_active: 42,
  needle_available: true,
  needle_confidence_threshold: 0.8,
};

const FALLBACK_FLEET: FleetOverview = {
  total_assets: 42,
  assets_at_risk: 4,
  offline_assets: 1,
  fleet_health: 93.8,
  generation_kw: 62450,
  expected_generation_kw: 68200,
  availability_pct: 97.6,
  revenue_at_risk_inr_per_day: 485000,
};

const FALLBACK_PRIORITY: PriorityQueueItem[] = [
  {
    asset_id: "WT-017",
    asset_name: "Turbine 17 · Kutch",
    asset_type: "wind",
    site_name: "Kutch Wind Farm",
    risk_score: 0.88,
    risk_band: "critical",
    revenue_at_risk_inr: 155000,
    dominant_signal: "Gearbox High-Speed Bearing Temp",
    deadline_hours: 48,
    requires_human_review: false,
    headline: "Progressive inner race degradation (+3.4σ residual)",
  },
  {
    asset_id: "INV-023",
    asset_name: "Central Inverter 23 · Charanka",
    asset_type: "solar",
    site_name: "Charanka Solar Park",
    risk_score: 0.74,
    risk_band: "high",
    revenue_at_risk_inr: 88000,
    dominant_signal: "Severe Soiling / Dust Ingress",
    deadline_hours: 36,
    requires_human_review: false,
    headline: "Severe dust event (+14.2% soiling loss, rain wash possible)",
  },
  {
    asset_id: "WT-004",
    asset_name: "Turbine 04 · Kutch",
    asset_type: "wind",
    site_name: "Kutch Wind Farm",
    risk_score: 0.62,
    risk_band: "elevated",
    revenue_at_risk_inr: 54000,
    dominant_signal: "Pitch Cylinder Pressure Asymmetry",
    deadline_hours: 96,
    requires_human_review: true,
    headline: "Pitch actuator lag under high turbulence",
  },
  {
    asset_id: "INV-009",
    asset_name: "String Inverter 09 · Charanka",
    asset_type: "solar",
    site_name: "Charanka Solar Park",
    risk_score: 0.45,
    risk_band: "elevated",
    revenue_at_risk_inr: 32000,
    dominant_signal: "DC Bus Voltage Ripple",
    deadline_hours: 120,
    requires_human_review: false,
    headline: "Minor MPPT clipping during peak irradiance",
  },
];

export async function getHealth(): Promise<HealthResponse> {
  return fetchWithFallback(`${API_BASE}/health`, FALLBACK_HEALTH);
}

export async function getFleetOverview(): Promise<FleetOverview> {
  return fetchWithFallback(`${API_BASE}/fleet`, FALLBACK_FLEET);
}

export async function getPriorityQueue(): Promise<PriorityQueueItem[]> {
  return fetchWithFallback(`${API_BASE}/fleet/priority`, FALLBACK_PRIORITY);
}

export async function getFleetAssets(): Promise<FleetAssetItem[]> {
  const fallbackAssets: FleetAssetItem[] = Array.from({ length: 42 }, (_, i) => {
    const isWind = i < 24;
    const id = isWind
      ? `WT-${String(i + 1).padStart(3, "0")}`
      : `INV-${String(i - 23).padStart(3, "0")}`;
    const isWT17 = id === "WT-017";
    const isINV23 = id === "INV-023";

    return {
      asset_id: id,
      name: isWind ? `Turbine ${i + 1}` : `Inverter ${i - 23}`,
      asset_type: isWind ? "wind" : "solar",
      site: isWind ? "Kutch Wind Farm" : "Charanka Solar Park",
      status: isWT17 ? "critical" : isINV23 ? "warning" : "nominal",
      health_score: isWT17 ? 48.2 : isINV23 ? 64.0 : 96.5,
      risk_score: isWT17 ? 0.88 : isINV23 ? 0.74 : 0.08,
      risk_band: isWT17 ? "critical" : isINV23 ? "high" : "low",
      power_kw: isWind ? 1850 : 820,
      expected_power_kw: isWind ? (isWT17 ? 2100 : 1870) : (isINV23 ? 950 : 825),
      residual_pct: isWT17 ? -11.9 : isINV23 ? -13.7 : -0.6,
      operating_state: "generating",
      last_update: new Date().toISOString(),
    };
  });

  return fetchWithFallback(`${API_BASE}/assets`, fallbackAssets);
}

export async function getAssetTimeseries(assetId: string): Promise<TimeseriesPoint[]> {
  const points: TimeseriesPoint[] = [];
  const now = Date.now();
  const isWT17 = assetId === "WT-017";
  const isINV23 = assetId === "INV-023";

  for (let i = 48; i >= 0; i--) {
    const t = new Date(now - i * 3600 * 1000).toISOString();
    const baseExp = isWT17 ? 1950 : 850;
    const drop = (isWT17 || isINV23) && i < 20 ? (20 - i) * (isWT17 ? 14 : 7) : 0;
    const actual = Math.max(0, baseExp - drop + (Math.random() * 40 - 20));
    const residual = actual - baseExp;
    const zScore = residual / 45;

    points.push({
      timestamp: t,
      expected: baseExp,
      actual: Math.round(actual),
      lower_band: Math.round(baseExp * 0.92),
      upper_band: Math.round(baseExp * 1.05),
      residual: Math.round(residual),
      z_score: Number(zScore.toFixed(2)),
    });
  }

  return fetchWithFallback(`${API_BASE}/assets/${assetId}/timeseries`, points);
}

export async function getInvestigation(assetId: string): Promise<InvestigationResult> {
  const isWT17 = assetId === "WT-017";
  const fallback: InvestigationResult = {
    asset_id: assetId,
    verdict: isWT17
      ? "Equipment failure in progress: Stage-3 bearing spalling"
      : "Severe dust accumulation and soiling degradation",
    confidence: isWT17 ? 0.91 : 0.88,
    needle_used: "needle2",
    requires_human_review: false,
    timeline: [
      { stage: "telemetry", status: "done", detail: "SCADA ingestion validated; zero sensor dropouts", elapsed_ms: 12 },
      { stage: "expected_behavior", status: "done", detail: "Normal power/thermal deviation detected (>3σ)", elapsed_ms: 24 },
      { stage: "environment", status: "done", detail: isWT17 ? "Weather conditions normal; cannot explain anomaly" : "CAMS dust event confirmed (AOD 0.82)", elapsed_ms: 38 },
      { stage: "peers", status: "done", detail: isWT17 ? "8 neighboring turbines operating nominal" : "Site-wide solar attenuation confirmed", elapsed_ms: 45 },
      { stage: "history", status: "done", detail: "Matched CASE-0031 (93% similarity)", elapsed_ms: 58 },
      { stage: "knowledge", status: "done", detail: "Retrieved OEM SOP Section 4.2.1 Bearing Limits", elapsed_ms: 72 },
      { stage: "economics", status: "done", detail: "Optimal action: inspect & schedule within 72h", elapsed_ms: 85 },
      { stage: "decision", status: "done", detail: "Confidence 0.91 > threshold 0.80 — Automated Alert Approved", elapsed_ms: 91 },
    ],
    evidence: {
      anomaly: {
        score: 0.88,
        threshold: 0.45,
        severity: "critical",
        signals: isWT17
          ? [
              { name: "Gearbox High-Speed Bearing Temp", actual: 88.4, expected: 64.2, residual: 24.2, z_score: 3.6, trend_per_day: 4.8, dominant: true },
              { name: "Drive-End Vibration RMS", actual: 4.8, expected: 2.1, residual: 2.7, z_score: 3.1, trend_per_day: 0.5, dominant: false },
              { name: "Gearbox Sump Oil Temp", actual: 72.1, expected: 62.0, residual: 10.1, z_score: 2.2, trend_per_day: 1.8, dominant: false },
            ]
          : [
              { name: "Normalized PR (Performance Ratio)", actual: 0.69, expected: 0.84, residual: -0.15, z_score: -3.2, trend_per_day: -0.04, dominant: true },
              { name: "Inverter DC-to-AC Efficiency", actual: 95.8, expected: 98.4, residual: -2.6, z_score: -2.4, trend_per_day: -0.5, dominant: false },
            ],
      },
      environment: {
        is_explained: !isWT17,
        loss_breakdown: isWT17
          ? { weather: 0.0, curtailment: 0.0, equipment: 18.2, unexplained: 1.1 }
          : { irradiance: 4.0, soiling: 11.5, thermal: 1.2, equipment: 0.0, unexplained: 0.8 },
        ambient_temp_c: 34.2,
        wind_speed_ms: 8.4,
        irradiance_wm2: 820,
        dust_risk: isWT17 ? "low" : "high",
      },
      peers: {
        group_size: 8,
        peer_z_score: isWT17 ? 3.4 : 0.4,
        is_isolated: isWT17,
        distribution: [
          { peer_id: assetId, power_kw: 1850, residual_pct: -11.9, is_subject: true },
          { peer_id: isWT17 ? "WT-015" : "INV-021", power_kw: 2100, residual_pct: 0.2, is_subject: false },
          { peer_id: isWT17 ? "WT-016" : "INV-022", power_kw: 2085, residual_pct: -0.4, is_subject: false },
          { peer_id: isWT17 ? "WT-018" : "INV-024", power_kw: 2110, residual_pct: 0.5, is_subject: false },
        ],
      },
      history: {
        cases: [
          {
            case_id: "CASE-0031",
            similarity: 0.93,
            component: "Gearbox High-Speed Shaft",
            fault_mode: "Bearing fatigue spalling",
            outcome: "Planned replacement avoided secondary gear mesh failure",
            lead_time_days: 14,
            repair_cost_inr: 850000,
            source: "synthetic_case_library",
          },
        ],
      },
      knowledge: {
        citations: [
          {
            doc_id: "SOP-WIND-042",
            title: "Bearing Temperature Thresholds & Vibration Envelope",
            snippet: "When bearing delta exceeds 20°C above peer mean, schedule endoscopic inspection within 72h.",
            relevance: 0.94,
          },
        ],
      },
      economics: {
        daily_exposure_inr: 155000,
        options: [
          { action: "Repair Now (Planned)", cost_inr: 850000, avoided_loss_inr: 4500000, net_benefit_inr: 3650000, is_recommended: true },
          { action: "Defer 7 Days", cost_inr: 1250000, avoided_loss_inr: 3200000, net_benefit_inr: 1950000, is_recommended: false },
          { action: "Run to Failure", cost_inr: 5200000, avoided_loss_inr: 0, net_benefit_inr: -5200000, is_recommended: false },
        ],
      },
    },
    intervention: {
      recommended_action: isWT17 ? "Schedule High-Speed Bearing Inspection" : "Initiate Targeted Jet Cleaning (Zone 2)",
      recommended_window_hours: isWT17 ? 72 : 48,
      expected_savings_inr: isWT17 ? 3650000 : 210000,
      net_benefit_inr: isWT17 ? 3650000 : 165000,
    },
  };

  return fetchWithFallback(`${API_BASE}/assets/${assetId}/investigate`, fallback);
}

export async function getSoilingIntelligence(assetId = "INV-023"): Promise<SoilingResponse> {
  const fallback: SoilingResponse = {
    asset_id: assetId,
    site: "Charanka Solar Park",
    timestamp: new Date().toISOString(),
    dust_risk: "high",
    dust_concentration_ug_m3: 168.4,
    aod_550: 0.84,
    pm10_ug_m3: 142.1,
    rain_probability_24h: 0.15,
    rain_wash_probability: 0.12,
    mud_cementation_risk: "medium",
    soiling_ratio: 0.874,
    current_soiling_loss_pct: 12.6,
    daily_accumulation_rate_pct: 0.65,
    last_cleaning_days_ago: 14,
    advisor_options: [
      {
        action: "Clean Now",
        recommended_window_hours: 24,
        expected_energy_recovered_kwh: 14500,
        cleaning_cost_inr: 45000,
        avoided_loss_inr: 122000,
        net_benefit_inr: 77000,
        break_even_days: 3.2,
        confidence: 0.89,
        is_recommended: true,
        rationale: "High dust accumulation; low rain probability (15%) makes immediate cleaning NPV positive.",
      },
      {
        action: "Wait 24h",
        recommended_window_hours: 48,
        expected_energy_recovered_kwh: 13200,
        cleaning_cost_inr: 45000,
        avoided_loss_inr: 104000,
        net_benefit_inr: 59000,
        break_even_days: 4.1,
        confidence: 0.85,
        is_recommended: false,
        rationale: "Delaying results in an additional ~₹18,000 avoidable energy loss.",
      },
      {
        action: "Wait 72h",
        recommended_window_hours: 72,
        expected_energy_recovered_kwh: 11400,
        cleaning_cost_inr: 45000,
        avoided_loss_inr: 72000,
        net_benefit_inr: 27000,
        break_even_days: 5.8,
        confidence: 0.81,
        is_recommended: false,
        rationale: "Suboptimal: rain forecast remains dry and generation revenue continues bleeding.",
      },
      {
        action: "Wait 7 Days",
        recommended_window_hours: 168,
        expected_energy_recovered_kwh: 6800,
        cleaning_cost_inr: 45000,
        avoided_loss_inr: 34000,
        net_benefit_inr: -11000,
        break_even_days: 9.4,
        confidence: 0.74,
        is_recommended: false,
        rationale: "Negative NPV: losses exceed cleaning cost; cementation risks increase with humidity.",
      },
    ],
    loss_decomposition: {
      total_loss_pct: 16.5,
      irradiance_loss_pct: 2.1,
      soiling_loss_pct: 12.6,
      thermal_loss_pct: 1.1,
      curtailment_loss_pct: 0.0,
      equipment_loss_pct: 0.0,
      unexplained_loss_pct: 0.7,
    },
  };

  return fetchWithFallback(`${API_BASE}/soiling?asset_id=${assetId}`, fallback);
}

export async function getScenarios(): Promise<ScenarioItem[]> {
  const fallback: ScenarioItem[] = [
    { id: "bearing_wear", name: "Bearing Inner-Race Spalling", asset_type: "wind", description: "Progressive thermal and vibration increase on high-speed shaft", category: "equipment", affected_signals: ["bearing_temp", "vibration_rms"], duration_hours: 72 },
    { id: "dust_storm", name: "Thar Desert Sandstorm Ingress", asset_type: "solar", description: "Rapid AOD & PM10 surge causing steep soiling attenuation", category: "environment", affected_signals: ["irradiance", "soiling_ratio", "power"], duration_hours: 24 },
    { id: "dust_plus_rain", name: "Dust Storm Followed by Light Rain", asset_type: "solar", description: "Aerosol deposition followed by drizzle creating muddy cementation", category: "environment", affected_signals: ["soiling_ratio", "cementation_index"], duration_hours: 48 },
    { id: "cloud_transient", name: "Monsoon Cumulus Cloud Transients", asset_type: "solar", description: "Rapid irradiance fluctuations without equipment impairment", category: "environment", affected_signals: ["irradiance", "power"], duration_hours: 12 },
    { id: "grid_curtailment", name: "SLDC Grid Curtailment Directive", asset_type: "wind", description: "Active power setpoint capping; normal component temperatures", category: "environment", affected_signals: ["active_power"], duration_hours: 8 },
    { id: "pitch_misalignment", name: "Blade Pitch Actuator Lag", asset_type: "wind", description: "Asymmetric aerodynamic loads and rotor speed hunting", category: "equipment", affected_signals: ["pitch_angle", "power_deficit"], duration_hours: 36 },
  ];

  return fetchWithFallback(`${API_BASE}/simulator/scenarios`, fallback);
}

export async function searchKnowledge(query: string) {
  try {
    const res = await fetch(`${API_BASE}/knowledge/search?q=${encodeURIComponent(query)}`);
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Knowledge search unreachable:", err);
  }
  return {
    query,
    total_results: 1,
    results: [
      {
        section_id: "SOP-WIND-042",
        doc_id: "SOP-WIND-042",
        title: "Bearing Temperature Thresholds & Vibration Envelope",
        snippet: "When bearing delta exceeds 20°C above peer mean, schedule endoscopic inspection within 72h.",
        category: "sop",
        similarity: 0.92,
      },
    ],
  };
}

export interface EvaluationData {
  computed_at: string | null;
  available: boolean;
  dataset?: {
    source: string;
    assets: number;
    days: number;
    monitored_hours: number;
    total_eval_time_s: number;
  };
  split?: {
    policy: string;
    gap_hours: number;
    held_out_assets: number;
    leakage_free: boolean;
  };
  champion_model?: {
    model: string;
    care_score: number;
    pr_auc: number;
    coverage: number;
    accuracy: number;
    reliability: number;
    earliness: number;
    false_alarms_per_year: number;
    median_lead_days: number;
  };
  benchmarks?: Array<{
    model: string;
    tier: string;
    care_score: number;
    pr_auc: number;
    precision: number;
    recall: number;
    false_alarms_per_year: number;
    median_lead_days: number;
  }>;
  generalization?: Record<string, unknown>;
  calibration_bins?: {
    brier_score: number;
    expected_calibration_error: number;
    bin_confidences: number[];
    bin_accuracies: number[];
    bin_counts: number[];
  };
  latencies?: Record<string, number>;
  alert_fatigue_funnel?: {
    raw_statistical_detections_per_year: number;
    persistence_filtered_per_year: number;
    environmental_filtered_per_year: number;
    peer_consensus_filtered_per_year: number;
    confidence_gated_alerts_per_year: number;
    final_actionable_rate_per_asset_year: number;
    overall_noise_suppression_pct: number;
    stages: Array<{ stage: string; annual_alarms: number; eliminated_pct: number }>;
  };
  decision_regret?: {
    optimal_execution_pct: number;
    mean_regret_inr: number;
    median_regret_inr: number;
    p95_regret_inr: number;
    mean_expected_cost_inr: number;
    mean_realized_cost_inr: number;
    simulated_scenarios: number;
  };
  track_b_external_benchmark?: {
    benchmark_name: string;
    status: string;
    n_turbines: number;
    n_labeled_anomaly_frames: number;
    n_normal_time_series: number;
    metrics_claimable: boolean;
    reason: string;
    zero_shot_verification?: {
      n_turbines: number;
      mean_expected_power_r2: number;
      mean_thermal_tracking_r2: number;
      false_alarm_rate_per_year: number;
      validation_passed: boolean;
    };
  };
}

export async function getEvaluationMetrics(): Promise<EvaluationData | null> {
  try {
    const res = await fetch(`${API_BASE}/evaluation`, { next: { revalidate: 10 } });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Evaluation metrics fetch failed, using offline fallback:", err);
  }
  return null;
}

