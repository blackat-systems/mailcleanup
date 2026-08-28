from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from mailmap.classification_domain import classify_indexed_records
from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint, SyncMode, SyncState
from mailmap.map_composition import (
    MapSnapshotLike,
    validate_synthetic_snapshot,
)
from mailmap.map_model import MapCompositionError, MapCompositionErrorCode
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SYNTHETIC_MAP_FIXTURE_VERSION,
)
from mailmap.model import Intencion, Rubro
from mailmap.policy_domain import apply_local_policies, prepare_policy_decision
from mailmap.policy_model import (
    ActivePolicy,
    PolicyEvent,
    PreparedPolicyDecision,
    ProtectTarget,
    SenderSelector,
    SetFlowIntention,
    SetSourceDisplayName,
    SetSourceRubro,
    is_policy_decision_command,
)

_BASE_TIME = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)


class SyntheticMapFixtureRepository(Protocol):
    def map_input_snapshot(self, account_key: str) -> MapSnapshotLike: ...

    def install_synthetic_map_fixture(
        self,
        account_key: str,
        fixture_version: str,
        records: tuple[IndexedMessageRecord, ...],
        checkpoint: SyncCheckpoint,
        policy_events: tuple[PolicyEvent, ...],
    ) -> MapSnapshotLike: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class SyntheticMapFixture:
    account_key: str
    fixture_version: str
    records: tuple[IndexedMessageRecord, ...] = field(repr=False)
    checkpoint: SyncCheckpoint = field(repr=False)
    policy_events: tuple[PolicyEvent, ...] = field(repr=False)

    def __repr__(self) -> str:
        return (
            "SyntheticMapFixture("
            f"fixture_version={self.fixture_version!r}, "
            f"record_count={len(self.records)}, "
            f"checkpoint_state={self.checkpoint.state.value!r}, "
            f"policy_event_count={len(self.policy_events)})"
        )


def _record(
    message_id: str,
    *,
    thread_id: str,
    received_at: datetime,
    sender_name: str | None,
    sender_address: str | None,
    subject: str | None,
    labels: tuple[str, ...] = ("INBOX",),
    category: str | None = None,
    size: int = 1024,
    authenticated_domain: str | None = None,
    list_id: str | None = None,
    list_unsubscribe: str | None = None,
    list_unsubscribe_post: str | None = None,
    dkim_result: str | None = "pass",
    dmarc_result: str | None = "pass",
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        provider_message_id=message_id,
        provider_thread_id=thread_id,
        received_at=received_at,
        sender_name=sender_name,
        sender_address=sender_address,
        subject=subject,
        label_ids=labels,
        category=category,
        size_estimate_bytes=size,
        authenticated_domain=authenticated_domain,
        list_id=list_id,
        list_unsubscribe=list_unsubscribe,
        list_unsubscribe_post=list_unsubscribe_post,
        dkim_result=dkim_result,
        dmarc_result=dmarc_result,
    )


def _canonical_records() -> tuple[IndexedMessageRecord, ...]:
    return (
        _record(
            "synthetic-alpha-security",
            thread_id="synthetic-thread-alpha-security",
            received_at=datetime(2026, 1, 15, 13, 0, tzinfo=UTC),
            sender_name="Plataforma Software",
            sender_address="alertas@plataforma-software.example",
            subject="Alerta de seguridad por inicio de sesión",
            labels=("IMPORTANT", "INBOX"),
            category="updates",
            size=1500,
            authenticated_domain="plataforma-software.example",
        ),
        _record(
            "synthetic-alpha-document",
            thread_id="synthetic-thread-alpha-document",
            received_at=datetime(2026, 2, 20, 14, 0, tzinfo=UTC),
            sender_name="Plataforma Software",
            sender_address="facturacion@plataforma-software.example",
            subject="Factura y comprobante disponible",
            labels=("INBOX",),
            category="updates",
            size=2500,
            authenticated_domain="plataforma-software.example",
        ),
        _record(
            "synthetic-alpha-promotion",
            thread_id="synthetic-thread-alpha-promotion",
            received_at=datetime(2026, 3, 1, 2, 30, tzinfo=UTC),
            sender_name="Plataforma Software",
            sender_address="novedades@plataforma-software.example",
            subject="Oferta con descuento de temporada",
            labels=("CATEGORY_PROMOTIONS", "INBOX"),
            category="promotions",
            size=3500,
            authenticated_domain="plataforma-software.example",
            list_id="<promos.plataforma-software.example>",
            list_unsubscribe=(
                "<https://unsubscribe.plataforma-software.example/promociones>"
            ),
            list_unsubscribe_post="List-Unsubscribe=One-Click",
        ),
        _record(
            "synthetic-probable-list",
            thread_id="synthetic-thread-probable",
            received_at=datetime(2026, 3, 5, 15, 0, tzinfo=UTC),
            sender_name=None,
            sender_address="news@lista-probable.example",
            subject=None,
            category=None,
            size=900,
            authenticated_domain=None,
            list_id="<weekly.lista-probable.example>",
            dkim_result="neutral",
            dmarc_result="neutral",
        ),
        _record(
            "synthetic-unknown",
            thread_id="synthetic-thread-unknown",
            received_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            sender_name=None,
            sender_address=None,
            subject=None,
            labels=(),
            category=None,
            size=700,
            authenticated_domain=None,
            dkim_result=None,
            dmarc_result=None,
        ),
        _record(
            "synthetic-contradiction",
            thread_id="synthetic-thread-contradiction",
            received_at=datetime(2026, 5, 10, 16, 30, tzinfo=UTC),
            sender_name="Servicio Contradictorio",
            sender_address="news@contradictorio.example",
            subject="Resumen semanal",
            category="promotions",
            size=1100,
            authenticated_domain=None,
            list_id="<weekly.contradictorio.example>",
            list_unsubscribe="<https://unsubscribe.contradictorio.example/weekly>",
            dkim_result="fail",
            dmarc_result="fail",
        ),
        _record(
            "synthetic-spam",
            thread_id="synthetic-thread-spam",
            received_at=datetime(2026, 6, 12, 18, 0, tzinfo=UTC),
            sender_name="Ofertas Dudosas",
            sender_address="envios@ofertas-dudosas.example",
            subject="Factura con oferta urgente",
            labels=("SPAM",),
            category="promotions",
            size=1200,
            authenticated_domain="ofertas-dudosas.example",
        ),
        _record(
            "synthetic-community-notice",
            thread_id="synthetic-thread-community",
            received_at=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
            sender_name="Comunidad Local",
            sender_address="avisos@comunidad-local.example",
            subject="Notificación de actividad de la comunidad",
            labels=("INBOX",),
            category="updates",
            size=1800,
            authenticated_domain="comunidad-local.example",
        ),
        _record(
            "synthetic-editorial",
            thread_id="synthetic-thread-editorial",
            received_at=datetime(2026, 8, 20, 20, 0, tzinfo=UTC),
            sender_name="Revista Sintética",
            sender_address="boletin@revista-sintetica.example",
            subject="Boletín editorial semanal",
            labels=("INBOX", "STARRED"),
            category="updates",
            size=2100,
            authenticated_domain="revista-sintetica.example",
            list_id="<editorial.revista-sintetica.example>",
            list_unsubscribe="<mailto:baja@revista-sintetica.example>",
        ),
    )


def _active(event: PolicyEvent) -> ActivePolicy:
    if not is_policy_decision_command(event.command):
        raise TypeError("fixture policy events must be decisions")
    return ActivePolicy(
        command=event.command,
        account_revision=event.account_revision,
        anchors=event.anchors,
        relations=event.relations,
    )


def _event(prepared: PreparedPolicyDecision) -> PolicyEvent:
    command = prepared.command
    return PolicyEvent(
        command=command,
        account_revision=command.expected_revision + 1,
        anchors=prepared.anchors,
        relations=prepared.relations,
    )


def _canonical_policy_events(
    records: tuple[IndexedMessageRecord, ...],
) -> tuple[PolicyEvent, ...]:
    original_records = tuple(
        record
        for record in records
        if record.provider_message_id
        not in {"synthetic-alpha-document", "synthetic-alpha-promotion"}
    )
    original_classification = classify_indexed_records(original_records)
    original_view = apply_local_policies(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        original_records,
        original_classification,
        (),
    )
    alpha_source = next(
        source
        for source in original_view.sources
        if "synthetic-alpha-security" in source.message_ids
    )
    review_prepared = prepare_policy_decision(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        records=original_records,
        classification=original_classification,
        active_policies=(),
        command=SetSourceDisplayName(
            command_id="10000000-0000-4000-8000-000000000001",
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            occurred_at=_BASE_TIME,
            expected_revision=0,
            decision_id="20000000-0000-4000-8000-000000000001",
            selector=alpha_source.selector,
            display_name="Plataforma elegida por Joa",
        ),
    )
    review_event = _event(review_prepared)
    policies: tuple[ActivePolicy, ...] = (_active(review_event),)

    classification = classify_indexed_records(records)
    first_view = apply_local_policies(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        records,
        classification,
        policies,
    )
    community_source = next(
        source
        for source in first_view.sources
        if "synthetic-community-notice" in source.message_ids
    )
    rubro_prepared = prepare_policy_decision(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        records=records,
        classification=classification,
        active_policies=policies,
        command=SetSourceRubro(
            command_id="10000000-0000-4000-8000-000000000002",
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            occurred_at=datetime(2026, 3, 1, 2, 31, tzinfo=UTC),
            expected_revision=1,
            decision_id="20000000-0000-4000-8000-000000000002",
            selector=community_source.selector,
            rubro=Rubro.PERSONAL,
        ),
    )
    rubro_event = _event(rubro_prepared)
    policies = (*policies, _active(rubro_event))

    second_view = apply_local_policies(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        records,
        classification,
        policies,
    )
    community_flow = next(
        flow
        for flow in second_view.flows
        if "synthetic-community-notice" in flow.message_ids
    )
    intention_prepared = prepare_policy_decision(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        records=records,
        classification=classification,
        active_policies=policies,
        command=SetFlowIntention(
            command_id="10000000-0000-4000-8000-000000000003",
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            occurred_at=datetime(2026, 3, 1, 2, 32, tzinfo=UTC),
            expected_revision=2,
            decision_id="20000000-0000-4000-8000-000000000003",
            selector=community_flow.selector,
            intention=Intencion.EDITORIAL,
        ),
    )
    intention_event = _event(intention_prepared)
    policies = (*policies, _active(intention_event))

    protect_prepared = prepare_policy_decision(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        records=records,
        classification=classification,
        active_policies=policies,
        command=ProtectTarget(
            command_id="10000000-0000-4000-8000-000000000004",
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            occurred_at=datetime(2026, 3, 1, 2, 33, tzinfo=UTC),
            expected_revision=3,
            decision_id="20000000-0000-4000-8000-000000000004",
            selector=SenderSelector(
                account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
                sender_address="avisos@comunidad-local.example",
            ),
        ),
    )
    protect_event = _event(protect_prepared)
    return (review_event, rubro_event, intention_event, protect_event)


def canonical_synthetic_map_fixture() -> SyntheticMapFixture:
    records = _canonical_records()
    return SyntheticMapFixture(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
        records=records,
        checkpoint=SyncCheckpoint(
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            scan_id="synthetic-map-scan-v1",
            mode=SyncMode.FULL,
            state=SyncState.COMPLETED,
            page_token=None,
            history_id="synthetic-map-history-v1",
            processed_count=len(records),
            started_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 8, 27, 12, 1, tzinfo=UTC),
            error_code=None,
        ),
        policy_events=_canonical_policy_events(records),
    )


def ensure_synthetic_map_fixture(
    repository: SyntheticMapFixtureRepository,
) -> MapSnapshotLike:
    snapshot = repository.map_input_snapshot(SYNTHETIC_MAP_ACCOUNT_KEY)
    if snapshot.account_exists:
        validate_synthetic_snapshot(snapshot)
        fixture = canonical_synthetic_map_fixture()
        current_records = tuple(
            sorted(snapshot.records, key=lambda item: item.provider_message_id)
        )
        expected_records = tuple(
            sorted(fixture.records, key=lambda item: item.provider_message_id)
        )
        if (
            current_records != expected_records
            or snapshot.checkpoint != fixture.checkpoint
            or snapshot.policy_history[: len(fixture.policy_events)]
            != fixture.policy_events
        ):
            raise MapCompositionError(MapCompositionErrorCode.MAP_UNAVAILABLE)
        return snapshot
    if snapshot.indexed_account_keys or snapshot.fixture_version is not None:
        raise MapCompositionError(MapCompositionErrorCode.MAP_UNAVAILABLE)
    if (
        snapshot.records
        or snapshot.checkpoint is not None
        or snapshot.policy_history
        or snapshot.active_policies
        or snapshot.policy_revision != 0
    ):
        raise MapCompositionError(MapCompositionErrorCode.MAP_UNAVAILABLE)

    fixture = canonical_synthetic_map_fixture()
    repository.install_synthetic_map_fixture(
        fixture.account_key,
        fixture.fixture_version,
        fixture.records,
        fixture.checkpoint,
        fixture.policy_events,
    )
    installed = repository.map_input_snapshot(SYNTHETIC_MAP_ACCOUNT_KEY)
    validate_synthetic_snapshot(installed)
    return installed
