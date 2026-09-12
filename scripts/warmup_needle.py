"""Pre-fetch the Needle 2 native library and weights, then smoke-test a tool call.

Run this once on an unrestricted network. Needle downloads from the HuggingFace Hub on first
construction; after this succeeds the model runs fully offline (~14 MB binary, ~28 MB RAM per
session), which is the point of keeping inference local.

    python scripts/warmup_needle.py

If the download is blocked, the system stays fully functional on the deterministic reasoner in
`rai/agent/fallback.py` — this script tells you which path is live rather than failing the build.
"""

from __future__ import annotations

import sys
import time


def main() -> int:
    print("Needle 2 warmup")
    print("-" * 52)

    try:
        import needle
    except ImportError as exc:
        print(f"FAIL  cactus-needle is not installed: {exc}")
        print("      pip install cactus-needle")
        return 1

    print(f"ok    package imported (version {getattr(needle, '__version__', 'unknown')})")

    print("      constructing session (downloads on first run, may take a few minutes)...")
    started = time.perf_counter()
    try:
        needle.Needle(system="warmup")
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).splitlines()[-1] if str(exc) else type(exc).__name__
        print(f"FAIL  session construction failed after {time.perf_counter() - started:.1f}s")
        print(f"      {type(exc).__name__}: {detail[:300]}")
        print()
        print("      Most likely cause: huggingface.co is unreachable from this network.")
        print("      The system remains fully functional using the deterministic reasoner.")
        print("      GET /api/health will report needle_available=false with this reason.")
        return 2
    print(f"ok    session constructed in {time.perf_counter() - started:.1f}s")

    @needle.tool
    def get_asset_risk(asset_id: str):
        "Get the computed failure risk for a renewable asset."
        return {"asset_id": asset_id, "risk": 0.82, "band": "high"}

    print("      running a tool-call smoke test...")
    started = time.perf_counter()
    try:
        agent = needle.Needle(tools=[get_asset_risk], system="You are a maintenance analyst.")
        result = agent.run("What is the failure risk for asset WT-017?", max_new_tokens=128)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN  tool-call smoke test failed: {type(exc).__name__}: {exc}")
        print("      Weights are cached, but the agent loop did not complete.")
        return 3

    elapsed = (time.perf_counter() - started) * 1000
    print(f"ok    tool call completed in {elapsed:.0f} ms")
    print(f"      result keys: {sorted(result)[:8] if isinstance(result, dict) else type(result)}")
    print()
    print("Needle 2 is ready. Restart the API to pick it up:")
    print("  python -m uvicorn services.api.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
