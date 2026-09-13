"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import StatusPill from "../../components/StatusPill";
import MetricTile from "../../components/MetricTile";
import { getFleetAssets } from "../../lib/api";
import { formatPower, formatPercent } from "../../lib/format";
import { FleetAssetItem } from "../../lib/types";
import {
  Wind,
  Sun,
  Search,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

type SortField = "asset_id" | "health_score" | "risk_score" | "power_kw" | "residual_pct";
type SortDirection = "asc" | "desc";

export default function AssetRegistryPage() {
  const [assets, setAssets] = useState<FleetAssetItem[]>([]);
  const [assetsLive, setAssetsLive] = useState(false);
  const [loading, setLoading] = useState(true);

  // Filters & Controls
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "wind_turbine" | "solar_inverter">("all");
  const [riskFilter, setRiskFilter] = useState<"all" | "critical" | "high" | "elevated" | "low">("all");
  const [siteFilter, setSiteFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("risk_score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  useEffect(() => {
    async function loadData() {
      try {
        const assetRes = await getFleetAssets();
        setAssets(assetRes.data);
        setAssetsLive(assetRes.live);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Compute available sites for filtering
  const availableSites = useMemo(() => {
    const sites = new Set<string>();
    assets.forEach((a) => {
      if (a.site) sites.add(a.site);
    });
    return Array.from(sites);
  }, [assets]);

  // Handle sorting toggles
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection(field === "asset_id" ? "asc" : "desc");
    }
  };

  // Filtered and Sorted Assets
  const filteredAssets = useMemo(() => {
    return assets
      .filter((asset) => {
        if (typeFilter !== "all" && asset.asset_type !== typeFilter) return false;
        if (riskFilter !== "all" && asset.risk_band !== riskFilter) return false;
        if (siteFilter !== "all" && asset.site !== siteFilter) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const matchesId = asset.asset_id.toLowerCase().includes(q);
          const matchesName = asset.name?.toLowerCase().includes(q);
          const matchesSite = asset.site?.toLowerCase().includes(q);
          const matchesState = asset.operating_state?.toLowerCase().includes(q);
          if (!matchesId && !matchesName && !matchesSite && !matchesState) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];

        if (typeof valA === "string" && typeof valB === "string") {
          return sortDirection === "asc"
            ? valA.localeCompare(valB)
            : valB.localeCompare(valA);
        }

        const numA = Number(valA) || 0;
        const numB = Number(valB) || 0;
        return sortDirection === "asc" ? numA - numB : numB - numA;
      });
  }, [assets, typeFilter, riskFilter, siteFilter, searchQuery, sortField, sortDirection]);

  const windAssets = assets.filter((a) => a.asset_type === "wind_turbine");
  const solarAssets = assets.filter((a) => a.asset_type === "solar_inverter");
  const atRiskCount = assets.filter((a) => a.risk_band === "high" || a.risk_band === "critical").length;

  return (
    <div className="space-y-6">
      {/* Page Heading */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Fleet Asset Registry
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Complete inventory and operational status of all {assets.length || 42} renewable energy generation assets
          </p>
        </div>
        <div className="flex items-center space-x-2 font-mono text-xs text-[var(--text-secondary)]">
          <span className="w-2 h-2 rounded-full bg-[var(--ok)]" />
          <span>CARE-benchmarked Registry</span>
        </div>
      </div>

      {/* Summary KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile
          label="Total Registered Units"
          value={loading ? "—" : `${assets.length}`}
          context="Kutch Wind & Charanka Solar"
          hero
          source="GET /api/assets"
          live={assetsLive}
        />
        <MetricTile
          label="Wind Turbine Units"
          value={loading ? "—" : `${windAssets.length}`}
          context="Suzlon S88 / GE 2.1 MW Fleet"
          source="GET /api/assets?type=wind"
          live={assetsLive}
        />
        <MetricTile
          label="Solar Central Inverters"
          value={loading ? "—" : `${solarAssets.length}`}
          context="ABB PVS980 / 1.0-1.5 MW Fleet"
          source="GET /api/assets?type=solar"
          live={assetsLive}
        />
        <MetricTile
          label="High Risk / Warning Units"
          value={loading ? "—" : `${atRiskCount}`}
          context={`${formatPercent(assets.length ? (atRiskCount / assets.length) * 100 : 0)} of fleet requires attention`}
          source="GET /api/fleet"
          live={assetsLive}
        />
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden space-y-3">
        <div className="p-3 bg-[var(--surface-inset)] border-b border-[var(--border)] flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xs font-semibold text-[var(--text-primary)] whitespace-nowrap">
              {loading
                ? "Loading Fleet Registry…"
                : `Assets (${filteredAssets.length} of ${assets.length})`}
            </h2>

            {/* Asset Type Filter */}
            <div className="flex items-center border border-[var(--border)] rounded-[2px] bg-[var(--surface-raised)] text-xs font-mono">
              <button
                onClick={() => setTypeFilter("all")}
                className={`px-2.5 py-1 ${
                  typeFilter === "all"
                    ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setTypeFilter("wind_turbine")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  typeFilter === "wind_turbine"
                    ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Wind ({windAssets.length})
              </button>
              <button
                onClick={() => setTypeFilter("solar_inverter")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  typeFilter === "solar_inverter"
                    ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Solar ({solarAssets.length})
              </button>
            </div>

            {/* Risk Band Filter */}
            <div className="flex items-center border border-[var(--border)] rounded-[2px] bg-[var(--surface-raised)] text-xs font-mono">
              <button
                onClick={() => setRiskFilter("all")}
                className={`px-2.5 py-1 ${
                  riskFilter === "all"
                    ? "bg-[var(--surface-sunken)] font-semibold text-[var(--text-primary)]"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                All Risks
              </button>
              <button
                onClick={() => setRiskFilter("critical")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  riskFilter === "critical"
                    ? "bg-[var(--critical-surface)] text-[var(--critical)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Critical
              </button>
              <button
                onClick={() => setRiskFilter("high")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  riskFilter === "high"
                    ? "bg-[var(--warn-surface)] text-[var(--warn-ink)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                High
              </button>
              <button
                onClick={() => setRiskFilter("elevated")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  riskFilter === "elevated"
                    ? "bg-[var(--accent-surface)] text-[var(--accent)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Elevated
              </button>
              <button
                onClick={() => setRiskFilter("low")}
                className={`px-2.5 py-1 border-l border-[var(--border)] ${
                  riskFilter === "low"
                    ? "bg-[var(--ok-surface)] text-[var(--ok)] font-semibold"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Nominal
              </button>
            </div>

            {/* Site Filter */}
            {availableSites.length > 1 && (
              <select
                value={siteFilter}
                onChange={(e) => setSiteFilter(e.target.value)}
                className="px-2.5 py-1 text-xs bg-[var(--surface-raised)] border border-[var(--border-control)] rounded-[2px] text-[var(--text-primary)] font-mono focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="all">All Sites</option>
                {availableSites.map((site) => (
                  <option key={site} value={site}>
                    {site}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Search Box */}
          <div className="relative min-w-[220px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[var(--text-tertiary)]" />
            <input
              type="text"
              placeholder="Search ID, name, site..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1 text-xs bg-[var(--surface-raised)] border border-[var(--border-control)] rounded-[2px] text-[var(--text-primary)] placeholder-[var(--text-tertiary)] font-sans focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
        </div>

        {/* Assets Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[var(--border)] text-[10px] text-[var(--text-tertiary)] uppercase text-left bg-[var(--surface-sunken)]">
                <th
                  className="py-2.5 px-4 cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                  onClick={() => handleSort("asset_id")}
                >
                  <div className="flex items-center space-x-1">
                    <span>Asset ID</span>
                    {sortField === "asset_id" && (
                      sortDirection === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                    )}
                  </div>
                </th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Site / Park</th>
                <th className="py-2.5 px-3">Status</th>
                <th
                  className="py-2.5 px-3 text-right cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                  onClick={() => handleSort("health_score")}
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Health</span>
                    {sortField === "health_score" && (
                      sortDirection === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                    )}
                  </div>
                </th>
                <th
                  className="py-2.5 px-3 text-right cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                  onClick={() => handleSort("risk_score")}
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Risk Score</span>
                    {sortField === "risk_score" && (
                      sortDirection === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                    )}
                  </div>
                </th>
                <th
                  className="py-2.5 px-3 text-right cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                  onClick={() => handleSort("power_kw")}
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Actual Power</span>
                    {sortField === "power_kw" && (
                      sortDirection === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                    )}
                  </div>
                </th>
                <th className="py-2.5 px-3 text-right">Expected</th>
                <th
                  className="py-2.5 px-3 text-right cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                  onClick={() => handleSort("residual_pct")}
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Residual</span>
                    {sortField === "residual_pct" && (
                      sortDirection === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                    )}
                  </div>
                </th>
                <th className="py-2.5 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filteredAssets.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-[var(--text-tertiary)]">
                    {loading ? "Loading assets data..." : "No assets matching current filters."}
                  </td>
                </tr>
              ) : (
                filteredAssets.map((asset) => {
                  const isWind = asset.asset_type === "wind_turbine";
                  return (
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
                      <td className="py-2.5 px-4 font-semibold text-[var(--text-primary)]">
                        <Link
                          href={`/assets/${asset.asset_id}`}
                          className="hover:text-[var(--accent)] hover:underline flex items-center space-x-2"
                        >
                          {isWind ? (
                            <Wind className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" />
                          ) : (
                            <Sun className="w-3.5 h-3.5 text-[var(--series-2)] flex-shrink-0" />
                          )}
                          <span>{asset.asset_id}</span>
                        </Link>
                      </td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                        {isWind ? "Wind Turbine" : "Solar Inverter"}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] truncate max-w-[140px]">
                        {asset.site}
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusPill band={asset.risk_band} />
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`font-semibold ${
                            asset.health_score < 70
                              ? "text-[var(--critical)]"
                              : asset.health_score < 85
                              ? "text-[var(--warn-ink)]"
                              : "text-[var(--ok)]"
                          }`}
                        >
                          {asset.health_score.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-[var(--text-primary)]">
                        {asset.risk_score.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-[var(--text-primary)] font-medium">
                        {formatPower(asset.power_kw)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">
                        {formatPower(asset.expected_power_kw)}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={
                            Math.abs(asset.residual_pct) > 15
                              ? "text-[var(--critical)] font-semibold"
                              : Math.abs(asset.residual_pct) > 8
                              ? "text-[var(--warn-ink)]"
                              : "text-[var(--text-secondary)]"
                          }
                        >
                          {asset.residual_pct > 0 ? `+${asset.residual_pct.toFixed(1)}%` : `${asset.residual_pct.toFixed(1)}%`}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        <Link
                          href={`/assets/${asset.asset_id}`}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 bg-[var(--surface-sunken)] border border-[var(--border-control)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[11px] font-medium text-[var(--text-primary)] rounded-[2px] transition-colors whitespace-nowrap"
                        >
                          <span>Deep-Dive</span>
                          <ArrowUpRight className="w-3 h-3 flex-shrink-0" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Source metadata stamp */}
        <div className="p-3 bg-[var(--surface-sunken)] border-t border-[var(--border)] flex items-center justify-between text-[11px] font-mono text-[var(--text-tertiary)]">
          <span>SOURCE: GET /api/assets ({assets.length} fleet generation assets)</span>
          <span className="flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />
            <span>{assetsLive ? "Live telemetry synced" : "Demonstration telemetry snapshot"}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
