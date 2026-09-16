from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from acacium.schemas import ReviewRequest, ReviewStatus, Run, RunStatus, Signal


class ReviewStore:
    """Persists review decisions, run state and completed evidence snapshots locally."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._lock = RLock()
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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_runs (
                run_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extracted_signals (
                signal_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(run_id, signal_id),
                FOREIGN KEY(run_id) REFERENCES extraction_runs(run_id)
            )
            """
        )
        self._migrate_signal_snapshot_key()
        self._connection.commit()

    def apply(self, signals: list[Signal]) -> list[Signal]:
        with self._lock:
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
        with self._lock:
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

    def load_runs(self) -> list[Run]:
        with self._lock:
            runs = [
                Run.model_validate_json(row[0])
                for row in self._connection.execute("SELECT payload_json FROM extraction_runs")
            ]
            for run in runs:
                if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
                    run.status = RunStatus.FAILED
                    run.error = "Local process restarted before extraction completed."
                    run.completed_at = datetime.now(UTC)
                    self._save_run(run)
            self._connection.commit()
        return runs

    def save_run(self, run: Run) -> None:
        with self._lock:
            self._save_run(run)
            self._connection.commit()

    def replace_signals(self, run_id: str, signals: list[Signal]) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM extracted_signals WHERE run_id = ?", (run_id,))
            self._connection.executemany(
                """
                INSERT INTO extracted_signals (signal_id, run_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, signal_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    created_at = excluded.created_at
                """,
                [
                    (signal.id, run_id, signal.model_dump_json(), datetime.now(UTC).isoformat())
                    for signal in signals
                ],
            )
            self._connection.commit()

    def load_signals(self, run_id: str) -> list[Signal]:
        with self._lock:
            signals = [
                Signal.model_validate_json(row[0])
                for row in self._connection.execute(
                    "SELECT payload_json FROM extracted_signals WHERE run_id = ?", (run_id,)
                )
            ]
        return self.apply(signals)

    def update_signal(self, signal: Signal) -> None:
        with self._lock:
            self._connection.execute(
                "UPDATE extracted_signals SET payload_json = ? WHERE signal_id = ?",
                (signal.model_dump_json(), signal.id),
            )
            self._connection.commit()

    def _save_run(self, run: Run) -> None:
        self._connection.execute(
            """
            INSERT INTO extraction_runs (run_id, payload_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (run.id, run.model_dump_json(), datetime.now(UTC).isoformat()),
        )

    def _migrate_signal_snapshot_key(self) -> None:
        primary_key_columns = {
            row[1]: row[5]
            for row in self._connection.execute("PRAGMA table_info(extracted_signals)")
        }
        if primary_key_columns.get("signal_id") != 1 or primary_key_columns.get("run_id"):
            return
        self._connection.execute(
            """
            CREATE TABLE extracted_signals_v2 (
                signal_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(run_id, signal_id),
                FOREIGN KEY(run_id) REFERENCES extraction_runs(run_id)
            )
            """
        )
        self._connection.execute(
            """
            INSERT INTO extracted_signals_v2 (signal_id, run_id, payload_json, created_at)
            SELECT signal_id, run_id, payload_json, created_at FROM extracted_signals
            """
        )
        self._connection.execute("DROP TABLE extracted_signals")
        self._connection.execute("ALTER TABLE extracted_signals_v2 RENAME TO extracted_signals")

    def close(self) -> None:
        with self._lock:
            self._connection.close()
