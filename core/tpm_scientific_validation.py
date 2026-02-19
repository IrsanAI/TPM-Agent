#!/usr/bin/env python3
"""TPM Scientific Validation Framework (Backtest + Statistical Validation).

Improvements over previous iteration:
- robust chi2 handling for zero-cell contingency tables
- adaptive detector with alert cooldown and alpha-delta gating
- stdlib-only implementation for constrained environments (e.g., Termux)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


@dataclass
class ValidationConfig:
    n_ticks: int = 9000
    seed: int = 42
    window_size: int = 30
    history_warmup: int = 50
    percentile: float = 95.0
    safety_floor: float = 0.40
    min_alpha_delta: float = 0.005
    alert_cooldown_ticks: int = 8
    pre_event_window: int = 30
    n_permutations: int = 400


@dataclass
class TestResult:
    name: str
    metric: float
    p_value: float
    passed: bool
    notes: str


def mean(values: Sequence[float]) -> float:
    return sum(values) / max(len(values), 1)


def std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.pstdev(values)


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    p = max(0.0, min(100.0, p))
    vals = sorted(values)
    idx = (len(vals) - 1) * (p / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (idx - lo)


def compute_return(prev_price: float, price: float) -> float:
    if prev_price == 0:
        return 0.0
    return (price - prev_price) / prev_price


def compute_alpha(returns_window: Sequence[float]) -> float:
    """TPM alpha: low realized volatility -> high alpha."""
    vol = std(returns_window)
    exp_arg = max(-20.0, min(20.0, 100.0 * (vol - 0.005)))
    return 1.0 / (1.0 + math.exp(exp_arg))


def generate_synthetic_data(cfg: ValidationConfig) -> Dict[str, List[float]]:
    random.seed(cfg.seed)
    prices: List[float] = [75000.0]
    labels: List[int] = [0]

    segments = [
        (500, 610),
        (1450, 1600),
        (2750, 2860),
        (3900, 4050),
        (5300, 5440),
        (7100, 7250),
    ]
    frozen_lookup = set(i for a, b in segments for i in range(a, b))

    for t in range(1, cfg.n_ticks):
        is_frozen = t in frozen_lookup

        if is_frozen:
            ret = random.gauss(0.0, 0.00004)
        else:
            ret = random.gauss(0.0, 0.0012)

        if any(t == b for _, b in segments):
            ret += random.choice([-1, 1]) * random.uniform(0.002, 0.006)

        prices.append(prices[-1] * (1.0 + ret))
        labels.append(1 if is_frozen else 0)

    return {"prices": prices, "labels": labels, "frozen_segments": segments}


def run_backtest(data: Dict[str, List[float]], cfg: ValidationConfig) -> Dict[str, List[float]]:
    prices = data["prices"]
    labels = data["labels"]

    returns_window: List[float] = []
    alpha_history: List[float] = []
    alphas: List[float] = [0.0] * len(prices)
    predictions: List[int] = [0] * len(prices)

    prev_price = prices[0]
    cooldown = 0
    prev_alpha = 0.0

    for t, price in enumerate(prices[1:], start=1):
        r = compute_return(prev_price, price)
        prev_price = price

        returns_window.append(r)
        if len(returns_window) > cfg.window_size:
            returns_window.pop(0)
        if len(returns_window) < cfg.window_size:
            continue

        alpha = compute_alpha(returns_window)
        alphas[t] = alpha
        alpha_history.append(alpha)

        if cooldown > 0:
            cooldown -= 1

        if len(alpha_history) > cfg.history_warmup:
            theta = percentile(alpha_history, cfg.percentile)
            strong_enough = alpha > cfg.safety_floor
            dynamic_hit = alpha > theta
            changing = (alpha - prev_alpha) >= cfg.min_alpha_delta
            if dynamic_hit and strong_enough and changing and cooldown == 0:
                predictions[t] = 1
                cooldown = cfg.alert_cooldown_ticks

        prev_alpha = alpha

    return {"prices": prices, "labels": labels, "alphas": alphas, "predictions": predictions}


def confusion(labels: Sequence[int], preds: Sequence[int]) -> Tuple[int, int, int, int]:
    tp = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 0)
    tn = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 0)
    return tp, fp, fn, tn


def chi2_pvalue_safe(tp: int, fp: int, fn: int, tn: int) -> float:
    a, b, c, d = float(tp), float(fp), float(fn), float(tn)
    n = a + b + c + d
    if n == 0:
        return 1.0

    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d
    if row1 == 0 or row2 == 0 or col1 == 0 or col2 == 0:
        return 1.0

    e11 = row1 * col1 / n
    e12 = row1 * col2 / n
    e21 = row2 * col1 / n
    e22 = row2 * col2 / n
    if min(e11, e12, e21, e22) <= 0:
        return 1.0

    chi2 = ((a - e11) ** 2) / e11 + ((b - e12) ** 2) / e12 + ((c - e21) ** 2) / e21 + ((d - e22) ** 2) / e22
    return max(0.0, min(1.0, math.erfc(math.sqrt(max(0.0, chi2) / 2.0))))


def permutation_pvalue(observed: float, null_samples: Sequence[float], higher_is_better: bool = True) -> float:
    if not null_samples:
        return 1.0
    if higher_is_better:
        k = sum(1 for x in null_samples if x >= observed)
    else:
        k = sum(1 for x in null_samples if x <= observed)
    return (k + 1) / (len(null_samples) + 1)


def compute_lead_times(labels: Sequence[int], preds: Sequence[int], pre_event_window: int) -> List[int]:
    starts = [i for i in range(1, len(labels)) if labels[i] == 1 and labels[i - 1] == 0]
    out: List[int] = []
    for s in starts:
        lo = max(0, s - pre_event_window)
        candidate = [i for i in range(lo, s) if preds[i] == 1]
        if candidate:
            out.append(s - candidate[-1])
    return out


def evaluate(backtest: Dict[str, List[float]], cfg: ValidationConfig) -> List[TestResult]:
    labels = backtest["labels"]
    preds = backtest["predictions"]
    alphas = backtest["alphas"]
    prices = backtest["prices"]

    tp, fp, fn, tn = confusion(labels, preds)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)

    chi2_p = chi2_pvalue_safe(tp, fp, fn, tn)

    random.seed(cfg.seed + 100)
    null_f1 = []
    for _ in range(cfg.n_permutations):
        rand_preds = [random.randint(0, 1) for _ in labels]
        rtp, rfp, rfn, _ = confusion(labels, rand_preds)
        rp = rtp / max(rtp + rfp, 1)
        rr = rtp / max(rtp + rfn, 1)
        null_f1.append(2 * rp * rr / max(rp + rr, 1e-12))
    p_f1 = max(chi2_p, permutation_pvalue(f1, null_f1, True))

    lead_times = compute_lead_times(labels, preds, cfg.pre_event_window)
    lead_mean = mean(lead_times) if lead_times else 0.0
    random.seed(cfg.seed + 101)
    null_lead = [
        mean([random.randint(1, cfg.pre_event_window) for _ in range(max(1, len(lead_times)))])
        for _ in range(cfg.n_permutations)
    ]
    p_lead = permutation_pvalue(lead_mean, null_lead, True)

    alpha_pos = [a for a, y in zip(alphas, labels) if y == 1]
    alpha_neg = [a for a, y in zip(alphas, labels) if y == 0]
    pooled = alpha_pos + alpha_neg
    d = (mean(alpha_pos) - mean(alpha_neg)) / max(std(pooled), 1e-12)
    random.seed(cfg.seed + 102)
    null_d = []
    for _ in range(cfg.n_permutations):
        shuf = alpha_pos + alpha_neg
        random.shuffle(shuf)
        s_pos = shuf[: len(alpha_pos)]
        s_neg = shuf[len(alpha_pos) :]
        null_d.append((mean(s_pos) - mean(s_neg)) / max(std(shuf), 1e-12))
    p_d = permutation_pvalue(d, null_d, True)

    fpr = fp / max(fp + tn, 1)

    strategy_returns: List[float] = []
    for i in range(1, len(prices)):
        market_ret = compute_return(prices[i - 1], prices[i])
        strategy_returns.append(-market_ret if preds[i] == 1 else 0.0)

    sr = mean(strategy_returns) / max(std(strategy_returns), 1e-12) * math.sqrt(365 * 24 * 60)
    random.seed(cfg.seed + 103)
    null_sr = []
    for _ in range(cfg.n_permutations):
        rand_preds = [random.randint(0, 1) for _ in preds]
        rs = []
        for i in range(1, len(prices)):
            market_ret = compute_return(prices[i - 1], prices[i])
            rs.append(-market_ret if rand_preds[i] == 1 else 0.0)
        null_sr.append(mean(rs) / max(std(rs), 1e-12) * math.sqrt(365 * 24 * 60))
    p_sr = permutation_pvalue(sr, null_sr, True)

    return [
        TestResult("classification_f1", f1, p_f1, f1 >= 0.60 and p_f1 < 0.05, f"precision={precision:.3f}, recall={recall:.3f}, chi2_p={chi2_p:.4f}"),
        TestResult("lead_time_ticks", lead_mean, p_lead, lead_mean >= 5.0 and p_lead < 0.05, f"lead_events={len(lead_times)}"),
        TestResult("alpha_separation_cohens_d", d, p_d, d >= 0.80 and p_d < 0.05, "frozen vs normal alpha separation"),
        TestResult("false_positive_rate", fpr, 0.0, fpr <= 0.30, f"fp_rate={fpr:.3f}"),
        TestResult("strategy_sharpe", sr, p_sr, sr >= 0.5 and p_sr < 0.05, "simple short-on-alert proxy"),
    ]


def write_artifacts(cfg: ValidationConfig, tests: Sequence[TestResult], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow().isoformat()
    payload = {
        "generated_at_utc": now,
        "config": asdict(cfg),
        "tests": [asdict(t) for t in tests],
        "pass_count": sum(1 for t in tests if t.passed),
    }
    (out_dir / "TPM_test_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# TPM Scientific Validation Report",
        "",
        f"Generated (UTC): `{now}`",
        "",
        "## Configuration",
        "",
        f"- n_ticks: {cfg.n_ticks}",
        f"- window_size: {cfg.window_size}",
        f"- percentile: {cfg.percentile}",
        f"- safety_floor: {cfg.safety_floor}",
        f"- min_alpha_delta: {cfg.min_alpha_delta}",
        f"- alert_cooldown_ticks: {cfg.alert_cooldown_ticks}",
        f"- pre_event_window: {cfg.pre_event_window}",
        "",
        "## Test Results",
        "",
        "| Test | Metric | p-value | Pass | Notes |",
        "|---|---:|---:|:---:|---|",
    ]
    for t in tests:
        lines.append(f"| {t.name} | {t.metric:.4f} | {t.p_value:.4f} | {'✅' if t.passed else '❌'} | {t.notes} |")
    lines.extend(
        [
            "",
            f"**Passed:** {payload['pass_count']}/{len(tests)}",
            "",
            "## Notes",
            "",
            "- Chi² uses zero-cell guards to avoid contingency crashes.",
            "- Detector includes cooldown + alpha delta gate to reduce alert spam clusters.",
            "- This is synthetic validation; out-of-sample real-market checks remain mandatory.",
        ]
    )
    (out_dir / "TPM_Scientific_Report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TPM Backtest + Statistical Validation")
    parser.add_argument("--ticks", type=int, default=ValidationConfig.n_ticks)
    parser.add_argument("--seed", type=int, default=ValidationConfig.seed)
    parser.add_argument("--window-size", type=int, default=ValidationConfig.window_size)
    parser.add_argument("--percentile", type=float, default=ValidationConfig.percentile)
    parser.add_argument("--safety-floor", type=float, default=ValidationConfig.safety_floor)
    parser.add_argument("--min-alpha-delta", type=float, default=ValidationConfig.min_alpha_delta)
    parser.add_argument("--alert-cooldown", type=int, default=ValidationConfig.alert_cooldown_ticks)
    parser.add_argument("--out-dir", default="state")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ValidationConfig(
        n_ticks=args.ticks,
        seed=args.seed,
        window_size=args.window_size,
        percentile=args.percentile,
        safety_floor=args.safety_floor,
        min_alpha_delta=args.min_alpha_delta,
        alert_cooldown_ticks=args.alert_cooldown,
    )

    data = generate_synthetic_data(cfg)
    backtest = run_backtest(data, cfg)
    tests = evaluate(backtest, cfg)
    write_artifacts(cfg, tests, Path(args.out_dir))

    print("TPM Scientific Validation finished.")
    print(f"Artifacts: {args.out_dir}/TPM_Scientific_Report.md, {args.out_dir}/TPM_test_results.json")
    print(f"Passed tests: {sum(1 for t in tests if t.passed)}/{len(tests)}")


if __name__ == "__main__":
    main()
