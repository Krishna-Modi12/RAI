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
  source_dataset?: string;
  source_reference?: string;
  event_class?: string;
  evidence_quality?: string;
  adjudication?: {
    what_is_explicitly_known?: string;
    what_is_inferred?: string;
    what_remains_unknown?: string;
    what_source_proves?: string;
    what_source_does_not_prove?: string;
  };
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
  avoided_loss_inr: number | null;
  net_benefit_inr: number | null;
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
    avoidable_exposure_inr: number | null;
  };
  differential?: DifferentialVerdict;
}

export interface DiagnosticHypothesisItem {
  name: string;
  component: string;
  category: string;
  description: string;
  status: "supported" | "ruled_out" | "contending" | "unsupported";
  supporting_evidence: string[];
  counterevidence: string[];
  confidence_delta: number;
}

export interface DifferentialVerdict {
  dominant_hypothesis?: string | null;
  status:
    | "resolved_single_fault"
    | "resolved_operational"
    | "resolved_environmental"
    | "resolved_sensor_anomaly"
    | "competing_hypotheses"
    | "no_plausible_hypothesis";
  hypotheses: DiagnosticHypothesisItem[];
  counterevidence_summary: string[];
  abstention_rationale?: string | null;
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
    expected_savings_inr: number | null;
    net_benefit_inr: number | null;
  };
  economic_decision?: EconomicDecision | null;
}

export interface EconomicDecision {
  decision: "INTERVENE" | "INSPECT" | "MONITOR" | "WAIT" | "ABSTAIN";
  status: string;
  asset_id: string;
  component: string | null;
  why: string;
  assumptions: Array<{
    name: string;
    value: number | string | null;
    state: "OBSERVED" | "ASSUMED" | "RETRIEVED" | "INFERRED" | "UNKNOWN";
    source: string;
    limitation?: string | null;
  }>;
  uncertainty: string[];
  alternatives: string[];
  energy_loss_inr: number | null;
  downtime_cost_inr: number | null;
  intervention_cost_inr: number | null;
  inspection_cost_inr: number | null;
  expected_waiting_consequence_inr: number | null;
  information_value_inr: number | null;
  recommended_option_id: string | null;
  robustness: string;
  options: Array<Record<string, unknown>>;
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

export type WorkOrderStatus =
  | "proposed_awaiting_human_approval"
  | "approved_scheduled"
  | "rejected"
  | "in_progress"
  | "completed"
  | "cancelled";

export type WorkOrderPriority = "low" | "medium" | "high" | "emergency";

export type FieldResolution =
  | "confirmed_fault"
  | "false_alarm"
  | "early_inspection_prevented_failure"
  | "no_fault_found"
  | "maintenance_deferred";

export interface WorkOrderFeedback {
  feedback_id: string;
  ticket_id: string;
  technician_id: string;
  submitted_at: string;
  resolution: FieldResolution;
  findings: string;
  component_inspected: string;
  actual_downtime_hours: number;
  actual_parts_cost_inr: number;
  notes?: string;
}

export interface WorkOrder {
  ticket_id: string;
  asset_id: string;
  asset_name: string;
  site: string;
  component: string;
  action: string;
  priority: WorkOrderPriority;
  deadline_hours: number;
  status: WorkOrderStatus;
  created_at: string;
  created_by: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  feedback?: WorkOrderFeedback[];
}

export interface SiteWeatherWindow {
  site: string;
  asset_type: string;
  current_wind_speed_ms: number;
  current_ambient_temp_c: number;
  current_rain_probability_pct: number;
  climb_safe: boolean;
  electrical_safe: boolean;
  status: "SAFE" | "MARGINAL" | "UNSAFE";
  safety_rationale: string;
  safe_window_hours: number;
}

export interface CrewAssignment {
  assignment_id: string;
  crew_id: string;
  site: string;
  ticket_id: string;
  asset_id: string;
  component: string;
  priority: string;
  action: string;
  estimated_duration_hours: number;
  scheduled_start_hour_offset: number;
  weather_status: string;
  projected_avoided_loss_inr: number;
  dispatch_readiness: "READY_IMMEDIATE" | "AWAITING_WEATHER_WINDOW" | "PENDING_APPROVAL";
}

export interface DispatchPlan {
  generated_at: string;
  site_windows: Record<string, SiteWeatherWindow>;
  assignments: CrewAssignment[];
  unassigned_orders: Array<Record<string, unknown>>;
  active_crews_count: number;
  total_avoided_loss_inr: number;
  total_scheduled_hours: number;
}

export interface ClosedLoopMetrics {
  total_orders: number;
  pending_approval: number;
  approved: number;
  in_progress: number;
  completed: number;
  rejected: number;
  total_feedbacks: number;
  confirmed_faults: number;
  concordance_rate_pct: number;
  indexed_field_cases_count: number;
  total_academic_real_cases_count: number;
  total_real_retrieval_pool_size: number;
  total_parts_cost_inr: number;
  total_downtime_hours: number;
  mean_downtime_hours: number;
}

