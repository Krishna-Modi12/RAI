# Retrieval & Case Corpus Claim Audit

## Audit Standard
Every user-facing statement regarding historical cases, retrieval accuracy, field learning, and provenance was audited against underlying source files. Unsupported or inflated claims were downgraded.

---

## 1. Claim Adjudication Ledger

| Claim Text / Location | Original Phrasing | Underlying Truth | Adjudication / Action |
|---|---|---|---|
| `docs/evaluation/CLOSED_LOOP_INTEGRITY_AUDIT.md` (lines 19, 135) | *"16 real adjudicated cases (10 wind cases from CARE/Kelmarsh, 6 solar cases from PVPMC)"* | The real corpus contains **14** cases (12 wind from CARE/Kelmarsh, 2 solar from NREL PVDAQ). The 6 solar cases in `library.py` are internal synthetic scenarios. | **DOWNGRADED:** Corrected count to 14 audited external cases (12 wind, 2 solar) + 14 synthetic scenario cases. Removed false attribution to PVPMC. |
| `CHECKPOINT.md` (line 5) | *"16 real adjudicated cases across CARE, Kelmarsh, and PVPMC"* | Exactly 14 audited cases across CARE, Kelmarsh, and NREL PVDAQ. Zero cases from PVPMC. | **DOWNGRADED:** Updated to "14 audited real cases across CARE, Kelmarsh, and NREL PVDAQ + 14 synthetic scenario cases". |
| `docs/CLAIMS.md` | *"RAI implements a closed-loop mechanism where technician field feedback is ingested and promoted to retrieval memory"* | Mechanism is fully implemented and browser-verified with Playwright. However, all current tickets are internal test fixtures or demo simulations; zero active commercial field deployments exist. | **CONFIRMED WITH LIMITATIONS:** Explicit boundary preserved: demonstrated on internal synthetic/simulated corpus; empty-state KPI `NO_VERIFIED_CASES_YET` confirmed. |
| General UI / Documentation | *"Field-verified real cases"* | Real cases in retrieval are academic benchmark events from published datasets, not live technician reports from an RAI deployment. | **CLARIFIED:** Replaced ambiguous "field-verified" phrasing with "audited external benchmark cases" when referring to CARE/Kelmarsh/PVDAQ. |
| Retrieval Accuracy Claim | *"Precision@1: 90.0%, Recall@3: 85.0%, MRR: 0.950 with 100% provenance preservation"* | Measured on the deterministic 10-query benchmark `rai.eval.retrieval_eval`. Verified by automated test suites. | **VERIFIED:** Validated mathematically across deterministic test suite. |

---

## 2. Updated Canonical Evidence Inventory

Going forward, the authoritative case counts for RAI are:
- **Total Audited Academic Real Cases:** **14**
  - Wind: **12** (8 CARE to Compare, 4 Kelmarsh Wind Farm)
  - Solar: **2** (NREL PVDAQ OEDI Systems 34 & 1283)
- **Total Internal Synthetic Scenario Cases:** **14**
  - Wind: **8** (`CASE-W-001` through `CASE-W-008`)
  - Solar: **6** (`CASE-S-001` through `CASE-S-006`)
- **Total Live Field Feedback Promoted to `EXTERNAL_REAL`:** **0** (All test/demo tickets quarantined as `INTERNAL_TEST_FIXTURE` or `DEMO_SIMULATION`)
