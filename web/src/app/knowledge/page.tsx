"use client";

import React, { useState, useEffect } from "react";
import { KnowledgeSearchResult, KnowledgeDoc, searchKnowledge, getKnowledgeDocs } from "../../lib/api";
import { Search, FileText } from "lucide-react";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [docsLive, setDocsLive] = useState(false);

  const sampleQueries = [
    "bearing temperature delta SOP",
    "soiling ratio Kimber recovery",
    "inverter MPPT efficiency drop",
    "gearbox oil sampling intervals",
    "wind curtailment grid directive",
  ];

  useEffect(() => {
    async function load() {
      const d = await getKnowledgeDocs();
      setDocs(d.data);
      setDocsLive(d.live);
    }
    load();
  }, []);

  const handleSearch = async (q = query) => {
    if (!q.trim()) return;
    setIsSearching(true);
    const data = await searchKnowledge(q);
    setResults(data.data.results ?? []);
    setIsSearching(false);
  };

  const totalSections = docs.reduce((sum, d) => sum + d.sections, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Domain Knowledge Corpus & Technical SOPs
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Deterministic SQLite FTS5 RAG index spanning {docs.length || "—"} engineering specifications, OEM manuals, and failure catalogs ({totalSections || "—"} sections)
          </p>
        </div>

        <span
          className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase tracking-wider"
          title={docsLive ? "Live from /api/knowledge/docs" : "API unavailable — showing last-known snapshot"}
        >
          {docsLive ? "LIVE" : "CACHED · last-known snapshot"}
        </span>
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
                    {res.doc_id} · {res.score.toFixed(3)}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-[var(--text-tertiary)]">{res.section}</div>
                <blockquote className="text-xs font-sans text-[var(--text-secondary)] leading-relaxed italic border-l-2 border-[var(--accent)] pl-2 whitespace-pre-line">
                  &ldquo;{res.snippet}&rdquo;
                </blockquote>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full Document Corpus Catalog */}
      <div className="bg-[var(--surface-raised)] border border-[var(--border)] rounded-[3px] overflow-hidden">
        <div className="p-4 bg-[var(--surface-inset)] border-b border-[var(--border)] flex justify-between items-center">
          <h2 className="text-xs font-semibold text-[var(--text-primary)]">
            Core Engineering Knowledge Index ({docs.length} Domain Documents)
          </h2>
          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
            SOURCE: GET /api/knowledge/docs
          </span>
        </div>

        <div className="divide-y divide-[var(--border)]">
          {docs.map((doc) => (
            <div
              key={doc.doc_id}
              className="p-3.5 flex items-center justify-between hover:bg-[var(--surface-sunken)] transition-colors text-xs font-mono"
            >
              <div className="flex items-center space-x-3">
                <FileText className="w-4 h-4 text-[var(--accent)] flex-shrink-0" />
                <div>
                  <div className="font-semibold text-[var(--text-primary)] font-sans">
                    {doc.title}
                  </div>
                  <div className="text-[11px] text-[var(--text-tertiary)]">
                    {doc.doc_id} · {doc.kind} · {doc.asset_type}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <span className="text-[11px] text-[var(--text-secondary)]">
                  {doc.sections} sections
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
