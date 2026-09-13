# Renewable Asset Intelligence (RAI)
## Demo Failure Playbook: Real-Time Contingency Procedures

This playbook prepares the presenter for live demonstration glitches, network drops, or latency issues. **Rule #1: Never panic, never bluff, and never fabricate results.** Every failure mode in RAI is backed by an architected graceful degradation or deterministic fallback.

---

### Failure Matrix & Rapid Recovery Actions

| Failure Scenario | Immediate Visual Symptom | Root Cause | Exact Action for Presenter | What to Say to the Judges |
|---|---|---|---|---|
| **1. Local Needle Model is Slow or Unresponsive** | Investigation screen shows loading spinner on Section 7 (>5 seconds). | Quantized local LLM inference queue contention or CPU throttling. | Refresh the page, or click the Section 7 fallback toggle. | *"Notice that our architecture does not stall if local LLM inference slows down; our Python fallback engine immediately computes the exact same structured decision schema deterministically."* |
| **2. Needle Engine Unavailable / Crash** | Banner displays `Engine: FALLBACK (rule_based)`. | Local model weights unmounted or dependency mismatch. | Continue demo normally. Fallback generates identical structured schema. | *"This highlights our core safety invariant: zero core math runs in the LLM. If the local reasoner goes offline, the deterministic Python rule engine takes over seamlessly."* |
| **3. Live Open-Meteo Weather API Fails** | Network timeout on weather cards or dispatch tab. | External internet connectivity drop or Open-Meteo rate limit. | The system automatically serves local cached weather in `artifacts/weather_cache/`. | *"Because utility infrastructure often operates in air-gapped environments, RAI automatically falls back to cached meteorological telemetry with zero interruption."* |
| **4. Weather Cache Also Unavailable** | Weather cards display default / conservative constraints. | Cache directory wiped or permissions restricted. | Point out that dispatch window defaults to safe, restricted limits. | *"When weather data is completely absent, RAI's dispatch optimizer degrades conservatively: it restricts high-risk climbs until atmospheric safety can be verified."* |
| **5. Backend Service (Port 8000) Stops** | Frontend displays red network error toast: `Failed to fetch API`. | Uvicorn process killed or machine slept. | 1. Open background terminal.<br>2. Run: `python -m uvicorn services.api.main:app --port 8000`<br>3. Refresh browser (takes <3s). | *"Let me quickly restart the local FastAPI daemon—it boots in under two seconds because all state is persisted in fast DuckDB/Parquet stores."* |
| **6. Frontend (Port 3000) Dev Server Halts** | Browser displays `This site can't be reached`. | Next.js dev process terminated. | 1. In terminal: `cd web && npm run dev`<br>2. Switch to static screenshots in `artifacts/evaluation/demo_audit/` while booting. | *"While the Next.js dev server reloads, let me show you the identical verified screenshots from our automated Playwright audit in the repository."* |
| **7. Historical Case Retrieval Fails / Empty** | Section 4 shows 0 similar cases. | Filter set to an impossible combination or vector query glitch. | Click the `ALL (14 real + synthetic)` button, then re-click `REAL ONLY`. | *"Our trajectory memory strictly partitions external academic cases from synthetic scenarios to prevent benchmark contamination. Let's inspect the 14 real records."* |
| **8. Work Order Modal Glitch** | Modal fails to close or submit button unresponsive. | Stale browser tab state or duplicate ticket key. | Press `Escape` or navigate directly to `/work-orders` via the left sidebar. | *"The proposal is staged directly into the operational ledger. Let's inspect the live tickets on the Operations Console."* |
| **9. Browser Hard Refresh Loses In-Progress State** | Refreshing `/assets/WT-004` resets temporary modal inputs. | Next.js client state reset on F5. | Click `WT-004` again from Fleet Command or use deep link `/assets/WT-004`. | *"All core telemetry, residuals, and economic models are rendered dynamically from backend state, so navigating straight back to WT-004 restores the full investigation."* |
| **10. Total Network & Process Failure** | Laptop freezes or machine crash. | System-level hardware crash. | Switch directly to the verified screenshots in [`artifacts/evaluation/demo_audit/`](../presentation/SCREENSHOT_GUIDE.md) and [`README.md`](../../README.md). | *"We have captured full-resolution, timestamped screenshots of every step in the operational loop during our automated Playwright audit. Let's walk through the exact verified workflow."* |

---

### Emergency Terminal One-Liners (Keep Handy)

```bash
# Verify backend is alive
curl http://127.0.0.1:8000/api/health

# Restart backend instantly
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000

# Start frontend
cd web && npm run dev

# Open verified screenshot directory
explorer artifacts\evaluation\demo_audit
```
