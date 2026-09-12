"use client";

import React, { useState } from "react";
import { TimeseriesPoint } from "../lib/types";
import { formatTimestamp } from "../lib/format";

interface HeroChartProps {
  data: TimeseriesPoint[];
  title?: string;
  unit?: string;
}

export default function HeroChart({
  data,
  title = "Power: Actual vs Expected (7-Day Horizon)",
  unit = "kW",
}: HeroChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-6 text-center text-xs font-mono text-[var(--text-tertiary)]">
        — No timeseries observations recorded —
      </div>
    );
  }

  // Dimensions
  const width = 800;
  const mainHeight = 220;
  const residualHeight = 70;
  const gap = 16;
  const padL = 60;
  const padR = 40;
  const padT = 20;
  const padB = 24;

  const totalHeight = padT + mainHeight + gap + residualHeight + padB;
  const plotW = width - padL - padR;

  // Scales for Main Plot
  const maxVal = Math.max(...data.map((d) => Math.max(d.upper_band || 0, d.actual, d.expected))) * 1.08;
  const minVal = 0;

  const getX = (index: number) => padL + (index / (data.length - 1)) * plotW;
  const getY = (val: number) => padT + mainHeight - ((val - minVal) / (maxVal - minVal)) * mainHeight;

  // Scales for Residual Strip
  const maxResidualZ = 4.0;
  const minResidualZ = -4.0;
  const resZeroY = padT + mainHeight + gap + residualHeight / 2;
  const getResidualY = (z: number) => {
    const clamped = Math.max(-maxResidualZ, Math.min(maxResidualZ, z));
    return resZeroY - (clamped / maxResidualZ) * (residualHeight / 2);
  };

  // Generate Band Path
  const bandPoints = [
    ...data.map((d, i) => `${getX(i)},${getY(d.upper_band)}`),
    ...data
      .slice()
      .reverse()
      .map((d, i) => `${getX(data.length - 1 - i)},${getY(d.lower_band)}`),
  ].join(" ");

  // Generate Lines
  const expectedPath = data.map((d, i) => `${i === 0 ? "M" : "L"}${getX(i)},${getY(d.expected)}`).join(" ");
  const actualPath = data.map((d, i) => `${i === 0 ? "M" : "L"}${getX(i)},${getY(d.actual)}`).join(" ");

  const hoveredPoint = hoverIdx !== null ? data[hoverIdx] : data[data.length - 1];

  return (
    <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 flex flex-col space-y-3 select-none">
      {/* Chart Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
        <div>
          <h3 className="text-xs font-semibold tracking-tight text-[var(--text-primary)]">
            {title}
          </h3>
          <div className="text-[11px] font-mono text-[var(--text-tertiary)] flex items-center space-x-3 mt-0.5">
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-0.5 bg-[var(--series-1)] inline-block" />
              <span>Actual ({unit})</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-0.5 border-t border-dashed border-[var(--viz-expected)] inline-block" />
              <span>Expected ({unit})</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 bg-[var(--accent)] opacity-20 inline-block" />
              <span>Normal Range (p10–p90)</span>
            </span>
          </div>
        </div>

        {/* Live Hover Readout */}
        {hoveredPoint && (
          <div className="text-xs font-mono bg-[var(--surface-sunken)] border border-[var(--border)] px-2.5 py-1 rounded-[2px] flex items-center space-x-3">
            <span className="text-[var(--text-tertiary)]">
              {formatTimestamp(hoveredPoint.timestamp)}
            </span>
            <span className="text-[var(--series-1)] font-semibold">
              Act: {hoveredPoint.actual.toLocaleString()} {unit}
            </span>
            <span className="text-[var(--text-secondary)]">
              Exp: {hoveredPoint.expected.toLocaleString()} {unit}
            </span>
            <span
              className={`font-semibold ${
                Math.abs(hoveredPoint.z_score) >= 3
                  ? "text-[var(--critical)]"
                  : Math.abs(hoveredPoint.z_score) >= 2
                  ? "text-[var(--warn-ink)]"
                  : "text-[var(--text-secondary)]"
              }`}
            >
              Residual: {hoveredPoint.residual > 0 ? "+" : ""}
              {hoveredPoint.residual} {unit} ({hoveredPoint.z_score > 0 ? "+" : ""}
              {hoveredPoint.z_score}σ)
            </span>
          </div>
        )}
      </div>

      {/* SVG Viewport */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${totalHeight}`}
          className="w-full h-auto max-w-full font-mono text-[10px]"
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* Main Grid Lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const y = padT + mainHeight * (1 - pct);
            const val = Math.round(minVal + pct * (maxVal - minVal));
            return (
              <g key={pct}>
                <line
                  x1={padL}
                  y1={y}
                  x2={width - padR}
                  y2={y}
                  stroke="var(--border)"
                  strokeDasharray="2 2"
                  strokeWidth="1"
                />
                <text
                  x={padL - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--text-tertiary)"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Upper/Lower Normal Band */}
          <polygon points={bandPoints} fill="var(--accent)" opacity="0.12" />

          {/* Expected Behavior Line */}
          <path
            d={expectedPath}
            fill="none"
            stroke="var(--viz-expected)"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />

          {/* Actual Measured Line */}
          <path
            d={actualPath}
            fill="none"
            stroke="var(--series-1)"
            strokeWidth="2"
            strokeLinecap="round"
          />

          {/* Latest Point Indicator */}
          {data.length > 0 && (
            <circle
              cx={getX(data.length - 1)}
              cy={getY(data[data.length - 1].actual)}
              r="4"
              fill="var(--series-1)"
              stroke="var(--surface-raised)"
              strokeWidth="2"
            />
          )}

          {/* Residual Strip Baseline & Thresholds */}
          <g>
            {/* Zero Line */}
            <line
              x1={padL}
              y1={resZeroY}
              x2={width - padR}
              y2={resZeroY}
              stroke="var(--border-strong)"
              strokeWidth="1"
            />
            {/* +2 / -2 Sigma */}
            <line
              x1={padL}
              y1={getResidualY(2)}
              x2={width - padR}
              y2={getResidualY(2)}
              stroke="var(--border)"
              strokeDasharray="2 2"
            />
            <line
              x1={padL}
              y1={getResidualY(-2)}
              x2={width - padR}
              y2={getResidualY(-2)}
              stroke="var(--border)"
              strokeDasharray="2 2"
            />
            {/* +3 / -3 Sigma Alerts */}
            <line
              x1={padL}
              y1={getResidualY(3)}
              x2={width - padR}
              y2={getResidualY(3)}
              stroke="var(--warn)"
              strokeDasharray="2 2"
              opacity="0.6"
            />
            <line
              x1={padL}
              y1={getResidualY(-3)}
              x2={width - padR}
              y2={getResidualY(-3)}
              stroke="var(--critical)"
              strokeDasharray="2 2"
              opacity="0.6"
            />

            {/* Right-edge Residual Labels */}
            <text
              x={width - padR + 6}
              y={resZeroY + 3}
              fill="var(--text-tertiary)"
            >
              0σ
            </text>
            <text
              x={width - padR + 6}
              y={getResidualY(3) + 3}
              fill="var(--warn-ink)"
            >
              +3σ
            </text>
            <text
              x={width - padR + 6}
              y={getResidualY(-3) + 3}
              fill="var(--critical)"
            >
              -3σ
            </text>

            {/* Left Axis Label */}
            <text
              x={padL - 8}
              y={resZeroY + 3}
              textAnchor="end"
              fill="var(--text-tertiary)"
            >
              RESIDUAL
            </text>
          </g>

          {/* Residual Columns */}
          {data.map((d, i) => {
            const x = getX(i);
            const colW = Math.max(2, plotW / data.length - 2);
            const y = d.z_score >= 0 ? getResidualY(d.z_score) : resZeroY;
            const h = Math.abs(getResidualY(d.z_score) - resZeroY);
            const isAlert = Math.abs(d.z_score) >= 3;
            const isWarn = Math.abs(d.z_score) >= 2;

            const colFill = isAlert
              ? "var(--critical)"
              : isWarn
              ? "var(--warn)"
              : d.z_score < 0
              ? "var(--series-1)"
              : "var(--border-strong)";

            return (
              <rect
                key={i}
                x={x - colW / 2}
                y={y}
                width={colW}
                height={Math.max(1, h)}
                fill={colFill}
                opacity={isAlert ? "0.9" : "0.75"}
              />
            );
          })}

          {/* Interactive Crosshair & Slices */}
          {data.map((d, i) => {
            const x = getX(i);
            const sliceW = plotW / data.length;
            return (
              <rect
                key={`slice-${i}`}
                x={x - sliceW / 2}
                y={padT}
                width={sliceW}
                height={totalHeight - padT - padB}
                fill="transparent"
                onMouseEnter={() => setHoverIdx(i)}
                className="cursor-crosshair"
              />
            );
          })}

          {/* Active Hover Guide */}
          {hoverIdx !== null && (
            <line
              x1={getX(hoverIdx)}
              y1={padT}
              x2={getX(hoverIdx)}
              y2={totalHeight - padB}
              stroke="var(--text-primary)"
              strokeWidth="1"
              strokeDasharray="2 2"
              pointerEvents="none"
            />
          )}
        </svg>
      </div>

      {/* Trust Device Source Line */}
      <div className="pt-2 border-t border-[var(--border)] text-[10px] font-mono text-[var(--text-tertiary)] flex items-center justify-between">
        <span>SOURCE: GET /api/assets/{`{id}`}/timeseries · physics_gbm_residual_engine</span>
        <span>RESIDUAL METRIC: signed_z = (actual - expected) / σ_healthy</span>
      </div>
    </div>
  );
}
