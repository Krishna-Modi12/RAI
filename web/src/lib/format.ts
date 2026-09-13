/**
 * Formatting utilities for Renewable Asset Intelligence (RAI)
 * Adheres strictly to docs/DESIGN.md:
 * - Indian currency formatting (₹ Lakhs / Crores)
 * - Strict unit conventions and thin spaces
 * - Tabular mono formatting for numerals
 * - Em-dash for null values with 'not evaluated' title
 */

export function formatINR(
  amount: number | null | undefined,
  options?: { showExact?: boolean }
): { display: string; exact: string } {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return { display: "—", exact: "not evaluated" };
  }

  const exactStr = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

  let displayStr = "";
  const abs = Math.abs(amount);

  if (abs >= 1_00_00_000) {
    displayStr = `₹${(amount / 1_00_00_000).toFixed(2)} Cr`;
  } else if (abs >= 1_00_000) {
    displayStr = `₹${(amount / 1_00_000).toFixed(2)} L`;
  } else {
    displayStr = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  }

  return {
    display: options?.showExact ? exactStr : displayStr,
    exact: exactStr,
  };
}

export function formatPower(kw: number | null | undefined): string {
  if (kw === null || kw === undefined || isNaN(kw)) return "—";
  if (Math.abs(kw) >= 100) {
    return `${Math.round(kw).toLocaleString("en-IN")} kW`;
  }
  return `${kw.toFixed(1)} kW`;
}

export function formatEnergy(kwh: number | null | undefined): string {
  if (kwh === null || kwh === undefined || isNaN(kwh)) return "—";
  return `${Math.round(kwh).toLocaleString("en-IN")} kWh`;
}

export function formatTemp(celsius: number | null | undefined): string {
  if (celsius === null || celsius === undefined || isNaN(celsius)) return "—";
  return `${celsius.toFixed(1)}°C`;
}

export function formatVibration(mms: number | null | undefined): string {
  if (mms === null || mms === undefined || isNaN(mms)) return "—";
  return `${mms.toFixed(2)} mm/s`;
}

export function formatPercent(
  pct: number | null | undefined,
  signed = false
): string {
  if (pct === null || pct === undefined || isNaN(pct)) return "—";
  const sign = signed && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function formatRatio(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined || isNaN(ratio)) return "—";
  return ratio.toFixed(3);
}

export function formatZScore(z: number | null | undefined): string {
  if (z === null || z === undefined || isNaN(z)) return "—";
  const sign = z > 0 ? "+" : "";
  return `${sign}${z.toFixed(1)}`;
}

export function formatTimestamp(isoStr: string | null | undefined): string {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }) + " UTC";
  } catch {
    return isoStr;
  }
}
