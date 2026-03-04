from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable


class MetacognitiveResilienceOrchestrator:
    """Lightweight runtime resilience brain for source health + predictive cooldowns."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS source_metrics (
                source_id TEXT PRIMARY KEY,
                ok_count INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms REAL NOT NULL DEFAULT 0,
                ewma_fail REAL NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                last_checked_ts INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS source_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                success INTEGER NOT NULL,
                latency_ms REAL,
                error TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self.conn.commit()

    def record_result(self, source_id: str, success: bool, latency_ms: float | None, error: str = "") -> None:
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM source_metrics WHERE source_id=?", (source_id,)).fetchone()
        if row is None:
            row = {
                "ok_count": 0,
                "fail_count": 0,
                "consecutive_failures": 0,
                "avg_latency_ms": 0.0,
                "ewma_fail": 0.0,
            }
        ok = int(row["ok_count"]) + (1 if success else 0)
        fail = int(row["fail_count"]) + (0 if success else 1)
        consecutive = 0 if success else int(row["consecutive_failures"]) + 1
        prev_lat = float(row["avg_latency_ms"]) if row else 0.0
        new_lat = prev_lat if latency_ms is None else ((prev_lat * 0.8) + (float(latency_ms) * 0.2))
        prev_ewma = float(row["ewma_fail"]) if row else 0.0
        obs = 0.0 if success else 1.0
        ewma = (prev_ewma * 0.8) + (obs * 0.2)

        cur.execute(
            """
            INSERT INTO source_metrics(source_id, ok_count, fail_count, consecutive_failures, avg_latency_ms, ewma_fail, last_error, last_checked_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
              ok_count=excluded.ok_count,
              fail_count=excluded.fail_count,
              consecutive_failures=excluded.consecutive_failures,
              avg_latency_ms=excluded.avg_latency_ms,
              ewma_fail=excluded.ewma_fail,
              last_error=excluded.last_error,
              last_checked_ts=excluded.last_checked_ts
            """,
            (source_id, ok, fail, consecutive, new_lat, ewma, ("" if success else error), int(time.time())),
        )
        cur.execute(
            "INSERT INTO source_events(source_id, ts, success, latency_ms, error) VALUES (?, ?, ?, ?, ?)",
            (source_id, int(time.time()), 1 if success else 0, latency_ms, error),
        )
        self.conn.commit()

    def predict(self, source_id: str) -> dict[str, Any]:
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM source_metrics WHERE source_id=?", (source_id,)).fetchone()
        if row is None:
            return {"status": "unknown", "predicted_cooldown_s": 0, "fail_ratio": 0.0, "recommended_action": "observe"}

        ok = int(row["ok_count"])
        fail = int(row["fail_count"])
        total = max(1, ok + fail)
        fail_ratio = fail / total
        ewma_fail = float(row["ewma_fail"])
        consecutive = int(row["consecutive_failures"])

        predicted_cooldown_s = 0
        status = "healthy"
        if fail_ratio > 0.2 or ewma_fail > 0.25:
            status = "degraded"
        if fail_ratio > 0.5 or ewma_fail > 0.45 or consecutive >= 3:
            status = "critical"
            predicted_cooldown_s = min(300, 10 * (2 ** min(5, consecutive)))

        action = "normal"
        if status == "degraded":
            action = "prefer cached/secondary source"
        if status == "critical":
            action = "activate heroic fallback + cooldown"

        return {
            "status": status,
            "predicted_cooldown_s": predicted_cooldown_s,
            "fail_ratio": round(fail_ratio, 3),
            "ewma_fail": round(ewma_fail, 3),
            "avg_latency_ms": round(float(row["avg_latency_ms"]), 2),
            "recommended_action": action,
            "last_error": str(row["last_error"]),
        }

    def startup_index(self, candidates: list[dict[str, Any]], probe: Callable[[dict[str, Any]], tuple[bool, float | None, str]]) -> dict[str, Any]:
        rows = []
        for item in candidates:
            source_id = f"{item.get('market','')}::{item.get('source_type','')}::{item.get('url','')}"
            ok, latency_ms, error = probe(item)
            self.record_result(source_id, ok, latency_ms, error)
            rows.append({**item, "source_id": source_id, "health": self.predict(source_id)})
        return {
            "generated_at": int(time.time()),
            "total_sources": len(rows),
            "healthy_sources": sum(1 for r in rows if r["health"].get("status") == "healthy"),
            "sources": rows,
        }

    def status(self) -> dict[str, Any]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT source_id FROM source_metrics ORDER BY source_id ASC").fetchall()
        payload = [{"source_id": r["source_id"], **self.predict(r["source_id"])} for r in rows]
        return {
            "generated_at": int(time.time()),
            "sources": payload,
            "critical": [p for p in payload if p.get("status") == "critical"],
        }
