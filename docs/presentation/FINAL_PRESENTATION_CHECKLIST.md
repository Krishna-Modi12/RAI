# Renewable Asset Intelligence (RAI)
## Final Presentation Checklist: Pre-Flight, Live Demo & Post-Pitch

---

### Phase A: 15 Minutes Before Presentation (Pre-Flight Setup)

- [ ] **Backend Health Check:**
  - Run: `curl http://127.0.0.1:8000/api/health`
  - Verify JSON response: `status: "ok"`, `assets: 42`, `models_loaded: ["wind_expected_power", "solar_expected_power", "risk"]`.
- [ ] **Frontend Dev Server Active:**
  - Open: `http://localhost:3000`
  - Verify initial load displays 42 assets, 90.6% health, and ₹1.21 Cr exposure.
- [ ] **Browser Window Preparation:**
  - Recommended resolution: `1440×900` or `1280×720` (avoid ultra-wide full-screen or mobile emulators during main stage pitch).
  - Zoom level: Exactly 100%.
  - Close unused tabs, notifications, and devtools.
  - Pre-open tabs:
    1. Tab 1: `http://localhost:3000` (Fleet Operations Command)
    2. Tab 2: `http://localhost:3000/assets/WT-004` (Asset Deep Dive)
    3. Tab 3: `http://localhost:3000/work-orders` (Operations Console)
    4. Tab 4: GitHub README or local `README.md`
- [ ] **Local Reasoner & Fallback Verification:**
  - Verify `NEEDLE2` or `FALLBACK` is displayed in top bar; verify response latency is normal.
- [ ] **Backup Screenshots Ready:**
  - Keep folder `artifacts/evaluation/demo_audit/` open in file explorer as an instant backup.

---

### Phase B: During the Presentation (Live Demo Execution)

- [ ] **1. Core Problem & Thesis (0:00–0:30):**
  - Highlight ambiguous generation deficits (bearing vs dust vs weather vs curtailment).
  - State the thesis: *RAI doesn't just alert; it turns ambiguous telemetry into a defensible operational decision.*
- [ ] **2. Fleet Command & Triage (0:30–0:50):**
  - Point to ₹1.21 Cr 30-Day Expected Exposure.
  - Explain how Priority Queue ranks by `Expected Financial Exposure × Risk`.
  - Click `Investigate ↗` on `WT-004`.
- [ ] **3. Physical Signal Residuals (0:50–1:15):**
  - Point to `generator_winding_temp_c` at **+12.3σ** (+13.7°C above expectation).
  - Point to active power dropping at **-8.9σ**.
- [ ] **4. Atmospheric Attribution (1:15–1:35):**
  - Point to CAMS dust aerosol index (0.18, LOW).
  - Point to weather explaining only 24% of power drop.
  - Show verdict: `Equipment Deficit Asserted`.
- [ ] **5. Feeder Peer Cohort Isolation (1:35–2:00):**
  - Show WT-004 compared against 8 identical peers on Feeder 4B.
  - Show WT-004 deviating beyond 88% of cohort (rules out curtailment).
- [ ] **6. Historical Precedent Retrieval (2:00–2:20):**
  - Click `REAL ONLY` filter button.
  - Point to matching Kelmarsh cooling trip (`REAL-KEL-1-FORCED-2550`, 80% similarity).
  - Point out "Why Matched" and "What Differs".
- [ ] **7. Techno-Economic Trade-Off (2:20–2:45):**
  - Compare `Act Now` vs `Defer 3 Days` vs `Defer 14 Days`.
  - Point to `Projected Avoidable Exposure: ₹17.42L` and `Modelled Net Benefit: +₹9.07L`.
  - Emphasize honest wording: *modeled counterfactual, not guaranteed ROI*.
- [ ] **8. Bounded AI & Decision Gating (2:45–3:10):**
  - Point to 72% calibrated confidence (<80% threshold).
  - Point to red `Human Escalation Required` banner.
  - Emphasize: *zero math in LLM; AI cannot actuate physical plant controls*.
- [ ] **9. Work Order Governance (3:10–3:30):**
  - Click `Propose Work Order` to show structured enterprise ticketing.
- [ ] **10. Operations & Safe Dispatch (3:30–4:10):**
  - Navigate to `/work-orders` Operations Console.
  - Click `Crew Dispatch & Weather Windows` tab.
  - Show meteorological safety gates: Kutch 6h safe window vs Charanka 0h rain lockout.
- [ ] **11. Closed-Loop Boundary & Quarantine (4:10–4:35):**
  - Click `Closed-Loop Learning Status` tab.
  - Point out dual-key gate: 14 academic cases protected, 0 field cases promoted, 122 demo tickets quarantined.
- [ ] **12. Closing (4:35–4:45):**
  - Reiterate: *All 554 tests pass offline. Evidence is frozen and boundaries are honest.*

---

### Phase C: Post-Presentation Judge Q&A

- [ ] **Adhere to the 4 Evidence Tiers:**
  - Wind Anomaly & Cross-Farm Transfer: **VALIDATED** (CARE benchmark, normal accuracy > 0.995; PR-AUC 0.822 is a separate internal Gate 2 metric, not CARE).
  - Historical Retrieval: **DEMONSTRATED** (14 audited academic cases; internal retrieval-quality checks, not externally validated).
  - Decision Loop, Economics & Local Agent: **DEMONSTRATED** (Operational prototype).
  - Independent Solar Failure Validation & Live Plant SCADA: **NOT VALIDATED** (Unclosed gate; 0 live commercial feeds).
- [ ] **Defend Against Core Challenges (Refer to `JUDGE_QA.md`):**
  - If asked about LLM hallucinations: *Zero math in LLM; deterministic Python engine.*
  - If asked about commercial deployment: *Explicitly research prototype; zero live utility feeds.*
  - If asked about benchmark leakage: *Strict dual-key quarantine prevents synthetic pollution.*
- [ ] **Never Overclaim:**
  - Do not claim universal hardware RUL failure prediction.
  - Do not claim realized cash savings.
  - Do not claim autonomous plant control.
