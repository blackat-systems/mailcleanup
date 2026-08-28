from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

import pytest

from mailmap.classification_domain import classify_indexed_records
from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint, SyncMode, SyncState
from mailmap.policy_domain import apply_local_policies, prepare_policy_decision
from mailmap.policy_model import (
    PolicyError,
    PolicyErrorCode,
    PolicyEvent,
    PreparedPolicyDecision,
    SetSourceDisplayName,
    UndoPolicy,
)
from mailmap.repository import (
    MAP_POLICY_REQUEST_CONTRACT_VERSION,
    MIGRATIONS,
    MapPolicyWriteResult,
    MapRepositoryError,
    MapRepositoryErrorCode,
    Repository,
)

ACCOUNT = "synthetic-map-v1"
OTHER_ACCOUNT = "synthetic-map-other"
FIXTURE_VERSION = "map-total-synthetic-v1"
NOW = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(
    message_id: str = "message-map-001",
    *,
    account_key: str = ACCOUNT,
    subject: str = "Resumen sintético",
    received_at: datetime = NOW,
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=message_id,
        provider_thread_id=f"thread-{message_id}",
        received_at=received_at,
        sender_name="Fuente Sintética",
        sender_address="avisos@fuente.example",
        subject=subject,
        label_ids=("INBOX",),
        category="updates",
        size_estimate_bytes=2048,
        authenticated_domain="fuente.example",
        list_id="boletin.fuente.example",
        list_unsubscribe="https://fuente.example/unsubscribe/synthetic",
        list_unsubscribe_post="List-Unsubscribe=One-Click",
        dkim_result="pass",
        dmarc_result="pass",
    )


def _checkpoint(
    *,
    account_key: str = ACCOUNT,
    processed_count: int = 1,
    updated_at: datetime = NOW,
) -> SyncCheckpoint:
    return SyncCheckpoint(
        account_key=account_key,
        scan_id="scan-map-synthetic",
        mode=SyncMode.FULL,
        state=SyncState.COMPLETED,
        page_token=None,
        history_id="history-map-synthetic",
        processed_count=processed_count,
        started_at=NOW - timedelta(minutes=5),
        updated_at=updated_at,
        error_code=None,
    )


def _prepared(
    records: tuple[IndexedMessageRecord, ...],
    *,
    command_id: str = "command-map-name-001",
    decision_id: str = "decision-map-name-001",
    expected_revision: int = 0,
) -> PreparedPolicyDecision:
    classification = classify_indexed_records(records)
    effective = apply_local_policies(
        ACCOUNT,
        records,
        classification,
        (),
    )
    command = SetSourceDisplayName(
        command_id=command_id,
        account_key=ACCOUNT,
        occurred_at=NOW + timedelta(minutes=expected_revision),
        expected_revision=expected_revision,
        decision_id=decision_id,
        selector=effective.sources[0].selector,
        display_name="Nombre sintético elegido",
    )
    return prepare_policy_decision(
        account_key=ACCOUNT,
        records=records,
        classification=classification,
        active_policies=(),
        command=command,
    )


def _policy_event(prepared: PreparedPolicyDecision) -> PolicyEvent:
    return PolicyEvent(
        command=prepared.command,
        account_revision=prepared.command.expected_revision + 1,
        anchors=prepared.anchors,
        relations=prepared.relations,
    )


def _installed_repository(
    path: Path,
    *,
    policy_events: tuple[PolicyEvent, ...] = (),
) -> tuple[Repository, tuple[IndexedMessageRecord, ...]]:
    repository = Repository(path)
    records = (
        _record(),
        _record(
            "message-map-002",
            subject="Segundo resumen sintético",
            received_at=NOW - timedelta(days=1),
        ),
    )
    repository.install_synthetic_map_fixture(
        ACCOUNT,
        FIXTURE_VERSION,
        records,
        _checkpoint(processed_count=len(records)),
        policy_events,
    )
    return repository, records


def _receipt_rows(path: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(
                "SELECT account_key, command_id, contract_version, "
                "request_fingerprint FROM map_policy_requests "
                "ORDER BY account_key, command_id"
            ).fetchall()
        )


def test_v4_migration_is_cumulative_typed_and_cascades_with_account(
    tmp_path: Path,
) -> None:
    path = tmp_path / "map-v4.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    result = repository.record_map_policy(
        _prepared(records),
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=_fingerprint("request-one"),
        required_fixture_version=FIXTURE_VERSION,
    )

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        columns = tuple(
            str(row[1])
            for row in connection.execute("PRAGMA table_info(map_policy_requests)")
        )
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(map_policy_requests)"
        ).fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO map_policy_requests VALUES (?, ?, ?, ?)",
                (ACCOUNT, "invalid", 1, "A" * 64),
            )

    assert repository.schema_version() == 4
    assert len(MIGRATIONS) == 4
    assert columns == (
        "account_key",
        "command_id",
        "contract_version",
        "request_fingerprint",
    )
    assert any(row[2] == "indexed_accounts" and row[6] == "CASCADE" for row in foreign_keys)
    assert any(row[2] == "local_policy_events" and row[6] == "CASCADE" for row in foreign_keys)
    assert result.event.account_revision == 1
    assert len(_receipt_rows(path)) == 1

    repository.delete_account_index(ACCOUNT)
    assert _receipt_rows(path) == ()


def test_snapshot_distinguishes_missing_empty_and_populated_accounts(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "snapshots.db")

    missing = repository.map_input_snapshot(ACCOUNT)
    assert missing.account_exists is False
    assert missing.indexed_account_keys == ()
    assert missing.fixture_version is None
    assert missing.records == ()
    assert missing.checkpoint is None
    assert missing.policy_history == ()
    assert missing.active_policies == ()
    assert missing.policy_revision == 0

    empty = repository.install_synthetic_map_fixture(
        ACCOUNT,
        FIXTURE_VERSION,
        (),
        _checkpoint(processed_count=0),
        (),
    )
    assert empty.account_exists is True
    assert empty.indexed_account_keys == (ACCOUNT,)
    assert empty.records == ()
    assert empty.checkpoint == _checkpoint(processed_count=0)

    repository.apply_index_page(
        ACCOUNT,
        (_record(),),
        (),
        _checkpoint(),
    )
    populated = repository.map_input_snapshot(ACCOUNT)
    assert populated.account_exists is True
    assert tuple(record.provider_message_id for record in populated.records) == (
        "message-map-001",
    )
    assert populated.input_revision != empty.input_revision


def test_snapshot_is_closed_frozen_redacted_and_deterministic(tmp_path: Path) -> None:
    repository, _ = _installed_repository(tmp_path / "redacted.db")
    first = repository.map_input_snapshot(ACCOUNT)
    second = Repository(repository.path).map_input_snapshot(ACCOUNT)

    assert first == second
    assert first.input_revision == second.input_revision
    assert not hasattr(first, "__dict__")
    with pytest.raises(FrozenInstanceError):
        first.policy_revision = 10  # type: ignore[misc]
    rendered = repr(first)
    assert "synthetic-map-v1" not in rendered
    assert "Fuente Sintética" not in rendered
    assert "avisos@fuente.example" not in rendered
    assert "message-map-001" not in rendered
    assert "record_count=2" in rendered
    assert "checkpoint_state='completed'" in rendered


def test_snapshot_keeps_one_sqlite_view_during_a_concurrent_index_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "snapshot-concurrent.db"
    repository, records = _installed_repository(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone()[0] == "wal"

    reader_materialized_record = Event()
    writer_finished = Event()
    original = Repository._indexed_message_from_row
    paused_once = False

    def pause_after_record(row: sqlite3.Row) -> IndexedMessageRecord:
        nonlocal paused_once
        result = original(row)
        if not paused_once:
            paused_once = True
            reader_materialized_record.set()
            assert writer_finished.wait(timeout=5)
        return result

    monkeypatch.setattr(
        Repository,
        "_indexed_message_from_row",
        staticmethod(pause_after_record),
    )

    def update_index() -> None:
        assert reader_materialized_record.wait(timeout=5)
        repository.apply_index_page(
            ACCOUNT,
            (replace(records[0], subject="Cambio posterior sintético"),),
            (),
            replace(
                _checkpoint(processed_count=2),
                updated_at=NOW + timedelta(minutes=1),
            ),
        )
        writer_finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(repository.map_input_snapshot, ACCOUNT)
        writer = pool.submit(update_index)
        snapshot = reader.result(timeout=10)
        writer.result(timeout=10)

    first = next(
        record
        for record in snapshot.records
        if record.provider_message_id == records[0].provider_message_id
    )
    assert first.subject == records[0].subject
    assert snapshot.checkpoint is not None
    assert snapshot.checkpoint.updated_at == NOW
    assert Repository(path).map_input_snapshot(ACCOUNT).input_revision != snapshot.input_revision


def test_snapshot_keeps_one_sqlite_view_during_a_concurrent_policy_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "snapshot-concurrent-policy.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    first_event = repository.record_policy(prepared)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone()[0] == "wal"

    reader_materialized_event = Event()
    writer_finished = Event()
    original = Repository._event_from_row
    paused_once = False

    def pause_after_event(
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> PolicyEvent:
        nonlocal paused_once
        result = original(connection, row)
        if not paused_once:
            paused_once = True
            reader_materialized_event.set()
            assert writer_finished.wait(timeout=5)
        return result

    monkeypatch.setattr(
        Repository,
        "_event_from_row",
        staticmethod(pause_after_event),
    )

    def update_policy() -> None:
        assert reader_materialized_event.wait(timeout=5)
        repository.undo_policy(
            UndoPolicy(
                command_id="command-concurrent-snapshot-undo",
                account_key=ACCOUNT,
                occurred_at=NOW + timedelta(minutes=1),
                expected_revision=1,
                target_decision_id=first_event.command.decision_id,
            )
        )
        writer_finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(repository.map_input_snapshot, ACCOUNT)
        writer = pool.submit(update_policy)
        snapshot = reader.result(timeout=10)
        writer.result(timeout=10)

    assert snapshot.policy_revision == 1
    assert snapshot.policy_history == (first_event,)
    assert len(snapshot.active_policies) == 1
    after = Repository(path).map_input_snapshot(ACCOUNT)
    assert after.policy_revision == 2
    assert len(after.policy_history) == 2
    assert after.active_policies == ()
    assert after.input_revision != snapshot.input_revision


def test_input_revision_covers_index_checkpoint_marker_accounts_and_policy_ledger(
    tmp_path: Path,
) -> None:
    path = tmp_path / "revision.db"
    repository, records = _installed_repository(path)
    initial = repository.map_input_snapshot(ACCOUNT)

    repository.apply_index_page(
        ACCOUNT,
        (replace(records[0], subject="Asunto sintético cambiado"),),
        (),
        replace(_checkpoint(processed_count=2), updated_at=NOW + timedelta(minutes=1)),
    )
    after_record_and_checkpoint = repository.map_input_snapshot(ACCOUNT)
    assert after_record_and_checkpoint.input_revision != initial.input_revision

    with repository._connect() as connection:
        connection.execute(
            "UPDATE app_meta SET value = ? WHERE key = 'map_fixture_version'",
            ("map-fixture-v2",),
        )
    after_marker = repository.map_input_snapshot(ACCOUNT)
    assert after_marker.input_revision != after_record_and_checkpoint.input_revision

    repository.apply_index_page(
        OTHER_ACCOUNT,
        (_record("other-message", account_key=OTHER_ACCOUNT),),
        (),
        _checkpoint(account_key=OTHER_ACCOUNT),
    )
    after_account = repository.map_input_snapshot(ACCOUNT)
    assert after_account.indexed_account_keys == tuple(sorted((ACCOUNT, OTHER_ACCOUNT)))
    assert after_account.input_revision != after_marker.input_revision

    repository.delete_account_index(OTHER_ACCOUNT)
    with repository._connect() as connection:
        connection.execute(
            "UPDATE app_meta SET value = ? WHERE key = 'map_fixture_version'",
            (FIXTURE_VERSION,),
        )
    restored = repository.map_input_snapshot(ACCOUNT)
    prepared = _prepared(restored.records)
    repository.record_policy(prepared)
    after_policy = repository.map_input_snapshot(ACCOUNT)
    assert after_policy.policy_revision == 1
    assert after_policy.input_revision != restored.input_revision


def test_policy_revision_tracks_undo_even_when_no_policy_remains(tmp_path: Path) -> None:
    path = tmp_path / "undo-revision.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    repository.record_policy(prepared)
    repository.undo_policy(
        UndoPolicy(
            command_id="command-map-undo-internal",
            account_key=ACCOUNT,
            occurred_at=NOW + timedelta(minutes=1),
            expected_revision=1,
            target_decision_id=prepared.command.decision_id,
        )
    )

    snapshot = repository.map_input_snapshot(ACCOUNT)
    assert snapshot.policy_revision == 2
    assert len(snapshot.policy_history) == 2
    assert snapshot.active_policies == ()


def test_fixture_install_is_atomic_strict_and_does_not_replace_prior_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fixture-strict.db"
    repository, records = _installed_repository(path)
    before = repository.map_input_snapshot(ACCOUNT)

    with pytest.raises(MapRepositoryError) as error:
        repository.install_synthetic_map_fixture(
            ACCOUNT,
            "replacement-v1",
            records,
            _checkpoint(processed_count=2),
            (),
        )
    assert error.value.code is MapRepositoryErrorCode.MAP_UNAVAILABLE
    assert repository.map_input_snapshot(ACCOUNT) == before

    empty_path = tmp_path / "fixture-invalid.db"
    empty = Repository(empty_path)
    with pytest.raises(MapRepositoryError) as error:
        empty.install_synthetic_map_fixture(
            ACCOUNT,
            FIXTURE_VERSION,
            (_record(account_key=OTHER_ACCOUNT),),
            _checkpoint(),
            (),
        )
    assert error.value.code is MapRepositoryErrorCode.INVALID_INPUT
    assert empty.map_input_snapshot(ACCOUNT).account_exists is False


def test_fixture_install_enforces_the_complete_synthetic_gate(tmp_path: Path) -> None:
    fixture_version = FIXTURE_VERSION
    outside_address = "probe@" + "outside.invalid"

    for name, account_key, records, checkpoint, events, expected_code in (
        (
            "outside-address",
            ACCOUNT,
            (_record(), replace(_record("outside"), sender_address=outside_address)),
            _checkpoint(processed_count=2),
            (),
            MapRepositoryErrorCode.MAP_UNAVAILABLE,
        ),
        (
            "outside-authority-url",
            ACCOUNT,
            (
                replace(
                    _record(),
                    list_unsubscribe="//outside.invalid/private",
                ),
            ),
            _checkpoint(),
            (),
            MapRepositoryErrorCode.MAP_UNAVAILABLE,
        ),
        (
            "wrong-account",
            OTHER_ACCOUNT,
            (_record(account_key=OTHER_ACCOUNT),),
            _checkpoint(account_key=OTHER_ACCOUNT),
            (),
            MapRepositoryErrorCode.MAP_UNAVAILABLE,
        ),
        (
            "unsafe-policy",
            ACCOUNT,
            (_record(),),
            _checkpoint(),
            (
                _policy_event(
                    replace(
                        _prepared((_record(),)),
                        command=replace(
                            _prepared((_record(),)).command,
                            display_name="Contacto " + outside_address,
                        ),
                    )
                ),
            ),
            MapRepositoryErrorCode.MAP_UNAVAILABLE,
        ),
    ):
        repository = Repository(tmp_path / f"gate-{name}.db")
        with pytest.raises(MapRepositoryError) as error:
            repository.install_synthetic_map_fixture(
                account_key,
                fixture_version,
                records,
                checkpoint,
                events,
            )
        assert error.value.code is expected_code
        assert repository.map_input_snapshot(ACCOUNT).account_exists is False

    repository = Repository(tmp_path / "gate-wrong-marker.db")
    with pytest.raises(MapRepositoryError) as error:
        repository.install_synthetic_map_fixture(
            ACCOUNT,
            "other-fixture-v1",
            (_record(),),
            _checkpoint(),
            (),
        )
    assert error.value.code is MapRepositoryErrorCode.MAP_UNAVAILABLE


def test_map_write_rechecks_synthetic_rows_inside_the_transaction(
    tmp_path: Path,
) -> None:
    path = tmp_path / "gate-before-write.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE indexed_messages SET subject = ? "
            "WHERE account_key = ? AND provider_message_id = ?",
            (
                "Visitá https://outside.invalid/private",
                ACCOUNT,
                records[0].provider_message_id,
            ),
        )
    changed = repository.map_input_snapshot(ACCOUNT)

    with pytest.raises(MapRepositoryError) as error:
        repository.record_map_policy(
            prepared,
            expected_input_revision=changed.input_revision,
            request_fingerprint=_fingerprint("gate-before-write"),
            required_fixture_version=FIXTURE_VERSION,
        )

    assert error.value.code is MapRepositoryErrorCode.MAP_UNAVAILABLE
    assert repository.policy_history(ACCOUNT) == ()
    assert _receipt_rows(path) == ()


def test_fixture_install_accepts_a_valid_complete_policy_sequence(tmp_path: Path) -> None:
    path = tmp_path / "fixture-policy.db"
    records = (_record(),)
    prepared = _prepared(records)
    event = _policy_event(prepared)
    repository = Repository(path)

    snapshot = repository.install_synthetic_map_fixture(
        ACCOUNT,
        FIXTURE_VERSION,
        records,
        _checkpoint(),
        (event,),
    )

    assert snapshot.policy_history == (event,)
    assert len(snapshot.active_policies) == 1
    assert snapshot.policy_revision == 1
    assert _receipt_rows(path) == ()


def test_fixture_install_rejects_non_contiguous_policy_history_without_writes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fixture-policy-invalid.db"
    records = (_record(),)
    prepared = _prepared(records)
    invalid_event = replace(
        _policy_event(prepared),
        command=replace(prepared.command, expected_revision=1),
        account_revision=2,
    )
    repository = Repository(path)

    with pytest.raises(MapRepositoryError) as error:
        repository.install_synthetic_map_fixture(
            ACCOUNT,
            FIXTURE_VERSION,
            records,
            _checkpoint(),
            (invalid_event,),
        )
    assert error.value.code is MapRepositoryErrorCode.INVALID_INPUT
    assert repository.map_input_snapshot(ACCOUNT).account_exists is False


def test_record_map_policy_persists_event_and_receipt_atomically_and_replays(
    tmp_path: Path,
) -> None:
    path = tmp_path / "record-map.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    prepared = _prepared(records)
    fingerprint = _fingerprint("canonical-public-request")

    applied = repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )
    replayed = repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )

    assert applied == MapPolicyWriteResult(event=applied.event, replayed=False)
    assert replayed.event == applied.event
    assert replayed.replayed is True
    assert len(repository.policy_history(ACCOUNT)) == 1
    assert _receipt_rows(path) == (
        (
            ACCOUNT,
            prepared.command.command_id,
            MAP_POLICY_REQUEST_CONTRACT_VERSION,
            fingerprint,
        ),
    )


def test_receipt_lookup_supports_replay_before_current_topology_resolution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lookup.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    fingerprint = _fingerprint("lookup-request")
    applied = repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )
    repository.undo_policy(
        UndoPolicy(
            command_id="command-internal-undo-before-replay",
            account_key=ACCOUNT,
            occurred_at=NOW + timedelta(minutes=1),
            expected_revision=1,
            target_decision_id=prepared.command.decision_id,
        )
    )

    lookup = repository.map_policy_replay(
        ACCOUNT,
        prepared.command.command_id,
        request_fingerprint=fingerprint,
    )
    missing = repository.map_policy_replay(
        ACCOUNT,
        "command-not-seen",
        request_fingerprint=_fingerprint("missing"),
    )

    assert lookup == MapPolicyWriteResult(event=applied.event, replayed=True)
    assert missing is None
    authoritative = repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )
    assert authoritative == MapPolicyWriteResult(event=applied.event, replayed=True)


def test_receipt_conflict_and_internal_event_collision_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "receipt-conflicts.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=_fingerprint("original"),
        required_fixture_version=FIXTURE_VERSION,
    )

    with pytest.raises(MapRepositoryError) as error:
        repository.map_policy_replay(
            ACCOUNT,
            prepared.command.command_id,
            request_fingerprint=_fingerprint("changed"),
        )
    assert error.value.code is MapRepositoryErrorCode.COMMAND_ID_CONFLICT

    internal_repository, internal_records = _installed_repository(
        tmp_path / "internal-collision.db"
    )
    second = _prepared(
        internal_records,
        command_id="command-internal-only",
        decision_id="decision-internal-only",
    )
    internal_repository.record_policy(second)
    with pytest.raises(MapRepositoryError) as error:
        internal_repository.map_policy_replay(
            ACCOUNT,
            second.command.command_id,
            request_fingerprint=_fingerprint("internal-collision"),
        )
    assert error.value.code is MapRepositoryErrorCode.COMMAND_ID_CONFLICT


def test_receipt_without_event_is_reported_as_corruption(tmp_path: Path) -> None:
    path = tmp_path / "receipt-corrupt.db"
    repository, _ = _installed_repository(path)
    fingerprint = _fingerprint("orphan-receipt")
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO map_policy_requests VALUES (?, ?, ?, ?)",
            (ACCOUNT, "command-orphan-receipt", 1, fingerprint),
        )

    with pytest.raises(MapRepositoryError) as error:
        repository.map_policy_replay(
            ACCOUNT,
            "command-orphan-receipt",
            request_fingerprint=fingerprint,
        )
    assert error.value.code is MapRepositoryErrorCode.RECEIPT_CORRUPT
    assert "command-orphan-receipt" not in repr(error.value)


def test_stale_map_revision_fixture_gate_and_policy_cas_write_nothing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cas.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    prepared = _prepared(records)

    repository.apply_index_page(
        ACCOUNT,
        (replace(records[0], subject="Cambio concurrente sintético"),),
        (),
        replace(_checkpoint(processed_count=2), updated_at=NOW + timedelta(minutes=1)),
    )
    with pytest.raises(MapRepositoryError) as error:
        repository.record_map_policy(
            prepared,
            expected_input_revision=snapshot.input_revision,
            request_fingerprint=_fingerprint("stale-map"),
            required_fixture_version=FIXTURE_VERSION,
        )
    assert error.value.code is MapRepositoryErrorCode.MAP_REVISION_CONFLICT
    assert repository.policy_history(ACCOUNT) == ()
    assert _receipt_rows(path) == ()

    current = repository.map_input_snapshot(ACCOUNT)
    with pytest.raises(MapRepositoryError) as error:
        repository.record_map_policy(
            _prepared(current.records),
            expected_input_revision=current.input_revision,
            request_fingerprint=_fingerprint("wrong-fixture"),
            required_fixture_version="other-fixture-v1",
        )
    assert error.value.code is MapRepositoryErrorCode.MAP_UNAVAILABLE
    assert repository.policy_history(ACCOUNT) == ()

    bad_policy_revision = replace(
        _prepared(current.records),
        command=replace(_prepared(current.records).command, expected_revision=1),
    )
    with pytest.raises(PolicyError) as error:
        repository.record_map_policy(
            bad_policy_revision,
            expected_input_revision=current.input_revision,
            request_fingerprint=_fingerprint("wrong-policy-revision"),
            required_fixture_version=FIXTURE_VERSION,
        )
    assert error.value.code is PolicyErrorCode.REVISION_CONFLICT
    assert repository.policy_history(ACCOUNT) == ()


def test_account_set_gate_is_rechecked_under_write_lock(tmp_path: Path) -> None:
    path = tmp_path / "account-gate.db"
    repository, records = _installed_repository(path)
    repository.apply_index_page(
        OTHER_ACCOUNT,
        (_record("other-message", account_key=OTHER_ACCOUNT),),
        (),
        _checkpoint(account_key=OTHER_ACCOUNT),
    )
    snapshot = repository.map_input_snapshot(ACCOUNT)

    with pytest.raises(MapRepositoryError) as error:
        repository.record_map_policy(
            _prepared(records),
            expected_input_revision=snapshot.input_revision,
            request_fingerprint=_fingerprint("multiple-accounts"),
            required_fixture_version=FIXTURE_VERSION,
        )
    assert error.value.code is MapRepositoryErrorCode.MAP_UNAVAILABLE
    assert repository.policy_history(ACCOUNT) == ()


def test_receipt_failure_rolls_back_the_policy_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "receipt-rollback.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)

    def fail_receipt(*args: object, **kwargs: object) -> None:
        raise sqlite3.IntegrityError("synthetic receipt failure")

    monkeypatch.setattr(
        Repository,
        "_insert_map_policy_receipt",
        staticmethod(fail_receipt),
    )
    with pytest.raises(MapRepositoryError):
        repository.record_map_policy(
            _prepared(records),
            expected_input_revision=snapshot.input_revision,
            request_fingerprint=_fingerprint("rollback"),
            required_fixture_version=FIXTURE_VERSION,
        )

    assert repository.policy_history(ACCOUNT) == ()
    assert _receipt_rows(path) == ()


def test_undo_event_and_receipt_are_atomic_and_exactly_replayable(tmp_path: Path) -> None:
    path = tmp_path / "undo-map.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    first_snapshot = repository.map_input_snapshot(ACCOUNT)
    repository.record_map_policy(
        prepared,
        expected_input_revision=first_snapshot.input_revision,
        request_fingerprint=_fingerprint("decision"),
        required_fixture_version=FIXTURE_VERSION,
    )
    undo_snapshot = repository.map_input_snapshot(ACCOUNT)
    undo = UndoPolicy(
        command_id="command-map-undo-001",
        account_key=ACCOUNT,
        occurred_at=NOW + timedelta(minutes=1),
        expected_revision=1,
        target_decision_id=prepared.command.decision_id,
    )
    fingerprint = _fingerprint("undo")

    applied = repository.undo_map_policy(
        undo,
        expected_input_revision=undo_snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )
    replay = repository.undo_map_policy(
        undo,
        expected_input_revision=undo_snapshot.input_revision,
        request_fingerprint=fingerprint,
        required_fixture_version=FIXTURE_VERSION,
    )

    assert applied.event.account_revision == 2
    assert applied.replayed is False
    assert replay.event == applied.event
    assert replay.replayed is True
    assert repository.map_input_snapshot(ACCOUNT).active_policies == ()
    assert len(_receipt_rows(path)) == 2


def test_undo_receipt_failure_rolls_back_the_undo_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "undo-rollback.db"
    repository, records = _installed_repository(path)
    prepared = _prepared(records)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    repository.record_map_policy(
        prepared,
        expected_input_revision=snapshot.input_revision,
        request_fingerprint=_fingerprint("decision-before-undo-failure"),
        required_fixture_version=FIXTURE_VERSION,
    )
    undo_snapshot = repository.map_input_snapshot(ACCOUNT)
    undo = UndoPolicy(
        command_id="command-map-undo-failure",
        account_key=ACCOUNT,
        occurred_at=NOW + timedelta(minutes=1),
        expected_revision=1,
        target_decision_id=prepared.command.decision_id,
    )

    def fail_receipt(*args: object, **kwargs: object) -> None:
        raise sqlite3.IntegrityError("synthetic undo receipt failure")

    monkeypatch.setattr(
        Repository,
        "_insert_map_policy_receipt",
        staticmethod(fail_receipt),
    )
    with pytest.raises(MapRepositoryError):
        repository.undo_map_policy(
            undo,
            expected_input_revision=undo_snapshot.input_revision,
            request_fingerprint=_fingerprint("undo-failure"),
            required_fixture_version=FIXTURE_VERSION,
        )

    after = repository.map_input_snapshot(ACCOUNT)
    assert after.policy_revision == 1
    assert len(after.active_policies) == 1
    assert len(_receipt_rows(path)) == 1


def test_two_map_commands_from_one_snapshot_accept_exactly_one(tmp_path: Path) -> None:
    path = tmp_path / "concurrent-cas.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    first = _prepared(
        records,
        command_id="command-concurrent-a",
        decision_id="decision-concurrent-a",
    )
    second = _prepared(
        records,
        command_id="command-concurrent-b",
        decision_id="decision-concurrent-b",
    )

    def write(prepared: PreparedPolicyDecision, fingerprint: str) -> str:
        try:
            result = repository.record_map_policy(
                prepared,
                expected_input_revision=snapshot.input_revision,
                request_fingerprint=fingerprint,
                required_fixture_version=FIXTURE_VERSION,
            )
            return f"accepted:{result.event.account_revision}"
        except MapRepositoryError as error:
            return error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(
            pool.map(
                lambda arguments: write(*arguments),
                (
                    (first, _fingerprint("concurrent-a")),
                    (second, _fingerprint("concurrent-b")),
                ),
            )
        )

    assert outcomes.count("accepted:1") == 1
    assert outcomes.count(MapRepositoryErrorCode.MAP_REVISION_CONFLICT.value) == 1
    assert len(repository.policy_history(ACCOUNT)) == 1
    assert len(_receipt_rows(path)) == 1


def test_two_identical_concurrent_map_commands_apply_once_and_replay_once(
    tmp_path: Path,
) -> None:
    path = tmp_path / "concurrent-replay.db"
    repository, records = _installed_repository(path)
    snapshot = repository.map_input_snapshot(ACCOUNT)
    prepared = _prepared(
        records,
        command_id="command-concurrent-replay",
        decision_id="decision-concurrent-replay",
    )
    fingerprint = _fingerprint("concurrent-replay")

    def write() -> MapPolicyWriteResult:
        return repository.record_map_policy(
            prepared,
            expected_input_revision=snapshot.input_revision,
            request_fingerprint=fingerprint,
            required_fixture_version=FIXTURE_VERSION,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(lambda _: write(), range(2)))

    assert sorted(result.replayed for result in outcomes) == [False, True]
    assert outcomes[0].event == outcomes[1].event
    assert len(repository.policy_history(ACCOUNT)) == 1
    assert len(_receipt_rows(path)) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("expected_input_revision", "input-v1-short"),
        ("request_fingerprint", "A" * 64),
        ("required_fixture_version", " fixture "),
        ("contract_version", 2),
    ),
)
def test_map_write_metadata_is_strict(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    repository, records = _installed_repository(tmp_path / f"strict-{field}.db")
    snapshot = repository.map_input_snapshot(ACCOUNT)
    arguments: dict[str, object] = {
        "expected_input_revision": snapshot.input_revision,
        "request_fingerprint": _fingerprint("strict"),
        "required_fixture_version": FIXTURE_VERSION,
        "contract_version": 1,
    }
    arguments[field] = value

    with pytest.raises(MapRepositoryError) as error:
        repository.record_map_policy(_prepared(records), **arguments)  # type: ignore[arg-type]
    assert error.value.code is MapRepositoryErrorCode.INVALID_INPUT
    assert repository.policy_history(ACCOUNT) == ()
