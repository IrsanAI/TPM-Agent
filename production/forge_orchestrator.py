from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib import request

from core.forge_agents import DynamicAgentFactory
from core.forge_config import load_config
from core.forge_entropy import TransferEntropyEngine
from core.forge_optimizer import NeuronalOptimizationEngine


def _send_webhook(url: str, message: str) -> None:
    payload = json.dumps({"text": message}).encode("utf-8")
    req = request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=4):
        return


class ForgeOrchestrator:
    def __init__(self, config_path: Path | None = None):
        self.config, self.paths = load_config(config_path)
        self.agents = DynamicAgentFactory.build(self.config["agents"])
        engine_cfg = self.config["engine"]
        self.entropy = TransferEntropyEngine(bins=int(engine_cfg["entropy_bins"]), lag=int(engine_cfg["transfer_lag"]))
        self.optimizer = NeuronalOptimizationEngine(lr=float(engine_cfg["reward_learning_rate"]))
        self.cache_file = self.paths.state_dir / "latest_prices.json"
        self.series = defaultdict(lambda: deque(maxlen=int(engine_cfg["lookback_window"])))
        self.fail_state = defaultdict(int)

    def _store_cache(self, frame: dict) -> None:
        self.cache_file.write_text(json.dumps(frame, indent=2), encoding="utf-8")

    def _broadcast_alert(self, message: str) -> None:
        telegram = self.config["alerts"]["telegram"]
        if telegram.get("enabled") and telegram.get("bot_token") and telegram.get("chat_id"):
            tg_url = f"https://api.telegram.org/bot{telegram['bot_token']}/sendMessage?chat_id={telegram['chat_id']}&text={message}"
            _send_webhook(tg_url, message)
        signal = self.config["alerts"]["signal"]
        if signal.get("enabled") and signal.get("endpoint"):
            _send_webhook(signal["endpoint"], message)

    def _domain_summary(self, scored: list[dict]) -> dict[str, dict]:
        grouped: dict[str, dict] = {}
        for row in scored:
            item = grouped.setdefault(row["domain"], {"count": 0, "avg_fitness": 0.0, "markets": []})
            item["count"] += 1
            item["avg_fitness"] += row["fitness"]
            item["markets"].append(row["market"])
        for domain, item in grouped.items():
            item["avg_fitness"] = item["avg_fitness"] / max(1, item["count"])
            item["template"] = f"{domain}+future"
        return grouped

    def tick(self) -> dict:
        signals = []
        for agent in self.agents:
            try:
                signal = agent.fetch()
                self.series[agent.name].append(signal.value)
                self.fail_state[agent.name] = 0
                signals.append(signal)
            except Exception:
                agent.failures += 1
                self.fail_state[agent.name] += 1

        graph = self.entropy.correlation_graph({name: list(values) for name, values in self.series.items()})
        predictive_power = (sum(graph.values()) / max(1, len(graph))) if graph else 0.0

        scored = []
        for signal in signals:
            redundancy = sum(1 for edge, score in graph.items() if signal.name in edge and score > 0.8)
            fitness = self.optimizer.fitness_score(
                success_rate=1.0,
                latency_ms=signal.latency_ms,
                freshness_s=signal.freshness_s,
                uptime=signal.uptime,
                predictive_power=predictive_power,
                redundancy_penalty=float(redundancy),
            )
            reward = self.optimizer.update_reward(signal.name, fitness)
            scored.append(
                {
                    "agent": signal.name,
                    "domain": signal.domain,
                    "market": signal.market,
                    "value": signal.value,
                    "fitness": fitness,
                    "reward": reward,
                }
            )

        cull = self.optimizer.cull_candidates()
        frame = {
            "ts": int(time.time()),
            "runtime": self.config["runtime"],
            "signals": scored,
            "domain_summary": self._domain_summary(scored),
            "ui_profile": self.config.get("ui", {}),
            "transfer_entropy_graph": graph,
            "cull_candidates": cull,
        }
        self._store_cache(frame)
        if cull:
            self._broadcast_alert(f"Forge circuit warning: low-reward agents={','.join(cull)}")
        return frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Forge stage-4 self-evolution loop")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--ticks", type=int, default=1)
    args = parser.parse_args()

    orch = ForgeOrchestrator(Path(args.config))
    for _ in range(args.ticks):
        frame = orch.tick()
        print(json.dumps(frame, indent=2))
        time.sleep(int(orch.config["engine"]["interval_seconds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
