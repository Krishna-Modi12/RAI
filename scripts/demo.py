"""Run a deterministic, judge-facing RAI investigation.

Examples:
    .venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear
    .venv\Scripts\python.exe scripts\demo.py --scenario cloud_transient
    .venv\Scripts\python.exe scripts\demo.py --asset INV-023 --json
"""

from __future__ import annotations

import argparse
import sys

from rai.config import MODELS, SYNTHETIC
from rai.store import telemetry_available


def _scenario_assets() -> dict[str, str]:
    if not SYNTHETIC.joinpath("events.parquet").is_file():
        return {}
    from rai.store import load_events

    return {event.scenario: event.asset_id for event in load_events()}


def _prepare() -> None:
    if not telemetry_available():
        from rai.sim.generate import generate_fleet

        generate_fleet()
    if not (MODELS / "metadata.json").is_file():
        from rai.models.expected import train_all

        train_all()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one reproducible RAI investigation")
    parser.add_argument("--asset", help="asset id, for example WT-017 or INV-023")
    parser.add_argument(
        "--scenario",
        default="gearbox_bearing_wear",
        help="pre-generated scenario to investigate",
    )
    parser.add_argument("--json", action="store_true", help="print the full investigation JSON")
    args = parser.parse_args()

    _prepare()
    asset_id = args.asset or _scenario_assets().get(args.scenario)
    if asset_id is None:
        raise SystemExit(f"scenario {args.scenario!r} is not present in generated ground truth")

    from rai.agent.investigator import investigate

    # None explicitly selects the deterministic path and avoids a model/network probe.
    investigation = investigate(asset_id, force_refresh=None)
    if args.json:
        print(investigation.model_dump_json(indent=2))
        return 0

    verdict = investigation.verdict
    packet = investigation.packet
    print("Renewable Asset Intelligence — deterministic investigation")
    print(f"asset:       {asset_id}")
    print(f"scenario:    {args.scenario}")
    print(f"anomaly:     {packet.anomaly.anomaly_score:.3f}")
    print(f"risk:        {packet.risk.risk_score:.3f} ({packet.risk.risk_band.value})")
    print(f"environment: {packet.environment.verdict.value if packet.environment else 'null'}")
    print(f"peers:       {packet.peers.verdict.value if packet.peers else 'null'}")
    if verdict is not None:
        print(f"diagnosis:   {verdict.likely_cause}")
        print(f"component:   {verdict.component}")
        print(f"confidence:  {verdict.confidence:.3f}")
        print(f"review:      {'yes' if verdict.requires_human_review else 'no'}")
        print(f"action:      {verdict.recommended_action}")
        print(f"model:       {verdict.model_used} (fallback={verdict.fallback_used})")
    print(f"timeline:    {' -> '.join(step.stage for step in investigation.timeline)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
