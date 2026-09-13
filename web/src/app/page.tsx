"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import MetricTile from "../components/MetricTile";
import StatusPill from "../components/StatusPill";
import {
  getFleetOverview,
  getPriorityQueue,
  getFleetAssets,
} from "../lib/api";
import { formatINR, formatPower, formatPercent } from "../lib/format";
import {
  FleetOverview,
  PriorityQueueItem,
  FleetAssetItem,
} from "../lib/types";
import { Wind, Sun, Search, ArrowUpRight, AlertOctagon } from "lucide-react";

export default function FleetPage() {
  const [overview, setOverview] = useState<FleetOverview | null>(null);
  const [overviewLive, setOverviewLive] = useState(false);
  const [priorityQueue, setPriorityQueue] = useState<PriorityQueueItem[]>([]);
  const [assets, setAssets] = useState<FleetAssetItem[]>([]);
  const [assetsLive, setAssetsLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "wind_turbine" | "solar_inverter">("all");
  const [riskFilter, setRiskFilter] = useState<"all" | "at_risk" | "nominal">("all");

  useEffect(() => {
    async function loadData() {
      try {
        const [ov, pq, as] = await Promise.all([
          getFleetOverview(),
          getPriorityQueue(),
          getFleetAssets(),
        ]);
        setOverview(ov.data);
        setOverviewLive(ov.live);
        setPriorityQueue(pq.data);
        setAssets(as.data);
        setAssetsLive(as.live);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const windCount = overview?.by_type?.find((t) => t.asset_type === "wind_turbine")?.count
    ?? assets.filter((a) => a.asset_type === "wind_turbine").length;
  const solarCount = overview?.by_type?.find((t) => t.asset_type === "solar_inverter")?.count
    ?? assets.filter((a) => a.asset_type === "solar_inverter").length;

  const filteredAssets = assets.filter((asset) => {
    if (typeFilter !== "all" && asset.asset_type !== typeFilter) return false;
    if (riskFilter === "at_risk" && asset.risk_band === "low") return false;
    if (riskFilter === "nominal" && asset.risk_band !== "low") return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        asset.asset_id.toLowerCase().includes(q) ||
        asset.name.toLowerCase().includes(q) ||
        asset.site.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Heading */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Fleet operations command
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            SCADA telemetry and evidence-backed maintenance decisions across the fleet
          </p>
        </div>
        <div className="flex items-center space-x-2 font-mono text-xs text-[var(--text-secondary)]">
          <span className="w-2 h-2 rounded-full bg-[var(--ok)]" />
          <span>CARE benchmarked</span>
        </div>
      </div>

      {/* Metric Tiles - Exactly 4 per docs/DESIGN.md */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile
          label="Fleet Operational Health"
          value={overview ? `${overview.fleet_health}%` : "—"}
          context={overview ? `Weighted across ${overview.assets_total} generation units` : "Loading live data"}
          hero
          source="GET /api/fleet"
          live={overviewLive}
        />
        <MetricTile
          label="Generation vs Expected"
          value={overview ? formatPower(overview.generation_kw) : "—"}
          context={overview ? `Expected: ${formatPower(overview.expected_generation_kw)}` : "Loading live data"}
          source="physics_gbm_expectation"
          live={overviewLive}
        />
        <MetricTile
          label="Plant Availability"
          value={overview ? `${overview.availability_pct}%` : "—"}
          context={overview ? `${overview.assets_total - overview.assets_offline} active / ${overview.assets_offline} offline` : "Loading live data"}
          source="scada_status_flags"
          live={overviewLive}
        />
        <MetricTile
          label="Expected Exposure (30-Day)"
          value={overview ? formatINR(overview.revenue_at_risk_inr_30d).display : "—"}
          context={overview ? "Modeled cost of leaving at-risk assets unaddressed for 30 days" : "Loading live data"}
          source="rai.economics.engine"
          live={overviewLive}
        />
      </div>

      {/* Ranked Priority Action Queue */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="h-10 px-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertOctagon className="w-4 h-4 text-[var(--critical)]" />
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">
              Ranked Action Queue (Sorted by 14-Day Expected Exposure × Risk)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-[var(--text-tertiary)]">
            {loading ? "Loading work orders" : `${priorityQueue.length} Active Work Orders`}
          </span>
        </div>

        <div className="divide-y divide-[var(--border)]">
          {loading && priorityQueue.length === 0 ? (
            <div className="p-4 text-xs text-[var(--text-secondary)]">Loading live work orders…</div>
          ) : priorityQueue.length === 0 ? (
            <div className="p-4 text-xs text-[var(--text-secondary)]">Unavailable — no live work-order data received.</div>
          ) : priorityQueue.map((item) => (
            <div
              key={item.asset_id}
              className={`p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 hover:bg-[var(--surface-sunken)] transition-colors border-l-[3px] ${
                item.risk_band === "critical"
                  ? "border-[var(--critical)]"
                  : item.risk_band === "high"
                  ? "border-[var(--warn)]"
                  : "border-[var(--border)]"
              }`}
            >
              {/* Asset ID & Type */}
              <div className="min-w-[140px]">
                <div className="flex items-center space-x-1.5">
                  {item.asset_type === "wind_turbine" ? (
                    <Wind className="w-3.5 h-3.5 text-[var(--accent)]" />
                  ) : (
                    <Sun className="w-3.5 h-3.5 text-[var(--series-2)]" />
                  )}
                  <span className="font-mono font-semibold text-sm text-[var(--text-primary)]">
                    {item.asset_id}
                  </span>
                </div>
                <div className="text-[11px] text-[var(--text-tertiary)] font-sans">
                  {item.name} · {item.site}
                </div>
              </div>

              {/* Headline & Signal */}
              <div className="flex-1 space-y-0.5">
                <div className="text-xs font-medium text-[var(--text-primary)]">
                  {item.headline}
                </div>
                <div className="text-[11px] font-mono text-[var(--text-tertiary)]">
                  Dominant Signal: <span className="text-[var(--text-secondary)]">{item.dominant_signal}</span>
                </div>
              </div>

              {/* Metrics (Risk, Revenue, Deadline) */}
              <div className="flex items-center space-x-6 font-mono text-xs">
                <div>
                  <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Risk</div>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <StatusPill band={item.risk_band} />
                    <span className="font-semibold text-[var(--text-primary)]">
                      {(item.risk_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Exposure</div>
                  <div className="font-semibold text-[var(--text-primary)] mt-0.5">
                    {formatINR(item.revenue_at_risk_inr).display}
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Deadline</div>
                  <div
                    className={`font-semibold mt-0.5 ${
                      item.deadline_hours <= 48 ? "text-[var(--critical)]" : "text-[var(--warn-ink)]"
                    }`}
                  >
                    {item.deadline_hours}h
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div>
                <Link
                  href={`/assets/${item.asset_id}`}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 bg-[var(--surface-raised)] border border-[var(--border-control)] hover:border-[var(--accent)] text-xs font-medium text-[var(--text-primary)] rounded-[2px] transition-colors"
                >
                  <span>Investigate</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 42-Asset Tabular Fleet Grid */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden space-y-3">
        {/* Table Controls */}
        <div className="p-3 bg-[var(--surface-inset)] border-b border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">
              {loading ? "All Fleet Generation Assets (loading…)" : assetsLive ? `All Fleet Generation Assets (${filteredAssets.length} of ${assets.length})` : assets.length ? `All Fleet Generation Assets (${filteredAssets.length} of ${assets.length}, cached)` : "All Fleet Generation Assets (unavailable)"}
            </h2>

            {/* Type Filters */}
            <div className="flex items-center border border-[var(--border)] rounded-[2px] bg-[var(--surface-raised)] text-xs font-mono">
              <button
                onClick={() => setTypeFilter("all")}
                className={`px-2.5 py-1 ${typeFilter === "all" ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold" : "text-[var(--text-secondary)]"}`}
              >
                All
              </button>
              <button
                onClick={() => setTypeFilter("wind_turbine")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${typeFilter === "wind_turbine" ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold" : "text-[var(--text-secondary)]"}`}
              >
                Wind ({windCount})
              </button>
              <button
                onClick={() => setTypeFilter("solar_inverter")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${typeFilter === "solar_inverter" ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold" : "text-[var(--text-secondary)]"}`}
              >
                Solar ({solarCount})
              </button>
            </div>

            {/* Risk Filters */}
            <div className="flex items-center border border-[var(--border)] rounded-[2px] bg-[var(--surface-raised)] text-xs font-mono">
              <button
                onClick={() => setRiskFilter("all")}
                className={`px-2.5 py-1 ${riskFilter === "all" ? "bg-[var(--surface-sunken)] font-semibold text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}
              >
                All States
              </button>
              <button
                onClick={() => setRiskFilter("at_risk")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${riskFilter === "at_risk" ? "bg-[var(--warn-surface)] text-[var(--warn-ink)] font-semibold" : "text-[var(--text-secondary)]"}`}
              >
                At Risk Only
              </button>
              <button
                onClick={() => setRiskFilter("nominal")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${riskFilter === "nominal" ? "bg-[var(--ok-surface)] text-[var(--ok)] font-semibold" : "text-[var(--text-secondary)]"}`}
              >
                Nominal
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[var(--text-tertiary)]" />
            <input
              type="text"
              placeholder="Search asset ID or site..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs bg-[var(--surface-raised)] border border-[var(--border-control)] rounded-[2px] text-[var(--text-primary)] placeholder-[var(--text-tertiary)] font-sans focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
        </div>

        {/* Compact Table Body */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left bg-[var(--surface-sunken)]">
                <th className="py-2.5 px-4">Asset ID</th>
                <th className="py-2.5 px-2">Type</th>
                <th className="py-2.5 px-2">Site</th>
                <th className="py-2.5 px-2">Status</th>
                <th className="py-2.5 px-2 text-right">Health</th>
                <th className="py-2.5 px-2 text-right">Risk Score</th>
                <th className="py-2.5 px-2 text-right">Power</th>
                <th className="py-2.5 px-2 text-right">Expected</th>
                <th className="py-2.5 px-2 text-right">Residual</th>
                <th className="py-2.5 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filteredAssets.map((asset) => (
                <tr
                  key={asset.asset_id}
                  className={`hover:bg-[var(--surface-sunken)] transition-colors ${
                    asset.risk_band === "critical"
                      ? "bg-[var(--critical-surface)]/20"
                      : asset.risk_band === "high"
                      ? "bg-[var(--warn-surface)]/10"
                      : ""
                  }`}
                >
                  <td className="py-2 px-4 font-semibold text-[var(--text-primary)] flex items-center space-x-2">
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        asset.status === "critical"
                          ? "bg-[var(--critical)]"
                          : asset.status === "warning"
                          ? "bg-[var(--warn)]"
                          : "bg-[var(--ok)]"
                      }`}
                    />
                    <Link
                      href={`/assets/${asset.asset_id}`}
                      className="hover:text-[var(--accent)] hover:underline"
                    >
                      {asset.asset_id}
                    </Link>
                  </td>
                  <td className="py-2 px-2 capitalize text-[var(--text-secondary)] font-sans">
                    {asset.asset_type === "wind_turbine" ? "Wind" : "Solar"}
                  </td>
                  <td className="py-2 px-2 text-[var(--text-secondary)] font-sans">
                    {asset.site}
                  </td>
                  <td className="py-2 px-2">
                    <StatusPill status={asset.status} />
                  </td>
                  <td className="py-2 px-2 text-right font-medium">
                    {asset.health_score.toFixed(1)}%
                  </td>
                  <td className="py-2 px-2 text-right font-semibold">
                    <span
                      className={
                        asset.risk_score >= 0.7
                          ? "text-[var(--critical)]"
                          : asset.risk_score >= 0.4
                          ? "text-[var(--warn-ink)]"
                          : "text-[var(--ok)]"
                      }
                    >
                      {(asset.risk_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right">{formatPower(asset.power_kw)}</td>
                  <td className="py-2 px-2 text-right text-[var(--text-secondary)]">
                    {formatPower(asset.expected_power_kw)}
                  </td>
                  <td
                    className={`py-2 px-2 text-right font-semibold ${
                      asset.residual_pct < -5
                        ? "text-[var(--critical)]"
                        : asset.residual_pct > 5
                        ? "text-[var(--series-1)]"
                        : "text-[var(--text-secondary)]"
                    }`}
                  >
                    {formatPercent(asset.residual_pct, true)}
                  </td>
                  <td className="py-2 px-4 text-center">
                    <Link
                      href={`/assets/${asset.asset_id}`}
                      className="text-[11px] text-[var(--accent)] hover:underline font-sans"
                    >
                      Inspect
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-3 border-t border-[var(--border)] text-[10px] font-mono text-[var(--text-tertiary)] flex justify-between">
          <span>SOURCE: GET /api/assets ({assets.length} assets)</span>
          <span>{assetsLive ? "LIVE" : "CACHED — API unavailable, showing last-known snapshot"}</span>
        </div>
      </div>
    </div>
  );
}
