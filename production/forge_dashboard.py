from __future__ import annotations

import json
import time
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


def _source_catalog() -> dict[str, Any]:
    idx = _source_index()
    sources = idx.get("sources", []) if isinstance(idx, dict) else []
    free = [s for s in sources if s.get("registration_type") == "free_no_registration"]
    reg = [s for s in sources if s.get("registration_type") == "registration_required"]
    return {"generated_at": idx.get("generated_at"), "free_no_registration": free, "registration_required": reg}


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
    return {"backtest_summary": True, "engine_transparency": True, "source_resilience": True, "sources_index": True, "predictions": True, "sources_catalog": True, "version": 5}


@app.get("/api/sources/health")
def api_sources_health() -> dict:
    frame = api_frame()
    payload = frame.get("source_resilience", {}) if isinstance(frame, dict) else {}
    return payload if isinstance(payload, dict) else {"agents": {}, "detected_issues": []}


@app.get("/api/sources/index")
def api_sources_index() -> dict:
    return _source_index()


@app.get("/api/predictions/aggregated")
def api_predictions_aggregated() -> dict:
    frame = api_frame()
    signals = frame.get("signals", []) if isinstance(frame, dict) else []
    grouped = {}
    for row in signals:
        market = str(row.get("market", ""))
        val = float(row.get("value", 0.0) or 0.0)
        if market:
            grouped.setdefault(market, []).append(val)
    payload = []
    for market, vals in grouped.items():
        last = vals[-1]
        payload.append({"market": market, "last": last, "slope": 0.0, "forecast": [last]*5, "confidence": 0.5})
    return {"generated_at": int(time.time()), "markets": payload}


@app.get("/api/sources/catalog")
def api_sources_catalog() -> dict:
    return _source_catalog()
