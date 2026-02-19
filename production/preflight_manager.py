#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("IRSANAI_DB_PATH", os.path.join(BASE_DIR, "data", "irsanai_production.db"))
STATE_DIR = Path(os.environ.get("IRSANAI_STATE_DIR", os.path.join(BASE_DIR, "state")))
CACHE_PATH = STATE_DIR / "latest_prices.json"

# Set ALPHAVANTAGE_KEY in environment for coffee API.
AV_KEY = os.environ.get("ALPHAVANTAGE_KEY", "")


@dataclass
class Source:
    name: str
    type: str
    url: str


def _coffee_sources() -> list[Source]:
    out = []
    if AV_KEY:
        out.append(
            Source(
                "alpha_vantage_global_quote",
                "alpha_vantage_global_quote",
                f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=KC&apikey={AV_KEY}",
            )
        )
    out.extend(
        [
            Source("tradingview", "tradingview", "https://scanner.tradingview.com/futures/scan"),
            Source("yahoo_fallback", "yahoo", "https://query1.finance.yahoo.com/v7/finance/quote?symbols=KC=F"),
        ]
    )
    return out


SOURCE_POOLS = {
    "BTC": [
        Source("kraken", "kraken", "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"),
        Source("binance", "binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"),
        Source("coingecko", "coingecko", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"),
    ],
    "COFFEE": _coffee_sources(),
}


def log_price_to_db(market: str, source: str, price: float, latency_ms: float):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO price_history (market, source, price, latency) VALUES (?, ?, ?, ?)",
        (market, source, price, latency_ms),
    )
    conn.commit()
    conn.close()


class PreflightManager:
    def __init__(self, pool_map=SOURCE_POOLS):
        self.pool_map = pool_map
        self.timeout = 4.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        }
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_json(self, url: str):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            code = response.getcode()
            body = response.read().decode("utf-8")
        return code, json.loads(body)

    def _post_json(self, url: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={**self.headers, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            code = response.getcode()
            resp_body = response.read().decode("utf-8")
        return code, json.loads(resp_body)

    def _load_cache(self) -> dict:
        if not CACHE_PATH.exists():
            return {}
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cache_entry(self, market: str, payload: dict) -> None:
        cache = self._load_cache()
        cache[market] = payload
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def _cached_fallback(self, market: str) -> Optional[dict]:
        entry = self._load_cache().get(market)
        if not entry:
            return None
        return {
            "source": f"cache:{entry.get('source','unknown')}",
            "price": entry.get("price"),
            "latency": 0.0,
            "status": "CACHED",
            "cached_at": entry.get("ts"),
        }

    def fetch_price(self, source: Source) -> dict:
        try:
            t0 = time.time()
            if source.type == "tradingview":
                payload = {"symbols": {"tickers": ["ICEUS:KC1!"]}, "columns": ["close"]}
                code, data = self._post_json(source.url, payload)
                latency = (time.time() - t0) * 1000
                if code == 200:
                    row = data.get("data", [])
                    if row and row[0].get("d"):
                        return {"source": source.name, "price": float(row[0]["d"][0]), "latency": latency, "status": "OK"}
                return {"source": source.name, "latency": latency, "status": f"HTTP_{code}"}

            code, data = self._get_json(source.url)
            latency = (time.time() - t0) * 1000
            if code != 200:
                return {"source": source.name, "latency": latency, "status": f"HTTP_{code}"}

            price = None
            if source.type == "alpha_vantage_global_quote":
                price = float(data.get("Global Quote", {}).get("05. price", 0) or 0)
            elif source.type == "yahoo":
                result = data.get("quoteResponse", {}).get("result", [])
                if result:
                    price = float(result[0].get("regularMarketPrice", 0) or 0)
            elif source.type == "binance":
                price = float(data.get("price", 0) or 0)
            elif source.type == "kraken":
                pair_data = data.get("result", {}).get("XXBTZUSD", [])
                if pair_data:
                    price = float(pair_data[-1][4])
            elif source.type == "coingecko":
                price = float(data.get("bitcoin", {}).get("usd", 0) or 0)

            if price is None or price <= 0:
                return {"source": source.name, "latency": latency, "status": "PARSE_ERROR"}
            return {"source": source.name, "price": price, "latency": latency, "status": "OK"}

        except urllib.error.HTTPError as exc:
            return {"source": source.name, "status": f"HTTP_{exc.code}", "error": str(exc)}
        except Exception as exc:
            return {"source": source.name, "status": "EXCEPTION", "error": str(exc)}

    def probe_market(self, market: str):
        pools = self.pool_map.get(market, [])
        results = []
        for source in pools:
            result = self.fetch_price(source)
            results.append(result)
            if result.get("status") == "OK":
                log_price_to_db(market, result["source"], result["price"], result["latency"])
                self._save_cache_entry(
                    market,
                    {
                        "source": result["source"],
                        "price": result["price"],
                        "latency": result.get("latency", 0),
                        "ts": int(time.time()),
                    },
                )
            time.sleep(0.3)

        good = [r for r in results if r.get("status") == "OK"]
        if not good:
            cached = self._cached_fallback(market)
            if cached:
                good = [cached]
                results.append(cached)

        return good, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IrsanAI source preflight")
    parser.add_argument("--market", choices=["BTC", "COFFEE", "ALL"], default="ALL")
    args = parser.parse_args()

    print("--- IrsanAI Preflight (AlphaVantage+Fallbacks) ---")
    if not AV_KEY:
        print("NOTE: ALPHAVANTAGE_KEY not set; COFFEE uses fallbacks only.")

    targets = ["BTC", "COFFEE"] if args.market == "ALL" else [args.market]
    pm = PreflightManager()
    for market in targets:
        good, all_res = pm.probe_market(market)
        print(f"\nMarket: {market} ({len(good)}/{len(all_res)} usable)")
        print(json.dumps(all_res, indent=2, default=str))
