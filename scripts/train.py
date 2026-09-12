"""Train every model and write artifacts.

    python scripts/train.py

Prints only measured numbers. Anything not evaluated is reported as such rather than
filled in with a plausible-looking value.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Train RAI models")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)-7s %(message)s",
    )

    from rai.models.expected import train_all

    started = time.perf_counter()
    report = train_all()
    elapsed = time.perf_counter() - started

    print()
    print("Expected-behaviour models")
    print("-" * 78)
    print(f"{'model':<24} {'MAE':>10} {'RMSE':>10} {'R2':>8} {'n_train':>9} {'n_test':>9}")
    for key, m in report["models"].items():
        print(
            f"{key:<24} {m['mae']:>10.3f} {m['rmse']:>10.3f} {m['r2']:>8.4f} "
            f"{m['n_train']:>9,} {m['n_test']:>9,}"
        )

    print()
    print("Splits (time-ordered, healthy prefix only)")
    for asset_type, split in report["splits"].items():
        print(f"  {asset_type:<16} train {split['train']}  val {split['validation']}  test {split['test']}")

    print()
    print(f"Residual baselines fitted for {report['baselines']['assets']} assets")

    from rai.models.anomaly import train_isolation_forests
    from rai.models.expected import reset_cache

    reset_cache()
    print()
    print("Supporting detectors")
    print("-" * 78)
    forests = train_isolation_forests()
    print(f"  isolation forests fitted for {forests['assets']} assets")

    from rai.models.risk import train_risk_model

    print()
    print("Risk model (leave-one-asset-out validation)")
    print("-" * 78)
    risk = train_risk_model()
    for key, value in risk.items():
        print(f"  {key:<18} {value}")
    if risk.get("status") != "fitted":
        print("  -> heuristic scorer active; risk is reported as uncalibrated")

    print()
    print(f"trained in {time.perf_counter() - started:.1f}s (models {elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
