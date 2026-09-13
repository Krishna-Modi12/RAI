/**
 * TypeScript types matching docs/API_CONTRACT.md
 */

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  version: string;
  data_as_of: string;
  needle_available: boolean;
  needle_detail: string;
  models_loaded: string[];
  assets: number;
}

export interface FleetOverview {
  assets_total: number;
  assets_at_risk: number;
  assets_offline: number;
  fleet_health: number;
  generation_kw: number;
  expected_generation_kw: number;
  availability_pct: number;
  revenue_at_risk_inr_30d: number;
  by_type?: Array<{
    asset_type: "wind_turbine" | "solar_inverter";
    count: number;
    health: number;
    generation_kw: number;
  }>;
}

export interface PriorityQueueItem {
  asset_id: string;
  name: string;
  asset_type: "wind_turbine" | "solar_inverter";
  site: string;
  risk_score: number;
  risk_band: "low" | "elevated" | "high" | "critical";
  revenue_at_risk_inr: number | null;
  dominant_signal: string;
  deadline_hours: number;
  requires_human_review: boolean;
  headline: string;
}

export interface FleetAssetItem {
  asset_id: string;
  name: string;
  asset_type: "wind_turbine" | "solar_inverter";
  site: string;
  status: "nominal" | "warning" | "critical" | "offline";
  health_score: number;
  risk_score: number;
  risk_band: "low" | "elevated" | "high" | "critical";
  power_kw: number;
  expected_power_kw: number;
  residual_pct: number;
  operating_state: string;
  last_update: string;
}

export interface ResidualSignal {
  name: string;
  actual: number;
  expected: number;
  residual: number;
  z_score: number;
  trend_per_day: number;
  dominant: boolean;
}

export interface HistoricalCaseItem {
  case_id: string;
  similarity: number;
  asset_id?: string;
  component: string;
  fault_mode: string;
  outcome: string;
  lead_time_days: number | null;
  repair_cost_inr: number | null;
  source: string;
  source_type?: string;
  evidence_states?: Record<string, string>;
  why_matched?: string[];
  what_is_similar?: string[];
  what_is_different?: string[];
  why_may_not_apply?: string[];
}

export interface CitationItem {
  doc_id: string;
  title: string;
  snippet: string;
  relevance: number;
}

export interface EconomicOptionItem {
  action: string;
  cost_inr: number;
  avoided_loss_inr: number;
  net_benefit_inr: number;
  is_recommended: boolean;
}

export interface InvestigationEvidence {
  anomaly?: {
    score: number;
    threshold: number;
    severity: string;
    signals: ResidualSignal[];
  };
  environment?: {
    is_explained: boolean;
    // Fraction of the deviation environmental conditions explain, per the risk model's own
    // explains_fraction output — not a per-cause breakdown (the API does not provide one).
    explains_fraction?: number;
    ambient_temp_c?: number;
    wind_speed_ms?: number;
    irradiance_wm2?: number;
    dust_risk?: string;
  };
  peers?: {
    group_size: number;
    is_isolated: boolean;
    subject_residual_pct: number;
    peer_median_residual_pct: number;
    deviation_percentile: number;
  };
  history?: {
    cases: HistoricalCaseItem[];
  };
  knowledge?: {
    citations: CitationItem[];
  };
  economics?: {
    options: EconomicOptionItem[];
    // Total avoidable exposure across the evaluation horizon (not a daily rate — the API
    // does not report one).
    avoidable_exposure_inr: number;
  };
}

export interface InvestigationResult {
  asset_id: string;
  verdict: string;
  confidence: number;
  needle_used: string;
  requires_human_review: boolean;
  timeline: Array<{
    stage: string;
    status: "pending" | "running" | "done" | "skipped";
    detail: string;
    elapsed_ms: number;
  }>;
  evidence: InvestigationEvidence;
  intervention: {
    recommended_action: string;
    recommended_window_hours: number;
    expected_savings_inr: number;
    net_benefit_inr: number;
  };
}

export interface TimeseriesPoint {
  timestamp: string;
  actual: number;
  expected: number;
  lower_band: number;
  upper_band: number;
  residual: number;
  z_score: number;
}

export interface CleaningOption {
  option_id: string;
  label: string;
  delay_hours: number;
  cleaning_cost_inr: number;
  expected_energy_loss_inr: number;
  net_exposure_inr: number;
  break_even_days: number;
  rain_cleaning_probability: number;
  cementation_risk: boolean;
  summary: string;
  assumptions: Record<string, number>;
}

export interface SoilingZone {
  zone: string;
  inverters: number;
  soiling_loss_pct: number;
  performance_ratio: number;
  status: "normal" | "watch" | "investigate";
  worst_asset_id: string;
}

export interface SoilingResponse {
  site: string;
  updated_at: string;
  site_soiling_loss_pct: number;
  dust_risk: "low" | "moderate" | "high";
  rain_probability_48h: number;
  days_since_rain: number;
  cleaning_cost_inr: number;
  recommendation: {
    action: "wait" | "clean";
    wait_hours: number;
    rationale: string;
    breakeven_days: number;
  };
  // Absent when the advisor has no options to compare (the API omits, rather than
  // fabricates, this field in that case).
  cleaning_options?: CleaningOption[];
  zones: SoilingZone[];
}

export interface ScenarioItem {
  scenario: string;
  label: string;
  asset_type: "wind_turbine" | "solar_inverter";
  component: string;
  is_equipment_fault: boolean;
  typical_onset_days: number;
  description: string;
  expected_detection: string;
}
