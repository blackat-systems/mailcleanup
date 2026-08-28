from __future__ import annotations

import ast
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import cast

import pytest

import mailmap.repository as repository_module
from mailmap.classification_domain import classify_indexed_records
from mailmap.classification_model import ClassificationResult
from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint, SyncMode, SyncState
from mailmap.model import Confianza, Intencion, Proteccion, Rubro
from mailmap.policy_domain import apply_local_policies, prepare_policy_decision
from mailmap.policy_model import (
    ActivePolicy,
    EffectiveFlow,
    EffectiveMessage,
    EffectiveSource,
    EffectiveSourceKind,
    EffectiveSourceSelector,
    LabelSelector,
    MergeSources,
    MessageSelector,
    PartitionAnchor,
    PartitionAnchorKind,
    PartitionGroup,
    PartitionSource,
    PolicyApplicationResult,
    PolicyBindingStatus,
    PolicyDecisionCommand,
    PolicyDecisionEvidence,
    PolicyError,
    PolicyErrorCode,
    PolicyProtectionReason,
    PolicyTargetSelector,
    PreparedPolicyDecision,
    ProtectTarget,
    SenderSelector,
    SetFlowDisplayName,
    SetFlowIntention,
    SetSourceDisplayName,
    SetSourceRubro,
    UndoPolicy,
)
from mailmap.repository import MIGRATIONS, Repository

ACCOUNT_A = "account-policy-synthetic-a"
ACCOUNT_B = "account-policy-synthetic-b"
NOW = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)


def _record(
    message_id: str,
    *,
    account_key: str = ACCOUNT_A,
    sender_name: str = "Servicio Sintetico",
    sender_address: str = "avisos@alpha-suite.example",
    authenticated_domain: str = "alpha-suite.example",
    subject: str = "Resumen operativo sintetico",
    labels: tuple[str, ...] = ("INBOX",),
    list_id: str | None = None,
    thread_id: str | None = None,
    dkim_result: str | None = "pass",
    dmarc_result: str | None = "pass",
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=message_id,
        provider_thread_id=thread_id or f"thread-{message_id}",
        received_at=NOW,
        sender_name=sender_name,
        sender_address=sender_address,
        subject=subject,
        label_ids=labels,
        category="updates",
        size_estimate_bytes=2048,
        authenticated_domain=authenticated_domain,
        list_id=list_id,
        list_unsubscribe=None,
        list_unsubscribe_post=None,
        dkim_result=dkim_result,
        dmarc_result=dmarc_result,
    )


def _standard_records(*, account_key: str = ACCOUNT_A) -> tuple[IndexedMessageRecord, ...]:
    shared_list = "shared.alpha-suite.example"
    return (
        _record(
            "message-alpha-alert",
            account_key=account_key,
            sender_name="Alpha Suite",
            sender_address="alertas@alpha-suite.example",
            authenticated_domain="alpha-suite.example",
            subject="Resumen operativo Alpha",
            list_id=shared_list,
        ),
        _record(
            "message-alpha-billing",
            account_key=account_key,
            sender_name="Alpha Suite",
            sender_address="facturacion@alpha-suite.example",
            authenticated_domain="alpha-suite.example",
            subject="Resumen operativo Alpha",
            list_id=shared_list,
        ),
        _record(
            "message-beta-offer",
            account_key=account_key,
            sender_name="Beta Shop",
            sender_address="ofertas@beta-shop.example",
            authenticated_domain="beta-shop.example",
            subject="Oferta sintetica de temporada",
            list_id="offers.beta-shop.example",
        ),
        _record(
            "message-gamma-update",
            account_key=account_key,
            sender_name="Gamma Viajes",
            sender_address="avisos@gamma-travel.example",
            authenticated_domain="gamma-travel.example",
            subject="Actualizacion sintetica de reserva",
        ),
    )


def _checkpoint(
    *,
    account_key: str = ACCOUNT_A,
    scan_id: str = "scan-policy-synthetic",
    processed_count: int = 1,
) -> SyncCheckpoint:
    return SyncCheckpoint(
        account_key=account_key,
        scan_id=scan_id,
        mode=SyncMode.FULL,
        state=SyncState.RUNNING,
        page_token="page-policy-synthetic" if processed_count else None,
        history_id="history-policy-synthetic",
        processed_count=processed_count,
        started_at=NOW,
        updated_at=NOW,
        error_code=None,
    )


def _classification(records: tuple[IndexedMessageRecord, ...]) -> ClassificationResult:
    return classify_indexed_records(records)


def _baseline(
    records: tuple[IndexedMessageRecord, ...],
    *,
    policies: tuple[ActivePolicy, ...] = (),
    account_key: str | None = None,
    classification: ClassificationResult | None = None,
) -> PolicyApplicationResult:
    return apply_local_policies(
        account_key or records[0].account_key,
        records,
        classification or _classification(records),
        policies,
    )


def _message(result: PolicyApplicationResult, message_id: str) -> EffectiveMessage:
    return next(item for item in result.messages if item.provider_message_id == message_id)


def _source_for_message(
    result: PolicyApplicationResult, message_id: str
) -> EffectiveSource:
    message = _message(result, message_id)
    return next(
        item for item in result.sources if item.effective_source_id == message.effective_source_id
    )


def _flow_for_message(
    result: PolicyApplicationResult, message_id: str
) -> EffectiveFlow:
    message = _message(result, message_id)
    return next(
        item for item in result.flows if item.effective_flow_id == message.effective_flow_id
    )


def _active(prepared: PreparedPolicyDecision) -> ActivePolicy:
    return ActivePolicy(
        command=prepared.command,
        account_revision=prepared.command.expected_revision + 1,
        anchors=prepared.anchors,
        relations=prepared.relations,
    )


def _prepare(
    command: PolicyDecisionCommand,
    records: tuple[IndexedMessageRecord, ...],
    *,
    policies: tuple[ActivePolicy, ...] = (),
    classification: ClassificationResult | None = None,
) -> PreparedPolicyDecision:
    return prepare_policy_decision(
        account_key=command.account_key,
        records=records,
        classification=classification or _classification(records),
        active_policies=policies,
        command=command,
    )


def _source_name_command(
    selector: EffectiveSourceSelector,
    *,
    command_id: str = "command-source-name",
    decision_id: str = "decision-source-name",
    expected_revision: int = 0,
    display_name: str = "Nombre elegido sintetico",
    supersedes: tuple[str, ...] = (),
) -> SetSourceDisplayName:
    return SetSourceDisplayName(
        command_id=command_id,
        account_key=selector.account_key,
        occurred_at=NOW + timedelta(minutes=expected_revision),
        expected_revision=expected_revision,
        decision_id=decision_id,
        supersedes_decision_ids=supersedes,
        selector=selector,
        display_name=display_name,
    )


def _repo_with_records(
    path: Path,
    records: tuple[IndexedMessageRecord, ...],
) -> Repository:
    repository = Repository(path)
    by_account: dict[str, list[IndexedMessageRecord]] = {}
    for record in records:
        by_account.setdefault(record.account_key, []).append(record)
    for index, (account_key, account_records) in enumerate(sorted(by_account.items())):
        repository.apply_index_page(
            account_key,
            tuple(account_records),
            (),
            _checkpoint(
                account_key=account_key,
                scan_id=f"scan-policy-{index}",
                processed_count=len(account_records),
            ),
        )
    return repository


def _schema_signature(path: Path) -> tuple[tuple[str, str, str], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            (str(row[0]), str(row[1]), " ".join(str(row[2]).split()))
            for row in connection.execute(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )
        )


def _create_exact_v2(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        for version, script in MIGRATIONS[:2]:
            connection.executescript(script)
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (version, NOW.isoformat()),
            )


def _table_counts(path: Path) -> dict[str, int]:
    tables = (
        "local_policy_events",
        "local_policy_anchors",
        "local_policy_anchor_sources",
        "local_policy_partition_members",
        "local_policy_observed_ids",
        "local_policy_relations",
    )
    with sqlite3.connect(path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _partition_command(
    source_selector: EffectiveSourceSelector,
    *,
    expected_revision: int = 0,
    command_id: str = "command-partition",
    decision_id: str = "decision-partition",
    supersedes: tuple[str, ...] = (),
) -> PartitionSource:
    groups = tuple(
        sorted(
            (
                PartitionGroup(
                    anchors=(
                        PartitionAnchor(
                            kind=PartitionAnchorKind.SENDER,
                            sender_address="alertas@alpha-suite.example",
                        ),
                    )
                ),
                PartitionGroup(
                    anchors=(
                        PartitionAnchor(
                            kind=PartitionAnchorKind.SENDER,
                            sender_address="facturacion@alpha-suite.example",
                        ),
                    )
                ),
            ),
            key=lambda item: item.canonical_key,
        )
    )
    return PartitionSource(
        command_id=command_id,
        account_key=source_selector.account_key,
        occurred_at=NOW + timedelta(minutes=expected_revision),
        expected_revision=expected_revision,
        decision_id=decision_id,
        supersedes_decision_ids=supersedes,
        source_selector=source_selector,
        groups=groups,
    )


def _merge_command(
    selectors: tuple[EffectiveSourceSelector, ...],
    *,
    expected_revision: int = 0,
    command_id: str = "command-merge",
    decision_id: str = "decision-merge",
    supersedes: tuple[str, ...] = (),
) -> MergeSources:
    ordered = tuple(sorted(selectors, key=lambda item: item.canonical_key))
    return MergeSources(
        command_id=command_id,
        account_key=ordered[0].account_key,
        occurred_at=NOW + timedelta(minutes=expected_revision),
        expected_revision=expected_revision,
        decision_id=decision_id,
        supersedes_decision_ids=supersedes,
        source_selectors=ordered,
    )


def _replace_automatic_ids(
    classification: ClassificationResult,
    *,
    source_id: str,
) -> ClassificationResult:
    source = next(item for item in classification.sources if item.source_id == source_id)
    new_source_id = "source-v1-aaaaaaaaaaaaaaaaaaaaaaaa"
    flow_mapping = {
        flow_id: f"flow-v1-{index:024x}"
        for index, flow_id in enumerate(source.flow_ids, start=10)
    }
    messages = tuple(
        replace(
            message,
            source_id=new_source_id if message.source_id == source_id else message.source_id,
            flow_id=flow_mapping.get(message.flow_id, message.flow_id),
        )
        for message in classification.messages
    )
    flows = tuple(
        sorted(
            (
                replace(
                    flow,
                    flow_id=flow_mapping.get(flow.flow_id, flow.flow_id),
                    source_id=new_source_id if flow.source_id == source_id else flow.source_id,
                )
                for flow in classification.flows
            ),
            key=lambda item: item.flow_id,
        )
    )
    sources = tuple(
        sorted(
            (
                replace(
                    item,
                    source_id=new_source_id,
                    flow_ids=tuple(sorted(flow_mapping[value] for value in item.flow_ids)),
                )
                if item.source_id == source_id
                else item
                for item in classification.sources
            ),
            key=lambda item: item.source_id,
        )
    )
    return ClassificationResult(
        account_key=classification.account_key,
        messages=messages,
        sources=sources,
        flows=flows,
    )


def _with_single_message_traits(
    classification: ClassificationResult,
    *,
    intention: Intencion | None = None,
    confidence: Confianza | None = None,
    rubro: Rubro | None = None,
) -> ClassificationResult:
    assert len(classification.messages) == 1
    assert len(classification.sources) == 1
    assert len(classification.flows) == 1
    message = classification.messages[0]
    source = classification.sources[0]
    flow = classification.flows[0]
    selected_intention = intention or message.intencion
    selected_confidence = confidence or message.confianza
    selected_rubro = rubro or message.rubro
    descriptor = replace(
        flow.identity_descriptor,
        automatic_intention=selected_intention,
    )
    return ClassificationResult(
        account_key=classification.account_key,
        messages=(
            replace(
                message,
                intencion=selected_intention,
                confianza=selected_confidence,
                rubro=selected_rubro,
            ),
        ),
        sources=(
            replace(
                source,
                confianza=selected_confidence,
                rubro=selected_rubro,
            ),
        ),
        flows=(
            replace(
                flow,
                identity_descriptor=descriptor,
                intencion=selected_intention,
                confianza=selected_confidence,
            ),
        ),
    )


def test_fresh_and_exact_v2_migration_have_the_same_latest_schema(tmp_path: Path) -> None:
    fresh_path = tmp_path / "fresh-policy.db"
    migrated_path = tmp_path / "migrated-policy.db"
    fresh = Repository(fresh_path)
    _create_exact_v2(migrated_path)
    migrated = Repository(migrated_path)

    assert fresh.schema_version() == migrated.schema_version() == len(MIGRATIONS)
    assert _schema_signature(fresh_path) == _schema_signature(migrated_path)
    assert "begin" not in MIGRATIONS[2][1].casefold()
    assert "commit" not in MIGRATIONS[2][1].casefold()
    assert "rollback" not in MIGRATIONS[2][1].casefold()


def test_failed_v3_migration_rolls_back_schema_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "failed-v3.db"
    failing = (
        *MIGRATIONS[:2],
        (3, "CREATE TABLE partial_policy_table(value TEXT); INVALID SQL;"),
    )
    monkeypatch.setattr(repository_module, "MIGRATIONS", failing)

    with pytest.raises(sqlite3.OperationalError):
        Repository(path)

    with sqlite3.connect(path) as connection:
        versions = tuple(
            int(row[0])
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        )
        partial = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'partial_policy_table'"
        ).fetchone()
    assert versions == (1, 2)
    assert partial is None


def test_v3_schema_is_typed_normalized_indexed_and_account_scoped(tmp_path: Path) -> None:
    path = tmp_path / "introspection.db"
    repository = Repository(path)
    expected_tables = {
        "local_policy_events",
        "local_policy_anchors",
        "local_policy_anchor_sources",
        "local_policy_partition_members",
        "local_policy_observed_ids",
        "local_policy_relations",
    }
    with repository._connect() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name LIKE 'local_policy_%'"
            )
        }
        indexes = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name LIKE 'idx_local_policy_%'"
            )
        }
        ddl = " ".join(
            str(row[0]).casefold()
            for row in connection.execute(
                "SELECT sql FROM sqlite_master WHERE name LIKE 'local_policy_%'"
            )
            if row[0] is not None
        )
        event_fks = connection.execute(
            "PRAGMA foreign_key_list(local_policy_events)"
        ).fetchall()
        anchor_fks = connection.execute(
            "PRAGMA foreign_key_list(local_policy_anchors)"
        ).fetchall()
        relation_fks = connection.execute(
            "PRAGMA foreign_key_list(local_policy_relations)"
        ).fetchall()

    assert tables == expected_tables
    assert {
        "idx_local_policy_events_history",
        "idx_local_policy_events_command",
        "idx_local_policy_anchors_role",
        "idx_local_policy_relations_target",
    }.issubset(indexes)
    assert all(marker not in ddl for marker in ("payload_json", " blob", " extra"))
    assert any(row[2] == "indexed_accounts" and row[6] == "CASCADE" for row in event_fks)
    assert all(row[2] != "indexed_messages" for row in anchor_fks)
    assert any(row[2] == "local_policy_events" for row in relation_fks)


def test_v3_checks_reject_invalid_utc_and_impossible_anchor_columns(tmp_path: Path) -> None:
    path = tmp_path / "v3-checks.db"
    records = (_standard_records()[0],)
    _repo_with_records(path, records)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        invalid_event = (
            ACCOUNT_A,
            1,
            "command-invalid-date",
            "set_source_display_name",
            1,
            "garbage+00:00",
            0,
            "decision-invalid-date",
            None,
            "Nombre sintetico",
            None,
            None,
            None,
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO local_policy_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                invalid_event,
            )

    repository = Repository(path)
    selector = _baseline(records).sources[0].selector
    repository.record_policy(_prepare(_source_name_command(selector), records))
    with sqlite3.connect(path) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE local_policy_anchors SET flow_list_id = ? "
            "WHERE account_key = ? AND account_revision = 1 AND anchor_order = 0",
            ("stray.policy.example", ACCOUNT_A),
        )


def test_preparation_rejects_missing_merge_and_incomplete_partition_without_writes(
    tmp_path: Path,
) -> None:
    records = _standard_records()
    classification = _classification(records)
    baseline = _baseline(records, classification=classification)
    alpha = _source_for_message(baseline, "message-alpha-alert").selector
    beta = _source_for_message(baseline, "message-beta-offer").selector
    repository = _repo_with_records(tmp_path / "preparation.db", records)

    missing_command = _source_name_command(alpha)
    with pytest.raises(PolicyError) as missing:
        _prepare(missing_command, (), classification=classify_indexed_records(()))
    assert missing.value.code is PolicyErrorCode.TARGET_NOT_FOUND

    merge = _merge_command((alpha, beta), command_id="command-invalid-merge")
    alpha_records = tuple(
        record for record in records if record.provider_message_id.startswith("message-alpha")
    )
    with pytest.raises(PolicyError) as invalid_merge:
        _prepare(merge, alpha_records)
    assert invalid_merge.value.code is PolicyErrorCode.TARGET_NOT_FOUND

    bad_groups = tuple(
        sorted(
            (
                PartitionGroup(
                    anchors=(
                        PartitionAnchor(
                            kind=PartitionAnchorKind.SENDER,
                            sender_address="alertas@alpha-suite.example",
                        ),
                    )
                ),
                PartitionGroup(
                    anchors=(
                        PartitionAnchor(
                            kind=PartitionAnchorKind.SENDER,
                            sender_address="missing@alpha-suite.example",
                        ),
                    )
                ),
            ),
            key=lambda item: item.canonical_key,
        )
    )
    incomplete = PartitionSource(
        command_id="command-incomplete-partition",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id="decision-incomplete-partition",
        source_selector=alpha,
        groups=bad_groups,
    )
    with pytest.raises(PolicyError) as invalid_partition:
        _prepare(incomplete, records, classification=classification)
    assert invalid_partition.value.code is PolicyErrorCode.INVALID_INPUT

    with pytest.raises(PolicyError) as raw:
        repository.record_policy(cast(PreparedPolicyDecision, missing_command))
    assert raw.value.code is PolicyErrorCode.INVALID_INPUT
    assert repository.policy_history(ACCOUNT_A) == ()


def test_event_anchor_and_last_relation_rollback_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _standard_records()
    classification = _classification(records)
    baseline = _baseline(records, classification=classification)
    alpha = _source_for_message(baseline, "message-alpha-alert").selector
    beta = _source_for_message(baseline, "message-beta-offer").selector
    repository = _repo_with_records(tmp_path / "relation-rollback.db", records)
    merge_prepared = _prepare(_merge_command((alpha, beta)), records)
    merge_event = repository.record_policy(merge_prepared)
    active = repository.active_policies(ACCOUNT_A)
    merged = next(
        source
        for source in _baseline(records, policies=active).sources
        if source.selector.kind is EffectiveSourceKind.MERGED
    )
    name = _source_name_command(
        merged.selector,
        command_id="command-name-after-merge",
        decision_id="decision-name-after-merge",
        expected_revision=merge_event.account_revision,
    )
    prepared = _prepare(name, records, policies=active)
    before = _table_counts(repository.path)

    def fail_last_relation(*_args: object, **_kwargs: object) -> None:
        raise sqlite3.IntegrityError("synthetic relation failure")

    monkeypatch.setattr(
        Repository,
        "_insert_policy_relation",
        staticmethod(fail_last_relation),
    )
    with pytest.raises(PolicyError) as error:
        repository.record_policy(prepared)
    assert error.value.code is PolicyErrorCode.INVALID_INPUT
    assert _table_counts(repository.path) == before
    assert repository.policy_history(ACCOUNT_A) == (merge_event,)


def test_replay_precedes_preparation_revision_and_binding_revalidation(tmp_path: Path) -> None:
    records = _standard_records()
    classification = _classification(records)
    selector = _source_for_message(
        _baseline(records, classification=classification), "message-alpha-alert"
    ).selector
    command = _source_name_command(selector)
    prepared = _prepare(command, records, classification=classification)
    repository = _repo_with_records(tmp_path / "replay.db", records)
    first = repository.record_policy(prepared)

    assert repository.policy_event_for_command(command) == first
    with pytest.raises(PolicyError) as no_target:
        _prepare(command, (), classification=classify_indexed_records(()))
    assert no_target.value.code is PolicyErrorCode.TARGET_NOT_FOUND

    forged_anchor = replace(
        prepared.anchors[0],
        observed_source_ids=("source-v1-aaaaaaaaaaaaaaaaaaaaaaaa",),
        observed_flow_ids=("flow-v1-bbbbbbbbbbbbbbbbbbbbbbbb",),
    )
    forged = PreparedPolicyDecision(
        command=command,
        anchors=(forged_anchor,),
        relations=prepared.relations,
    )
    replay = repository.record_policy(forged)
    assert replay == first
    assert replay.anchors == prepared.anchors
    assert repository.policy_history(ACCOUNT_A) == (first,)

    conflict = replace(command, display_name="Otro nombre sintetico")
    with pytest.raises(PolicyError) as mismatch:
        repository.policy_event_for_command(conflict)
    assert mismatch.value.code is PolicyErrorCode.COMMAND_ID_CONFLICT


def test_identical_prepared_decisions_are_one_event_under_concurrency(tmp_path: Path) -> None:
    records = _standard_records()
    selector = _source_for_message(_baseline(records), "message-alpha-alert").selector
    prepared = _prepare(_source_name_command(selector), records)
    repository = _repo_with_records(tmp_path / "same-command-race.db", records)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(repository.record_policy, prepared) for _ in range(2)]
        results = tuple(future.result(timeout=10) for future in futures)

    assert results[0] == results[1]
    assert repository.policy_history(ACCOUNT_A) == (results[0],)


def test_distinct_commands_with_same_revision_have_one_winner(tmp_path: Path) -> None:
    records = _standard_records()
    selector = _source_for_message(_baseline(records), "message-alpha-alert").selector
    first = _prepare(_source_name_command(selector), records)
    second_command = SetSourceRubro(
        command_id="command-source-rubro",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id="decision-source-rubro",
        selector=selector,
        rubro=Rubro.SOFTWARE,
    )
    second = _prepare(second_command, records)
    repository = _repo_with_records(tmp_path / "revision-race.db", records)

    def record(value: PreparedPolicyDecision) -> PolicyErrorCode | int:
        try:
            return repository.record_policy(value).account_revision
        except PolicyError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(record, (first, second)))

    assert sorted(str(item) for item in results) == sorted(
        (str(1), str(PolicyErrorCode.REVISION_CONFLICT))
    )
    assert len(repository.policy_history(ACCOUNT_A)) == 1


def test_history_replacement_undo_reactivation_and_undo_replay(tmp_path: Path) -> None:
    records = _standard_records()
    selector = _source_for_message(_baseline(records), "message-alpha-alert").selector
    repository = _repo_with_records(tmp_path / "history-undo.db", records)

    first_prepared = _prepare(_source_name_command(selector), records)
    first = repository.record_policy(first_prepared)
    replacement_command = _source_name_command(
        selector,
        command_id="command-source-name-replacement",
        decision_id="decision-source-name-replacement",
        expected_revision=1,
        display_name="Nombre reemplazante sintetico",
        supersedes=(first_prepared.command.decision_id,),
    )
    replacement = repository.record_policy(
        _prepare(
            replacement_command,
            records,
            policies=repository.active_policies(ACCOUNT_A),
        )
    )
    undo = UndoPolicy(
        command_id="command-undo-replacement",
        account_key=ACCOUNT_A,
        occurred_at=NOW + timedelta(minutes=2),
        expected_revision=2,
        target_decision_id=replacement_command.decision_id,
    )
    undo_event = repository.undo_policy(undo)

    history = repository.policy_history(ACCOUNT_A)
    assert tuple(event.account_revision for event in history) == (1, 2, 3)
    assert history == (first, replacement, undo_event)
    assert tuple(policy.decision_id for policy in repository.active_policies(ACCOUNT_A)) == (
        first_prepared.command.decision_id,
    )
    assert repository.undo_policy(undo) == undo_event
    assert repository.policy_history(ACCOUNT_A) == history

    conflicting_undo = replace(undo, target_decision_id=first_prepared.command.decision_id)
    with pytest.raises(PolicyError) as conflict:
        repository.undo_policy(conflicting_undo)
    assert conflict.value.code is PolicyErrorCode.COMMAND_ID_CONFLICT


def test_corrupt_supersedes_cycle_is_rejected_as_controlled_input(tmp_path: Path) -> None:
    records = _standard_records()
    selector = _source_for_message(_baseline(records), "message-alpha-alert").selector
    repository = _repo_with_records(tmp_path / "cycle.db", records)
    first_command = _source_name_command(selector)
    repository.record_policy(_prepare(first_command, records))
    second_command = _source_name_command(
        selector,
        command_id="command-cycle-second",
        decision_id="decision-cycle-second",
        expected_revision=1,
        supersedes=(first_command.decision_id,),
    )
    repository.record_policy(
        _prepare(second_command, records, policies=repository.active_policies(ACCOUNT_A))
    )

    with sqlite3.connect(repository.path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "UPDATE local_policy_relations SET target_decision_id = ? "
            "WHERE account_key = ? AND account_revision = 2 "
            "AND relation_kind = 'supersedes'",
            (second_command.decision_id, ACCOUNT_A),
        )

    with pytest.raises(PolicyError) as error:
        repository.active_policies(ACCOUNT_A)
    assert error.value.code is PolicyErrorCode.INVALID_INPUT
    assert str(error.value) == PolicyErrorCode.INVALID_INPUT.value


def test_binding_exact_and_rebound_only_for_automatic_id_changes() -> None:
    records = _standard_records()
    classification = _classification(records)
    baseline = _baseline(records, classification=classification)
    source = _source_for_message(baseline, "message-alpha-alert")
    prepared = _prepare(
        _source_name_command(source.selector),
        records,
        classification=classification,
    )
    policy = _active(prepared)

    exact = _baseline(records, policies=(policy,), classification=classification)
    assert exact.bindings[0].status is PolicyBindingStatus.EXACT
    assert _source_for_message(exact, "message-alpha-alert").effective_display_name == (
        cast(SetSourceDisplayName, prepared.command).display_name
    )

    rebound_classification = _replace_automatic_ids(
        classification,
        source_id=classification.messages[0].source_id,
    )
    rebound = _baseline(
        records,
        policies=(policy,),
        classification=rebound_classification,
    )
    assert rebound.bindings[0].status is PolicyBindingStatus.REBOUND
    assert _source_for_message(rebound, "message-alpha-alert").effective_display_name == (
        cast(SetSourceDisplayName, prepared.command).display_name
    )

    changed_effective_anchor = replace(
        prepared.anchors[0],
        observed_effective_id="effective-source-v1-ffffffffffffffffffffffff",
    )
    changed_effective_policy = ActivePolicy(
        command=prepared.command,
        account_revision=1,
        anchors=(changed_effective_anchor,),
        relations=prepared.relations,
    )
    changed_effective = _baseline(records, policies=(changed_effective_policy,))
    assert changed_effective.bindings[0].status is PolicyBindingStatus.NEEDS_REVIEW


def test_growth_is_automatic_but_source_anchor_changes_require_review() -> None:
    original = (
        _record(
            "message-growth-original",
            sender_name="Growth Suite",
            sender_address="avisos@growth-suite.example",
            authenticated_domain="growth-suite.example",
        ),
    )
    original_view = _baseline(original)
    selector = original_view.sources[0].selector
    prepared = _prepare(_source_name_command(selector), original)
    policy = _active(prepared)

    same_sender = (
        *original,
        _record(
            "message-growth-future",
            sender_name="Growth Suite",
            sender_address="avisos@growth-suite.example",
            authenticated_domain="growth-suite.example",
        ),
    )
    grown = _baseline(same_sender, policies=(policy,))
    assert grown.bindings[0].status in {
        PolicyBindingStatus.EXACT,
        PolicyBindingStatus.REBOUND,
    }
    assert all(
        message.decision_ids == (prepared.command.decision_id,)
        for message in grown.messages
    )

    new_anchor = (
        *original,
        _record(
            "message-growth-new-anchor",
            sender_name="Growth Suite",
            sender_address="facturacion@growth-suite.example",
            authenticated_domain="growth-suite.example",
        ),
    )
    reviewed = _baseline(new_anchor, policies=(policy,))
    assert reviewed.bindings[0].status is PolicyBindingStatus.NEEDS_REVIEW
    assert all(message.review_required for message in reviewed.messages)
    assert all(
        source.effective_display_name == source.automatic_display_name
        for source in reviewed.sources
    )


def test_flow_descriptor_change_requires_review_instead_of_orphaning() -> None:
    original = (
        _record(
            "message-flow-change",
            sender_name="Flow Suite",
            sender_address="news@flow-suite.example",
            authenticated_domain="flow-suite.example",
            list_id="weekly.flow-suite.example",
        ),
    )
    original_view = _baseline(original)
    flow = original_view.flows[0]
    command = SetFlowDisplayName(
        command_id="command-flow-change",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id="decision-flow-change",
        selector=flow.selector,
        display_name="Flujo elegido sintetico",
    )
    policy = _active(_prepare(command, original))
    changed = (
        replace(original[0], list_id="monthly.flow-suite.example"),
    )

    result = _baseline(changed, policies=(policy,))
    assert result.bindings[0].status is PolicyBindingStatus.NEEDS_REVIEW
    assert result.messages[0].review_required is True
    assert result.flows[0].effective_display_name == result.flows[0].automatic_display_name


def test_flow_selector_that_now_has_multiple_candidates_is_ambiguous() -> None:
    original = (
        _record(
            "message-flow-ambiguous-original",
            sender_name="Ambiguous Flow Suite",
            sender_address="news@ambiguous-flow.example",
            authenticated_domain="ambiguous-flow.example",
            list_id="weekly.ambiguous-flow.example",
        ),
    )
    flow = _baseline(original).flows[0]
    command = SetFlowDisplayName(
        command_id="command-flow-ambiguous",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id="decision-flow-ambiguous",
        selector=flow.selector,
        display_name="Flujo ambiguo no aplicable",
    )
    policy = _active(_prepare(command, original))
    current = (
        replace(
            original[0],
            provider_message_id="message-flow-ambiguous-monthly",
            provider_thread_id="thread-flow-ambiguous-monthly",
            list_id="monthly.ambiguous-flow.example",
        ),
        replace(
            original[0],
            provider_message_id="message-flow-ambiguous-daily",
            provider_thread_id="thread-flow-ambiguous-daily",
            list_id="daily.ambiguous-flow.example",
        ),
    )

    result = _baseline(current, policies=(policy,))
    assert result.bindings[0].status is PolicyBindingStatus.AMBIGUOUS
    assert all(message.review_required and message.protected for message in result.messages)
    assert all(flow.effective_display_name != command.display_name for flow in result.flows)


def test_orphan_ambiguous_and_conflict_never_apply_silently() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    correction_prepared = _prepare(_source_name_command(alpha.selector), records)
    correction = _active(correction_prepared)

    orphaned = apply_local_policies(
        ACCOUNT_A,
        (),
        classify_indexed_records(()),
        (correction,),
    )
    assert orphaned.bindings[0].status is PolicyBindingStatus.ORPHANED
    assert orphaned.messages == ()

    partition_prepared = _prepare(
        _partition_command(alpha.selector, expected_revision=1),
        records,
        policies=(correction,),
    )
    ambiguous = _baseline(records, policies=(correction, _active(partition_prepared)))
    correction_binding = next(
        binding
        for binding in ambiguous.bindings
        if binding.decision_id == correction.decision_id
    )
    assert correction_binding.status is PolicyBindingStatus.NEEDS_REVIEW
    alpha_messages = tuple(
        _message(ambiguous, message_id)
        for message_id in ("message-alpha-alert", "message-alpha-billing")
    )
    assert all(message.review_required and message.protected for message in alpha_messages)
    assert all(
        source.effective_display_name == source.automatic_display_name
        for source in ambiguous.sources
    )

    second_command = _source_name_command(
        alpha.selector,
        command_id="command-source-name-conflict",
        decision_id="decision-source-name-conflict",
        expected_revision=1,
        display_name="Nombre conflictivo sintetico",
    )
    second = _active(_prepare(second_command, records))
    conflicted = _baseline(records, policies=(correction, second))
    assert {binding.status for binding in conflicted.bindings} == {
        PolicyBindingStatus.CONFLICT
    }
    assert all(message.review_required and message.protected for message in conflicted.messages[:2])


def test_name_rubro_and_intention_corrections_preserve_d4_and_records() -> None:
    records = _standard_records()
    classification = _classification(records)
    baseline = _baseline(records, classification=classification)
    source = _source_for_message(baseline, "message-alpha-alert")
    flow = _flow_for_message(baseline, "message-alpha-alert")
    commands: tuple[PolicyDecisionCommand, ...] = (
        _source_name_command(source.selector),
        SetSourceRubro(
            command_id="command-correction-rubro",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=1,
            decision_id="decision-correction-rubro",
            selector=source.selector,
            rubro=Rubro.FINANZAS,
        ),
        SetFlowDisplayName(
            command_id="command-correction-flow-name",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=2,
            decision_id="decision-correction-flow-name",
            selector=flow.selector,
            display_name="Flujo manual sintetico",
        ),
        SetFlowIntention(
            command_id="command-correction-intention",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=3,
            decision_id="decision-correction-intention",
            selector=flow.selector,
            intention=Intencion.PERSONAL,
        ),
    )
    policies = tuple(_active(_prepare(command, records)) for command in commands)
    records_before = tuple(records)
    classification_before = classification

    result = _baseline(records, policies=policies, classification=classification)
    changed_source = _source_for_message(result, "message-alpha-alert")
    changed_flow = _flow_for_message(result, "message-alpha-alert")
    changed_message = _message(result, "message-alpha-alert")

    assert records == records_before
    assert classification == classification_before
    assert changed_source.automatic_display_name == source.automatic_display_name
    assert changed_source.effective_display_name == "Nombre elegido sintetico"
    assert changed_source.automatic_rubro == source.automatic_rubro
    assert changed_source.effective_rubro is Rubro.FINANZAS
    assert changed_flow.automatic_display_name == flow.automatic_display_name
    assert changed_flow.effective_display_name == "Flujo manual sintetico"
    assert changed_flow.automatic_intention == flow.automatic_intention
    assert changed_flow.effective_intention is Intencion.PERSONAL
    assert changed_message.automatic_rubro != changed_message.effective_rubro
    assert set(changed_message.automatic_evidence).issubset(changed_message.effective_evidence)
    assert any(
        isinstance(item, PolicyDecisionEvidence) for item in changed_message.effective_evidence
    )


def test_merge_is_exact_deterministic_and_preserves_membership_and_flows() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    beta = _source_for_message(baseline, "message-beta-offer")
    prepared = _prepare(_merge_command((alpha.selector, beta.selector)), records)
    policy = _active(prepared)

    result = _baseline(records, policies=(policy,))
    reversed_result = apply_local_policies(
        ACCOUNT_A,
        reversed(records),
        _classification(records),
        (policy,),
    )
    merged = next(
        source for source in result.sources if source.selector.kind is EffectiveSourceKind.MERGED
    )
    expected_members = tuple(sorted((*alpha.message_ids, *beta.message_ids)))

    assert result == reversed_result
    assert len(result.sources) == len(baseline.sources) - 1
    assert merged.message_ids == expected_members
    assert merged.effective_source_id.startswith("effective-source-v1-")
    assert all(flow.effective_flow_id.startswith("effective-flow-v1-") for flow in result.flows)
    assert {message.provider_message_id for message in result.messages} == {
        record.provider_message_id for record in records
    }
    assert sum(len(source.message_ids) for source in result.sources) == len(records)


def test_partition_is_complete_deterministic_and_fragments_crossing_flow() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    alpha_flow_ids = {
        _message(baseline, "message-alpha-alert").automatic_flow_id,
        _message(baseline, "message-alpha-billing").automatic_flow_id,
    }
    assert len(alpha_flow_ids) == 1
    prepared = _prepare(_partition_command(alpha.selector), records)

    result = _baseline(records, policies=(_active(prepared),))
    alert = _message(result, "message-alpha-alert")
    billing = _message(result, "message-alpha-billing")

    assert len(result.sources) == len(baseline.sources) + 1
    assert alert.effective_source_id != billing.effective_source_id
    assert alert.effective_flow_id != billing.effective_flow_id
    assert alert.automatic_flow_id == billing.automatic_flow_id
    assert sum(len(source.message_ids) for source in result.sources) == len(records)
    assert tuple(message.provider_message_id for message in result.messages) == tuple(
        sorted(record.provider_message_id for record in records)
    )


def test_partition_fragments_preserve_original_automatic_flow_confidence() -> None:
    records = _standard_records()
    original = _classification(records)
    alert = next(
        message
        for message in original.messages
        if message.provider_message_id == "message-alpha-alert"
    )
    billing = next(
        message
        for message in original.messages
        if message.provider_message_id == "message-alpha-billing"
    )
    assert alert.flow_id == billing.flow_id

    classification = ClassificationResult(
        account_key=original.account_key,
        messages=tuple(
            replace(
                message,
                confianza=(
                    Confianza.CONTRADICTORIA
                    if message.provider_message_id == billing.provider_message_id
                    else message.confianza
                ),
            )
            for message in original.messages
        ),
        sources=tuple(
            replace(source, confianza=Confianza.CONTRADICTORIA)
            if source.source_id == alert.source_id
            else source
            for source in original.sources
        ),
        flows=tuple(
            replace(flow, confianza=Confianza.CONTRADICTORIA)
            if flow.flow_id == alert.flow_id
            else flow
            for flow in original.flows
        ),
    )
    baseline = _baseline(records, classification=classification)
    alpha = _source_for_message(baseline, alert.provider_message_id)
    partition = _active(
        _prepare(
            _partition_command(alpha.selector),
            records,
            classification=classification,
        )
    )

    result = _baseline(
        records,
        policies=(partition,),
        classification=classification,
    )

    assert (
        _flow_for_message(result, alert.provider_message_id).automatic_confidence
        is Confianza.CONTRADICTORIA
    )
    assert (
        _flow_for_message(result, alert.provider_message_id).effective_confidence
        is Confianza.CONTRADICTORIA
    )
    assert (
        _flow_for_message(result, billing.provider_message_id).automatic_confidence
        is Confianza.CONTRADICTORIA
    )


def test_effective_structural_sources_and_flows_accept_later_corrections() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    beta = _source_for_message(baseline, "message-beta-offer")
    merge = _active(_prepare(_merge_command((alpha.selector, beta.selector)), records))
    merged_view = _baseline(records, policies=(merge,))
    merged_source = next(
        source
        for source in merged_view.sources
        if source.selector.kind is EffectiveSourceKind.MERGED
    )
    merged_flow = _flow_for_message(merged_view, "message-alpha-alert")
    later_commands: tuple[PolicyDecisionCommand, ...] = (
        _source_name_command(
            merged_source.selector,
            command_id="command-merged-name",
            decision_id="decision-merged-name",
            expected_revision=1,
        ),
        SetSourceRubro(
            command_id="command-merged-rubro",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=2,
            decision_id="decision-merged-rubro",
            selector=merged_source.selector,
            rubro=Rubro.TRABAJO,
        ),
        SetFlowIntention(
            command_id="command-merged-flow-intention",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=3,
            decision_id="decision-merged-flow-intention",
            selector=merged_flow.selector,
            intention=Intencion.DOCUMENTO,
        ),
        ProtectTarget(
            command_id="command-protect-merged",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=4,
            decision_id="decision-protect-merged",
            selector=merged_source.selector,
        ),
    )
    later = tuple(
        _active(_prepare(command, records, policies=(merge,))) for command in later_commands
    )

    result = _baseline(records, policies=(merge, *later))
    changed_source = _source_for_message(result, "message-alpha-alert")
    changed_flow = _flow_for_message(result, "message-alpha-alert")

    assert changed_source.effective_display_name == "Nombre elegido sintetico"
    assert changed_source.effective_rubro is Rubro.TRABAJO
    assert changed_flow.effective_intention is Intencion.DOCUMENTO
    assert all(_message(result, message_id).protected for message_id in merged_source.message_ids)
    assert all(
        binding.status in {PolicyBindingStatus.EXACT, PolicyBindingStatus.REBOUND}
        for binding in result.bindings
    )


def test_partition_group_and_fragmented_flow_accept_exact_later_policies() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    partition = _active(_prepare(_partition_command(alpha.selector), records))
    partitioned = _baseline(records, policies=(partition,))
    group = _source_for_message(partitioned, "message-alpha-alert")
    fragment = _flow_for_message(partitioned, "message-alpha-alert")
    source_command = SetSourceRubro(
        command_id="command-partition-group-rubro",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=1,
        decision_id="decision-partition-group-rubro",
        selector=group.selector,
        rubro=Rubro.SALUD,
    )
    flow_command = SetFlowDisplayName(
        command_id="command-fragment-name",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=2,
        decision_id="decision-fragment-name",
        selector=fragment.selector,
        display_name="Fragmento sintetico elegido",
    )
    policies = (
        partition,
        _active(_prepare(source_command, records, policies=(partition,))),
        _active(_prepare(flow_command, records, policies=(partition,))),
    )

    result = _baseline(records, policies=policies)
    assert _source_for_message(result, "message-alpha-alert").effective_rubro is Rubro.SALUD
    assert (
        _flow_for_message(result, "message-alpha-alert").effective_display_name
        == "Fragmento sintetico elegido"
    )
    assert _source_for_message(result, "message-alpha-billing").effective_rubro is not Rubro.SALUD


def test_structural_undo_or_replacement_sends_dependent_policy_to_review() -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    beta = _source_for_message(baseline, "message-beta-offer")
    merge_prepared = _prepare(_merge_command((alpha.selector, beta.selector)), records)
    merge = _active(merge_prepared)
    merged = next(
        source
        for source in _baseline(records, policies=(merge,)).sources
        if source.selector.kind is EffectiveSourceKind.MERGED
    )
    name_prepared = _prepare(
        _source_name_command(
            merged.selector,
            command_id="command-dependent-name",
            decision_id="decision-dependent-name",
            expected_revision=1,
        ),
        records,
        policies=(merge,),
    )
    dependent = _active(name_prepared)

    undone_view = _baseline(records, policies=(dependent,))
    undone_binding = undone_view.bindings[0]
    assert undone_binding.status not in {
        PolicyBindingStatus.EXACT,
        PolicyBindingStatus.REBOUND,
    }
    assert all(
        source.effective_display_name
        != cast(SetSourceDisplayName, name_prepared.command).display_name
        for source in undone_view.sources
    )
    assert any(message.review_required for message in undone_view.messages)

    replacement_command = _merge_command(
        (alpha.selector, beta.selector),
        command_id="command-replacement-merge",
        decision_id="decision-replacement-merge",
        expected_revision=2,
        supersedes=(merge.decision_id,),
    )
    replacement = _active(
        _prepare(replacement_command, records, policies=(merge, dependent))
    )
    replaced_view = _baseline(records, policies=(replacement, dependent))
    dependent_binding = next(
        binding
        for binding in replaced_view.bindings
        if binding.decision_id == dependent.decision_id
    )
    assert dependent_binding.status is PolicyBindingStatus.NEEDS_REVIEW
    assert any(message.review_required for message in replaced_view.messages)


def test_policies_never_generalize_by_name_domain_or_similarity() -> None:
    original = (
        _record(
            "message-original-similarity",
            sender_name="Marca Parecida",
            sender_address="avisos@original-brand.example",
            authenticated_domain="original-brand.example",
        ),
    )
    source = _baseline(original).sources[0]
    source_policy = _active(_prepare(_source_name_command(source.selector), original))
    sender_command = ProtectTarget(
        command_id="command-exact-sender",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=1,
        decision_id="decision-exact-sender",
        selector=SenderSelector(
            account_key=ACCOUNT_A,
            sender_address="avisos@original-brand.example",
        ),
    )
    sender_policy = _active(_prepare(sender_command, original))
    similar = (
        _record(
            "message-similar-only",
            sender_name="Marca Parecida",
            sender_address="avisos@original-brand-similar.example",
            authenticated_domain="original-brand-similar.example",
        ),
    )

    result = _baseline(similar, policies=(source_policy, sender_policy))
    assert {binding.status for binding in result.bindings} == {
        PolicyBindingStatus.ORPHANED
    }
    assert result.messages[0].protected is False
    assert result.sources[0].effective_display_name == result.sources[0].automatic_display_name


def test_accounts_are_strictly_isolated_in_ids_history_and_selectors(tmp_path: Path) -> None:
    records_a = (_standard_records(account_key=ACCOUNT_A)[0],)
    records_b = (_standard_records(account_key=ACCOUNT_B)[0],)
    view_a = _baseline(records_a)
    view_b = _baseline(records_b)
    repository = _repo_with_records(tmp_path / "accounts.db", (*records_a, *records_b))
    command_a = _source_name_command(
        view_a.sources[0].selector,
        command_id="command-account-a",
        decision_id="decision-account-a",
    )
    command_b = _source_name_command(
        view_b.sources[0].selector,
        command_id="command-account-b",
        decision_id="decision-account-b",
    )
    event_a = repository.record_policy(_prepare(command_a, records_a))
    event_b = repository.record_policy(_prepare(command_b, records_b))

    assert view_a.sources[0].effective_source_id != view_b.sources[0].effective_source_id
    assert repository.policy_history(ACCOUNT_A) == (event_a,)
    assert repository.policy_history(ACCOUNT_B) == (event_b,)
    assert event_a.account_revision == event_b.account_revision == 1
    with pytest.raises(ValueError, match="another account"):
        SetSourceDisplayName(
            command_id="command-cross-account",
            account_key=ACCOUNT_B,
            occurred_at=NOW,
            expected_revision=1,
            decision_id="decision-cross-account",
            selector=view_a.sources[0].selector,
            display_name="No debe aplicar",
        )


@pytest.mark.parametrize(
    ("label", "reason", "hard_excluded"),
    (
        ("SENT", PolicyProtectionReason.SENT, True),
        ("DRAFT", PolicyProtectionReason.DRAFT, True),
        ("TRASH", PolicyProtectionReason.TRASH, True),
        ("STARRED", PolicyProtectionReason.STARRED, False),
        ("IMPORTANT", PolicyProtectionReason.IMPORTANT, False),
    ),
)
def test_automatic_label_protections_are_preserved(
    label: str,
    reason: PolicyProtectionReason,
    hard_excluded: bool,
) -> None:
    records = (
        _record(
            f"message-label-{label.casefold()}",
            labels=(label,),
        ),
    )
    message = _baseline(records).messages[0]

    assert message.protected is True
    assert message.hard_excluded is hard_excluded
    assert reason in message.protection_reasons
    assert message.automatic_protection is not Proteccion.ORDINARIA


@pytest.mark.parametrize(
    ("intention", "confidence", "reason"),
    (
        (Intencion.SEGURIDAD, Confianza.ALTA, PolicyProtectionReason.SECURITY),
        (Intencion.DOCUMENTO, Confianza.ALTA, PolicyProtectionReason.DOCUMENT),
        (Intencion.PERSONAL, Confianza.ALTA, PolicyProtectionReason.PERSONAL),
        (Intencion.OPERATIVO, Confianza.BAJA, PolicyProtectionReason.LOW_CONFIDENCE),
        (
            Intencion.OPERATIVO,
            Confianza.CONTRADICTORIA,
            PolicyProtectionReason.CONTRADICTION,
        ),
    ),
)
def test_automatic_semantic_and_confidence_protections_are_preserved(
    intention: Intencion,
    confidence: Confianza,
    reason: PolicyProtectionReason,
) -> None:
    records = (_record("message-automatic-protection"),)
    classification = _with_single_message_traits(
        _classification(records),
        intention=intention,
        confidence=confidence,
    )

    message = _baseline(records, classification=classification).messages[0]
    assert message.protected is True
    assert reason in message.protection_reasons
    if confidence in {Confianza.BAJA, Confianza.CONTRADICTORIA}:
        assert message.review_required is True


@pytest.mark.parametrize(
    "selector_kind",
    ("message", "sender", "label", "source", "flow"),
)
def test_manual_protection_supports_every_closed_target_selector(
    selector_kind: str,
) -> None:
    records = tuple(
        replace(record, label_ids=(*record.label_ids, "POLICY_SYNTHETIC"))
        if record.provider_message_id == "message-alpha-alert"
        else record
        for record in _standard_records()
    )
    baseline = _baseline(records)
    selector: PolicyTargetSelector
    if selector_kind == "message":
        selector = MessageSelector(
            account_key=ACCOUNT_A,
            provider_message_id="message-alpha-alert",
        )
        expected = {"message-alpha-alert"}
    elif selector_kind == "sender":
        selector = SenderSelector(
            account_key=ACCOUNT_A,
            sender_address="alertas@alpha-suite.example",
        )
        expected = {"message-alpha-alert"}
    elif selector_kind == "label":
        selector = LabelSelector(account_key=ACCOUNT_A, label_id="POLICY_SYNTHETIC")
        expected = {"message-alpha-alert"}
    elif selector_kind == "source":
        source = _source_for_message(baseline, "message-alpha-alert")
        selector = source.selector
        expected = set(source.message_ids)
    else:
        flow = _flow_for_message(baseline, "message-alpha-alert")
        selector = flow.selector
        expected = set(flow.message_ids)
    command = ProtectTarget(
        command_id=f"command-protect-{selector_kind}",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id=f"decision-protect-{selector_kind}",
        selector=selector,
    )

    result = _baseline(records, policies=(_active(_prepare(command, records)),))
    protected = {
        message.provider_message_id
        for message in result.messages
        if command.decision_id in message.decision_ids
    }
    assert protected == expected
    assert all(_message(result, message_id).protected for message_id in expected)
    assert all(
        PolicyProtectionReason.MANUAL_POLICY
        in _message(result, message_id).protection_reasons
        for message_id in expected
    )
    if selector_kind == "label":
        assert PolicyProtectionReason.PROTECTED_LABEL in _message(
            result, "message-alpha-alert"
        ).protection_reasons


@pytest.mark.parametrize("selector_kind", ("sender", "label"))
def test_exact_sender_and_label_selectors_cover_future_messages(selector_kind: str) -> None:
    original = (
        _record(
            "message-direct-original",
            sender_address="future@direct-policy.example",
            authenticated_domain="direct-policy.example",
            labels=("INBOX", "DIRECT_POLICY"),
        ),
    )
    selector = (
        SenderSelector(
            account_key=ACCOUNT_A,
            sender_address="future@direct-policy.example",
        )
        if selector_kind == "sender"
        else LabelSelector(account_key=ACCOUNT_A, label_id="DIRECT_POLICY")
    )
    command = ProtectTarget(
        command_id=f"command-future-{selector_kind}",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id=f"decision-future-{selector_kind}",
        selector=selector,
    )
    policy = _active(_prepare(command, original))
    future = (
        *original,
        _record(
            "message-direct-future",
            sender_address=(
                "future@direct-policy.example"
                if selector_kind == "sender"
                else "other@direct-policy.example"
            ),
            authenticated_domain="direct-policy.example",
            labels=("INBOX", "DIRECT_POLICY"),
        ),
    )

    result = _baseline(future, policies=(policy,))
    assert result.bindings[0].status is PolicyBindingStatus.EXACT
    assert all(message.protected for message in result.messages)
    assert all(command.decision_id in message.decision_ids for message in result.messages)


def test_mixed_conversation_and_contradiction_protect_conservatively() -> None:
    thread_id = "thread-mixed-synthetic"
    records = (
        _record(
            "message-mixed-security",
            sender_name="Security Synthetic",
            sender_address="security@mixed-security.example",
            authenticated_domain="mixed-security.example",
            thread_id=thread_id,
        ),
        _record(
            "message-mixed-ordinary",
            sender_name="Ordinary Synthetic",
            sender_address="ordinary@mixed-ordinary.example",
            authenticated_domain="mixed-ordinary.example",
            thread_id=thread_id,
        ),
    )
    classified = _classification(records)
    security_message = next(
        item for item in classified.messages if item.provider_message_id == "message-mixed-security"
    )
    security_flow = next(
        item for item in classified.flows if item.flow_id == security_message.flow_id
    )
    security_source = next(
        item for item in classified.sources if item.source_id == security_message.source_id
    )
    security_descriptor = replace(
        security_flow.identity_descriptor,
        automatic_intention=Intencion.SEGURIDAD,
    )
    modified = ClassificationResult(
        account_key=classified.account_key,
        messages=tuple(
            replace(item, intencion=Intencion.SEGURIDAD)
            if item.provider_message_id == security_message.provider_message_id
            else item
            for item in classified.messages
        ),
        sources=tuple(
            replace(item, confianza=Confianza.CONTRADICTORIA)
            if item.source_id == security_source.source_id
            else item
            for item in classified.sources
        ),
        flows=tuple(
            replace(
                item,
                identity_descriptor=security_descriptor,
                intencion=Intencion.SEGURIDAD,
                confianza=Confianza.CONTRADICTORIA,
            )
            if item.flow_id == security_flow.flow_id
            else item
            for item in classified.flows
        ),
    )
    modified = replace(
        modified,
        messages=tuple(
            replace(item, confianza=Confianza.CONTRADICTORIA)
            if item.provider_message_id == security_message.provider_message_id
            else item
            for item in modified.messages
        ),
    )

    result = _baseline(records, classification=modified)
    security = _message(result, "message-mixed-security")
    ordinary = _message(result, "message-mixed-ordinary")
    assert PolicyProtectionReason.SECURITY in security.protection_reasons
    assert PolicyProtectionReason.CONTRADICTION in security.protection_reasons
    assert PolicyProtectionReason.MIXED_CONVERSATION in security.protection_reasons
    assert PolicyProtectionReason.MIXED_CONVERSATION in ordinary.protection_reasons
    assert security.protected and ordinary.protected
    assert security.review_required and ordinary.review_required


def test_manual_correction_and_undo_cannot_lower_automatic_protection(tmp_path: Path) -> None:
    records = (_record("message-protection-undo"),)
    classification = _with_single_message_traits(
        _classification(records),
        intention=Intencion.SEGURIDAD,
    )
    baseline = _baseline(records, classification=classification)
    flow = baseline.flows[0]
    command = SetFlowIntention(
        command_id="command-lower-intention",
        account_key=ACCOUNT_A,
        occurred_at=NOW,
        expected_revision=0,
        decision_id="decision-lower-intention",
        selector=flow.selector,
        intention=Intencion.PROMOCIONAL,
    )
    prepared = _prepare(command, records, classification=classification)
    repository = _repo_with_records(tmp_path / "protection-undo.db", records)
    repository.record_policy(prepared)
    corrected = _baseline(
        records,
        policies=repository.active_policies(ACCOUNT_A),
        classification=classification,
    )
    undo = UndoPolicy(
        command_id="command-undo-lower-intention",
        account_key=ACCOUNT_A,
        occurred_at=NOW + timedelta(minutes=1),
        expected_revision=1,
        target_decision_id=command.decision_id,
    )
    repository.undo_policy(undo)
    restored = _baseline(
        records,
        policies=repository.active_policies(ACCOUNT_A),
        classification=classification,
    )

    for result in (baseline, corrected, restored):
        message = result.messages[0]
        assert message.automatic_protection is Proteccion.CRITICA
        assert message.effective_protection is Proteccion.CRITICA
        assert PolicyProtectionReason.SECURITY in message.protection_reasons
    assert corrected.messages[0].effective_intention is Intencion.PROMOCIONAL
    assert restored.messages[0].effective_intention is Intencion.SEGURIDAD


def test_full_index_restart_preserves_policy_history_and_active_ledger(tmp_path: Path) -> None:
    records = _standard_records()
    selector = _source_for_message(_baseline(records), "message-alpha-alert").selector
    repository = _repo_with_records(tmp_path / "full-index.db", records)
    event = repository.record_policy(_prepare(_source_name_command(selector), records))
    active_before = repository.active_policies(ACCOUNT_A)

    repository.start_full_index(
        ACCOUNT_A,
        _checkpoint(
            account_key=ACCOUNT_A,
            scan_id="scan-policy-full-restart",
            processed_count=0,
        ),
    )

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.policy_history(ACCOUNT_A) == (event,)
    assert repository.active_policies(ACCOUNT_A) == active_before


def test_delete_account_cascades_only_that_account_and_old_commands_do_not_recreate_it(
    tmp_path: Path,
) -> None:
    records_a = (_standard_records(account_key=ACCOUNT_A)[0],)
    records_b = (_standard_records(account_key=ACCOUNT_B)[0],)
    repository = _repo_with_records(tmp_path / "delete-account.db", (*records_a, *records_b))
    selector_a = _baseline(records_a).sources[0].selector
    selector_b = _baseline(records_b).sources[0].selector
    prepared_a = _prepare(
        _source_name_command(
            selector_a,
            command_id="command-delete-a",
            decision_id="decision-delete-a",
        ),
        records_a,
    )
    prepared_b = _prepare(
        _source_name_command(
            selector_b,
            command_id="command-delete-b",
            decision_id="decision-delete-b",
        ),
        records_b,
    )
    event_a = repository.record_policy(prepared_a)
    event_b = repository.record_policy(prepared_b)

    repository.delete_account_index(ACCOUNT_A)

    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.policy_history(ACCOUNT_A) == ()
    assert repository.active_policies(ACCOUNT_A) == ()
    assert repository.policy_event_for_command(prepared_a.command) is None
    assert repository.policy_history(ACCOUNT_B) == (event_b,)
    assert repository.indexed_messages(ACCOUNT_B) == records_b
    with pytest.raises(PolicyError) as retry:
        repository.record_policy(prepared_a)
    assert retry.value.code is PolicyErrorCode.TARGET_NOT_FOUND
    old_undo = UndoPolicy(
        command_id="command-delete-old-undo",
        account_key=ACCOUNT_A,
        occurred_at=NOW + timedelta(minutes=1),
        expected_revision=0,
        target_decision_id=cast(SetSourceDisplayName, event_a.command).decision_id,
    )
    with pytest.raises(PolicyError) as undo_error:
        repository.undo_policy(old_undo)
    assert undo_error.value.code is PolicyErrorCode.INVALID_TRANSITION
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute(
            "SELECT 1 FROM indexed_accounts WHERE account_key = ?", (ACCOUNT_A,)
        ).fetchone() is None


def test_delete_winning_the_lock_makes_concurrent_record_fail_without_recreation(
    tmp_path: Path,
) -> None:
    records = (_standard_records()[0],)
    repository = _repo_with_records(tmp_path / "delete-first-race.db", records)
    selector = _baseline(records).sources[0].selector
    prepared = _prepare(_source_name_command(selector), records)
    started = Event()

    def record_after_signal() -> PolicyErrorCode | None:
        started.set()
        try:
            repository.record_policy(prepared)
        except PolicyError as error:
            return error.code
        return None

    with sqlite3.connect(repository.path, timeout=10) as deleting:
        deleting.execute("PRAGMA foreign_keys = ON")
        deleting.execute("BEGIN IMMEDIATE")
        deleting.execute(
            "DELETE FROM indexed_accounts WHERE account_key = ?",
            (ACCOUNT_A,),
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(record_after_signal)
            assert started.wait(timeout=5)
            deleting.commit()
            result = future.result(timeout=10)

    assert result is PolicyErrorCode.TARGET_NOT_FOUND
    assert repository.policy_history(ACCOUNT_A) == ()
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute(
            "SELECT 1 FROM indexed_accounts WHERE account_key = ?", (ACCOUNT_A,)
        ).fetchone() is None


def test_record_winning_the_lock_is_erased_by_concurrent_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = (_standard_records()[0],)
    repository = _repo_with_records(tmp_path / "record-first-race.db", records)
    selector = _baseline(records).sources[0].selector
    prepared = _prepare(_source_name_command(selector), records)
    inserted = Event()
    release_writer = Event()
    delete_started = Event()
    original_insert = Repository._insert_policy_event

    def paused_insert(
        connection: sqlite3.Connection,
        command: object,
        account_revision: int,
    ) -> None:
        original_insert(connection, command, account_revision)  # type: ignore[arg-type]
        inserted.set()
        if not release_writer.wait(timeout=5):
            raise RuntimeError("synthetic writer barrier timed out")

    def delete_after_signal() -> None:
        delete_started.set()
        repository.delete_account_index(ACCOUNT_A)

    monkeypatch.setattr(Repository, "_insert_policy_event", staticmethod(paused_insert))
    with ThreadPoolExecutor(max_workers=2) as executor:
        write_future = executor.submit(repository.record_policy, prepared)
        assert inserted.wait(timeout=5)
        delete_future = executor.submit(delete_after_signal)
        assert delete_started.wait(timeout=5)
        release_writer.set()
        event = write_future.result(timeout=10)
        delete_future.result(timeout=10)

    assert event.command == prepared.command
    assert repository.policy_history(ACCOUNT_A) == ()
    assert repository.policy_event_for_command(prepared.command) is None
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute(
            "SELECT 1 FROM indexed_accounts WHERE account_key = ?", (ACCOUNT_A,)
        ).fetchone() is None


def test_models_are_closed_frozen_versioned_canonical_and_redacted() -> None:
    records = (_standard_records()[0],)
    selector = _baseline(records).sources[0].selector
    command = _source_name_command(
        selector,
        command_id="command-private-synthetic",
        decision_id="decision-private-synthetic",
        display_name="Valor privado sintetico",
    )
    prepared = _prepare(command, records)

    with pytest.raises(FrozenInstanceError):
        command.display_name = "mutated"  # type: ignore[misc]
    assert not hasattr(command, "__dict__")
    for invalid in (
        {"version": True},
        {"version": 2},
        {"expected_revision": True},
        {"occurred_at": datetime(2026, 8, 27, 15, 0)},
        {"account_key": "private@account.example"},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(command, **invalid)
    with pytest.raises((TypeError, ValueError)):
        replace(selector, version=True)
    with pytest.raises(ValueError, match="ordered"):
        replace(
            command,
            supersedes_decision_ids=("decision-z", "decision-a"),
        )

    private_values = (
        ACCOUNT_A,
        command.command_id,
        command.decision_id,
        command.display_name,
        records[0].sender_address,
        records[0].provider_message_id,
    )
    rendered = " ".join(
        repr(value)
        for value in (
            command,
            selector,
            prepared,
            prepared.anchors[0],
        )
    )
    assert all(value not in rendered for value in private_values if value is not None)
    error = PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
    assert str(error) == PolicyErrorCode.TARGET_NOT_FOUND.value
    assert repr(error) == "PolicyError(code='target_not_found')"
    assert all(value not in f"{error!s} {error!r}" for value in private_values if value)


@pytest.mark.parametrize("corrupt_table", ("event", "anchor", "relation"))
def test_unknown_persisted_policy_versions_are_controlled(
    tmp_path: Path,
    corrupt_table: str,
) -> None:
    records = _standard_records()
    repository = _repo_with_records(tmp_path / f"unknown-{corrupt_table}.db", records)
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    if corrupt_table == "relation":
        beta = _source_for_message(baseline, "message-beta-offer")
        merge = repository.record_policy(
            _prepare(_merge_command((alpha.selector, beta.selector)), records)
        )
        active = repository.active_policies(ACCOUNT_A)
        merged = next(
            source
            for source in _baseline(records, policies=active).sources
            if source.selector.kind is EffectiveSourceKind.MERGED
        )
        command = _source_name_command(
            merged.selector,
            command_id="command-version-relation",
            decision_id="decision-version-relation",
            expected_revision=merge.account_revision,
        )
        repository.record_policy(_prepare(command, records, policies=active))
        statement = (
            "UPDATE local_policy_relations SET policy_version = 2 "
            "WHERE account_key = ? AND account_revision = 2"
        )
    else:
        repository.record_policy(_prepare(_source_name_command(alpha.selector), records))
        table = "local_policy_events" if corrupt_table == "event" else "local_policy_anchors"
        statement = (
            f"UPDATE {table} SET policy_version = 2 "
            "WHERE account_key = ? AND account_revision = 1"
        )
    with sqlite3.connect(repository.path) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute(statement, (ACCOUNT_A,))

    with pytest.raises(PolicyError) as error:
        repository.policy_history(ACCOUNT_A)
    assert error.value.code is PolicyErrorCode.UNKNOWN_POLICY_VERSION
    assert str(error.value) == PolicyErrorCode.UNKNOWN_POLICY_VERSION.value


def test_composite_foreign_keys_reject_cross_account_relations(tmp_path: Path) -> None:
    records_a = (_standard_records(account_key=ACCOUNT_A)[0],)
    records_b = (_standard_records(account_key=ACCOUNT_B)[0],)
    repository = _repo_with_records(tmp_path / "cross-account-fk.db", (*records_a, *records_b))
    event_a = repository.record_policy(
        _prepare(_source_name_command(_baseline(records_a).sources[0].selector), records_a)
    )
    event_b = repository.record_policy(
        _prepare(
            _source_name_command(
                _baseline(records_b).sources[0].selector,
                command_id="command-cross-b",
                decision_id="decision-cross-b",
            ),
            records_b,
        )
    )
    with sqlite3.connect(repository.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO local_policy_relations("
                "account_key, account_revision, relation_order, relation_kind, "
                "anchor_order, target_decision_id, policy_version"
                ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ACCOUNT_A,
                    event_a.account_revision,
                    0,
                    "supersedes",
                    None,
                    cast(SetSourceDisplayName, event_b.command).decision_id,
                    1,
                ),
            )


def test_all_seven_decision_commands_round_trip_through_repository(tmp_path: Path) -> None:
    records = _standard_records()
    baseline = _baseline(records)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    beta = _source_for_message(baseline, "message-beta-offer")
    flow = _flow_for_message(baseline, "message-alpha-alert")
    commands: tuple[PolicyDecisionCommand, ...] = (
        _source_name_command(alpha.selector),
        SetSourceRubro(
            command_id="command-roundtrip-rubro",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=0,
            decision_id="decision-roundtrip-rubro",
            selector=alpha.selector,
            rubro=Rubro.SOFTWARE,
        ),
        SetFlowDisplayName(
            command_id="command-roundtrip-flow-name",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=0,
            decision_id="decision-roundtrip-flow-name",
            selector=flow.selector,
            display_name="Flujo roundtrip sintetico",
        ),
        SetFlowIntention(
            command_id="command-roundtrip-intention",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=0,
            decision_id="decision-roundtrip-intention",
            selector=flow.selector,
            intention=Intencion.NOTIFICACION,
        ),
        _merge_command((alpha.selector, beta.selector)),
        _partition_command(alpha.selector),
        ProtectTarget(
            command_id="command-roundtrip-protect",
            account_key=ACCOUNT_A,
            occurred_at=NOW,
            expected_revision=0,
            decision_id="decision-roundtrip-protect",
            selector=MessageSelector(
                account_key=ACCOUNT_A,
                provider_message_id="message-alpha-alert",
            ),
        ),
    )
    for index, command in enumerate(commands):
        repository = _repo_with_records(tmp_path / f"roundtrip-{index}.db", records)
        prepared = _prepare(command, records)
        event = repository.record_policy(prepared)
        assert event.command == command
        assert event.anchors == prepared.anchors
        assert event.relations == prepared.relations
        assert repository.policy_event_for_command(command) == event
        assert repository.policy_history(ACCOUNT_A) == (event,)


def test_conservative_composition_preserves_worst_confidence_subscription_and_evidence() -> None:
    records = _standard_records()
    classification = _classification(records)
    baseline = _baseline(records, classification=classification)
    alpha = _source_for_message(baseline, "message-alpha-alert")
    beta = _source_for_message(baseline, "message-beta-offer")
    policy = _active(
        _prepare(
            _merge_command((alpha.selector, beta.selector)),
            records,
            classification=classification,
        )
    )
    expected_rubro = (
        alpha.automatic_rubro
        if alpha.automatic_rubro is beta.automatic_rubro
        else Rubro.DESCONOCIDO
    )
    confidence_order = (
        Confianza.ALTA,
        Confianza.MEDIA,
        Confianza.BAJA,
        Confianza.CONTRADICTORIA,
    )
    expected_confidence = max(
        (alpha.automatic_confidence, beta.automatic_confidence),
        key=confidence_order.index,
    )
    subscriptions_before = {
        flow.automatic_flow_id: flow.subscription
        for flow in baseline.flows
        if flow.effective_source_id in {
            alpha.effective_source_id,
            beta.effective_source_id,
        }
    }

    result = _baseline(records, policies=(policy,), classification=classification)
    merged = next(
        source for source in result.sources if source.selector.kind is EffectiveSourceKind.MERGED
    )
    subscriptions_after = {
        flow.automatic_flow_id: flow.subscription
        for flow in result.flows
        if flow.effective_source_id == merged.effective_source_id
    }

    assert merged.automatic_rubro is expected_rubro
    assert merged.effective_rubro is expected_rubro
    assert merged.automatic_confidence is expected_confidence
    assert merged.effective_confidence is expected_confidence
    assert subscriptions_after == subscriptions_before
    assert set(alpha.automatic_evidence).issubset(merged.automatic_evidence)
    assert set(beta.automatic_evidence).issubset(merged.automatic_evidence)
    assert set(merged.automatic_evidence).issubset(merged.effective_evidence)


def test_d5_uses_only_public_d4_models_and_has_no_external_capabilities() -> None:
    project_root = Path(__file__).resolve().parents[1]
    policy_model_path = project_root / "src" / "mailmap" / "policy_model.py"
    policy_domain_path = project_root / "src" / "mailmap" / "policy_domain.py"
    repository_path = project_root / "src" / "mailmap" / "repository.py"

    def imports(path: Path) -> tuple[set[str], set[str]]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: set[str] = set()
        d4_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
                if node.module == "mailmap.classification_model":
                    d4_names.update(alias.name for alias in node.names)
        return modules, d4_names

    model_imports, model_d4_names = imports(policy_model_path)
    domain_imports, domain_d4_names = imports(policy_domain_path)
    repository_imports, repository_d4_names = imports(repository_path)
    forbidden_prefixes = {
        "anthropic",
        "google",
        "googleapiclient",
        "httpx",
        "logging",
        "openai",
        "os",
        "pathlib",
        "playwright",
        "random",
        "requests",
        "selenium",
        "socket",
        "sqlite3",
        "time",
        "urllib",
        "webbrowser",
    }
    allowed_d4_names = {
        "CLASSIFICATION_MODEL_VERSION",
        "ClassificationEvidence",
        "ClassificationResult",
        "ClassifiedFlow",
        "ClassifiedMessage",
        "ClassifiedSource",
        "FlowAnchorKind",
        "FlowIdentityDescriptor",
        "SourceAnchorKind",
        "SourceIdentityDescriptor",
    }

    for modules in (model_imports, domain_imports):
        assert "mailmap.classification_model" in modules
        assert "mailmap.classification_domain" not in modules
        assert all(
            not any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            )
            for module in modules
        )
    assert model_d4_names | domain_d4_names <= allowed_d4_names
    assert all(not name.startswith("_") for name in model_d4_names | domain_d4_names)
    assert "mailmap.policy_model" in repository_imports
    assert "mailmap.classification_model" not in repository_imports
    assert "mailmap.classification_domain" not in repository_imports
    assert repository_d4_names == set()
    combined = (
        policy_model_path.read_text(encoding="utf-8").casefold()
        + policy_domain_path.read_text(encoding="utf-8").casefold()
    )
    assert "classify_indexed_records" not in combined
    assert all(
        marker not in combined
        for marker in (
            "webbrowser.",
            "urlopen(",
            "requests.",
            "httpx.",
            "datetime.now(",
            "datetime.utcnow(",
            "random.",
            "print(",
            "basicconfig(",
        )
    )
