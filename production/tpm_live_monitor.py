#!/usr/bin/env python3
"""TPM live monitor for BTC with optional history warm-start.

- Uses Kraken OHLC endpoint (interval in minutes)
- Warm-start from CSV to avoid long alpha warmup
- Alert cooldown to avoid repetitive cluster spam
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, List, Optional, Tuple

from core.prediction_oracle import PredictionOracle


class TPMEngineAdaptive:
    def __init__(
        self,
        window_size: int = 30,
        percentile: float = 95.0,
        safety_floor: float = 0.40,
        min_alpha_delta: float = 0.005,
        cooldown_ticks: int = 8,
    ) -> None:
        self.window_size = window_size
        self.percentile = percentile
        self.safety_floor = safety_floor
        self.min_alpha_delta = min_alpha_delta
        self.cooldown_ticks = cooldown_ticks

        self.price_history: Deque[float] = deque(maxlen=2)
        self.return_buffer: Deque[float] = deque(maxlen=window_size)
        self.alpha_history: Deque[float] = deque(maxlen=1000)

        self._last_alpha: float = 0.0
        self._cooldown: int = 0

    def process_tick(self, price: float) -> Tuple[float, bool]:
        if len(self.price_history) == 2:
            prev = self.price_history[-1]
            ret = (price - prev) / prev if prev != 0 else 0.0
            self.return_buffer.append(ret)
        self.price_history.append(price)

        if len(self.return_buffer) < self.window_size:
            return 0.0, False

        alpha = self.calculate_alpha(list(self.return_buffer))
        self.alpha_history.append(alpha)

        if self._cooldown > 0:
            self._cooldown -= 1

        triggered = False
        if len(self.alpha_history) > 50:
            theta = self.percentile_value(list(self.alpha_history), self.percentile)
            changing = (alpha - self._last_alpha) >= self.min_alpha_delta
            if alpha > theta and alpha > self.safety_floor and changing and self._cooldown == 0:
                triggered = True
                self._cooldown = self.cooldown_ticks

        self._last_alpha = alpha
        return alpha, triggered

    @staticmethod
    def calculate_alpha(returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((x - mean) ** 2 for x in returns) / len(returns)
        vol = math.sqrt(var)
        exp_arg = max(-20.0, min(20.0, 100.0 * (vol - 0.005)))
        return 1.0 / (1.0 + math.exp(exp_arg))

    @staticmethod
    def percentile_value(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        vals = sorted(values)
        idx = (len(vals) - 1) * (max(0.0, min(100.0, p)) / 100.0)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return vals[lo]
        return vals[lo] + (vals[hi] - vals[lo]) * (idx - lo)


def get_latest_btc_price(interval_min: int = 60) -> Optional[float]:
    url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval={interval_min}"
    try:
        res = subprocess.run(["curl", "-s", url], capture_output=True, text=True, check=False)
        data = json.loads(res.stdout)
        candles = data.get("result", {}).get("XXBTZUSD")
        if not candles:
            return None
        return float(candles[-1][4])
    except Exception:
        return None


def load_history_csv(path: Path) -> List[float]:
    if not path.exists():
        return []
    out: List[float] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                out.append(float(row[0]))
            except ValueError:
                continue
    return out




def infer_target(price: float, alpha: float, last_returns: List[float], horizon_seconds: int, poll_seconds: int) -> tuple[float, str, float]:
    """Infer target price from short return trend + alpha confidence."""
    if not last_returns:
        drift = 0.0
    else:
        drift = sum(last_returns[-10:]) / max(1, len(last_returns[-10:]))
    direction = "UP" if drift >= 0 else "DOWN"
    steps = max(1, horizon_seconds // max(1, poll_seconds))
    projected = price * (1.0 + drift * steps)
    target = max(0.01, projected)
    base_conf = max(40.0, min(99.0, (1.0 - alpha) * 100.0 + 15.0))
    return target, direction, base_conf




def confidence_components(alpha: float, trigger: bool, tick_count: int) -> tuple[float, float, float]:
    signal = max(20.0, min(98.0, 100.0 - alpha * 100.0))
    regime = 78.0 if trigger else 64.0
    data_quality = 55.0 if tick_count < 10 else 84.0
    return signal, regime, data_quality


def adaptive_tolerance(alpha: float, misses: int, rounds: int) -> float:
    miss_pressure = (misses / max(1, rounds)) * 1.2
    raw = max(0.2, (1.0 - alpha) * 0.9 + miss_pressure)
    return max(0.2, min(3.5, raw))

def save_oracle_snapshot(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(snapshot)
    payload["snapshot_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def run_termux_notification(message: str, vibrate_ms: int) -> None:
    """Best-effort Termux notification; ignored outside Termux or if unavailable."""
    try:
        subprocess.run(["termux-toast", message], check=False, capture_output=True, text=True)
        if vibrate_ms > 0:
            subprocess.run(["termux-vibrate", "-d", str(vibrate_ms)], check=False, capture_output=True, text=True)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="TPM live BTC monitor")
    parser.add_argument("--history-csv", default="btc_real_24h.csv")
    parser.add_argument("--poll-seconds", type=int, default=3600)
    parser.add_argument("--interval-min", type=int, default=60)
    parser.add_argument("--window-size", type=int, default=30)
    parser.add_argument("--percentile", type=float, default=95.0)
    parser.add_argument("--safety-floor", type=float, default=0.40)
    parser.add_argument("--min-alpha-delta", type=float, default=0.005)
    parser.add_argument("--cooldown", type=int, default=8)
    parser.add_argument("--notify", action="store_true", help="Enable termux-toast + termux-vibrate on alerts")
    parser.add_argument("--vibrate-ms", type=int, default=800)
    parser.add_argument("--oracle-market", default="BTC")
    parser.add_argument("--oracle-horizon-seconds", type=int, default=180)
    parser.add_argument("--oracle-recalc-every", type=int, default=3, help="Create a fresh prediction every N ticks")
    args = parser.parse_args()

    engine = TPMEngineAdaptive(
        window_size=args.window_size,
        percentile=args.percentile,
        safety_floor=args.safety_floor,
        min_alpha_delta=args.min_alpha_delta,
        cooldown_ticks=args.cooldown,
    )

    oracle = PredictionOracle()
    snapshot_path = Path("state/prediction_hub_latest.json")
    tick_count = 0

    history = load_history_csv(Path(args.history_csv))
    if history:
        print(f"Loaded history: {len(history)} rows from {args.history_csv}")
        for i, p in enumerate(history):
            alpha, trig = engine.process_tick(p)
            if trig:
                print(f"[HISTORY] GLITCH tick={i:04d} alpha={alpha:.4f} price=${p:,.2f}")
    else:
        print("No history warm-start loaded.")

    mode = "with notifications" if args.notify else "without notifications"
    print(f"IrsanAI Live-Monitor v2 ({mode}) started. Ctrl+C to stop.")
    while True:
        price = get_latest_btc_price(args.interval_min)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if price is None:
            print(f"[{now}] BTC fetch failed; retrying in {args.poll_seconds}s")
            time.sleep(args.poll_seconds)
            continue

        alpha, trigger = engine.process_tick(price)
        tick_count += 1
        print(f"[{now}] BTC=${price:,.2f} alpha={alpha:.4f}")

        should_recalc = (tick_count % max(1, args.oracle_recalc_every) == 0) or trigger
        if should_recalc and len(engine.return_buffer) >= 3:
            target_price, direction, base_conf = infer_target(
                price=price,
                alpha=alpha,
                last_returns=list(engine.return_buffer),
                horizon_seconds=args.oracle_horizon_seconds,
                poll_seconds=args.poll_seconds,
            )
            latest_before = oracle.latest_snapshot(args.oracle_market) or {}
            signal_c, regime_c, quality_c = confidence_components(alpha, trigger, tick_count)
            tol = adaptive_tolerance(alpha, int(latest_before.get("misses", 0)), int(latest_before.get("validation_rounds", 0)))
            pred = oracle.create_prediction(
                market=args.oracle_market,
                current_price=price,
                target_price=target_price,
                horizon_seconds=args.oracle_horizon_seconds,
                base_confidence_pct=base_conf,
                tolerance_pct=tol,
                direction=direction,
                signal_confidence_pct=signal_c,
                regime_confidence_pct=regime_c,
                data_quality_confidence_pct=quality_c,
            )
            print(
                f"[ORACLE] id={pred.prediction_id[:8]} market={pred.market} now=${pred.created_price:,.2f} "
                f"target=${pred.target_price:,.2f} eta={pred.target_ts} conf={pred.base_confidence_pct:.1f}%"
            )

        oracle.validate_latest(args.oracle_market, price)
        snap = oracle.latest_snapshot(args.oracle_market)
        if snap:
            save_oracle_snapshot(snapshot_path, snap)
            eta = snap.get("seconds_left", 0)
            status = snap.get("status", "pending")
            streak = snap.get("confirmations_in_row", 0)
            rounds = snap.get("validation_rounds", 0)
            print(
                f"[ORACLE] status={status} rounds={rounds} streak={streak} "
                f"⏱️ {eta}s left to target @ ${snap['target_price']:,.2f}"
            )

        if trigger:
            alert = f"🔥 LIVE-GLITCH DETECTED alpha={alpha:.4f} price=${price:,.2f}"
            print(alert)
            if args.notify:
                run_termux_notification(f"GLITCH alpha={alpha:.4f} BTC ${price:,.0f}", args.vibrate_ms)
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
