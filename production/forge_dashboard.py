from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from core.forge_config import load_config

app = FastAPI(title="IrsanAI The Forge Dashboard")
CONFIG, PATHS = load_config()
CACHE_FILE = PATHS.state_dir / "latest_prices.json"
HTML_FILE = Path(__file__).resolve().parents[1] / "playground" / "forge_dashboard.html"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.get("/api/frame")
def api_frame() -> dict:
    if not CACHE_FILE.exists():
        return {"signals": [], "transfer_entropy_graph": {}}
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        payload = api_frame()
        await websocket.send_text(json.dumps(payload))
        await websocket.receive_text()
