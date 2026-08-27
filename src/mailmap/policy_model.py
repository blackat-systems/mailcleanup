from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeAlias, TypeGuard

from mailmap.classification_model import (
    CLASSIFICATION_MODEL_VERSION,
    ClassificationEvidence,
    FlowAnchorKind,
    SourceAnchorKind,
)
from mailmap.classification_model import (
    FlowIdentityDescriptor as FlowIdentityDescriptor,
)
from mailmap.classification_model import (
    SourceIdentityDescriptor as SourceIdentityDescriptor,
)
from mailmap.model import Confianza, Intencion, Proteccion, Rubro, Suscripcion

POLICY_MODEL_VERSION = 1
POLICY_SELECTOR_VERSION = 1
POLICY_RESULT_VERSION = 1

_EMAIL_LIKE = re.compile(r"^[^@\s]+@[^@\s]+$")
_CANONICAL_ADDRESS = re.compile(
    r"^[^@\s<>]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$"
)
_SOURCE_ID = re.compile(r"^source-v1-[0-9a-f]{24}$")
_FLOW_ID = re.compile(r"^flow-v1-[0-9a-f]{24}$")
_EFFECTIVE_SOURCE_ID = re.compile(r"^effective-source-v1-[0-9a-f]{24}$")
_EFFECTIVE_FLOW_ID = re.compile(r"^effective-flow-v1-[0-9a-f]{24}$")
_CONFIDENCE_RANK = {
    Confianza.ALTA: 0,
    Confianza.MEDIA: 1,
    Confianza.BAJA: 2,
    Confianza.CONTRADICTORIA: 3,
}


def _exact_version(value: int, expected: int, field_name: str = "version") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value


def _non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _normalized_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != " ".join(value.split()):
        raise ValueError(f"{field_name} must be a non-empty normalized value")
    return value


def _opaque_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must be a non-empty opaque identifier")
    return value


def _account_key(value: str) -> str:
    _opaque_identifier(value, "account_key")
    if "@" in value or _EMAIL_LIKE.fullmatch(value):
        raise ValueError("account_key must not have the form of an email address")
    return value


def _canonical_address(value: str, field_name: str) -> str:
    _normalized_text(value, field_name)
    if value != value.casefold() or _CANONICAL_ADDRESS.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical address")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


def _string_tuple(
    value: tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = False,
    validator: object | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    for item in value:
        if validator is _canonical_address:
            _canonical_address(item, f"{field_name} item")
        else:
            _opaque_identifier(item, f"{field_name} item")
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must not contain duplicates")
    if value != tuple(sorted(value)):
        raise ValueError(f"{field_name} must be ordered")
    return value


def _source_descriptor_key(value: SourceIdentityDescriptor) -> tuple[object, ...]:
    return (
        value.version,
        value.kind.value,
        value.sender_addresses,
        value.isolated_message_id or "",
    )


def _flow_descriptor_key(value: FlowIdentityDescriptor) -> tuple[object, ...]:
    return (
        value.version,
        value.kind.value,
        _source_descriptor_key(value.source),
        value.list_id or "",
        value.sender_address or "",
        value.automatic_intention.value,
        value.isolated_message_id or "",
    )


def source_identity_descriptor_from_parts(
    *,
    kind: str,
    sender_addresses: tuple[str, ...],
    isolated_message_id: str | None,
    version: int,
) -> SourceIdentityDescriptor:
    return SourceIdentityDescriptor(
        kind=SourceAnchorKind(kind),
        sender_addresses=sender_addresses,
        isolated_message_id=isolated_message_id,
        version=version,
    )


def flow_identity_descriptor_from_parts(
    *,
    kind: str,
    source: SourceIdentityDescriptor,
    list_id: str | None,
    sender_address: str | None,
    automatic_intention: Intencion,
    isolated_message_id: str | None,
    version: int,
) -> FlowIdentityDescriptor:
    return FlowIdentityDescriptor(
        kind=FlowAnchorKind(kind),
        source=source,
        list_id=list_id,
        sender_address=sender_address,
        automatic_intention=automatic_intention,
        isolated_message_id=isolated_message_id,
        version=version,
    )


def _versioned_id(value: str, field_name: str, pattern: re.Pattern[str]) -> str:
    _opaque_identifier(value, field_name)
    if pattern.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a versioned opaque identifier")
    return value


class PolicyCommandType(StrEnum):
    SET_SOURCE_DISPLAY_NAME = "set_source_display_name"
    SET_SOURCE_RUBRO = "set_source_rubro"
    SET_FLOW_DISPLAY_NAME = "set_flow_display_name"
    SET_FLOW_INTENTION = "set_flow_intention"
    MERGE_SOURCES = "merge_sources"
    PARTITION_SOURCE = "partition_source"
    PROTECT_TARGET = "protect_target"
    UNDO_POLICY = "undo_policy"


class PolicySelectorKind(StrEnum):
    MESSAGE = "message"
    SENDER = "sender"
    LABEL = "label"
    EFFECTIVE_SOURCE = "effective_source"
    EFFECTIVE_FLOW = "effective_flow"
    PARTITION_ANCHOR = "partition_anchor"


class EffectiveSourceKind(StrEnum):
    AUTOMATIC = "automatic"
    MERGED = "merged"
    PARTITION_GROUP = "partition_group"


class PartitionAnchorKind(StrEnum):
    SENDER = "sender"
    FLOW = "flow"
    MESSAGE = "message"


class PolicyAnchorRole(StrEnum):
    TARGET = "target"
    MERGE_PARTICIPANT = "merge_participant"
    PARTITION_MEMBER = "partition_member"


class PolicyRelationKind(StrEnum):
    SUPERSEDES = "supersedes"
    UNDOES = "undoes"
    STRUCTURAL_CONTEXT = "structural_context"


class PolicyBindingStatus(StrEnum):
    EXACT = "EXACT"
    REBOUND = "REBOUND"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ORPHANED = "ORPHANED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


class PolicyProtectionReason(StrEnum):
    SENT = "sent"
    DRAFT = "draft"
    TRASH = "trash"
    STARRED = "starred"
    IMPORTANT = "important"
    PROTECTED_LABEL = "protected_label"
    SECURITY = "security"
    DOCUMENT = "document"
    PERSONAL = "personal"
    LOW_CONFIDENCE = "low_confidence"
    CONTRADICTION = "contradiction"
    MIXED_CONVERSATION = "mixed_conversation"
    MANUAL_POLICY = "manual_policy"
    POLICY_REVIEW = "policy_review"


class PolicyEvidenceCode(StrEnum):
    SOURCE_DISPLAY_NAME = "policy.source_display_name"
    SOURCE_RUBRO = "policy.source_rubro"
    FLOW_DISPLAY_NAME = "policy.flow_display_name"
    FLOW_INTENTION = "policy.flow_intention"
    MERGE_SOURCES = "policy.merge_sources"
    PARTITION_SOURCE = "policy.partition_source"
    PROTECT_TARGET = "policy.protect_target"


class PolicyErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    MIXED_ACCOUNTS = "mixed_accounts"
    UNSUPPORTED_TARGET = "unsupported_target"
    TARGET_NOT_FOUND = "target_not_found"
    REVISION_CONFLICT = "revision_conflict"
    COMMAND_ID_CONFLICT = "command_id_conflict"
    POLICY_CONFLICT = "policy_conflict"
    INVALID_TRANSITION = "invalid_transition"
    UNKNOWN_POLICY_VERSION = "unknown_policy_version"


class PolicyError(RuntimeError):
    __slots__ = ()
    _RUNTIME_ATTRIBUTES = frozenset(
        {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
    )

    def __init__(self, code: PolicyErrorCode) -> None:
        if not isinstance(code, PolicyErrorCode):
            raise TypeError("code must be a PolicyErrorCode")
        super().__init__(code.value)

    @property
    def code(self) -> PolicyErrorCode:
        return PolicyErrorCode(self.args[0])

    def __getattribute__(self, name: str) -> object:
        if name == "__dict__":
            raise AttributeError("PolicyError is closed")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__setattr__(self, name, value)
            return
        raise AttributeError("PolicyError is immutable")

    def __delattr__(self, name: str) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__delattr__(self, name)
            return
        raise AttributeError("PolicyError is immutable")

    def __repr__(self) -> str:
        return f"PolicyError(code={self.code.value!r})"


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionAnchor:
    kind: PartitionAnchorKind
    sender_address: str | None = field(default=None, repr=False)
    flow: FlowIdentityDescriptor | None = field(default=None, repr=False)
    provider_message_id: str | None = field(default=None, repr=False)
    version: int = POLICY_SELECTOR_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PartitionAnchorKind):
            raise TypeError("kind must be a PartitionAnchorKind")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)
        if self.sender_address is not None:
            _canonical_address(self.sender_address, "sender_address")
        if self.flow is not None and not isinstance(self.flow, FlowIdentityDescriptor):
            raise TypeError("flow must be a FlowIdentityDescriptor or None")
        if self.provider_message_id is not None:
            _opaque_identifier(self.provider_message_id, "provider_message_id")
        populated = sum(
            value is not None
            for value in (self.sender_address, self.flow, self.provider_message_id)
        )
        if populated != 1:
            raise ValueError("partition anchor must contain exactly one value")
        if self.kind is PartitionAnchorKind.SENDER and self.sender_address is None:
            raise ValueError("sender partition anchor requires sender_address")
        if self.kind is PartitionAnchorKind.FLOW and self.flow is None:
            raise ValueError("flow partition anchor requires flow")
        if self.kind is PartitionAnchorKind.MESSAGE and self.provider_message_id is None:
            raise ValueError("message partition anchor requires provider_message_id")

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (
            self.version,
            self.kind.value,
            self.sender_address or "",
            _flow_descriptor_key(self.flow) if self.flow is not None else (),
            self.provider_message_id or "",
        )

    def __repr__(self) -> str:
        return f"PartitionAnchor(kind={self.kind.value!r}, version={self.version})"


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveSourceSelector:
    account_key: str = field(repr=False)
    kind: EffectiveSourceKind
    automatic_sources: tuple[SourceIdentityDescriptor, ...] = field(repr=False)
    partition_anchors: tuple[PartitionAnchor, ...] = field(default=(), repr=False)
    version: int = POLICY_SELECTOR_VERSION

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        if not isinstance(self.kind, EffectiveSourceKind):
            raise TypeError("kind must be an EffectiveSourceKind")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)
        if not isinstance(self.automatic_sources, tuple) or any(
            not isinstance(item, SourceIdentityDescriptor)
            for item in self.automatic_sources
        ):
            raise TypeError("automatic_sources must contain SourceIdentityDescriptor values")
        if not self.automatic_sources:
            raise ValueError("automatic_sources must not be empty")
        source_keys = tuple(_source_descriptor_key(item) for item in self.automatic_sources)
        if len(set(source_keys)) != len(source_keys) or source_keys != tuple(sorted(source_keys)):
            raise ValueError("automatic_sources must be canonical, unique and ordered")
        if not isinstance(self.partition_anchors, tuple) or any(
            not isinstance(item, PartitionAnchor) for item in self.partition_anchors
        ):
            raise TypeError("partition_anchors must contain PartitionAnchor values")
        anchor_keys = tuple(item.canonical_key for item in self.partition_anchors)
        if len(set(anchor_keys)) != len(anchor_keys) or anchor_keys != tuple(sorted(anchor_keys)):
            raise ValueError("partition_anchors must be canonical, unique and ordered")
        if self.kind is EffectiveSourceKind.AUTOMATIC:
            if len(self.automatic_sources) != 1 or self.partition_anchors:
                raise ValueError("automatic source selector has invalid anchors")
        elif self.kind is EffectiveSourceKind.MERGED:
            if len(self.automatic_sources) < 2 or self.partition_anchors:
                raise ValueError("merged source selector has invalid anchors")
        elif len(self.automatic_sources) != 1 or not self.partition_anchors:
            raise ValueError("partition source selector has invalid anchors")
        for anchor in self.partition_anchors:
            if anchor.flow is not None and anchor.flow.source != self.automatic_sources[0]:
                raise ValueError("partition flow anchor must belong to the automatic source")

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (
            self.version,
            self.account_key,
            self.kind.value,
            tuple(_source_descriptor_key(item) for item in self.automatic_sources),
            tuple(item.canonical_key for item in self.partition_anchors),
        )

    def __repr__(self) -> str:
        return (
            "EffectiveSourceSelector(account_key=<redacted>, "
            f"kind={self.kind.value!r}, automatic_source_count="
            f"{len(self.automatic_sources)}, partition_anchor_count="
            f"{len(self.partition_anchors)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveFlowSelector:
    account_key: str = field(repr=False)
    automatic_flow: FlowIdentityDescriptor = field(repr=False)
    effective_source: EffectiveSourceSelector = field(repr=False)
    version: int = POLICY_SELECTOR_VERSION

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        if not isinstance(self.automatic_flow, FlowIdentityDescriptor):
            raise TypeError("automatic_flow must be a FlowIdentityDescriptor")
        if not isinstance(self.effective_source, EffectiveSourceSelector):
            raise TypeError("effective_source must be an EffectiveSourceSelector")
        if self.effective_source.account_key != self.account_key:
            raise ValueError("effective flow selector references another account")
        if self.automatic_flow.source not in self.effective_source.automatic_sources:
            raise ValueError("automatic flow must belong to the effective source")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (
            self.version,
            self.account_key,
            _flow_descriptor_key(self.automatic_flow),
            self.effective_source.canonical_key,
        )

    def __repr__(self) -> str:
        return (
            "EffectiveFlowSelector(account_key=<redacted>, "
            f"flow_kind={self.automatic_flow.kind.value!r}, "
            f"source_kind={self.effective_source.kind.value!r}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageSelector:
    account_key: str = field(repr=False)
    provider_message_id: str = field(repr=False)
    version: int = POLICY_SELECTOR_VERSION
    kind: PolicySelectorKind = field(init=False, default=PolicySelectorKind.MESSAGE)

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        _opaque_identifier(self.provider_message_id, "provider_message_id")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (self.version, self.kind.value, self.account_key, self.provider_message_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class SenderSelector:
    account_key: str = field(repr=False)
    sender_address: str = field(repr=False)
    version: int = POLICY_SELECTOR_VERSION
    kind: PolicySelectorKind = field(init=False, default=PolicySelectorKind.SENDER)

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        _canonical_address(self.sender_address, "sender_address")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (self.version, self.kind.value, self.account_key, self.sender_address)


@dataclass(frozen=True, slots=True, kw_only=True)
class LabelSelector:
    account_key: str = field(repr=False)
    label_id: str = field(repr=False)
    version: int = POLICY_SELECTOR_VERSION
    kind: PolicySelectorKind = field(init=False, default=PolicySelectorKind.LABEL)

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        _opaque_identifier(self.label_id, "label_id")
        _exact_version(self.version, POLICY_SELECTOR_VERSION)

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (self.version, self.kind.value, self.account_key, self.label_id)


PolicyTargetSelector: TypeAlias = (
    MessageSelector
    | SenderSelector
    | LabelSelector
    | EffectiveSourceSelector
    | EffectiveFlowSelector
)


def policy_selector_kind(value: PolicyTargetSelector | PartitionAnchor) -> PolicySelectorKind:
    if isinstance(value, MessageSelector):
        return PolicySelectorKind.MESSAGE
    if isinstance(value, SenderSelector):
        return PolicySelectorKind.SENDER
    if isinstance(value, LabelSelector):
        return PolicySelectorKind.LABEL
    if isinstance(value, EffectiveSourceSelector):
        return PolicySelectorKind.EFFECTIVE_SOURCE
    if isinstance(value, EffectiveFlowSelector):
        return PolicySelectorKind.EFFECTIVE_FLOW
    if isinstance(value, PartitionAnchor):
        return PolicySelectorKind.PARTITION_ANCHOR
    raise TypeError("value must be a closed policy selector")


def policy_selector_account(value: PolicyTargetSelector | PartitionAnchor) -> str | None:
    if isinstance(value, PartitionAnchor):
        return None
    return value.account_key


def policy_selector_key(value: PolicyTargetSelector | PartitionAnchor) -> tuple[object, ...]:
    kind = policy_selector_kind(value)
    return (kind.value, value.canonical_key)


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionGroup:
    anchors: tuple[PartitionAnchor, ...] = field(repr=False)
    version: int = POLICY_SELECTOR_VERSION

    def __post_init__(self) -> None:
        _exact_version(self.version, POLICY_SELECTOR_VERSION)
        if not isinstance(self.anchors, tuple) or any(
            not isinstance(item, PartitionAnchor) for item in self.anchors
        ):
            raise TypeError("anchors must contain PartitionAnchor values")
        if not self.anchors:
            raise ValueError("partition group must not be empty")
        keys = tuple(item.canonical_key for item in self.anchors)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError("partition group anchors must be canonical, unique and ordered")

    @property
    def canonical_key(self) -> tuple[object, ...]:
        return (self.version, tuple(item.canonical_key for item in self.anchors))

    def __repr__(self) -> str:
        return f"PartitionGroup(anchor_count={len(self.anchors)}, version={self.version})"


@dataclass(frozen=True, slots=True, kw_only=True)
class _CommandBase:
    command_id: str = field(repr=False)
    account_key: str = field(repr=False)
    occurred_at: datetime = field(repr=False)
    expected_revision: int
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        _opaque_identifier(self.command_id, "command_id")
        _account_key(self.account_key)
        object.__setattr__(self, "occurred_at", _utc_datetime(self.occurred_at, "occurred_at"))
        _non_negative_int(self.expected_revision, "expected_revision")
        _exact_version(self.version, POLICY_MODEL_VERSION)


@dataclass(frozen=True, slots=True, kw_only=True)
class _DecisionBase(_CommandBase):
    decision_id: str = field(repr=False)
    supersedes_decision_ids: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        _CommandBase.__post_init__(self)
        _opaque_identifier(self.decision_id, "decision_id")
        _string_tuple(
            self.supersedes_decision_ids,
            "supersedes_decision_ids",
            allow_empty=True,
        )
        if self.decision_id in self.supersedes_decision_ids:
            raise ValueError("a decision cannot supersede itself")


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSourceDisplayName(_DecisionBase):
    selector: EffectiveSourceSelector = field(repr=False)
    display_name: str = field(repr=False)
    command_type: PolicyCommandType = field(
        init=False, default=PolicyCommandType.SET_SOURCE_DISPLAY_NAME
    )

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.selector, EffectiveSourceSelector):
            raise TypeError("selector must be an EffectiveSourceSelector")
        if self.selector.account_key != self.account_key:
            raise ValueError("selector references another account")
        _normalized_text(self.display_name, "display_name")


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSourceRubro(_DecisionBase):
    selector: EffectiveSourceSelector = field(repr=False)
    rubro: Rubro
    command_type: PolicyCommandType = field(init=False, default=PolicyCommandType.SET_SOURCE_RUBRO)

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.selector, EffectiveSourceSelector):
            raise TypeError("selector must be an EffectiveSourceSelector")
        if self.selector.account_key != self.account_key:
            raise ValueError("selector references another account")
        if not isinstance(self.rubro, Rubro):
            raise TypeError("rubro must be a Rubro")


@dataclass(frozen=True, slots=True, kw_only=True)
class SetFlowDisplayName(_DecisionBase):
    selector: EffectiveFlowSelector = field(repr=False)
    display_name: str = field(repr=False)
    command_type: PolicyCommandType = field(
        init=False, default=PolicyCommandType.SET_FLOW_DISPLAY_NAME
    )

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.selector, EffectiveFlowSelector):
            raise TypeError("selector must be an EffectiveFlowSelector")
        if self.selector.account_key != self.account_key:
            raise ValueError("selector references another account")
        _normalized_text(self.display_name, "display_name")


@dataclass(frozen=True, slots=True, kw_only=True)
class SetFlowIntention(_DecisionBase):
    selector: EffectiveFlowSelector = field(repr=False)
    intention: Intencion
    command_type: PolicyCommandType = field(
        init=False, default=PolicyCommandType.SET_FLOW_INTENTION
    )

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.selector, EffectiveFlowSelector):
            raise TypeError("selector must be an EffectiveFlowSelector")
        if self.selector.account_key != self.account_key:
            raise ValueError("selector references another account")
        if not isinstance(self.intention, Intencion):
            raise TypeError("intention must be an Intencion")


@dataclass(frozen=True, slots=True, kw_only=True)
class MergeSources(_DecisionBase):
    source_selectors: tuple[EffectiveSourceSelector, ...] = field(repr=False)
    command_type: PolicyCommandType = field(init=False, default=PolicyCommandType.MERGE_SOURCES)

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.source_selectors, tuple) or any(
            not isinstance(item, EffectiveSourceSelector) for item in self.source_selectors
        ):
            raise TypeError("source_selectors must contain EffectiveSourceSelector values")
        if len(self.source_selectors) < 2:
            raise ValueError("merge requires at least two source selectors")
        if any(item.account_key != self.account_key for item in self.source_selectors):
            raise ValueError("merge selectors reference another account")
        if any(item.kind is not EffectiveSourceKind.AUTOMATIC for item in self.source_selectors):
            raise ValueError("v1 merges only automatic sources")
        keys = tuple(item.canonical_key for item in self.source_selectors)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError("merge selectors must be canonical, unique and ordered")


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionSource(_DecisionBase):
    source_selector: EffectiveSourceSelector = field(repr=False)
    groups: tuple[PartitionGroup, ...] = field(repr=False)
    command_type: PolicyCommandType = field(init=False, default=PolicyCommandType.PARTITION_SOURCE)

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        if not isinstance(self.source_selector, EffectiveSourceSelector):
            raise TypeError("source_selector must be an EffectiveSourceSelector")
        if self.source_selector.account_key != self.account_key:
            raise ValueError("source selector references another account")
        if self.source_selector.kind is not EffectiveSourceKind.AUTOMATIC:
            raise ValueError("v1 partitions only an automatic source")
        if not isinstance(self.groups, tuple) or any(
            not isinstance(item, PartitionGroup) for item in self.groups
        ):
            raise TypeError("groups must contain PartitionGroup values")
        if len(self.groups) < 2:
            raise ValueError("partition requires at least two groups")
        keys = tuple(item.canonical_key for item in self.groups)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError("partition groups must be canonical, unique and ordered")
        anchors = tuple(anchor for group in self.groups for anchor in group.anchors)
        anchor_keys = tuple(anchor.canonical_key for anchor in anchors)
        if len(set(anchor_keys)) != len(anchor_keys):
            raise ValueError("partition anchors must be disjoint")
        automatic_source = self.source_selector.automatic_sources[0]
        if any(
            anchor.flow is not None and anchor.flow.source != automatic_source
            for anchor in anchors
        ):
            raise ValueError("partition flow anchor references another source")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtectTarget(_DecisionBase):
    selector: PolicyTargetSelector = field(repr=False)
    protection: Proteccion = Proteccion.USUARIO
    command_type: PolicyCommandType = field(init=False, default=PolicyCommandType.PROTECT_TARGET)

    def __post_init__(self) -> None:
        _DecisionBase.__post_init__(self)
        policy_selector_kind(self.selector)
        if policy_selector_account(self.selector) != self.account_key:
            raise ValueError("selector references another account")
        if self.protection is not Proteccion.USUARIO:
            raise ValueError("ProtectTarget can only add user protection")


@dataclass(frozen=True, slots=True, kw_only=True)
class UndoPolicy(_CommandBase):
    target_decision_id: str = field(repr=False)
    command_type: PolicyCommandType = field(init=False, default=PolicyCommandType.UNDO_POLICY)

    def __post_init__(self) -> None:
        _CommandBase.__post_init__(self)
        _opaque_identifier(self.target_decision_id, "target_decision_id")


PolicyDecisionCommand: TypeAlias = (
    SetSourceDisplayName
    | SetSourceRubro
    | SetFlowDisplayName
    | SetFlowIntention
    | MergeSources
    | PartitionSource
    | ProtectTarget
)
LocalPolicyCommand: TypeAlias = PolicyDecisionCommand | UndoPolicy


def is_policy_decision_command(value: object) -> TypeGuard[PolicyDecisionCommand]:
    return isinstance(
        value,
        (
            SetSourceDisplayName,
            SetSourceRubro,
            SetFlowDisplayName,
            SetFlowIntention,
            MergeSources,
            PartitionSource,
            ProtectTarget,
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedPolicyAnchor:
    anchor_order: int
    role: PolicyAnchorRole
    selector: PolicyTargetSelector | PartitionAnchor = field(repr=False)
    group_order: int | None = None
    classification_version: int = CLASSIFICATION_MODEL_VERSION
    observed_effective_id: str | None = field(default=None, repr=False)
    observed_source_ids: tuple[str, ...] = field(default=(), repr=False)
    observed_flow_ids: tuple[str, ...] = field(default=(), repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        _non_negative_int(self.anchor_order, "anchor_order")
        if not isinstance(self.role, PolicyAnchorRole):
            raise TypeError("role must be a PolicyAnchorRole")
        policy_selector_kind(self.selector)
        if self.role is PolicyAnchorRole.PARTITION_MEMBER:
            if not isinstance(self.selector, PartitionAnchor) or self.group_order is None:
                raise ValueError("partition member requires an anchor and group_order")
            _non_negative_int(self.group_order, "group_order")
        elif self.group_order is not None:
            raise ValueError("only partition members may contain group_order")
        _exact_version(
            self.classification_version,
            CLASSIFICATION_MODEL_VERSION,
            "classification_version",
        )
        _exact_version(self.version, POLICY_MODEL_VERSION)
        if self.observed_effective_id is not None:
            _opaque_identifier(self.observed_effective_id, "observed_effective_id")
        _string_tuple(
            self.observed_source_ids,
            "observed_source_ids",
        )
        _string_tuple(
            self.observed_flow_ids,
            "observed_flow_ids",
        )
        for source_id in self.observed_source_ids:
            _versioned_id(source_id, "observed source id", _SOURCE_ID)
        for flow_id in self.observed_flow_ids:
            _versioned_id(flow_id, "observed flow id", _FLOW_ID)
        _string_tuple(
            self.structural_decision_ids,
            "structural_decision_ids",
            allow_empty=True,
        )
        if isinstance(self.selector, EffectiveSourceSelector):
            if self.observed_effective_id is None:
                raise ValueError("effective source anchor requires observed_effective_id")
            _versioned_id(
                self.observed_effective_id,
                "observed_effective_id",
                _EFFECTIVE_SOURCE_ID,
            )
        elif isinstance(self.selector, EffectiveFlowSelector):
            if self.observed_effective_id is None:
                raise ValueError("effective flow anchor requires observed_effective_id")
            _versioned_id(
                self.observed_effective_id,
                "observed_effective_id",
                _EFFECTIVE_FLOW_ID,
            )
        elif self.observed_effective_id is not None:
            raise ValueError("only effective selectors contain observed_effective_id")

    def __repr__(self) -> str:
        return (
            f"PreparedPolicyAnchor(anchor_order={self.anchor_order}, "
            f"role={self.role.value!r}, selector_kind="
            f"{policy_selector_kind(self.selector).value!r}, group_order="
            f"{self.group_order!r}, classification_version={self.classification_version}, "
            f"observed_source_count={len(self.observed_source_ids)}, "
            f"observed_flow_count={len(self.observed_flow_ids)}, "
            f"structural_context_count={len(self.structural_decision_ids)}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedPolicyRelation:
    relation_order: int
    kind: PolicyRelationKind
    target_decision_id: str = field(repr=False)
    anchor_order: int | None = None
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        _non_negative_int(self.relation_order, "relation_order")
        if not isinstance(self.kind, PolicyRelationKind):
            raise TypeError("kind must be a PolicyRelationKind")
        _opaque_identifier(self.target_decision_id, "target_decision_id")
        if self.kind is PolicyRelationKind.STRUCTURAL_CONTEXT:
            if self.anchor_order is None:
                raise ValueError("structural context requires anchor_order")
            _non_negative_int(self.anchor_order, "anchor_order")
        elif self.anchor_order is not None:
            raise ValueError("only structural context may reference an anchor")
        _exact_version(self.version, POLICY_MODEL_VERSION)


def _validate_anchor_sequence(value: tuple[PreparedPolicyAnchor, ...]) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, PreparedPolicyAnchor) for item in value
    ):
        raise TypeError("anchors must contain PreparedPolicyAnchor values")
    if tuple(item.anchor_order for item in value) != tuple(range(len(value))):
        raise ValueError("anchor_order must form a canonical contiguous sequence")


def _validate_relation_sequence(value: tuple[PreparedPolicyRelation, ...]) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, PreparedPolicyRelation) for item in value
    ):
        raise TypeError("relations must contain PreparedPolicyRelation values")
    if tuple(item.relation_order for item in value) != tuple(range(len(value))):
        raise ValueError("relation_order must form a canonical contiguous sequence")
    keys = tuple(
        (
            item.kind.value,
            item.anchor_order if item.anchor_order is not None else -1,
            item.target_decision_id,
        )
        for item in value
    )
    if len(set(keys)) != len(keys):
        raise ValueError("relations must not contain duplicates")


def _command_selector(command: PolicyDecisionCommand) -> PolicyTargetSelector | None:
    if isinstance(
        command,
        (
            SetSourceDisplayName,
            SetSourceRubro,
            SetFlowDisplayName,
            SetFlowIntention,
            ProtectTarget,
        ),
    ):
        return command.selector
    return None


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedPolicyDecision:
    command: PolicyDecisionCommand = field(repr=False)
    anchors: tuple[PreparedPolicyAnchor, ...] = field(repr=False)
    relations: tuple[PreparedPolicyRelation, ...] = field(default=(), repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        if not is_policy_decision_command(self.command):
            raise TypeError("command must be a PolicyDecisionCommand")
        _exact_version(self.version, POLICY_MODEL_VERSION)
        _validate_anchor_sequence(self.anchors)
        if not self.anchors:
            raise ValueError("prepared decision must contain anchors")
        _validate_relation_sequence(self.relations)
        if any(
            (account := policy_selector_account(anchor.selector)) is not None
            and account != self.command.account_key
            for anchor in self.anchors
        ):
            raise ValueError("prepared anchor references another account")

        command_selector = _command_selector(self.command)
        if command_selector is not None:
            if len(self.anchors) != 1 or self.anchors[0].role is not PolicyAnchorRole.TARGET:
                raise ValueError("targeted command requires exactly one target anchor")
            if self.anchors[0].selector != command_selector:
                raise ValueError("prepared target does not match original command")
        elif isinstance(self.command, MergeSources):
            if any(
                anchor.role is not PolicyAnchorRole.MERGE_PARTICIPANT
                or not isinstance(anchor.selector, EffectiveSourceSelector)
                for anchor in self.anchors
            ):
                raise ValueError("merge preparation contains invalid anchors")
            if tuple(anchor.selector for anchor in self.anchors) != self.command.source_selectors:
                raise ValueError("merge preparation does not match original command")
        elif isinstance(self.command, PartitionSource):
            first, *members = self.anchors
            if (
                first.role is not PolicyAnchorRole.TARGET
                or first.selector != self.command.source_selector
                or any(
                    member.role is not PolicyAnchorRole.PARTITION_MEMBER
                    or not isinstance(member.selector, PartitionAnchor)
                    for member in members
                )
            ):
                raise ValueError("partition preparation contains invalid anchors")
            grouped = tuple(
                PartitionGroup(
                    anchors=tuple(
                        member.selector
                        for member in members
                        if member.group_order == group_order
                        and isinstance(member.selector, PartitionAnchor)
                    )
                )
                for group_order in range(len(self.command.groups))
            )
            if grouped != self.command.groups:
                raise ValueError("partition preparation does not match original command")
            expected_members = tuple(
                (group_order, anchor)
                for group_order, group in enumerate(self.command.groups)
                for anchor in group.anchors
            )
            actual_members = tuple(
                (member.group_order, member.selector) for member in members
            )
            if actual_members != expected_members:
                raise ValueError("partition prepared anchors must be canonical")

        supersedes = tuple(
            relation.target_decision_id
            for relation in self.relations
            if relation.kind is PolicyRelationKind.SUPERSEDES
        )
        if supersedes != self.command.supersedes_decision_ids:
            raise ValueError("prepared supersedes relations do not match original command")
        if any(relation.kind is PolicyRelationKind.UNDOES for relation in self.relations):
            raise ValueError("prepared decision cannot contain an undo relation")
        expected_relations = tuple(
            (PolicyRelationKind.SUPERSEDES, None, decision_id)
            for decision_id in self.command.supersedes_decision_ids
        ) + tuple(
            (PolicyRelationKind.STRUCTURAL_CONTEXT, anchor.anchor_order, decision_id)
            for anchor in self.anchors
            for decision_id in anchor.structural_decision_ids
        )
        actual_relations = tuple(
            (relation.kind, relation.anchor_order, relation.target_decision_id)
            for relation in self.relations
        )
        if actual_relations != expected_relations:
            raise ValueError("prepared relations must match canonical command context")

    def __repr__(self) -> str:
        return (
            "PreparedPolicyDecision(command=<redacted>, "
            f"command_type={self.command.command_type.value!r}, "
            f"anchor_count={len(self.anchors)}, relation_count={len(self.relations)}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyEvent:
    command: LocalPolicyCommand = field(repr=False)
    account_revision: int
    anchors: tuple[PreparedPolicyAnchor, ...] = field(default=(), repr=False)
    relations: tuple[PreparedPolicyRelation, ...] = field(default=(), repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        if not is_policy_decision_command(self.command) and not isinstance(
            self.command, UndoPolicy
        ):
            raise TypeError("command must be a LocalPolicyCommand")
        _exact_version(self.version, POLICY_MODEL_VERSION)
        _non_negative_int(self.account_revision, "account_revision")
        if self.account_revision != self.command.expected_revision + 1:
            raise ValueError("account_revision must advance expected_revision exactly once")
        _validate_anchor_sequence(self.anchors)
        _validate_relation_sequence(self.relations)
        if is_policy_decision_command(self.command):
            PreparedPolicyDecision(
                command=self.command,
                anchors=self.anchors,
                relations=self.relations,
            )
        else:
            if not isinstance(self.command, UndoPolicy):
                raise TypeError("command must be an UndoPolicy")
            if self.anchors:
                raise ValueError("undo event must not contain anchors")
            if len(self.relations) != 1:
                raise ValueError("undo event requires exactly one relation")
            relation = self.relations[0]
            if (
                relation.kind is not PolicyRelationKind.UNDOES
                or relation.target_decision_id != self.command.target_decision_id
            ):
                raise ValueError("undo relation does not match original command")

    def __repr__(self) -> str:
        return (
            "PolicyEvent(command=<redacted>, "
            f"command_type={self.command.command_type.value!r}, "
            f"account_revision={self.account_revision}, anchor_count={len(self.anchors)}, "
            f"relation_count={len(self.relations)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ActivePolicy:
    command: PolicyDecisionCommand = field(repr=False)
    account_revision: int
    anchors: tuple[PreparedPolicyAnchor, ...] = field(repr=False)
    relations: tuple[PreparedPolicyRelation, ...] = field(default=(), repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        if not is_policy_decision_command(self.command):
            raise TypeError("command must be a PolicyDecisionCommand")
        PolicyEvent(
            command=self.command,
            account_revision=self.account_revision,
            anchors=self.anchors,
            relations=self.relations,
            version=self.version,
        )

    @property
    def account_key(self) -> str:
        return self.command.account_key

    @property
    def decision_id(self) -> str:
        return self.command.decision_id

    def __repr__(self) -> str:
        return (
            "ActivePolicy(command=<redacted>, "
            f"command_type={self.command.command_type.value!r}, "
            f"account_revision={self.account_revision}, anchor_count={len(self.anchors)}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyBinding:
    decision_id: str = field(repr=False)
    status: PolicyBindingStatus
    selectors: tuple[PolicyTargetSelector | PartitionAnchor, ...] = field(repr=False)
    observed_effective_ids: tuple[str, ...] = field(default=(), repr=False)
    current_effective_ids: tuple[str, ...] = field(default=(), repr=False)
    observed_source_ids: tuple[str, ...] = field(default=(), repr=False)
    current_source_ids: tuple[str, ...] = field(default=(), repr=False)
    observed_flow_ids: tuple[str, ...] = field(default=(), repr=False)
    current_flow_ids: tuple[str, ...] = field(default=(), repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)
    current_structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)
    affected_message_ids: tuple[str, ...] = field(default=(), repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        _opaque_identifier(self.decision_id, "decision_id")
        if not isinstance(self.status, PolicyBindingStatus):
            raise TypeError("status must be a PolicyBindingStatus")
        if not isinstance(self.selectors, tuple) or not self.selectors:
            raise ValueError("selectors must be a non-empty tuple")
        for selector in self.selectors:
            policy_selector_kind(selector)
        _exact_version(self.version, POLICY_MODEL_VERSION)
        for field_name in (
            "observed_effective_ids",
            "current_effective_ids",
            "observed_source_ids",
            "current_source_ids",
            "observed_flow_ids",
            "current_flow_ids",
            "structural_decision_ids",
            "current_structural_decision_ids",
            "affected_message_ids",
        ):
            _string_tuple(getattr(self, field_name), field_name, allow_empty=True)
        for source_id in (*self.observed_source_ids, *self.current_source_ids):
            _versioned_id(source_id, "source id", _SOURCE_ID)
        for flow_id in (*self.observed_flow_ids, *self.current_flow_ids):
            _versioned_id(flow_id, "flow id", _FLOW_ID)
        for effective_id in (
            *self.observed_effective_ids,
            *self.current_effective_ids,
        ):
            _opaque_identifier(effective_id, "effective id")
            if (
                _EFFECTIVE_SOURCE_ID.fullmatch(effective_id) is None
                and _EFFECTIVE_FLOW_ID.fullmatch(effective_id) is None
            ):
                raise ValueError("effective id must be versioned and opaque")

    def __repr__(self) -> str:
        return (
            "PolicyBinding(decision_id=<redacted>, "
            f"status={self.status.value!r}, selector_count={len(self.selectors)}, "
            f"current_candidate_count={len(self.current_effective_ids)}, "
            f"affected_message_count={len(self.affected_message_ids)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyDecisionEvidence:
    code: PolicyEvidenceCode
    decision_id: str = field(repr=False)
    version: int = POLICY_MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.code, PolicyEvidenceCode):
            raise TypeError("code must be a PolicyEvidenceCode")
        _opaque_identifier(self.decision_id, "decision_id")
        _exact_version(self.version, POLICY_MODEL_VERSION)

    def __repr__(self) -> str:
        return (
            f"PolicyDecisionEvidence(code={self.code.value!r}, "
            f"decision_id=<redacted>, version={self.version})"
        )


EffectiveEvidence: TypeAlias = ClassificationEvidence | PolicyDecisionEvidence


def evidence_sort_key(value: EffectiveEvidence) -> tuple[object, ...]:
    if isinstance(value, ClassificationEvidence):
        return (
            0,
            value.code.value,
            value.strength.value,
            value.origin.value,
            value.label,
            value.detail,
        )
    if isinstance(value, PolicyDecisionEvidence):
        return (1, value.code.value, value.decision_id)
    raise TypeError("evidence must be closed and typed")


def _evidence_tuple(value: tuple[EffectiveEvidence, ...], field_name: str) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, (ClassificationEvidence, PolicyDecisionEvidence))
        for item in value
    ):
        raise TypeError(f"{field_name} must contain typed evidence")
    keys = tuple(evidence_sort_key(item) for item in value)
    if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
        raise ValueError(f"{field_name} must be canonical, unique and ordered")


_PROTECTION_RANK = {
    Proteccion.ORDINARIA: 0,
    Proteccion.REVISION: 1,
    Proteccion.USUARIO: 2,
    Proteccion.DOCUMENTAL: 3,
    Proteccion.CRITICA: 4,
}


def _validate_protection_projection(
    *,
    automatic_protection: Proteccion,
    effective_protection: Proteccion,
    protected: bool,
    review_required: bool,
    hard_excluded: bool,
    protection_reasons: tuple[PolicyProtectionReason, ...],
    decision_ids: tuple[str, ...],
) -> None:
    if not isinstance(automatic_protection, Proteccion) or not isinstance(
        effective_protection, Proteccion
    ):
        raise TypeError("protection values must be Proteccion values")
    if _PROTECTION_RANK[effective_protection] < _PROTECTION_RANK[automatic_protection]:
        raise ValueError("effective protection must not weaken automatic protection")
    if not isinstance(protected, bool) or not isinstance(review_required, bool) or not isinstance(
        hard_excluded, bool
    ):
        raise TypeError("protection flags must be booleans")
    if hard_excluded and not protected:
        raise ValueError("a hard exclusion must be protected")
    if not isinstance(protection_reasons, tuple) or any(
        not isinstance(item, PolicyProtectionReason) for item in protection_reasons
    ):
        raise TypeError("protection_reasons must contain PolicyProtectionReason values")
    reason_values = tuple(item.value for item in protection_reasons)
    if len(set(reason_values)) != len(reason_values) or reason_values != tuple(
        sorted(reason_values)
    ):
        raise ValueError("protection reasons must be canonical, unique and ordered")
    if protected != bool(protection_reasons):
        raise ValueError("protected must agree with protection reasons")
    _string_tuple(decision_ids, "decision_ids", allow_empty=True)


def _validate_confidence_projection(
    automatic: Confianza,
    effective: Confianza,
) -> None:
    if not isinstance(automatic, Confianza) or not isinstance(effective, Confianza):
        raise TypeError("confidence values must be Confianza values")
    if _CONFIDENCE_RANK[effective] < _CONFIDENCE_RANK[automatic]:
        raise ValueError("effective confidence must not improve automatic confidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveMessage:
    provider_message_id: str = field(repr=False)
    automatic_source_id: str
    effective_source_id: str
    automatic_flow_id: str
    effective_flow_id: str
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    automatic_protection: Proteccion
    effective_protection: Proteccion
    protected: bool
    review_required: bool
    hard_excluded: bool
    protection_reasons: tuple[PolicyProtectionReason, ...]
    decision_ids: tuple[str, ...] = field(repr=False)
    automatic_evidence: tuple[ClassificationEvidence, ...] = field(repr=False)
    effective_evidence: tuple[EffectiveEvidence, ...] = field(repr=False)
    version: int = POLICY_RESULT_VERSION

    def __post_init__(self) -> None:
        _opaque_identifier(self.provider_message_id, "provider_message_id")
        _versioned_id(self.automatic_source_id, "automatic_source_id", _SOURCE_ID)
        _versioned_id(self.effective_source_id, "effective_source_id", _EFFECTIVE_SOURCE_ID)
        _versioned_id(self.automatic_flow_id, "automatic_flow_id", _FLOW_ID)
        _versioned_id(self.effective_flow_id, "effective_flow_id", _EFFECTIVE_FLOW_ID)
        if not isinstance(self.automatic_rubro, Rubro) or not isinstance(
            self.effective_rubro, Rubro
        ):
            raise TypeError("rubro values must be Rubro values")
        if not isinstance(self.automatic_intention, Intencion) or not isinstance(
            self.effective_intention, Intencion
        ):
            raise TypeError("intention values must be Intencion values")
        if not isinstance(self.subscription, Suscripcion):
            raise TypeError("subscription must be a Suscripcion")
        _validate_confidence_projection(
            self.automatic_confidence, self.effective_confidence
        )
        _validate_protection_projection(
            automatic_protection=self.automatic_protection,
            effective_protection=self.effective_protection,
            protected=self.protected,
            review_required=self.review_required,
            hard_excluded=self.hard_excluded,
            protection_reasons=self.protection_reasons,
            decision_ids=self.decision_ids,
        )
        _evidence_tuple(self.automatic_evidence, "automatic_evidence")
        if any(not isinstance(item, ClassificationEvidence) for item in self.automatic_evidence):
            raise TypeError("automatic_evidence must contain ClassificationEvidence values")
        _evidence_tuple(self.effective_evidence, "effective_evidence")
        if not set(self.automatic_evidence).issubset(self.effective_evidence):
            raise ValueError("effective evidence must preserve automatic evidence")
        _exact_version(self.version, POLICY_RESULT_VERSION)

    def __repr__(self) -> str:
        return (
            "EffectiveMessage(provider_message_id=<redacted>, "
            f"automatic_source_id={self.automatic_source_id!r}, "
            f"effective_source_id={self.effective_source_id!r}, "
            f"automatic_flow_id={self.automatic_flow_id!r}, "
            f"effective_flow_id={self.effective_flow_id!r}, protected={self.protected}, "
            f"review_required={self.review_required}, hard_excluded={self.hard_excluded}, "
            f"decision_count={len(self.decision_ids)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveSource:
    effective_source_id: str
    selector: EffectiveSourceSelector = field(repr=False)
    automatic_source_ids: tuple[str, ...]
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    flow_ids: tuple[str, ...]
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_confidence: Confianza
    effective_confidence: Confianza
    automatic_protection: Proteccion
    effective_protection: Proteccion
    protected: bool
    review_required: bool
    hard_excluded: bool
    protection_reasons: tuple[PolicyProtectionReason, ...]
    decision_ids: tuple[str, ...] = field(repr=False)
    automatic_evidence: tuple[ClassificationEvidence, ...] = field(repr=False)
    effective_evidence: tuple[EffectiveEvidence, ...] = field(repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)
    version: int = POLICY_RESULT_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.effective_source_id, "effective_source_id", _EFFECTIVE_SOURCE_ID)
        if not isinstance(self.selector, EffectiveSourceSelector):
            raise TypeError("selector must be an EffectiveSourceSelector")
        _string_tuple(self.automatic_source_ids, "automatic_source_ids")
        for source_id in self.automatic_source_ids:
            _versioned_id(source_id, "automatic source id", _SOURCE_ID)
        if len(self.automatic_source_ids) != len(self.selector.automatic_sources):
            raise ValueError("automatic source IDs must match selector membership")
        _normalized_text(self.automatic_display_name, "automatic_display_name")
        _normalized_text(self.effective_display_name, "effective_display_name")
        _string_tuple(self.message_ids, "message_ids")
        _string_tuple(self.flow_ids, "flow_ids")
        for flow_id in self.flow_ids:
            _versioned_id(flow_id, "effective flow id", _EFFECTIVE_FLOW_ID)
        if not isinstance(self.automatic_rubro, Rubro) or not isinstance(
            self.effective_rubro, Rubro
        ):
            raise TypeError("rubro values must be Rubro values")
        _validate_confidence_projection(
            self.automatic_confidence, self.effective_confidence
        )
        _validate_protection_projection(
            automatic_protection=self.automatic_protection,
            effective_protection=self.effective_protection,
            protected=self.protected,
            review_required=self.review_required,
            hard_excluded=self.hard_excluded,
            protection_reasons=self.protection_reasons,
            decision_ids=self.decision_ids,
        )
        _evidence_tuple(self.automatic_evidence, "automatic_evidence")
        if any(not isinstance(item, ClassificationEvidence) for item in self.automatic_evidence):
            raise TypeError("automatic_evidence must contain ClassificationEvidence values")
        _evidence_tuple(self.effective_evidence, "effective_evidence")
        if not set(self.automatic_evidence).issubset(self.effective_evidence):
            raise ValueError("effective evidence must preserve automatic evidence")
        _string_tuple(
            self.structural_decision_ids,
            "structural_decision_ids",
            allow_empty=True,
        )
        _exact_version(self.version, POLICY_RESULT_VERSION)

    def __repr__(self) -> str:
        return (
            f"EffectiveSource(effective_source_id={self.effective_source_id!r}, "
            f"selector_kind={self.selector.kind.value!r}, "
            f"automatic_source_count={len(self.automatic_source_ids)}, "
            f"message_count={len(self.message_ids)}, flow_ids={self.flow_ids!r}, "
            f"protected={self.protected}, review_required={self.review_required}, "
            f"decision_count={len(self.decision_ids)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveFlow:
    effective_flow_id: str
    effective_source_id: str
    selector: EffectiveFlowSelector = field(repr=False)
    automatic_flow_id: str
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    automatic_protection: Proteccion
    effective_protection: Proteccion
    protected: bool
    review_required: bool
    hard_excluded: bool
    protection_reasons: tuple[PolicyProtectionReason, ...]
    decision_ids: tuple[str, ...] = field(repr=False)
    automatic_evidence: tuple[ClassificationEvidence, ...] = field(repr=False)
    effective_evidence: tuple[EffectiveEvidence, ...] = field(repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)
    version: int = POLICY_RESULT_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.effective_flow_id, "effective_flow_id", _EFFECTIVE_FLOW_ID)
        _versioned_id(self.effective_source_id, "effective_source_id", _EFFECTIVE_SOURCE_ID)
        if not isinstance(self.selector, EffectiveFlowSelector):
            raise TypeError("selector must be an EffectiveFlowSelector")
        _versioned_id(self.automatic_flow_id, "automatic_flow_id", _FLOW_ID)
        _normalized_text(self.automatic_display_name, "automatic_display_name")
        _normalized_text(self.effective_display_name, "effective_display_name")
        _string_tuple(self.message_ids, "message_ids")
        if not isinstance(self.automatic_intention, Intencion) or not isinstance(
            self.effective_intention, Intencion
        ):
            raise TypeError("intention values must be Intencion values")
        if not isinstance(self.subscription, Suscripcion):
            raise TypeError("subscription must be a Suscripcion")
        _validate_confidence_projection(
            self.automatic_confidence, self.effective_confidence
        )
        _validate_protection_projection(
            automatic_protection=self.automatic_protection,
            effective_protection=self.effective_protection,
            protected=self.protected,
            review_required=self.review_required,
            hard_excluded=self.hard_excluded,
            protection_reasons=self.protection_reasons,
            decision_ids=self.decision_ids,
        )
        _evidence_tuple(self.automatic_evidence, "automatic_evidence")
        if any(not isinstance(item, ClassificationEvidence) for item in self.automatic_evidence):
            raise TypeError("automatic_evidence must contain ClassificationEvidence values")
        _evidence_tuple(self.effective_evidence, "effective_evidence")
        if not set(self.automatic_evidence).issubset(self.effective_evidence):
            raise ValueError("effective evidence must preserve automatic evidence")
        _string_tuple(
            self.structural_decision_ids,
            "structural_decision_ids",
            allow_empty=True,
        )
        _exact_version(self.version, POLICY_RESULT_VERSION)

    def __repr__(self) -> str:
        return (
            f"EffectiveFlow(effective_flow_id={self.effective_flow_id!r}, "
            f"effective_source_id={self.effective_source_id!r}, "
            f"automatic_flow_id={self.automatic_flow_id!r}, "
            f"message_count={len(self.message_ids)}, protected={self.protected}, "
            f"review_required={self.review_required}, "
            f"decision_count={len(self.decision_ids)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyApplicationResult:
    account_key: str = field(repr=False)
    messages: tuple[EffectiveMessage, ...]
    sources: tuple[EffectiveSource, ...]
    flows: tuple[EffectiveFlow, ...]
    bindings: tuple[PolicyBinding, ...]
    version: int = POLICY_RESULT_VERSION

    def __post_init__(self) -> None:
        _account_key(self.account_key)
        if not isinstance(self.messages, tuple) or any(
            not isinstance(item, EffectiveMessage) for item in self.messages
        ):
            raise TypeError("messages must contain EffectiveMessage values")
        if not isinstance(self.sources, tuple) or any(
            not isinstance(item, EffectiveSource) for item in self.sources
        ):
            raise TypeError("sources must contain EffectiveSource values")
        if not isinstance(self.flows, tuple) or any(
            not isinstance(item, EffectiveFlow) for item in self.flows
        ):
            raise TypeError("flows must contain EffectiveFlow values")
        if not isinstance(self.bindings, tuple) or any(
            not isinstance(item, PolicyBinding) for item in self.bindings
        ):
            raise TypeError("bindings must contain PolicyBinding values")
        if any(source.selector.account_key != self.account_key for source in self.sources):
            raise ValueError("source selector references another account")
        if any(flow.selector.account_key != self.account_key for flow in self.flows):
            raise ValueError("flow selector references another account")
        if any(
            (selector_account := policy_selector_account(selector)) is not None
            and selector_account != self.account_key
            for binding in self.bindings
            for selector in binding.selectors
        ):
            raise ValueError("binding selector references another account")
        _exact_version(self.version, POLICY_RESULT_VERSION)
        message_ids = tuple(item.provider_message_id for item in self.messages)
        source_ids = tuple(item.effective_source_id for item in self.sources)
        flow_ids = tuple(item.effective_flow_id for item in self.flows)
        binding_ids = tuple(item.decision_id for item in self.bindings)
        for values, field_name in (
            (message_ids, "messages"),
            (source_ids, "sources"),
            (flow_ids, "flows"),
            (binding_ids, "bindings"),
        ):
            if len(set(values)) != len(values) or values != tuple(sorted(values)):
                raise ValueError(f"{field_name} must be unique and ordered")
        known_sources = set(source_ids)
        known_flows = set(flow_ids)
        if any(item.effective_source_id not in known_sources for item in self.messages):
            raise ValueError("every message must reference a known effective source")
        if any(item.effective_flow_id not in known_flows for item in self.messages):
            raise ValueError("every message must reference a known effective flow")
        if any(item.effective_source_id not in known_sources for item in self.flows):
            raise ValueError("every flow must reference a known effective source")
        flow_sources = {item.effective_flow_id: item.effective_source_id for item in self.flows}
        if any(
            flow_sources[item.effective_flow_id] != item.effective_source_id
            for item in self.messages
        ):
            raise ValueError("message source and flow relationships must agree")
        for flow in self.flows:
            expected_messages = tuple(
                item.provider_message_id
                for item in self.messages
                if item.effective_flow_id == flow.effective_flow_id
            )
            if flow.message_ids != expected_messages:
                raise ValueError("flow message relationships must be complete")
        for source in self.sources:
            expected_messages = tuple(
                item.provider_message_id
                for item in self.messages
                if item.effective_source_id == source.effective_source_id
            )
            expected_flows = tuple(
                item.effective_flow_id
                for item in self.flows
                if item.effective_source_id == source.effective_source_id
            )
            if source.message_ids != expected_messages:
                raise ValueError("source message relationships must be complete")
            if source.flow_ids != expected_flows:
                raise ValueError("source flow relationships must be complete")

    def __repr__(self) -> str:
        return (
            "PolicyApplicationResult(account_key=<redacted>, "
            f"message_count={len(self.messages)}, source_count={len(self.sources)}, "
            f"flow_count={len(self.flows)}, binding_count={len(self.bindings)}, "
            f"version={self.version})"
        )
