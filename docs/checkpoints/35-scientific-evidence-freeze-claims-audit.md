---
task: scientific-evidence-freeze-claims-audit
phase: 5
status: complete
---

## What was built

- Corrected the Scientific Evidence Freeze to audit all **18** named RAI capabilities (a
  concurrently-committed draft, `d7a92d1`, covered only 13 and used a different, less
  complete field schema). Rewrote `scripts/generate_scientific_evidence_freeze.py` around a
  capability-centric 10-field schema: `capability, evidence_source, dataset_or_fixture,
  real_or_synthetic, external_or_internal, metric_or_result, artifact,
  what_the_evidence_actually_proves, what_it_does_NOT_prove, final_status`.
- Reclassified **Historical Case Retrieval** from `VALIDATED` to `DEMONSTRATED`: the
  underlying 14-case corpus is real, but its P@1/R@3/MRR retrieval-quality metrics are
  scored against `relevant_case_ids` authored by the RAI team itself, not an independent
  judge — a self-graded evaluation of retrieval mechanics, not an externally validated one.
- Documented that **Dispatch Optimization** and **Weather-Aware Scheduling** are the same
  underlying subsystem (`rai/decision/dispatch_optimizer.py`), not two independently
  evidenced capabilities, and added an explicit "not a certified safety guarantee"
  disclaimer to both registry entries.
- Regenerated all 6 frozen artifacts under `artifacts/evaluation/evidence_freeze/`:
  `evidence_registry.csv`/`.json`, `evidence_matrix.md`, `claim_to_evidence.csv`,
  `unsupported_claims.csv`, `freeze_summary.md`. Final tally: 4 `VALIDATED`,
  9 `DEMONSTRATED`, 4 `ARCHITECTURALLY_SUPPORTED`, 1 `NOT_VALIDATED`.
- Added 2 invariant tests to `tests/test_evidence_freeze_invariants.py` (11 total) guarding
  the frozen registry against silent re-upgrading of any downgraded capability, on top of the
  9 pre-existing invariants (no synthetic→EXTERNAL_REAL, no historical→FIELD_VERIFIED, Gate
  5.6B Validation=[] unchanged, Gate 5.6C non-independence, economics non-realized-savings,
  operational-events non-automatic-failure, closed-loop demo-not-production).
- Ran a background adversarial claims audit (parallel search agents per surface area +
  independent skeptical verifiers) across README.md, CHECKPOINT.md, `docs/evaluation/*`,
  other `docs/*`, `docs/checkpoints/*`, and `web/src/**`. It returned 19 confirmed wording
  downgrades (0 rejected). Applied the ones that were still live on disk after concurrent
  commits (`4e80839`, `4ca5a69`, `0801681`) had already superseded several others by
  independently redesigning the same sections:
  - `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` §19 — "Production Ready" for
    closed-loop ingestion and "Validated" for historical case library both overstated the
    frozen tier; both now read `DEMONSTRATED`-consistent.
  - `docs/PHASE_2_JUDGE_PACKAGE.md` — two VOI figures ("saves ₹65,000+", "expected savings
    ₹18,400") relabeled as modeled/projected, not realized.
  - `docs/checkpoints/29-fleet-exposure-integrity.md` — removed a self-contradictory
    "independently validated Gate 5.6C ... remains incomplete" sentence; now states
    `NOT_INDEPENDENTLY_VALIDATED` directly.
  - `web/src/components/EvidenceAccordion.tsx` — "Avoided Cost" (mislabeled a historical
    case's *repair* cost as an avoided cost) → "Historical Repair Cost"; "Automated Execution
    Allowed" (implied autonomous physical execution, which the system never performs) →
    "Standard Review (No Escalation)".
  - `web/src/app/work-orders/page.tsx` — "continuously enhances ... through human operator
    authorization and technician physical inspection ground truth" (implied live production
    learning) → explicit "demonstrated mechanism ... Shown end-to-end on internal/demo
    fixtures; no live commercial site is connected yet."
  - `web/src/app/layout.tsx` `metadata.description` — "leak-free operational validation"
    (conflated a model-evaluation property with whole-system deployment validation) →
    "leak-free evaluation; decision-support prototype, not a deployed system."
  - `README.md` — Historical Case Retrieval moved out of the VALIDATED tier into
    DEMONSTRATED in the four-tier capability table (this fix landed before the audit
    returned; the audit's own finding independently confirmed it was required).
  - The remaining flagged sentences (README.md's original "Real external validation...two
    independent forms" / "Gate 5.6C ... verified" paragraph, five specific CHECKPOINT.md
    body lines) no longer exist verbatim: concurrent commits `400fb53`/`5ba4c85` had already
    rewritten those sections. Spot-checked the surviving text in both files and it is already
    consistent with the frozen boundaries (e.g. README §"Scientific Evidence Freeze" now
    correctly labels Gate 5.6C `NOT_VALIDATED`/"remains unclosed").

## Files

- `scripts/generate_scientific_evidence_freeze.py` — rewritten, 18-capability schema.
- `artifacts/evaluation/evidence_freeze/{evidence_registry.csv,evidence_registry.json,evidence_matrix.md,claim_to_evidence.csv,unsupported_claims.csv,freeze_summary.md}` — regenerated.
- `tests/test_evidence_freeze_invariants.py` — 2 new invariant tests (11 total).
- `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` — §19 table wording downgrade.
- `docs/PHASE_2_JUDGE_PACKAGE.md` — 2 VOI figures relabeled modeled/projected.
- `docs/checkpoints/29-fleet-exposure-integrity.md` — Limitations wording fix.
- `web/src/components/EvidenceAccordion.tsx` — 2 label fixes.
- `web/src/app/work-orders/page.tsx` — closed-loop description fix.
- `web/src/app/layout.tsx` — metadata description fix.
- `docs/checkpoints/35-scientific-evidence-freeze-claims-audit.md` — this record.

## How it was verified

- `.venv\Scripts\python.exe -m pytest tests/test_evidence_freeze_invariants.py -q` → 11 passed.
- `.venv\Scripts\python.exe -m pytest -q` (full suite) → 554 passed, 30 warnings, 244s.
- `.venv\Scripts\python.exe -m ruff check rai tests services scripts` → All checks passed!
- `npm run build` (in `web/`) → compiled successfully, 0 errors, 10 routes.
- `npm run lint` (in `web/`) → 0 errors, 5 pre-existing unrelated warnings (unused vars in
  `HeroChart.tsx`/`api.ts`, not touched by this task).

## Measured results

18 capabilities audited: 4 VALIDATED, 9 DEMONSTRATED, 4 ARCHITECTURALLY_SUPPORTED,
1 NOT_VALIDATED. 19 claims flagged by the adversarial audit, 19 confirmed real, 8 still
requiring an on-disk wording change at audit time (the other 11 had already been rewritten
by concurrent commits before this task could apply them) — all 8 applied and verified above.

## Limitations

- This session's working tree was shared with at least one other concurrently-running
  Claude Code session under the same git identity (commits `d7a92d1`, `4e80839`, `4ca5a69`,
  `0801681` landed mid-task, including a presentation deck under `docs/presentation/` and a
  public GitHub Pages site under `site/` — both outside this task's scope and not reviewed
  or endorsed by this task record).
- `CHECKPOINT.md` line 5 (hand-maintained header, not regenerated by
  `scripts/update_checkpoint.py`) still said "13 core capabilities" from the superseded
  draft; corrected in the same pass as this record's `update_checkpoint.py` run.
- The claims audit covered README/CHECKPOINT/docs/evaluation/other-docs/checkpoints/web —
  it did not re-scan the newly added `docs/presentation/` or `site/` trees, since those were
  created by out-of-scope concurrent work after the audit was scoped and are not part of
  this task's deliverable.

## Next

None initiated by this task per the user's explicit stop rule ("Do not start UI redesign,
new datasets, or new research after completing the freeze"). Recommend the user review
whether the concurrently-produced presentation deck (`docs/presentation/`) and public site
(`site/`) cite figures consistent with this frozen registry before those are shared
externally.
