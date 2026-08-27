from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime

import pytest

from mailmap.classification_domain import classify_indexed_records
from mailmap.classification_model import (
    CLASSIFICATION_MODEL_VERSION,
    IDENTITY_DESCRIPTOR_VERSION,
    ClassificationError,
    ClassificationErrorCode,
    ClassificationEvidence,
    ClassificationResult,
    ClassifiedFlow,
    ClassifiedMessage,
    ClassifiedSource,
    EvidenceCode,
    EvidenceOrigin,
    EvidenceStrength,
    FlowAnchorKind,
    FlowIdentityDescriptor,
    SourceAnchorKind,
    SourceIdentityDescriptor,
)
from mailmap.index_model import IndexedMessageRecord
from mailmap.model import Confianza, Intencion, Rubro, Suscripcion

ACCOUNT = "account-synthetic-d4"
RECEIVED_AT = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def indexed_record(
    message_id: str,
    *,
    account_key: str = ACCOUNT,
    sender_name: str | None = "Servicio Software",
    sender_address: str | None = "avisos@software-norte.example",
    subject: str | None = "Notificación de estado",
    labels: tuple[str, ...] = ("INBOX",),
    category: str | None = None,
    authenticated_domain: str | None = "software-norte.example",
    list_id: str | None = None,
    list_unsubscribe: str | None = None,
    list_unsubscribe_post: str | None = None,
    dkim_result: str | None = "pass",
    dmarc_result: str | None = "pass",
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=message_id,
        provider_thread_id=f"thread-{message_id}",
        received_at=RECEIVED_AT,
        sender_name=sender_name,
        sender_address=sender_address,
        subject=subject,
        label_ids=labels,
        category=category,
        size_estimate_bytes=1024,
        authenticated_domain=authenticated_domain,
        list_id=list_id,
        list_unsubscribe=list_unsubscribe,
        list_unsubscribe_post=list_unsubscribe_post,
        dkim_result=dkim_result,
        dmarc_result=dmarc_result,
    )


def message_by_id(result: ClassificationResult, message_id: str) -> ClassifiedMessage:
    return next(
        message for message in result.messages if message.provider_message_id == message_id
    )


def evidence_codes(
    value: ClassifiedMessage | ClassifiedSource | ClassifiedFlow,
) -> set[EvidenceCode]:
    return {item.code for item in value.evidence}


def test_identity_descriptor_models_are_closed_frozen_and_versioned() -> None:
    source = SourceIdentityDescriptor(
        kind=SourceAnchorKind.SENDERS,
        sender_addresses=("sender@descriptor.example",),
        isolated_message_id=None,
    )
    flow = FlowIdentityDescriptor(
        kind=FlowAnchorKind.SENDER_INTENT,
        source=source,
        list_id=None,
        sender_address="sender@descriptor.example",
        automatic_intention=Intencion.NOTIFICACION,
        isolated_message_id=None,
    )

    assert CLASSIFICATION_MODEL_VERSION == 2
    assert IDENTITY_DESCRIPTOR_VERSION == 1
    assert tuple(item.value for item in SourceAnchorKind) == (
        "senders",
        "isolated_message",
    )
    assert tuple(item.value for item in FlowAnchorKind) == (
        "list_intent",
        "sender_intent",
        "isolated_message",
    )
    assert tuple(item.name for item in fields(SourceIdentityDescriptor)) == (
        "kind",
        "sender_addresses",
        "isolated_message_id",
        "version",
    )
    assert tuple(item.name for item in fields(FlowIdentityDescriptor)) == (
        "kind",
        "source",
        "list_id",
        "sender_address",
        "automatic_intention",
        "isolated_message_id",
        "version",
    )
    assert not hasattr(source, "__dict__")
    assert not hasattr(flow, "__dict__")

    with pytest.raises(FrozenInstanceError):
        source.kind = SourceAnchorKind.ISOLATED_MESSAGE  # type: ignore[misc]
    with pytest.raises(TypeError):
        SourceIdentityDescriptor(  # type: ignore[call-arg]
            kind=SourceAnchorKind.SENDERS,
            sender_addresses=("sender@descriptor.example",),
            isolated_message_id=None,
            arbitrary="not-allowed",
        )
    with pytest.raises(ValueError, match="version"):
        replace(source, version=True)
    with pytest.raises(ValueError, match="version"):
        replace(source, version=1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="version"):
        replace(flow, version=IDENTITY_DESCRIPTOR_VERSION + 1)
    with pytest.raises(ValueError, match="version"):
        replace(flow, version=1.0)  # type: ignore[arg-type]

    result = classify_indexed_records((indexed_record("descriptor-version"),))
    with pytest.raises(ValueError, match="version"):
        replace(result, version=2.0)  # type: ignore[arg-type]


def test_source_identity_descriptor_enforces_kind_invariants() -> None:
    isolated = SourceIdentityDescriptor(
        kind=SourceAnchorKind.ISOLATED_MESSAGE,
        sender_addresses=(),
        isolated_message_id="isolated-provider-id",
    )
    assert isolated.isolated_message_id == "isolated-provider-id"

    invalid_values = (
        {
            "kind": SourceAnchorKind.SENDERS,
            "sender_addresses": (),
            "isolated_message_id": None,
        },
        {
            "kind": SourceAnchorKind.SENDERS,
            "sender_addresses": ("sender@descriptor.example",),
            "isolated_message_id": "unexpected-id",
        },
        {
            "kind": SourceAnchorKind.ISOLATED_MESSAGE,
            "sender_addresses": ("sender@descriptor.example",),
            "isolated_message_id": None,
        },
        {
            "kind": SourceAnchorKind.SENDERS,
            "sender_addresses": (
                "second@descriptor.example",
                "first@descriptor.example",
            ),
            "isolated_message_id": None,
        },
        {
            "kind": SourceAnchorKind.SENDERS,
            "sender_addresses": ("Sender@descriptor.example",),
            "isolated_message_id": None,
        },
    )
    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            SourceIdentityDescriptor(**value)  # type: ignore[arg-type]


def test_flow_identity_descriptor_enforces_kind_invariants() -> None:
    source = SourceIdentityDescriptor(
        kind=SourceAnchorKind.SENDERS,
        sender_addresses=("sender@descriptor.example",),
        isolated_message_id=None,
    )
    list_flow = FlowIdentityDescriptor(
        kind=FlowAnchorKind.LIST_INTENT,
        source=source,
        list_id="weekly.descriptor.example",
        sender_address=None,
        automatic_intention=Intencion.EDITORIAL,
        isolated_message_id=None,
    )
    isolated_flow = FlowIdentityDescriptor(
        kind=FlowAnchorKind.ISOLATED_MESSAGE,
        source=source,
        list_id=None,
        sender_address=None,
        automatic_intention=Intencion.SOSPECHOSO,
        isolated_message_id="isolated-flow-id",
    )
    assert list_flow.list_id == "weekly.descriptor.example"
    assert isolated_flow.isolated_message_id == "isolated-flow-id"

    with pytest.raises(ValueError, match="List-ID"):
        replace(list_flow, list_id="<Weekly.Descriptor.Example>")
    with pytest.raises(ValueError, match="invalid anchors"):
        replace(list_flow, sender_address="sender@descriptor.example")
    with pytest.raises(ValueError, match="does not belong"):
        FlowIdentityDescriptor(
            kind=FlowAnchorKind.SENDER_INTENT,
            source=source,
            list_id=None,
            sender_address="other@descriptor.example",
            automatic_intention=Intencion.NOTIFICACION,
            isolated_message_id=None,
        )
    isolated_source = SourceIdentityDescriptor(
        kind=SourceAnchorKind.ISOLATED_MESSAGE,
        sender_addresses=(),
        isolated_message_id="source-isolated-id",
    )
    with pytest.raises(ValueError, match="requires a sender source"):
        replace(list_flow, source=isolated_source)
    with pytest.raises(ValueError, match="same message"):
        replace(isolated_flow, source=isolated_source)
    with pytest.raises(TypeError, match="automatic_intention"):
        replace(list_flow, automatic_intention="Editorial")  # type: ignore[arg-type]


def test_public_descriptors_follow_current_source_and_flow_identity() -> None:
    multi_source = classify_indexed_records(
        (
            indexed_record(
                "descriptor-multi-01",
                sender_name="Plataforma Software",
                sender_address="alertas@plataforma-software.example",
                authenticated_domain="plataforma-software.example",
            ),
            indexed_record(
                "descriptor-multi-02",
                sender_name="Plataforma Software",
                sender_address="facturacion@plataforma-software.example",
                authenticated_domain="plataforma-software.example",
            ),
        )
    ).sources[0]
    assert multi_source.identity_descriptor.kind is SourceAnchorKind.SENDERS
    assert (
        multi_source.identity_descriptor.sender_addresses
        == multi_source.sender_addresses
    )

    missing = classify_indexed_records(
        (
            indexed_record(
                "descriptor-missing",
                sender_name=None,
                sender_address=None,
                subject=None,
                authenticated_domain=None,
                dkim_result=None,
                dmarc_result=None,
            ),
        )
    )
    assert missing.sources[0].identity_descriptor.kind is SourceAnchorKind.ISOLATED_MESSAGE
    assert (
        missing.sources[0].identity_descriptor.isolated_message_id
        == "descriptor-missing"
    )
    assert missing.flows[0].identity_descriptor.kind is FlowAnchorKind.ISOLATED_MESSAGE

    listed = classify_indexed_records(
        (
            indexed_record(
                "descriptor-list",
                subject="Resumen semanal",
                list_id="<Weekly.Software-Norte.Example>",
                list_unsubscribe="<https://unsubscribe.software-norte.example/weekly>",
            ),
        )
    )
    assert listed.flows[0].identity_descriptor.kind is FlowAnchorKind.LIST_INTENT
    assert listed.flows[0].identity_descriptor.list_id == "weekly.software-norte.example"

    sender_flow = classify_indexed_records((indexed_record("descriptor-sender"),))
    assert (
        sender_flow.flows[0].identity_descriptor.kind
        is FlowAnchorKind.SENDER_INTENT
    )
    assert (
        sender_flow.flows[0].identity_descriptor.sender_address
        == "avisos@software-norte.example"
    )

    contradictory = classify_indexed_records(
        (
            indexed_record(
                "descriptor-contradiction",
                sender_address="alertas@identity-a.example",
                authenticated_domain="identity-b.example",
            ),
        )
    )
    assert (
        contradictory.flows[0].identity_descriptor.kind
        is FlowAnchorKind.ISOLATED_MESSAGE
    )
    for result in (missing, listed, sender_flow, contradictory):
        flow = result.flows[0]
        source = next(item for item in result.sources if item.source_id == flow.source_id)
        assert flow.identity_descriptor.source == source.identity_descriptor
        assert flow.identity_descriptor.automatic_intention is flow.intencion


def test_descriptor_changes_when_membership_changes_even_if_source_id_does_not() -> None:
    first = indexed_record(
        "descriptor-membership-01",
        sender_name="Plataforma Software",
        sender_address="alertas@plataforma-software.example",
        authenticated_domain="plataforma-software.example",
    )
    second = indexed_record(
        "descriptor-membership-02",
        sender_name="Plataforma Software",
        sender_address="facturacion@plataforma-software.example",
        authenticated_domain="plataforma-software.example",
    )

    original = classify_indexed_records((first,)).sources[0]
    expanded = classify_indexed_records((first, second)).sources[0]

    assert original.source_id == expanded.source_id
    assert original.identity_descriptor != expanded.identity_descriptor
    assert expanded.identity_descriptor.sender_addresses == (
        "alertas@plataforma-software.example",
        "facturacion@plataforma-software.example",
    )


def test_public_descriptors_preserve_a_literal_d4_semantic_baseline() -> None:
    result = classify_indexed_records((indexed_record("descriptor-regression"),))
    message = result.messages[0]
    source = result.sources[0]
    flow = result.flows[0]

    assert source.source_id == "source-v1-6ffcec499ca5e64671a0fa6b"
    assert flow.flow_id == "flow-v1-855a37aba8864e1fca7aa3c6"
    assert (
        message.source_id,
        message.flow_id,
        message.rubro,
        message.intencion,
        message.suscripcion,
        message.confianza,
    ) == (
        source.source_id,
        flow.flow_id,
        Rubro.SOFTWARE,
        Intencion.NOTIFICACION,
        Suscripcion.DESCONOCIDO,
        Confianza.MEDIA,
    )
    assert tuple(item.code.value for item in message.evidence) == (
        "authentication.dkim_passed",
        "authentication.dmarc_passed",
        "authentication.domain_coherent",
        "flow.sender_intent",
        "intent.notification",
        "rubro.generic_signal",
        "source.authenticated",
        "subscription.unknown",
    )


def test_empty_input_and_same_sender_identity_are_stable() -> None:
    assert classify_indexed_records(()) == ClassificationResult(
        account_key=None,
        messages=(),
        sources=(),
        flows=(),
    )

    first = indexed_record("same-sender-01", subject="Notificación de estado")
    second = indexed_record("same-sender-02", subject="Ticket de soporte abierto")
    result = classify_indexed_records((first, second))

    assert len(result.sources) == 1
    assert {message.source_id for message in result.messages} == {
        result.sources[0].source_id
    }
    assert result.sources[0].sender_addresses == (
        "avisos@software-norte.example",
    )
    assert (
        classify_indexed_records((first,)).sources[0].source_id
        == classify_indexed_records((second,)).sources[0].source_id
    )


def test_multiple_coherent_authenticated_addresses_merge_one_source() -> None:
    records = (
        indexed_record(
            "multi-address-01",
            sender_name="Plataforma Software",
            sender_address="alertas@plataforma-software.example",
            authenticated_domain="plataforma-software.example",
        ),
        indexed_record(
            "multi-address-02",
            sender_name="Plataforma Software",
            sender_address="facturacion@plataforma-software.example",
            authenticated_domain="plataforma-software.example",
            subject="Factura disponible",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 1
    assert result.sources[0].sender_addresses == (
        "alertas@plataforma-software.example",
        "facturacion@plataforma-software.example",
    )
    assert EvidenceCode.SOURCE_MERGED in evidence_codes(result.sources[0])
    assert result.sources[0].rubro is Rubro.SOFTWARE


def test_same_sender_id_survives_name_and_authentication_changes() -> None:
    authenticated = indexed_record(
        "stable-address-01",
        sender_name="Nombre Visible Inicial",
        sender_address="stable@identity.example",
        authenticated_domain="identity.example",
    )
    weak = indexed_record(
        "stable-address-02",
        sender_name="Nombre Visible Diferente",
        sender_address="stable@identity.example",
        authenticated_domain=None,
        dkim_result="neutral",
        dmarc_result="unknown",
    )

    authenticated_source = classify_indexed_records((authenticated,)).sources[0]
    weak_source = classify_indexed_records((weak,)).sources[0]
    combined = classify_indexed_records((authenticated, weak))

    assert authenticated_source.source_id == weak_source.source_id
    assert combined.sources[0].source_id == authenticated_source.source_id


def test_shared_infrastructure_without_visible_identity_does_not_merge() -> None:
    records = (
        indexed_record(
            "shared-infra-01",
            sender_name=None,
            sender_address="envios@alpha.mailer.example",
            authenticated_domain="mailer.example",
            subject=None,
        ),
        indexed_record(
            "shared-infra-02",
            sender_name=None,
            sender_address="envios@beta.mailer.example",
            authenticated_domain="mailer.example",
            subject=None,
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 2
    assert {source.sender_addresses for source in result.sources} == {
        ("envios@alpha.mailer.example",),
        ("envios@beta.mailer.example",),
    }


def test_distinct_visible_sources_using_same_provider_stay_separate() -> None:
    records = (
        indexed_record(
            "provider-brand-01",
            sender_name="Tienda Norte",
            sender_address="news@tienda.mailer.example",
            authenticated_domain="mailer.example",
            subject="Oferta semanal",
        ),
        indexed_record(
            "provider-brand-02",
            sender_name="Viaje Sur",
            sender_address="news@viaje.mailer.example",
            authenticated_domain="mailer.example",
            subject="Notificación de viaje",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 2
    assert len({message.source_id for message in result.messages}) == 2


def test_domain_change_without_complete_positive_evidence_stays_separate() -> None:
    records = (
        indexed_record(
            "domain-change-01",
            sender_name="Servicio General",
            sender_address="avisos@dominio-anterior.example",
            authenticated_domain="dominio-anterior.example",
        ),
        indexed_record(
            "domain-change-02",
            sender_name="Servicio General",
            sender_address="avisos@dominio-nuevo.example",
            authenticated_domain="dominio-nuevo.example",
            dkim_result="neutral",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 2
    assert len({message.source_id for message in result.messages}) == 2


def test_authenticated_same_name_on_different_domains_stays_separate() -> None:
    records = (
        indexed_record(
            "domain-change-authenticated-01",
            sender_name="Servicio General",
            sender_address="avisos@dominio-uno.example",
            authenticated_domain="dominio-uno.example",
        ),
        indexed_record(
            "domain-change-authenticated-02",
            sender_name="Servicio General",
            sender_address="avisos@dominio-dos.example",
            authenticated_domain="dominio-dos.example",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 2
    assert len({message.source_id for message in result.messages}) == 2


def test_security_document_and_promotion_are_distinct_flows_in_one_source() -> None:
    common = {
        "sender_name": "Tienda Software",
        "sender_address": "avisos@tienda-software.example",
        "authenticated_domain": "tienda-software.example",
    }
    records = (
        indexed_record(
            "three-flows-security",
            subject="Alerta de seguridad por inicio de sesión",
            category="promotions",
            **common,
        ),
        indexed_record(
            "three-flows-document",
            subject="Factura y comprobante disponible",
            category="promotions",
            **common,
        ),
        indexed_record(
            "three-flows-promotion",
            subject="Oferta con descuento",
            category="promotions",
            list_id="<promos.tienda-software.example>",
            list_unsubscribe="<https://unsubscribe.tienda-software.example/promos>",
            **common,
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 1
    assert len(result.flows) == 3
    assert {flow.intencion for flow in result.flows} == {
        Intencion.SEGURIDAD,
        Intencion.DOCUMENTO,
        Intencion.PROMOCIONAL,
    }
    assert message_by_id(result, "three-flows-security").confianza is Confianza.CONTRADICTORIA
    assert message_by_id(result, "three-flows-document").confianza is Confianza.CONTRADICTORIA
    assert result.sources[0].confianza is Confianza.CONTRADICTORIA


def test_distinct_list_ids_never_merge_only_because_category_matches() -> None:
    records = (
        indexed_record(
            "two-lists-01",
            subject="Oferta semanal",
            category="promotions",
            list_id="<weekly.software-norte.example>",
            list_unsubscribe="<https://unsubscribe.software-norte.example/weekly>",
        ),
        indexed_record(
            "two-lists-02",
            subject="Oferta mensual",
            category="promotions",
            list_id="<monthly.software-norte.example>",
            list_unsubscribe="<https://unsubscribe.software-norte.example/monthly>",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 1
    assert len(result.flows) == 2
    assert {flow.intencion for flow in result.flows} == {Intencion.PROMOCIONAL}
    assert all(EvidenceCode.FLOW_LIST_ID in evidence_codes(flow) for flow in result.flows)


def test_low_confidence_senders_remain_separate() -> None:
    records = (
        indexed_record(
            "low-confidence-01",
            sender_name=None,
            sender_address="first@ambiguous-a.example",
            subject=None,
            authenticated_domain=None,
            dkim_result="unknown",
            dmarc_result="unknown",
        ),
        indexed_record(
            "low-confidence-02",
            sender_name=None,
            sender_address="second@ambiguous-b.example",
            subject=None,
            authenticated_domain=None,
            dkim_result="unknown",
            dmarc_result="unknown",
        ),
    )

    result = classify_indexed_records(records)

    assert len(result.sources) == 2
    assert all(message.confianza is Confianza.BAJA for message in result.messages)
    assert all(source.confianza is Confianza.BAJA for source in result.sources)


def test_material_contradiction_is_explicit_and_flow_isolated() -> None:
    record = indexed_record(
        "contradiction-01",
        sender_name="Servicio General",
        sender_address="alertas@identidad-a.example",
        authenticated_domain="identidad-b.example",
        subject="Alerta de seguridad",
        category="promotions",
    )

    result = classify_indexed_records((record,))
    message = result.messages[0]

    assert message.intencion is Intencion.SEGURIDAD
    assert message.confianza is Confianza.CONTRADICTORIA
    assert EvidenceCode.AUTH_DOMAIN_CONFLICT in evidence_codes(message)
    assert EvidenceCode.CONFLICT_CATEGORY_INTENT in evidence_codes(message)
    assert EvidenceCode.FLOW_ISOLATED in evidence_codes(message)
    assert result.sources[0].confianza is Confianza.CONTRADICTORIA
    assert result.flows[0].confianza is Confianza.CONTRADICTORIA


def test_spam_and_authentication_failure_precede_other_intentions() -> None:
    records = (
        indexed_record(
            "suspicious-spam",
            subject="Factura disponible",
            labels=("INBOX", "SPAM"),
        ),
        indexed_record(
            "suspicious-auth",
            subject="Oferta semanal",
            dkim_result="fail",
            dmarc_result="fail",
            authenticated_domain=None,
        ),
    )

    result = classify_indexed_records(records)

    assert all(message.intencion is Intencion.SOSPECHOSO for message in result.messages)
    assert EvidenceCode.INTENT_SPAM in evidence_codes(
        message_by_id(result, "suspicious-spam")
    )
    assert EvidenceCode.AUTH_FAILED in evidence_codes(
        message_by_id(result, "suspicious-auth")
    )


def test_record_without_sender_subject_or_signals_stays_unknown_and_stable() -> None:
    record = indexed_record(
        "unknown-01",
        sender_name=None,
        sender_address=None,
        subject=None,
        labels=(),
        category=None,
        authenticated_domain=None,
        dkim_result=None,
        dmarc_result=None,
    )

    first = classify_indexed_records((record,))
    second = classify_indexed_records(iter((record,)))

    assert first == second
    assert first.messages[0].rubro is Rubro.DESCONOCIDO
    assert first.messages[0].intencion is Intencion.DESCONOCIDO
    assert first.messages[0].suscripcion is Suscripcion.DESCONOCIDO
    assert first.messages[0].confianza is Confianza.BAJA
    assert first.sources[0].display_name == "Fuente desconocida"
    assert first.flows[0].display_name == "Flujo desconocido"


def test_isolated_identity_caps_message_source_and_flow_confidence() -> None:
    records = (
        indexed_record(
            "isolated-missing-sender",
            sender_name=None,
            sender_address=None,
            subject="Alerta de seguridad",
            authenticated_domain=None,
        ),
        indexed_record(
            "isolated-incomplete-authentication",
            sender_name="Servicio Software",
            sender_address="avisos@identidad-debil.example",
            subject="Notificación de estado",
            authenticated_domain="identidad-debil.example",
            dkim_result="pass",
            dmarc_result="neutral",
        ),
    )

    for record in records:
        result = classify_indexed_records((record,))
        assert result.messages[0].confianza is Confianza.BAJA
        assert result.sources[0].confianza is Confianza.BAJA
        assert result.flows[0].confianza is Confianza.BAJA


def test_high_confidence_requires_independent_strong_signal_families() -> None:
    record = indexed_record(
        "independent-strong-signals",
        subject="Alerta de seguridad",
    )

    result = classify_indexed_records((record,))

    assert result.messages[0].confianza is Confianza.ALTA


def test_output_is_identical_for_every_input_order() -> None:
    records = (
        indexed_record(
            "order-03",
            sender_name="Plataforma Software",
            sender_address="facturas@plataforma-software.example",
            authenticated_domain="plataforma-software.example",
            subject="Factura disponible",
        ),
        indexed_record(
            "order-01",
            sender_name="Plataforma Software",
            sender_address="avisos@plataforma-software.example",
            authenticated_domain="plataforma-software.example",
            subject="Notificación de estado",
        ),
        indexed_record(
            "order-02",
            sender_name="Plataforma Software",
            sender_address="avisos@plataforma-software.example",
            authenticated_domain="plataforma-software.example",
            subject="Oferta semanal",
            category="promotions",
            list_id="<offers.plataforma-software.example>",
            list_unsubscribe="<https://unsubscribe.plataforma-software.example/offers>",
        ),
    )

    expected = classify_indexed_records(records)

    assert classify_indexed_records(reversed(records)) == expected
    assert classify_indexed_records((records[1], records[2], records[0])) == expected
    assert tuple(message.provider_message_id for message in expected.messages) == (
        "order-01",
        "order-02",
        "order-03",
    )
    assert tuple(source.source_id for source in expected.sources) == tuple(
        sorted(source.source_id for source in expected.sources)
    )
    assert tuple(flow.flow_id for flow in expected.flows) == tuple(
        sorted(flow.flow_id for flow in expected.flows)
    )


def test_accounts_are_isolated_and_mixed_input_is_rejected() -> None:
    base = indexed_record("account-isolation-01")
    first = classify_indexed_records((replace(base, account_key="opaque-account-one"),))
    second = classify_indexed_records((replace(base, account_key="opaque-account-two"),))

    assert first.sources[0].source_id != second.sources[0].source_id
    assert first.flows[0].flow_id != second.flows[0].flow_id
    assert first.sources[0].identity_descriptor == second.sources[0].identity_descriptor
    assert first.flows[0].identity_descriptor == second.flows[0].identity_descriptor

    with pytest.raises(ClassificationError) as error:
        classify_indexed_records(
            (
                replace(base, account_key="opaque-account-one"),
                replace(
                    base,
                    account_key="opaque-account-two",
                    provider_message_id="account-isolation-02",
                ),
            )
        )
    assert error.value.code is ClassificationErrorCode.MIXED_ACCOUNTS


def test_duplicate_and_invalid_records_fail_with_controlled_codes() -> None:
    duplicate = indexed_record("duplicate-01")
    with pytest.raises(ClassificationError) as duplicate_error:
        classify_indexed_records((duplicate, duplicate))
    assert (
        duplicate_error.value.code
        is ClassificationErrorCode.DUPLICATE_MESSAGE_IDENTITY
    )

    with pytest.raises(ClassificationError) as type_error:
        classify_indexed_records((duplicate, object()))  # type: ignore[arg-type]
    assert type_error.value.code is ClassificationErrorCode.INVALID_RECORD

    malformed = replace(duplicate, sender_address="not-a-normalized-address")
    with pytest.raises(ClassificationError) as malformed_error:
        classify_indexed_records((malformed,))
    assert malformed_error.value.code is ClassificationErrorCode.INVALID_RECORD


def test_subscription_states_follow_only_technical_evidence() -> None:
    records = (
        indexed_record(
            "subscription-confirmed",
            subject="Resumen semanal",
            list_id="<weekly.software-norte.example>",
            list_unsubscribe="<https://unsubscribe.software-norte.example/weekly>",
            list_unsubscribe_post="List-Unsubscribe=One-Click",
        ),
        indexed_record(
            "subscription-probable",
            sender_address="news@probable-list.example",
            sender_name=None,
            authenticated_domain=None,
            subject=None,
            list_id="<weekly.probable-list.example>",
            dkim_result="neutral",
            dmarc_result="neutral",
        ),
        indexed_record(
            "subscription-not-applicable",
            sender_address="security@no-list.example",
            sender_name="Servicio Software",
            authenticated_domain="no-list.example",
            subject="Código de seguridad",
        ),
        indexed_record(
            "subscription-conflict",
            sender_address="news@untrusted-list.example",
            sender_name="Servicio Software",
            authenticated_domain=None,
            subject="Resumen semanal",
            list_id="<weekly.untrusted-list.example>",
            list_unsubscribe="<https://unsubscribe.untrusted-list.example/weekly>",
            dkim_result="fail",
            dmarc_result="fail",
        ),
    )

    result = classify_indexed_records(records)

    assert message_by_id(result, "subscription-confirmed").suscripcion is Suscripcion.CONFIRMADA
    assert message_by_id(result, "subscription-probable").suscripcion is Suscripcion.PROBABLE
    assert (
        message_by_id(result, "subscription-not-applicable").suscripcion
        is Suscripcion.NO_CORRESPONDE
    )
    conflict = message_by_id(result, "subscription-conflict")
    assert conflict.suscripcion is Suscripcion.POSIBLE_INCUMPLIMIENTO
    assert conflict.confianza is Confianza.CONTRADICTORIA


@pytest.mark.parametrize(
    "list_unsubscribe",
    (
        "opaque-unsubscribe-value",
        "http://unsubscribe.software-norte.example/insecure",
        "<https://unsubscribe.software-norte.example/valid>, malformed",
    ),
)
def test_untrusted_unsubscribe_is_contradictory_not_confirmed(
    list_unsubscribe: str,
) -> None:
    record = indexed_record(
        "subscription-untrusted-unsubscribe",
        subject="Resumen semanal",
        list_id="<weekly.software-norte.example>",
        list_unsubscribe=list_unsubscribe,
    )

    message = classify_indexed_records((record,)).messages[0]

    assert message.suscripcion is Suscripcion.POSIBLE_INCUMPLIMIENTO
    assert message.confianza is Confianza.CONTRADICTORIA
    assert EvidenceCode.UNSUBSCRIBE_UNTRUSTED in evidence_codes(message)


def test_list_and_unsubscribe_prove_subscription_but_not_editorial_intent() -> None:
    record = indexed_record(
        "subscription-without-content-signal",
        subject=None,
        category=None,
        list_id="<technical-list.software-norte.example>",
        list_unsubscribe="<mailto:unsubscribe@software-norte.example>",
    )

    result = classify_indexed_records((record,))

    assert result.messages[0].suscripcion is Suscripcion.CONFIRMADA
    assert result.messages[0].intencion is Intencion.DESCONOCIDO
    assert EvidenceCode.INTENT_UNKNOWN in evidence_codes(result.messages[0])


@pytest.mark.parametrize(
    "list_id",
    (
        "not-a-structured-list-id",
        "list.foo..example",
        ".list.example",
        "list.example.",
        "List without separator <list.example><second.example>",
    ),
)
def test_unstructured_list_header_is_contradictory_not_confirmed(
    list_id: str,
) -> None:
    record = indexed_record(
        "untrusted-list-structure",
        subject=None,
        category=None,
        list_id=list_id,
        list_unsubscribe="<https://unsubscribe.software-norte.example/weekly>",
    )

    result = classify_indexed_records((record,))
    message = result.messages[0]

    assert message.suscripcion is Suscripcion.POSIBLE_INCUMPLIMIENTO
    assert message.confianza is Confianza.CONTRADICTORIA
    assert EvidenceCode.LIST_ID_UNTRUSTED in evidence_codes(message)
    assert EvidenceCode.FLOW_ISOLATED in evidence_codes(message)


def test_generic_rubro_rules_do_not_turn_missing_evidence_into_a_fact() -> None:
    records = (
        indexed_record(
            "rubro-commerce",
            sender_name="Tienda General",
            sender_address="avisos@tienda-general.example",
            authenticated_domain="tienda-general.example",
        ),
        indexed_record(
            "rubro-unknown",
            sender_name="Entidad Alfa",
            sender_address="avisos@entidad-alfa.example",
            authenticated_domain="entidad-alfa.example",
            subject=None,
        ),
    )

    result = classify_indexed_records(records)

    assert message_by_id(result, "rubro-commerce").rubro is Rubro.COMERCIO
    assert message_by_id(result, "rubro-unknown").rubro is Rubro.DESCONOCIDO
    assert EvidenceCode.RUBRO_UNKNOWN in evidence_codes(
        message_by_id(result, "rubro-unknown")
    )


def test_absence_of_list_headers_never_implies_personal_communication() -> None:
    record = indexed_record(
        "not-personal-by-absence",
        sender_name="Persona Sintética",
        sender_address="persona@correspondencia.example",
        subject="Hola",
        authenticated_domain="correspondencia.example",
        list_id=None,
        list_unsubscribe=None,
    )

    result = classify_indexed_records((record,))

    assert result.messages[0].intencion is Intencion.DESCONOCIDO
    assert result.messages[0].intencion is not Intencion.PERSONAL


def test_models_are_closed_immutable_and_do_not_depend_on_fixture_fields() -> None:
    prohibited = {
        "brand" + "_hint",
        "rubro" + "_hint",
        "flow" + "_hint",
        "personal" + "_signal",
        "fixture" + "_tags",
    }
    assert prohibited.isdisjoint(field.name for field in fields(IndexedMessageRecord))

    result = classify_indexed_records((indexed_record("immutable-01"),))
    values = (
        result,
        result.messages[0],
        result.sources[0],
        result.flows[0],
        result.sources[0].identity_descriptor,
        result.flows[0].identity_descriptor,
        result.messages[0].evidence[0],
    )
    assert all(not hasattr(value, "__dict__") for value in values)
    with pytest.raises(FrozenInstanceError):
        result.messages[0].source_id = "changed"  # type: ignore[misc]


def test_controlled_error_is_closed_immutable_and_redacted() -> None:
    error = ClassificationError(ClassificationErrorCode.INVALID_RECORD)

    assert not hasattr(error, "__dict__")
    with pytest.raises(AttributeError):
        error.code = ClassificationErrorCode.INVALID_INPUT  # type: ignore[misc]
    with pytest.raises(AttributeError):
        error.extra = "private@error.example"  # type: ignore[attr-defined]

    evidence = ClassificationEvidence(
        code=EvidenceCode.INTENT_UNKNOWN,
        label="private@evidence.example",
        detail="Asunto privado sintético",
        strength=EvidenceStrength.WEAK,
        origin=EvidenceOrigin.RECORD,
    )
    rendered = repr(evidence).casefold()
    assert "private@evidence.example" not in rendered
    assert "asunto privado sintético".casefold() not in rendered


def test_public_result_rejects_semantically_inconsistent_aggregates() -> None:
    result = classify_indexed_records(
        (
            indexed_record(
                "public-model-invariants",
                sender_name=None,
                sender_address=None,
                subject=None,
                labels=(),
                category=None,
                authenticated_domain=None,
                dkim_result=None,
                dmarc_result=None,
            ),
        )
    )
    message = result.messages[0]
    flow = result.flows[0]
    source = result.sources[0]
    assert message.confianza is Confianza.BAJA

    with pytest.raises(ValueError, match="flow intention"):
        replace(
            result,
            flows=(replace(flow, intencion=Intencion.SEGURIDAD),),
        )
    with pytest.raises(ValueError, match="flow confidence"):
        replace(
            result,
            flows=(replace(flow, confianza=Confianza.ALTA),),
        )
    with pytest.raises(ValueError, match="source confidence"):
        replace(
            result,
            sources=(replace(source, confianza=Confianza.ALTA),),
        )
    with pytest.raises(ValueError, match="isolated source descriptor"):
        replace(
            source,
            identity_descriptor=replace(
                source.identity_descriptor,
                isolated_message_id="other-provider-message",
            ),
        )
    sender_source_descriptor = SourceIdentityDescriptor(
        kind=SourceAnchorKind.SENDERS,
        sender_addresses=("sender@aggregate.example",),
        isolated_message_id=None,
    )
    with pytest.raises(ValueError, match="isolated flow descriptor"):
        replace(
            flow,
            identity_descriptor=replace(
                flow.identity_descriptor,
                source=sender_source_descriptor,
                isolated_message_id="other-provider-message",
            ),
        )

    foreign_flow = replace(
        flow,
        identity_descriptor=replace(
            flow.identity_descriptor,
            source=sender_source_descriptor,
        ),
    )
    with pytest.raises(ValueError, match="flow identity descriptor"):
        replace(result, flows=(foreign_flow,))


def test_public_models_reject_non_opaque_local_identifiers() -> None:
    result = classify_indexed_records((indexed_record("opaque-local-ids"),))

    with pytest.raises(ValueError, match="source_id"):
        replace(result.messages[0], source_id="private@sender.example")
    with pytest.raises(ValueError, match="flow_id"):
        replace(result.messages[0], flow_id="Asunto y List-ID en claro")
    with pytest.raises(ValueError, match="source_id"):
        replace(result.sources[0], source_id="source-without-versioned-hash")
    with pytest.raises(ValueError, match="flow_id"):
        replace(result.flows[0], flow_id="flow-without-versioned-hash")


def test_local_ids_and_representations_redact_all_input_metadata() -> None:
    record = indexed_record(
        "provider-secret-identifier",
        account_key="opaque-secret-account",
        sender_name="Nombre Sintético Secreto",
        sender_address="private-value@redacted-source.example",
        authenticated_domain="redacted-source.example",
        subject="Factura sintética reservada",
        list_id="<private-list.redacted-source.example>",
        list_unsubscribe="<https://unsubscribe.redacted-source.example/private-value>",
    )
    result = classify_indexed_records((record,))

    identifiers = (
        result.sources[0].source_id,
        result.flows[0].flow_id,
        result.messages[0].source_id,
        result.messages[0].flow_id,
    )
    forbidden_identifier_parts = (
        "private-value",
        "redacted-source",
        "nombre",
        "private-list",
    )
    assert all(
        part not in identifier.casefold()
        for identifier in identifiers
        for part in forbidden_identifier_parts
    )

    rendered = "\n".join(
        repr(value)
        for value in (
            result,
            *result.messages,
            *result.sources,
            *result.flows,
            *(source.identity_descriptor for source in result.sources),
            *(flow.identity_descriptor for flow in result.flows),
            *(item for message in result.messages for item in message.evidence),
        )
    ).casefold()
    forbidden_repr_values = (
        "provider-secret-identifier",
        "opaque-secret-account",
        "nombre sintético secreto".casefold(),
        "private-value@redacted-source.example",
        "redacted-source.example",
        "factura sintética reservada".casefold(),
        "private-list.redacted-source.example",
        "https://unsubscribe.redacted-source.example/private-value",
    )
    assert all(value not in rendered for value in forbidden_repr_values)

    with pytest.raises(ClassificationError) as error:
        classify_indexed_records((record, record))
    error_rendered = f"{error.value!s}\n{error.value!r}".casefold()
    assert error.value.code is ClassificationErrorCode.DUPLICATE_MESSAGE_IDENTITY
    assert all(value not in error_rendered for value in forbidden_repr_values)


def test_evidence_is_closed_unique_and_deterministically_ordered() -> None:
    result = classify_indexed_records(
        (
            indexed_record(
                "evidence-order-01",
                subject="Alerta de seguridad",
                category="promotions",
                list_id="<alerts.software-norte.example>",
                list_unsubscribe="<https://unsubscribe.software-norte.example/evidence>",
            ),
        )
    )

    for value in (*result.messages, *result.sources, *result.flows):
        codes = tuple(item.code.value for item in value.evidence)
        assert codes == tuple(sorted(codes))
        assert len(codes) == len(set(codes))
        assert all(item.detail for item in value.evidence)
