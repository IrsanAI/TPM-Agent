#!/usr/bin/env python3
"""Unified IrsanAI web hub server.

Serves the playground UI and exposes JSON endpoints for:
- prediction oracle snapshot
- update status/start
- platform capability report (Docker/Termux)
- health/readiness checks for ops
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prediction_oracle import PredictionOracle
STATE = ROOT / "state"
SNAPSHOT_MAX_AGE_SEC = int(os.environ.get("WEB_HUB_SNAPSHOT_MAX_AGE_SEC", "21600"))
ORACLE = PredictionOracle()


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

    def _error(self, error_code: str, error_detail: str, code: int = 400) -> None:
        self._json({"ok": False, "error_code": error_code, "error_detail": error_detail}, code=code)

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
        system = platform.system().lower()
        return {
            "platform": "termux" if is_termux else ("docker" if is_docker else system),
            "termux": is_termux,
            "docker": is_docker,
            "linux": system == "linux",
            "macos": system == "darwin",
            "update_actions": True,
            "oracle_snapshot": (STATE / "prediction_hub_latest.json").exists(),
            "update_status": (STATE / "update_status.json").exists(),
        }

    def _health(self) -> dict:
        return {
            "ok": True,
            "service": "web_hub",
            "ts": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        }

    def _probe_state_write(self) -> tuple[bool, str]:
        STATE.mkdir(parents=True, exist_ok=True)
        probe = STATE / ".ready_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True, "state writable"
        except Exception as exc:
            return False, f"state write probe failed: {exc}"

    def _snapshot_freshness(self) -> tuple[bool, str]:
        snap_file = STATE / "prediction_hub_latest.json"
        if not snap_file.exists():
            return True, "snapshot missing (allowed before first prediction)"
        try:
            payload = json.loads(snap_file.read_text(encoding="utf-8"))
            snap_ts = payload.get("snapshot_utc")
            if not snap_ts:
                return False, "snapshot missing snapshot_utc"
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(snap_ts)).total_seconds()
            if age > SNAPSHOT_MAX_AGE_SEC:
                return False, f"snapshot stale: age={int(age)}s > {SNAPSHOT_MAX_AGE_SEC}s"
            return True, f"snapshot fresh: age={int(age)}s"
        except Exception as exc:
            return False, f"snapshot parse failed: {exc}"

    def _ready(self) -> tuple[dict, int]:
        required_dirs = [ROOT / "playground", ROOT / "scripts", ROOT / "state"]
        missing = [str(p.relative_to(ROOT)) for p in required_dirs if not p.exists()]
        if missing:
            return (
                {
                    "ok": False,
                    "error_code": "READINESS_MISSING_PATHS",
                    "error_detail": "required paths missing",
                    "missing": missing,
                },
                503,
            )

        write_ok, write_detail = self._probe_state_write()
        if not write_ok:
            return (
                {
                    "ok": False,
                    "error_code": "READINESS_STATE_UNWRITABLE",
                    "error_detail": write_detail,
                },
                503,
            )

        snap_ok, snap_detail = self._snapshot_freshness()
        if not snap_ok:
            return (
                {
                    "ok": False,
                    "error_code": "READINESS_STALE_SNAPSHOT",
                    "error_detail": snap_detail,
                },
                503,
            )

        return (
            {
                "ok": True,
                "service": "web_hub",
                "ready": True,
                "checks": {
                    "state_write": write_detail,
                    "snapshot": snap_detail,
                },
            },
            200,
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.path = "/playground/index.html"
            return super().do_GET()
        if path == "/api/health":
            return self._json(self._health())
        if path == "/api/ready":
            body, code = self._ready()
            return self._json(body, code=code)
        if path == "/api/capabilities":
            return self._json(self._capabilities())
        if path == "/api/update/status":
            return self._json(self._read_json("state/update_status.json", {"phase": "idle", "progress_pct": 0, "message": "idle", "steps": []}))
        if path == "/api/oracle":
            q = parse_qs(parsed.query)
            snap = self._read_json("state/prediction_hub_latest.json", {"available": False})
            if "available" not in snap:
                snap["available"] = True
            if not snap.get("available", False):
                snap.setdefault("error_code", "ORACLE_SNAPSHOT_MISSING")
                snap.setdefault("error_detail", "No oracle snapshot found yet")
            if q.get("device_ts"):
                try:
                    device_ts = datetime.fromisoformat(q["device_ts"][0])
                    if snap.get("snapshot_utc"):
                        server_ts = datetime.fromisoformat(snap["snapshot_utc"])
                        snap["device_clock_delta_seconds"] = (device_ts - server_ts).total_seconds()
                except Exception:
                    return self._error("INVALID_DEVICE_TS", "Query parameter device_ts must be ISO-8601", 400)
            return self._json(snap)
        if path == "/api/replay/recent":
            q = parse_qs(parsed.query)
            market = q.get("market", [None])[0]
            limit = int(q.get("limit", [10])[0])
            return self._json({"ok": True, "items": ORACLE.recent_replays(market=market, limit=limit)})
        if path == "/api/replay":
            q = parse_qs(parsed.query)
            pid = q.get("prediction_id", [""])[0].strip()
            if not pid:
                return self._error("MISSING_PREDICTION_ID", "Query parameter prediction_id is required", 400)
            item = ORACLE.replay(pid)
            if not item:
                return self._error("REPLAY_NOT_FOUND", f"No replay found for prediction_id={pid}", 404)
            return self._json({"ok": True, "item": item})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/update/start":

            def _run():
                subprocess.run(["python3", "scripts/update_orchestrator.py", "apply"], cwd=str(ROOT), check=False)

            threading.Thread(target=_run, daemon=True).start()
            return self._json({"ok": True, "message": "update started"})
        return self._error("NOT_FOUND", f"Endpoint not found: {path}", 404)


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
