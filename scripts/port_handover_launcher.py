#!/usr/bin/env python3
"""Launch web hub after cockpit shutdown and optional delay."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--wait-for-free-port", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args()

    deadline = time.time() + args.timeout
    while args.wait_for_free_port and time.time() < deadline and port_open(args.wait_for_free_port):
        time.sleep(0.25)

    subprocess.Popen(
        [sys.executable, "scripts/web_hub_server.py", "--port", str(args.port)],
        cwd=str(ROOT),
        start_new_session=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
