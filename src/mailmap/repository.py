from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from mailmap.fixtures import synthetic_messages
from mailmap.index_model import (
    IndexedMessageRecord,
    SyncCheckpoint,
    SyncMode,
    SyncState,
    validate_account_key,
    validate_opaque_identifier,
)
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
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS indexed_accounts (
            account_key TEXT PRIMARY KEY
                CHECK(length(trim(account_key)) > 0 AND instr(account_key, '@') = 0)
        );
        CREATE TABLE IF NOT EXISTS indexed_messages (
            account_key TEXT NOT NULL,
            provider_message_id TEXT NOT NULL CHECK(length(trim(provider_message_id)) > 0),
            provider_thread_id TEXT NOT NULL CHECK(length(trim(provider_thread_id)) > 0),
            received_at TEXT NOT NULL,
            sender_name TEXT,
            sender_address TEXT,
            subject TEXT,
            label_ids_json TEXT NOT NULL,
            category TEXT,
            size_estimate_bytes INTEGER NOT NULL CHECK(size_estimate_bytes >= 0),
            authenticated_domain TEXT,
            list_id TEXT,
            list_unsubscribe TEXT,
            list_unsubscribe_post TEXT,
            dkim_result TEXT CHECK(
                dkim_result IS NULL OR dkim_result IN ('pass', 'fail', 'neutral', 'unknown')
            ),
            dmarc_result TEXT CHECK(
                dmarc_result IS NULL OR dmarc_result IN ('pass', 'fail', 'neutral', 'unknown')
            ),
            record_version INTEGER NOT NULL CHECK(record_version = 1),
            PRIMARY KEY (account_key, provider_message_id),
            FOREIGN KEY (account_key) REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_received
            ON indexed_messages(account_key, received_at DESC, provider_message_id ASC);
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_thread
            ON indexed_messages(account_key, provider_thread_id);
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_sender
            ON indexed_messages(account_key, sender_address);
        CREATE TABLE IF NOT EXISTS sync_checkpoints (
            account_key TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL CHECK(length(trim(scan_id)) > 0),
            mode TEXT NOT NULL CHECK(mode IN ('full', 'partial')),
            state TEXT NOT NULL CHECK(state IN (
                'not_started', 'running', 'paused', 'completed',
                'requires_full_resync', 'failed'
            )),
            page_token TEXT,
            history_id TEXT,
            processed_count INTEGER NOT NULL CHECK(processed_count >= 0),
            started_at TEXT,
            updated_at TEXT NOT NULL,
            error_code TEXT,
            CHECK(state != 'completed' OR page_token IS NULL),
            CHECK(state != 'requires_full_resync' OR page_token IS NULL),
            FOREIGN KEY (account_key) REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
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
                connection.executescript("BEGIN IMMEDIATE;\n" + script)
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

    @staticmethod
    def _indexed_message_values(record: IndexedMessageRecord) -> tuple[object, ...]:
        return (
            record.account_key,
            record.provider_message_id,
            record.provider_thread_id,
            record.received_at.isoformat(),
            record.sender_name,
            record.sender_address,
            record.subject,
            json.dumps(record.label_ids, ensure_ascii=False, separators=(",", ":")),
            record.category,
            record.size_estimate_bytes,
            record.authenticated_domain,
            record.list_id,
            record.list_unsubscribe,
            record.list_unsubscribe_post,
            record.dkim_result,
            record.dmarc_result,
            record.record_version,
        )

    @staticmethod
    def _indexed_message_from_row(row: sqlite3.Row) -> IndexedMessageRecord:
        raw_labels = json.loads(str(row["label_ids_json"]))
        if not isinstance(raw_labels, list) or not all(
            isinstance(label, str) for label in raw_labels
        ):
            raise ValueError("Stored label_ids_json is not a string list")
        labels = tuple(label for label in raw_labels if isinstance(label, str))
        return IndexedMessageRecord(
            account_key=str(row["account_key"]),
            provider_message_id=str(row["provider_message_id"]),
            provider_thread_id=str(row["provider_thread_id"]),
            received_at=datetime.fromisoformat(str(row["received_at"])),
            sender_name=str(row["sender_name"]) if row["sender_name"] is not None else None,
            sender_address=(
                str(row["sender_address"]) if row["sender_address"] is not None else None
            ),
            subject=str(row["subject"]) if row["subject"] is not None else None,
            label_ids=labels,
            category=str(row["category"]) if row["category"] is not None else None,
            size_estimate_bytes=int(row["size_estimate_bytes"]),
            authenticated_domain=(
                str(row["authenticated_domain"])
                if row["authenticated_domain"] is not None
                else None
            ),
            list_id=str(row["list_id"]) if row["list_id"] is not None else None,
            list_unsubscribe=(
                str(row["list_unsubscribe"])
                if row["list_unsubscribe"] is not None
                else None
            ),
            list_unsubscribe_post=(
                str(row["list_unsubscribe_post"])
                if row["list_unsubscribe_post"] is not None
                else None
            ),
            dkim_result=(
                str(row["dkim_result"]) if row["dkim_result"] is not None else None
            ),
            dmarc_result=(
                str(row["dmarc_result"]) if row["dmarc_result"] is not None else None
            ),
            record_version=int(row["record_version"]),
        )

    @staticmethod
    def _checkpoint_values(checkpoint: SyncCheckpoint) -> tuple[object, ...]:
        return (
            checkpoint.account_key,
            checkpoint.scan_id,
            checkpoint.mode.value,
            checkpoint.state.value,
            checkpoint.page_token,
            checkpoint.history_id,
            checkpoint.processed_count,
            checkpoint.started_at.isoformat() if checkpoint.started_at else None,
            checkpoint.updated_at.isoformat(),
            checkpoint.error_code,
        )

    @staticmethod
    def _checkpoint_from_row(row: sqlite3.Row) -> SyncCheckpoint:
        return SyncCheckpoint(
            account_key=str(row["account_key"]),
            scan_id=str(row["scan_id"]),
            mode=SyncMode(str(row["mode"])),
            state=SyncState(str(row["state"])),
            page_token=str(row["page_token"]) if row["page_token"] is not None else None,
            history_id=str(row["history_id"]) if row["history_id"] is not None else None,
            processed_count=int(row["processed_count"]),
            started_at=(
                datetime.fromisoformat(str(row["started_at"]))
                if row["started_at"] is not None
                else None
            ),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            error_code=str(row["error_code"]) if row["error_code"] is not None else None,
        )

    def save_index_page(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        checkpoint: SyncCheckpoint,
    ) -> None:
        self.apply_index_page(account_key, records, (), checkpoint)

    def apply_index_page(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        deleted_message_ids: Iterable[str],
        checkpoint: SyncCheckpoint,
    ) -> None:
        validated_account_key = validate_account_key(account_key)
        if not isinstance(checkpoint, SyncCheckpoint):
            raise TypeError("checkpoint must be a SyncCheckpoint")
        validated_checkpoint = replace(checkpoint)
        if validated_checkpoint.account_key != validated_account_key:
            raise ValueError("checkpoint account_key does not match apply_index_page account_key")

        validated_records: list[IndexedMessageRecord] = []
        identities: set[str] = set()
        for record in records:
            if not isinstance(record, IndexedMessageRecord):
                raise TypeError("records must contain IndexedMessageRecord values")
            validated_record = replace(record)
            if validated_record.account_key != validated_account_key:
                raise ValueError("record account_key does not match apply_index_page account_key")
            if validated_record.provider_message_id in identities:
                raise ValueError("records contains a duplicate provider_message_id")
            identities.add(validated_record.provider_message_id)
            validated_records.append(validated_record)

        validated_deleted_ids = tuple(
            sorted(
                {
                    validate_opaque_identifier(message_id, "provider_message_id")
                    for message_id in deleted_message_ids
                }
            )
        )
        overlap = identities.intersection(validated_deleted_ids)
        if overlap:
            raise ValueError("a provider_message_id cannot be updated and deleted together")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_index_account(connection, validated_account_key)
            connection.executemany(
                "DELETE FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                [
                    (validated_account_key, message_id)
                    for message_id in validated_deleted_ids
                ],
            )
            self._upsert_index_records(connection, validated_records)
            self._upsert_checkpoint(connection, validated_checkpoint)

    def start_full_index(
        self, account_key: str, checkpoint: SyncCheckpoint
    ) -> None:
        validated_account_key = validate_account_key(account_key)
        if not isinstance(checkpoint, SyncCheckpoint):
            raise TypeError("checkpoint must be a SyncCheckpoint")
        validated_checkpoint = replace(checkpoint)
        if validated_checkpoint.account_key != validated_account_key:
            raise ValueError("checkpoint account_key does not match start_full_index account_key")
        if validated_checkpoint.mode is not SyncMode.FULL:
            raise ValueError("start_full_index requires a full checkpoint")
        if validated_checkpoint.state is not SyncState.RUNNING:
            raise ValueError("start_full_index requires a running checkpoint")
        if validated_checkpoint.processed_count != 0:
            raise ValueError("start_full_index requires processed_count zero")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_index_account(connection, validated_account_key)
            connection.execute(
                "DELETE FROM indexed_messages WHERE account_key = ?",
                (validated_account_key,),
            )
            self._upsert_checkpoint(connection, validated_checkpoint)

    @staticmethod
    def _ensure_index_account(
        connection: sqlite3.Connection, account_key: str
    ) -> None:
        connection.execute(
            "INSERT INTO indexed_accounts(account_key) VALUES (?) "
            "ON CONFLICT(account_key) DO NOTHING",
            (account_key,),
        )

    def _upsert_index_records(
        self,
        connection: sqlite3.Connection,
        records: Iterable[IndexedMessageRecord],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO indexed_messages(
                account_key, provider_message_id, provider_thread_id, received_at,
                sender_name, sender_address, subject, label_ids_json, category,
                size_estimate_bytes, authenticated_domain, list_id, list_unsubscribe,
                list_unsubscribe_post, dkim_result, dmarc_result, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_key, provider_message_id) DO UPDATE SET
                provider_thread_id = excluded.provider_thread_id,
                received_at = excluded.received_at,
                sender_name = excluded.sender_name,
                sender_address = excluded.sender_address,
                subject = excluded.subject,
                label_ids_json = excluded.label_ids_json,
                category = excluded.category,
                size_estimate_bytes = excluded.size_estimate_bytes,
                authenticated_domain = excluded.authenticated_domain,
                list_id = excluded.list_id,
                list_unsubscribe = excluded.list_unsubscribe,
                list_unsubscribe_post = excluded.list_unsubscribe_post,
                dkim_result = excluded.dkim_result,
                dmarc_result = excluded.dmarc_result,
                record_version = excluded.record_version
            """,
            [self._indexed_message_values(record) for record in records],
        )

    def _upsert_checkpoint(
        self, connection: sqlite3.Connection, checkpoint: SyncCheckpoint
    ) -> None:
        connection.execute(
            """
            INSERT INTO sync_checkpoints(
                account_key, scan_id, mode, state, page_token, history_id,
                processed_count, started_at, updated_at, error_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_key) DO UPDATE SET
                scan_id = excluded.scan_id,
                mode = excluded.mode,
                state = excluded.state,
                page_token = excluded.page_token,
                history_id = excluded.history_id,
                processed_count = excluded.processed_count,
                started_at = excluded.started_at,
                updated_at = excluded.updated_at,
                error_code = excluded.error_code
            """,
            self._checkpoint_values(checkpoint),
        )

    def indexed_messages(self, account_key: str) -> tuple[IndexedMessageRecord, ...]:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM indexed_messages WHERE account_key = ? "
                "ORDER BY received_at DESC, provider_message_id ASC",
                (validated_account_key,),
            ).fetchall()
        return tuple(self._indexed_message_from_row(row) for row in rows)

    def indexed_message(
        self, account_key: str, provider_message_id: str
    ) -> IndexedMessageRecord | None:
        validated_account_key = validate_account_key(account_key)
        validated_message_id = validate_opaque_identifier(
            provider_message_id, "provider_message_id"
        )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                (validated_account_key, validated_message_id),
            ).fetchone()
        return self._indexed_message_from_row(row) if row else None

    def sync_checkpoint(self, account_key: str) -> SyncCheckpoint | None:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sync_checkpoints WHERE account_key = ?",
                (validated_account_key,),
            ).fetchone()
        return self._checkpoint_from_row(row) if row else None

    def delete_indexed_messages(
        self, account_key: str, provider_message_ids: Iterable[str]
    ) -> int:
        validated_account_key = validate_account_key(account_key)
        validated_ids = tuple(
            sorted(
                {
                    validate_opaque_identifier(message_id, "provider_message_id")
                    for message_id in provider_message_ids
                }
            )
        )
        if not validated_ids:
            return 0
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.executemany(
                "DELETE FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                [(validated_account_key, message_id) for message_id in validated_ids],
            )
            return cursor.rowcount

    def delete_account_index(self, account_key: str) -> None:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM indexed_accounts WHERE account_key = ?",
                (validated_account_key,),
            )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
