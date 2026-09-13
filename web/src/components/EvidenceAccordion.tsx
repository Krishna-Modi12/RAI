"use client";

import React, { useState, useEffect } from "react";
import { InvestigationResult, WorkOrder } from "../lib/types";
import { formatINR, formatZScore } from "../lib/format";
import { getWorkOrders, proposeWorkOrder } from "../lib/api";
import WorkOrderModal from "./WorkOrderModal";
import {
  AlertTriangle,
  CloudSun,
  Users,
  Clock,
  BookOpen,
  DollarSign,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Wrench,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import StatusPill from "./StatusPill";

interface EvidenceAccordionProps {
  investigation: InvestigationResult;
}

// A historical case's source_type ("EXTERNAL_REAL" vs "INTERNAL_SYNTHETIC") only says where the
// record came from, not whether it was a confirmed equipment failure. Several EXTERNAL_REAL event
// classes (operational trips, scheduled maintenance, weather-driven curtailment) are non-fault
// events by definition and must not read as "confirmed failure" just because they are real.
const CONFIRMED_FAILURE_EVENT_CLASS = "REAL_VERIFIED_EVENT";

const EVENT_CLASS_GLOSS: Record<string, string> = {
  REAL_VERIFIED_EVENT: "confirmed component failure",
  REAL_OPERATIONAL_EVENT: "operational trip — no confirmed hardware damage",
  REAL_MAINTENANCE_EVENT: "maintenance intervention — not a failure",
  ENVIRONMENTAL_EVENT: "weather/environment-driven — not a fault",
};

function isConfirmedFailure(eventClass?: string | null): boolean {
  return eventClass === CONFIRMED_FAILURE_EVENT_CLASS;
}

export default function EvidenceAccordion({ investigation }: EvidenceAccordionProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    anomaly: true,
    environment: true,
    peers: true,
    history: true,
    knowledge: true,
    economics: true,
    decision: true,
    workorders: true,
  });
  const [historyFilter, setHistoryFilter] = useState<"all" | "real" | "synthetic">("all");

  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"approve" | "reject" | "feedback">("approve");
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadWorkOrders() {
      const res = await getWorkOrders(investigation.asset_id);
      if (!cancelled && res.data) {
        setWorkOrders(res.data);
      }
    }
    loadWorkOrders();
    return () => {
      cancelled = true;
    };
  }, [investigation.asset_id]);

  const handleApproveClick = async () => {
    const pending = workOrders.find((wo) => wo.status === "proposed_awaiting_human_approval");
    if (pending) {
      setSelectedWorkOrder(pending);
      setModalMode("approve");
      setModalOpen(true);
    } else {
      const dominantSignal = investigation.evidence.anomaly?.signals?.find((s) => s.dominant)?.name || "system";
      const created = await proposeWorkOrder({
        asset_id: investigation.asset_id,
        component: dominantSignal,
        action: investigation.intervention.recommended_action || "Inspect and verify asset condition",
        deadline_hours: investigation.intervention.recommended_window_hours || 72,
        priority: "high",
        created_by: "rai_agent_recommendation",
      });
      if (created) {
        setWorkOrders((prev) => [created, ...prev]);
        setSelectedWorkOrder(created);
        setModalMode("approve");
        setModalOpen(true);
      }
    }
  };

  const handleOpenAction = (wo: WorkOrder, mode: "approve" | "reject" | "feedback") => {
    setSelectedWorkOrder(wo);
    setModalMode(mode);
    setModalOpen(true);
  };

  const handleModalSuccess = (updated: WorkOrder) => {
    setWorkOrders((prev) => {
      const idx = prev.findIndex((w) => w.ticket_id === updated.ticket_id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updated;
        return next;
      }
      return [updated, ...prev];
    });
  };

  const toggleSection = (id: string) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };


  const { evidence, intervention, verdict, confidence, needle_used, requires_human_review } =
    investigation;

  return (
    <div className="space-y-4">
      {/* 1. ANOMALY DETECTION */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("anomaly")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-[var(--critical)]" />
            <span>1. Anomaly Detection & Signal Residuals</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              OBSERVED
            </span>
            <StatusPill band={evidence.anomaly?.severity === "critical" ? "critical" : "high"} />
          </div>
          {openSections.anomaly ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.anomaly && (
          <div className="p-4 space-y-3">
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left">
                    <th className="py-2 px-3">Signal Name</th>
                    <th className="py-2 px-3 text-right">Actual</th>
                    <th className="py-2 px-3 text-right">Expected</th>
                    <th className="py-2 px-3 text-right">Residual</th>
                    <th className="py-2 px-3 text-right">Z-Score</th>
                    <th className="py-2 px-3 text-right">Trend/Day</th>
                    <th className="py-2 px-3 text-center">Deviation Bar (±3σ)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {evidence.anomaly?.signals.map((sig, i) => (
                    <tr
                      key={i}
                      className={`hover:bg-[var(--surface-sunken)] ${
                        sig.dominant ? "bg-[var(--accent-surface)]/30 font-medium" : ""
                      }`}
                    >
                      <td className="py-2 px-3">
                        <div className="flex items-center space-x-1.5 font-sans">
                          {sig.dominant && (
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] flex-shrink-0" />
                          )}
                          <span className="text-[var(--text-primary)]">{sig.name}</span>
                          {sig.dominant && (
                            <span className="text-[9px] font-mono px-1 py-0.5 bg-[var(--accent-surface)] text-[var(--accent)] rounded-[2px] whitespace-nowrap">
                              DOMINANT
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-right whitespace-nowrap">{sig.actual.toFixed(1)}</td>
                      <td className="py-2 px-3 text-right text-[var(--text-secondary)] whitespace-nowrap">
                        {sig.expected.toFixed(1)}
                      </td>
                      <td
                        className={`py-2 px-3 text-right font-semibold whitespace-nowrap ${
                          sig.residual > 0 ? "text-[var(--critical)]" : "text-[var(--series-1)]"
                        }`}
                      >
                        {sig.residual > 0 ? "+" : ""}
                        {sig.residual.toFixed(1)}
                      </td>
                      <td
                        className={`py-2 px-3 text-right font-semibold whitespace-nowrap ${
                          Math.abs(sig.z_score) >= 3
                            ? "text-[var(--critical)]"
                            : Math.abs(sig.z_score) >= 2
                            ? "text-[var(--warn-ink)]"
                            : "text-[var(--text-secondary)]"
                        }`}
                      >
                        {formatZScore(sig.z_score)}σ
                      </td>
                      <td className="py-2 px-3 text-right text-[var(--text-secondary)] whitespace-nowrap">
                        {sig.trend_per_day > 0 ? "+" : ""}
                        {sig.trend_per_day.toFixed(2)}
                      </td>
                      <td className="py-2 w-32 px-2">
                        <div className="w-28 h-2 bg-[var(--surface-sunken)] rounded-[1px] relative mx-auto border border-[var(--border)]">
                          <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-[var(--border-strong)]" />
                          <div
                            className={`absolute top-0 bottom-0 ${
                              sig.z_score > 0
                                ? "bg-[var(--critical)] left-1/2"
                                : "bg-[var(--series-1)] right-1/2"
                            }`}
                            style={{
                              width: `${Math.min(50, (Math.abs(sig.z_score) / 4) * 50)}%`,
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: POST /api/assets/{`{id}`}/investigate · residual_anomaly_detector
            </div>
          </div>
        )}
      </div>

      {/* 2. ENVIRONMENTAL CONTEXT */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("environment")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <CloudSun className="w-4 h-4 text-[var(--info)]" />
            <span>2. Environmental Attribution & Weather Context</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              OBSERVED
            </span>
            <StatusPill
              status={evidence.environment?.is_explained ? "nominal" : "warning"}
              label={evidence.environment?.is_explained ? "Explained by Environment" : "Unexplained by Environment"}
            />
          </div>
          {openSections.environment ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.environment && (
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
                <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Ambient Temp</div>
                <div className="text-sm font-semibold mt-0.5">{evidence.environment?.ambient_temp_c ?? 32.4}°C</div>
              </div>
              <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
                <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Wind / Irradiance</div>
                <div className="text-sm font-semibold mt-0.5">
                  {evidence.environment?.wind_speed_ms
                    ? `${evidence.environment.wind_speed_ms} m/s`
                    : `${evidence.environment?.irradiance_wm2 ?? 780} W/m²`}
                </div>
              </div>
              <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
                <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Dust Exposure</div>
                <div className="text-sm font-semibold mt-0.5 capitalize text-[var(--warn-ink)]">
                  {evidence.environment?.dust_risk ?? "low"}
                </div>
              </div>
              <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
                <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Attribution Verdict</div>
                <div className="text-sm font-semibold mt-0.5 text-[var(--text-primary)]">
                  {evidence.environment?.is_explained ? "Environmental Loss" : "Equipment Deficit"}
                </div>
              </div>
            </div>

            {/* Environmental Attribution */}
            {evidence.environment?.explains_fraction != null && (
              <div className="space-y-1.5 pt-2">
                <div className="text-[11px] font-sans font-medium text-[var(--text-secondary)]">
                  Environmental Attribution:
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-mono">
                  <span className="px-2 py-1 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
                    <span className="text-[var(--text-tertiary)] uppercase mr-1">explains:</span>
                    <span className="font-semibold text-[var(--text-primary)]">
                      {(evidence.environment.explains_fraction * 100).toFixed(1)}%
                    </span>
                    <span className="text-[var(--text-tertiary)]"> of deviation</span>
                  </span>
                </div>
              </div>
            )}
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: Open-Meteo CAMS Dust / NASA POWER / pvlib clear_sky normalization
            </div>
          </div>
        )}
      </div>

      {/* 3. PEER COMPARISON */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("peers")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <Users className="w-4 h-4 text-[var(--accent)]" />
            <span>3. Fleet & Peer Cohort Isolation</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              OBSERVED
            </span>
            <StatusPill
              status={evidence.peers?.is_isolated ? "critical" : "nominal"}
              label={evidence.peers?.is_isolated ? "Isolated Asset Anomaly" : "Fleet-Wide Congruence"}
            />
          </div>
          {openSections.peers ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.peers && (
          <div className="p-4 space-y-3">
            <p className="text-xs font-sans text-[var(--text-secondary)]">
              Comparing against a cohort of {evidence.peers?.group_size ?? 8} identical-configuration assets on the same feeder. Subject deviates further than{" "}
              <span className="font-mono font-semibold text-[var(--critical)]">
                {evidence.peers?.deviation_percentile?.toFixed(0) ?? "—"}%
              </span>{" "}
              of the cohort.
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded-[2px] border bg-[var(--accent-surface)] border-[var(--accent)] font-semibold">
                <div className="flex justify-between">
                  <span>Subject</span>
                  <span className="text-[9px] text-[var(--accent)]">TARGET</span>
                </div>
                <div className="text-[10px] text-[var(--text-tertiary)] mt-1">
                  residual: {(evidence.peers?.subject_residual_pct ?? 0) > 0 ? "+" : ""}
                  {evidence.peers?.subject_residual_pct?.toFixed(1) ?? "—"}%
                </div>
              </div>
              <div className="p-2 rounded-[2px] border bg-[var(--surface-sunken)] border-[var(--border)]">
                <div>Peer Median (n={evidence.peers?.group_size ?? 0})</div>
                <div className="text-[10px] text-[var(--text-tertiary)] mt-1">
                  residual: {(evidence.peers?.peer_median_residual_pct ?? 0) > 0 ? "+" : ""}
                  {evidence.peers?.peer_median_residual_pct?.toFixed(1) ?? "—"}%
                </div>
              </div>
            </div>
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: POST /api/assets/{`{id}`}/investigate · packet.peers
            </div>
          </div>
        )}
      </div>

      {/* 4. HISTORICAL CASE MEMORY */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("history")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <Clock className="w-4 h-4 text-[var(--warn-ink)]" />
            <span>4. Similar Historical Cases (Contextual Evidence)</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--accent-surface)] border border-[var(--accent)] text-[var(--accent)] rounded-[2px]">
              RETRIEVED
            </span>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              {evidence.history?.cases.length ?? 0} matches
            </span>
          </div>
          {openSections.history ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.history && (
          <div className="p-4 space-y-3">
            {/* Partition Filter Control */}
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase tracking-wider">
                Corpus Partition:
              </span>
              <div className="inline-flex rounded-[2px] border border-[var(--border)] bg-[var(--surface-inset)] p-0.5 text-[10px] font-mono">
                <button
                  type="button"
                  onClick={() => setHistoryFilter("all")}
                  className={`px-2 py-0.5 rounded-[1px] transition-colors ${
                    historyFilter === "all"
                      ? "bg-[var(--surface-raised)] text-[var(--text-primary)] font-semibold shadow-xs"
                      : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  ALL ({evidence.history?.cases.length ?? 0})
                </button>
                <button
                  type="button"
                  onClick={() => setHistoryFilter("real")}
                  className={`px-2 py-0.5 rounded-[1px] transition-colors ${
                    historyFilter === "real"
                      ? "bg-emerald-950/60 text-emerald-300 font-semibold border border-emerald-500/40"
                      : "text-[var(--text-tertiary)] hover:text-emerald-400"
                  }`}
                >
                  REAL ONLY ({(evidence.history?.cases ?? []).filter(c => c.source_type === "EXTERNAL_REAL").length})
                </button>
                <button
                  type="button"
                  onClick={() => setHistoryFilter("synthetic")}
                  className={`px-2 py-0.5 rounded-[1px] transition-colors ${
                    historyFilter === "synthetic"
                      ? "bg-amber-950/60 text-amber-300 font-semibold border border-amber-500/40"
                      : "text-[var(--text-tertiary)] hover:text-amber-400"
                  }`}
                >
                  SYNTHETIC ({(evidence.history?.cases ?? []).filter(c => c.source_type !== "EXTERNAL_REAL").length})
                </button>
              </div>
            </div>

            {(evidence.history?.cases ?? [])
              .filter((c) => {
                if (historyFilter === "real") return c.source_type === "EXTERNAL_REAL";
                if (historyFilter === "synthetic") return c.source_type !== "EXTERNAL_REAL";
                return true;
              })
              .map((c) => {
                const isReal = c.source_type === "EXTERNAL_REAL";
                return (
                  <div
                    key={c.case_id}
                    className={`p-3 bg-[var(--surface-sunken)] border rounded-[3px] space-y-2 text-xs ${
                      isReal
                        ? "border-emerald-500/30 shadow-[inset_0_1px_0_rgba(16,185,129,0.08)]"
                        : "border-[var(--border)]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-semibold text-[var(--text-primary)]">
                          {c.case_id} · {c.component}
                        </span>
                        {isReal ? (
                          <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-emerald-950/50 border border-emerald-500/50 text-emerald-400 rounded-[2px] flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                            REAL HISTORICAL CASE
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-amber-950/40 border border-amber-500/40 text-amber-400 rounded-[2px]">
                            SYNTHETIC SCENARIO
                          </span>
                        )}
                        {c.event_class && (
                          <span
                            title={EVENT_CLASS_GLOSS[c.event_class] ?? undefined}
                            className={`px-1.5 py-0.5 font-mono text-[9px] rounded-[2px] border ${
                              isConfirmedFailure(c.event_class)
                                ? "bg-red-950/40 border-red-500/40 text-red-400 font-semibold"
                                : "bg-[var(--surface-raised)] border-[var(--border)] text-[var(--text-secondary)]"
                            }`}
                          >
                            {c.event_class}
                            {EVENT_CLASS_GLOSS[c.event_class] ? ` — ${EVENT_CLASS_GLOSS[c.event_class]}` : ""}
                          </span>
                        )}
                        {isReal && !c.event_class && (
                          <span className="px-1.5 py-0.5 font-mono text-[9px] bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-tertiary)] rounded-[2px]">
                            event class not recorded — do not assume confirmed failure
                          </span>
                        )}
                      </div>
                      <span className="font-mono px-1.5 py-0.5 bg-[var(--accent-surface)] text-[var(--accent)] rounded-[2px] text-[10px]">
                        Cosine Similarity: {(c.similarity * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div
                      className={`font-medium flex items-center justify-between ${
                        isReal && !isConfirmedFailure(c.event_class)
                          ? "text-[var(--text-primary)]"
                          : "text-[var(--warn-ink)]"
                      }`}
                    >
                      <span>{c.fault_mode}</span>
                      <span className="text-[10px] font-mono text-[var(--text-tertiary)]">{c.source}</span>
                    </div>

                    <p className="text-[var(--text-secondary)] text-[11px] leading-relaxed">
                      {c.outcome}
                    </p>

                    <div className="grid gap-2 sm:grid-cols-2 pt-1 text-[11px]">
                      <div className="p-2 rounded-[2px] bg-[var(--surface-raised)]/60 border border-[var(--border)]/70">
                        <div className="font-semibold text-[var(--text-primary)] flex items-center gap-1 text-[10px] uppercase font-mono tracking-wider">
                          Why matched / Similarities
                        </div>
                        <div className="text-[var(--text-secondary)] mt-0.5">
                          {(c.why_matched ?? []).join(" ") || (c.what_is_similar ?? []).join(", ") || "Residual feature pattern matched baseline vector"}
                        </div>
                      </div>
                      <div className="p-2 rounded-[2px] bg-[var(--surface-raised)]/60 border border-[var(--border)]/70">
                        <div className="font-semibold text-[var(--text-primary)] flex items-center gap-1 text-[10px] uppercase font-mono tracking-wider">
                          What differs / Boundary
                        </div>
                        <div className="text-[var(--text-secondary)] mt-0.5">
                          {(c.what_is_different ?? []).join(", ") || "No material difference recorded"}
                        </div>
                      </div>
                    </div>

                    {c.why_may_not_apply && c.why_may_not_apply.length > 0 && (
                      <div className="p-1.5 bg-amber-950/20 border border-amber-500/20 rounded-[2px] text-[10px] text-amber-300 font-mono">
                        Applicability limitations: {c.why_may_not_apply.join("; ")}
                      </div>
                    )}

                    <div className="flex items-center space-x-4 pt-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                      <span>Lead Time: {c.lead_time_days ?? "not evaluated"} days</span>
                      <span>Avoided Cost: {c.repair_cost_inr == null ? "not evaluated" : formatINR(c.repair_cost_inr).display}</span>
                      <span className="uppercase text-[9px]">
                        Provenance: {c.source_type ?? (isReal ? "EXTERNAL_REAL" : "INTERNAL_SYNTHETIC")}
                      </span>
                    </div>

                    <div className="text-[10px] text-[var(--warn-ink)] flex items-center justify-between pt-1 border-t border-[var(--border)]/40">
                      <span>Historical context only; it does not confirm the current diagnosis.</span>
                      <span className="text-[var(--text-tertiary)] font-mono text-[9px]">
                        Corpus: {isReal ? "EXTERNAL_REAL (Audited Record)" : "INTERNAL_SYNTHETIC (Simulation)"}
                      </span>
                    </div>
                  </div>
                );
              })}
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: SQLite Trajectory Embeddings · cosine_knn_retriever · Partition: {historyFilter.toUpperCase()}
            </div>
          </div>
        )}
      </div>

      {/* 5. DOMAIN KNOWLEDGE & SOPS (FTS5) */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("knowledge")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <BookOpen className="w-4 h-4 text-[var(--accent)]" />
            <span>5. Technical Knowledge & OEM SOP Citations</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--accent-surface)] border border-[var(--accent)] text-[var(--accent)] rounded-[2px]">
              RETRIEVED
            </span>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              SQLite FTS5 RAG
            </span>
          </div>
          {openSections.knowledge ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.knowledge && (
          <div className="p-4 space-y-3">
            {evidence.knowledge?.citations.map((cite, i) => (
              <div
                key={i}
                className="p-3 border-l-2 border-[var(--accent)] bg-[var(--surface-sunken)] space-y-1 text-xs"
              >
                <div className="flex justify-between items-center font-semibold text-[var(--text-primary)] font-sans">
                  <span>{cite.title}</span>
                  <span className="font-mono text-[10px] text-[var(--text-tertiary)]">
                    doc: {cite.doc_id}
                  </span>
                </div>
                <blockquote className="text-[var(--text-secondary)] italic text-[11px] leading-relaxed">
                  &ldquo;{cite.snippet}&rdquo;
                </blockquote>
              </div>
            ))}
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: GET /api/knowledge/search · sqlite_fts5_bm25_index (221 sections indexed)
            </div>
          </div>
        )}
      </div>

      {/* 6. ECONOMIC CONSEQUENCE ENGINE */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("economics")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <DollarSign className="w-4 h-4 text-[var(--ok)]" />
            <span>6. Techno-Economic Intervention Trade-Offs</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              INFERRED
            </span>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              Avoidable Exposure: {formatINR(evidence.economics?.avoidable_exposure_inr).display}
            </span>
          </div>
          {openSections.economics ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.economics && (
          <div className="p-4 space-y-3">
            {investigation.economic_decision && (
              <div className="grid gap-3 md:grid-cols-[auto_1fr] p-3 bg-[var(--accent-surface)]/20 border border-[var(--accent-border)] rounded-[3px]">
                <div>
                  <div className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase">Decision support</div>
                  <div className="text-lg font-mono font-semibold text-[var(--text-primary)] mt-1">
                    {investigation.economic_decision.decision}
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-tertiary)] mt-1">
                    {investigation.economic_decision.status.replaceAll("_", " ")}
                  </div>
                </div>
                <div className="space-y-2 text-xs text-[var(--text-secondary)]">
                  <p>{investigation.economic_decision.why}</p>
                  <p className="text-[10px] text-[var(--text-tertiary)]">
                    Robustness: {investigation.economic_decision.robustness.replaceAll("_", " ")} ·
                    Information value: {investigation.economic_decision.information_value_inr == null
                      ? "not estimated"
                      : formatINR(investigation.economic_decision.information_value_inr).display}
                  </p>
                  {investigation.economic_decision.uncertainty.length > 0 && (
                    <div className="text-[10px] text-[var(--warn-ink)]">
                      Uncertainty: {investigation.economic_decision.uncertainty[0]}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left">
                    <th className="py-2">Intervention Strategy</th>
                    <th className="py-2 text-right">Intervention Cost</th>
                    <th className="py-2 text-right">Projected Avoidable Exposure</th>
                    <th className="py-2 text-right">Modelled Net Benefit</th>
                    <th className="py-2 text-center">Recommendation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {evidence.economics?.options.map((opt, i) => (
                    <tr
                      key={i}
                      className={`hover:bg-[var(--surface-sunken)] ${
                        opt.is_recommended ? "bg-[var(--ok-surface)]/30 font-semibold" : ""
                      }`}
                    >
                      <td className="py-2.5 font-sans flex items-center space-x-1.5">
                        {opt.is_recommended && (
                          <span className="w-2 h-2 rounded-full bg-[var(--ok)]" />
                        )}
                        <span>{opt.action}</span>
                      </td>
                      <td className="py-2.5 text-right">{formatINR(opt.cost_inr).display}</td>
                      <td className="py-2.5 text-right">{formatINR(opt.avoided_loss_inr).display}</td>
                      <td
                        className={`py-2.5 text-right ${
                          opt.net_benefit_inr != null && opt.net_benefit_inr > 0
                            ? "text-[var(--ok)]"
                            : "text-[var(--critical)]"
                        }`}
                      >
                        {opt.net_benefit_inr == null ? "not evaluated" : formatINR(opt.net_benefit_inr).display}
                      </td>
                      <td className="py-2.5 text-center">
                        {opt.is_recommended ? (
                          <span className="px-2 py-0.5 bg-[var(--ok-surface)] text-[var(--ok)] border border-[var(--ok)] rounded-[2px] text-[10px]">
                            RECOMMENDED
                          </span>
                        ) : (
                          <span className="text-[var(--text-tertiary)] text-[10px]">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: rai.economics.engine · deterministic_npv_calculator
            </div>
          </div>
        )}
      </div>

      {/* 7. DECISION & CONFIDENCE GATING */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("decision")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <CheckCircle className="w-4 h-4 text-[var(--accent)]" />
            <span>7. Decision Synthesis & Needle Model Gating</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              INFERRED
            </span>
            <span className="text-[10px] font-mono text-[var(--accent)] font-semibold">
              Confidence: {(confidence * 100).toFixed(0)}%
            </span>
          </div>
          {openSections.decision ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.decision && (
          <div className="p-4 space-y-3">
            <div className="p-3 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px] space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-[11px] font-mono text-[var(--text-tertiary)] uppercase">
                    Consensus Verdict
                  </div>
                  <div className="text-sm font-semibold text-[var(--text-primary)] mt-0.5">
                    {verdict}
                  </div>
                </div>
                <StatusPill
                  status={requires_human_review ? "warning" : "nominal"}
                  label={requires_human_review ? "Human Escalation Required" : "Automated Execution Allowed"}
                />
              </div>

              {/* Confidence Track Bar with 0.80 Threshold Rule */}
              <div className="pt-2 space-y-1">
                <div className="flex justify-between text-[11px] font-mono text-[var(--text-secondary)]">
                  <span>Reasoning Confidence: {(confidence * 100).toFixed(1)}%</span>
                  <span>Threshold: 80.0%</span>
                </div>
                <div className="w-full h-2 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[1px] relative">
                  <div
                    className="absolute left-[80%] top-0 bottom-0 w-[1.5px] bg-[var(--text-primary)] z-10"
                    title="80% Gating Threshold"
                  />
                  <div
                    className={`h-full ${
                      confidence >= 0.8 ? "bg-[var(--accent)]" : "bg-[var(--warn)]"
                    }`}
                    style={{ width: `${Math.min(100, confidence * 100)}%` }}
                  />
                </div>
                <div className="text-[10px] font-mono text-[var(--text-tertiary)] flex justify-between">
                  <span>Engine: {needle_used} (calibrated)</span>
                  <span>
                    Status:{" "}
                    {confidence >= 0.8 ? "Passed Gating Gate" : "Below Gate — Gated to Operator"}
                  </span>
                </div>
              </div>
            </div>

            {/* Recommended Action Summary */}
            <div className="p-3 bg-[var(--accent-surface)]/20 border border-[var(--accent-border)] rounded-[3px] flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-[10px] font-mono text-[var(--accent)] uppercase font-semibold">
                  Prescribed Operational Intervention
                </div>
                <div className="text-xs font-semibold text-[var(--text-primary)] mt-0.5">
                  {intervention.recommended_action}
                  {intervention.recommended_window_hours > 0
                    ? ` (Within ${intervention.recommended_window_hours} Hours)`
                    : ""}
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right font-mono text-xs">
                  <div className="text-[10px] text-[var(--text-tertiary)]">Net Project NPV</div>
                  <div className="font-semibold text-[var(--ok)]">
                    {intervention.net_benefit_inr == null
                      ? "not evaluated"
                      : `+${formatINR(intervention.net_benefit_inr).display}`}
                  </div>
                </div>
                <button
                  onClick={handleApproveClick}
                  className="px-3.5 py-1.5 bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)] font-sans text-xs font-medium rounded-[2px] transition-colors shadow-sm flex items-center space-x-1.5 cursor-pointer"
                >
                  <ClipboardList className="w-3.5 h-3.5" />
                  <span>Authorize Work Order</span>
                </button>
              </div>
            </div>

            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: needle2_agent_evidence_synthesis · figures computed deterministically, not LLM-authored
            </div>
          </div>
        )}
      </div>

      {/* 8. OPERATIONAL WORK ORDERS & FIELD FEEDBACK HISTORY */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <button
          onClick={() => toggleSection("workorders")}
          className="w-full h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <div className="flex items-center space-x-2.5">
            <ClipboardList className="w-4 h-4 text-[var(--accent)]" />
            <span>8. Operational Work Orders & Ground-Truth Field Ledger</span>
            <span className="px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-secondary)] rounded-[2px]">
              AUDIT LEDGER
            </span>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              {workOrders.length} {workOrders.length === 1 ? "record" : "records"}
            </span>
          </div>
          {openSections.workorders ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {openSections.workorders && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <span className="text-xs text-[var(--text-secondary)] font-medium">
                Asset Maintenance Lifecycle Controls
              </span>
              <button
                onClick={handleApproveClick}
                className="px-3 py-1.5 bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)] font-sans text-xs font-semibold rounded-[2px] transition-colors flex items-center space-x-1.5 shadow-xs"
              >
                <ClipboardList className="w-3.5 h-3.5" />
                <span>Propose Work Order</span>
              </button>
            </div>

            {workOrders.length === 0 ? (
              <div className="p-4 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px] text-center text-xs text-[var(--text-tertiary)]">
                No maintenance work orders have been logged yet for asset {investigation.asset_id}.
                Click <span className="text-[var(--text-primary)] font-medium">Propose Work Order</span> to dispatch an intervention.
              </div>
            ) : (
              <div className="space-y-3">
                {workOrders.map((wo) => {
                  const isPending = wo.status === "proposed_awaiting_human_approval";
                  const isApproved = wo.status === "approved_scheduled";
                  const isCompleted = wo.status === "completed";
                  const isRejected = wo.status === "rejected";

                  return (
                    <div
                      key={wo.ticket_id}
                      className="p-3.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px] space-y-2.5"
                    >
                      {/* Ticket Header Row */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                            {wo.ticket_id}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 text-[9px] font-mono font-medium uppercase rounded-[2px] border ${
                              isApproved
                                ? "bg-[var(--ok-surface)] text-[var(--ok)] border-[var(--ok)]/40"
                                : isCompleted
                                ? "bg-[var(--accent-surface)] text-[var(--accent)] border-[var(--accent-border)]"
                                : isRejected
                                ? "bg-[var(--critical-surface)]/20 text-[var(--critical)] border-[var(--critical)]/40"
                                : "bg-[var(--surface-inset)] text-[var(--warn-ink)] border-[var(--warn-ink)]/40"
                            }`}
                          >
                            {wo.status.replaceAll("_", " ")}
                          </span>
                          <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase">
                            Priority: {wo.priority} · {wo.deadline_hours}h
                          </span>
                        </div>

                        {/* Action buttons based on lifecycle state */}
                        <div className="flex items-center space-x-2">
                          {isPending && (
                            <>
                              <button
                                onClick={() => handleOpenAction(wo, "approve")}
                                className="px-2.5 py-1 bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)] font-sans text-[11px] font-medium rounded-[2px] transition-colors flex items-center space-x-1"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Approve</span>
                              </button>
                              <button
                                onClick={() => handleOpenAction(wo, "reject")}
                                className="px-2.5 py-1 bg-[var(--surface-inset)] hover:bg-[var(--critical-surface)]/20 text-[var(--critical)] border border-[var(--border)] hover:border-[var(--critical)]/40 font-sans text-[11px] font-medium rounded-[2px] transition-colors flex items-center space-x-1"
                              >
                                <XCircle className="w-3 h-3" />
                                <span>Reject</span>
                              </button>
                            </>
                          )}
                          {(isApproved || isCompleted) && (
                            <button
                              onClick={() => handleOpenAction(wo, "feedback")}
                              className="px-2.5 py-1 bg-[var(--surface-raised)] hover:bg-[var(--surface-inset)] text-[var(--text-primary)] border border-[var(--border)] font-sans text-[11px] font-medium rounded-[2px] transition-colors flex items-center space-x-1"
                            >
                              <Wrench className="w-3 h-3 text-[var(--accent)]" />
                              <span>{isCompleted ? "Add Inspection Notes" : "Log Field Feedback"}</span>
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Ticket Details */}
                      <div className="text-xs text-[var(--text-secondary)]">
                        <span className="font-semibold text-[var(--text-primary)]">{wo.component}:</span> {wo.action}
                      </div>

                      {/* Audit Log / Rejection Reason */}
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-mono text-[var(--text-tertiary)] pt-1 border-t border-[var(--border)]">
                        <span>Created: {new Date(wo.created_at).toLocaleString()} ({wo.created_by})</span>
                        {wo.approved_by && (
                          <span className="text-[var(--ok)]">
                            Approved by {wo.approved_by} on {wo.approved_at ? new Date(wo.approved_at).toLocaleDateString() : "—"}
                          </span>
                        )}
                        {wo.rejected_by && (
                          <span className="text-[var(--critical)]">
                            Rejected by {wo.rejected_by}: &quot;{wo.rejection_reason}&quot;
                          </span>
                        )}
                      </div>

                      {/* Feedback Records List */}
                      {wo.feedback && wo.feedback.length > 0 && (
                        <div className="pt-2 space-y-2">
                          <div className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] font-semibold">
                            Recorded Ground-Truth Findings:
                          </div>
                          {wo.feedback.map((fb) => (
                            <div
                              key={fb.feedback_id}
                              className="p-2.5 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[2px] text-xs space-y-1"
                            >
                              <div className="flex items-center justify-between text-[10px] font-mono">
                                <span className="font-semibold text-[var(--text-primary)]">
                                  Resolution: {fb.resolution.replaceAll("_", " ").toUpperCase()}
                                </span>
                                <span className="text-[var(--text-tertiary)]">
                                  Tech: {fb.technician_id} · {new Date(fb.submitted_at).toLocaleDateString()}
                                </span>
                              </div>
                              <p className="text-[var(--text-secondary)] font-sans">{fb.findings}</p>
                              {(fb.actual_downtime_hours > 0 || fb.actual_parts_cost_inr > 0) && (
                                <div className="text-[10px] font-mono text-[var(--text-tertiary)] flex space-x-3 pt-0.5">
                                  <span>Downtime: {fb.actual_downtime_hours}h</span>
                                  <span>Parts: ₹{fb.actual_parts_cost_inr.toLocaleString()}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)]">
              SOURCE: rai.memory.work_orders · persistent audit ledger (artifacts/tickets.jsonl)
            </div>
          </div>
        )}
      </div>

      {/* Interactive Work Order Modal */}
      {modalOpen && selectedWorkOrder && (
        <WorkOrderModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          workOrder={selectedWorkOrder}
          mode={modalMode}
          onSuccess={handleModalSuccess}
        />
      )}
    </div>
  );
}

