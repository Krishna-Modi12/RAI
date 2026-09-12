"""Generate the synthetic fleet dataset.

    python scripts/generate_data.py
    python scripts/generate_data.py --days 60 --seed 7
    python scripts/generate_data.py --assets WT-017,INV-023
"""

from __future__ import annotations

import argparse
import sys
import time

from rai.config import settings
from rai.sim.generate import generate_fleet, summarise


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic fleet telemetry")
    parser.add_argument("--days", type=int, default=settings.sim_days)
    parser.add_argument("--seed", type=int, default=settings.sim_seed)
    parser.add_argument("--assets", type=str, default=None, help="comma-separated asset ids")
    args = parser.parse_args()

    only = [a.strip() for a in args.assets.split(",")] if args.assets else None

    print(f"Generating {args.days} days for {'all assets' if not only else ', '.join(only)}")
    started = time.perf_counter()
    result = generate_fleet(days=args.days, seed=args.seed, only_assets=only)
    elapsed = time.perf_counter() - started

    print()
    print(summarise(result))
    print()
    print(f"generated in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
