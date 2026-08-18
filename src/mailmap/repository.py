from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from mailmap.fixtures import synthetic_messages
from mailmap.model import DATASET_VERSION, Intencion, Rubro, SyntheticMessage

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            labels_json TEXT NOT NULL,
            gmail_category TEXT NOT NULL,
            authenticated_domain TEXT,
            list_id TEXT,
            unsubscribe_method TEXT,
            dkim_pass INTEGER NOT NULL,
            dmarc_pass INTEGER NOT NULL,
            brand_hint TEXT,
            rubro_hint TEXT,
            flow_hint TEXT,
            personal_signal INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL,
            failure_state TEXT,
            fixture_tags_json TEXT NOT NULL,
            revision INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_received_at ON messages(received_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sender_email ON messages(sender_email);
        CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            selection_json TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """,
    ),
)


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()
        self._seed_if_needed()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                int(row[0])
                for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
            }
            for version, script in MIGRATIONS:
                if version in applied:
                    continue
                connection.executescript(script)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, datetime.now().astimezone().isoformat()),
                )

    def _seed_if_needed(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_meta WHERE key = 'dataset_version'"
            ).fetchone()
            if row and row[0] == DATASET_VERSION:
                return
            connection.execute("DELETE FROM plans")
            connection.execute("DELETE FROM messages")
            self._insert_messages(connection, synthetic_messages())
            connection.execute(
                "INSERT INTO app_meta(key, value) VALUES ('dataset_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (DATASET_VERSION,),
            )
            connection.execute(
                "INSERT INTO app_meta(key, value) VALUES ('mode', 'synthetic') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )

    def _insert_messages(
        self, connection: sqlite3.Connection, messages: Iterable[SyntheticMessage]
    ) -> None:
        connection.executemany(
            """
            INSERT INTO messages(
                id, thread_id, received_at, sender_name, sender_email, subject,
                labels_json, gmail_category, authenticated_domain, list_id,
                unsubscribe_method, dkim_pass, dmarc_pass, brand_hint, rubro_hint,
                flow_hint, personal_signal, size_bytes, failure_state,
                fixture_tags_json, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    message.id,
                    message.thread_id,
                    message.received_at.isoformat(),
                    message.sender_name,
                    message.sender_email,
                    message.subject,
                    json.dumps(message.labels, ensure_ascii=False),
                    message.gmail_category,
                    message.authenticated_domain,
                    message.list_id,
                    message.unsubscribe_method,
                    int(message.dkim_pass),
                    int(message.dmarc_pass),
                    message.brand_hint,
                    message.rubro_hint.value if message.rubro_hint else None,
                    message.flow_hint.value if message.flow_hint else None,
                    int(message.personal_signal),
                    message.size_bytes,
                    message.failure_state,
                    json.dumps(message.fixture_tags, ensure_ascii=False),
                    message.revision,
                )
                for message in messages
            ],
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> SyntheticMessage:
        return SyntheticMessage(
            id=str(row["id"]),
            thread_id=str(row["thread_id"]),
            received_at=datetime.fromisoformat(str(row["received_at"])),
            sender_name=str(row["sender_name"]),
            sender_email=str(row["sender_email"]),
            subject=str(row["subject"]),
            labels=tuple(json.loads(str(row["labels_json"]))),
            gmail_category=str(row["gmail_category"]),
            authenticated_domain=(
                str(row["authenticated_domain"]) if row["authenticated_domain"] else None
            ),
            list_id=str(row["list_id"]) if row["list_id"] else None,
            unsubscribe_method=(
                str(row["unsubscribe_method"]) if row["unsubscribe_method"] else None
            ),
            dkim_pass=bool(row["dkim_pass"]),
            dmarc_pass=bool(row["dmarc_pass"]),
            brand_hint=str(row["brand_hint"]) if row["brand_hint"] else None,
            rubro_hint=Rubro(str(row["rubro_hint"])) if row["rubro_hint"] else None,
            flow_hint=Intencion(str(row["flow_hint"])) if row["flow_hint"] else None,
            personal_signal=bool(row["personal_signal"]),
            size_bytes=int(row["size_bytes"]),
            failure_state=str(row["failure_state"]) if row["failure_state"] else None,
            fixture_tags=tuple(json.loads(str(row["fixture_tags_json"]))),
            revision=int(row["revision"]),
        )

    def messages(self) -> tuple[SyntheticMessage, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages ORDER BY received_at DESC, id ASC"
            ).fetchall()
        return tuple(self._message_from_row(row) for row in rows)

    def message(self, message_id: str) -> SyntheticMessage | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
        return self._message_from_row(row) if row else None

    def update_labels(self, message_id: str, labels: tuple[str, ...]) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE messages SET labels_json = ?, revision = revision + 1 WHERE id = ?",
                (json.dumps(labels, ensure_ascii=False), message_id),
            )
            if updated.rowcount != 1:
                raise KeyError(message_id)

    def save_plan(
        self,
        *,
        plan_id: str,
        created_at: str,
        selection: dict[str, Any],
        snapshot: dict[str, Any],
        status: str = "simulated",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plans(id, created_at, selection_json, snapshot_json, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    created_at = excluded.created_at,
                    selection_json = excluded.selection_json,
                    snapshot_json = excluded.snapshot_json,
                    status = excluded.status
                """,
                (
                    plan_id,
                    created_at,
                    json.dumps(selection, ensure_ascii=False, sort_keys=True),
                    json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                    status,
                ),
            )

    def plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "createdAt": str(row["created_at"]),
            "selection": json.loads(str(row["selection_json"])),
            "snapshot": json.loads(str(row["snapshot_json"])),
            "status": str(row["status"]),
        }

    def plans(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM plans ORDER BY created_at DESC").fetchall()
        return [plan for row in rows if (plan := self.plan(str(row["id"]))) is not None]

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
