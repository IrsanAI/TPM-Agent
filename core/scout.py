#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("IRSANAI_DB_PATH", os.path.join(BASE_DIR, "data", "irsanai_production.db"))


class IrsanAIScout:
    def __init__(self):
        self.db = DB_PATH
        self.agents = ["BTC", "COFFEE"]
        self.init_fitness_table()

    def init_fitness_table(self):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_fitness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_name TEXT NOT NULL,
                fitness_score REAL NOT NULL,
                success_rate REAL,
                avg_latency REAL,
                uptime_hours REAL,
                last_price REAL,
                hivemind_eligible BOOLEAN
            )
            """
        )
        conn.commit()
        conn.close()

    def get_agent_metrics(self, agent):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("SELECT COUNT(*) FROM price_history WHERE market=? AND timestamp > ?", (agent, cutoff))
        writes = cur.fetchone()[0]

        expected_writes = 100
        success_rate = min(100.0, (writes / expected_writes) * 100)

        cur.execute("SELECT AVG(latency) FROM price_history WHERE market=? AND latency IS NOT NULL", (agent,))
        avg_latency = cur.fetchone()[0] or 999

        cur.execute("SELECT MIN(timestamp) FROM price_history WHERE market=?", (agent,))
        first_ts = cur.fetchone()[0]
        if first_ts:
            first_dt = datetime.strptime(first_ts, "%Y-%m-%d %H:%M:%S")
            uptime_hours = (datetime.now() - first_dt).total_seconds() / 3600
        else:
            uptime_hours = 0

        cur.execute("SELECT price FROM price_history WHERE market=? ORDER BY timestamp DESC LIMIT 1", (agent,))
        row = cur.fetchone()
        last_price = row[0] if row else 0

        cur.execute("SELECT (strftime('%s','now') - strftime('%s', MAX(timestamp))) FROM price_history WHERE market=?", (agent,))
        db_age = cur.fetchone()[0] or 999

        conn.close()
        return {
            "writes": writes,
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "uptime_hours": uptime_hours,
            "last_price": last_price,
            "db_age": db_age,
        }

    @staticmethod
    def calculate_fitness(metrics):
        sr_score = metrics["success_rate"] * 0.4
        latency_score = max(0, 30 - (metrics["avg_latency"] / 1000 * 30))
        fresh_score = max(0, 20 - (metrics["db_age"] / 180 * 20))
        uptime_score = min(10, metrics["uptime_hours"] * 10)
        return round(sr_score + latency_score + fresh_score + uptime_score, 1)

    def assess_agent(self, agent):
        metrics = self.get_agent_metrics(agent)
        fitness = self.calculate_fitness(metrics)
        hivemind_eligible = fitness > 60

        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_fitness
            (agent_name, fitness_score, success_rate, avg_latency, uptime_hours, last_price, hivemind_eligible)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent,
                fitness,
                metrics["success_rate"],
                metrics["avg_latency"],
                metrics["uptime_hours"],
                metrics["last_price"],
                hivemind_eligible,
            ),
        )
        conn.commit()
        conn.close()

        return {"agent": agent, "fitness": fitness, "metrics": metrics, "hivemind": hivemind_eligible}

    def dashboard(self):
        print("\n" + "=" * 60)
        print("     🔍 IrsanAI Scout Dashboard")
        print("=" * 60)
        print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        for agent in self.agents:
            result = self.assess_agent(agent)
            m = result["metrics"]
            if result["fitness"] > 60:
                status = "🟢 HEALTHY"
            elif result["fitness"] > 30:
                status = "🟡 DEGRADED"
            else:
                status = "🔴 CRITICAL"
            print(f"Agent: {agent}")
            print(f"  Status: {status}")
            print(f"  Fitness: {result['fitness']}/100")
            print(f"  Uptime: {m['uptime_hours']:.1f} hours")
            print(f"  Success Rate: {m['success_rate']:.1f}% ({m['writes']} writes/hour)")
            print(f"  Avg Latency: {m['avg_latency']:.0f}ms")
            print(f"  DB Age: {m['db_age']}s")
            print(f"  Last Price: ${m['last_price']:.2f}")
            print(f"  → HIVEMIND: {'✅ YES' if result['hivemind'] else '❌ NO'}\n")


if __name__ == "__main__":
    IrsanAIScout().dashboard()
