---
task: end-to-end-integration-verification
phase: 5
status: complete
---

## What was built

No new code. A real execution of the full agent pipeline end-to-end (`scripts/demo.py --all`),
prioritized over further benchmark work per the master task's explicit guidance that
integration is higher-value than chasing more benchmark numbers, and as a natural checkpoint
after the backend-contracts audit (checkpoint 20) and the claim-integrity corrections
(checkpoint 21): confirm the whole stack still actually works together, using real computed
values, before continuing further into either more research or the eventual product/demo
readiness phase.

All three demo scenario groups executed successfully with real, non-fabricated numbers at
every stage:

1. **Wind hero investigation (WT-017):** telemetry → residual stack (5 signals, dominant
   `gearbox_oil_temp_c` z=+15.1σ) → environment ruling (unexplained by weather) → peer
   comparison (asset-specific, 100th percentile vs. 8 cohort peers) → historical case retrieval
   (CASE-W-001, 68% similarity) → knowledge RAG citation → economics (₹7,662,567 avoidable
   exposure, 3 costed options) → final verdict (deterministic fallback, CRITICAL risk 82.9%,
   confidence 90%, correctly escalated to human review despite confidence being above the 80%
   threshold, because severity independently triggers escalation).
2. **Solar environmental intelligence (INV-023):** CAMS atmospheric data → dust-storm risk →
   Kimber-RdTools soiling kinetics → an exact additive loss decomposition (soiling + irradiance
   + thermal + curtailment + equipment + unexplained residual sums to the measured deficit,
   160.1 kW vs. 160.0 kW measured) → the cleaning advisor's cost/benefit table. **This run
   directly exercised today's economics fix (checkpoint 20)**: `Wait 72h` shows
   `Cost=INR 462`, which is `UNIT_CLEANING_COST_INR (1850) × (1 - rain_wash_prob 0.75)` —
   confirming the newly-named constant and its `assumptions` plumbing are live in the actual
   demo path, not just covered by unit tests.
3. **Non-fault environmental discrimination:** a solar cloud transient (GHI 920→510 W/m²) is
   correctly attributed 100% to irradiance loss with zero equipment suspicion, and a wind grid
   curtailment directive (measured power matches the SLDC setpoint, bearing/vibration nominal)
   is correctly attributed to curtailment with zero equipment alarm — a direct, live
   demonstration that CLAUDE.md's "an environmental explanation must be ruled out before an
   equipment fault is asserted" rule is real, exercised behavior, not just a written policy.

## Files

None changed. Verification-only task.

## How it was verified

- `.venv/Scripts/python.exe scripts/demo.py --scenario gearbox_bearing_wear` then
  `.venv/Scripts/python.exe scripts/demo.py --all` — both exit 0, full output inspected line
  by line (reproduced above); only warnings were benign sklearn version-mismatch pickle
  warnings, unrelated to correctness.
- Cross-checked the solar cleaning-advisor's printed `Wait 72h` cost (₹462) by hand:
  `1850.0 * (1 - 0.75) = 462.5`, rounds to the displayed `462` — confirms the real code path
  (not a cached/stale value) and that checkpoint 20's `UNIT_CLEANING_COST_INR` fix is correctly
  wired into the live demo output.
- `.venv/Scripts/python.exe -m pytest tests/ -q` → **421 passed** (already re-confirmed
  earlier this iteration after the checkpoint 20/21 changes; unchanged by this task since no
  code was touched).

## Measured results

No new metrics — this task's output is the demo transcript itself (reproduced above), which is
real computed output, not asserted. All eight investigation stages (telemetry, residuals,
environment, peers, history, knowledge, economics, decision) and both fault-suppression tests
produced internally consistent, cross-checkable numbers.

## Limitations

- This confirms the demo/CLI integration path works, not the HTTP API or web frontend paths —
  `services/api/` and `web/` were separately confirmed buildable in checkpoint 21
  (`npm run build`: 8 routes, 0 errors) but not exercised against a live running backend in
  this task.
- `--scenario cloud_transient` exists as a named option but `--all` groups its content into the
  "non-fault" scenario block rather than running it as a separate named block — noted, not a
  defect (the content is exercised either way), not investigated further since it's a
  demo-script presentation detail with no correctness implication.

## Next

With backend intelligence contracts (checkpoint 20), claim/status integrity (checkpoint 21),
and end-to-end integration (this checkpoint) all verified, reassess: either continue
research/backend work if a genuinely unresolved, high-value question remains within the
~4-hour remaining pre-7:00-AM window, or begin light, bounded product/submission-readiness
prep (e.g., confirming `services/api/` starts cleanly and serves the routes the web frontend
expects) without yet starting new frontend UI work, per the master task's deadline rule.
