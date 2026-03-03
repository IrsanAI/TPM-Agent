from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.forge_config import load_config
from production.forge_orchestrator import ForgeOrchestrator


SUGGESTED_MARKETS: dict[str, list[dict[str, str]]] = {
    "binance": [
        {"market": "BTC", "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"},
        {"market": "ETH", "url": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"},
        {"market": "SOL", "url": "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"},
    ],
    "kraken": [
        {"market": "BTC", "url": "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"},
        {"market": "ETH", "url": "https://api.kraken.com/0/public/OHLC?pair=ETHUSD&interval=60"},
    ],
    "alphavantage_commodity": [
        {"market": "COFFEE", "url": "https://www.alphavantage.co/query?function=COFFEE&interval=monthly&apikey={API_KEY}"},
        {"market": "WTI", "url": "https://www.alphavantage.co/query?function=WTI&interval=monthly&apikey={API_KEY}"},
    ],
}

REQUIRES_API_KEY = {"alphavantage_commodity"}

LOCALE_LABELS = {
    "en": "English",
    "de": "Deutsch",
    "bs": "Bosanski",
    "es": "Español",
    "fr": "Français",
    "hi": "हिन्दी",
    "it": "Italiano",
    "ja": "日本語",
    "pt-BR": "Português (Brasil)",
    "ru": "Русский",
    "tr": "Türkçe",
    "zh-CN": "中文（简体）",
}


def _discover_locales() -> list[dict[str, str]]:
    repo_root = Path(__file__).resolve().parents[1]
    i18n_dir = repo_root / "docs" / "i18n"
    locales: list[dict[str, str]] = [{
        "code": "en",
        "label": LOCALE_LABELS.get("en", "English"),
        "doc_path": "README.md",
    }, {
        "code": "de",
        "label": LOCALE_LABELS.get("de", "Deutsch"),
        "doc_path": "README.de.md",
    }]
    if i18n_dir.exists():
        for file in sorted(i18n_dir.glob("README.*.md")):
            match = re.match(r"README\.(.+)\.md$", file.name)
            if not match:
                continue
            code = match.group(1)
            locales.append({
                "code": code,
                "label": LOCALE_LABELS.get(code, code),
                "doc_path": f"docs/i18n/{file.name}",
            })

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in locales:
        code = item["code"]
        if code in seen:
            continue
        seen.add(code)
        deduped.append(item)
    return deduped


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return value.encode("utf-8", "replace").decode("utf-8")
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


class AgentSpec(BaseModel):
    name: str = Field(..., description="Unique agent name")
    domain: str = Field(..., description="Domain, e.g. finance")
    market: str = Field(..., description="Market identifier, e.g. BTC")
    source_type: str = Field(..., description="Supported: kraken, binance, open_meteo, alphavantage_commodity")
    url: str
    weight: float = 1.0
    api_key: str | None = Field(default=None, description="Optional API key for protected/external sources")


class ForgeRuntime:
    def __init__(self, config_path: Path | None = None):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._engine_enabled = True
        self._transition: dict[str, Any] | None = None
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

    def market_suggestions(self) -> dict:
        active_markets = sorted({a.get("market", "") for a in self.list_agents() if a.get("market")})
        observed_markets = sorted({s.get("market", "") for s in self.latest_frame.get("signals", []) if s.get("market")})
        return {
            "suggested_by_source": SUGGESTED_MARKETS,
            "active_markets": active_markets,
            "observed_markets": observed_markets,
            "requires_api_key": sorted(REQUIRES_API_KEY),
        }

    def locales(self) -> dict:
        return {"locales": _discover_locales()}

    def runtime_status(self) -> dict:
        transition = self._transition
        progress = 100
        state = "running" if self._engine_enabled else "stopped"
        action = "idle"
        if transition:
            elapsed = time.time() - transition["started_at"]
            pct = int(min(100, max(0, (elapsed / transition["duration_s"]) * 100)))
            progress = pct
            action = transition["action"]
            state = "running" if transition["target_enabled"] else "stopped"
            if pct >= 100:
                self._engine_enabled = bool(transition["target_enabled"])
                self._transition = None
                action = "idle"
                state = "running" if self._engine_enabled else "stopped"
                progress = 100
        return {
            "engine_state": state,
            "transition_action": action,
            "progress_pct": progress,
            "agent_count": len(self.list_agents()),
        }

    def set_engine_state(self, enabled: bool) -> dict:
        with self._lock:
            if self._transition is not None:
                # allow overriding an in-flight transition with a new target for better UX
                if bool(self._transition.get("target_enabled")) == enabled:
                    return self.runtime_status()
                self._transition = None
            current = self._engine_enabled
            if current == enabled:
                return self.runtime_status()
            self._transition = {
                "action": "starting" if enabled else "stopping",
                "target_enabled": enabled,
                "started_at": time.time(),
                "duration_s": 3.0,
            }
            return self.runtime_status()

    def _validate_spec(self, spec: AgentSpec) -> dict:
        payload = spec.model_dump()
        source = payload["source_type"]
        if source not in {"kraken", "binance", "open_meteo", "alphavantage_commodity"}:
            raise HTTPException(status_code=400, detail=f"unsupported source_type={source}")

        url = payload["url"].strip()
        if source in REQUIRES_API_KEY:
            key = (payload.get("api_key") or "").strip()
            if "{API_KEY}" in url and not key:
                raise HTTPException(status_code=400, detail="source requires API key; provide api_key")
            if key and "{API_KEY}" in url:
                url = url.replace("{API_KEY}", key)
            elif key and "apikey=" in url and "apikey=demo" in url:
                url = url.replace("apikey=demo", f"apikey={key}")
        payload["url"] = url
        payload.pop("api_key", None)
        return payload

    def add_agent(self, spec: AgentSpec) -> None:
        with self._lock:
            agents = self.list_agents()
            if any(item["name"] == spec.name for item in agents):
                raise HTTPException(status_code=409, detail=f"Agent '{spec.name}' already exists")
            override = self._load_override_agents()
            override.append(self._validate_spec(spec))
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
                self.runtime_status()
                if self._engine_enabled:
                    self.run_tick()
                    interval = int(self.orchestrator.config["engine"]["interval_seconds"])
                else:
                    interval = 1
            except Exception as exc:
                self.latest_frame = {"error": str(exc), "ts": int(time.time()), "signals": []}
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


@app.get("/api/suggestions")
def api_suggestions() -> dict:
    return _sanitize(runtime.market_suggestions())


@app.get("/api/locales")
def api_locales() -> dict:
    return _sanitize(runtime.locales())


@app.get("/api/runtime/status")
def api_runtime_status() -> dict:
    return _sanitize(runtime.runtime_status())


@app.post("/api/runtime/start")
def api_runtime_start() -> dict:
    return _sanitize(runtime.set_engine_state(True))


@app.post("/api/runtime/stop")
def api_runtime_stop() -> dict:
    return _sanitize(runtime.set_engine_state(False))


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
