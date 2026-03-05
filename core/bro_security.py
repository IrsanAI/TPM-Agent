#!/usr/bin/env python3
"""Lightweight authenticated payload protection for TPM-Bro MVP.

Note: This is an interim local-first scheme (HMAC + stream XOR). Replace with
Noise/age/libsodium channel in the secure mesh phase.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Dict


def _derive(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_payload(secret: str, payload: Dict) -> Dict:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    key = _derive(secret)
    nonce = hashlib.sha256(raw + key).digest()[:12]
    ks = _keystream(key, nonce, len(raw))
    cipher = bytes(a ^ b for a, b in zip(raw, ks))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return {
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "cipher": base64.b64encode(cipher).decode("ascii"),
        "mac": base64.b64encode(mac).decode("ascii"),
        "scheme": "bro-xor-hmac-v1",
    }


def decrypt_payload(secret: str, box: Dict) -> Dict:
    key = _derive(secret)
    nonce = base64.b64decode(box["nonce"])
    cipher = base64.b64decode(box["cipher"])
    mac = base64.b64decode(box["mac"])
    exp = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, exp):
        raise ValueError("invalid mac")
    ks = _keystream(key, nonce, len(cipher))
    raw = bytes(a ^ b for a, b in zip(cipher, ks))
    return json.loads(raw.decode("utf-8"))
