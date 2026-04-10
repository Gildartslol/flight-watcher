from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS watcher_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher_id TEXT NOT NULL,
    run_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok',
    message TEXT
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher_run_id INTEGER,
    watcher_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    return_date TEXT,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    stops INTEGER NOT NULL,
    airline_summary TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    raw_json TEXT,
    UNIQUE(watcher_run_id, fingerprint),
    FOREIGN KEY(watcher_run_id) REFERENCES watcher_runs(id)
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    details_json TEXT,
    UNIQUE(watcher_id, fingerprint, alert_type)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_watcher_checked
    ON price_snapshots(watcher_id, checked_at DESC);
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = connect_db(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
