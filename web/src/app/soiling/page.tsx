"use client";

import React, { useState, useEffect } from "react";
import { getSoilingIntelligence } from "../../lib/api";
import { formatINR, formatPercent } from "../../lib/format";
import { SoilingResponse } from "../../lib/types";
import StatusPill from "../../components/StatusPill";
import {
  Sun,
  CloudRain,
  Wind,
  Droplets,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Sparkles,
  TrendingDown,
} from "lucide-react";

export default function SoilingPage() {
  const [soiling, setSoiling] = useState<SoilingResponse | null>(null);
  const [selectedAsset, setSelectedAsset] = useState("INV-023");

  useEffect(() => {
    async function load() {
      const data = await getSoilingIntelligence(selectedAsset);
      setSoiling(data);
    }
    load();
  }, [selectedAsset]);

  if (!soiling) {
    return (
      <div className="p-8 text-center text-xs font-mono text-[var(--text-tertiary)]">
        Loading environmental & soiling intelligence...
      </div>
    );
  }

  const {
    dust_risk,
    dust_concentration_ug_m3,
    aod_550,
    pm10_ug_m3,
    rain_probability_24h,
    rain_wash_probability,
    mud_cementation_risk,
    soiling_ratio,
    current_soiling_loss_pct,
    daily_accumulation_rate_pct,
    last_cleaning_days_ago,
    advisor_options,
    loss_decomposition,
  } = soiling;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Solar Environmental & Soiling Intelligence
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            CAMS-backed atmospheric composition forecasts, Kimber-RdTools soiling kinetics, and techno-economic wash optimization
          </p>
        </div>

        {/* Asset Selector */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="text-[var(--text-secondary)]">Monitored Inverter:</span>
          <select
            value={selectedAsset}
            onChange={(e) => setSelectedAsset(e.target.value)}
            className="bg-[var(--surface-raised)] border border-[var(--border-control)] text-[var(--text-primary)] px-2 py-1 rounded-[2px]"
          >
            <option value="INV-023">INV-023 (Charanka Zone 2 - High Soiling)</option>
            <option value="INV-009">INV-009 (Charanka Zone 1 - Moderate)</option>
            <option value="INV-001">INV-001 (Charanka Baseline)</option>
          </select>
        </div>
      </div>

      {/* Flagship Dust & Weather Alert Banner */}
      <div
        className={`p-4 rounded-[3px] border ${
          dust_risk === "high" || dust_risk === "severe"
            ? "bg-[var(--warn-surface)] border-[var(--warn)] text-[var(--warn-ink)]"
            : "bg-[var(--surface-raised)] border-[var(--border)] text-[var(--text-primary)]"
        } flex flex-col md:flex-row items-start md:items-center justify-between gap-4`}
      >
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px]">
            <Wind className="w-5 h-5 text-[var(--warn)]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm">
                CAMS Desert Dust Advisory: {dust_risk.toUpperCase()} EXPOSURE
              </span>
              <StatusPill band={dust_risk === "high" ? "high" : "low"} />
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Atmospheric Optical Depth ({aod_550.toFixed(2)}) & PM10 ({pm10_ug_m3.toFixed(0)} µg/m³) indicate an active dust storm plume over Gujarat.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6 text-xs font-mono">
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Rain (24h)</div>
            <div className="font-semibold">{(rain_probability_24h * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Wash Probability</div>
            <div className="font-semibold text-[var(--ok)]">
              {(rain_wash_probability * 100).toFixed(0)}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Mud Cementation Risk</div>
            <div className="font-semibold capitalize text-[var(--warn-ink)]">
              {mud_cementation_risk}
            </div>
          </div>
        </div>
      </div>

      {/* 4 Environmental KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Soiling Ratio (SR)</div>
          <div className="text-2xl font-semibold text-[var(--text-primary)]">
            {soiling_ratio.toFixed(3)}
          </div>
          <div className="text-[11px] text-[var(--critical)]">
            Current Loss: −{current_soiling_loss_pct.toFixed(1)}%
          </div>
        </div>

        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Daily Accumulation</div>
          <div className="text-2xl font-semibold text-[var(--warn-ink)]">
            +{daily_accumulation_rate_pct.toFixed(2)}%
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">
            Accelerated by Thar dust plume
          </div>
        </div>

        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Dust Concentration</div>
          <div className="text-2xl font-semibold text-[var(--text-primary)]">
            {dust_concentration_ug_m3.toFixed(0)} <span className="text-xs font-normal">µg/m³</span>
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">
            PM10: {pm10_ug_m3.toFixed(0)} µg/m³ · AOD: {aod_550.toFixed(2)}
          </div>
        </div>

        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Last Panel Wash</div>
          <div className="text-2xl font-semibold text-[var(--text-primary)]">
            {last_cleaning_days_ago} <span className="text-xs font-normal">Days Ago</span>
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">
            Dry cycle elapsed: 336 hours
          </div>
        </div>
      </div>

      {/* Model-Based Loss Attribution Breakdown */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-3">
        <div className="flex justify-between items-center border-b border-[var(--border)] pb-2.5">
          <h2 className="text-xs font-semibold text-[var(--text-primary)]">
            Model-Based Loss Attribution (Total Deficit: {loss_decomposition.total_loss_pct.toFixed(1)}% ± 2.5%)
          </h2>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
            Estimated model-based attribution across physical and operational factors
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 font-mono text-xs">
          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Soiling Loss</div>
            <div className="text-base font-semibold text-[var(--critical)] mt-1">
              {loss_decomposition.soiling_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Aerosol coating</div>
          </div>

          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Irradiance / Cloud</div>
            <div className="text-base font-semibold text-[var(--info)] mt-1">
              {loss_decomposition.irradiance_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Atmospheric diff</div>
          </div>

          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Thermal Derating</div>
            <div className="text-base font-semibold text-[var(--text-secondary)] mt-1">
              {loss_decomposition.thermal_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Cell temp coeff</div>
          </div>

          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Grid Curtailment</div>
            <div className="text-base font-semibold text-[var(--text-secondary)] mt-1">
              {loss_decomposition.curtailment_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Set-point limit</div>
          </div>

          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Equipment Inefficiency</div>
            <div className="text-base font-semibold text-[var(--ok)] mt-1">
              {loss_decomposition.equipment_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Inverter healthy</div>
          </div>

          <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px]">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Unexplained Residual</div>
            <div className="text-base font-semibold text-[var(--text-tertiary)] mt-1">
              {loss_decomposition.unexplained_loss_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">Sensor noise band</div>
          </div>
        </div>

        <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)] flex justify-between">
          <span>SOURCE: rai.environment.attribution.decompose_pv_power_loss</span>
          <span>PHYSICS NORMALIZATION: pvlib.clearsky.ineichen + RdTools SRR</span>
        </div>
      </div>

      {/* Smart Cleaning Advisor Techno-Economic Engine */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden space-y-3">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[var(--accent)]" />
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">
              Smart Cleaning Advisor (Techno-Economic Net Benefit Comparison)
            </h2>
          </div>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
            Rain vs Wash NPV Optimization Engine
          </span>
        </div>

        <div className="p-4 space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left">
                  <th className="py-2.5">Strategy Option</th>
                  <th className="py-2.5 text-right">Window</th>
                  <th className="py-2.5 text-right">Wash Cost</th>
                  <th className="py-2.5 text-right">Recovered Energy</th>
                  <th className="py-2.5 text-right">Avoided Loss</th>
                  <th className="py-2.5 text-right">Net Financial Benefit</th>
                  <th className="py-2.5 text-right">Break-Even</th>
                  <th className="py-2.5 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {advisor_options.map((opt, i) => (
                  <tr
                    key={i}
                    className={`hover:bg-[var(--surface-sunken)] ${
                      opt.is_recommended
                        ? "bg-[var(--ok-surface)]/40 font-semibold"
                        : ""
                    }`}
                  >
                    <td className="py-3 font-sans">
                      <div className="flex items-center space-x-2">
                        {opt.is_recommended && (
                          <CheckCircle2 className="w-4 h-4 text-[var(--ok)] flex-shrink-0" />
                        )}
                        <span className="text-[var(--text-primary)] font-medium">
                          {opt.action}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-[var(--text-tertiary)] mt-0.5 max-w-md">
                        {opt.rationale}
                      </div>
                    </td>
                    <td className="py-3 text-right">{opt.recommended_window_hours}h</td>
                    <td className="py-3 text-right">{formatINR(opt.cleaning_cost_inr).display}</td>
                    <td className="py-3 text-right">
                      {opt.expected_energy_recovered_kwh.toLocaleString()} kWh
                    </td>
                    <td className="py-3 text-right">{formatINR(opt.avoided_loss_inr).display}</td>
                    <td
                      className={`py-3 text-right font-semibold ${
                        opt.net_benefit_inr > 0 ? "text-[var(--ok)]" : "text-[var(--critical)]"
                      }`}
                    >
                      {formatINR(opt.net_benefit_inr).display}
                    </td>
                    <td className="py-3 text-right">{opt.break_even_days.toFixed(1)} days</td>
                    <td className="py-3 text-center">
                      {opt.is_recommended ? (
                        <span className="px-2 py-0.5 bg-[var(--ok-surface)] text-[var(--ok)] border border-[var(--ok)] rounded-[2px] text-[10px]">
                          OPTIMAL ACTION
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

          <div className="p-3 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px] text-xs space-y-1">
            <div className="font-semibold text-[var(--text-primary)]">
              Operational Recommendation:
            </div>
            <p className="text-[var(--text-secondary)] text-[11px] leading-relaxed">
              Because 24-hour rain probability is low (15%), natural wash recovery is insufficient to overcome the high current daily revenue loss (-₹8,200/day). Immediate cleaning yields maximum NPV of +₹77,000 with a 3.2-day payback period.
            </p>
          </div>

          <div className="text-[10px] font-mono text-[var(--text-tertiary)] pt-2 border-t border-[var(--border)] flex justify-between">
            <span>SOURCE: GET /api/soiling?asset_id={selectedAsset}</span>
            <span>DATA SOURCE: Open-Meteo Air Quality CAMS + GFS Precipitation Forecasts</span>
          </div>
        </div>
      </div>
    </div>
  );
}
