# Renewable Asset Intelligence (RAI) — Official Static Website Report

The official, public-facing static website for **Renewable Asset Intelligence (RAI)** has been created in `site/` and configured for automated deployment to **GitHub Pages** via `.github/workflows/deploy-pages.yml`.

---

## 1. Architectural Role & Boundary Separation

```
                    RAI Project Architecture
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
     GitHub Pages Static Site              RAI Application
        UNDERSTAND & BELIEVE                    OPERATE
            │                                     │
     - Public Product Narrative           - Live SCADA Telemetry
     - 10-Stage Decision Loop             - Asset Deep Dive (WT-004)
     - 4-Tier Evidence Taxonomy           - Dispatch & Weather Gating
     - 47 Adversarial Stress Gates        - Closed-Loop Field Feedback
     - Zero Backend Required              - Release-Frozen at 4e80839d
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                      GitHub Repository
             https://github.com/Krishna-Modi12/RAI
```

The static website is strictly decoupled from the operational application (`web/`) and backend services (`rai/`, `services/`), which remain release-frozen and untouched.

---

## 2. Design System: Premium Light Industrial Intelligence + Editorial Scientific Software

Guided by **Impeccable** and **Taste** design principles:
- **Surface Palette:** Warm parchment/paper background (`#fbfbfa`, `#f4f4ee`), near-black ink typography (`#121312`), hairline borders (`#e3e3dc`), crisp cards (`#ffffff`).
- **Restrained Accents:** Renewable forest green (`#15803d`), technical cobalt blue (`#1d4ed8`), amber warnings (`#b45309`), red reserved strictly for critical anomalies (`#b91c1c`). Zero purple AI gradients or floating card soup.
- **Typography:** Modern editorial system sans-serif for reading rhythm, paired with precision tabular monospace (`ui-monospace`, `SFMono-Regular`, `Menlo`) for metrics, z-scores, and telemetry.
- **Subtle Industrial Tactility:** Workstation screenshot chassis with active telemetry indicators, hairline dividers, and top-border status highlights on hover.

---

## 3. Implemented Narrative Sections

1. **Header & Navigation:** Persistent sticky header with brand mark, anchor links, GitHub repo CTA, and mobile drawer toggle.
2. **Hero Section:**
   - Headline: *"Turn renewable-asset anomalies into defensible intervention decisions."*
   - Live telemetry status strip: `42 Assets Tracked`, `554/554 Tests Passing`, `47/47 Adversarial Gates Passed`, `14 Real Academic Cases Partitioned`, `Commit: 4e80839d`.
   - Verified screenshot frame displaying Fleet Command Overview (`01_home_fleet_command.png`).
3. **The Problem:** Causal attribution showing why generation deficit $\ne$ equipment failure, supported by a responsive handcrafted SVG diagram.
4. **The Signature 10-Stage Loop:**
   - `SENSE` &rarr; `EXPECT` &rarr; `DETECT` &rarr; `CONTEXTUALIZE` &rarr; `COMPARE` &rarr; `RETRIEVE` &rarr; `QUANTIFY` &rarr; `DECIDE` &rarr; `ACT` &rarr; `LEARN`.
   - Each stage constrained to 1 sentence with explicit subsystem tags.
5. **The Difference:** Traditional SCADA alarm guesswork vs RAI evidence-gated decision intelligence.
6. **Product Walkthrough:** 5 interactive tabs showcasing real verified screenshots from `artifacts/evaluation/demo_audit/`:
   - Tab 1: Fleet Command Console (`01_home_fleet_command.png`)
   - Tab 2: Physics Baseline Residuals & WT-004 Anomaly (`03_asset_section1_residuals.png`)
   - Tab 3: Environmental Context & Peer Feeder Isolation (`04_asset_section2_3_environment_peers.png`)
   - Tab 4: Historical Trajectory Retrieval & Techno-Economics (`06_asset_section6_7_economics_decision.png`)
   - Tab 5: Work Order Lifecycle & Safe-Weather Dispatch (`09_crew_dispatch_weather_windows.png`)
7. **Turbine WT-004 Operational Case Study:** Narrative climax tracking the +12.3&sigma; winding anomaly from detection to weather-safe dispatch.
8. **Technical Architecture Diagram:** Handcrafted SVG showing `NUMERICAL ENGINE &ne; LOCAL AI REASONER` (zero math executed in LLM).
9. **Bounded Local AI & Human Governance:** Air-gapped execution, JSON schema bounding, calibrated confidence gating (&lt;80% triggers human escalation), and zero plant-control write privileges.
10. **Four-Tier Scientific Evidence Matrix:** Filterable table covering all 18 capabilities (`VALIDATED`, `DEMONSTRATED`, `ARCHITECTURALLY SUPPORTED`, `NOT VALIDATED`).
11. **Provenance & Dual-Key Promotion Gate:** Explaining the quarantine boundary (`EXTERNAL_REAL` vs `INTERNAL_SYNTHETIC`).
12. **Adversarial Stress Testing:** Visual scorecard of 47/47 hostile evaluator tests passed across 10 attack vectors.
13. **Explicit Limitations:** Transparent disclosures: zero live commercial utility connections, solar failure validation unclosed, modeled economic cash flows.
14. **Quickstart & Final CTA:** Reproducible 3-minute local setup instructions and GitHub repository links.

---

## 4. Verification & Testing

### Automated Playwright Audit Across 3 Viewports
Ran `python scripts/audit_static_site.py`:
- **Desktop (1440&times;900):** 0 console errors, 0 failed network requests, 0 horizontal scroll overflow (`scrollWidth == clientWidth == 1440`), interactive tabs and filters verified.
- **Laptop (1280&times;720):** 0 console errors, 0 failed requests, 0 horizontal scroll overflow (`scrollWidth == clientWidth == 1280`).
- **Mobile (390&times;844):** 0 console errors, 0 failed requests, 0 horizontal scroll overflow (`scrollWidth == clientWidth == 390`), mobile navigation toggle verified.

### Core System Integrity Check
- **Backend Tests:** 31 sampled tests passed in 14.57s.
- **Python Linting:** `ruff check scripts/audit_static_site.py` &rarr; 0 errors.
- **Frontend Linting:** `npm run lint --prefix web` &rarr; 0 errors, 5 warnings (identical to frozen state).
- **Git Status:** Operational application files remain untouched and release-frozen.
