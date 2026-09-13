"use client";

import React, { useState, useEffect } from "react";
import { getSoilingIntelligence } from "../../lib/api";
import { formatINR, formatPercent } from "../../lib/format";
import { SoilingResponse } from "../../lib/types";
import StatusPill from "../../components/StatusPill";
import {
  Wind,
  Droplets,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

export default function SoilingPage() {
  const [soiling, setSoiling] = useState<SoilingResponse | null>(null);
  const [live, setLive] = useState(false);

  useEffect(() => {
    async function load() {
      const result = await getSoilingIntelligence();
      setSoiling(result.data);
      setLive(result.live);
    }
    load();
  }, []);

  if (!soiling) {
    return (
      <div className="p-8 text-center text-xs font-mono text-[var(--text-tertiary)]">
        Loading environmental & soiling intelligence...
      </div>
    );
  }

  const {
    site,
    site_soiling_loss_pct,
    dust_risk,
    rain_probability_48h,
    days_since_rain,
    cleaning_cost_inr,
    recommendation,
    cleaning_options,
    zones,
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
            Site-level dust risk, rain-wash forecast, and cleaning economics for {site}
          </p>
        </div>

        <span
          className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider"
          title={live ? "Live from /api/soiling" : "API unavailable — showing last-known snapshot"}
        >
          {live ? "LIVE" : "CACHED · last-known snapshot"}
        </span>
      </div>

      {/* Advisory Banner */}
      <div
        className={`p-4 rounded-[3px] border ${
          dust_risk === "high"
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
              <span className="font-semibold text-sm capitalize">
                Dust Risk: {dust_risk}
              </span>
              <StatusPill band={dust_risk === "high" ? "high" : dust_risk === "moderate" ? "elevated" : "low"} />
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Recommendation: <span className="font-semibold capitalize">{recommendation.action}</span>
              {recommendation.action === "wait" && ` ${recommendation.wait_hours}h`} — {recommendation.rationale}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6 text-xs font-mono">
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Rain (48h)</div>
            <div className="font-semibold whitespace-nowrap">{formatPercent(rain_probability_48h * 100)}</div>
          </div>
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Days Since Rain</div>
            <div className="font-semibold text-[var(--text-primary)] whitespace-nowrap">{days_since_rain.toFixed(1)} d</div>
          </div>
          <div>
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Breakeven</div>
            <div className="font-semibold text-[var(--text-primary)] whitespace-nowrap">{recommendation.breakeven_days.toFixed(1)} d</div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-xs">
        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Site Soiling Loss</div>
          <div className="text-2xl font-semibold text-[var(--critical)]">
            {site_soiling_loss_pct.toFixed(1)}%
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">Fleet-wide average across zones</div>
        </div>

        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Cleaning Cost (Full Site)</div>
          <div className="text-2xl font-semibold text-[var(--text-primary)]">
            {formatINR(cleaning_cost_inr).display}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">All inverter blocks</div>
        </div>

        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-1">
          <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Rain Wash Probability (48h)</div>
          <div className="text-2xl font-semibold text-[var(--ok)]">
            {formatPercent(rain_probability_48h * 100)}
          </div>
          <div className="text-[11px] text-[var(--text-tertiary)]">Natural cleaning likelihood</div>
        </div>
      </div>

      {/* Zone Breakdown */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Droplets className="w-4 h-4 text-[var(--accent)]" />
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">Zone-Level Soiling</h2>
          </div>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">SOURCE: GET /api/soiling · zones</span>
        </div>

        <div className="overflow-x-auto p-4">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left">
                <th className="py-2 px-3">Zone</th>
                <th className="py-2 px-3 text-right">Inverters</th>
                <th className="py-2 px-3 text-right">Soiling Loss</th>
                <th className="py-2 px-3 text-right">Performance Ratio</th>
                <th className="py-2 px-3 text-right">Worst Asset</th>
                <th className="py-2 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {zones.map((z) => (
                <tr key={z.zone} className="hover:bg-[var(--surface-sunken)]">
                  <td className="py-2.5 px-3 font-sans font-medium text-[var(--text-primary)] whitespace-nowrap">{z.zone}</td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">{z.inverters}</td>
                  <td className="py-2.5 px-3 text-right text-[var(--critical)] whitespace-nowrap">{z.soiling_loss_pct.toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">{z.performance_ratio.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">{z.worst_asset_id}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-[2px] text-[10px] border whitespace-nowrap ${
                        z.status === "investigate"
                          ? "bg-[var(--critical-surface)] text-[var(--critical-ink)] border-[var(--critical)]"
                          : z.status === "watch"
                          ? "bg-[var(--warn-surface)] text-[var(--warn-ink)] border-[var(--warn)]"
                          : "bg-[var(--ok-surface)] text-[var(--ok)] border-[var(--ok)]"
                      }`}
                    >
                      {z.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Smart Cleaning Advisor */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden space-y-3">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[var(--accent)]" />
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">Cleaning Advisor</h2>
          </div>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">SOURCE: GET /api/soiling · cleaning_options</span>
        </div>

        {cleaning_options && cleaning_options.length > 0 ? (
          <div className="p-4 overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left">
                  <th className="py-2.5">Option</th>
                  <th className="py-2.5 text-right">Delay</th>
                  <th className="py-2.5 text-right">Cleaning Cost</th>
                  <th className="py-2.5 text-right">Expected Loss</th>
                  <th className="py-2.5 text-right">Net Exposure</th>
                  <th className="py-2.5 text-right">Break-Even</th>
                  <th className="py-2.5 text-center">Cementation Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {cleaning_options.map((opt) => (
                  <tr key={opt.option_id} className="hover:bg-[var(--surface-sunken)]">
                    <td className="py-3 font-sans">
                      <div className="text-[var(--text-primary)] font-medium">{opt.label}</div>
                      <div className="text-[11px] font-mono text-[var(--text-tertiary)] mt-0.5 max-w-md">
                        {opt.summary}
                      </div>
                    </td>
                    <td className="py-3 text-right">{opt.delay_hours}h</td>
                    <td className="py-3 text-right">{formatINR(opt.cleaning_cost_inr).display}</td>
                    <td className="py-3 text-right">{formatINR(opt.expected_energy_loss_inr).display}</td>
                    <td className="py-3 text-right font-semibold">{formatINR(opt.net_exposure_inr).display}</td>
                    <td className="py-3 text-right">{opt.break_even_days.toFixed(1)}d</td>
                    <td className="py-3 text-center">
                      {opt.cementation_risk ? (
                        <span className="text-[var(--critical)]">Yes</span>
                      ) : (
                        <span className="text-[var(--text-tertiary)]">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-4 text-xs font-mono text-[var(--text-tertiary)] flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>No cleaning options computed for the current recommendation — not evaluated.</span>
          </div>
        )}
      </div>
    </div>
  );
}
