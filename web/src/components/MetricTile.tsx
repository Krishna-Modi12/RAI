import React from "react";

interface MetricTileProps {
  label: string;
  value: string;
  unit?: string;
  context?: string;
  delta?: {
    value: string;
    isPositive?: boolean;
    isGood?: boolean;
  };
  hero?: boolean;
  source?: string;
  live?: boolean;
}

export default function MetricTile({
  label,
  value,
  unit,
  context,
  delta,
  hero = false,
  source,
  live = true,
}: MetricTileProps) {
  return (
    <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 flex flex-col justify-between min-h-[96px]">
      <div className="text-[11px] font-sans text-[var(--text-secondary)] tracking-tight">
        {label}
      </div>

      <div className="my-1 flex items-baseline space-x-1.5">
        <span
          className={`font-mono font-medium tracking-tight text-[var(--text-primary)] ${
            hero ? "text-3xl" : "text-2xl"
          }`}
        >
          {value}
        </span>
        {unit && (
          <span className="text-xs font-mono text-[var(--text-tertiary)]">
            {unit}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
        {context && <span>{context}</span>}
        {delta && (
          <span
            className={`font-mono flex items-center space-x-0.5 ${
              delta.isGood
                ? "text-[var(--ok)]"
                : delta.isGood === false
                ? "text-[var(--critical)]"
                : "text-[var(--text-secondary)]"
            }`}
          >
            <span>{delta.isPositive ? "▲" : "▼"}</span>
            <span>{delta.value}</span>
          </span>
        )}
      </div>
      {source && (
        <div className="mt-1.5 pt-1.5 border-t border-[var(--border)]">
          <span
            className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider"
            title={live ? undefined : "API unavailable — showing last-known snapshot value"}
          >
            {source}
            {!live && " · cached"}
          </span>
        </div>
      )}
    </div>
  );
}
