from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Literal, TypeAlias

from mailmap.classification_model import EvidenceOrigin, EvidenceStrength
from mailmap.index_model import SyncMode, SyncState
from mailmap.model import Confianza, Intencion, Proteccion, Rubro, Suscripcion
from mailmap.policy_model import (
    PolicyBindingStatus,
    PolicyEvidenceCode,
    PolicyProtectionReason,
)

MAP_CONTRACT_VERSION = 1
MAP_DATA_MODE: Final[Literal["synthetic"]] = "synthetic"

_MAP_REVISION = re.compile(r"^map-v1-[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^effective-source-v1-[0-9a-f]{24}$")
_FLOW_ID = re.compile(r"^effective-flow-v1-[0-9a-f]{24}$")
_MESSAGE_ID = re.compile(r"^message-v1-[0-9a-f]{64}$")

_CONFIDENCE_RANK = {
    Confianza.ALTA: 0,
    Confianza.MEDIA: 1,
    Confianza.BAJA: 2,
    Confianza.CONTRADICTORIA: 3,
}
_PROTECTION_RANK = {
    Proteccion.ORDINARIA: 0,
    Proteccion.REVISION: 1,
    Proteccion.USUARIO: 2,
    Proteccion.DOCUMENTAL: 3,
    Proteccion.CRITICA: 4,
}


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be normalized and non-empty")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


def _optional_utc(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    return _utc_datetime(value, field_name)


def _non_negative(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _canonical_strings(
    value: tuple[str, ...],
    field_name: str,
    *,
    key: Callable[[str], tuple[str, str]] | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        _non_empty(item, f"{field_name} item")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must be unique")
    expected = tuple(sorted(value, key=key)) if key is not None else tuple(sorted(value))
    if value != expected:
        raise ValueError(f"{field_name} must be ordered")
    return value


class MapCompositionErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    MAP_UNAVAILABLE = "map_unavailable"
    COMPOSITION_MISMATCH = "composition_mismatch"


class MapCompositionError(RuntimeError):
    __slots__ = ()
    _RUNTIME_ATTRIBUTES = frozenset(
        {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
    )

    def __init__(self, code: MapCompositionErrorCode) -> None:
        if not isinstance(code, MapCompositionErrorCode):
            raise TypeError("code must be a MapCompositionErrorCode")
        super().__init__(code.value)

    @property
    def code(self) -> MapCompositionErrorCode:
        return MapCompositionErrorCode(self.args[0])

    def __getattribute__(self, name: str) -> object:
        if name == "__dict__":
            raise AttributeError("MapCompositionError is closed")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__setattr__(self, name, value)
            return
        raise AttributeError("MapCompositionError is immutable")

    def __delattr__(self, name: str) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__delattr__(self, name)
            return
        raise AttributeError("MapCompositionError is immutable")

    def __repr__(self) -> str:
        return f"MapCompositionError(code={self.code.value!r})"


@dataclass(frozen=True, slots=True, kw_only=True)
class MapClassificationEvidence:
    kind: Literal["classification"] = "classification"
    code: str
    label: str = field(repr=False)
    detail: str = field(repr=False)
    strength: EvidenceStrength
    origin: EvidenceOrigin

    def __post_init__(self) -> None:
        if self.kind != "classification":
            raise ValueError("kind must be classification")
        _non_empty(self.code, "code")
        _non_empty(self.label, "label")
        _non_empty(self.detail, "detail")
        if not isinstance(self.strength, EvidenceStrength):
            raise TypeError("strength must be an EvidenceStrength")
        if not isinstance(self.origin, EvidenceOrigin):
            raise TypeError("origin must be an EvidenceOrigin")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPolicyEvidence:
    kind: Literal["policy"] = "policy"
    code: PolicyEvidenceCode
    decision_id: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.kind != "policy":
            raise ValueError("kind must be policy")
        if not isinstance(self.code, PolicyEvidenceCode):
            raise TypeError("code must be a PolicyEvidenceCode")
        _non_empty(self.decision_id, "decision_id")


MapEvidence: TypeAlias = MapClassificationEvidence | MapPolicyEvidence


def _evidence_key(value: MapEvidence) -> tuple[str, ...]:
    if isinstance(value, MapClassificationEvidence):
        return (
            "classification",
            value.code,
            value.strength.value,
            value.origin.value,
            value.label,
            value.detail,
        )
    return ("policy", value.code.value, value.decision_id)


def _evidence_tuple(value: tuple[MapEvidence, ...], field_name: str) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, (MapClassificationEvidence, MapPolicyEvidence))
        for item in value
    ):
        raise TypeError(f"{field_name} must contain closed evidence values")
    keys = tuple(_evidence_key(item) for item in value)
    if len(keys) != len(set(keys)) or keys != tuple(sorted(keys)):
        raise ValueError(f"{field_name} must be canonical, unique and ordered")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapProtection:
    automatic: Proteccion
    effective: Proteccion
    protected: bool
    review_required: bool
    hard_excluded: bool
    reasons: tuple[PolicyProtectionReason, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.automatic, Proteccion) or not isinstance(
            self.effective, Proteccion
        ):
            raise TypeError("protection values must be Proteccion values")
        if _PROTECTION_RANK[self.effective] < _PROTECTION_RANK[self.automatic]:
            raise ValueError("effective protection must not weaken automatic protection")
        for field_name in ("protected", "review_required", "hard_excluded"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean")
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(item, PolicyProtectionReason) for item in self.reasons
        ):
            raise TypeError("reasons must contain PolicyProtectionReason values")
        values = tuple(item.value for item in self.reasons)
        if values != tuple(sorted(set(values))):
            raise ValueError("reasons must be canonical, unique and ordered")
        if self.protected != bool(self.reasons):
            raise ValueError("protected must agree with reasons")
        if self.hard_excluded and not self.protected:
            raise ValueError("hard exclusion must be protected")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapMonthlyVolume:
    month: str
    message_count: int
    total_bytes: int

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", self.month) is None:
            raise ValueError("month must use YYYY-MM")
        _non_negative(self.message_count, "message_count")
        _non_negative(self.total_bytes, "total_bytes")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSync:
    state: SyncState
    mode: SyncMode | None
    processed_count: int
    started_at: datetime | None
    updated_at: datetime | None
    error_code: str | None
    partial: bool

    def __post_init__(self) -> None:
        if not isinstance(self.state, SyncState):
            raise TypeError("state must be a SyncState")
        if self.mode is not None and not isinstance(self.mode, SyncMode):
            raise TypeError("mode must be a SyncMode or None")
        _non_negative(self.processed_count, "processed_count")
        object.__setattr__(self, "started_at", _optional_utc(self.started_at, "started_at"))
        object.__setattr__(self, "updated_at", _optional_utc(self.updated_at, "updated_at"))
        if self.error_code is not None:
            _non_empty(self.error_code, "error_code")
        if not isinstance(self.partial, bool):
            raise TypeError("partial must be a boolean")
        if self.partial != (self.state is not SyncState.COMPLETED):
            raise ValueError("partial must reflect checkpoint completion")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapFlow:
    id: str
    source_id: str
    automatic_flow_id: str
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    message_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime
    last_seen: datetime
    protection: MapProtection
    automatic_evidence: tuple[MapClassificationEvidence, ...] = field(repr=False)
    effective_evidence: tuple[MapEvidence, ...] = field(repr=False)
    decision_ids: tuple[str, ...] = field(repr=False)
    structural_decision_ids: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if _FLOW_ID.fullmatch(self.id) is None:
            raise ValueError("id must be an effective flow identifier")
        if _SOURCE_ID.fullmatch(self.source_id) is None:
            raise ValueError("source_id must be an effective source identifier")
        _non_empty(self.automatic_flow_id, "automatic_flow_id")
        _non_empty(self.automatic_display_name, "automatic_display_name")
        _non_empty(self.effective_display_name, "effective_display_name")
        if not isinstance(self.automatic_intention, Intencion) or not isinstance(
            self.effective_intention, Intencion
        ):
            raise TypeError("intentions must be Intencion values")
        if not isinstance(self.subscription, Suscripcion):
            raise TypeError("subscription must be a Suscripcion")
        if not isinstance(self.automatic_confidence, Confianza) or not isinstance(
            self.effective_confidence, Confianza
        ):
            raise TypeError("confidences must be Confianza values")
        if _CONFIDENCE_RANK[self.effective_confidence] < _CONFIDENCE_RANK[
            self.automatic_confidence
        ]:
            raise ValueError("effective confidence must not improve automatic confidence")
        for name in (
            "message_count",
            "protected_message_count",
            "review_required_message_count",
            "hard_excluded_message_count",
            "total_bytes",
        ):
            _non_negative(getattr(self, name), name)
        if self.message_count == 0:
            raise ValueError("a projected flow must contain messages")
        if any(
            getattr(self, name) > self.message_count
            for name in (
                "protected_message_count",
                "review_required_message_count",
                "hard_excluded_message_count",
            )
        ):
            raise ValueError("flow counters cannot exceed message_count")
        object.__setattr__(self, "first_seen", _utc_datetime(self.first_seen, "first_seen"))
        object.__setattr__(self, "last_seen", _utc_datetime(self.last_seen, "last_seen"))
        if self.first_seen > self.last_seen:
            raise ValueError("first_seen must not follow last_seen")
        if not isinstance(self.protection, MapProtection):
            raise TypeError("protection must be a MapProtection")
        _evidence_tuple(self.automatic_evidence, "automatic_evidence")
        if any(not isinstance(item, MapClassificationEvidence) for item in self.automatic_evidence):
            raise TypeError("automatic_evidence must contain classification evidence")
        _evidence_tuple(self.effective_evidence, "effective_evidence")
        if not set(self.automatic_evidence).issubset(self.effective_evidence):
            raise ValueError("effective evidence must preserve automatic evidence")
        _canonical_strings(self.decision_ids, "decision_ids")
        _canonical_strings(self.structural_decision_ids, "structural_decision_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSource:
    id: str
    automatic_source_ids: tuple[str, ...]
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_confidence: Confianza
    effective_confidence: Confianza
    message_count: int
    flow_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime
    last_seen: datetime
    senders: tuple[str, ...] = field(repr=False)
    domains: tuple[str, ...] = field(repr=False)
    monthly_volume: tuple[MapMonthlyVolume, ...]
    protection: MapProtection
    automatic_evidence: tuple[MapClassificationEvidence, ...] = field(repr=False)
    effective_evidence: tuple[MapEvidence, ...] = field(repr=False)
    decision_ids: tuple[str, ...] = field(repr=False)
    structural_decision_ids: tuple[str, ...] = field(repr=False)
    flows: tuple[MapFlow, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if _SOURCE_ID.fullmatch(self.id) is None:
            raise ValueError("id must be an effective source identifier")
        _canonical_strings(self.automatic_source_ids, "automatic_source_ids")
        _non_empty(self.automatic_display_name, "automatic_display_name")
        _non_empty(self.effective_display_name, "effective_display_name")
        if not isinstance(self.automatic_rubro, Rubro) or not isinstance(
            self.effective_rubro, Rubro
        ):
            raise TypeError("rubros must be Rubro values")
        if not isinstance(self.automatic_confidence, Confianza) or not isinstance(
            self.effective_confidence, Confianza
        ):
            raise TypeError("confidences must be Confianza values")
        if _CONFIDENCE_RANK[self.effective_confidence] < _CONFIDENCE_RANK[
            self.automatic_confidence
        ]:
            raise ValueError("effective confidence must not improve automatic confidence")
        for name in (
            "message_count",
            "flow_count",
            "protected_message_count",
            "review_required_message_count",
            "hard_excluded_message_count",
            "total_bytes",
        ):
            _non_negative(getattr(self, name), name)
        if self.message_count == 0:
            raise ValueError("a projected source must contain messages")
        if any(
            getattr(self, name) > self.message_count
            for name in (
                "protected_message_count",
                "review_required_message_count",
                "hard_excluded_message_count",
            )
        ):
            raise ValueError("source counters cannot exceed message_count")
        object.__setattr__(self, "first_seen", _utc_datetime(self.first_seen, "first_seen"))
        object.__setattr__(self, "last_seen", _utc_datetime(self.last_seen, "last_seen"))
        if self.first_seen > self.last_seen:
            raise ValueError("first_seen must not follow last_seen")
        _canonical_strings(
            self.senders,
            "senders",
            key=lambda item: (item.casefold(), item),
        )
        _canonical_strings(self.domains, "domains")
        if not isinstance(self.monthly_volume, tuple) or any(
            not isinstance(item, MapMonthlyVolume) for item in self.monthly_volume
        ):
            raise TypeError("monthly_volume must contain MapMonthlyVolume values")
        months = tuple(item.month for item in self.monthly_volume)
        if months != tuple(sorted(set(months))):
            raise ValueError("monthly_volume must be canonical")
        if not isinstance(self.protection, MapProtection):
            raise TypeError("protection must be a MapProtection")
        _evidence_tuple(self.automatic_evidence, "automatic_evidence")
        if any(not isinstance(item, MapClassificationEvidence) for item in self.automatic_evidence):
            raise TypeError("automatic_evidence must contain classification evidence")
        _evidence_tuple(self.effective_evidence, "effective_evidence")
        if not set(self.automatic_evidence).issubset(self.effective_evidence):
            raise ValueError("effective evidence must preserve automatic evidence")
        _canonical_strings(self.decision_ids, "decision_ids")
        _canonical_strings(self.structural_decision_ids, "structural_decision_ids")
        if not isinstance(self.flows, tuple) or any(
            not isinstance(item, MapFlow) for item in self.flows
        ):
            raise TypeError("flows must contain MapFlow values")
        if self.flow_count != len(self.flows):
            raise ValueError("flow_count must match flows")
        if any(item.source_id != self.id for item in self.flows):
            raise ValueError("every flow must belong to its source")
        flow_order = tuple(
            (-item.message_count, item.effective_display_name.casefold(), item.id)
            for item in self.flows
        )
        if flow_order != tuple(sorted(flow_order)):
            raise ValueError("flows must be deterministically ordered")
        if sum(item.message_count for item in self.flows) != self.message_count:
            raise ValueError("flow message counts must cover the source")
        if sum(item.total_bytes for item in self.flows) != self.total_bytes:
            raise ValueError("flow bytes must cover the source")
        if sum(item.protected_message_count for item in self.flows) != (
            self.protected_message_count
        ):
            raise ValueError("flow protected counts must cover the source")
        if sum(item.review_required_message_count for item in self.flows) != (
            self.review_required_message_count
        ):
            raise ValueError("flow review counts must cover the source")
        if sum(item.hard_excluded_message_count for item in self.flows) != (
            self.hard_excluded_message_count
        ):
            raise ValueError("flow exclusion counts must cover the source")
        if sum(item.message_count for item in self.monthly_volume) != self.message_count:
            raise ValueError("monthly volume must cover source messages")
        if sum(item.total_bytes for item in self.monthly_volume) != self.total_bytes:
            raise ValueError("monthly volume must cover source bytes")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSummary:
    message_count: int
    source_count: int
    flow_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime | None
    last_seen: datetime | None

    def __post_init__(self) -> None:
        for name in (
            "message_count",
            "source_count",
            "flow_count",
            "protected_message_count",
            "review_required_message_count",
            "hard_excluded_message_count",
            "total_bytes",
        ):
            _non_negative(getattr(self, name), name)
        if any(
            getattr(self, name) > self.message_count
            for name in (
                "protected_message_count",
                "review_required_message_count",
                "hard_excluded_message_count",
            )
        ):
            raise ValueError("summary counters cannot exceed message_count")
        first_seen = _optional_utc(self.first_seen, "first_seen")
        last_seen = _optional_utc(self.last_seen, "last_seen")
        object.__setattr__(self, "first_seen", first_seen)
        object.__setattr__(self, "last_seen", last_seen)
        if (first_seen is None) != (last_seen is None):
            raise ValueError("first_seen and last_seen must be absent together")
        if first_seen is not None and last_seen is not None and first_seen > last_seen:
            raise ValueError("first_seen must not follow last_seen")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPolicyReviewBinding:
    decision_id: str = field(repr=False)
    status: PolicyBindingStatus
    current_effective_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _non_empty(self.decision_id, "decision_id")
        if not isinstance(self.status, PolicyBindingStatus):
            raise TypeError("status must be a PolicyBindingStatus")
        if self.status in {PolicyBindingStatus.EXACT, PolicyBindingStatus.REBOUND}:
            raise ValueError("applicable bindings do not belong in policy review")
        _canonical_strings(self.current_effective_ids, "current_effective_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPolicyReview:
    total: int
    bindings: tuple[MapPolicyReviewBinding, ...]

    def __post_init__(self) -> None:
        _non_negative(self.total, "total")
        if not isinstance(self.bindings, tuple) or any(
            not isinstance(item, MapPolicyReviewBinding) for item in self.bindings
        ):
            raise TypeError("bindings must contain MapPolicyReviewBinding values")
        if self.total != len(self.bindings):
            raise ValueError("total must match bindings")
        ids = tuple(item.decision_id for item in self.bindings)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("bindings must be unique and ordered")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapObservedTarget:
    kind: Literal["source", "flow", "message", "sender", "label"]
    observed_effective_id: str | None
    observed_source_ids: tuple[str, ...]
    observed_flow_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in {"source", "flow", "message", "sender", "label"}:
            raise ValueError("kind must be a public target kind")
        if self.observed_effective_id is not None:
            _non_empty(self.observed_effective_id, "observed_effective_id")
        _canonical_strings(self.observed_source_ids, "observed_source_ids")
        _canonical_strings(self.observed_flow_ids, "observed_flow_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPartitionGroupSummary:
    group_index: int
    anchor_count: int
    anchor_kinds: tuple[Literal["flow", "message", "sender"], ...]
    observed_source_ids: tuple[str, ...]
    observed_flow_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _non_negative(self.group_index, "group_index")
        _non_negative(self.anchor_count, "anchor_count")
        if not isinstance(self.anchor_kinds, tuple) or any(
            item not in {"flow", "message", "sender"} for item in self.anchor_kinds
        ):
            raise TypeError("anchor_kinds must contain public partition kinds")
        if self.anchor_kinds != tuple(sorted(set(self.anchor_kinds))):
            raise ValueError("anchor_kinds must be canonical")
        _canonical_strings(self.observed_source_ids, "observed_source_ids")
        _canonical_strings(self.observed_flow_ids, "observed_flow_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class _MapDecisionBase:
    command_id: str = field(repr=False)
    revision: int
    occurred_at: datetime = field(repr=False)
    active: bool
    undoable: bool
    supersedes_decision_ids: tuple[str, ...] = field(repr=False)
    binding_status: PolicyBindingStatus | None
    current_target_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _non_empty(self.command_id, "command_id")
        if self.revision < 1:
            raise ValueError("revision must be positive")
        object.__setattr__(self, "occurred_at", _utc_datetime(self.occurred_at, "occurred_at"))
        if not isinstance(self.active, bool) or not isinstance(self.undoable, bool):
            raise TypeError("active and undoable must be booleans")
        if self.undoable and not self.active:
            raise ValueError("only an active decision may be undoable")
        _canonical_strings(self.supersedes_decision_ids, "supersedes_decision_ids")
        if self.binding_status is not None and not isinstance(
            self.binding_status, PolicyBindingStatus
        ):
            raise TypeError("binding_status must be a PolicyBindingStatus or None")
        _canonical_strings(self.current_target_ids, "current_target_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSetSourceDisplayNameDecision(_MapDecisionBase):
    type: Literal["setSourceDisplayName"] = "setSourceDisplayName"
    decision_id: str = field(repr=False)
    source_id: str
    display_name: str = field(repr=False)

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "setSourceDisplayName":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _non_empty(self.source_id, "source_id")
        _non_empty(self.display_name, "display_name")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSetSourceRubroDecision(_MapDecisionBase):
    type: Literal["setSourceRubro"] = "setSourceRubro"
    decision_id: str = field(repr=False)
    source_id: str
    rubro: Rubro

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "setSourceRubro":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _non_empty(self.source_id, "source_id")
        if not isinstance(self.rubro, Rubro):
            raise TypeError("rubro must be a Rubro")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSetFlowDisplayNameDecision(_MapDecisionBase):
    type: Literal["setFlowDisplayName"] = "setFlowDisplayName"
    decision_id: str = field(repr=False)
    flow_id: str
    display_name: str = field(repr=False)

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "setFlowDisplayName":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _non_empty(self.flow_id, "flow_id")
        _non_empty(self.display_name, "display_name")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSetFlowIntentionDecision(_MapDecisionBase):
    type: Literal["setFlowIntention"] = "setFlowIntention"
    decision_id: str = field(repr=False)
    flow_id: str
    intention: Intencion

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "setFlowIntention":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _non_empty(self.flow_id, "flow_id")
        if not isinstance(self.intention, Intencion):
            raise TypeError("intention must be an Intencion")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapMergeSourcesDecision(_MapDecisionBase):
    type: Literal["mergeSources"] = "mergeSources"
    decision_id: str = field(repr=False)
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "mergeSources":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _canonical_strings(self.source_ids, "source_ids")
        if len(self.source_ids) < 2:
            raise ValueError("merge history requires at least two source IDs")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPartitionSourceDecision(_MapDecisionBase):
    type: Literal["partitionSource"] = "partitionSource"
    decision_id: str = field(repr=False)
    source_id: str
    group_count: int
    groups: tuple[MapPartitionGroupSummary, ...]

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "partitionSource":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        _non_empty(self.source_id, "source_id")
        _non_negative(self.group_count, "group_count")
        if not isinstance(self.groups, tuple) or any(
            not isinstance(item, MapPartitionGroupSummary) for item in self.groups
        ):
            raise TypeError("groups must contain MapPartitionGroupSummary values")
        if self.group_count != len(self.groups):
            raise ValueError("group_count must match groups")
        if tuple(item.group_index for item in self.groups) != tuple(range(len(self.groups))):
            raise ValueError("groups must be contiguous and ordered")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapProtectTargetDecision(_MapDecisionBase):
    type: Literal["protectTarget"] = "protectTarget"
    decision_id: str = field(repr=False)
    target: MapObservedTarget = field(repr=False)

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "protectTarget":
            raise ValueError("invalid decision type")
        _non_empty(self.decision_id, "decision_id")
        if not isinstance(self.target, MapObservedTarget):
            raise TypeError("target must be a MapObservedTarget")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapUndoPolicyDecision(_MapDecisionBase):
    type: Literal["undoPolicy"] = "undoPolicy"
    decision_id: None = None
    target_decision_id: str = field(repr=False)

    def __post_init__(self) -> None:
        _MapDecisionBase.__post_init__(self)
        if self.type != "undoPolicy" or self.decision_id is not None:
            raise ValueError("invalid undo projection")
        if self.active or self.undoable or self.binding_status is not None:
            raise ValueError("undo events are never active, undoable or bound")
        if self.supersedes_decision_ids or self.current_target_ids:
            raise ValueError("undo events have no correction targets")
        _non_empty(self.target_decision_id, "target_decision_id")


MapDecision: TypeAlias = (
    MapSetSourceDisplayNameDecision
    | MapSetSourceRubroDecision
    | MapSetFlowDisplayNameDecision
    | MapSetFlowIntentionDecision
    | MapMergeSourcesDecision
    | MapPartitionSourceDecision
    | MapProtectTargetDecision
    | MapUndoPolicyDecision
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MapDecisionHistory:
    contract_version: int
    data_mode: Literal["synthetic"]
    policy_revision: int
    events: tuple[MapDecision, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if self.contract_version != MAP_CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {MAP_CONTRACT_VERSION}")
        if self.data_mode != MAP_DATA_MODE:
            raise ValueError("data_mode must be synthetic")
        _non_negative(self.policy_revision, "policy_revision")
        if not isinstance(self.events, tuple) or any(
            not isinstance(
                item,
                (
                    MapSetSourceDisplayNameDecision,
                    MapSetSourceRubroDecision,
                    MapSetFlowDisplayNameDecision,
                    MapSetFlowIntentionDecision,
                    MapMergeSourcesDecision,
                    MapPartitionSourceDecision,
                    MapProtectTargetDecision,
                    MapUndoPolicyDecision,
                ),
            )
            for item in self.events
        ):
            raise TypeError("events must contain closed MapDecision values")
        if tuple(item.revision for item in self.events) != tuple(
            range(1, len(self.events) + 1)
        ):
            raise ValueError("events must be ordered by contiguous revision")
        if self.policy_revision != len(self.events):
            raise ValueError("policy_revision must match the last event")


@dataclass(frozen=True, slots=True, kw_only=True)
class MapMessageSample:
    id: str
    received_at: datetime
    sender_name: str | None = field(repr=False)
    sender_address: str | None = field(repr=False)
    subject: str | None = field(repr=False)
    label_ids: tuple[str, ...] = field(repr=False)
    category: str | None
    size_estimate_bytes: int
    source_id: str
    flow_id: str
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    protection: MapProtection

    def __post_init__(self) -> None:
        if _MESSAGE_ID.fullmatch(self.id) is None:
            raise ValueError("id must be a local message identifier")
        object.__setattr__(self, "received_at", _utc_datetime(self.received_at, "received_at"))
        for name in ("sender_name", "sender_address", "subject", "category"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string or None")
        _canonical_strings(self.label_ids, "label_ids")
        _non_negative(self.size_estimate_bytes, "size_estimate_bytes")
        if _SOURCE_ID.fullmatch(self.source_id) is None:
            raise ValueError("source_id must be an effective source identifier")
        if _FLOW_ID.fullmatch(self.flow_id) is None:
            raise ValueError("flow_id must be an effective flow identifier")
        if not isinstance(self.automatic_rubro, Rubro) or not isinstance(
            self.effective_rubro, Rubro
        ):
            raise TypeError("rubros must be Rubro values")
        if not isinstance(self.automatic_intention, Intencion) or not isinstance(
            self.effective_intention, Intencion
        ):
            raise TypeError("intentions must be Intencion values")
        if not isinstance(self.subscription, Suscripcion):
            raise TypeError("subscription must be a Suscripcion")
        if not isinstance(self.automatic_confidence, Confianza) or not isinstance(
            self.effective_confidence, Confianza
        ):
            raise TypeError("confidences must be Confianza values")
        if _CONFIDENCE_RANK[self.effective_confidence] < _CONFIDENCE_RANK[
            self.automatic_confidence
        ]:
            raise ValueError("effective confidence must not improve automatic confidence")
        if not isinstance(self.protection, MapProtection):
            raise TypeError("protection must be a MapProtection")

    def __repr__(self) -> str:
        return (
            f"MapMessageSample(id={self.id!r}, received_at={self.received_at!r}, "
            "metadata=<redacted>, "
            f"source_id={self.source_id!r}, flow_id={self.flow_id!r}, "
            f"protected={self.protection.protected})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MapSourceDetail:
    source: MapSource = field(repr=False)
    recent_messages: tuple[MapMessageSample, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, MapSource):
            raise TypeError("source must be a MapSource")
        if not isinstance(self.recent_messages, tuple) or any(
            not isinstance(item, MapMessageSample) for item in self.recent_messages
        ):
            raise TypeError("recent_messages must contain MapMessageSample values")
        if len(self.recent_messages) > 5:
            raise ValueError("recent_messages cannot exceed five entries")
        if any(item.source_id != self.source.id for item in self.recent_messages):
            raise ValueError("recent messages must belong to the source")
        order = tuple((-item.received_at.timestamp(), item.id) for item in self.recent_messages)
        if order != tuple(sorted(order)):
            raise ValueError("recent_messages must be deterministically ordered")

    def __repr__(self) -> str:
        return (
            f"MapSourceDetail(source_id={self.source.id!r}, "
            f"recent_message_count={len(self.recent_messages)})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MapProjection:
    contract_version: int
    data_mode: Literal["synthetic"]
    map_revision: str
    policy_revision: int
    sync: MapSync
    summary: MapSummary
    policy_review: MapPolicyReview
    sources: tuple[MapSource, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if self.contract_version != MAP_CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {MAP_CONTRACT_VERSION}")
        if self.data_mode != MAP_DATA_MODE:
            raise ValueError("data_mode must be synthetic")
        if _MAP_REVISION.fullmatch(self.map_revision) is None:
            raise ValueError("map_revision must be a versioned opaque identifier")
        _non_negative(self.policy_revision, "policy_revision")
        if not isinstance(self.sync, MapSync):
            raise TypeError("sync must be a MapSync")
        if not isinstance(self.summary, MapSummary):
            raise TypeError("summary must be a MapSummary")
        if not isinstance(self.policy_review, MapPolicyReview):
            raise TypeError("policy_review must be a MapPolicyReview")
        if not isinstance(self.sources, tuple) or any(
            not isinstance(item, MapSource) for item in self.sources
        ):
            raise TypeError("sources must contain MapSource values")
        ids = tuple(item.id for item in self.sources)
        if len(ids) != len(set(ids)):
            raise ValueError("sources must be unique")
        if self.summary.source_count != len(self.sources):
            raise ValueError("summary source_count must match sources")
        source_order = tuple(
            (-item.message_count, item.effective_display_name.casefold(), item.id)
            for item in self.sources
        )
        if source_order != tuple(sorted(source_order)):
            raise ValueError("sources must be deterministically ordered")
        if sum(item.message_count for item in self.sources) != self.summary.message_count:
            raise ValueError("source message counts must match summary")
        if sum(item.flow_count for item in self.sources) != self.summary.flow_count:
            raise ValueError("source flow counts must match summary")
        if sum(item.total_bytes for item in self.sources) != self.summary.total_bytes:
            raise ValueError("source bytes must match summary")
        if sum(item.protected_message_count for item in self.sources) != (
            self.summary.protected_message_count
        ):
            raise ValueError("source protected counts must match summary")
        if sum(item.review_required_message_count for item in self.sources) != (
            self.summary.review_required_message_count
        ):
            raise ValueError("source review counts must match summary")
        if sum(item.hard_excluded_message_count for item in self.sources) != (
            self.summary.hard_excluded_message_count
        ):
            raise ValueError("source exclusion counts must match summary")

    def __repr__(self) -> str:
        return (
            f"MapProjection(contract_version={self.contract_version}, "
            f"data_mode={self.data_mode!r}, map_revision={self.map_revision!r}, "
            f"policy_revision={self.policy_revision}, "
            f"sync_state={self.sync.state.value!r}, "
            f"message_count={self.summary.message_count}, "
            f"source_count={self.summary.source_count}, "
            f"policy_review_count={self.policy_review.total})"
        )
