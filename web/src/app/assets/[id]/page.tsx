"use client";

import React, { useState, useEffect, use } from "react";
import Link from "next/link";
import HeroChart from "../../../components/HeroChart";
import EvidenceAccordion from "../../../components/EvidenceAccordion";
import StatusPill from "../../../components/StatusPill";
import { getAssetTimeseries, getInvestigation } from "../../../lib/api";
import { formatPower, formatINR, formatPercent } from "../../../lib/format";
import { TimeseriesPoint, InvestigationResult } from "../../../lib/types";
import { Wind, Sun, ArrowLeft, Cpu } from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AssetPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const assetId = resolvedParams.id;
  const isWind = assetId.startsWith("WT");

  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [timeseriesLive, setTimeseriesLive] = useState(false);
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);
  const [investigationLive, setInvestigationLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const [ts, inv] = await Promise.all([
        getAssetTimeseries(assetId),
        getInvestigation(assetId),
      ]);
      if (cancelled) return;
      setTimeseries(ts.data);
      setTimeseriesLive(ts.live);
      setInvestigation(inv.data);
      setInvestigationLive(inv.live);
      setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [assetId]);

  const handleRunAgent = async () => {
    setRecomputing(true);
    const inv = await getInvestigation(assetId);
    setInvestigation(inv.data);
    setInvestigationLive(inv.live);
    setTimeout(() => setRecomputing(false), 600);
  };

  const severityToBand = (severity: string | undefined): "low" | "elevated" | "high" | "critical" => {
    switch (severity) {
      case "critical":
        return "critical";
      case "high":
        return "high";
      case "medium":
        return "elevated";
      default:
        return "low";
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs font-mono text-[var(--text-secondary)]">
        <Link href="/" className="hover:text-[var(--text-primary)] flex items-center space-x-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Fleet Command</span>
        </Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-semibold">{assetId}</span>
        <span>/</span>
        <span>Deep-Dive Investigation</span>
      </div>

      {/* Asset Header Banner */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-3 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[3px]">
            {isWind ? (
              <Wind className="w-6 h-6 text-[var(--accent)]" />
            ) : (
              <Sun className="w-6 h-6 text-[var(--series-2)]" />
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-xl font-mono font-semibold tracking-tight text-[var(--text-primary)]">
                {assetId}
              </h1>
              {loading ? (
                <StatusPill label="Syncing…" />
              ) : (
                <StatusPill band={severityToBand(investigation?.evidence.anomaly?.severity)} />
              )}
              <span className="text-xs font-mono text-[var(--text-tertiary)] bg-[var(--surface-sunken)] px-2 py-0.5 rounded-[2px] border border-[var(--border)]">
                {isWind ? "Suzlon S111 / 2.1 MW" : "SMA Central / 1.0 MW"}
              </span>
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-1">
              {isWind ? "Kutch Wind Farm · Sector 3 · Feeder 4B" : "Charanka Solar Park · Array Zone 2"}
            </div>
          </div>
        </div>

        {/* Action Button: Run Reasoning Cycle */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRunAgent}
            disabled={recomputing}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)] font-sans text-xs font-medium rounded-[2px] transition-colors shadow-sm disabled:opacity-50"
          >
            <Cpu className={`w-4 h-4 ${recomputing ? "animate-spin" : ""}`} />
            <span>{recomputing ? "Executing Needle2..." : "Run Needle2 Reasoning"}</span>
          </button>
        </div>
      </div>

      {/* Quick Metrics Strip */}
      <div className="flex items-center justify-end">
        <span
          className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider"
          title={
            loading
              ? "Fetching current telemetry and investigation evidence"
              : timeseriesLive && investigationLive
              ? undefined
              : "API unavailable — showing last-known snapshot"
          }
        >
          {loading
            ? "SYNCING…"
            : timeseriesLive && investigationLive
            ? "LIVE"
            : "CACHED · last-known snapshot"}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="p-3 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] space-y-2"
            >
              <div className="h-2.5 w-20 bg-[var(--surface-sunken)] rounded-[2px] animate-pulse" />
              <div className="h-4 w-16 bg-[var(--surface-sunken)] rounded-[2px] animate-pulse" />
              <div className="h-2.5 w-24 bg-[var(--surface-sunken)] rounded-[2px] animate-pulse" />
            </div>
          ))
        ) : (
          <>
            <div className="p-3 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px]">
              <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Measured Power</div>
              <div className="text-base font-semibold text-[var(--text-primary)] mt-1">
                {timeseries.length ? formatPower(timeseries[timeseries.length - 1].actual) : "—"}
              </div>
              <div className="text-[10px] text-[var(--text-tertiary)]">
                Exp: {timeseries.length ? formatPower(timeseries[timeseries.length - 1].expected) : "—"}
              </div>
            </div>

            <div className="p-3 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px]">
              <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Power Deficit</div>
              <div className="text-base font-semibold text-[var(--critical)] mt-1">
                {timeseries.length
                  ? formatPercent(
                      ((timeseries[timeseries.length - 1].actual -
                        timeseries[timeseries.length - 1].expected) /
                        (timeseries[timeseries.length - 1].expected || 1)) *
                        100,
                      true
                    )
                  : "—"}
              </div>
              <div className="text-[10px] text-[var(--text-tertiary)]">
                residual z: {timeseries.length ? timeseries[timeseries.length - 1].z_score : "—"}σ
              </div>
            </div>

            <div className="p-3 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px]">
              <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Anomaly Score</div>
              <div className="text-base font-semibold text-[var(--critical)] mt-1">
                {investigation?.evidence.anomaly?.score != null
                  ? `${(investigation.evidence.anomaly.score * 100).toFixed(0)}%`
                  : "—"}
              </div>
              <div className="text-[10px] text-[var(--text-tertiary)] capitalize">
                severity: {investigation?.evidence.anomaly?.severity ?? "—"}
              </div>
            </div>

            <div className="p-3 bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px]">
              <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Avoidable Exposure</div>
              <div className="text-base font-semibold text-[var(--text-primary)] mt-1">
                {investigation?.evidence.economics?.avoidable_exposure_inr != null
                  ? formatINR(investigation.evidence.economics.avoidable_exposure_inr).display
                  : "—"}
              </div>
              <div className="text-[10px] text-[var(--text-tertiary)]">
                Net NPV: {investigation ? `+${formatINR(investigation.intervention.net_benefit_inr).display}` : "—"}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Hero Chart: Expected vs Actual with Residual Strip */}
      <HeroChart
        data={timeseries}
        title={`${assetId} Active Power vs Normal Range (168-Hour Horizon)`}
        unit="kW"
      />

      {/* Evidence Accordion Ledger */}
      {investigation && <EvidenceAccordion investigation={investigation} />}
    </div>
  );
}
