---
task: concurrent-investigate-crash-fix
phase: 5
status: complete
---

## What was built

Root-caused and fixed the API process crash checkpoint 27 reported ("the FastAPI/uvicorn
process segfaulted three times during this task's browser-verification loop... outside this
task's `web/`-scoped surface, worked around by restarting rather than debugged"). This was a
concrete, evidence-backed backend task, not speculative work: the concurrent agent's own
checkpoint explicitly named it as the top follow-up item.

**Reproduction.** Started a local uvicorn instance and fired concurrent requests at every
endpoint the concurrent agent's browser session had exercised. Isolated the trigger to
`POST /api/assets/{id}/investigate`: 20 simultaneous investigate requests killed the process
(only 3/20 completed, the rest got connection-refused, and the process was gone from the
process list afterward -- not merely hung). A more realistic load -- 4 concurrent requests,
matching a single browser page with React effects firing twice -- succeeded on the first wave
but killed the process on the second wave, every time. This is a demo-relevant severity, not
just a synthetic stress-test edge case.

**Two independent root causes found, both unsynchronized lazy-singleton races:**

1. `rai/models/risk.py: get_model()` and `rai/models/anomaly.py: _isolation_score()`'s
   `_iforest_cache` both used an unguarded `if _cached is None: _cached = load()` pattern.
   Concurrent requests raced past the check before the first finished loading, so each
   independently unpickled the same scaler/classifier/calibrator/isolation-forest bundle from
   disk at once (confirmed by the `InconsistentVersionWarning` sklearn log line repeating many
   times per burst instead of once). Fixed with a double-checked lock
   (`threading.Lock()`) in both places. This eliminated the duplicate loads (confirmed: the
   warning now appears exactly once per model per process) but did not by itself stop the
   crash -- a second, more serious cause remained.
2. **The actual crash trigger:** `rai/agent/investigator.py: _get_runtime()` constructs one
   `NeedleRuntime` singleton per process, wrapping a single native `needle.Needle` inference
   session (`cactus-needle`, a 45M-parameter tool-calling model) in `self._agent`. Every
   concurrent `/investigate` call was invoking `self._agent.run(...)` /
   `self._needle.extract(...)` on that *same shared native session object* from different
   threads simultaneously (FastAPI runs sync routes in a thread pool) with no synchronization.
   Concurrent invocation of a single native inference session is not something the library
   documents as safe, and it reliably corrupted state badly enough to kill the process. Fixed
   by adding a `threading.Lock()` to `NeedleRuntime` and holding it for the duration of both
   `run_investigation()` and `extract_verdict()` -- one investigation uses the native session
   at a time; concurrent requests queue briefly instead of racing on shared native state.

## Files

- `rai/models/risk.py` -- double-checked lock around the cached risk-model singleton.
- `rai/models/anomaly.py` -- double-checked lock around the per-asset isolation-forest cache.
- `rai/agent/runtime.py` -- `threading.Lock()` added to `NeedleRuntime`, held across
  `run_investigation()` and `extract_verdict()`.

## How it was verified

- `.venv/Scripts/python.exe -m pytest tests/ -q` -> **421 passed**, 24 warnings, unchanged --
  the fix is concurrency-safety hardening only, no behavioural change on the single-request
  path.
- `ruff check rai/models/risk.py rai/models/anomaly.py` -> clean.
- Before the fix: 4 concurrent `POST /investigate` requests, repeated once, crashed the process
  on the second wave (0/4 completed, port no longer listening, process gone from the process
  list) -- reproduced twice, consistently.
- After the fix: the same 4-concurrent x 5-round sequence completed cleanly, 20/20 `200 OK`,
  server still healthy afterward. The harsher 20-simultaneous-request burst (the original
  reproduction, which killed the process after only 3/20 completed) was also re-run against the
  fixed code: **20/20 `200 OK`**, and the health check immediately after also returned `200` --
  full recovery, not merely "didn't crash."

## Measured results

Not a modeling change -- no metric moved. This is a reliability fix: before, P(process survives
a 4-concurrent investigate burst repeated twice) was effectively 0 (crashed both trials); after,
it survived 5/5 repeats in the same test.

## Limitations

- The lock makes concurrent investigations correct but serial through the native session --
  under sustained heavy concurrent load, requests queue rather than crash, which is the correct
  trade-off for a single-operator demo app but would not scale a production multi-tenant
  deployment. Out of scope for this fix.
- `_get_runtime()` in `rai/agent/investigator.py` still has a narrow, lower-severity race: it
  sets `_runtime_tried = True` before `NeedleRuntime(...)` finishes constructing, so a
  concurrent request arriving during that first construction can see `_runtime_tried=True` but
  `_runtime` still `None` and permanently fall back to the deterministic reasoner for that
  request, even though the real runtime becomes available moments later. This does not crash
  the process (the fallback path is safe) and was not fixed here to keep this change minimal
  and reviewable this close to the submission deadline -- flagged as the next task.
- Root cause was diagnosed by reproduction and elimination (removing the duplicate-load
  warnings, then testing whether serializing native-session access stopped the crash), not by
  reading a native stack trace -- no Windows Application Error / WER event was found in the
  Application event log for the crash window, so the exact native failure mode (access
  violation vs. an abort from the native library's own concurrency guard) is not confirmed,
  only that concurrent access is necessary and sufficient to trigger it and serializing access
  is necessary and sufficient to prevent it in every trial run.

## Next

The `_get_runtime()` TOCTOU race noted above is the natural follow-up if more time remains
before submission. Otherwise, the backend's demo-relevant stability gap the concurrent agent
flagged is closed: `/investigate` no longer crashes under realistic concurrent browser load.
