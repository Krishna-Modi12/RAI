"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Wind,
  Sun,
  BookOpen,
  Cpu,
  BarChart3,
  Moon,
  SunMedium,
  CheckCircle2,
  AlertCircle,
  Wrench,
} from "lucide-react";
import { getHealth, getFleetOverview } from "../lib/api";
import { HealthResponse, FleetOverview } from "../lib/types";

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [utcTime, setUtcTime] = useState<string>("");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLive, setHealthLive] = useState(false);
  const [overview, setOverview] = useState<FleetOverview | null>(null);

  useEffect(() => {
    // Theme sync
    const savedTheme = localStorage.getItem("rai.theme") as "light" | "dark" | null;
    if (savedTheme) {
      // eslint-disable-next-line
      setTheme(savedTheme);
      document.documentElement.setAttribute("data-theme", savedTheme);
    }

    // Live UTC Clock
    const updateTime = () => {
      const now = new Date();
      setUtcTime(
        now.toISOString().substring(11, 19) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);

    async function loadStatus() {
      const [h, ov] = await Promise.all([getHealth(), getFleetOverview()]);
      setHealth(h.data);
      setHealthLive(h.live);
      setOverview(ov.data);
    }
    loadStatus();

    return () => clearInterval(interval);
  }, []);

  const windCount = overview?.by_type?.find((t) => t.asset_type === "wind_turbine")?.count;
  const solarCount = overview?.by_type?.find((t) => t.asset_type === "solar_inverter")?.count;

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("rai.theme", next);
    document.documentElement.setAttribute("data-theme", next);
  };

  const navItems = [
    { href: "/", label: "Fleet Command", icon: Activity },
    { href: "/assets", label: "Asset Registry", icon: Wind },
    { href: "/work-orders", label: "Operations", icon: Wrench },
    { href: "/soiling", label: "Soiling & Weather", icon: Sun },
    { href: "/evaluation", label: "Model Scorecard", icon: BarChart3 },
    { href: "/knowledge", label: "Knowledge Corpus", icon: BookOpen },
    { href: "/simulator", label: "Simulator Console", icon: Cpu },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[var(--surface)] text-[var(--text-primary)]">
      {/* Top Bar - 48px */}
      <header className="h-12 sticky top-0 z-40 bg-[var(--surface-raised)] border-b border-[var(--border)] px-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-semibold tracking-tight text-lg text-[var(--accent)] font-sans whitespace-nowrap">
              RAI
            </span>
          </Link>
          <div className="hidden sm:flex items-center text-xs text-[var(--text-secondary)] bg-[var(--surface-sunken)] px-2.5 py-1 rounded-[2px] border border-[var(--border)]">
            <span className="font-medium text-[var(--text-primary)] mr-1.5">Site:</span>
            <span>
              Kutch Wind ({windCount ?? "—"}) + Charanka Solar ({solarCount ?? "—"})
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Data freshness & UTC Clock */}
          <div className="flex items-center space-x-2 text-xs font-mono text-[var(--text-secondary)] bg-[var(--surface-sunken)] px-2 py-1 rounded-[2px] border border-[var(--border)]">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--ok)] animate-pulse" />
            <span className="text-[var(--text-primary)]">{utcTime || "12:00:00 UTC"}</span>
          </div>

          {/* Needle Status — sourced from GET /api/health, per docs/DESIGN.md §6.1 */}
          <div
            className={`hidden md:flex items-center space-x-1.5 text-xs font-mono px-2 py-1 rounded-[2px] border ${
              health?.needle_available
                ? "bg-[var(--accent-surface)] text-[var(--accent)] border-[var(--accent-border)]"
                : "bg-[var(--warn-surface)] text-[var(--warn-ink)] border-[var(--warn)]"
            }`}
            title={healthLive ? "Live from /api/health" : "API unavailable — showing last-known snapshot"}
          >
            {health?.needle_available ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
            <span>
              {health?.needle_available ? "NEEDLE2" : "DETERMINISTIC REASONER (FALLBACK)"}
              {!healthLive && " · cached"}
            </span>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="p-1.5 rounded-[2px] hover:bg-[var(--surface-sunken)] text-[var(--text-secondary)] transition-colors"
          >
            {theme === "light" ? (
              <Moon className="w-4 h-4" />
            ) : (
              <SunMedium className="w-4 h-4" />
            )}
          </button>
        </div>
      </header>

      {/* Main Container with Left Rail */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Rail - 224px */}
        <aside className="w-56 flex-shrink-0 bg-[var(--surface-inset)] border-r border-[var(--border)] flex flex-col justify-between p-3 hidden md:flex">
          <nav className="space-y-1">
            <div className="px-2 py-1.5 text-[11px] font-mono tracking-wider text-[var(--text-tertiary)] uppercase">
              Operations Control
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href.split("/")[1] ? `/${item.href.split("/")[1]}` : item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-2.5 px-3 py-2 text-xs font-medium rounded-[2px] transition-colors border-l-2 ${
                    isActive
                      ? "bg-[var(--surface-raised)] text-[var(--accent)] border-[var(--accent)] shadow-sm"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-sunken)] border-transparent"
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="whitespace-nowrap">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Compact Fleet Counter Block — sourced from GET /api/fleet */}
          <div className="pt-3 border-t border-[var(--border)] space-y-2">
            <div className="bg-[var(--surface-raised)] p-2.5 rounded-[2px] border border-[var(--border)] text-xs font-mono space-y-1">
              <div className="flex justify-between text-[var(--text-secondary)]">
                <span>Fleet Active</span>
                <span className="text-[var(--text-primary)] font-semibold">
                  {overview ? `${overview.assets_total - overview.assets_offline} / ${overview.assets_total}` : "—"}
                </span>
              </div>
              <div className="flex justify-between text-[var(--warn-ink)]">
                <span>At Risk</span>
                <span className="font-semibold">{overview?.assets_at_risk ?? "—"}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Scrollable Main Surface */}
        <main className="flex-1 overflow-y-auto bg-[var(--surface)] p-4 sm:p-6 lg:p-8">
          <div className="max-w-[1600px] mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
