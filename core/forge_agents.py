from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import time
import urllib.request


@dataclass
class AgentSignal:
    name: str
    domain: str
    market: str
    value: float
    latency_ms: float
    uptime: float
    freshness_s: float
    source_ok: bool


class BaseAgent(ABC):
    def __init__(self, spec: dict):
        self.spec = spec
        self.name = spec["name"]
        self.domain = spec["domain"]
        self.market = spec["market"]
        self.weight = float(spec.get("weight", 1.0))
        self.failures = 0
        self.success = 0

    @abstractmethod
    def parse_value(self, payload: dict) -> float:
        ...

    def fetch(self, timeout: float = 6.0) -> AgentSignal:
        t0 = time.time()
        req = urllib.request.Request(self.spec["url"], headers={"User-Agent": "IrsanAI-TPM/Forge"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)
        value = self.parse_value(payload)
        latency_ms = (time.time() - t0) * 1000.0
        self.success += 1
        return AgentSignal(
            name=self.name,
            domain=self.domain,
            market=self.market,
            value=value,
            latency_ms=latency_ms,
            uptime=self.success / max(1, self.success + self.failures),
            freshness_s=0.0,
            source_ok=True,
        )


class GenericMarketAgent(BaseAgent):
    def parse_value(self, payload: dict) -> float:
        stype = self.spec["source_type"]
        if stype == "kraken":
            return float(payload["result"]["XXBTZUSD"][-1][4])
        if stype == "binance":
            return float(payload["price"])
        if stype == "open_meteo":
            return float(payload["current"]["temperature_2m"])
        raise ValueError(f"unsupported source_type={stype}")


class DynamicAgentFactory:
    @staticmethod
    def build(agent_specs: list[dict]) -> list[BaseAgent]:
        return [GenericMarketAgent(spec) for spec in agent_specs]
