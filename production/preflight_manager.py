#!/usr/bin/env python3
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("IRSANAI_DB_PATH", os.path.join(BASE_DIR, "data", "irsanai_production.db"))
AV_KEY = os.environ.get("ALPHAVANTAGE_KEY", "UMNB8KX128R230NF")


@dataclass
class Source:
    name: str
    type: str
    url: str


SOURCE_POOLS = {
    "BTC": [
        Source("kraken", "kraken", "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"),
        Source("binance", "binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"),
        Source("coingecko", "coingecko", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"),
    ],
    "COFFEE": [
        Source("tradingview", "tradingview", "https://scanner.tradingview.com/futures/scan"),
        Source("alpha_vantage_commodity", "alpha_vantage_commodity", f"https://www.alphavantage.co/query?function=COFFEE&apikey={AV_KEY}"),
    ],
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
        self.timeout = 10.0
        self.headers = {"User-Agent": "IrsanAI-TPM/1.0", "Accept": "application/json"}

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
            if source.type == "alpha_vantage_commodity":
                val = data.get("data", [{}])[0].get("value")
                if val and val != ".":
                    price = float(val)
            elif source.type == "binance":
                price = float(data.get("price", 0))
            elif source.type == "kraken":
                pair_data = data.get("result", {}).get("XXBTZUSD", [])
                if pair_data:
                    price = float(pair_data[-1][4])
            elif source.type == "coingecko":
                price = float(data.get("bitcoin", {}).get("usd", 0))

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
            time.sleep(1.5)
        good = [r for r in results if r.get("status") == "OK"]
        return good, results


if __name__ == "__main__":
    print("--- IrsanAI Preflight (TradingView Coffee) ---")
    pm = PreflightManager()
    for market in ["BTC", "COFFEE"]:
        good, all_res = pm.probe_market(market)
        print(f"\nMarket: {market} ({len(good)}/{len(all_res)} OK)")
        print(json.dumps(all_res, indent=2, default=str))
