from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from acacium.schemas import ReviewRequest, ReviewStatus, Signal


class ReviewStore:
    """Keeps review decisions separate from immutable extracted evidence."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_decisions (
                signal_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def apply(self, signals: list[Signal]) -> list[Signal]:
        decisions = {
            row[0]: (ReviewStatus(row[1]), row[2])
            for row in self._connection.execute(
                "SELECT signal_id, status, reason FROM review_decisions"
            )
        }
        for signal in signals:
            decision = decisions.get(signal.id)
            if decision is not None:
                signal.review_status, signal.review_reason = decision
        return signals

    def save(self, signal_id: str, request: ReviewRequest) -> None:
        self._connection.execute(
            """
            INSERT INTO review_decisions (signal_id, status, reason, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(signal_id) DO UPDATE SET
                status = excluded.status,
                reason = excluded.reason,
                updated_at = excluded.updated_at
            """,
            (signal_id, request.decision.value, request.reason, datetime.now(UTC).isoformat()),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
