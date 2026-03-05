#!/usr/bin/env python3
"""Unified TPM launcher for Termux/Linux/macOS/Windows and The Forge stage-4 runtime."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEVICE_ROOT = Path.home() / "IrsanAI-TPM"
ROOT = DEVICE_ROOT if DEVICE_ROOT.exists() else REPO_ROOT


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("HOME", "")


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd))
    return p.returncode


def cmd_init_device_root(_: argparse.Namespace) -> int:
    DEVICE_ROOT.mkdir(parents=True, exist_ok=True)
    for rel in ["state", "data", "config", "backups"]:
        (DEVICE_ROOT / rel).mkdir(parents=True, exist_ok=True)
    print(f"Device root initialized: {DEVICE_ROOT}")
    return 0


def cmd_validate(_: argparse.Namespace) -> int:
    return run([sys.executable, "core/tpm_scientific_validation.py"])


def cmd_preflight(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    if args.alpha_vantage_key:
        env["ALPHAVANTAGE_KEY"] = args.alpha_vantage_key

    init_rc = run([sys.executable, "core/init_db_v2.py"], cwd=REPO_ROOT)
    if init_rc != 0:
        return init_rc

    cmd = [sys.executable, "production/preflight_manager.py", "--market", args.market]
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
    return p.returncode


def cmd_live(args: argparse.Namespace) -> int:
    notify = args.notify and is_termux()
    if args.notify and not notify:
        print("[warn] --notify is Termux-only.")
    cmd = [
        sys.executable,
        "production/tpm_live_monitor.py",
        "--history-csv",
        args.history_csv,
        "--poll-seconds",
        str(args.poll_seconds),
    ]
    if notify:
        cmd.extend(["--notify", "--vibrate-ms", str(args.vibrate_ms)])
    return run(cmd)


def cmd_update(args: argparse.Namespace) -> int:
    return run([sys.executable, "scripts/update_orchestrator.py", args.action])


def cmd_cockpit(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "scripts/update_cockpit_server.py", "--port", str(args.port), "--target-port", str(args.target_port)]
    return run(cmd)


def cmd_web(args: argparse.Namespace) -> int:
    return run([sys.executable, "scripts/web_hub_server.py", "--port", str(args.port)])


def cmd_env(_: argparse.Namespace) -> int:
    print("Platform:", platform.platform())
    print("Python:", sys.version.split()[0])
    print("Termux:", "yes" if is_termux() else "no")
    print("Repo root:", REPO_ROOT)
    print("Device root:", DEVICE_ROOT)
    print("Active root:", ROOT)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="IrsanAI TPM unified launcher")
    sp = p.add_subparsers(dest="command", required=True)

    sp.add_parser("env", help="print environment summary").set_defaults(func=cmd_env)
    sp.add_parser("init-device-root", help="prepare ~/IrsanAI-TPM layout").set_defaults(func=cmd_init_device_root)
    sp.add_parser("validate", help="run scientific validation").set_defaults(func=cmd_validate)

    pf = sp.add_parser("preflight", help="run source preflight")
    pf.add_argument("--market", choices=["BTC", "COFFEE", "ALL"], default="ALL")
    pf.add_argument("--alpha-vantage-key", default=os.environ.get("ALPHAVANTAGE_KEY", ""))
    pf.set_defaults(func=cmd_preflight)

    live = sp.add_parser("live", help="run live monitor")
    live.add_argument("--history-csv", default="btc_real_24h.csv")
    live.add_argument("--poll-seconds", type=int, default=3600)
    live.add_argument("--notify", action="store_true")
    live.add_argument("--vibrate-ms", type=int, default=1000)
    live.set_defaults(func=cmd_live)

    web = sp.add_parser("web", help="start unified web hub (playground + oracle + update APIs)")
    web.add_argument("--port", type=int, default=8765)
    web.set_defaults(func=cmd_web)

    upd = sp.add_parser("update", help="check/apply orchestrated app updates")
    upd.add_argument("action", choices=["check", "status", "apply"], default="check")
    upd.set_defaults(func=cmd_update)

    cockpit = sp.add_parser("update-cockpit", help="start update cockpit web UI")
    cockpit.add_argument("--port", type=int, default=8787)
    cockpit.add_argument("--target-port", type=int, default=8765, help="web hub port after handover")
    cockpit.set_defaults(func=cmd_cockpit)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
