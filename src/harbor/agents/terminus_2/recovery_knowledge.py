"""Persistent, privacy-conscious storage for adaptive recovery outcomes.

Only categorical metadata is stored; raw terminal output and prompts are never
persisted by this module. The caller must opt in by configuring a database path.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from harbor.agents.terminus_2.adaptive_recovery import RecoveryRecord


class RecoveryKnowledgeStore:
    """Store recovery outcomes and summarize historical strategy reliability."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        if str(self.path) == ":memory:":
            raise ValueError("RecoveryKnowledgeStore requires a persistent file path")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    failure_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    attempts_used INTEGER NOT NULL CHECK (attempts_used >= 0),
                    succeeded INTEGER,
                    outcome TEXT,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_recovery_type_action
                ON recovery_outcomes (failure_type, action, succeeded)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def record(self, record: RecoveryRecord) -> None:
        """Persist a categorical outcome; raw evidence is intentionally omitted."""
        if record.attempts_used < 0:
            raise ValueError("attempts_used must be non-negative")
        succeeded = None if record.succeeded is None else int(record.succeeded)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO recovery_outcomes
                    (failure_type, action, attempts_used, succeeded, outcome, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.failure_type.value,
                    record.action.value,
                    record.attempts_used,
                    succeeded,
                    record.outcome,
                    record.recorded_at,
                ),
            )

    def failed_count(self, failure_type: str, action: str) -> int:
        """Return historical records where the failure signal did not clear."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count FROM recovery_outcomes
                WHERE failure_type = ? AND action = ? AND succeeded = 0
                """,
                (failure_type, action),
            ).fetchone()
        return int(row["count"])

    def summary(self) -> dict[str, Any]:
        """Return aggregate counts without exposing prompts or terminal output."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT failure_type, action,
                       COUNT(*) AS decisions,
                       SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END) AS cleared,
                       SUM(CASE WHEN succeeded = 0 THEN 1 ELSE 0 END) AS not_cleared,
                       SUM(CASE WHEN succeeded IS NULL THEN 1 ELSE 0 END) AS unresolved
                FROM recovery_outcomes
                GROUP BY failure_type, action
                ORDER BY failure_type, action
                """
            ).fetchall()
        return {
            "total_records": sum(int(row["decisions"]) for row in rows),
            "strategies": [
                {
                    "failure_type": row["failure_type"],
                    "action": row["action"],
                    "decisions": int(row["decisions"]),
                    "failure_signal_cleared": int(row["cleared"] or 0),
                    "failure_signal_not_cleared": int(row["not_cleared"] or 0),
                    "unresolved": int(row["unresolved"] or 0),
                }
                for row in rows
            ],
        }
