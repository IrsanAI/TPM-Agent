#!/usr/bin/env python3
"""LAN discovery baseline for TPM-Bro sessions via UDP broadcast."""

from __future__ import annotations

import json
import socket
import time
from datetime import datetime, timezone
from typing import List

PORT = 45888
MAGIC = "TPM_BRO_DISCOVERY_V1"


def scan(alias: str, timeout_s: float = 1.2) -> List[dict]:
    now = datetime.now(timezone.utc).isoformat()
    hello = {
        "magic": MAGIC,
        "alias": alias,
        "ts": now,
    }
    raw = json.dumps(hello).encode("utf-8")

    found = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    try:
        sock.sendto(raw, ("255.255.255.255", PORT))
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                msg = json.loads(data.decode("utf-8"))
                if msg.get("magic") != MAGIC:
                    continue
                found.append(
                    {
                        "ip": addr[0],
                        "port": addr[1],
                        "alias": msg.get("alias", "unknown"),
                        "ts": msg.get("ts"),
                    }
                )
            except Exception:
                continue
    except Exception:
        pass
    finally:
        sock.close()

    dedup = {}
    for x in found:
        dedup[(x["ip"], x["alias"])] = x
    return list(dedup.values())
