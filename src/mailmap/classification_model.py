from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from mailmap.model import Confianza, Intencion, Rubro, Suscripcion

CLASSIFICATION_MODEL_VERSION = 2
IDENTITY_DESCRIPTOR_VERSION = 1
_SOURCE_IDENTIFIER = re.compile(r"^source-v1-[0-9a-f]{24}$")
_FLOW_IDENTIFIER = re.compile(r"^flow-v1-[0-9a-f]{24}$")
_CANONICAL_ADDRESS = re.compile(
    r"^[^@\s<>]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$"
)
_LIST_ID_COMPONENT = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9_+-]*[a-z0-9])$")


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical value")
    return value


def _optional_account_key(value: str | None) -> str | None:
    if value is None:
        return None
    _non_empty(value, "account_key")
    if "@" in value:
        raise ValueError("account_key must be opaque")
    return value


def _optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _non_empty(value, field_name)


def _exact_version(value: int, expected: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"version must be {expected}")
    return value


def _canonical_address(value: str, field_name: str) -> str:
    _non_empty(value, field_name)
    if value != value.casefold() or _CANONICAL_ADDRESS.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical address")
    return value


def _canonical_addresses(
    value: tuple[str, ...], field_name: str
) -> tuple[str, ...]:
    _string_tuple(value, field_name, allow_empty=True)
    for item in value:
        _canonical_address(item, f"{field_name} item")
    return value


def _canonical_list_id(value: str, field_name: str) -> str:
    _non_empty(value, field_name)
    components = value.split(".")
    if (
        value != value.casefold()
        or len(components) < 2
        or any(_LIST_ID_COMPONENT.fullmatch(component) is None for component in components)
    ):
        raise ValueError(f"{field_name} must be a canonical List-ID")
    return value


def _confidence_rank(value: Confianza) -> int:
    return (
        Confianza.ALTA,
        Confianza.MEDIA,
        Confianza.BAJA,
        Confianza.CONTRADICTORIA,
    ).index(value)


def _source_id(value: str) -> str:
    _non_empty(value, "source_id")
    if _SOURCE_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("source_id must be a versioned opaque identifier")
    return value


def _flow_id(value: str) -> str:
    _non_empty(value, "flow_id")
    if _FLOW_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("flow_id must be a versioned opaque identifier")
    return value


def _evidence_tuple(
    value: tuple[ClassificationEvidence, ...],
) -> tuple[ClassificationEvidence, ...]:
    if not isinstance(value, tuple) or any(
        not isinstance(item, ClassificationEvidence) for item in value
    ):
        raise TypeError("evidence must be a tuple of ClassificationEvidence values")
    if not value:
        raise ValueError("classified values must contain evidence")
    codes = tuple(item.code for item in value)
    if len(set(codes)) != len(codes):
        raise ValueError("evidence codes must not be duplicated")
    if codes != tuple(sorted(codes, key=lambda item: item.value)):
        raise ValueError("evidence must be ordered by code")
    return value


def _string_tuple(
    value: tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        _non_empty(item, f"{field_name} item")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must not contain duplicates")
    if value != tuple(sorted(value)):
        raise ValueError(f"{field_name} must be ordered")
    return value


class SourceAnchorKind(StrEnum):
    SENDERS = "senders"
    ISOLATED_MESSAGE = "isolated_message"


class FlowAnchorKind(StrEnum):
    LIST_INTENT = "list_intent"
    SENDER_INTENT = "sender_intent"
    ISOLATED_MESSAGE = "isolated_message"


class EvidenceStrength(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class EvidenceOrigin(StrEnum):
    RECORD = "record"
    SENDER = "sender"
    AUTHENTICATION = "authentication"
    SUBJECT = "subject"
    LABEL = "label"
    CATEGORY = "category"
    LIST = "list"
    UNSUBSCRIBE = "unsubscribe"
    AGGREGATION = "aggregation"


class EvidenceCode(StrEnum):
    SOURCE_AUTHENTICATED = "source.authenticated"
    SOURCE_MERGED = "source.merged"
    SOURCE_SENDER_ISOLATED = "source.sender_isolated"
    SOURCE_SENDER_MISSING = "source.sender_missing"
    SOURCE_IDENTITY_UNRESOLVED = "source.identity_unresolved"
    AUTH_DKIM_PASSED = "authentication.dkim_passed"
    AUTH_DMARC_PASSED = "authentication.dmarc_passed"
    AUTH_FAILED = "authentication.failed"
    AUTH_INCOMPLETE = "authentication.incomplete"
    AUTH_DOMAIN_COHERENT = "authentication.domain_coherent"
    AUTH_DOMAIN_CONFLICT = "authentication.domain_conflict"
    INTENT_SPAM = "intent.spam"
    INTENT_SECURITY = "intent.security"
    INTENT_DOCUMENT = "intent.document"
    INTENT_OPERATIONAL = "intent.operational"
    INTENT_NOTIFICATION = "intent.notification"
    INTENT_EDITORIAL = "intent.editorial"
    INTENT_PROMOTIONAL = "intent.promotional"
    INTENT_PROVIDER_CATEGORY = "intent.provider_category"
    INTENT_UNKNOWN = "intent.unknown"
    RUBRO_GENERIC_SIGNAL = "rubro.generic_signal"
    RUBRO_UNKNOWN = "rubro.unknown"
    LIST_ID_PRESENT = "list.id_present"
    LIST_ID_UNTRUSTED = "list.id_untrusted"
    UNSUBSCRIBE_PRESENT = "unsubscribe.present"
    UNSUBSCRIBE_UNTRUSTED = "unsubscribe.untrusted"
    UNSUBSCRIBE_ONE_CLICK = "unsubscribe.one_click"
    SUBSCRIPTION_CONFIRMED = "subscription.confirmed"
    SUBSCRIPTION_PROBABLE = "subscription.probable"
    SUBSCRIPTION_NOT_APPLICABLE = "subscription.not_applicable"
    SUBSCRIPTION_CONFLICT = "subscription.conflict"
    SUBSCRIPTION_UNKNOWN = "subscription.unknown"
    CONFLICT_CATEGORY_INTENT = "conflict.category_intent"
    CONFLICT_GROUP_AUTHENTICATION = "conflict.group_authentication"
    FLOW_LIST_ID = "flow.list_id"
    FLOW_SENDER_INTENT = "flow.sender_intent"
    FLOW_ISOLATED = "flow.isolated"


class ClassificationErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_RECORD = "invalid_record"
    MIXED_ACCOUNTS = "mixed_accounts"
    DUPLICATE_MESSAGE_IDENTITY = "duplicate_message_identity"


class ClassificationError(RuntimeError):
    __slots__ = ()

    def __init__(self, code: ClassificationErrorCode) -> None:
        if not isinstance(code, ClassificationErrorCode):
            raise TypeError("code must be a ClassificationErrorCode")
        super().__init__(code.value)

    @property
    def code(self) -> ClassificationErrorCode:
        return ClassificationErrorCode(self.args[0])

    def __getattribute__(self, name: str) -> object:
        if name == "__dict__":
            raise AttributeError("ClassificationError is closed")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ClassificationError is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ClassificationError is immutable")

    def __repr__(self) -> str:
        return f"ClassificationError(code={self.code.value!r})"


@dataclass(frozen=True, slots=True)
class ClassificationEvidence:
    code: EvidenceCode
    label: str
    detail: str = field(repr=False)
    strength: EvidenceStrength
    origin: EvidenceOrigin

    def __post_init__(self) -> None:
        if not isinstance(self.code, EvidenceCode):
            raise TypeError("code must be an EvidenceCode")
        _non_empty(self.label, "label")
        _non_empty(self.detail, "detail")
        if not isinstance(self.strength, EvidenceStrength):
            raise TypeError("strength must be an EvidenceStrength")
        if not isinstance(self.origin, EvidenceOrigin):
            raise TypeError("origin must be an EvidenceOrigin")

    def __repr__(self) -> str:
        return (
            "ClassificationEvidence("
            f"code={self.code.value!r}, label=<redacted>, detail=<redacted>, "
            f"strength={self.strength.value!r}, origin={self.origin.value!r})"
        )


@dataclass(frozen=True, slots=True)
class SourceIdentityDescriptor:
    kind: SourceAnchorKind
    sender_addresses: tuple[str, ...] = field(repr=False)
    isolated_message_id: str | None = field(repr=False)
    version: int = IDENTITY_DESCRIPTOR_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SourceAnchorKind):
            raise TypeError("kind must be a SourceAnchorKind")
        _canonical_addresses(self.sender_addresses, "sender_addresses")
        _optional_non_empty(self.isolated_message_id, "isolated_message_id")
        _exact_version(self.version, IDENTITY_DESCRIPTOR_VERSION)
        if self.kind is SourceAnchorKind.SENDERS:
            if not self.sender_addresses or self.isolated_message_id is not None:
                raise ValueError("senders source descriptor has invalid anchors")
        elif self.sender_addresses or self.isolated_message_id is None:
            raise ValueError("isolated source descriptor has invalid anchors")

    def __repr__(self) -> str:
        return (
            "SourceIdentityDescriptor("
            f"kind={self.kind.value!r}, sender_count={len(self.sender_addresses)}, "
            f"has_isolated_message={self.isolated_message_id is not None}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True)
class FlowIdentityDescriptor:
    kind: FlowAnchorKind
    source: SourceIdentityDescriptor
    list_id: str | None = field(repr=False)
    sender_address: str | None = field(repr=False)
    automatic_intention: Intencion
    isolated_message_id: str | None = field(repr=False)
    version: int = IDENTITY_DESCRIPTOR_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FlowAnchorKind):
            raise TypeError("kind must be a FlowAnchorKind")
        if not isinstance(self.source, SourceIdentityDescriptor):
            raise TypeError("source must be a SourceIdentityDescriptor")
        _optional_non_empty(self.list_id, "list_id")
        _optional_non_empty(self.sender_address, "sender_address")
        _optional_non_empty(self.isolated_message_id, "isolated_message_id")
        if not isinstance(self.automatic_intention, Intencion):
            raise TypeError("automatic_intention must be an Intencion")
        _exact_version(self.version, IDENTITY_DESCRIPTOR_VERSION)

        if self.kind is FlowAnchorKind.LIST_INTENT:
            if (
                self.list_id is None
                or self.sender_address is not None
                or self.isolated_message_id is not None
            ):
                raise ValueError("list flow descriptor has invalid anchors")
            if self.source.kind is not SourceAnchorKind.SENDERS:
                raise ValueError("list flow descriptor requires a sender source")
            _canonical_list_id(self.list_id, "list_id")
        elif self.kind is FlowAnchorKind.SENDER_INTENT:
            if (
                self.sender_address is None
                or self.list_id is not None
                or self.isolated_message_id is not None
            ):
                raise ValueError("sender flow descriptor has invalid anchors")
            if self.source.kind is not SourceAnchorKind.SENDERS:
                raise ValueError("sender flow descriptor requires a sender source")
            _canonical_address(self.sender_address, "sender_address")
            if self.sender_address not in self.source.sender_addresses:
                raise ValueError("sender flow descriptor does not belong to source")
        elif (
            self.isolated_message_id is None
            or self.list_id is not None
            or self.sender_address is not None
        ):
            raise ValueError("isolated flow descriptor has invalid anchors")
        elif (
            self.source.kind is SourceAnchorKind.ISOLATED_MESSAGE
            and self.source.isolated_message_id != self.isolated_message_id
        ):
            raise ValueError("isolated source and flow must reference the same message")

    def __repr__(self) -> str:
        return (
            "FlowIdentityDescriptor("
            f"kind={self.kind.value!r}, source_kind={self.source.kind.value!r}, "
            f"automatic_intention={self.automatic_intention.value!r}, "
            f"has_list={self.list_id is not None}, "
            f"has_sender={self.sender_address is not None}, "
            f"has_isolated_message={self.isolated_message_id is not None}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True)
class ClassifiedMessage:
    provider_message_id: str = field(repr=False)
    source_id: str
    flow_id: str
    rubro: Rubro
    intencion: Intencion
    suscripcion: Suscripcion
    confianza: Confianza
    evidence: tuple[ClassificationEvidence, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _non_empty(self.provider_message_id, "provider_message_id")
        _source_id(self.source_id)
        _flow_id(self.flow_id)
        if not isinstance(self.rubro, Rubro):
            raise TypeError("rubro must be a Rubro")
        if not isinstance(self.intencion, Intencion):
            raise TypeError("intencion must be an Intencion")
        if not isinstance(self.suscripcion, Suscripcion):
            raise TypeError("suscripcion must be a Suscripcion")
        if not isinstance(self.confianza, Confianza):
            raise TypeError("confianza must be a Confianza")
        _evidence_tuple(self.evidence)

    def __repr__(self) -> str:
        return (
            "ClassifiedMessage(provider_message_id=<redacted>, "
            f"source_id={self.source_id!r}, flow_id={self.flow_id!r}, "
            f"rubro={self.rubro.value!r}, intencion={self.intencion.value!r}, "
            f"suscripcion={self.suscripcion.value!r}, "
            f"confianza={self.confianza.value!r}, evidence_count={len(self.evidence)})"
        )


@dataclass(frozen=True, slots=True)
class ClassifiedSource:
    source_id: str
    identity_descriptor: SourceIdentityDescriptor = field(repr=False)
    display_name: str = field(repr=False)
    sender_addresses: tuple[str, ...] = field(repr=False)
    domains: tuple[str, ...] = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    flow_ids: tuple[str, ...]
    rubro: Rubro
    confianza: Confianza
    evidence: tuple[ClassificationEvidence, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _source_id(self.source_id)
        if not isinstance(self.identity_descriptor, SourceIdentityDescriptor):
            raise TypeError("identity_descriptor must be a SourceIdentityDescriptor")
        _non_empty(self.display_name, "display_name")
        _string_tuple(self.sender_addresses, "sender_addresses", allow_empty=True)
        _string_tuple(self.domains, "domains", allow_empty=True)
        _string_tuple(self.message_ids, "message_ids", allow_empty=False)
        _string_tuple(self.flow_ids, "flow_ids", allow_empty=False)
        for flow_id in self.flow_ids:
            _flow_id(flow_id)
        if not isinstance(self.rubro, Rubro):
            raise TypeError("rubro must be a Rubro")
        if not isinstance(self.confianza, Confianza):
            raise TypeError("confianza must be a Confianza")
        _evidence_tuple(self.evidence)
        if self.identity_descriptor.sender_addresses != self.sender_addresses:
            raise ValueError("source identity descriptor does not match senders")
        if (
            self.identity_descriptor.kind is SourceAnchorKind.ISOLATED_MESSAGE
            and self.message_ids != (self.identity_descriptor.isolated_message_id,)
        ):
            raise ValueError("isolated source descriptor does not match members")

    def __repr__(self) -> str:
        return (
            f"ClassifiedSource(source_id={self.source_id!r}, display_name=<redacted>, "
            f"identity_kind={self.identity_descriptor.kind.value!r}, "
            f"sender_count={len(self.sender_addresses)}, domain_count={len(self.domains)}, "
            f"message_count={len(self.message_ids)}, flow_ids={self.flow_ids!r}, "
            f"rubro={self.rubro.value!r}, confianza={self.confianza.value!r}, "
            f"evidence_count={len(self.evidence)})"
        )


@dataclass(frozen=True, slots=True)
class ClassifiedFlow:
    flow_id: str
    source_id: str
    identity_descriptor: FlowIdentityDescriptor = field(repr=False)
    display_name: str = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    intencion: Intencion
    suscripcion: Suscripcion
    confianza: Confianza
    evidence: tuple[ClassificationEvidence, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _flow_id(self.flow_id)
        _source_id(self.source_id)
        if not isinstance(self.identity_descriptor, FlowIdentityDescriptor):
            raise TypeError("identity_descriptor must be a FlowIdentityDescriptor")
        _non_empty(self.display_name, "display_name")
        _string_tuple(self.message_ids, "message_ids", allow_empty=False)
        if not isinstance(self.intencion, Intencion):
            raise TypeError("intencion must be an Intencion")
        if not isinstance(self.suscripcion, Suscripcion):
            raise TypeError("suscripcion must be a Suscripcion")
        if not isinstance(self.confianza, Confianza):
            raise TypeError("confianza must be a Confianza")
        _evidence_tuple(self.evidence)
        if self.identity_descriptor.automatic_intention is not self.intencion:
            raise ValueError("flow intention must match identity descriptor")
        if (
            self.identity_descriptor.kind is FlowAnchorKind.ISOLATED_MESSAGE
            and self.message_ids != (self.identity_descriptor.isolated_message_id,)
        ):
            raise ValueError("isolated flow descriptor does not match members")

    def __repr__(self) -> str:
        return (
            f"ClassifiedFlow(flow_id={self.flow_id!r}, source_id={self.source_id!r}, "
            f"identity_kind={self.identity_descriptor.kind.value!r}, "
            f"display_name=<redacted>, message_count={len(self.message_ids)}, "
            f"intencion={self.intencion.value!r}, suscripcion={self.suscripcion.value!r}, "
            f"confianza={self.confianza.value!r}, evidence_count={len(self.evidence)})"
        )


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    account_key: str | None = field(repr=False)
    messages: tuple[ClassifiedMessage, ...]
    sources: tuple[ClassifiedSource, ...]
    flows: tuple[ClassifiedFlow, ...]
    version: int = CLASSIFICATION_MODEL_VERSION

    def __post_init__(self) -> None:
        _optional_account_key(self.account_key)
        if not isinstance(self.messages, tuple) or any(
            not isinstance(item, ClassifiedMessage) for item in self.messages
        ):
            raise TypeError("messages must be a tuple of ClassifiedMessage values")
        if not isinstance(self.sources, tuple) or any(
            not isinstance(item, ClassifiedSource) for item in self.sources
        ):
            raise TypeError("sources must be a tuple of ClassifiedSource values")
        if not isinstance(self.flows, tuple) or any(
            not isinstance(item, ClassifiedFlow) for item in self.flows
        ):
            raise TypeError("flows must be a tuple of ClassifiedFlow values")
        _exact_version(self.version, CLASSIFICATION_MODEL_VERSION)

        is_empty = not self.messages and not self.sources and not self.flows
        if is_empty != (self.account_key is None):
            raise ValueError("only an empty result may omit account_key")

        message_ids = tuple(item.provider_message_id for item in self.messages)
        source_ids = tuple(item.source_id for item in self.sources)
        flow_ids = tuple(item.flow_id for item in self.flows)
        if len(set(message_ids)) != len(message_ids):
            raise ValueError("messages must not contain duplicate identities")
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("sources must not contain duplicate identities")
        if len(set(flow_ids)) != len(flow_ids):
            raise ValueError("flows must not contain duplicate identities")
        source_descriptors = tuple(item.identity_descriptor for item in self.sources)
        flow_descriptors = tuple(item.identity_descriptor for item in self.flows)
        if len(set(source_descriptors)) != len(source_descriptors):
            raise ValueError("sources must not contain duplicate identity descriptors")
        if len(set(flow_descriptors)) != len(flow_descriptors):
            raise ValueError("flows must not contain duplicate identity descriptors")
        if message_ids != tuple(sorted(message_ids)):
            raise ValueError("messages must be ordered by identity")
        if source_ids != tuple(sorted(source_ids)):
            raise ValueError("sources must be ordered by identity")
        if flow_ids != tuple(sorted(flow_ids)):
            raise ValueError("flows must be ordered by identity")

        known_sources = set(source_ids)
        known_flows = set(flow_ids)
        if any(item.source_id not in known_sources for item in self.messages):
            raise ValueError("every message must reference a known source")
        if any(item.flow_id not in known_flows for item in self.messages):
            raise ValueError("every message must reference a known flow")
        if any(item.source_id not in known_sources for item in self.flows):
            raise ValueError("every flow must reference a known source")

        descriptors_by_source = {
            item.source_id: item.identity_descriptor for item in self.sources
        }
        if any(
            item.identity_descriptor.source != descriptors_by_source[item.source_id]
            for item in self.flows
        ):
            raise ValueError("flow identity descriptor must reference its source descriptor")

        flow_sources = {item.flow_id: item.source_id for item in self.flows}
        if any(
            flow_sources[item.flow_id] != item.source_id for item in self.messages
        ):
            raise ValueError("message source and flow relationships must agree")
        for flow in self.flows:
            flow_messages = tuple(
                item for item in self.messages if item.flow_id == flow.flow_id
            )
            expected_message_ids = tuple(
                item.provider_message_id for item in flow_messages
            )
            if flow.message_ids != expected_message_ids:
                raise ValueError("flow message relationships must be complete")
            if any(item.intencion is not flow.intencion for item in flow_messages):
                raise ValueError("flow intention must match every member")
            if _confidence_rank(flow.confianza) < max(
                _confidence_rank(item.confianza) for item in flow_messages
            ):
                raise ValueError("flow confidence must not improve its worst member")
        for source in self.sources:
            source_messages = tuple(
                item for item in self.messages if item.source_id == source.source_id
            )
            expected_message_ids = tuple(
                item.provider_message_id for item in source_messages
            )
            expected_flow_ids = tuple(
                item.flow_id
                for item in self.flows
                if item.source_id == source.source_id
            )
            if source.message_ids != expected_message_ids:
                raise ValueError("source message relationships must be complete")
            if source.flow_ids != expected_flow_ids:
                raise ValueError("source flow relationships must be complete")
            if _confidence_rank(source.confianza) < max(
                _confidence_rank(item.confianza) for item in source_messages
            ):
                raise ValueError("source confidence must not improve its worst member")

    def __repr__(self) -> str:
        return (
            "ClassificationResult(account_key=<redacted>, "
            f"message_count={len(self.messages)}, source_count={len(self.sources)}, "
            f"flow_count={len(self.flows)}, version={self.version})"
        )
