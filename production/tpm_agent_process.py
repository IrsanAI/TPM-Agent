#!/usr/bin/env python3
import argparse
import time

from production.preflight_manager import PreflightManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, choices=["BTC", "COFFEE"])
    parser.add_argument("--interval", type=int, default=20)
    args = parser.parse_args()

    pm = PreflightManager()
    print(f"[{args.market}] Agent starting...")

    while True:
        good, results = pm.probe_market(args.market)
        if not good:
            print(f"[{args.market}] No valid source and no cached fallback price available.")
        else:
            best = min(good, key=lambda x: x.get("latency", 9e9))
            print(
                f"[{args.market}] price={best['price']} src={best['source']} "
                f"latency={best['latency']:.0f}ms ok={len(good)}/{len(results)}"
            )
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
