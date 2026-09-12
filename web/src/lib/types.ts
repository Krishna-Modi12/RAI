/**
 * TypeScript types matching docs/API_CONTRACT.md
 */

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  timestamp: string;
  data_freshness_s: number;
  models_loaded: string[];
  assets_active: number;
  needle_available: boolean;
  needle_confidence_threshold: number;
}

export interface FleetOverview {
  total_assets: number;
  assets_at_risk: number;
  offline_assets: number;
  fleet_health: number;
  generation_kw: number;
  expected_generation_kw: number;
  availability_pct: number;
  revenue_at_risk_inr_per_day: number;
}

export interface PriorityQueueItem {
  asset_id: string;
  asset_name: string;
  asset_type: "wind" | "solar";
  site_name: string;
  risk_score: number;
  risk_band: "low" | "elevated" | "high" | "critical";
  revenue_at_risk_inr: number;
  dominant_signal: string;
  deadline_hours: number;
  requires_human_review: boolean;
  headline: string;
}

export interface FleetAssetItem {
  asset_id: string;
  name: string;
  asset_type: "wind" | "solar";
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

export interface PeerComparisonItem {
  peer_id: string;
  power_kw: number;
  residual_pct: number;
  is_subject: boolean;
}

export interface HistoricalCaseItem {
  case_id: string;
  similarity: number;
  component: string;
  fault_mode: string;
  outcome: string;
  lead_time_days: number;
  repair_cost_inr: number;
  source: string;
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
    loss_breakdown: Record<string, number>;
    ambient_temp_c?: number;
    wind_speed_ms?: number;
    irradiance_wm2?: number;
    dust_risk?: string;
  };
  peers?: {
    group_size: number;
    peer_z_score: number;
    is_isolated: boolean;
    distribution: PeerComparisonItem[];
  };
  history?: {
    cases: HistoricalCaseItem[];
  };
  knowledge?: {
    citations: CitationItem[];
  };
  economics?: {
    options: EconomicOptionItem[];
    daily_exposure_inr: number;
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

export interface CleaningAdvisorOption {
  action: string;
  recommended_window_hours: number;
  expected_energy_recovered_kwh: number;
  cleaning_cost_inr: number;
  avoided_loss_inr: number;
  net_benefit_inr: number;
  break_even_days: number;
  confidence: number;
  is_recommended: boolean;
  rationale: string;
}

export interface SoilingResponse {
  asset_id: string;
  site: string;
  timestamp: string;
  dust_risk: "low" | "moderate" | "high" | "severe";
  dust_concentration_ug_m3: number;
  aod_550: number;
  pm10_ug_m3: number;
  rain_probability_24h: number;
  rain_wash_probability: number;
  mud_cementation_risk: "low" | "medium" | "high";
  soiling_ratio: number;
  current_soiling_loss_pct: number;
  daily_accumulation_rate_pct: number;
  last_cleaning_days_ago: number;
  advisor_options: CleaningAdvisorOption[];
  loss_decomposition: {
    total_loss_pct: number;
    irradiance_loss_pct: number;
    soiling_loss_pct: number;
    thermal_loss_pct: number;
    curtailment_loss_pct: number;
    equipment_loss_pct: number;
    unexplained_loss_pct: number;
  };
}

export interface ScenarioItem {
  id: string;
  name: string;
  asset_type: "wind" | "solar";
  description: string;
  category: "equipment" | "environment" | "sensor";
  affected_signals: string[];
  duration_hours: number;
}
