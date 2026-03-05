from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from urllib.error import URLError
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.forge_config import load_config
from core.metacognitive_resilience import MetacognitiveResilienceOrchestrator
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

DISCOVERY_MARKETS: dict[str, list[dict[str, str]]] = {
    "coingecko": [
        {"market": "BTC", "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"},
        {"market": "ETH", "url": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"},
        {"market": "SOL", "url": "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"},
    ],
    "stooq": [
        {"market": "BTC", "url": "https://stooq.com/q/l/?s=btcusd&i=d"},
    ],
}

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


class AlertPrefs(BaseModel):
    termux_notify_enabled: bool = True
    vibrate_ms: int = 800
    beep_enabled: bool = False
    telegram_enabled: bool = False


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
        self._market_history: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=240))
        self._agent_history: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=240))
        self.alert_prefs_file = self.paths.state_dir / "alert_prefs.json"
        self._last_alert_ts: dict[str, float] = {}
        self.validation_report_file = self.paths.state_dir / "TPM_test_results.json"
        self.source_index_file = self.paths.state_dir / "source_index.json"
        self.mro = MetacognitiveResilienceOrchestrator(self.paths.state_dir / "resilience.db")

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
        payload = spec.model_dump() if hasattr(spec, "model_dump") else spec.dict()
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
            self._record_live_metrics(self.latest_frame)
            return self.latest_frame

    def _record_live_metrics(self, frame: dict[str, Any]) -> None:
        ts = int(frame.get("ts") or time.time())
        for signal in frame.get("signals", []):
            market = str(signal.get("market") or "").upper()
            agent = str(signal.get("agent") or "")
            if not market or not agent:
                continue
            point = {
                "ts": ts,
                "value": float(signal.get("value") or 0.0),
                "fitness": float(signal.get("fitness") or 0.0),
                "reward": float(signal.get("reward") or 0.0),
                "agent": agent,
                "market": market,
            }
            self._market_history[market].append(point)
            self._agent_history[agent].append(point)

    def live_market_snapshot(self) -> dict:
        markets: list[dict[str, Any]] = []
        for market, points in sorted(self._market_history.items()):
            if not points:
                continue
            latest = points[-1]
            prev = points[-2] if len(points) > 1 else latest
            delta = latest["value"] - prev["value"]
            pct = (delta / prev["value"] * 100.0) if prev["value"] else 0.0
            outlook = self._market_outlook(list(points))
            glitch = self._is_glitch(list(points))
            if glitch:
                self._dispatch_alert(market, outlook, float(latest["value"]))
            markets.append({
                "market": market,
                "latest": latest,
                "delta": delta,
                "delta_pct": pct,
                "outlook": outlook,
                "glitch": glitch,
                "points": list(points),
            })

        agents: list[dict[str, Any]] = []
        for agent, points in sorted(self._agent_history.items()):
            if not points:
                continue
            latest = points[-1]
            agents.append({
                "agent": agent,
                "market": latest.get("market", ""),
                "latest": latest,
                "points": list(points),
            })

        return {
            "ts": int(time.time()),
            "markets": markets,
            "agents": agents,
        }

    def _is_termux(self) -> bool:
        prefix = os.environ.get("PREFIX", "")
        return "com.termux" in prefix

    def _load_alert_prefs(self) -> dict[str, Any]:
        defaults = AlertPrefs().model_dump() if hasattr(AlertPrefs, "model_dump") else AlertPrefs().dict()
        if self.alert_prefs_file.exists():
            try:
                payload = json.loads(self.alert_prefs_file.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    defaults.update(payload)
            except Exception:
                pass
        return defaults

    def alert_preferences(self) -> dict[str, Any]:
        prefs = self._load_alert_prefs()
        prefs["termux_available"] = self._is_termux()
        return prefs

    def save_alert_preferences(self, spec: AlertPrefs) -> dict[str, Any]:
        payload = spec.model_dump() if hasattr(spec, "model_dump") else spec.dict()
        self.alert_prefs_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.alert_preferences()

    def _market_outlook(self, points: list[dict[str, Any]]) -> dict[str, Any]:
        if len(points) < 3:
            return {"direction": "unknown", "confidence": 0.0, "horizon_ticks": 3}
        tail = points[-5:]
        vals = [float(p.get("value", 0.0)) for p in tail]
        start, end = vals[0], vals[-1]
        slope = (end - start) / max(1, len(vals) - 1)
        avg = sum(vals) / max(1, len(vals))
        rel = abs(slope) / (abs(avg) + 1e-9)
        if rel < 0.0005:
            direction = "sideways"
        else:
            direction = "up" if slope > 0 else "down"
        confidence = max(0.0, min(1.0, rel * 200))
        return {"direction": direction, "confidence": round(confidence, 3), "horizon_ticks": 3}

    def _is_glitch(self, points: list[dict[str, Any]]) -> bool:
        if len(points) < 3:
            return False
        a = float(points[-3].get("value", 0.0))
        b = float(points[-2].get("value", 0.0))
        c = float(points[-1].get("value", 0.0))
        accel = c - (2 * b - a)
        baseline = abs(b) + 1e-9
        return abs(accel) / baseline > 0.01

    def _dispatch_alert(self, market: str, outlook: dict[str, Any], latest_value: float) -> None:
        prefs = self._load_alert_prefs()
        now = time.time()
        key = f"{market}:{outlook.get('direction')}"
        if now - self._last_alert_ts.get(key, 0) < 120:
            return
        self._last_alert_ts[key] = now
        message = f"IrsanAI GLITCH {market}: outlook={outlook.get('direction')} conf={outlook.get('confidence')} value={latest_value:.4f}"

        if prefs.get("termux_notify_enabled") and self._is_termux():
            try:
                subprocess.run(["termux-toast", message], check=False, capture_output=True, text=True)
                if int(prefs.get("vibrate_ms", 0)) > 0:
                    subprocess.run(["termux-vibrate", "-d", str(int(prefs.get("vibrate_ms", 0)))], check=False, capture_output=True, text=True)
                if prefs.get("beep_enabled"):
                    subprocess.run(["termux-notification", "--title", "IrsanAI TPM", "--content", message], check=False, capture_output=True, text=True)
            except Exception:
                pass

        telegram_cfg = (self.base_config.get("alerts", {}).get("telegram", {}) or {}).copy()
        if prefs.get("telegram_enabled"):
            telegram_cfg["enabled"] = True
        if telegram_cfg.get("enabled") and telegram_cfg.get("bot_token") and telegram_cfg.get("chat_id"):
            tg = f"https://api.telegram.org/bot{telegram_cfg['bot_token']}/sendMessage?chat_id={telegram_cfg['chat_id']}&text={urllib.parse.quote(message)}"
            try:
                urllib.request.urlopen(tg, timeout=4).read()
            except Exception:
                pass

    def trigger_test_alert(self) -> dict[str, Any]:
        self._dispatch_alert("TEST", {"direction": "up", "confidence": 0.99}, 1.0)
        return {"ok": True, "message": "test alert dispatched"}


    def backtest_summary(self) -> dict[str, Any]:
        if not self.validation_report_file.exists():
            return {"available": False, "reason": "validation report not found"}
        try:
            payload = json.loads(self.validation_report_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"available": False, "reason": f"invalid report: {exc}"}

        tests = payload.get("tests", []) if isinstance(payload, dict) else []
        compact = []
        for t in tests:
            if not isinstance(t, dict):
                continue
            compact.append({
                "name": t.get("name", "unknown"),
                "metric": t.get("metric"),
                "passed": bool(t.get("passed")),
                "p_value": t.get("p_value"),
            })
        return {
            "available": True,
            "generated_at_utc": payload.get("generated_at_utc"),
            "tests": compact,
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "backtest_summary": True,
            "source_resilience": True,
            "engine_transparency": True,
            "sources_index": True,
            "sources_catalog": True,
            "version": 5,
        }

    def source_health(self) -> dict[str, Any]:
        resilience = self.latest_frame.get("source_resilience", {}) if isinstance(self.latest_frame, dict) else {}
        base = resilience if isinstance(resilience, dict) else {"agents": {}, "detected_issues": []}
        base["mro"] = self.mro.status()
        return base


    def _registration_type(self, source_type: str) -> str:
        return "registration_required" if source_type in REQUIRES_API_KEY else "free_no_registration"

    def _source_catalog(self) -> dict[str, Any]:
        idx = self.source_index()
        sources = idx.get("sources", []) if isinstance(idx, dict) else []
        free = [s for s in sources if s.get("registration_type") == "free_no_registration"]
        reg = [s for s in sources if s.get("registration_type") == "registration_required"]
        return {
            "generated_at": idx.get("generated_at") if isinstance(idx, dict) else None,
            "free_no_registration": free,
            "registration_required": reg,
        }

    def refresh_source_index(self) -> dict[str, Any]:
        active_markets = {str(a.get("market", "")).upper() for a in self.list_agents() if a.get("market")}
        candidates: list[dict[str, Any]] = []
        for source_type, items in SUGGESTED_MARKETS.items():
            for item in items:
                market = str(item.get("market", "")).upper()
                candidates.append({
                    "market": market,
                    "source_type": source_type,
                    "url": str(item.get("url", "")),
                    "priority": 2 if market in active_markets else 1,
                    "registration_type": self._registration_type(source_type),
                    "discovery_origin": "core_suggested",
                })

        for source_type, items in DISCOVERY_MARKETS.items():
            for item in items:
                market = str(item.get("market", "")).upper()
                candidates.append({
                    "market": market,
                    "source_type": source_type,
                    "url": str(item.get("url", "")),
                    "priority": 2 if market in active_markets else 1,
                    "registration_type": "free_no_registration",
                    "discovery_origin": "startup_discovery",
                })

        # keep previously discovered entries for persistent growth across restarts
        if self.source_index_file.exists():
            try:
                old_payload = json.loads(self.source_index_file.read_text(encoding="utf-8"))
                for item in old_payload.get("sources", []):
                    if isinstance(item, dict) and item.get("url"):
                        candidates.append({
                            "market": str(item.get("market", "")).upper(),
                            "source_type": str(item.get("source_type", "unknown")),
                            "url": str(item.get("url", "")),
                            "priority": int(item.get("priority", 1)),
                            "registration_type": str(item.get("registration_type", "free_no_registration")),
                            "discovery_origin": str(item.get("discovery_origin", "previous_index")),
                        })
            except Exception:
                pass

        # deduplicate by url
        dedup: dict[str, dict[str, Any]] = {}
        for c in candidates:
            if not c.get("url"):
                continue
            key = str(c["url"])
            existing = dedup.get(key)
            if existing is None or int(c.get("priority", 0)) > int(existing.get("priority", 0)):
                dedup[key] = c

        def _probe(item: dict[str, Any]) -> tuple[bool, float | None, str]:
            t0 = time.time()
            try:
                probe_url = str(item.get("url", ""))
                if "{API_KEY}" in probe_url:
                    probe_url = probe_url.replace("{API_KEY}", "demo")
                req = urllib.request.Request(probe_url, headers={"User-Agent": "IrsanAI-TPM/SourceIndexer"})
                with urllib.request.urlopen(req, timeout=4):
                    pass
                return True, round((time.time() - t0) * 1000.0, 2), ""
            except Exception as exc:
                return False, round((time.time() - t0) * 1000.0, 2), str(exc)

        payload = self.mro.startup_index(list(dedup.values()), _probe)
        payload["active_markets"] = sorted(active_markets)
        payload["version"] = 3
        self.source_index_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def source_index(self) -> dict[str, Any]:
        if not self.source_index_file.exists():
            return self.refresh_source_index()
        try:
            return json.loads(self.source_index_file.read_text(encoding="utf-8"))
        except Exception:
            return self.refresh_source_index()

    def aggregated_predictions(self) -> dict[str, Any]:
        markets: list[dict[str, Any]] = []
        for market, points in sorted(self._market_history.items()):
            if len(points) < 3:
                continue
            vals = [float(p.get("value", 0.0)) for p in points][-12:]
            x = list(range(len(vals)))
            x_mean = sum(x) / len(x)
            y_mean = sum(vals) / len(vals)
            denom = sum((xi - x_mean) ** 2 for xi in x) or 1.0
            slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, vals)) / denom
            future = [vals[-1] + slope * step for step in range(1, 6)]
            confidence = max(0.0, min(0.95, 1.0 - abs(slope) / (abs(y_mean) + 1e-9)))
            markets.append({
                "market": market,
                "last": vals[-1],
                "slope": slope,
                "forecast": future,
                "confidence": round(confidence, 3),
            })
        return {"generated_at": int(time.time()), "markets": markets}

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
    try:
        runtime.refresh_source_index()
    except Exception:
        pass
    if not runtime.validation_report_file.exists():
        runtime.validation_report_file.write_text(json.dumps({
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tests": [],
            "note": "auto-generated placeholder until scientific validation runs",
        }, indent=2), encoding="utf-8")


@app.on_event("shutdown")
def _shutdown() -> None:
    runtime.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE, headers={"Cache-Control": "no-store, max-age=0"})


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


@app.get("/api/markets/live")
def api_markets_live() -> dict:
    return _sanitize(runtime.live_market_snapshot())


@app.get("/api/alerts/preferences")
def api_alert_prefs() -> dict:
    return _sanitize(runtime.alert_preferences())


@app.post("/api/alerts/preferences")
def api_alert_prefs_save(spec: AlertPrefs) -> dict:
    return _sanitize(runtime.save_alert_preferences(spec))


@app.post("/api/alerts/test")
def api_alert_test() -> dict:
    return _sanitize(runtime.trigger_test_alert())


@app.get("/api/runtime/status")
def api_runtime_status() -> dict:
    return _sanitize(runtime.runtime_status())


@app.get("/api/capabilities")
def api_capabilities() -> dict:
    return _sanitize(runtime.capabilities())


@app.get("/api/backtest/summary")
def api_backtest_summary() -> dict:
    return _sanitize(runtime.backtest_summary())


@app.get("/api/sources/health")
def api_sources_health() -> dict:
    return _sanitize(runtime.source_health())


@app.get("/api/sources/index")
def api_sources_index() -> dict:
    return _sanitize(runtime.source_index())


@app.get("/api/sources/catalog")
def api_sources_catalog() -> dict:
    return _sanitize(runtime._source_catalog())


@app.get("/api/predictions/aggregated")
def api_predictions_aggregated() -> dict:
    return _sanitize(runtime.aggregated_predictions())


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
