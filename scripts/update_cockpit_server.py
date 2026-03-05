#!/usr/bin/env python3
"""Minimal installation/update cockpit with live progress API."""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "state" / "update_status.json"

HTML = """<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>IrsanAI Installation Cockpit</title>
<style>
body{font-family:Arial;background:#0d1117;color:#e6edf3;margin:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;max-width:900px}
.bar{height:18px;background:#21262d;border-radius:999px;overflow:hidden;margin:8px 0}
.fill{height:100%;width:0;background:linear-gradient(90deg,#2ea043,#58a6ff)}
.step{font-size:13px;margin:3px 0}
button{padding:10px 14px;border-radius:8px;border:1px solid #30363d;background:#238636;color:#fff;cursor:pointer}
.warn{color:#ffb86b}
</style></head>
<body><div class='card'>
<h2>🛠️ NEW IrsanAI – Update Cockpit</h2>
<p>Orchestrierter Shutdown → Backup → Update → Restore → Restart-Ready</p>
<button onclick='startUpdate()'>Update jetzt starten</button>
<p id='msg' class='warn'>Bereit.</p>
<div class='bar'><div id='fill' class='fill'></div></div>
<div id='pct'>0%</div>
<pre id='meta'></pre>
<div id='steps'></div>
<button onclick='window.location.href="/app"'>IrsanAI - TPM Agenten starten</button>
</div>
<script>
async function fetchStatus(){
  const r=await fetch('/api/status',{cache:'no-store'}); const s=await r.json();
  document.getElementById('fill').style.width=(s.progress_pct||0)+'%';
  document.getElementById('pct').textContent=(s.progress_pct||0)+'%';
  document.getElementById('msg').textContent=s.message||'';
  document.getElementById('meta').textContent=JSON.stringify({phase:s.phase,update_available:s.update_available,local_head:s.local_head,remote_head:s.remote_head,backup_dir:s.backup_dir},null,2);
  const steps=(s.steps||[]).slice(-12).map(x=>`<div class='step'>${x.ts} • ${x.step} • ${x.status} • ${x.detail||''}</div>`).join('');
  document.getElementById('steps').innerHTML=steps;
}
async function startUpdate(){ await fetch('/api/start',{method:'POST'}); }
setInterval(fetchStatus,1000); fetchStatus();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, code: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_status(self) -> dict:
        if STATUS_FILE.exists():
            try:
                return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"phase": "idle", "progress_pct": 0, "message": "idle", "steps": []}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self._json(self._read_status())
            return
        if path == "/app":
            html = "<html><body><p>Beende jetzt den Cockpit-Port und starte die Hauptanwendung auf dem Ziel-Port.</p></body></html>"
            raw = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        raw = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/start":
            def _run():
                subprocess.run(["python", "scripts/update_orchestrator.py", "apply"], cwd=str(ROOT), check=False)

            threading.Thread(target=_run, daemon=True).start()
            self._json({"ok": True, "message": "update started"})
            return
        self._json({"ok": False, "error": "not found"}, 404)


def main() -> int:
    parser = argparse.ArgumentParser(description="IrsanAI Update Cockpit server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Update cockpit listening on http://0.0.0.0:{args.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
