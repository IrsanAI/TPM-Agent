#!/usr/bin/env python3
"""Unified IrsanAI web hub server.

Serves the playground UI and exposes JSON endpoints for:
- prediction oracle snapshot
- update status/start
- platform capability report (Docker/Termux)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT / "playground"
STATE = ROOT / "state"


class HubHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload: dict, code: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self, rel: str, default: dict) -> dict:
        fp = ROOT / rel
        if fp.exists():
            try:
                return json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                return default
        return default

    def _capabilities(self) -> dict:
        is_termux = "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("HOME", "")
        is_docker = Path("/.dockerenv").exists() or os.environ.get("IRSANAI_DOCKER", "") == "1"
        return {
            "termux": is_termux,
            "docker": is_docker,
            "update_actions": True,
            "oracle_snapshot": (STATE / "prediction_hub_latest.json").exists(),
            "update_status": (STATE / "update_status.json").exists(),
        }

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/playground/index.html"
            return super().do_GET()
        if path == "/api/capabilities":
            return self._json(self._capabilities())
        if path == "/api/update/status":
            return self._json(self._read_json("state/update_status.json", {"phase": "idle", "progress_pct": 0, "message": "idle", "steps": []}))
        if path == "/api/oracle":
            snap = self._read_json("state/prediction_hub_latest.json", {"available": False})
            if "available" not in snap:
                snap["available"] = True
            return self._json(snap)
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/update/start":
            def _run():
                subprocess.run(["python", "scripts/update_orchestrator.py", "apply"], cwd=str(ROOT), check=False)

            threading.Thread(target=_run, daemon=True).start()
            return self._json({"ok": True, "message": "update started"})
        return self._json({"ok": False, "error": "not found"}, 404)


def main() -> int:
    parser = argparse.ArgumentParser(description="IrsanAI unified web hub")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), HubHandler)
    print(f"IrsanAI Web Hub listening on http://0.0.0.0:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
