#!/usr/bin/env python3
"""TPM-Bro cooperative session manager (local-first MVP).

This module provides a secure-ish local session backbone for collaborative
agent sessions across LAN/Wi-Fi environments.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

UTC = timezone.utc


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class BroSignal:
    ts: str
    alias: str
    market: str
    prediction_id: str
    confidence_pct: float
    reason_code: str
    drift_status: str


@dataclass
class BroSession:
    session_id: str
    clan_name: str
    admin_alias: str
    created_ts: str
    expires_ts: str
    status: str = "active"
    members: List[str] = field(default_factory=list)
    signals: List[BroSignal] = field(default_factory=list)


class BroSessionManager:
    def __init__(self, state_file: Path = Path("state/bro_sessions.json"), history_dir: Path = Path("state/bro_history")) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, BroSession] = {}
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
            for row in raw.get("sessions", []):
                row["signals"] = [BroSignal(**s) for s in row.get("signals", [])]
                s = BroSession(**row)
                self._sessions[s.session_id] = s
        except Exception:
            self._sessions = {}

    def _save(self) -> None:
        payload = {"sessions": [asdict(s) for s in self._sessions.values()]}
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    def list_sessions(self) -> List[dict]:
        now = datetime.now(UTC)
        out = []
        for s in self._sessions.values():
            expires = datetime.fromisoformat(s.expires_ts)
            if s.status == "active" and expires < now:
                s.status = "expired"
            out.append(
                {
                    "session_id": s.session_id,
                    "clan_name": s.clan_name,
                    "admin_alias": s.admin_alias,
                    "status": s.status,
                    "members": len(s.members),
                    "signals": len(s.signals),
                    "created_ts": s.created_ts,
                    "expires_ts": s.expires_ts,
                }
            )
        self._save()
        return sorted(out, key=lambda x: x["created_ts"], reverse=True)

    def create_session(self, clan_name: str, admin_alias: str, ttl_minutes: int = 90) -> dict:
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        s = BroSession(
            session_id=sid,
            clan_name=clan_name.strip()[:80] or "TPM-Bro Clan",
            admin_alias=admin_alias.strip()[:40] or "Admin",
            created_ts=now.isoformat(),
            expires_ts=(now + timedelta(minutes=max(5, min(720, ttl_minutes)))).isoformat(),
            members=[admin_alias.strip()[:40] or "Admin"],
        )
        self._sessions[sid] = s
        self._save()
        return {"ok": True, "session_id": sid, "session": self._session_detail(sid)}

    def join_session(self, session_id: str, alias: str) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"ok": False, "error_code": "BRO_SESSION_NOT_FOUND"}
        if s.status != "active":
            return {"ok": False, "error_code": "BRO_SESSION_CLOSED"}
        name = alias.strip()[:40] or "Guest"
        if name not in s.members:
            s.members.append(name)
        self._save()
        return {"ok": True, "session": self._session_detail(session_id)}

    def publish_signal(
        self,
        session_id: str,
        alias: str,
        market: str,
        prediction_id: str,
        confidence_pct: float,
        reason_code: str,
        drift_status: str,
    ) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"ok": False, "error_code": "BRO_SESSION_NOT_FOUND"}
        if s.status != "active":
            return {"ok": False, "error_code": "BRO_SESSION_CLOSED"}

        sig = BroSignal(
            ts=_now_iso(),
            alias=alias.strip()[:40] or "Unknown",
            market=market.strip().upper()[:20] or "BTC",
            prediction_id=prediction_id.strip()[:80],
            confidence_pct=max(0.0, min(100.0, float(confidence_pct))),
            reason_code=reason_code.strip()[:40] or "PENDING",
            drift_status=drift_status.strip()[:20] or "low",
        )
        s.signals.append(sig)
        self._save()
        return {"ok": True, "session": self._session_detail(session_id)}

    def close_session(self, session_id: str) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"ok": False, "error_code": "BRO_SESSION_NOT_FOUND"}
        s.status = "closed"

        # simple knowledge pack all participants can consume locally
        knowledge = {
            "session_id": s.session_id,
            "clan_name": s.clan_name,
            "closed_ts": _now_iso(),
            "members": s.members,
            "signals_count": len(s.signals),
            "market_counts": {},
            "reason_counts": {},
            "avg_confidence": 0.0,
        }
        if s.signals:
            knowledge["avg_confidence"] = round(sum(x.confidence_pct for x in s.signals) / len(s.signals), 2)
        for x in s.signals:
            knowledge["market_counts"][x.market] = knowledge["market_counts"].get(x.market, 0) + 1
            knowledge["reason_counts"][x.reason_code] = knowledge["reason_counts"].get(x.reason_code, 0) + 1

        hist = self.history_dir / f"{s.session_id}.json"
        hist.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
        self._save()
        return {"ok": True, "session": self._session_detail(session_id), "knowledge": knowledge}

    def _session_detail(self, session_id: str) -> Optional[dict]:
        s = self._sessions.get(session_id)
        if not s:
            return None
        recent = [asdict(x) for x in s.signals[-12:]]
        return {
            "session_id": s.session_id,
            "clan_name": s.clan_name,
            "admin_alias": s.admin_alias,
            "status": s.status,
            "created_ts": s.created_ts,
            "expires_ts": s.expires_ts,
            "members": s.members,
            "signals": recent,
        }

    def session_detail(self, session_id: str) -> dict:
        item = self._session_detail(session_id)
        if not item:
            return {"ok": False, "error_code": "BRO_SESSION_NOT_FOUND"}
        return {"ok": True, "session": item}
