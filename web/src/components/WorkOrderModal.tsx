"use client";

import React, { useState } from "react";
import { X, CheckCircle2, XCircle, Wrench, Clock, ShieldAlert } from "lucide-react";
import { WorkOrder, WorkOrderPriority, FieldResolution } from "../lib/types";
import { actionWorkOrder, submitWorkOrderFeedback } from "../lib/api";

interface WorkOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  workOrder: WorkOrder;
  mode: "approve" | "reject" | "feedback";
  onSuccess: (updated: WorkOrder) => void;
}

export default function WorkOrderModal({
  isOpen,
  onClose,
  workOrder,
  mode,
  onSuccess,
}: WorkOrderModalProps) {
  const [actor, setActor] = useState("ops_controller");
  const [priority, setPriority] = useState<WorkOrderPriority>(workOrder.priority || "medium");
  const [deadlineHours, setDeadlineHours] = useState<number>(workOrder.deadline_hours || 72);
  const [reason, setReason] = useState("");

  // Feedback state
  const [technicianId, setTechnicianId] = useState("field_tech_01");
  const [resolution, setResolution] = useState<FieldResolution>("confirmed_fault");
  const [findings, setFindings] = useState("");
  const [componentInspected, setComponentInspected] = useState(workOrder.component || "");
  const [downtimeHours, setDowntimeHours] = useState(4.0);
  const [partsCostINR, setPartsCostINR] = useState(15000);
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === "approve" || mode === "reject") {
        const res = await actionWorkOrder(workOrder.ticket_id, {
          action: mode,
          actor: actor.trim(),
          deadline_hours: deadlineHours,
          priority,
          reason: mode === "reject" ? reason.trim() : undefined,
        });
        if (res) {
          onSuccess(res);
          onClose();
        } else {
          setError("Action failed. Verify API connection.");
        }
      } else if (mode === "feedback") {
        if (!findings.trim()) {
          setError("Findings description is required.");
          setLoading(false);
          return;
        }
        const res = await submitWorkOrderFeedback(workOrder.ticket_id, {
          technician_id: technicianId.trim(),
          resolution,
          findings: findings.trim(),
          component_inspected: componentInspected.trim() || workOrder.component,
          actual_downtime_hours: Number(downtimeHours),
          actual_parts_cost_inr: Number(partsCostINR),
          notes: notes.trim(),
        });
        if (res) {
          onSuccess(res);
          onClose();
        } else {
          setError("Failed to record technician feedback. Verify API connection.");
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[4px] shadow-2xl w-full max-w-lg overflow-hidden flex flex-col font-sans animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-5 py-3.5 bg-[var(--surface-sunken)] border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            {mode === "approve" && <CheckCircle2 className="w-5 h-5 text-[var(--ok)]" />}
            {mode === "reject" && <XCircle className="w-5 h-5 text-[var(--critical)]" />}
            {mode === "feedback" && <Wrench className="w-5 h-5 text-[var(--accent)]" />}
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                {mode === "approve" && "Authorize & Dispatch Work Order"}
                {mode === "reject" && "Reject Proposed Maintenance Ticket"}
                {mode === "feedback" && "Record Ground-Truth Inspection Feedback"}
              </h2>
              <p className="text-[10px] font-mono text-[var(--text-tertiary)]">
                {workOrder.ticket_id} · {workOrder.asset_id} ({workOrder.component})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] rounded-[2px]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-2.5 bg-[var(--critical-surface)]/20 border border-[var(--critical)]/40 rounded-[2px] text-[var(--critical)] text-[11px] flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Proposal Summary Box */}
          <div className="p-3 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px] space-y-1">
            <div className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase">
              Prescribed Operational Action
            </div>
            <div className="text-xs font-semibold text-[var(--text-primary)]">
              {workOrder.action}
            </div>
            <div className="text-[10px] text-[var(--text-secondary)]">
              Site: {workOrder.site} · Asset: {workOrder.asset_name}
            </div>
          </div>

          {(mode === "approve" || mode === "reject") && (
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                  Operator / Controller ID
                </label>
                <input
                  type="text"
                  required
                  value={actor}
                  onChange={(e) => setActor(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
                />
              </div>

              {mode === "approve" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                      Dispatch Priority
                    </label>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value as WorkOrderPriority)}
                      className="w-full px-2.5 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                    >
                      <option value="low">Low (Routine)</option>
                      <option value="medium">Medium (Scheduled)</option>
                      <option value="high">High (Prevent Outage)</option>
                      <option value="emergency">Emergency (Immediate)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                      Deadline Horizon
                    </label>
                    <select
                      value={deadlineHours}
                      onChange={(e) => setDeadlineHours(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                    >
                      <option value={24}>Within 24 Hours</option>
                      <option value={48}>Within 48 Hours</option>
                      <option value={72}>Within 72 Hours</option>
                      <option value={168}>Within 7 Days (168h)</option>
                    </select>
                  </div>
                </div>
              )}

              {mode === "reject" && (
                <div>
                  <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                    Rejection Reason / Operational Justification *
                  </label>
                  <textarea
                    required
                    rows={3}
                    placeholder="e.g. Scheduled grid curtailment in effect; sensor drift verified during shift inspection."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full px-3 py-2 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-sans text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--critical)]"
                  />
                </div>
              )}
            </div>
          )}

          {mode === "feedback" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                    Field Technician ID *
                  </label>
                  <input
                    type="text"
                    required
                    value={technicianId}
                    onChange={(e) => setTechnicianId(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                    Component Inspected
                  </label>
                  <input
                    type="text"
                    value={componentInspected}
                    onChange={(e) => setComponentInspected(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                  Ground-Truth Field Resolution *
                </label>
                <select
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value as FieldResolution)}
                  className="w-full px-2.5 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                >
                  <option value="confirmed_fault">Confirmed Fault (Damage Found)</option>
                  <option value="early_inspection_prevented_failure">Early Inspection Prevented Failure (Incipient)</option>
                  <option value="false_alarm">False Alarm (Clean Inspection / Benign)</option>
                  <option value="no_fault_found">No Fault Found (Cannot Reproduce)</option>
                  <option value="maintenance_deferred">Maintenance Deferred</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                  Verified Inspection Findings & Physical Root Cause *
                </label>
                <textarea
                  required
                  rows={2}
                  placeholder="e.g. Disassembled bearing housing: severe brinelling and metallic debris in grease reservoir."
                  value={findings}
                  onChange={(e) => setFindings(e.target.value)}
                  className="w-full px-3 py-2 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-sans text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                    Actual Downtime (Hours)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={downtimeHours}
                    onChange={(e) => setDowntimeHours(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                    Actual Parts & Labor Cost (₹)
                  </label>
                  <input
                    type="number"
                    step="500"
                    min="0"
                    value={partsCostINR}
                    onChange={(e) => setPartsCostINR(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-mono text-[var(--text-primary)] focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1">
                  Operational Notes (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Lubricant replaced; scheduled vibration re-check in 14 days."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-xs font-sans text-[var(--text-primary)] focus:outline-hidden"
                />
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-3 border-t border-[var(--border)] flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-[var(--surface-sunken)] hover:bg-[var(--surface-inset)] text-[var(--text-secondary)] border border-[var(--border)] rounded-[2px] text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`px-4 py-1.5 font-sans font-medium text-xs rounded-[2px] transition-colors shadow-xs flex items-center space-x-1.5 ${
                mode === "approve"
                  ? "bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)]"
                  : mode === "reject"
                  ? "bg-[var(--critical)] text-white hover:opacity-90"
                  : "bg-[var(--ok)] text-white hover:opacity-90"
              }`}
            >
              {loading && <Clock className="w-3.5 h-3.5 animate-spin" />}
              <span>
                {mode === "approve" && "Authorize Dispatch"}
                {mode === "reject" && "Confirm Rejection"}
                {mode === "feedback" && "Record Field Resolution"}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
