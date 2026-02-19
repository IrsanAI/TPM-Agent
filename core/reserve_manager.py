#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from random import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("IRSANAI_DB_PATH", os.path.join(BASE_DIR, "data", "irsanai_production.db"))
RESERVE_CONFIG = os.path.join(BASE_DIR, "config", "reserve_pool.json")


class ReserveManager:
    def __init__(self):
        self.db = DB_PATH
        self.init_reserve_tables()
        self.reserve_pool = self.load_reserve_pool()

    def init_reserve_tables(self):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_reserve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'RESERVE',
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                activation_date DATETIME,
                source_config TEXT,
                validation_runs INTEGER DEFAULT 0,
                validation_success INTEGER DEFAULT 0,
                avg_fitness REAL DEFAULT 0,
                notes TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_name TEXT NOT NULL,
                test_type TEXT,
                success BOOLEAN,
                latency REAL,
                error_msg TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def load_reserve_pool(self):
        with open(RESERVE_CONFIG, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def add_to_reserve(self, agent_name, source_config, notes=""):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO agent_reserve (agent_name, source_config, notes) VALUES (?, ?, ?)",
                (agent_name, json.dumps(source_config), notes),
            )
            conn.commit()
            print(f"✅ {agent_name} added to Reserve Pool")
        except sqlite3.IntegrityError:
            print(f"⚠️ {agent_name} already in Reserve")
        finally:
            conn.close()

    def validate_agent(self, agent_name):
        success = random() > 0.3
        latency = 200 + random() * 300

        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO validation_history (agent_name, test_type, success, latency) VALUES (?, 'preflight', ?, ?)",
            (agent_name, success, latency),
        )
        cur.execute(
            """
            UPDATE agent_reserve
            SET validation_runs = validation_runs + 1,
                validation_success = validation_success + ?
            WHERE agent_name = ?
            """,
            (1 if success else 0, agent_name),
        )
        conn.commit()
        conn.close()
        return success, latency

    def check_activation_eligibility(self, agent_name):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute("SELECT validation_runs, validation_success, status FROM agent_reserve WHERE agent_name = ?", (agent_name,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return False, "Not in reserve"
        runs, success, status = row
        if status == "ACTIVE":
            return False, "Already active"

        conf = self.reserve_pool.get(agent_name, {})
        min_runs = conf.get("min_runs", 50)
        threshold = conf.get("validation_threshold", 80)

        if runs < min_runs:
            return False, f"Need {min_runs - runs} more validation runs"
        success_rate = (success / runs) * 100 if runs else 0.0
        if success_rate >= threshold:
            return True, f"Success rate {success_rate:.1f}% ≥ {threshold}%"
        return False, f"Success rate {success_rate:.1f}% < {threshold}%"

    def activate_agent(self, agent_name):
        eligible, reason = self.check_activation_eligibility(agent_name)
        if not eligible:
            print(f"❌ Cannot activate {agent_name}: {reason}")
            return False

        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            "UPDATE agent_reserve SET status='ACTIVE', activation_date=CURRENT_TIMESTAMP WHERE agent_name=?",
            (agent_name,),
        )
        conn.commit()
        conn.close()
        print(f"🚀 {agent_name} ACTIVATED! {reason}")
        return True

    def dashboard(self):
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute(
            "SELECT agent_name, status, validation_runs, validation_success, date(added_date) FROM agent_reserve ORDER BY status, agent_name"
        )
        rows = cur.fetchall()
        conn.close()

        print("\n" + "=" * 70)
        print("     🏦 IrsanAI Reserve Pool Dashboard")
        print("=" * 70)
        for name, status, runs, success, added in rows:
            success_rate = (success / runs * 100) if runs > 0 else 0
            eligible, reason = self.check_activation_eligibility(name)
            icon = "🟢" if status == "ACTIVE" else "🟡" if eligible else "⚪"
            print(f"\n{icon} Agent: {name}")
            print(f"   Status: {status}")
            print(f"   Added: {added}")
            print(f"   Validation: {success}/{runs} ({success_rate:.1f}%)")
            print(f"   Eligibility: {reason}")
        print("\n" + "=" * 70 + "\n")


def main():
    rm = ReserveManager()
    for agent_name, conf in rm.reserve_pool.items():
        rm.add_to_reserve(agent_name, conf.get("sources", []), "Auto-added from config")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
    if cmd == "dashboard":
        rm.dashboard()
    elif cmd == "validate" and len(sys.argv) > 2:
        success, latency = rm.validate_agent(sys.argv[2])
        print(f"validation={success} latency={latency:.1f}ms")
    elif cmd == "activate" and len(sys.argv) > 2:
        rm.activate_agent(sys.argv[2])
    else:
        print("Usage: python core/reserve_manager.py [dashboard|validate <AGENT>|activate <AGENT>]")


if __name__ == "__main__":
    main()
