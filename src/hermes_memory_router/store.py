from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


_SCHEMA_VERSION = 1


class RouterStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._connections: set[sqlite3.Connection] = set()
        self._connections_lock = threading.Lock()
        self._migrate()

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(
                str(self.path), timeout=30, isolation_level=None, check_same_thread=False
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            self._local.connection = connection
            with self._connections_lock:
                self._connections.add(connection)
        return connection

    def _migrate(self) -> None:
        conn = self._connection()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            namespace TEXT NOT NULL,
            environment TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            checksum TEXT NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            UNIQUE(namespace, environment, kind, checksum)
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
            backend TEXT NOT NULL,
            operation TEXT NOT NULL,
            state TEXT NOT NULL,
            external_id TEXT,
            receipt_json TEXT NOT NULL DEFAULT '{}',
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at REAL NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            UNIQUE(record_id, backend, operation)
        );

        CREATE INDEX IF NOT EXISTS idx_deliveries_due
        ON deliveries(state, next_attempt_at);

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT,
            event TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        """)
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
            (str(_SCHEMA_VERSION),),
        )

    @staticmethod
    def checksum(content: str, metadata: dict[str, Any]) -> str:
        canonical = json.dumps(
            {"content": content, "metadata": metadata},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def create_record(
        self,
        *,
        namespace: str,
        environment: str,
        kind: str,
        content: str,
        metadata: dict[str, Any],
        backends: list[str],
    ) -> tuple[str, bool]:
        now = time.time()
        checksum = self.checksum(content, metadata)
        record_id = f"mr_{uuid.uuid4().hex}"
        conn = self._connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute(
                """
                SELECT id FROM records
                WHERE namespace=? AND environment=? AND kind=? AND checksum=?
                """,
                (namespace, environment, kind, checksum),
            ).fetchone()
            if existing:
                conn.execute("COMMIT")
                return str(existing["id"]), True

            conn.execute(
                """
                INSERT INTO records(
                    id, namespace, environment, kind, content, metadata_json,
                    checksum, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id, namespace, environment, kind, content,
                    json.dumps(metadata, sort_keys=True),
                    checksum, now, now,
                ),
            )
            for backend in backends:
                conn.execute(
                    """
                    INSERT INTO deliveries(
                        record_id, backend, operation, state,
                        created_at, updated_at
                    ) VALUES (?, ?, 'retain', 'pending', ?, ?)
                    """,
                    (record_id, backend, now, now),
                )
            self._audit_conn(conn, record_id, "record_created", {"backends": backends})
            conn.execute("COMMIT")
            return record_id, False
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def record(self, record_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM records WHERE id=?", (record_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json"))
        return result

    def due_deliveries(self, limit: int) -> list[dict[str, Any]]:
        now = time.time()
        rows = self._connection().execute(
            """
            SELECT d.*, r.content, r.kind, r.metadata_json, r.deleted
            FROM deliveries d
            JOIN records r ON r.id=d.record_id
            WHERE d.state IN ('pending', 'failed')
              AND d.next_attempt_at <= ?
              AND (d.operation='delete' OR r.deleted=0)
            ORDER BY d.created_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json"))
            item["receipt"] = json.loads(item.pop("receipt_json"))
            results.append(item)
        return results

    def claim(self, delivery_id: int) -> bool:
        now = time.time()
        cursor = self._connection().execute(
            """
            UPDATE deliveries
            SET state='processing', attempts=attempts+1, updated_at=?
            WHERE id=? AND state IN ('pending', 'failed')
            """,
            (now, delivery_id),
        )
        return cursor.rowcount == 1

    def complete(
        self,
        delivery_id: int,
        *,
        external_id: str | None = None,
        receipt: dict[str, Any] | None = None,
    ) -> None:
        now = time.time()
        conn = self._connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                """
                SELECT d.record_id, d.backend, d.operation, r.deleted
                FROM deliveries d
                JOIN records r ON r.id=d.record_id
                WHERE d.id=?
                """,
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            conn.execute(
                """
                UPDATE deliveries
                SET state='complete', external_id=COALESCE(?, external_id),
                    receipt_json=?, last_error=NULL, updated_at=?
                WHERE id=?
                """,
                (external_id, json.dumps(receipt or {}), now, delivery_id),
            )
            if row["operation"] == "retain" and int(row["deleted"]) == 1 and external_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO deliveries(
                        record_id, backend, operation, state, external_id,
                        receipt_json, created_at, updated_at
                    ) VALUES (?, ?, 'delete', 'pending', ?, ?, ?, ?)
                    """,
                    (
                        row["record_id"],
                        row["backend"],
                        external_id,
                        json.dumps(receipt or {}),
                        now,
                        now,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def fail(
        self,
        delivery_id: int,
        *,
        error: str,
        next_attempt_at: float,
        dead: bool = False,
    ) -> None:
        self._connection().execute(
            """
            UPDATE deliveries
            SET state=?, last_error=?, next_attempt_at=?, updated_at=?
            WHERE id=?
            """,
            (
                "dead" if dead else "failed",
                error[:4000],
                next_attempt_at,
                time.time(),
                delivery_id,
            ),
        )

    def delivery_states(self, record_id: str) -> dict[str, str]:
        rows = self._connection().execute(
            """
            SELECT backend, operation, state FROM deliveries
            WHERE record_id=? ORDER BY backend, operation
            """,
            (record_id,),
        ).fetchall()
        return {
            f"{row['backend']}:{row['operation']}": str(row["state"])
            for row in rows
        }

    def schedule_delete(self, record_id: str) -> None:
        now = time.time()
        conn = self._connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            record = conn.execute(
                "SELECT id FROM records WHERE id=?", (record_id,)
            ).fetchone()
            if not record:
                raise KeyError(record_id)
            conn.execute(
                "UPDATE records SET deleted=1, updated_at=? WHERE id=?",
                (now, record_id),
            )
            conn.execute(
                """
                UPDATE deliveries
                SET state='cancelled', updated_at=?,
                    last_error='cancelled because record was forgotten'
                WHERE record_id=? AND operation='retain'
                  AND state IN ('pending', 'failed', 'dead')
                """,
                (now, record_id),
            )
            receipts = conn.execute(
                """
                SELECT backend, external_id, receipt_json
                FROM deliveries
                WHERE record_id=? AND operation='retain' AND state='complete'
                """,
                (record_id,),
            ).fetchall()
            for receipt in receipts:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO deliveries(
                        record_id, backend, operation, state, external_id,
                        receipt_json, created_at, updated_at
                    ) VALUES (?, ?, 'delete', 'pending', ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        receipt["backend"],
                        receipt["external_id"],
                        receipt["receipt_json"],
                        now,
                        now,
                    ),
                )
            self._audit_conn(conn, record_id, "delete_scheduled", {})
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def retry_failed(self, record_id: str | None = None) -> int:
        now = time.time()
        if record_id:
            cursor = self._connection().execute(
                """
                UPDATE deliveries SET state='pending', next_attempt_at=0, updated_at=?
                WHERE state IN ('failed', 'dead') AND record_id=?
                """,
                (now, record_id),
            )
        else:
            cursor = self._connection().execute(
                """
                UPDATE deliveries SET state='pending', next_attempt_at=0, updated_at=?
                WHERE state IN ('failed', 'dead')
                """,
                (now,),
            )
        return cursor.rowcount

    def stats(self) -> dict[str, Any]:
        conn = self._connection()
        record_counts = {
            row["kind"]: row["count"]
            for row in conn.execute(
                "SELECT kind, COUNT(*) count FROM records GROUP BY kind"
            )
        }
        delivery_counts = {
            row["state"]: row["count"]
            for row in conn.execute(
                "SELECT state, COUNT(*) count FROM deliveries GROUP BY state"
            )
        }
        return {
            "schema_version": _SCHEMA_VERSION,
            "records": record_counts,
            "deliveries": delivery_counts,
            "db_path": str(self.path),
        }

    def audit(self, record_id: str | None, event: str, details: dict[str, Any]) -> None:
        self._audit_conn(self._connection(), record_id, event, details)

    @staticmethod
    def _audit_conn(
        conn: sqlite3.Connection,
        record_id: str | None,
        event: str,
        details: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_events(record_id, event, details_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (record_id, event, json.dumps(details, sort_keys=True), time.time()),
        )

    def list_records(self, *, kind: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if kind:
            rows = self._connection().execute(
                """
                SELECT id, namespace, environment, kind, deleted, created_at
                FROM records WHERE kind=? ORDER BY created_at DESC LIMIT ?
                """,
                (kind, limit),
            ).fetchall()
        else:
            rows = self._connection().execute(
                """
                SELECT id, namespace, environment, kind, deleted, created_at
                FROM records ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            try:
                connection.close()
            except sqlite3.Error:
                pass
        self._local.connection = None
