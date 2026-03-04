#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = REPO_ROOT / "state" / "install_status.json"
HTML_FILE = REPO_ROOT / "playground" / "install_dashboard.html"

app = FastAPI(title="IrsanAI TPM Install Cockpit")


def _default_status() -> dict:
    return {
        "phase": "idle",
        "progress_pct": 0,
        "module": "n/a",
        "note": "No install session started yet.",
        "ts": int(time.time()),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/api/install/status")
def status() -> dict:
    if not STATUS_FILE.exists():
        return _default_status()
    try:
        payload = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return _default_status()


def write_snapshot() -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(_default_status(), indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()

    if args.snapshot:
        write_snapshot()
        return 0

    uvicorn.run(app, host="0.0.0.0", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
