"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Wrench,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Filter,
  RefreshCw,
  Wind,
  Sun,
  Database,
  TrendingUp,
  UserCheck,
  Check,
} from "lucide-react";
import {
  getWorkOrders,
  getDispatchPlan,
  getClosedLoopMetrics,
} from "../../lib/api";
import {
  WorkOrder,
  WorkOrderStatus,
  WorkOrderPriority,
  DispatchPlan,
  ClosedLoopMetrics,
} from "../../lib/types";
import WorkOrderModal from "../../components/WorkOrderModal";

export default function WorkOrdersPage() {
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [dispatchPlan, setDispatchPlan] = useState<DispatchPlan | null>(null);
  const [metrics, setMetrics] = useState<ClosedLoopMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"queue" | "dispatch" | "metrics">("queue");

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [siteFilter, setSiteFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");

  // Modal state
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [modalMode, setModalMode] = useState<"approve" | "reject" | "feedback">("approve");
  const [modalOpen, setModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [woData, planRes, metricsRes] = await Promise.all([
        getWorkOrders(),
        getDispatchPlan(2),
        getClosedLoopMetrics(),
      ]);
      setOrders(woData.data);
      setDispatchPlan(planRes.data);
      setMetrics(metricsRes.data);
    } catch (err) {
      console.error("Failed to load operations data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    Promise.all([
      getWorkOrders(),
      getDispatchPlan(2),
      getClosedLoopMetrics(),
    ])
      .then(([woData, planRes, metricsRes]) => {
        if (!ignore) {
          setOrders(woData.data);
          setDispatchPlan(planRes.data);
          setMetrics(metricsRes.data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("Failed to load operations data:", err);
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const openActionModal = (order: WorkOrder, mode: "approve" | "reject" | "feedback") => {
    setSelectedOrder(order);
    setModalMode(mode);
    setModalOpen(true);
  };

  const handleModalSuccess = (updated: WorkOrder) => {
    setOrders((prev) =>
      prev.map((o) => (o.ticket_id === updated.ticket_id ? updated : o))
    );
    loadData(); // refresh metrics & dispatch plan
  };

  // Filtered orders
  const filteredOrders = orders.filter((o) => {
    if (statusFilter !== "all" && o.status !== statusFilter) return false;
    if (siteFilter !== "all") {
      const isWind = o.asset_id.startsWith("WT");
      if (siteFilter === "kutch" && !isWind) return false;
      if (siteFilter === "charanka" && isWind) return false;
    }
    if (priorityFilter !== "all" && o.priority !== priorityFilter) return false;
    return true;
  });

  const getPriorityBadge = (p: WorkOrderPriority) => {
    switch (p) {
      case "emergency":
        return "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30";
      case "high":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30";
      case "medium":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30";
      case "low":
      default:
        return "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/30";
    }
  };

  const getStatusBadge = (s: WorkOrderStatus) => {
    switch (s) {
      case "proposed_awaiting_human_approval":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30";
      case "approved_scheduled":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
      case "in_progress":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30";
      case "completed":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30";
      case "rejected":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30";
      default:
        return "bg-zinc-500/10 text-zinc-600 border-zinc-500/30";
    }
  };

  const formatStatus = (s: string) => {
    return s.replace(/_/g, " ").toUpperCase();
  };

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Operations & Work Orders Command
            </h1>
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
              Closed-Loop Active
            </span>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Human-in-the-loop work order governance, meteorological safety dispatch windows, and verified technician feedback feeding the AI retrieval memory.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-3.5 py-2 text-xs font-medium rounded border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-sunken)] transition text-[var(--text-primary)]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Queue</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-1">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Pending Approval</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
            {metrics?.pending_approval ?? orders.filter((o) => o.status === "proposed_awaiting_human_approval").length}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)]">Requires human review</p>
        </div>

        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-1">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Active Dispatches</span>
            <Clock className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {(metrics?.approved ?? 0) + (metrics?.in_progress ?? 0)}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)]">Scheduled or in-progress</p>
        </div>

        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-1">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Field Concordance</span>
            <UserCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {metrics?.concordance_rate_pct != null ? (
              `${metrics.concordance_rate_pct}%`
            ) : (
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                No Verified Cases Yet
              </span>
            )}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)]">
            {metrics?.total_feedbacks && metrics.total_feedbacks > 0
              ? `${metrics.confirmed_faults} of ${metrics.total_feedbacks} confirmed`
              : "Awaiting field observations"}
          </p>
        </div>

        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-1">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Indexed Field Cases</span>
            <Database className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {metrics?.indexed_field_cases_count ?? 0}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)]">
            + {metrics?.total_academic_real_cases_count ?? 14} academic cases
          </p>
        </div>

        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-1 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Avoided Loss</span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            ₹{((dispatchPlan?.total_avoided_loss_inr ?? 0) / 100000).toFixed(1)}L
          </div>
          <p className="text-[11px] text-[var(--text-secondary)]">
            Projected risk estimate (Realised parts cost: ₹{((metrics?.total_parts_cost_inr ?? 0) / 1000).toFixed(0)}k)
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[var(--border)] space-x-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("queue")}
          className={`pb-3 relative flex items-center space-x-2 ${
            activeTab === "queue"
              ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Wrench className="w-4 h-4" />
          <span>Work Order Queue ({filteredOrders.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("dispatch")}
          className={`pb-3 relative flex items-center space-x-2 ${
            activeTab === "dispatch"
              ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Crew Dispatch & Weather Windows</span>
        </button>
        <button
          onClick={() => setActiveTab("metrics")}
          className={`pb-3 relative flex items-center space-x-2 ${
            activeTab === "metrics"
              ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Closed-Loop Learning Status</span>
        </button>
      </div>

      {/* TAB 1: WORK ORDER QUEUE */}
      {activeTab === "queue" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center gap-3 p-3 rounded border border-[var(--border)] bg-[var(--surface-raised)] text-xs">
            <div className="flex items-center space-x-1.5 text-[var(--text-secondary)] mr-2">
              <Filter className="w-3.5 h-3.5" />
              <span className="font-semibold">Filters:</span>
            </div>

            <div className="flex items-center space-x-1.5">
              <label className="text-[var(--text-secondary)]">Status:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2 py-1 rounded bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-primary)]"
              >
                <option value="all">All Statuses</option>
                <option value="proposed_awaiting_human_approval">Proposed (Awaiting Approval)</option>
                <option value="approved_scheduled">Approved / Scheduled</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div className="flex items-center space-x-1.5">
              <label className="text-[var(--text-secondary)]">Site:</label>
              <select
                value={siteFilter}
                onChange={(e) => setSiteFilter(e.target.value)}
                className="px-2 py-1 rounded bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-primary)]"
              >
                <option value="all">All Sites</option>
                <option value="kutch">Kutch Wind Farm (WT)</option>
                <option value="charanka">Charanka Solar Park (INV)</option>
              </select>
            </div>

            <div className="flex items-center space-x-1.5">
              <label className="text-[var(--text-secondary)]">Priority:</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="px-2 py-1 rounded bg-[var(--surface-sunken)] border border-[var(--border)] text-[var(--text-primary)]"
              >
                <option value="all">All Priorities</option>
                <option value="emergency">Emergency</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            {(statusFilter !== "all" || siteFilter !== "all" || priorityFilter !== "all") && (
              <button
                onClick={() => {
                  setStatusFilter("all");
                  setSiteFilter("all");
                  setPriorityFilter("all");
                }}
                className="ml-auto text-xs text-[var(--accent)] hover:underline"
              >
                Reset Filters
              </button>
            )}
          </div>

          {/* Work Orders List */}
          {filteredOrders.length === 0 ? (
            <div className="p-8 text-center rounded border border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)]">
              <p className="text-sm">No work orders matching the selected filter criteria.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOrders.map((wo) => {
                const isWind = wo.asset_id.startsWith("WT");
                const hasFeedback = (wo.feedback?.length ?? 0) > 0;
                const latestFb = hasFeedback ? wo.feedback![wo.feedback!.length - 1] : null;

                return (
                  <div
                    key={wo.ticket_id}
                    className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] hover:border-[var(--border-strong)] transition space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono text-xs font-bold text-[var(--text-primary)]">
                          {wo.ticket_id}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider ${getPriorityBadge(
                            wo.priority
                          )}`}
                        >
                          {wo.priority}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(
                            wo.status
                          )}`}
                        >
                          {formatStatus(wo.status)}
                        </span>
                        {wo.provenance === "external_field_observed" ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                            EXTERNAL FIELD
                          </span>
                        ) : wo.provenance === "demo_simulation" ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30">
                            DEMO SIMULATION
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono border uppercase tracking-wider bg-zinc-500/10 text-zinc-500 border-zinc-500/30">
                            SYNTHETIC TEST
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-3 text-xs text-[var(--text-secondary)]">
                        <span>Created: {new Date(wo.created_at).toLocaleDateString()}</span>
                        <span>Deadline: {wo.deadline_hours}h</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                      {/* Asset & Component */}
                      <div className="space-y-1">
                        <div className="text-[var(--text-secondary)] font-medium">Target Asset:</div>
                        <div className="flex items-center space-x-2">
                          {isWind ? (
                            <Wind className="w-3.5 h-3.5 text-blue-500" />
                          ) : (
                            <Sun className="w-3.5 h-3.5 text-amber-500" />
                          )}
                          <Link
                            href={`/assets/${wo.asset_id}`}
                            className="font-bold text-[var(--accent)] hover:underline flex items-center space-x-1"
                          >
                            <span>{wo.asset_id}</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                          <span className="text-[var(--text-secondary)]">({wo.site})</span>
                        </div>
                        <div className="text-[var(--text-secondary)]">
                          Component: <span className="font-semibold text-[var(--text-primary)]">{wo.component}</span>
                        </div>
                      </div>

                      {/* Action */}
                      <div className="md:col-span-2 space-y-1">
                        <div className="text-[var(--text-secondary)] font-medium">Proposed Action / Scope:</div>
                        <p className="text-[var(--text-primary)] font-mono text-[11px] bg-[var(--surface-sunken)] p-2 rounded border border-[var(--border)]">
                          {wo.action}
                        </p>
                      </div>
                    </div>

                    {/* Feedback if available */}
                    {latestFb && (
                      <div className="p-3 rounded bg-emerald-500/5 border border-emerald-500/20 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-emerald-700 dark:text-emerald-400 flex items-center space-x-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Technician Field Findings ({latestFb.resolution})</span>
                          </span>
                          <span className="text-[11px] text-[var(--text-secondary)]">
                            Tech: {latestFb.technician_id} | Downtime: {latestFb.actual_downtime_hours}h | Cost: ₹{latestFb.actual_parts_cost_inr.toLocaleString()}
                          </span>
                        </div>
                        <p className="text-[var(--text-primary)] italic">
                          &ldquo;{latestFb.findings}&rdquo;
                        </p>
                      </div>
                    )}

                    {/* Rejection reason if available */}
                    {wo.status === "rejected" && wo.rejection_reason && (
                      <div className="p-2.5 rounded bg-rose-500/5 border border-rose-500/20 text-xs text-rose-700 dark:text-rose-400">
                        <span className="font-semibold">Rejection Justification:</span> {wo.rejection_reason} (by {wo.rejected_by})
                      </div>
                    )}

                    {/* Action Bar */}
                    <div className="flex items-center justify-end space-x-2.5 pt-1">
                      {wo.status === "proposed_awaiting_human_approval" && (
                        <>
                          <button
                            onClick={() => openActionModal(wo, "reject")}
                            className="px-3 py-1.5 rounded text-xs font-semibold text-rose-600 dark:text-rose-400 border border-rose-500/30 hover:bg-rose-500/10 transition"
                          >
                            Reject Proposal
                          </button>
                          <button
                            onClick={() => openActionModal(wo, "approve")}
                            className="px-3.5 py-1.5 rounded text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 transition flex items-center space-x-1.5 shadow-sm"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve & Dispatch</span>
                          </button>
                        </>
                      )}

                      {(wo.status === "approved_scheduled" || wo.status === "in_progress") && (
                        <button
                          onClick={() => openActionModal(wo, "feedback")}
                          className="px-3.5 py-1.5 rounded text-xs font-semibold text-white bg-[var(--accent)] hover:opacity-90 transition flex items-center space-x-1.5 shadow-sm"
                        >
                          <Wrench className="w-3.5 h-3.5" />
                          <span>Record Field Findings</span>
                        </button>
                      )}

                      {wo.status === "completed" && (
                        <button
                          onClick={() => openActionModal(wo, "feedback")}
                          className="px-3 py-1.5 rounded text-xs font-medium text-[var(--text-secondary)] border border-[var(--border)] hover:bg-[var(--surface-sunken)] transition"
                        >
                          Append Additional Feedback
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CREW DISPATCH & WEATHER WINDOWS */}
      {activeTab === "dispatch" && (
        <div className="space-y-6">
          {/* Site Weather Windows */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {dispatchPlan &&
              Object.entries(dispatchPlan.site_windows).map(([key, win]) => {
                const isWind = key.includes("wind");
                const isSafe = win.status === "SAFE";
                return (
                  <div
                    key={key}
                    className={`p-4 rounded border ${
                      isSafe
                        ? "border-emerald-500/30 bg-emerald-500/5"
                        : "border-amber-500/30 bg-amber-500/5"
                    } space-y-2`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {isWind ? (
                          <Wind className="w-4 h-4 text-blue-500" />
                        ) : (
                          <Sun className="w-4 h-4 text-amber-500" />
                        )}
                        <h3 className="text-sm font-bold text-[var(--text-primary)]">
                          {isWind ? "Kutch Wind Farm" : "Charanka Solar Park"}
                        </h3>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-bold ${
                          isSafe
                            ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-400"
                            : "bg-amber-500/20 text-amber-700 dark:text-amber-400"
                        }`}
                      >
                        {win.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs py-1">
                      <div>
                        <span className="text-[var(--text-secondary)]">Wind Speed:</span>
                        <div className="font-bold text-[var(--text-primary)]">
                          {win.current_wind_speed_ms} m/s
                        </div>
                      </div>
                      <div>
                        <span className="text-[var(--text-secondary)]">Ambient Temp:</span>
                        <div className="font-bold text-[var(--text-primary)]">
                          {win.current_ambient_temp_c} °C
                        </div>
                      </div>
                      <div>
                        <span className="text-[var(--text-secondary)]">Rain Prob:</span>
                        <div className="font-bold text-[var(--text-primary)]">
                          {win.current_rain_probability_pct} %
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-[var(--text-secondary)] pt-1 border-t border-[var(--border)]">
                      {win.safety_rationale}
                    </p>
                    <div className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400">
                      Estimated Safe Operating Window: {win.safe_window_hours} hours continuous
                    </div>
                  </div>
                );
              })}
          </div>

          {/* Optimized Crew Schedule */}
          <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Optimized Fleet Crew Dispatch Schedule
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Ranked by projected avoidable outage exposure (modelled) and constrained by configured operational weather limits.
                </p>
              </div>
              <span className="text-xs font-mono text-[var(--text-secondary)]">
                Active Crews: {dispatchPlan?.active_crews_count ?? 4}
              </span>
            </div>

            {dispatchPlan && dispatchPlan.assignments.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--surface-sunken)] border-b border-[var(--border)] text-[var(--text-secondary)] uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Crew</th>
                      <th className="py-2.5 px-3">Ticket</th>
                      <th className="py-2.5 px-3">Asset</th>
                      <th className="py-2.5 px-3">Component</th>
                      <th className="py-2.5 px-3">Priority</th>
                      <th className="py-2.5 px-3">Est. Duration</th>
                      <th className="py-2.5 px-3">Weather Safety</th>
                      <th className="py-2.5 px-3">Projected Exposure</th>
                      <th className="py-2.5 px-3">Readiness</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)] font-mono">
                    {dispatchPlan.assignments.map((asgn) => (
                      <tr key={asgn.assignment_id} className="hover:bg-[var(--surface-sunken)]">
                        <td className="py-2.5 px-3 font-bold text-[var(--accent)]">{asgn.crew_id}</td>
                        <td className="py-2.5 px-3">{asgn.ticket_id}</td>
                        <td className="py-2.5 px-3 font-semibold">
                          <Link href={`/assets/${asgn.asset_id}`} className="hover:underline text-[var(--accent)]">
                            {asgn.asset_id}
                          </Link>
                        </td>
                        <td className="py-2.5 px-3 text-[var(--text-primary)]">{asgn.component}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] border ${getPriorityBadge(asgn.priority as WorkOrderPriority)}`}>
                            {asgn.priority}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">{asgn.estimated_duration_hours}h</td>
                        <td className="py-2.5 px-3 text-[11px] font-sans">{asgn.weather_status}</td>
                        <td className="py-2.5 px-3 text-emerald-600 dark:text-emerald-400 font-semibold">
                          ₹{asgn.projected_avoided_loss_inr.toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] ${
                              asgn.dispatch_readiness === "READY_IMMEDIATE"
                                ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                                : "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                            }`}
                          >
                            {asgn.dispatch_readiness}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-[var(--text-secondary)] italic">
                No pending work orders requiring immediate crew dispatch. All scheduled assets are within safe limits.
              </p>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: CLOSED-LOOP LEARNING STATUS */}
      {activeTab === "metrics" && (
        <div className="space-y-6">
          <div className="p-5 rounded border border-[var(--border)] bg-[var(--surface-raised)] space-y-4">
            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                The Closed-Loop Operational Intelligence Architecture
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                How RAI continuously enhances its retrieval-augmented intelligence through human operator authorization and technician physical inspection ground truth.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
              <div className="p-3.5 rounded border border-[var(--border)] bg-[var(--surface-sunken)] space-y-1.5">
                <span className="text-[10px] font-mono text-[var(--accent)] font-bold">STAGE 1</span>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">AI Anomaly & Reasoner</h4>
                <p className="text-[11px] text-[var(--text-secondary)]">
                  Physics residual + gradient boosted models flag anomalous component behavior and propose work orders.
                </p>
              </div>

              <div className="p-3.5 rounded border border-[var(--border)] bg-[var(--surface-sunken)] space-y-1.5">
                <span className="text-[10px] font-mono text-[var(--accent)] font-bold">STAGE 2</span>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">Human Gating & Dispatch</h4>
                <p className="text-[11px] text-[var(--text-secondary)]">
                  Control room operator audits evidence packet, approves work order, and assigns crew within safe weather windows.
                </p>
              </div>

              <div className="p-3.5 rounded border border-[var(--border)] bg-[var(--surface-sunken)] space-y-1.5">
                <span className="text-[10px] font-mono text-[var(--accent)] font-bold">STAGE 3</span>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">Technician Ground Truth</h4>
                <p className="text-[11px] text-[var(--text-secondary)]">
                  Physical teardown or borescope confirms component condition, actual parts cost, and downtime hours.
                </p>
              </div>

              <div className="p-3.5 rounded border border-purple-500/30 bg-purple-500/5 space-y-1.5">
                <span className="text-[10px] font-mono text-purple-600 dark:text-purple-400 font-bold">STAGE 4: LEARN</span>
                <h4 className="text-xs font-bold text-purple-700 dark:text-purple-300">Strict Provenance RAG Indexing</h4>
                <p className="text-[11px] text-[var(--text-secondary)]">
                  Only verified physical field inspections with confirmed external provenance are promoted to EXTERNAL_REAL; synthetic test fixtures and unverified records remain strictly INTERNAL_SYNTHETIC.
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-[var(--border)]">
              <h4 className="text-xs font-bold text-[var(--text-primary)] mb-2">
                Active Retrieval Memory Composition (Corpus Partition Purity):
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded border border-[var(--border)] bg-[var(--surface-sunken)]">
                  <span className="text-[var(--text-secondary)]">Audited Academic Cases:</span>
                  <div className="text-lg font-bold text-[var(--text-primary)]">
                    {metrics?.total_academic_real_cases_count ?? 14}
                  </div>
                  <span className="text-[10px] text-[var(--text-secondary)]">
                    CARE Wind A/B/C, Kelmarsh, PVDAQ (EXTERNAL_REAL)
                  </span>
                </div>

                <div className="p-3 rounded border border-emerald-500/30 bg-emerald-500/5">
                  <span className="text-emerald-700 dark:text-emerald-300">Verified Field Cases:</span>
                  <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                    {metrics?.indexed_real_field_cases_count ?? 0}
                  </div>
                  <span className="text-[10px] text-[var(--text-secondary)]">
                    Physical teardown ground truth (EXTERNAL_REAL)
                  </span>
                </div>

                <div className="p-3 rounded border border-zinc-500/30 bg-zinc-500/5">
                  <span className="text-zinc-500 dark:text-zinc-400">Synthetic Test Ledger:</span>
                  <div className="text-lg font-bold text-[var(--text-primary)]">
                    {metrics?.indexed_synthetic_field_cases_count ?? (metrics?.indexed_field_cases_count ?? 0)}
                  </div>
                  <span className="text-[10px] text-[var(--text-secondary)]">
                    Pipeline test fixtures (INTERNAL_SYNTHETIC)
                  </span>
                </div>

                <div className="p-3 rounded border border-blue-500/30 bg-blue-500/5">
                  <span className="text-blue-700 dark:text-blue-300">Concordance Rate:</span>
                  <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    {metrics?.concordance_rate_pct ?? 100}%
                  </div>
                  <span className="text-[10px] text-[var(--text-secondary)]">
                    Field confirmed vs total inspected
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal */}
      {selectedOrder && (
        <WorkOrderModal
          isOpen={modalOpen}
          onClose={() => {
            setModalOpen(false);
            setSelectedOrder(null);
          }}
          workOrder={selectedOrder}
          mode={modalMode}
          onSuccess={handleModalSuccess}
        />
      )}
    </div>
  );
}
