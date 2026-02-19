from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentFitness:
    name: str
    score: float


class NeuronalOptimizationEngine:
    def __init__(self, lr: float = 0.08):
        self.lr = lr
        self.rewards: dict[str, float] = {}

    def fitness_score(
        self,
        *,
        success_rate: float,
        latency_ms: float,
        freshness_s: float,
        uptime: float,
        predictive_power: float,
        redundancy_penalty: float,
    ) -> float:
        latency_term = max(0.0, 1.0 - latency_ms / 5000.0)
        freshness_term = max(0.0, 1.0 - freshness_s / 120.0)
        return (
            0.23 * success_rate
            + 0.15 * latency_term
            + 0.12 * freshness_term
            + 0.10 * uptime
            + 0.35 * predictive_power
            - 0.05 * redundancy_penalty
        )

    def update_reward(self, agent_name: str, fitness: float) -> float:
        prev = self.rewards.get(agent_name, 0.5)
        new = prev + self.lr * (fitness - prev)
        self.rewards[agent_name] = new
        return new

    def cull_candidates(self, min_reward: float = 0.35) -> list[str]:
        return [name for name, reward in self.rewards.items() if reward < min_reward]
