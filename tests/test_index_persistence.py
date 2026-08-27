from __future__ import annotations

import json
import sqlite3
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

import mailmap.repository as repository_module
from mailmap.fixtures import synthetic_messages
from mailmap.index_model import (
    INDEX_RECORD_VERSION,
    IndexedMessageRecord,
    SyncCheckpoint,
    SyncMode,
    SyncState,
)
from mailmap.model import DATASET_VERSION
from mailmap.repository import MIGRATIONS, Repository

ACCOUNT_A = "account-synthetic-a"
ACCOUNT_B = "account-synthetic-b"


def _record(
    provider_message_id: str = "message-001",
    *,
    account_key: str = ACCOUNT_A,
    received_at: datetime | None = None,
    label_ids: tuple[str, ...] = ("INBOX",),
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=provider_message_id,
        provider_thread_id=f"thread-{provider_message_id}",
        received_at=received_at or datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
        sender_name="Fuente Sintética",
        sender_address="fuente@indice.example",
        subject=f"Asunto sintético {provider_message_id}",
        label_ids=label_ids,
        category="updates",
        size_estimate_bytes=2048,
        authenticated_domain="indice.example",
        list_id="lista.indice.example",
        list_unsubscribe="https://indice.example/unsubscribe/synthetic",
        list_unsubscribe_post="List-Unsubscribe=One-Click",
        dkim_result="pass",
        dmarc_result="pass",
    )


def _checkpoint(
    *,
    account_key: str = ACCOUNT_A,
    scan_id: str = "scan-synthetic-001",
    state: SyncState = SyncState.RUNNING,
    page_token: str | None = "page-synthetic-002",
    processed_count: int = 1,
    updated_at: datetime | None = None,
) -> SyncCheckpoint:
    return SyncCheckpoint(
        account_key=account_key,
        scan_id=scan_id,
        mode=SyncMode.FULL,
        state=state,
        page_token=page_token,
        history_id="history-synthetic-001",
        processed_count=processed_count,
        started_at=datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
        updated_at=updated_at or datetime(2026, 8, 18, 12, 5, tzinfo=UTC),
        error_code=None,
    )


def _table_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }


def _columns(path: Path, table: str) -> tuple[str, ...]:
    with sqlite3.connect(path) as connection:
        return tuple(str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})"))


def _create_v1_database(path: Path) -> tuple[str, str]:
    message = synthetic_messages()[0]
    plan_id = "plan-v1-preserved"
    with sqlite3.connect(path) as connection:
        connection.executescript(MIGRATIONS[0][1])
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (1, ?)",
            (datetime(2026, 8, 18, 9, 0, tzinfo=UTC).isoformat(),),
        )
        connection.executemany(
            "INSERT INTO app_meta(key, value) VALUES (?, ?)",
            (("dataset_version", DATASET_VERSION), ("mode", "synthetic")),
        )
        connection.execute(
            """
            INSERT INTO messages(
                id, thread_id, received_at, sender_name, sender_email, subject,
                labels_json, gmail_category, authenticated_domain, list_id,
                unsubscribe_method, dkim_pass, dmarc_pass, brand_hint, rubro_hint,
                flow_hint, personal_signal, size_bytes, failure_state,
                fixture_tags_json, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
            ),
        )
        connection.execute(
            """
            INSERT INTO plans(id, created_at, selection_json, snapshot_json, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                datetime(2026, 8, 18, 9, 5, tzinfo=UTC).isoformat(),
                '{"synthetic":true}',
                '{"messageIds":[]}',
                "simulated",
            ),
        )
    return message.id, plan_id


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("account_key", ""),
        ("provider_message_id", ""),
        ("provider_thread_id", "  "),
        ("received_at", datetime(2026, 8, 18, 12, 0)),
        ("size_estimate_bytes", -1),
        ("dkim_result", "softfail"),
        ("dmarc_result", "PASS"),
        ("record_version", INDEX_RECORD_VERSION + 1),
    ),
)
def test_indexed_record_rejects_invalid_keys_dates_sizes_results_and_version(
    field: str, value: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(_record(), **{field: value})


def test_account_key_rejects_an_email_address_everywhere(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="email"):
        replace(_record(), account_key="persona@privado.example")
    with pytest.raises(ValueError, match="email"):
        replace(_checkpoint(), account_key="persona@privado.example")
    with pytest.raises(ValueError, match="email"):
        Repository(tmp_path / "index.db").indexed_messages("persona@privado.example")


def test_record_is_closed_frozen_and_normalizes_utc_and_labels() -> None:
    local_time = datetime(
        2026, 8, 18, 9, 30, tzinfo=timezone(timedelta(hours=-3))
    )
    record = _record(
        received_at=local_time,
        label_ids=("STARRED", "INBOX", "STARRED", "IMPORTANT"),
    )

    assert record.received_at == datetime(2026, 8, 18, 12, 30, tzinfo=UTC)
    assert record.label_ids == ("IMPORTANT", "INBOX", "STARRED")
    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        record.subject = "not-allowed"  # type: ignore[misc]


def test_checkpoint_validates_enums_counts_dates_states_and_codes() -> None:
    with pytest.raises(ValueError, match="SyncMode"):
        replace(_checkpoint(), mode=cast(SyncMode, "incremental"))
    with pytest.raises(ValueError, match="SyncState"):
        replace(_checkpoint(), state=cast(SyncState, "unknown_state"))
    with pytest.raises(ValueError, match="page_token"):
        replace(_checkpoint(), state=SyncState.COMPLETED)
    with pytest.raises(ValueError, match="greater than"):
        replace(_checkpoint(), processed_count=-1)
    with pytest.raises(ValueError, match="timezone"):
        replace(_checkpoint(), updated_at=datetime(2026, 8, 18, 12, 0))
    with pytest.raises(ValueError, match="controlled code"):
        replace(_checkpoint(), error_code="remote error with private text")

    resync = replace(_checkpoint(), state=SyncState.REQUIRES_FULL_RESYNC)
    assert resync.page_token is None
    assert resync.history_id == "history-synthetic-001"


def test_new_database_reaches_latest_version_with_foreign_keys_and_indexes(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "new.db")

    assert repository.schema_version() == len(MIGRATIONS)
    assert {
        "schema_migrations",
        "app_meta",
        "messages",
        "plans",
        "indexed_accounts",
        "indexed_messages",
        "sync_checkpoints",
    } <= _table_names(repository.path)
    with sqlite3.connect(repository.path) as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(indexed_messages)"
        ).fetchall()
        index_names = {
            str(row[1])
            for row in connection.execute("PRAGMA index_list(indexed_messages)")
        }
    assert any(row[2] == "indexed_accounts" and row[6] == "CASCADE" for row in foreign_keys)
    assert {
        "idx_indexed_messages_received",
        "idx_indexed_messages_thread",
        "idx_indexed_messages_sender",
    } <= index_names


def test_migration_from_v1_preserves_message_and_plan(tmp_path: Path) -> None:
    path = tmp_path / "from-v1.db"
    message_id, plan_id = _create_v1_database(path)
    fresh_path = tmp_path / "fresh.db"

    repository = Repository(path)
    Repository(fresh_path)

    assert repository.schema_version() == len(MIGRATIONS)
    assert [message.id for message in repository.messages()] == [message_id]
    assert repository.plan(plan_id) == {
        "id": plan_id,
        "createdAt": datetime(2026, 8, 18, 9, 5, tzinfo=UTC).isoformat(),
        "selection": {"synthetic": True},
        "snapshot": {"messageIds": []},
        "status": "simulated",
    }
    assert {"indexed_accounts", "indexed_messages", "sync_checkpoints"} <= _table_names(path)
    for table in ("indexed_accounts", "indexed_messages", "sync_checkpoints"):
        assert _columns(path, table) == _columns(fresh_path, table)


def test_failed_migration_rolls_back_schema_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "failed-migration.db"
    monkeypatch.setattr(repository_module, "MIGRATIONS", (MIGRATIONS[0],))
    Repository(path)
    broken_v2 = (
        2,
        "CREATE TABLE partial_marker(id INTEGER); SELECT * FROM missing_table;",
    )
    monkeypatch.setattr(repository_module, "MIGRATIONS", (MIGRATIONS[0], broken_v2))

    with pytest.raises(sqlite3.OperationalError, match="missing_table"):
        Repository(path)

    assert "partial_marker" not in _table_names(path)
    with sqlite3.connect(path) as connection:
        versions = [
            int(row[0])
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
    assert versions == [1]


def test_save_index_page_persists_records_and_checkpoint_atomically(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "atomic.db")
    record = _record(label_ids=("STARRED", "INBOX", "STARRED"))
    checkpoint = _checkpoint()

    repository.save_index_page(ACCOUNT_A, [record], checkpoint)

    assert repository.indexed_messages(ACCOUNT_A) == (record,)
    assert repository.indexed_message(ACCOUNT_A, record.provider_message_id) == record
    assert repository.sync_checkpoint(ACCOUNT_A) == checkpoint
    with sqlite3.connect(repository.path) as connection:
        stored = connection.execute(
            "SELECT received_at, label_ids_json FROM indexed_messages"
        ).fetchone()
    assert stored == (
        "2026-08-18T12:00:00+00:00",
        '["INBOX","STARRED"]',
    )


def test_checkpoint_failure_rolls_back_account_and_entire_page(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "rollback.db")
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_synthetic_checkpoint
            BEFORE INSERT ON sync_checkpoints
            BEGIN
                SELECT RAISE(ABORT, 'synthetic_checkpoint_failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic_checkpoint_failure"):
        repository.save_index_page(ACCOUNT_A, [_record()], _checkpoint())

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) is None
    with sqlite3.connect(repository.path) as connection:
        account_count = connection.execute("SELECT COUNT(*) FROM indexed_accounts").fetchone()[0]
    assert account_count == 0


def test_apply_index_page_commits_updates_deletes_and_checkpoint_together(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "atomic-delta.db")
    original_update = _record("message-update")
    original_delete = _record("message-delete")
    initial_checkpoint = _checkpoint(processed_count=2)
    repository.save_index_page(
        ACCOUNT_A,
        (original_update, original_delete),
        initial_checkpoint,
    )
    updated = replace(original_update, subject="Asunto sintético actualizado")
    added = _record("message-added")
    next_checkpoint = replace(
        initial_checkpoint,
        processed_count=5,
        page_token="page-synthetic-003",
    )

    repository.apply_index_page(
        ACCOUNT_A,
        (updated, added),
        (original_delete.provider_message_id,),
        next_checkpoint,
    )

    assert repository.indexed_messages(ACCOUNT_A) == (added, updated)
    assert repository.sync_checkpoint(ACCOUNT_A) == next_checkpoint


def test_apply_index_page_checkpoint_failure_rolls_back_updates_adds_and_deletes(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "atomic-delta-rollback.db")
    original_update = _record("message-update")
    original_delete = _record("message-delete")
    initial_checkpoint = _checkpoint(processed_count=2)
    repository.save_index_page(
        ACCOUNT_A,
        (original_update, original_delete),
        initial_checkpoint,
    )
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_synthetic_checkpoint_update
            BEFORE UPDATE ON sync_checkpoints
            BEGIN
                SELECT RAISE(ABORT, 'synthetic_checkpoint_update_failure');
            END
            """
        )

    with pytest.raises(
        sqlite3.IntegrityError, match="synthetic_checkpoint_update_failure"
    ):
        repository.apply_index_page(
            ACCOUNT_A,
            (
                replace(original_update, subject="Cambio que debe revertirse"),
                _record("message-added"),
            ),
            (original_delete.provider_message_id,),
            replace(initial_checkpoint, processed_count=5),
        )

    assert repository.indexed_messages(ACCOUNT_A) == (
        original_delete,
        original_update,
    )
    assert repository.sync_checkpoint(ACCOUNT_A) == initial_checkpoint


def test_start_full_index_replaces_only_target_account_index_and_checkpoint(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "start-full.db")
    stale = _record("message-stale")
    other = _record("message-other", account_key=ACCOUNT_B)
    repository.save_index_page(ACCOUNT_A, (stale,), _checkpoint())
    repository.save_index_page(
        ACCOUNT_B,
        (other,),
        _checkpoint(account_key=ACCOUNT_B, scan_id="scan-synthetic-b"),
    )
    full_start = replace(
        _checkpoint(),
        scan_id="scan-synthetic-replacement",
        state=SyncState.RUNNING,
        processed_count=0,
    )

    repository.start_full_index(ACCOUNT_A, full_start)

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) == full_start
    assert repository.indexed_messages(ACCOUNT_B) == (other,)


def test_start_full_index_checkpoint_failure_preserves_previous_index(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "start-full-rollback.db")
    stale = _record("message-stale")
    initial_checkpoint = _checkpoint()
    repository.save_index_page(ACCOUNT_A, (stale,), initial_checkpoint)
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_full_start_checkpoint
            BEFORE UPDATE ON sync_checkpoints
            BEGIN
                SELECT RAISE(ABORT, 'synthetic_full_start_failure');
            END
            """
        )

    full_start = replace(
        initial_checkpoint,
        scan_id="scan-synthetic-replacement",
        state=SyncState.RUNNING,
        processed_count=0,
    )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic_full_start_failure"):
        repository.start_full_index(ACCOUNT_A, full_start)

    assert repository.indexed_messages(ACCOUNT_A) == (stale,)
    assert repository.sync_checkpoint(ACCOUNT_A) == initial_checkpoint


def test_apply_index_page_rejects_overlap_before_writing(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "overlap.db")
    checkpoint = _checkpoint()

    with pytest.raises(ValueError, match="updated and deleted"):
        repository.apply_index_page(
            ACCOUNT_A,
            (_record("message-overlap"),),
            ("message-overlap",),
            checkpoint,
        )

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) is None


def test_all_input_is_validated_before_writing_and_page_duplicates_are_rejected(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "prevalidation.db")
    duplicate = _record()

    with pytest.raises(ValueError, match="duplicate"):
        repository.save_index_page(ACCOUNT_A, [duplicate, duplicate], _checkpoint())

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) is None

    with pytest.raises(ValueError, match="checkpoint account_key"):
        repository.save_index_page(
            ACCOUNT_A,
            [_record()],
            _checkpoint(account_key=ACCOUNT_B, scan_id="scan-synthetic-b"),
        )
    assert repository.indexed_messages(ACCOUNT_A) == ()


def test_retrying_the_same_page_is_idempotent(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "idempotent.db")
    record = _record()
    checkpoint = _checkpoint()

    repository.save_index_page(ACCOUNT_A, [record], checkpoint)
    repository.save_index_page(ACCOUNT_A, [record], checkpoint)

    assert repository.indexed_messages(ACCOUNT_A) == (record,)
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM indexed_messages").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM sync_checkpoints").fetchone()[0] == 1


def test_existing_identity_updates_only_its_allowed_record_fields(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "update.db")
    original = _record()
    repository.save_index_page(ACCOUNT_A, [original], _checkpoint())
    updated = replace(
        original,
        provider_thread_id="thread-message-001-updated",
        subject="Asunto sintético actualizado",
        label_ids=("IMPORTANT",),
        size_estimate_bytes=4096,
    )

    repository.save_index_page(
        ACCOUNT_A,
        [updated],
        replace(_checkpoint(), processed_count=2),
    )

    assert repository.indexed_messages(ACCOUNT_A) == (updated,)
    assert repository.indexed_message(ACCOUNT_B, updated.provider_message_id) is None


def test_index_query_order_is_received_descending_then_id_ascending(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "ordering.db")
    tie = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    records = (
        _record("message-b", received_at=tie),
        _record("message-new", received_at=tie + timedelta(minutes=1)),
        _record("message-a", received_at=tie),
    )

    repository.save_index_page(ACCOUNT_A, records, _checkpoint(processed_count=3))

    assert [record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)] == [
        "message-new",
        "message-a",
        "message-b",
    ]


def test_checkpoint_can_be_read_and_replaced_for_resume(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "resume.db")
    running = _checkpoint()
    repository.save_index_page(ACCOUNT_A, [_record()], running)

    persisted = repository.sync_checkpoint(ACCOUNT_A)
    assert persisted == running
    assert persisted is not None
    resumed = replace(
        persisted,
        state=SyncState.PAUSED,
        page_token="page-synthetic-003",
        processed_count=2,
        updated_at=datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=timezone(timedelta(hours=-3)),
        ),
    )
    repository.save_index_page(ACCOUNT_A, [_record("message-002")], resumed)

    assert repository.sync_checkpoint(ACCOUNT_A) == resumed
    assert repository.sync_checkpoint(ACCOUNT_A).updated_at == datetime(
        2026, 8, 18, 13, 0, tzinfo=UTC
    )


def test_delete_indexed_messages_is_partial_and_deduplicates_requested_ids(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "partial-delete.db")
    records = (_record("message-001"), _record("message-002"), _record("message-003"))
    repository.save_index_page(ACCOUNT_A, records, _checkpoint(processed_count=3))

    deleted = repository.delete_indexed_messages(
        ACCOUNT_A, ["message-002", "message-002", "missing-message"]
    )

    assert deleted == 1
    assert [record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)] == [
        "message-001",
        "message-003",
    ]
    assert repository.sync_checkpoint(ACCOUNT_A) is not None


def test_delete_account_index_is_isolated_and_cascades_only_that_account(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "account-delete.db")
    base_message_count = len(repository.messages())
    repository.save_plan(
        plan_id="base-plan-preserved",
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC).isoformat(),
        selection={"synthetic": True},
        snapshot={"messageIds": []},
    )
    repository.save_index_page(ACCOUNT_A, [_record()], _checkpoint())
    account_b_record = _record(account_key=ACCOUNT_B)
    repository.save_index_page(
        ACCOUNT_B,
        [account_b_record],
        _checkpoint(account_key=ACCOUNT_B, scan_id="scan-synthetic-b"),
    )

    repository.delete_account_index(ACCOUNT_A)

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) is None
    assert repository.indexed_messages(ACCOUNT_B) == (account_b_record,)
    assert repository.sync_checkpoint(ACCOUNT_B) is not None
    assert len(repository.messages()) == base_message_count
    assert repository.plan("base-plan-preserved") is not None


def test_index_schema_contains_only_explicit_contract_columns(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "columns.db")

    assert set(_columns(repository.path, "indexed_accounts")) == {"account_key"}
    assert set(_columns(repository.path, "indexed_messages")) == {
        "account_key",
        "provider_message_id",
        "provider_thread_id",
        "received_at",
        "sender_name",
        "sender_address",
        "subject",
        "label_ids_json",
        "category",
        "size_estimate_bytes",
        "authenticated_domain",
        "list_id",
        "list_unsubscribe",
        "list_unsubscribe_post",
        "dkim_result",
        "dmarc_result",
        "record_version",
    }
    assert set(_columns(repository.path, "sync_checkpoints")) == {
        "account_key",
        "scan_id",
        "mode",
        "state",
        "page_token",
        "history_id",
        "processed_count",
        "started_at",
        "updated_at",
        "error_code",
    }
    schema_text = " ".join(
        column
        for table in ("indexed_accounts", "indexed_messages", "sync_checkpoints")
        for column in _columns(repository.path, table)
    ).casefold()
    assert all(
        forbidden not in schema_text
        for forbidden in (
            "extra",
            "headers_json",
            "payload_json",
            "body",
            "html",
            "snippet",
            "mime",
            "attachment",
            "recipient",
            "token_json",
        )
    )


def test_base_segura_dataset_and_simulated_plans_remain_unchanged(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "base-regression.db")
    expected = synthetic_messages()

    assert {message.id for message in repository.messages()} == {
        message.id for message in expected
    }
    repository.save_plan(
        plan_id="simulated-plan",
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC).isoformat(),
        selection={"operations": ["archive"]},
        snapshot={"canExecute": False, "messageIds": []},
    )

    assert repository.plan("simulated-plan") == {
        "id": "simulated-plan",
        "createdAt": datetime(2026, 8, 18, 12, 0, tzinfo=UTC).isoformat(),
        "selection": {"operations": ["archive"]},
        "snapshot": {"canExecute": False, "messageIds": []},
        "status": "simulated",
    }
