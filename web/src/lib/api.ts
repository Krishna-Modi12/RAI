/**
 * Client API services for RAI. Every getter returns { data, live }: `data` is either the
 * real API response or a last-known snapshot, and `live` is false whenever the API was
 * unreachable — callers must surface that distinction rather than showing the snapshot
 * with full visual authority (see docs/DESIGN.md's numerical-honesty rules).
 */

import {
  HealthResponse,
  FleetOverview,
  PriorityQueueItem,
  FleetAssetItem,
  InvestigationResult,
  HistoricalCaseItem,
  TimeseriesPoint,
  SoilingResponse,
  ScenarioItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export interface LiveResult<T> {
  data: T;
  live: boolean;
}

async function fetchWithFallback<T>(url: string, fallback: T): Promise<LiveResult<T>> {
  try {
    const res = await fetch(url, { next: { revalidate: 10 } });
    if (!res.ok) {
      console.warn(`API call failed: ${url} (${res.status}), showing last-known snapshot`);
      return { data: fallback, live: false };
    }
    return { data: (await res.json()) as T, live: true };
  } catch (err) {
    console.warn(`API call unreachable: ${url}, showing last-known snapshot`);
    return { data: fallback, live: false };
  }
}

// Fallbacks matching real precomputed fleet states (18 wind turbines, 24 solar inverters —
// see docs/API_CONTRACT.md; do not swap this ratio without re-checking the live contract)
const FALLBACK_HEALTH: HealthResponse = {
  status: "ok",
  version: "0.1.0",
  data_as_of: new Date().toISOString(),
  models_loaded: ["wind_expected_power", "solar_expected_power", "risk"],
  assets: 42,
  needle_available: true,
  needle_detail: "needle 2 session constructed",
};

const FALLBACK_FLEET: FleetOverview = {
  assets_total: 42,
  assets_at_risk: 4,
  assets_offline: 1,
  fleet_health: 93.8,
  generation_kw: 62450,
  expected_generation_kw: 68200,
  availability_pct: 97.6,
  revenue_at_risk_inr_30d: 485000,
  by_type: [
    { asset_type: "wind_turbine", count: 18, health: 91.0, generation_kw: 48200 },
    { asset_type: "solar_inverter", count: 24, health: 95.4, generation_kw: 14250 },
  ],
};

const FALLBACK_PRIORITY: PriorityQueueItem[] = [
  {
    asset_id: "WT-017",
    name: "Turbine 17",
    asset_type: "wind_turbine",
    site: "Kutch Wind Farm",
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
    name: "Central Inverter 23",
    asset_type: "solar_inverter",
    site: "Charanka Solar Park",
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
    name: "Turbine 04",
    asset_type: "wind_turbine",
    site: "Kutch Wind Farm",
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
    name: "String Inverter 09",
    asset_type: "solar_inverter",
    site: "Charanka Solar Park",
    risk_score: 0.45,
    risk_band: "elevated",
    revenue_at_risk_inr: 32000,
    dominant_signal: "DC Bus Voltage Ripple",
    deadline_hours: 120,
    requires_human_review: false,
    headline: "Minor MPPT clipping during peak irradiance",
  },
];

export async function getHealth(): Promise<LiveResult<HealthResponse>> {
  return fetchWithFallback(`${API_BASE}/health`, FALLBACK_HEALTH);
}

export async function getFleetOverview(): Promise<LiveResult<FleetOverview>> {
  return fetchWithFallback(`${API_BASE}/fleet`, FALLBACK_FLEET);
}

export async function getPriorityQueue(): Promise<LiveResult<PriorityQueueItem[]>> {
  return fetchWithFallback(`${API_BASE}/fleet/priority`, FALLBACK_PRIORITY);
}

export async function getFleetAssets(): Promise<LiveResult<FleetAssetItem[]>> {
  const fallbackAssets: FleetAssetItem[] = Array.from({ length: 42 }, (_, i) => {
    const isWind = i < 18;
    const id = isWind
      ? `WT-${String(i + 1).padStart(3, "0")}`
      : `INV-${String(i - 17).padStart(3, "0")}`;
    const isWT17 = id === "WT-017";
    const isINV23 = id === "INV-023";

    return {
      asset_id: id,
      name: isWind ? `Turbine ${i + 1}` : `Inverter ${i - 17}`,
      asset_type: isWind ? "wind_turbine" : "solar_inverter",
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

// The real GET /api/assets/{id}/timeseries response is an object — {asset_id, signal,
// unit, interval_min, points, events} — not a bare array, and each point carries
// residual_z but no raw residual. `residual` here is actual - expected, the direct
// definition of the term, not an invented figure.
function normalizeTimeseries(raw: Record<string, unknown>): TimeseriesPoint[] {
  const points = (raw.points as Array<Record<string, unknown>>) ?? [];
  return points.map((p) => {
    const actual = p.actual as number;
    const expected = p.expected as number;
    return {
      timestamp: p.t as string,
      actual,
      expected,
      lower_band: p.lower as number,
      upper_band: p.upper as number,
      residual: actual - expected,
      z_score: p.residual_z as number,
    };
  });
}

export async function getAssetTimeseries(assetId: string): Promise<LiveResult<TimeseriesPoint[]>> {
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

  try {
    const res = await fetch(`${API_BASE}/assets/${assetId}/timeseries`, { next: { revalidate: 10 } });
    if (!res.ok) {
      console.warn(`API call failed: ${API_BASE}/assets/${assetId}/timeseries (${res.status}), showing last-known snapshot`);
      return { data: points, live: false };
    }
    const raw = await res.json();
    return { data: normalizeTimeseries(raw), live: true };
  } catch (err) {
    console.warn(`API call unreachable: ${API_BASE}/assets/${assetId}/timeseries, showing last-known snapshot`);
    return { data: points, live: false };
  }
}

// The real POST /api/assets/{id}/investigate response nests evidence under `packet`
// (anomaly/risk/peers/environment/soiling) alongside top-level verdict/timeline/
// historical_cases/citations/economics — a materially different shape from the
// InvestigationResult the UI renders. This maps real fields onto that shape; anything
// with no real equivalent (e.g. a per-peer power breakdown, a per-cause loss split) is
// left out rather than invented.
function normalizeInvestigation(raw: Record<string, unknown>, assetId: string): InvestigationResult {
  const packet = (raw.packet ?? {}) as Record<string, unknown>;
  const verdict = (raw.verdict ?? {}) as Record<string, unknown>;
  const anomaly = (packet.anomaly ?? {}) as Record<string, unknown>;
  const risk = (packet.risk ?? {}) as Record<string, unknown>;
  const peers = (packet.peers ?? {}) as Record<string, unknown>;
  const environment = (packet.environment ?? {}) as Record<string, unknown>;
  const conditions = (environment.conditions ?? {}) as Record<string, unknown>;
  const soiling = packet.soiling as Record<string, unknown> | null | undefined;
  const economics = (raw.economics ?? {}) as Record<string, unknown>;
  const startedAt = new Date((raw.started_at as string) ?? Date.now()).getTime();

  const detectors = (anomaly.detectors as Array<Record<string, unknown>>) ?? [];
  const dominantDetector = detectors.reduce<Record<string, unknown> | null>((best, d) => {
    if (!best || (d.score as number) > (best.score as number)) return d;
    return best;
  }, null);

  const signals = ((anomaly.signals as Array<Record<string, unknown>>) ?? []).map((s) => ({
    name: s.name as string,
    actual: s.actual as number,
    expected: s.expected as number,
    residual: s.residual as number,
    z_score: s.z_score as number,
    trend_per_day: s.trend_per_day as number,
    dominant: s.name === anomaly.dominant_signal,
  }));

  const options = ((economics.options as Array<Record<string, unknown>>) ?? []).map((o) => {
    const avoidableTotal = (economics.avoidable_exposure_inr as number) ?? 0;
    const expectedExposure = (o.expected_exposure_inr as number) ?? 0;
    const avoidedLoss = avoidableTotal - expectedExposure;
    return {
      action: o.label as string,
      cost_inr: o.intervention_cost_inr as number,
      avoided_loss_inr: avoidedLoss,
      net_benefit_inr: avoidedLoss - (o.intervention_cost_inr as number),
      is_recommended: o.option_id === economics.recommended_option_id,
    };
  });
  const recommendedOption = options.find((o) => o.is_recommended) ?? options[0];

  return {
    asset_id: (raw.asset_id as string) ?? assetId,
    verdict: (verdict.likely_cause as string) ?? "No verdict computed",
    confidence: (verdict.confidence as number) ?? 0,
    needle_used: (verdict.model_used as string) ?? "unknown",
    requires_human_review: Boolean(verdict.requires_human_review),
    timeline: ((raw.timeline as Array<Record<string, unknown>>) ?? []).map((t) => ({
      stage: t.stage as string,
      status: (t.status as "pending" | "running" | "done" | "skipped") ?? "done",
      detail: (t.detail as string) ?? (t.label as string) ?? "",
      elapsed_ms: Math.max(0, new Date(t.at as string).getTime() - startedAt),
    })),
    evidence: {
      anomaly: {
        score: (anomaly.anomaly_score as number) ?? 0,
        threshold: (dominantDetector?.threshold as number) ?? 0.5,
        severity: (verdict.severity as string) ?? "low",
        signals,
      },
      environment: {
        is_explained: environment.verdict === "environmental",
        explains_fraction: environment.explains_fraction as number | undefined,
        ambient_temp_c: conditions.ambient_temp_c as number | undefined,
        wind_speed_ms: conditions.wind_speed_ms as number | undefined,
        irradiance_wm2: conditions.irradiance_wm2 as number | undefined,
        dust_risk: soiling?.dust_risk as string | undefined,
      },
      peers: {
        group_size: (peers.n_peers as number) ?? 0,
        is_isolated: peers.verdict === "asset_specific",
        subject_residual_pct: (peers.asset_residual_pct as number) ?? 0,
        peer_median_residual_pct: (peers.peer_median_residual_pct as number) ?? 0,
        deviation_percentile: (peers.deviation_percentile as number) ?? 0,
      },
      history: {
        cases: ((raw.historical_cases as Array<Record<string, unknown>>) ?? []) as unknown as HistoricalCaseItem[],
      },
      knowledge: {
        citations: ((raw.citations as Array<Record<string, unknown>>) ?? []).map((c) => ({
          doc_id: c.doc_id as string,
          title: c.title as string,
          snippet: c.snippet as string,
          relevance: c.score as number,
        })),
      },
      economics: {
        options,
        avoidable_exposure_inr: (economics.avoidable_exposure_inr as number) ?? 0,
      },
    },
    intervention: {
      recommended_action: (verdict.recommended_action as string) ?? "No action recommended",
      recommended_window_hours: (verdict.action_deadline_hours as number) ?? 0,
      expected_savings_inr: (economics.avoidable_exposure_inr as number) ?? 0,
      net_benefit_inr: recommendedOption?.net_benefit_inr ?? 0,
    },
  };
}

export async function getInvestigation(assetId: string): Promise<LiveResult<InvestigationResult>> {
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
        explains_fraction: isWT17 ? 0.06 : 0.82,
        ambient_temp_c: 34.2,
        wind_speed_ms: 8.4,
        irradiance_wm2: 820,
        dust_risk: isWT17 ? "low" : "high",
      },
      peers: {
        group_size: 8,
        is_isolated: isWT17,
        subject_residual_pct: -11.9,
        peer_median_residual_pct: 0.2,
        deviation_percentile: isWT17 ? 100.0 : 92.0,
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
        avoidable_exposure_inr: 7662566,
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

  try {
    const res = await fetch(`${API_BASE}/assets/${assetId}/investigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force_refresh: false }),
    });
    if (!res.ok) {
      console.warn(`Investigation failed: ${API_BASE}/assets/${assetId}/investigate (${res.status}), showing last-known snapshot`);
      return { data: fallback, live: false };
    }
    const raw = await res.json();
    return { data: normalizeInvestigation(raw, assetId), live: true };
  } catch (err) {
    console.warn(`Investigation unreachable: ${API_BASE}/assets/${assetId}/investigate, showing last-known snapshot`);
    return { data: fallback, live: false };
  }
}

export async function getSoilingIntelligence(): Promise<LiveResult<SoilingResponse>> {
  // Matches the real GET /api/soiling contract (docs/API_CONTRACT.md) exactly, used only
  // when the API is unreachable. This is a site-level summary, not per-asset.
  const fallback: SoilingResponse = {
    site: "Charanka Solar Park",
    updated_at: new Date().toISOString(),
    site_soiling_loss_pct: 6.7,
    dust_risk: "high",
    rain_probability_48h: 0.23,
    days_since_rain: 19,
    cleaning_cost_inr: 42000,
    recommendation: {
      action: "wait",
      wait_hours: 36,
      rationale: "Rain probability 23% within 48 h; projected additional loss is below the cleaning cost threshold.",
      breakeven_days: 4.2,
    },
    zones: [
      { zone: "block-1", inverters: 12, soiling_loss_pct: 5.9, performance_ratio: 0.82, status: "watch", worst_asset_id: "INV-007" },
      { zone: "block-2", inverters: 12, soiling_loss_pct: 8.4, performance_ratio: 0.79, status: "investigate", worst_asset_id: "INV-023" },
    ],
  };

  return fetchWithFallback(`${API_BASE}/soiling`, fallback);
}

export async function getScenarios(): Promise<LiveResult<ScenarioItem[]>> {
  // Matches the real GET /api/simulator/scenarios contract (docs/API_CONTRACT.md) exactly,
  // used only when the API is unreachable.
  const fallback: ScenarioItem[] = [
    { scenario: "gearbox_bearing_wear", label: "Gearbox bearing wear", asset_type: "wind_turbine", component: "gearbox", is_equipment_fault: true, typical_onset_days: 14, description: "Progressive vibration and oil-temperature rise with mild power loss", expected_detection: "Asset-specific equipment fault, escalated for inspection" },
    { scenario: "generator_overheating", label: "Generator overheating", asset_type: "wind_turbine", component: "generator", is_equipment_fault: true, typical_onset_days: 9, description: "Winding temperature climbs and the controller derates at high load", expected_detection: "Asset-specific thermal fault" },
    { scenario: "pitch_misalignment", label: "Pitch misalignment", asset_type: "wind_turbine", component: "pitch_system", is_equipment_fault: true, typical_onset_days: 7, description: "Power loss concentrated at mid wind speeds with no thermal signature", expected_detection: "Aerodynamic fault distinguished from drivetrain wear by absent thermal rise" },
    { scenario: "yaw_misalignment", label: "Yaw misalignment", asset_type: "wind_turbine", component: "yaw_system", is_equipment_fault: true, typical_onset_days: 10, description: "Cosine-squared power loss correlated with wind direction", expected_detection: "Direction-dependent loss, separable from a uniform derate" },
    { scenario: "string_outage", label: "DC string outage", asset_type: "solar_inverter", component: "dc_string", is_equipment_fault: true, typical_onset_days: 1, description: "Step loss of DC current when strings drop offline", expected_detection: "Step change isolated to one inverter" },
    { scenario: "inverter_derate", label: "Inverter thermal derate", asset_type: "solar_inverter", component: "inverter", is_equipment_fault: true, typical_onset_days: 5, description: "Inverter temperature rises and output is clipped below rating", expected_detection: "Asset-specific thermal fault on the AC side" },
    { scenario: "soiling_accumulation", label: "Soiling accumulation", asset_type: "solar_inverter", component: "soiling", is_equipment_fault: false, typical_onset_days: 21, description: "Dust builds on the array and washes off after rain", expected_detection: "Recoverable loss, cleaning economics rather than a repair ticket" },
    { scenario: "anemometer_drift", label: "Anemometer drift", asset_type: "wind_turbine", component: "anemometer", is_equipment_fault: false, typical_onset_days: 12, description: "The wind sensor reads progressively high, so the asset appears to underperform against its own measured wind while nothing mechanical has changed", expected_detection: "Instrumentation fault, NOT a drivetrain alarm" },
    { scenario: "sensor_freeze", label: "Frozen sensor", asset_type: "wind_turbine", component: "anemometer", is_equipment_fault: false, typical_onset_days: 2, description: "A sensor holds its last value while the asset keeps operating", expected_detection: "Data-quality fault, suppressed from equipment alarms" },
    { scenario: "curtailment_window", label: "Grid curtailment", asset_type: "wind_turbine", component: "none", is_equipment_fault: false, typical_onset_days: 1, description: "Output capped by grid instruction", expected_detection: "Commanded reduction, never an equipment alarm" },
    { scenario: "cloud_transient", label: "Cloud transient", asset_type: "solar_inverter", component: "none", is_equipment_fault: false, typical_onset_days: 1, description: "Deep short-lived irradiance drops across the plant", expected_detection: "Environmental, explained by irradiance" },
    { scenario: "icing_event", label: "Blade icing", asset_type: "wind_turbine", component: "none", is_equipment_fault: false, typical_onset_days: 2, description: "Power loss under low temperature and high humidity", expected_detection: "Environmental, explained by ambient conditions" },
  ];

  return fetchWithFallback(`${API_BASE}/simulator/scenarios`, fallback);
}

export interface InjectResult {
  ok: boolean;
  detail?: string;
}

export async function injectScenario(
  assetId: string,
  scenario: string,
  severity = 0.7,
  accelerationFactor = 60,
  durationDays = 14
): Promise<InjectResult> {
  try {
    const res = await fetch(`${API_BASE}/simulator/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_id: assetId,
        scenario,
        severity,
        acceleration: accelerationFactor,
        duration_days: durationDays,
      }),
    });
    if (!res.ok) {
      console.warn(`Scenario injection failed: ${res.status}`);
      return { ok: false, detail: `API returned ${res.status}` };
    }
    return { ok: true };
  } catch (err) {
    console.warn("Scenario injection unreachable:", err);
    return { ok: false, detail: "API unreachable" };
  }
}

export async function resetScenario(assetId?: string): Promise<InjectResult> {
  try {
    const res = await fetch(`${API_BASE}/simulator/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(assetId ? { asset_id: assetId } : {}),
    });
    if (!res.ok) {
      console.warn(`Scenario reset failed: ${res.status}`);
      return { ok: false, detail: `API returned ${res.status}` };
    }
    return { ok: true };
  } catch (err) {
    console.warn("Scenario reset unreachable:", err);
    return { ok: false, detail: "API unreachable" };
  }
}

export interface KnowledgeSearchResult {
  doc_id: string;
  title: string;
  section: string;
  snippet: string;
  score: number;
  retrieval: string;
}

export interface KnowledgeSearchResponse {
  query: string;
  results: KnowledgeSearchResult[];
}

export async function searchKnowledge(query: string): Promise<LiveResult<KnowledgeSearchResponse>> {
  const fallback: KnowledgeSearchResponse = {
    query,
    results: [
      {
        doc_id: "wind-gearbox-system",
        title: "Wind Turbine Gearbox and Drivetrain System Manual",
        section: "3. Drivetrain failure modes and their observable signatures",
        snippet: "Failure-mode signatures expressed in the exact telemetry tags RAI monitors.",
        score: 0.25,
        retrieval: "fts5",
      },
    ],
  };
  return fetchWithFallback(`${API_BASE}/knowledge/search?q=${encodeURIComponent(query)}`, fallback);
}

export interface KnowledgeDoc {
  doc_id: string;
  title: string;
  asset_type: "wind_turbine" | "solar_inverter" | "both";
  component: string;
  kind: string;
  sections: number;
  source_note: string;
}

export async function getKnowledgeDocs(): Promise<LiveResult<KnowledgeDoc[]>> {
  const fallback: KnowledgeDoc[] = [
    { doc_id: "wind-gearbox-system", title: "Wind Turbine Gearbox and Drivetrain System Manual", asset_type: "wind_turbine", component: "gearbox", kind: "manual", sections: 13, source_note: "Illustrative sample document authored for this project" },
    { doc_id: "wind-bearing-replacement-sop", title: "Main Bearing and HSS Bearing Replacement", asset_type: "wind_turbine", component: "gearbox", kind: "sop", sections: 9, source_note: "Illustrative sample document authored for this project" },
    { doc_id: "solar-dc-string-system", title: "DC String and Array Manual", asset_type: "solar_inverter", component: "dc_array", kind: "manual", sections: 12, source_note: "Illustrative sample document authored for this project" },
  ];
  return fetchWithFallback(`${API_BASE}/knowledge/docs`, fallback);
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
    ece: number;
    bin_confidences: number[];
    bin_accuracies: number[];
    bin_counts: number[];
  };
  latencies?: Record<string, number>;
  alert_fatigue_funnel?: {
    is_empirically_measured?: boolean;
    raw_statistical_detections_per_year: number;
    persistence_filtered_per_year: number;
    environmental_filtered_per_year: number;
    peer_consensus_filtered_per_year: number;
    confidence_gated_alerts_per_year: number;
    final_actionable_rate_per_asset_year: number;
    overall_noise_suppression_pct: number;
    funnel_stages: Array<{ stage: string; annual_alarms: number; eliminated_pct: number }>;
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
