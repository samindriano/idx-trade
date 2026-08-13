from __future__ import annotations

import sqlite3
import threading
from typing import Final

from .snapshot import AppendResult, PortfolioSnapshot
from .types import SnapshotCompleteness

_TABLE: Final = "personal_portfolio_snapshots"


class SqlitePortfolioSnapshotStore:
    """Reference atomic append-only store for offline contract validation.

    A deployed implementation must preserve these uniqueness/immutability semantics
    in a private encrypted-at-rest storage layer. This reference class is not an
    authorization to persist real provider data in an unencrypted SQLite file.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = threading.RLock()
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    @classmethod
    def in_memory(cls) -> "SqlitePortfolioSnapshotStore":
        return cls(sqlite3.connect(":memory:", check_same_thread=False))

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    scope_ref TEXT NOT NULL,
                    history_dedup_key TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL UNIQUE,
                    snapshot_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    completeness TEXT NOT NULL CHECK (completeness IN ('COMPLETE', 'PARTIAL')),
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (scope_ref, history_dedup_key)
                );
                CREATE TRIGGER IF NOT EXISTS {_TABLE}_no_update
                BEFORE UPDATE ON {_TABLE}
                BEGIN
                    SELECT RAISE(ABORT, 'personal portfolio history is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS {_TABLE}_no_delete
                BEFORE DELETE ON {_TABLE}
                BEGIN
                    SELECT RAISE(ABORT, 'personal portfolio history is append-only');
                END;
                """
            )

    def append_if_new(self, snapshot: PortfolioSnapshot) -> AppendResult:
        payload_json = snapshot.canonical_json()
        dedup_key = snapshot.history_dedup_key()
        snapshot_id = snapshot.snapshot_id()
        with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    f"""INSERT OR IGNORE INTO {_TABLE}
                    (scope_ref, history_dedup_key, snapshot_id, snapshot_at, fetched_at, completeness, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snapshot.scope_ref,
                        dedup_key,
                        snapshot_id,
                        snapshot.snapshot_at.isoformat(),
                        snapshot.fetched_at.isoformat(),
                        snapshot.completeness.value,
                        payload_json,
                    ),
                )
                inserted = cursor.rowcount == 1
                row = cursor.execute(
                    f"SELECT snapshot_id FROM {_TABLE} WHERE scope_ref=? AND history_dedup_key=?",
                    (snapshot.scope_ref, dedup_key),
                ).fetchone()
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise
            finally:
                cursor.close()
        return AppendResult(inserted, row[0], dedup_key)

    def latest_observation(self, scope_ref: str) -> PortfolioSnapshot | None:
        return self._read_latest(scope_ref, complete_only=False)

    def latest_complete(self, scope_ref: str) -> PortfolioSnapshot | None:
        """Return last-good complete state; newer PARTIAL rows never replace it."""
        return self._read_latest(scope_ref, complete_only=True)

    def _read_latest(self, scope_ref: str, *, complete_only: bool) -> PortfolioSnapshot | None:
        where = "scope_ref = ?"
        params: tuple[str, ...] = (scope_ref,)
        if complete_only:
            where += " AND completeness = ?"
            params = (scope_ref, SnapshotCompleteness.COMPLETE.value)
        with self._lock:
            row = self._connection.execute(
                f"SELECT payload_json FROM {_TABLE} WHERE {where} ORDER BY snapshot_at DESC, fetched_at DESC, rowid DESC LIMIT 1",
                params,
            ).fetchone()
        return None if row is None else PortfolioSnapshot.from_canonical_json(row[0])
