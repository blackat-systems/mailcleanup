from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mailmap.classification_domain import classify_indexed_records
from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint, SyncState
from mailmap.map_composition import (
    MapCompositionResult,
    compose_map,
)
from mailmap.map_fixtures import (
    canonical_synthetic_map_fixture,
    ensure_synthetic_map_fixture,
)
from mailmap.map_model import (
    MapClassificationEvidence,
    MapCompositionError,
    MapCompositionErrorCode,
    MapMessageSample,
    MapPolicyEvidence,
    MapProjection,
    MapSource,
)
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SYNTHETIC_MAP_FIXTURE_VERSION,
)
from mailmap.model import Confianza, Intencion, Proteccion, Rubro, Suscripcion
from mailmap.policy_model import (
    ActivePolicy,
    PartitionGroup,
    PartitionSource,
    PolicyBindingStatus,
    PolicyEvent,
    SetSourceDisplayName,
    is_policy_decision_command,
)
from mailmap.repository import MapInputSnapshot, Repository

_FIXTURE_CHECKPOINT = object()


def _active(event: PolicyEvent) -> ActivePolicy:
    command = event.command
    if not is_policy_decision_command(command):
        raise AssertionError("fixture event must be a decision")
    return ActivePolicy(
        command=command,
        account_revision=event.account_revision,
        anchors=event.anchors,
        relations=event.relations,
    )


def _snapshot(
    *,
    records: tuple[IndexedMessageRecord, ...] | None = None,
    checkpoint: SyncCheckpoint | None | object = _FIXTURE_CHECKPOINT,
    history: tuple[PolicyEvent, ...] | None = None,
    input_revision: str = (
        "input-v1-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ),
) -> MapInputSnapshot:
    fixture = canonical_synthetic_map_fixture()
    selected_history = fixture.policy_events if history is None else history
    selected_records = fixture.records if records is None else records
    if checkpoint is _FIXTURE_CHECKPOINT:
        selected_checkpoint: SyncCheckpoint | None = fixture.checkpoint
    elif checkpoint is None or isinstance(checkpoint, SyncCheckpoint):
        selected_checkpoint = checkpoint
    else:
        raise TypeError("checkpoint test value is invalid")
    return MapInputSnapshot(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        account_exists=True,
        indexed_account_keys=(SYNTHETIC_MAP_ACCOUNT_KEY,),
        fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
        records=selected_records,
        checkpoint=selected_checkpoint,
        policy_history=selected_history,
        active_policies=tuple(_active(event) for event in selected_history),
        policy_revision=len(selected_history),
        input_revision=input_revision,
    )


def _result() -> MapCompositionResult:
    return compose_map(_snapshot())


def test_canonical_fixture_exercises_required_classification_and_policy_states() -> None:
    fixture = canonical_synthetic_map_fixture()
    classification = classify_indexed_records(fixture.records)
    result = _result()

    assert {message.suscripcion for message in classification.messages} >= {
        Suscripcion.CONFIRMADA,
        Suscripcion.PROBABLE,
        Suscripcion.DESCONOCIDO,
        Suscripcion.POSIBLE_INCUMPLIMIENTO,
    }
    assert {message.confianza for message in classification.messages} == {
        Confianza.ALTA,
        Confianza.MEDIA,
        Confianza.BAJA,
        Confianza.CONTRADICTORIA,
    }
    assert any(message.intencion is Intencion.SOSPECHOSO for message in classification.messages)

    alpha = next(
        source
        for source in result.effective.sources
        if "synthetic-alpha-security" in source.message_ids
    )
    assert len(alpha.message_ids) == 3
    assert len(alpha.flow_ids) == 3
    assert {binding.status for binding in result.effective.bindings} >= {
        PolicyBindingStatus.EXACT,
        PolicyBindingStatus.NEEDS_REVIEW,
    }
    community = next(
        message
        for message in result.effective.messages
        if message.provider_message_id == "synthetic-community-notice"
    )
    assert community.automatic_rubro is Rubro.SOCIAL
    assert community.effective_rubro is Rubro.PERSONAL
    assert community.automatic_intention is Intencion.NOTIFICACION
    assert community.effective_intention is Intencion.EDITORIAL
    assert community.effective_protection is Proteccion.USUARIO


def test_map_summary_order_sync_and_cordoba_months_are_deterministic() -> None:
    result = _result()
    projection = result.projection

    assert projection.summary.message_count == 9
    assert projection.summary.source_count == 7
    assert projection.summary.flow_count == 9
    assert projection.summary.total_bytes == 15_300
    assert projection.summary.first_seen == datetime(2026, 1, 15, 13, 0, tzinfo=UTC)
    assert projection.summary.last_seen == datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    assert projection.sync.state is SyncState.COMPLETED
    assert projection.sync.partial is False

    source_order = tuple(
        (-source.message_count, source.effective_display_name.casefold(), source.id)
        for source in projection.sources
    )
    assert source_order == tuple(sorted(source_order))
    assert all(
        tuple(
            (-flow.message_count, flow.effective_display_name.casefold(), flow.id)
            for flow in source.flows
        )
        == tuple(
            sorted(
                (
                    -flow.message_count,
                    flow.effective_display_name.casefold(),
                    flow.id,
                )
                for flow in source.flows
            )
        )
        for source in projection.sources
    )

    alpha = next(source for source in projection.sources if source.message_count == 3)
    assert tuple((item.month, item.message_count) for item in alpha.monthly_volume) == (
        ("2026-01", 1),
        ("2026-02", 2),
    )


def test_composition_uses_one_materialized_record_set_and_ignores_input_order() -> None:
    original = _snapshot(input_revision="input-v1-" + "b" * 64)
    reversed_snapshot = replace(original, records=tuple(reversed(original.records)))

    first = compose_map(original)
    second = compose_map(reversed_snapshot)

    assert first.projection == second.projection
    assert first.classification == second.classification
    assert first.effective == second.effective
    assert first.projection.map_revision == second.projection.map_revision


def test_empty_and_non_completed_snapshots_are_explicitly_partial() -> None:
    empty = MapInputSnapshot(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        account_exists=True,
        indexed_account_keys=(SYNTHETIC_MAP_ACCOUNT_KEY,),
        fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
        records=(),
        checkpoint=None,
        policy_history=(),
        active_policies=(),
        policy_revision=0,
        input_revision="input-v1-" + "c" * 64,
    )
    empty_projection = compose_map(empty).projection
    assert empty_projection.summary.message_count == 0
    assert empty_projection.sync.state is SyncState.NOT_STARTED
    assert empty_projection.sync.partial is True
    assert empty_projection.sources == ()

    fixture = canonical_synthetic_map_fixture()
    paused = replace(
        fixture.checkpoint,
        state=SyncState.PAUSED,
        page_token="synthetic-page-token",
    )
    partial = compose_map(_snapshot(checkpoint=paused)).projection
    assert partial.sync.state is SyncState.PAUSED
    assert partial.sync.partial is True


@pytest.mark.parametrize("field_name", ("sender_name", "subject"))
def test_synthetic_gate_rejects_real_url_hosts_in_any_textual_metadata(
    field_name: str,
) -> None:
    snapshot = _snapshot()
    record = replace(
        snapshot.records[0],
        **{
            field_name: "Ver https://" + "host-no-sintetico.test/privado",
        },
    )
    changed = replace(snapshot, records=(record, *snapshot.records[1:]))

    with pytest.raises(MapCompositionError) as error:
        compose_map(changed)
    assert error.value.code is MapCompositionErrorCode.MAP_UNAVAILABLE


def test_synthetic_gate_rejects_wrong_marker_accounts_and_real_addresses() -> None:
    snapshot = _snapshot()
    cases = (
        replace(snapshot, fixture_version="another-fixture"),
        replace(
            snapshot,
            indexed_account_keys=(SYNTHETIC_MAP_ACCOUNT_KEY, "unexpected-account"),
        ),
        replace(
            snapshot,
            records=(
                replace(
                    snapshot.records[0],
                    sender_address="persona@" + "host-no-sintetico.test",
                ),
                *snapshot.records[1:],
            ),
        ),
    )
    for candidate in cases:
        with pytest.raises(MapCompositionError) as error:
            compose_map(candidate)
        assert error.value.code is MapCompositionErrorCode.MAP_UNAVAILABLE


def test_local_message_ids_detail_and_representations_do_not_leak_remote_identity() -> None:
    result = _result()
    samples = result.samples
    provider_ids = {record.provider_message_id for record in result.records}

    assert len({sample.id for sample in samples}) == len(samples)
    assert all(sample.id.startswith("message-v1-") and len(sample.id) == 75 for sample in samples)
    assert all(provider_id not in repr(result) for provider_id in provider_ids)
    assert all(
        provider_id not in repr(sample)
        for sample in samples
        for provider_id in provider_ids
    )

    source = result.projection.sources[0]
    detail = result.source_detail(source.id)
    assert detail is not None
    assert len(detail.recent_messages) <= 5
    ordering = tuple((-item.received_at.timestamp(), item.id) for item in detail.recent_messages)
    assert ordering == tuple(sorted(ordering))
    assert {field.name for field in fields(MapMessageSample)} == {
        "id",
        "received_at",
        "sender_name",
        "sender_address",
        "subject",
        "label_ids",
        "category",
        "size_estimate_bytes",
        "source_id",
        "flow_id",
        "automatic_rubro",
        "effective_rubro",
        "automatic_intention",
        "effective_intention",
        "subscription",
        "automatic_confidence",
        "effective_confidence",
        "protection",
    }


def test_internal_lookups_resolve_server_side_without_entering_public_projection() -> None:
    result = _result()
    source = next(
        item for item in result.projection.sources if not item.decision_ids and item.senders
    )
    flow = source.flows[0]
    message = next(item for item in result.samples if item.source_id == source.id)

    assert result.resolve_source(source.id) is not None
    assert result.resolve_flow(flow.id) is not None
    assert result.resolve_message(message.id) is not None
    assert result.record_for_message(message.id) is not None
    assert result.resolve_sender(source.senders[0]) is not None
    assert result.resolve_label("IMPORTANT") is not None
    assert result.resolve_source("effective-source-v1-" + "0" * 24) is None
    assert "account_key" not in {field.name for field in fields(MapProjection)}
    assert "provider_message_id" not in {field.name for field in fields(MapMessageSample)}

    command = SetSourceDisplayName(
        command_id="30000000-0000-4000-8000-000000000001",
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        occurred_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        expected_revision=result.projection.policy_revision,
        decision_id="40000000-0000-4000-8000-000000000001",
        selector=result.resolve_source(source.id),  # type: ignore[arg-type]
        display_name="Nombre sintético actualizado",
    )
    prepared = result.prepare_decision(command)
    assert prepared.command is command
    assert prepared.anchors[0].observed_effective_id == source.id


def test_source_senders_and_domains_come_only_from_effective_members() -> None:
    result = _result()
    records_by_remote_id = {record.provider_message_id: record for record in result.records}
    messages_by_source: dict[str, list[str]] = {}
    for message in result.effective.messages:
        messages_by_source.setdefault(message.effective_source_id, []).append(
            message.provider_message_id
        )

    for source in result.projection.sources:
        records = tuple(records_by_remote_id[item] for item in messages_by_source[source.id])
        expected_senders = tuple(
            sorted(
                {record.sender_address for record in records if record.sender_address is not None},
                key=lambda value: (value.casefold(), value),
            )
        )
        expected_domains = {
            record.authenticated_domain.casefold()
            for record in records
            if record.authenticated_domain is not None
        }
        expected_domains.update(
            sender.rsplit("@", 1)[-1].casefold() for sender in expected_senders
        )
        assert source.senders == expected_senders
        assert source.domains == tuple(sorted(expected_domains))


def test_partitioned_source_recomputes_member_metadata_without_cross_contamination() -> None:
    base = _result()
    alpha = next(source for source in base.projection.sources if source.message_count == 3)
    anchors = base.canonical_partition_anchors(alpha.id)
    assert len(anchors) == 3
    command = PartitionSource(
        command_id="30000000-0000-4000-8000-000000000002",
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        occurred_at=datetime(2026, 8, 27, 18, 1, tzinfo=UTC),
        expected_revision=base.projection.policy_revision,
        decision_id="40000000-0000-4000-8000-000000000002",
        source_selector=base.resolve_source(alpha.id),  # type: ignore[arg-type]
        groups=tuple(PartitionGroup(anchors=(anchor,)) for anchor in anchors),
    )
    prepared = base.prepare_decision(command)
    event = PolicyEvent(
        command=command,
        account_revision=command.expected_revision + 1,
        anchors=prepared.anchors,
        relations=prepared.relations,
    )
    snapshot = _snapshot(
        history=(*canonical_synthetic_map_fixture().policy_events, event),
        input_revision="input-v1-" + "d" * 64,
    )
    partitioned = compose_map(snapshot)
    groups = tuple(
        source
        for source in partitioned.projection.sources
        if alpha.automatic_source_ids[0] in source.automatic_source_ids
    )

    assert len(groups) == 3
    assert all(source.message_count == 1 for source in groups)
    assert all(len(source.senders) == 1 for source in groups)
    assert len({source.senders[0] for source in groups}) == 3


def test_policy_review_is_visible_and_affected_messages_remain_protected() -> None:
    result = _result()
    review = result.projection.policy_review
    assert review.total == 1
    assert review.bindings[0].status is PolicyBindingStatus.NEEDS_REVIEW
    affected = set(result.effective.bindings[0].affected_message_ids)
    assert affected
    assert all(
        message.protected and message.review_required
        for message in result.effective.messages
        if message.provider_message_id in affected
    )


def test_automatic_and_effective_evidence_are_separate_closed_unions() -> None:
    result = _result()
    source = next(
        source
        for source in result.projection.sources
        if source.effective_rubro is Rubro.PERSONAL
    )
    assert all(isinstance(item, MapClassificationEvidence) for item in source.automatic_evidence)
    assert set(source.automatic_evidence).issubset(source.effective_evidence)
    assert any(isinstance(item, MapPolicyEvidence) for item in source.effective_evidence)

    forbidden = {
        "candidate",
        "candidate_count",
        "recommendation",
        "recoverable_bytes",
        "archive",
        "trash",
        "execute",
    }
    assert forbidden.isdisjoint({field.name for field in fields(MapProjection)})
    assert forbidden.isdisjoint({field.name for field in fields(MapSource)})


def test_decision_history_is_closed_redacted_and_ordered() -> None:
    result = _result()
    history = result.decision_history()

    assert history.policy_revision == 4
    assert tuple(event.revision for event in history.events) == (1, 2, 3, 4)
    assert tuple(event.type for event in history.events) == (
        "setSourceDisplayName",
        "setSourceRubro",
        "setFlowIntention",
        "protectTarget",
    )
    assert history.events[0].binding_status is PolicyBindingStatus.NEEDS_REVIEW
    assert all(event.active and event.undoable for event in history.events)
    rendered = repr(history.events)
    for record in result.records:
        assert record.provider_message_id not in rendered
        assert (record.sender_address or "not-present") not in rendered


def test_models_are_frozen_closed_and_repr_redacts_private_metadata() -> None:
    result = _result()
    projection = result.projection
    with pytest.raises(FrozenInstanceError):
        projection.policy_revision = 99  # type: ignore[misc]
    with pytest.raises(AttributeError):
        _ = projection.__dict__
    with pytest.raises(AttributeError):
        _ = result.__dict__
    rendered = repr(result)
    assert "Plataforma Software" not in rendered
    assert "@" not in rendered


def test_fixture_installation_is_atomic_idempotent_and_refuses_unexpected_state(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "fixture.db")
    first = ensure_synthetic_map_fixture(repository)
    second = ensure_synthetic_map_fixture(repository)

    assert first.input_revision == second.input_revision
    assert first.indexed_account_keys == (SYNTHETIC_MAP_ACCOUNT_KEY,)
    assert first.fixture_version == SYNTHETIC_MAP_FIXTURE_VERSION
    assert first.policy_revision == 4

    unexpected = Repository(tmp_path / "unexpected.db")
    fixture = canonical_synthetic_map_fixture()
    foreign_record = replace(
        fixture.records[0],
        account_key="unexpected-synthetic-account",
    )
    foreign_checkpoint = replace(
        fixture.checkpoint,
        account_key="unexpected-synthetic-account",
        scan_id="unexpected-synthetic-scan",
    )
    unexpected.apply_index_page(
        "unexpected-synthetic-account",
        (foreign_record,),
        (),
        foreign_checkpoint,
    )

    with pytest.raises(MapCompositionError) as error:
        ensure_synthetic_map_fixture(unexpected)
    assert error.value.code is MapCompositionErrorCode.MAP_UNAVAILABLE
    assert unexpected.indexed_messages("unexpected-synthetic-account") == (foreign_record,)
