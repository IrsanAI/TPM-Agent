#!/usr/bin/env python3
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("IRSANAI_DB_PATH", os.path.join(BASE_DIR, "data", "irsanai_production.db"))

SCHEMA = {
    "price_history": """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            market TEXT NOT NULL,
            source TEXT NOT NULL,
            price REAL NOT NULL,
            latency REAL,
            quality_score REAL DEFAULT 1.0
        )
    """,
    "agent_status": """
        CREATE TABLE IF NOT EXISTS agent_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            pid INTEGER,
            restarts INTEGER DEFAULT 0,
            last_error TEXT
        )
    """,
    "performance_metrics": """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL
        )
    """,
    "system_events": """
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            agent_name TEXT,
            details TEXT
        )
    """,
}


def column_names(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def recreate_table(cursor: sqlite3.Cursor, table_name: str, ddl: str):
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(ddl)


def init_db_v2() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for ddl in SCHEMA.values():
        cur.execute(ddl)

    # Selbstheilung für alte, inkonsistente Alt-Schemata.
    if "agent_name" not in column_names(cur, "agent_status"):
        recreate_table(cur, "agent_status", SCHEMA["agent_status"])
    if not {"agent_name", "metric_type", "value"}.issubset(column_names(cur, "performance_metrics")):
        recreate_table(cur, "performance_metrics", SCHEMA["performance_metrics"])
    if "event_type" not in column_names(cur, "system_events"):
        recreate_table(cur, "system_events", SCHEMA["system_events"])

    cur.execute("CREATE INDEX IF NOT EXISTS idx_price_market ON price_history(market, timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_status(agent_name, timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics ON performance_metrics(agent_name, timestamp)")

    conn.commit()
    conn.close()
    print(f"✅ DB v2 initialized: {DB_PATH}")
    print("📊 Tables: price_history, agent_status, performance_metrics, system_events")


if __name__ == "__main__":
    init_db_v2()
