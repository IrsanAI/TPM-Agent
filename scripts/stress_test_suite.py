#!/usr/bin/env python3
"""Failover stress test for PreflightManager.

Simulates AlphaVantage outage and checks fallback latency/serviceability.
Goal threshold: p95 < 1000ms.
"""

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.preflight_manager import PreflightManager, Source


def percentile(values, p):
    if not values:
        return 0.0
    vals = sorted(values)
    idx = (len(vals) - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(vals) - 1)
    frac = idx - lo
    return vals[lo] + (vals[hi] - vals[lo]) * frac


def run(iterations: int = 30):
    # Force COFFEE first source to an invalid endpoint to simulate AV outage.
    pm = PreflightManager()
    pool = list(pm.pool_map["COFFEE"])
    pool.insert(0, Source("alpha_vantage_sim_down", "alpha_vantage_global_quote", "https://127.0.0.1:1/av_down"))
    pm.pool_map["COFFEE"] = pool

    latencies = []
    usable_count = 0
    statuses = {}

    for _ in range(iterations):
        t0 = time.time()
        good, results = pm.probe_market("COFFEE")
        elapsed = (time.time() - t0) * 1000
        latencies.append(elapsed)
        if good:
            usable_count += 1
        for r in results:
            statuses[r.get("status", "UNKNOWN")] = statuses.get(r.get("status", "UNKNOWN"), 0) + 1

    report = {
        "iterations": iterations,
        "usable_rate": usable_count / iterations,
        "latency_ms": {
            "mean": statistics.mean(latencies),
            "p95": percentile(latencies, 95),
            "max": max(latencies),
        },
        "status_counts": statuses,
        "goal_p95_lt_1000ms": percentile(latencies, 95) < 1000,
    }

    out = Path("state/stress_test_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
