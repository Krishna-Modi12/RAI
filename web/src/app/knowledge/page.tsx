"use client";

import React, { useState } from "react";
import { searchKnowledge } from "../../lib/api";
import { BookOpen, Search, FileText, ArrowRight, ExternalLink } from "lucide-react";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const sampleQueries = [
    "bearing temperature delta SOP",
    "soiling ratio Kimber recovery",
    "inverter MPPT efficiency drop",
    "gearbox oil sampling intervals",
    "wind curtailment grid directive",
  ];

  const handleSearch = async (q = query) => {
    if (!q.trim()) return;
    setIsSearching(true);
    const data = await searchKnowledge(q);
    setResults(data.results || []);
    setIsSearching(false);
  };

  const domainDocs = [
    { id: "SOP-WIND-042", title: "Wind Turbine Gearbox & Bearing Temperature Monitoring", category: "SOP", sections: 14 },
    { id: "SOP-SOLAR-019", title: "PV Inverter Soiling Inspection & Jet Cleaning Protocol", category: "SOP", sections: 11 },
    { id: "TECH-WIND-101", title: "Suzlon S111 SCADA Signal Registry & Sensor Health Checks", category: "Specification", sections: 18 },
    { id: "TECH-SOLAR-202", title: "SMA Central Inverter Operating Limits & Derating Curves", category: "Specification", sections: 16 },
    { id: "FAIL-BEAR-001", title: "High-Speed Shaft Bearing Spalling Failure Mode Analysis", category: "Failure Guide", sections: 9 },
    { id: "FAIL-SOIL-002", title: "Desert Dust Deposition & Mud Cementation Kinetics in Kutch", category: "Failure Guide", sections: 12 },
    { id: "ECON-OPT-301", title: "Techno-Economic Maintenance Dispatch & Spares Optimization", category: "Economics", sections: 8 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Domain Knowledge Corpus & Technical SOPs
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Deterministic SQLite FTS5 RAG index spanning 19 engineering specifications, OEM manuals, and failure catalogs (221 sections)
          </p>
        </div>

        <div className="flex items-center space-x-2 font-mono text-xs text-[var(--accent)] bg-[var(--accent-surface)] px-2.5 py-1 rounded-[2px] border border-[var(--accent-border)]">
          <BookOpen className="w-4 h-4" />
          <span>FTS5 BM25 RETRIEVER ACTIVE</span>
        </div>
      </div>

      {/* Search Bar & Sample Pills */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-3">
        <div className="flex items-center space-x-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-[var(--text-tertiary)]" />
            <input
              type="text"
              placeholder="Search engineering SOPs, bearing tolerances, soiling limits..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-full pl-9 pr-4 py-2 text-xs bg-[var(--surface-sunken)] border border-[var(--border-control)] rounded-[2px] text-[var(--text-primary)] placeholder-[var(--text-tertiary)] font-sans focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={isSearching}
            className="px-4 py-2 bg-[var(--accent)] text-[var(--text-inverse)] hover:bg-[var(--accent-hover)] text-xs font-medium rounded-[2px] transition-colors"
          >
            {isSearching ? "Searching..." : "Query FTS5"}
          </button>
        </div>

        {/* Suggested Queries */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
          <span className="text-[var(--text-tertiary)] text-[11px] mr-1">Quick Queries:</span>
          {sampleQueries.map((sq) => (
            <button
              key={sq}
              onClick={() => {
                setQuery(sq);
                handleSearch(sq);
              }}
              className="px-2 py-0.5 bg-[var(--surface-sunken)] hover:bg-[var(--surface-inset)] border border-[var(--border)] rounded-[2px] text-[11px] text-[var(--text-secondary)] transition-colors"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      {results.length > 0 && (
        <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] p-4 space-y-3">
          <div className="flex justify-between items-center border-b border-[var(--border)] pb-2">
            <h2 className="text-xs font-semibold text-[var(--text-primary)]">
              Retrieved Technical Sections ({results.length} Matches)
            </h2>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
              Ranked by SQLite FTS5 BM25 Score
            </span>
          </div>

          <div className="space-y-3">
            {results.map((res, i) => (
              <div
                key={i}
                className="p-3 bg-[var(--surface-sunken)] border border-[var(--border)] rounded-[2px] space-y-1.5"
              >
                <div className="flex justify-between items-center text-xs font-semibold text-[var(--text-primary)]">
                  <span>{res.title}</span>
                  <span className="font-mono text-[10px] text-[var(--accent)]">
                    Doc: {res.doc_id || res.section_id}
                  </span>
                </div>
                <blockquote className="text-xs font-sans text-[var(--text-secondary)] leading-relaxed italic border-l-2 border-[var(--accent)] pl-2">
                  &ldquo;{res.snippet}&rdquo;
                </blockquote>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 19-Document Corpus Catalog */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex justify-between items-center">
          <h2 className="text-xs font-semibold text-[var(--text-primary)]">
            Core Engineering Knowledge Index (19 Domain Documents)
          </h2>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
            Indexed into artifacts/index/knowledge.db
          </span>
        </div>

        <div className="divide-y divide-[var(--border)]">
          {domainDocs.map((doc) => (
            <div
              key={doc.id}
              className="p-3.5 flex items-center justify-between hover:bg-[var(--surface-sunken)] transition-colors text-xs font-mono"
            >
              <div className="flex items-center space-x-3">
                <FileText className="w-4 h-4 text-[var(--accent)] flex-shrink-0" />
                <div>
                  <div className="font-semibold text-[var(--text-primary)] font-sans">
                    {doc.title}
                  </div>
                  <div className="text-[11px] text-[var(--text-tertiary)]">
                    {doc.id} · Category: {doc.category}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <span className="text-[11px] text-[var(--text-secondary)]">
                  {doc.sections} Indexed Sections
                </span>
                <span className="px-2 py-0.5 bg-[var(--ok-surface)] text-[var(--ok)] border border-[var(--ok)] rounded-[2px] text-[10px]">
                  FTS5 EMBEDDED
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
