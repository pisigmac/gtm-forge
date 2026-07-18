"""SQLite-backed local state: run history, cost ledger, breaker state, key-value store."""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    skill       TEXT NOT NULL,
    command     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',
    dry_run     INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    error       TEXT
);
CREATE TABLE IF NOT EXISTS costs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd      REAL NOT NULL,
    ts            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS breaker (
    name      TEXT PRIMARY KEY,
    state     TEXT NOT NULL DEFAULT 'closed',
    failures  INTEGER NOT NULL DEFAULT 0,
    opened_at TEXT
);
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StateStore:
    """Thread-safe wrapper over a single SQLite file. Safe for cron and CLI use."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- runs ---------------------------------------------------------------

    def start_run(self, run_id: str, skill: str, command: str, dry_run: bool) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO runs (run_id, skill, command, status, dry_run, started_at) "
                "VALUES (?, ?, ?, 'running', ?, ?)",
                (run_id, skill, command, int(dry_run), _now()),
            )

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE run_id = ?",
                (status, _now(), error, run_id),
            )

    def list_runs(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))
            return list(cur.fetchall())

    # -- costs --------------------------------------------------------------

    def record_cost(
        self, run_id: str, model: str, input_tokens: int, output_tokens: int, cost_usd: float
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO costs (run_id, model, input_tokens, output_tokens, cost_usd, ts) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, model, input_tokens, output_tokens, cost_usd, _now()),
            )

    def run_cost(self, run_id: str) -> float:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0.0) AS total FROM costs WHERE run_id = ?",
                (run_id,),
            )
            return float(cur.fetchone()["total"])

    def costs_summary(self) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT model, COUNT(*) AS calls, SUM(input_tokens) AS input_tokens, "
                "SUM(output_tokens) AS output_tokens, SUM(cost_usd) AS cost_usd "
                "FROM costs GROUP BY model ORDER BY cost_usd DESC"
            )
            return list(cur.fetchall())

    # -- circuit breaker ------------------------------------------------------

    def breaker_get(self, name: str) -> dict[str, object]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM breaker WHERE name = ?", (name,))
            row = cur.fetchone()
        if row is None:
            return {"name": name, "state": "closed", "failures": 0, "opened_at": None}
        return dict(row)

    def breaker_set(self, name: str, state: str, failures: int, opened_at: str | None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO breaker (name, state, failures, opened_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET state = excluded.state, "
                "failures = excluded.failures, opened_at = excluded.opened_at",
                (name, state, failures, opened_at),
            )

    # -- key-value ------------------------------------------------------------

    def kv_get(self, key: str) -> str | None:
        with self._lock:
            cur = self._conn.execute("SELECT value FROM kv WHERE key = ?", (key,))
            row = cur.fetchone()
        return str(row["value"]) if row else None

    def kv_set(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
