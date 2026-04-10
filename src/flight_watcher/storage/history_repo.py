from __future__ import annotations

import json
from datetime import UTC, datetime
import sqlite3

from flight_watcher.domain.models import FlightOption


class HistoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def start_run(self, watcher_id: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO watcher_runs(watcher_id, run_at, status) VALUES(?, ?, 'ok')",
            (watcher_id, datetime.now(UTC).isoformat()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str = "ok", message: str | None = None) -> None:
        self.conn.execute("UPDATE watcher_runs SET status=?, message=? WHERE id=?", (status, message, run_id))
        self.conn.commit()

    def insert_snapshots(self, run_id: int, watcher_id: str, options: list[FlightOption]) -> int:
        inserted = 0
        for option in options:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO price_snapshots(
                    watcher_run_id, watcher_id, checked_at, departure_date, return_date,
                    price, currency, duration_min, stops, airline_summary, fingerprint, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    watcher_id,
                    option.searched_at.isoformat(),
                    option.departure_date,
                    option.return_date,
                    option.total_price,
                    option.currency,
                    option.total_duration_min,
                    option.stops,
                    ",".join(option.airlines),
                    option.fingerprint,
                    json.dumps(option.model_dump(mode="json"), sort_keys=True),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        self.conn.commit()
        return inserted

    def latest_price(self, watcher_id: str) -> float | None:
        row = self.conn.execute(
            "SELECT price FROM price_snapshots WHERE watcher_id=? ORDER BY checked_at DESC LIMIT 1",
            (watcher_id,),
        ).fetchone()
        return float(row["price"]) if row else None

    def previous_best_price(self, watcher_id: str, before_run_id: int | None = None) -> float | None:
        if before_run_id is not None:
            row = self.conn.execute(
                """
                SELECT MIN(price) AS best_price
                FROM price_snapshots
                WHERE watcher_id=? AND watcher_run_id < ?
                """,
                (watcher_id, before_run_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT MIN(price) AS best_price FROM price_snapshots WHERE watcher_id=?",
                (watcher_id,),
            ).fetchone()
        if not row or row["best_price"] is None:
            return None
        return float(row["best_price"])

    def alert_sent(self, watcher_id: str, fingerprint: str, alert_type: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM alerts_sent WHERE watcher_id=? AND fingerprint=? AND alert_type=? LIMIT 1",
            (watcher_id, fingerprint, alert_type),
        ).fetchone()
        return row is not None

    def mark_alert_sent(self, watcher_id: str, fingerprint: str, alert_type: str, details: dict | None = None) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO alerts_sent(watcher_id, fingerprint, alert_type, sent_at, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                watcher_id,
                fingerprint,
                alert_type,
                datetime.now(UTC).isoformat(),
                json.dumps(details or {}, sort_keys=True),
            ),
        )
        self.conn.commit()
