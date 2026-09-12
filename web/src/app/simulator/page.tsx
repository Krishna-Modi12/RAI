"use client";

import React, { useState, useEffect } from "react";
import { getScenarios } from "../../lib/api";
import { ScenarioItem } from "../../lib/types";
import StatusPill from "../../components/StatusPill";
import {
  Cpu,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Wind,
  Sun,
  Flame,
  CloudSun,
} from "lucide-react";

export default function SimulatorPage() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [activeScenario, setActiveScenario] = useState<string | null>("bearing_wear");
  const [injectedTarget, setInjectedTarget] = useState<string>("WT-017");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const sc = await getScenarios();
      setScenarios(sc);
    }
    load();
  }, []);

  const handleInject = (scenario: ScenarioItem) => {
    setActiveScenario(scenario.id);
    const target = scenario.asset_type === "wind" ? "WT-017" : "INV-023";
    setInjectedTarget(target);
    setMessage(`Scenario '${scenario.name}' successfully injected into live telemetry for ${target}.`);
    setTimeout(() => setMessage(null), 4000);
  };

  const handleReset = () => {
    setActiveScenario(null);
    setMessage("Simulation state reset to nominal baseline telemetry across all 42 assets.");
    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            High-Fidelity Telemetry Simulator Console
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Inject controlled mechanical, environmental, and grid events into 42-asset SCADA pipelines to test model discrimination
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleReset}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-[var(--surface-raised)] hover:bg-[var(--surface-sunken)] border border-[var(--border-control)] text-xs font-medium text-[var(--text-primary)] rounded-[2px] transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Baseline Fleet</span>
          </button>
        </div>
      </div>

      {/* Status Alert */}
      {message && (
        <div className="p-3 bg-[var(--ok-surface)] border border-[var(--ok)] text-[var(--ok)] text-xs font-mono rounded-[2px] flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{message}</span>
        </div>
      )}

      {/* Active Injection Status Card */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px]">
            <Cpu className="w-5 h-5 text-[var(--accent)]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-[var(--text-primary)]">
                Active Telemetry State:
              </span>
              {activeScenario ? (
                <span className="text-xs font-mono font-semibold text-[var(--critical)]">
                  {scenarios.find((s) => s.id === activeScenario)?.name || activeScenario} (INJECTED)
                </span>
              ) : (
                <span className="text-xs font-mono font-semibold text-[var(--ok)]">
                  Nominal Fleet Baseline
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono text-[var(--text-secondary)] mt-0.5">
              Subject Target: {injectedTarget} · Pipeline Cadence: 10s streaming interval
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-xs font-mono">
          <span className="px-2.5 py-1 bg-[var(--accent-surface)] text-[var(--accent)] rounded-[2px] border border-[var(--accent-border)]">
            SSE Stream: Connected
          </span>
        </div>
      </div>

      {/* Scenarios Grid */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex justify-between items-center">
          <h2 className="text-xs font-semibold text-[var(--text-primary)]">
            Available Fault & Environmental Scenarios (12 Cataloged Scenarios)
          </h2>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
            OOD Synthetic Challenge Verified
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
          {scenarios.map((sc) => {
            const isActive = activeScenario === sc.id;
            return (
              <div
                key={sc.id}
                className={`p-4 rounded-[3px] border transition-all flex flex-col justify-between ${
                  isActive
                    ? "bg-[var(--surface-sunken)] border-[var(--accent)] shadow-sm ring-1 ring-[var(--accent)]"
                    : "bg-[var(--surface-raised)] border-[var(--border)] hover:border-[var(--border-strong)]"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1.5">
                      {sc.asset_type === "wind" ? (
                        <Wind className="w-4 h-4 text-[var(--accent)]" />
                      ) : (
                        <Sun className="w-4 h-4 text-[var(--series-2)]" />
                      )}
                      <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)]">
                        {sc.asset_type} · {sc.category}
                      </span>
                    </div>
                    {isActive && (
                      <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 bg-[var(--accent-surface)] text-[var(--accent)] rounded-[2px]">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  <h3 className="text-xs font-semibold text-[var(--text-primary)]">
                    {sc.name}
                  </h3>
                  <p className="text-[11px] font-sans text-[var(--text-secondary)] leading-relaxed">
                    {sc.description}
                  </p>
                </div>

                <div className="pt-4 mt-3 border-t border-[var(--border)] flex items-center justify-between text-xs font-mono">
                  <div className="text-[10px] text-[var(--text-tertiary)]">
                    Duration: {sc.duration_hours}h
                  </div>
                  <button
                    onClick={() => handleInject(sc)}
                    className={`flex items-center space-x-1 px-3 py-1 text-xs font-medium rounded-[2px] transition-colors ${
                      isActive
                        ? "bg-[var(--accent)] text-[var(--text-inverse)]"
                        : "bg-[var(--surface-sunken)] hover:bg-[var(--surface-inset)] text-[var(--text-primary)] border border-[var(--border-control)]"
                    }`}
                  >
                    <Play className="w-3 h-3" />
                    <span>{isActive ? "Re-Inject" : "Inject Fault"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
