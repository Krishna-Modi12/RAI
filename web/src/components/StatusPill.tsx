import React from "react";

type RiskBand = "low" | "elevated" | "high" | "critical";
type AssetStatus = "nominal" | "warning" | "critical" | "offline";

interface StatusPillProps {
  band?: RiskBand;
  status?: AssetStatus;
  label?: string;
}

export default function StatusPill({ band, status, label }: StatusPillProps) {
  let bg = "bg-[var(--surface-sunken)]";
  let text = "text-[var(--text-secondary)]";
  let border = "border-[var(--border)]";
  let glyph = "●";
  let textLabel = label || "";

  if (band) {
    switch (band) {
      case "critical":
        bg = "bg-[var(--critical-surface)]";
        text = "text-[var(--critical-ink)]";
        border = "border-[var(--critical)]";
        glyph = "▲";
        textLabel = label || "Critical";
        break;
      case "high":
        bg = "bg-[var(--warn-surface)]";
        text = "text-[var(--warn-ink)]";
        border = "border-[var(--warn)]";
        glyph = "▲";
        textLabel = label || "High Risk";
        break;
      case "elevated":
        bg = "bg-[var(--warn-surface)]";
        text = "text-[var(--warn-ink)]";
        border = "border-[var(--warn)]";
        glyph = "◆";
        textLabel = label || "Elevated";
        break;
      case "low":
        bg = "bg-[var(--ok-surface)]";
        text = "text-[var(--ok)]";
        border = "border-[var(--ok)]";
        glyph = "●";
        textLabel = label || "Nominal";
        break;
    }
  } else if (status) {
    switch (status) {
      case "critical":
        bg = "bg-[var(--critical-surface)]";
        text = "text-[var(--critical-ink)]";
        border = "border-[var(--critical)]";
        glyph = "▲";
        textLabel = label || "Critical";
        break;
      case "warning":
        bg = "bg-[var(--warn-surface)]";
        text = "text-[var(--warn-ink)]";
        border = "border-[var(--warn)]";
        glyph = "◆";
        textLabel = label || "Warning";
        break;
      case "offline":
        bg = "bg-[var(--surface-sunken)]";
        text = "text-[var(--text-tertiary)]";
        border = "border-[var(--border)]";
        glyph = "○";
        textLabel = label || "Offline";
        break;
      case "nominal":
      default:
        bg = "bg-[var(--ok-surface)]";
        text = "text-[var(--ok)]";
        border = "border-[var(--ok)]";
        glyph = "●";
        textLabel = label || "Nominal";
        break;
    }
  }

  return (
    <span
      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-[2px] border text-[11px] font-sans font-medium ${bg} ${text} ${border}`}
    >
      <span className="text-[9px] leading-none">{glyph}</span>
      <span>{textLabel}</span>
    </span>
  );
}
