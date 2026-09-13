"use client";

import React, { useState, useEffect } from "react";
import { getScenarios, injectScenario, resetScenario } from "../../lib/api";
import { ScenarioItem } from "../../lib/types";
import {
  Cpu,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Wind,
  Sun,
} from "lucide-react";

export default function SimulatorPage() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [scenariosLive, setScenariosLive] = useState(false);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [injectedTarget, setInjectedTarget] = useState<string>("WT-017");
  const [message, setMessage] = useState<string | null>(null);
  const [messageIsError, setMessageIsError] = useState(false);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const sc = await getScenarios();
      setScenarios(sc.data);
      setScenariosLive(sc.live);
    }
    load();
  }, []);

  const handleInject = async (scenario: ScenarioItem) => {
    const target = scenario.asset_type === "wind_turbine" ? "WT-017" : "INV-023";
    setPending(scenario.scenario);
    const result = await injectScenario(target, scenario.scenario);
    setPending(null);
    if (result.ok) {
      setActiveScenario(scenario.scenario);
      setInjectedTarget(target);
      setMessageIsError(false);
      setMessage(`Scenario '${scenario.label}' injected into live telemetry for ${target}.`);
    } else {
      setMessageIsError(true);
      setMessage(`Injection failed: ${result.detail ?? "API unreachable"}`);
    }
    setTimeout(() => setMessage(null), 4000);
  };

  const handleReset = async () => {
    setPending("reset");
    const result = await resetScenario();
    setPending(null);
    if (result.ok) {
      setActiveScenario(null);
      setMessageIsError(false);
      setMessage("Simulation state reset to nominal baseline telemetry across all assets.");
    } else {
      setMessageIsError(true);
      setMessage(`Reset failed: ${result.detail ?? "API unreachable"}`);
    }
    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Telemetry Simulator Console
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Inject controlled fault and environmental scenarios into live telemetry to test model discrimination
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleReset}
            disabled={pending !== null}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-[var(--surface-raised)] hover:bg-[var(--surface-sunken)] border border-[var(--border-control)] text-xs font-medium text-[var(--text-primary)] rounded-[2px] transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            <RotateCcw className={`w-3.5 h-3.5 flex-shrink-0 ${pending === "reset" ? "animate-spin" : ""}`} />
            <span>Reset Baseline Fleet</span>
          </button>
        </div>
      </div>

      {/* Status Alert */}
      {message && (
        <div
          className={`p-3 text-xs font-mono rounded-[2px] flex items-center space-x-2 ${
            messageIsError
              ? "bg-[var(--critical-surface)] border border-[var(--critical)] text-[var(--critical-ink)]"
              : "bg-[var(--ok-surface)] border border-[var(--ok)] text-[var(--ok)]"
          }`}
        >
          {messageIsError ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
                  {scenarios.find((s) => s.scenario === activeScenario)?.label ?? activeScenario} (injected)
                </span>
              ) : (
                <span className="text-xs font-mono font-semibold text-[var(--ok)]">
                  Nominal Fleet Baseline
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono text-[var(--text-secondary)] mt-0.5">
              Subject Target: {injectedTarget}
            </div>
          </div>
        </div>

        <div className="text-[10px] font-mono text-[var(--text-tertiary)]">
          SOURCE: POST /api/simulator/inject, /reset
        </div>
      </div>

      {/* Scenarios Grid */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex justify-between items-center">
          <h2 className="text-xs font-semibold text-[var(--text-primary)]">
            Available Fault & Environmental Scenarios ({scenarios.length} Cataloged)
          </h2>
          <span
            className="text-[10px] font-mono text-[var(--text-tertiary)]"
            title={scenariosLive ? "Live from /api/simulator/scenarios" : "API unavailable — showing last-known snapshot"}
          >
            {scenariosLive ? "LIVE" : "CACHED · last-known snapshot"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
          {scenarios.map((sc) => {
            const isActive = activeScenario === sc.scenario;
            return (
              <div
                key={sc.scenario}
                className={`p-4 rounded-[3px] border transition-all flex flex-col justify-between ${
                  isActive
                    ? "bg-[var(--surface-sunken)] border-[var(--accent)] shadow-sm ring-1 ring-[var(--accent)]"
                    : "bg-[var(--surface-raised)] border-[var(--border)] hover:border-[var(--border-strong)]"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1.5">
                      {sc.asset_type === "wind_turbine" ? (
                        <Wind className="w-4 h-4 text-[var(--accent)]" />
                      ) : (
                        <Sun className="w-4 h-4 text-[var(--series-2)]" />
                      )}
                      <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)]">
                        {sc.component} · {sc.is_equipment_fault ? "equipment fault" : "environmental"}
                      </span>
                    </div>
                    {isActive && (
                      <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 bg-[var(--accent-surface)] text-[var(--accent)] rounded-[2px]">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  <h3 className="text-xs font-semibold text-[var(--text-primary)]">
                    {sc.label}
                  </h3>
                  <p className="text-[11px] font-sans text-[var(--text-secondary)] leading-relaxed">
                    {sc.description}
                  </p>
                </div>

                <div className="pt-4 mt-3 border-t border-[var(--border)] flex items-center justify-between text-xs font-mono">
                  <div className="text-[10px] text-[var(--text-tertiary)]">
                    Typical onset: {sc.typical_onset_days}d
                  </div>
                  <button
                    onClick={() => handleInject(sc)}
                    disabled={pending !== null}
                    className={`flex items-center space-x-1 px-3 py-1 text-xs font-medium rounded-[2px] transition-colors disabled:opacity-50 whitespace-nowrap ${
                      isActive
                        ? "bg-[var(--accent)] text-[var(--text-inverse)]"
                        : "bg-[var(--surface-sunken)] hover:bg-[var(--surface-inset)] text-[var(--text-primary)] border border-[var(--border-control)]"
                    }`}
                  >
                    <Play className={`w-3 h-3 flex-shrink-0 ${pending === sc.scenario ? "animate-spin" : ""}`} />
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
