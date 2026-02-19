#!/usr/bin/env python3
"""Unified TPM launcher for Termux/Linux/macOS/Windows and The Forge stage-4 runtime."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVICE_ROOT = Path.home() / "IrsanAI-TPM"
ROOT = DEVICE_ROOT if DEVICE_ROOT.exists() else REPO_ROOT


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("HOME", "")




def is_windows() -> bool:
    return platform.system().lower().startswith("win")

def run(cmd: list[str], cwd: Path = REPO_ROOT) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd))
    return p.returncode


def cmd_validate(_: argparse.Namespace) -> int:
    return run([sys.executable, "core/tpm_scientific_validation.py"])


def cmd_preflight(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    if args.alpha_vantage_key:
        env["ALPHAVANTAGE_KEY"] = args.alpha_vantage_key
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


def cmd_forge_run(args: argparse.Namespace) -> int:
    return run([sys.executable, "-m", "production.forge_orchestrator", "--config", args.config, "--ticks", str(args.ticks)])


def cmd_forge_dashboard(args: argparse.Namespace) -> int:
    import importlib.util

    if importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None:
        print("[warn] fastapi/uvicorn not installed; falling back to static playground host.")
        return run([sys.executable, "-m", "http.server", str(args.port)])

    url = f"http://127.0.0.1:{args.port}/"
    if args.open_browser:
        try:
            webbrowser.open(url)
            if is_windows():
                print(f"[windows] opened immersive dashboard: {url}")
        except Exception as exc:
            print(f"[warn] browser auto-open failed: {exc}")

    return run([sys.executable, "-m", "uvicorn", "production.forge_dashboard:app", "--host", "0.0.0.0", "--port", str(args.port)])


def cmd_init_device_root(_: argparse.Namespace) -> int:
    DEVICE_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ["config", "data", "logs", "state"]:
        (DEVICE_ROOT / name).mkdir(parents=True, exist_ok=True)
    print(f"Device root ready at {DEVICE_ROOT}")
    return 0


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

    fr = sp.add_parser("forge-run", help="run stage-4 self-evolution loop")
    fr.add_argument("--config", default="config/config.yaml")
    fr.add_argument("--ticks", type=int, default=1)
    fr.set_defaults(func=cmd_forge_run)

    fd = sp.add_parser("forge-dashboard", help="launch FastAPI + WebSocket PWA dashboard")
    fd.add_argument("--port", type=int, default=8765)
    fd.add_argument("--open-browser", action="store_true", help="Open dashboard automatically (recommended for Windows desktop UX)")
    fd.set_defaults(func=cmd_forge_dashboard)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
