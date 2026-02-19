#!/usr/bin/env python3
"""Unified TPM launcher for Termux/Linux/macOS/Windows.

Examples:
  python scripts/tpm_cli.py validate
  python scripts/tpm_cli.py preflight --market COFFEE
  python scripts/tpm_cli.py live --history-csv btc_real_24h.csv --notify
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("HOME", "")


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT))
    return p.returncode


def cmd_validate(_: argparse.Namespace) -> int:
    return run([sys.executable, "core/tpm_scientific_validation.py"])


def cmd_preflight(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    if args.alpha_vantage_key:
        env["ALPHAVANTAGE_KEY"] = args.alpha_vantage_key
    cmd = [sys.executable, "production/preflight_manager.py", "--market", args.market]
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return p.returncode


def cmd_live(args: argparse.Namespace) -> int:
    notify = args.notify
    if notify and not is_termux():
        print("[warn] --notify uses termux-toast/termux-vibrate and is only available in Termux.")
        notify = False

    cmd = [
        sys.executable,
        "production/tpm_live_monitor.py",
        "--history-csv",
        args.history_csv,
        "--poll-seconds",
        str(args.poll_seconds),
        "--interval-min",
        str(args.interval_min),
        "--window-size",
        str(args.window_size),
        "--percentile",
        str(args.percentile),
        "--safety-floor",
        str(args.safety_floor),
        "--min-alpha-delta",
        str(args.min_alpha_delta),
        "--cooldown",
        str(args.cooldown),
    ]
    if notify:
        cmd.extend(["--notify", "--vibrate-ms", str(args.vibrate_ms)])
    return run(cmd)


def cmd_env(_: argparse.Namespace) -> int:
    print("Platform:", platform.platform())
    print("Python:", sys.version.split()[0])
    print("Termux:", "yes" if is_termux() else "no")
    print("Repo:", ROOT)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="IrsanAI TPM unified launcher")
    sp = p.add_subparsers(dest="command", required=True)

    env = sp.add_parser("env", help="print environment summary")
    env.set_defaults(func=cmd_env)

    v = sp.add_parser("validate", help="run scientific validation")
    v.set_defaults(func=cmd_validate)

    pf = sp.add_parser("preflight", help="run source preflight")
    pf.add_argument("--market", choices=["BTC", "COFFEE"], default="BTC")
    pf.add_argument("--alpha-vantage-key", default=os.environ.get("ALPHAVANTAGE_KEY", ""))
    pf.set_defaults(func=cmd_preflight)

    live = sp.add_parser("live", help="run live monitor")
    live.add_argument("--history-csv", default="btc_real_24h.csv")
    live.add_argument("--poll-seconds", type=int, default=3600)
    live.add_argument("--interval-min", type=int, default=60)
    live.add_argument("--window-size", type=int, default=30)
    live.add_argument("--percentile", type=float, default=95.0)
    live.add_argument("--safety-floor", type=float, default=0.40)
    live.add_argument("--min-alpha-delta", type=float, default=0.005)
    live.add_argument("--cooldown", type=int, default=8)
    live.add_argument("--notify", action="store_true")
    live.add_argument("--vibrate-ms", type=int, default=1000)
    live.set_defaults(func=cmd_live)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
