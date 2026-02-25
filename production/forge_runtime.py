from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return value.encode("utf-8", "replace").decode("utf-8")
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.forge_config import load_config
from production.forge_orchestrator import ForgeOrchestrator


class AgentSpec(BaseModel):
    name: str = Field(..., description="Unique agent name")
    domain: str = Field(..., description="Domain, e.g. finance")
    market: str = Field(..., description="Market identifier, e.g. BTC")
    source_type: str = Field(..., description="Supported: kraken, binance, open_meteo, alphavantage_commodity")
    url: str
    weight: float = 1.0


class ForgeRuntime:
    def __init__(self, config_path: Path | None = None):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._config_path = config_path or (Path(__file__).resolve().parents[1] / "config" / "config.yaml")
        self.base_config, self.paths = load_config(self._config_path)
        self.override_agents_file = self.paths.state_dir / "user_agents.json"
        self.runtime_config_file = self.paths.state_dir / "runtime_config.json"
        self.orchestrator = self._build_orchestrator()
        self.latest_frame: dict[str, Any] = {
            "signals": [],
            "domain_summary": {},
            "transfer_entropy_graph": {},
            "runtime": self.base_config.get("runtime", {}),
        }
        self._worker: threading.Thread | None = None

    def _load_override_agents(self) -> list[dict]:
        if not self.override_agents_file.exists():
            return []
        payload = json.loads(self.override_agents_file.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []

    def _merged_config(self) -> dict:
        merged = dict(self.base_config)
        agents = list(self.base_config.get("agents", []))
        agents.extend(self._load_override_agents())
        merged["agents"] = agents
        return merged

    def _build_orchestrator(self) -> ForgeOrchestrator:
        merged = self._merged_config()
        self.runtime_config_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        return ForgeOrchestrator(self.runtime_config_file)

    def list_agents(self) -> list[dict]:
        return self._merged_config().get("agents", [])

    def add_agent(self, spec: AgentSpec) -> None:
        with self._lock:
            agents = self.list_agents()
            if any(item["name"] == spec.name for item in agents):
                raise HTTPException(status_code=409, detail=f"Agent '{spec.name}' already exists")
            override = self._load_override_agents()
            override.append(spec.model_dump())
            self.override_agents_file.write_text(json.dumps(override, indent=2), encoding="utf-8")
            self.orchestrator = self._build_orchestrator()

    def run_tick(self) -> dict:
        with self._lock:
            self.latest_frame = self.orchestrator.tick()
            self.latest_frame["agent_count"] = len(self.list_agents())
            return self.latest_frame

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                frame = self.run_tick()
                interval = int(self.orchestrator.config["engine"]["interval_seconds"])
            except Exception as exc:  # runtime guard for long-running service
                frame = {"error": str(exc), "ts": int(time.time()), "signals": []}
                self.latest_frame = frame
                interval = 5
            self._stop_event.wait(max(1, interval))

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=2)


app = FastAPI(title="IrsanAI TPM Forge Runtime")
runtime = ForgeRuntime()
HTML_FILE = Path(__file__).resolve().parents[1] / "playground" / "forge_dashboard.html"


@app.on_event("startup")
def _startup() -> None:
    runtime.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    runtime.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.get("/api/frame")
def api_frame() -> dict:
    return _sanitize(runtime.latest_frame)


@app.post("/api/tick")
def api_tick() -> dict:
    return _sanitize(runtime.run_tick())


@app.get("/api/agents")
def api_agents() -> dict:
    return {"agents": runtime.list_agents()}


@app.post("/api/agents")
def api_add_agent(spec: AgentSpec) -> dict:
    runtime.add_agent(spec)
    return {"ok": True, "agent_count": len(runtime.list_agents())}


@app.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        await websocket.send_text(json.dumps(runtime.latest_frame))
        await websocket.receive_text()
