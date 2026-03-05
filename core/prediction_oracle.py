#!/usr/bin/env python3
"""Prediction Oracle core for TPM live monitoring."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat()


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(UTC)


@dataclass
class ValidationRound:
    ts: str
    observed_price: float
    target_price: float
    error_pct: float
    confidence_pct: float
    status: str
    reason_code: str = "PENDING"


@dataclass
class Prediction:
    market: str
    created_ts: str
    created_price: float
    target_price: float
    target_ts: str
    direction: str
    base_confidence_pct: float
    tolerance_pct: float
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    validations: List[ValidationRound] = field(default_factory=list)
    confirmations_in_row: int = 0
    misses: int = 0
    signal_confidence_pct: float = 0.0
    regime_confidence_pct: float = 0.0
    data_quality_confidence_pct: float = 0.0


class PredictionOracle:
    def __init__(self, state_dir: Path = Path("state/predictions"), max_predictions: int = 30) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.max_predictions = max_predictions
        self._store: Dict[str, List[Prediction]] = {}
        self._load_all()

    def _path(self, market: str) -> Path:
        return self.state_dir / f"{market.lower()}_oracle.json"

    def _load_all(self) -> None:
        for fp in self.state_dir.glob("*_oracle.json"):
            try:
                market = fp.stem.replace("_oracle", "").upper()
                raw = json.loads(fp.read_text(encoding="utf-8"))
                items: List[Prediction] = []
                for row in raw:
                    row["validations"] = [ValidationRound(**v) for v in row.get("validations", [])]
                    row.setdefault("signal_confidence_pct", row.get("base_confidence_pct", 0.0))
                    row.setdefault("regime_confidence_pct", row.get("base_confidence_pct", 0.0))
                    row.setdefault("data_quality_confidence_pct", row.get("base_confidence_pct", 0.0))
                    items.append(Prediction(**row))
                self._store[market] = items[-self.max_predictions :]
            except Exception:
                continue

    def _save_market(self, market: str) -> None:
        items = self._store.get(market, [])[-self.max_predictions :]
        self._store[market] = items
        payload = [asdict(p) for p in items]
        self._path(market).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_prediction(
        self,
        market: str,
        current_price: float,
        target_price: float,
        horizon_seconds: int,
        base_confidence_pct: float,
        tolerance_pct: float,
        direction: str,
        signal_confidence_pct: Optional[float] = None,
        regime_confidence_pct: Optional[float] = None,
        data_quality_confidence_pct: Optional[float] = None,
    ) -> Prediction:
        now = utc_now()
        base_conf = max(1.0, min(99.9, base_confidence_pct))
        pred = Prediction(
            market=market,
            created_ts=_iso(now),
            created_price=current_price,
            target_price=target_price,
            target_ts=_iso(now + timedelta(seconds=max(1, horizon_seconds))),
            direction=direction,
            base_confidence_pct=base_conf,
            tolerance_pct=max(0.05, min(5.0, tolerance_pct)),
            signal_confidence_pct=signal_confidence_pct if signal_confidence_pct is not None else base_conf,
            regime_confidence_pct=regime_confidence_pct if regime_confidence_pct is not None else base_conf,
            data_quality_confidence_pct=data_quality_confidence_pct if data_quality_confidence_pct is not None else base_conf,
        )
        self._store.setdefault(market, []).append(pred)
        self._save_market(market)
        return pred

    @staticmethod
    def _reason_code(error_pct: float, tolerance_pct: float, observed: float, target: float) -> str:
        if target == 0:
            return "TARGET_ZERO"
        if error_pct <= tolerance_pct:
            return "ON_TRACK"
        if error_pct <= tolerance_pct * 1.6:
            return "VOLATILITY_SPIKE"
        rel_dir = (observed - target)
        if rel_dir > 0:
            return "OVERSHOOT"
        return "UNDERSHOOT"

    def _score(self, observed: float, target: float, tolerance_pct: float) -> tuple[float, float, str, str]:
        if target == 0:
            return 100.0, 0.0, "missed", "TARGET_ZERO"
        error_pct = abs(observed - target) / abs(target) * 100.0
        confidence = max(0.0, 100.0 - (error_pct / max(0.0001, tolerance_pct)) * 100.0)
        status = "confirmed" if error_pct <= tolerance_pct else "missed"
        return error_pct, confidence, status, self._reason_code(error_pct, tolerance_pct, observed, target)

    def validate_latest(self, market: str, observed_price: float) -> Optional[Prediction]:
        preds = self._store.get(market, [])
        if not preds:
            return None
        pred = preds[-1]
        if pred.status in {"completed", "expired"}:
            return pred

        error_pct, confidence, status, reason_code = self._score(observed_price, pred.target_price, pred.tolerance_pct)
        vr = ValidationRound(
            ts=_iso(utc_now()),
            observed_price=observed_price,
            target_price=pred.target_price,
            error_pct=round(error_pct, 4),
            confidence_pct=round(confidence, 2),
            status=status,
            reason_code=reason_code,
        )
        pred.validations.append(vr)
        if status == "confirmed":
            pred.confirmations_in_row += 1
        else:
            pred.confirmations_in_row = 0
            pred.misses += 1

        now = utc_now()
        if now >= _parse(pred.target_ts):
            pred.status = "completed" if status == "confirmed" else "expired"

        self._save_market(market)
        return pred

    def latest_snapshot(self, market: str, device_ts: Optional[datetime] = None) -> Optional[dict]:
        preds = self._store.get(market, [])
        if not preds:
            return None
        pred = preds[-1]
        now = utc_now()
        target_ts = _parse(pred.target_ts)
        seconds_left = max(0, int((target_ts - now).total_seconds()))
        device_delta = (device_ts.astimezone(UTC) - now).total_seconds() if device_ts else None
        eta_window_seconds = max(5, int(seconds_left * 0.2))

        hops = [
            {
                "idx": i + 1,
                "confidence_pct": v.confidence_pct,
                "status": v.status,
                "ts": v.ts,
                "reason_code": v.reason_code,
            }
            for i, v in enumerate(pred.validations[-10:])
        ]
        latest_reason = hops[-1]["reason_code"] if hops else "PENDING"
        return {
            "prediction_id": pred.prediction_id,
            "market": pred.market,
            "status": pred.status,
            "created_ts": pred.created_ts,
            "created_price": pred.created_price,
            "target_price": pred.target_price,
            "target_ts": pred.target_ts,
            "eta_window_seconds": eta_window_seconds,
            "seconds_left": seconds_left,
            "base_confidence_pct": pred.base_confidence_pct,
            "confidence_decomposition": {
                "signal_pct": round(pred.signal_confidence_pct, 2),
                "regime_pct": round(pred.regime_confidence_pct, 2),
                "data_quality_pct": round(pred.data_quality_confidence_pct, 2),
            },
            "tolerance_pct": pred.tolerance_pct,
            "direction": pred.direction,
            "confirmations_in_row": pred.confirmations_in_row,
            "misses": pred.misses,
            "validation_rounds": len(pred.validations),
            "hops": hops,
            "reason_code": latest_reason,
            "device_clock_delta_seconds": device_delta,
        }
