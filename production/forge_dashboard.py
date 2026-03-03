from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from core.forge_config import load_config

app = FastAPI(title="IrsanAI The Forge Dashboard")
CONFIG, PATHS = load_config()
CACHE_FILE = PATHS.state_dir / "latest_prices.json"
BACKTEST_FILE = PATHS.state_dir / "TPM_test_results.json"
SOURCE_INDEX_FILE = PATHS.state_dir / "source_index.json"
HTML_FILE = Path(__file__).resolve().parents[1] / "playground" / "forge_dashboard.html"


def _source_index() -> dict[str, Any]:
    if not SOURCE_INDEX_FILE.exists():
        return {"generated_at": None, "total_sources": 0, "healthy_sources": 0, "sources": []}
    try:
        payload = json.loads(SOURCE_INDEX_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {"generated_at": None, "total_sources": 0, "healthy_sources": 0, "sources": []}


def _backtest_summary() -> dict[str, Any]:
    if not BACKTEST_FILE.exists():
        return {"available": False, "reason": "validation report not found"}
    try:
        payload = json.loads(BACKTEST_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "reason": f"invalid report: {exc}"}
    tests = payload.get("tests", []) if isinstance(payload, dict) else []
    compact = []
    for t in tests:
        if isinstance(t, dict):
            compact.append({
                "name": t.get("name", "unknown"),
                "metric": t.get("metric"),
                "passed": bool(t.get("passed")),
                "p_value": t.get("p_value"),
            })
    return {"available": True, "generated_at_utc": payload.get("generated_at_utc"), "tests": compact}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/api/frame")
def api_frame() -> dict:
    if not CACHE_FILE.exists():
        return {
            "signals": [],
            "domain_summary": {},
            "ui_profile": CONFIG.get("ui", {}),
            "transfer_entropy_graph": {},
            "runtime": CONFIG.get("runtime", {}),
        }
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        payload = api_frame()
        await websocket.send_text(json.dumps(payload))
        await websocket.receive_text()


@app.get("/api/backtest/summary")
def api_backtest_summary() -> dict:
    return _backtest_summary()


@app.get("/api/capabilities")
def api_capabilities() -> dict:
    return {"backtest_summary": True, "engine_transparency": True, "source_resilience": True, "sources_index": True, "version": 3}


@app.get("/api/sources/health")
def api_sources_health() -> dict:
    frame = api_frame()
    payload = frame.get("source_resilience", {}) if isinstance(frame, dict) else {}
    return payload if isinstance(payload, dict) else {"agents": {}, "detected_issues": []}


@app.get("/api/sources/index")
def api_sources_index() -> dict:
    return _source_index()
