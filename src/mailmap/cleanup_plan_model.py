from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from mailmap.index_model import validate_account_key, validate_opaque_identifier

CLEANUP_PLAN_CONTRACT_VERSION = 1
CLEANUP_PLAN_MODEL_VERSION = 1
CLEANUP_PLAN_VALIDITY_SECONDS = 86_400
CLEANUP_PLAN_TIME_ZONE = "America/Argentina/Cordoba"

MAX_TARGETS = 100
MAX_EXCLUDED_LABELS = 100
MAX_CONSIDERED_MESSAGES = 100_000
MAX_KEEP_LATEST_PER_FLOW = 10_000
MAX_OLDER_THAN_DAYS = 36_500
MAX_MESSAGE_SIZE_ESTIMATE_BYTES = 2_147_483_647
MAX_AGGREGATE_SIZE_ESTIMATE_BYTES = 214_748_364_700_000
MAX_VISIBLE_METADATA_BYTES = 16_384
MAX_INCLUDED_SAMPLES = 5
MAX_EXCLUDED_SAMPLES = 5

_MAP_REVISION = re.compile(r"^map-v1-[0-9a-f]{64}$")
_INPUT_REVISION = re.compile(r"^input-v1-[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^effective-source-v1-[0-9a-f]{24}$")
_FLOW_ID = re.compile(r"^effective-flow-v1-[0-9a-f]{24}$")
_SENDER_ID = re.compile(r"^sender-v1-[0-9a-f]{64}$")
_LABEL_ID = re.compile(r"^label-v1-[0-9a-f]{64}$")
_MESSAGE_ID = re.compile(r"^message-v1-[0-9a-f]{64}$")
_PLAN_ID = re.compile(
    r"^cleanup-plan-v1-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


def _exact_version(value: int, expected: int = CLEANUP_PLAN_MODEL_VERSION) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"version must be {expected}")
    return value


def _integer(value: int, field_name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise ValueError(f"{field_name} must be at least {minimum}")
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
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


def _civil_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise TypeError(f"{field_name} must be a date")
    return value


def _uuid_v4(value: str, field_name: str) -> str:
    validate_opaque_identifier(value, field_name)
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        raise ValueError(f"{field_name} must be a UUID v4") from None
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError(f"{field_name} must be a canonical UUID v4")
    return value


def _plan_id(value: str) -> str:
    validate_opaque_identifier(value, "plan_id")
    if _PLAN_ID.fullmatch(value) is None:
        raise ValueError("plan_id must be a versioned UUID v4 identifier")
    _uuid_v4(value.removeprefix("cleanup-plan-v1-"), "plan_id suffix")
    return value


def _versioned_id(value: str, field_name: str, pattern: re.Pattern[str]) -> str:
    validate_opaque_identifier(value, field_name)
    if pattern.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a versioned opaque identifier")
    return value


def _visible_text(value: str, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value.encode("utf-8")) > MAX_VISIBLE_METADATA_BYTES:
        raise ValueError(f"{field_name} exceeds the metadata limit")
    return value


def _optional_visible_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _visible_text(value, field_name, allow_empty=True)


class CleanupDisposition(StrEnum):
    ARCHIVE = "archive"
    TRASH = "trash"


class CleanupStorageEffect(StrEnum):
    NONE = "none"
    NOT_GUARANTEED = "not_guaranteed"


class CleanupPlanState(StrEnum):
    FROZEN = "frozen"
    REDUCED = "reduced"
    INVALIDATED = "invalidated"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CleanupReadState(StrEnum):
    ANY = "any"
    READ = "read"
    UNREAD = "unread"


class CleanupTargetKind(StrEnum):
    SOURCE = "source"
    FLOW = "flow"
    SENDER = "sender"
    LABEL = "label"


class CleanupTemporalKind(StrEnum):
    ALL = "all"
    BEFORE_DATE = "beforeDate"
    DATE_RANGE = "dateRange"
    OLDER_THAN_DAYS = "olderThanDays"


class CleanupExclusionReason(StrEnum):
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
    OUTSIDE_DATE = "outside_date"
    READ_STATE_MISMATCH = "read_state_mismatch"
    EXCLUDED_LABEL = "excluded_label"
    KEEP_LATEST = "keep_latest"
    MISSING_AFTER_CREATION = "missing_after_creation"
    SCOPE_CHANGED = "scope_changed"
    PROTECTION_CHANGED = "protection_changed"


class CleanupMemberInitialState(StrEnum):
    SELECTED = "selected"
    EXCLUDED = "excluded"


class CleanupMemberCurrentState(StrEnum):
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"
    REMOVED = "removed"


class CleanupSampleKind(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"


class CleanupEventType(StrEnum):
    CREATED = "created"
    REVALIDATED = "revalidated"
    REDUCED = "reduced"
    INVALIDATED = "invalidated"
    CANCELLED = "cancelled"


class CleanupCommandStatus(StrEnum):
    CREATED = "created"
    REVALIDATED = "revalidated"
    CANCELLED = "cancelled"


class CleanupPlanErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    INVALID_CURSOR = "invalid_cursor"
    INVALID_LOCAL_ORIGIN = "invalid_local_origin"
    ROUTE_NOT_FOUND = "route_not_found"
    TARGET_NOT_FOUND = "target_not_found"
    PLAN_NOT_FOUND = "plan_not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    MAP_REVISION_CONFLICT = "map_revision_conflict"
    POLICY_REVISION_CONFLICT = "policy_revision_conflict"
    PLAN_REVISION_CONFLICT = "plan_revision_conflict"
    COMMAND_ID_CONFLICT = "command_id_conflict"
    CURSOR_STALE = "cursor_stale"
    INVALID_TRANSITION = "invalid_transition"
    PLAN_EXPIRED = "plan_expired"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    PLAN_TOO_LARGE = "plan_too_large"
    JSON_REQUIRED = "json_required"
    UNSUPPORTED_TARGET = "unsupported_target"
    INVALID_FILTER = "invalid_filter"
    STUDY_UNAVAILABLE = "study_unavailable"
    INVENTORY_INCOMPLETE = "inventory_incomplete"
    ACCOUNT_UNAVAILABLE = "account_unavailable"
    INTERNAL_ERROR = "internal_error"


class CleanupPlanError(RuntimeError):
    __slots__ = ()
    _RUNTIME_ATTRIBUTES = frozenset(
        {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
    )

    def __init__(self, code: CleanupPlanErrorCode) -> None:
        if not isinstance(code, CleanupPlanErrorCode):
            raise TypeError("code must be a CleanupPlanErrorCode")
        super().__init__(code.value)

    @property
    def code(self) -> CleanupPlanErrorCode:
        return CleanupPlanErrorCode(self.args[0])

    def __getattribute__(self, name: str) -> object:
        if name == "__dict__":
            raise AttributeError("CleanupPlanError is closed")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__setattr__(self, name, value)
            return
        raise AttributeError("CleanupPlanError is immutable")

    def __delattr__(self, name: str) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__delattr__(self, name)
            return
        raise AttributeError("CleanupPlanError is immutable")

    def __repr__(self) -> str:
        return f"CleanupPlanError(code={self.code.value!r})"


@dataclass(frozen=True, slots=True, kw_only=True)
class AllTemporalFilter:
    kind: CleanupTemporalKind = field(default=CleanupTemporalKind.ALL, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class BeforeDateTemporalFilter:
    date: date = field(repr=False)
    kind: CleanupTemporalKind = field(default=CleanupTemporalKind.BEFORE_DATE, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _civil_date(self.date, "date")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class DateRangeTemporalFilter:
    on_or_after_date: date = field(repr=False)
    before_date: date = field(repr=False)
    kind: CleanupTemporalKind = field(default=CleanupTemporalKind.DATE_RANGE, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _civil_date(self.on_or_after_date, "on_or_after_date")
        _civil_date(self.before_date, "before_date")
        if self.on_or_after_date >= self.before_date:
            raise ValueError("on_or_after_date must precede before_date")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class OlderThanDaysTemporalFilter:
    days: int
    kind: CleanupTemporalKind = field(default=CleanupTemporalKind.OLDER_THAN_DAYS, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _integer(self.days, "days", minimum=1, maximum=MAX_OLDER_THAN_DAYS)
        _exact_version(self.version)


CleanupTemporalFilter: TypeAlias = (
    AllTemporalFilter
    | BeforeDateTemporalFilter
    | DateRangeTemporalFilter
    | OlderThanDaysTemporalFilter
)
_TEMPORAL_TYPES = (
    AllTemporalFilter,
    BeforeDateTemporalFilter,
    DateRangeTemporalFilter,
    OlderThanDaysTemporalFilter,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedTemporalFilter:
    requested: CleanupTemporalFilter
    resolved_on_or_after_utc: datetime | None = field(repr=False)
    resolved_before_utc: datetime | None = field(repr=False)
    time_zone: str = CLEANUP_PLAN_TIME_ZONE
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.requested, _TEMPORAL_TYPES):
            raise TypeError("requested must be a closed temporal filter")
        object.__setattr__(
            self,
            "resolved_on_or_after_utc",
            _optional_utc(self.resolved_on_or_after_utc, "resolved_on_or_after_utc"),
        )
        object.__setattr__(
            self,
            "resolved_before_utc",
            _optional_utc(self.resolved_before_utc, "resolved_before_utc"),
        )
        if self.time_zone != CLEANUP_PLAN_TIME_ZONE:
            raise ValueError("time_zone must be America/Argentina/Cordoba")
        if (
            self.resolved_on_or_after_utc is not None
            and self.resolved_before_utc is not None
            and self.resolved_on_or_after_utc >= self.resolved_before_utc
        ):
            raise ValueError("resolved temporal bounds are invalid")
        if isinstance(self.requested, AllTemporalFilter) and (
            self.resolved_on_or_after_utc is not None or self.resolved_before_utc is not None
        ):
            raise ValueError("all temporal filter must not have resolved bounds")
        if isinstance(
            self.requested,
            (BeforeDateTemporalFilter, OlderThanDaysTemporalFilter),
        ) and (self.resolved_on_or_after_utc is not None or self.resolved_before_utc is None):
            raise ValueError("exclusive temporal filter has invalid resolved bounds")
        if isinstance(self.requested, DateRangeTemporalFilter) and (
            self.resolved_on_or_after_utc is None or self.resolved_before_utc is None
        ):
            raise ValueError("date range must have both resolved bounds")
        _exact_version(self.version)


_TARGET_KIND_RANK = {
    CleanupTargetKind.SOURCE: 0,
    CleanupTargetKind.FLOW: 1,
    CleanupTargetKind.SENDER: 2,
    CleanupTargetKind.LABEL: 3,
}


def cleanup_target_sort_key(value: CleanupTarget) -> tuple[int, str]:
    return (_TARGET_KIND_RANK[value.kind], value.target_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupTarget:
    kind: CleanupTargetKind
    target_id: str = field(repr=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CleanupTargetKind):
            raise TypeError("kind must be a CleanupTargetKind")
        pattern = {
            CleanupTargetKind.SOURCE: _SOURCE_ID,
            CleanupTargetKind.FLOW: _FLOW_ID,
            CleanupTargetKind.SENDER: _SENDER_ID,
            CleanupTargetKind.LABEL: _LABEL_ID,
        }[self.kind]
        _versioned_id(self.target_id, "target_id", pattern)
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceCatalogItem:
    target_id: str = field(repr=False)
    display_name: str = field(repr=False)
    message_count: int
    selector_fingerprint: str = field(repr=False)
    kind: CleanupTargetKind = field(default=CleanupTargetKind.SOURCE, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _SOURCE_ID)
        _visible_text(self.display_name, "display_name")
        _integer(self.message_count, "message_count", minimum=1)
        if _FINGERPRINT.fullmatch(self.selector_fingerprint) is None:
            raise ValueError("selector_fingerprint must be a SHA-256 digest")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowCatalogItem:
    target_id: str = field(repr=False)
    source_id: str = field(repr=False)
    display_name: str = field(repr=False)
    message_count: int
    selector_fingerprint: str = field(repr=False)
    kind: CleanupTargetKind = field(default=CleanupTargetKind.FLOW, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _FLOW_ID)
        _versioned_id(self.source_id, "source_id", _SOURCE_ID)
        _visible_text(self.display_name, "display_name")
        _integer(self.message_count, "message_count", minimum=1)
        if _FINGERPRINT.fullmatch(self.selector_fingerprint) is None:
            raise ValueError("selector_fingerprint must be a SHA-256 digest")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class SenderCatalogItem:
    target_id: str = field(repr=False)
    display_address: str = field(repr=False)
    message_count: int
    kind: CleanupTargetKind = field(default=CleanupTargetKind.SENDER, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _SENDER_ID)
        _visible_text(self.display_address, "display_address")
        _integer(self.message_count, "message_count", minimum=1)
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class LabelCatalogItem:
    target_id: str = field(repr=False)
    display_name: str = field(repr=False)
    provider_label_id: str = field(repr=False)
    message_count: int
    kind: CleanupTargetKind = field(default=CleanupTargetKind.LABEL, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _LABEL_ID)
        _visible_text(self.display_name, "display_name")
        validate_opaque_identifier(self.provider_label_id, "provider_label_id")
        _integer(self.message_count, "message_count", minimum=1)
        _exact_version(self.version)


CleanupTargetCatalogItem: TypeAlias = (
    SourceCatalogItem | FlowCatalogItem | SenderCatalogItem | LabelCatalogItem
)
_CATALOG_ITEM_TYPES = (SourceCatalogItem, FlowCatalogItem, SenderCatalogItem, LabelCatalogItem)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceTargetSnapshot:
    target_id: str = field(repr=False)
    display_name: str = field(repr=False)
    selector_fingerprint: str = field(repr=False)
    kind: CleanupTargetKind = field(default=CleanupTargetKind.SOURCE, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _SOURCE_ID)
        _visible_text(self.display_name, "display_name")
        if _FINGERPRINT.fullmatch(self.selector_fingerprint) is None:
            raise ValueError("selector_fingerprint must be a SHA-256 digest")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowTargetSnapshot:
    target_id: str = field(repr=False)
    display_name: str = field(repr=False)
    selector_fingerprint: str = field(repr=False)
    kind: CleanupTargetKind = field(default=CleanupTargetKind.FLOW, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _FLOW_ID)
        _visible_text(self.display_name, "display_name")
        if _FINGERPRINT.fullmatch(self.selector_fingerprint) is None:
            raise ValueError("selector_fingerprint must be a SHA-256 digest")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class SenderTargetSnapshot:
    target_id: str = field(repr=False)
    display_address: str = field(repr=False)
    kind: CleanupTargetKind = field(default=CleanupTargetKind.SENDER, init=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.target_id, "target_id", _SENDER_ID)
        _visible_text(self.display_address, "display_address")
        _exact_version(self.version)


CleanupTargetSnapshot: TypeAlias = SourceTargetSnapshot | FlowTargetSnapshot | SenderTargetSnapshot
_TARGET_SNAPSHOT_TYPES = (SourceTargetSnapshot, FlowTargetSnapshot, SenderTargetSnapshot)


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupLabelSnapshot:
    label_id: str = field(repr=False)
    display_name: str = field(repr=False)
    provider_label_id: str = field(repr=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _versioned_id(self.label_id, "label_id", _LABEL_ID)
        _visible_text(self.display_name, "display_name")
        validate_opaque_identifier(self.provider_label_id, "provider_label_id")
        _exact_version(self.version)


def _validate_expected_revisions(map_revision: str, policy_revision: int) -> None:
    if _MAP_REVISION.fullmatch(map_revision) is None:
        raise ValueError("expected_map_revision must be a versioned opaque identifier")
    _integer(policy_revision, "expected_policy_revision")


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateCleanupPlanCommand:
    command_id: str = field(repr=False)
    expected_map_revision: str = field(repr=False)
    expected_policy_revision: int
    disposition: CleanupDisposition
    targets: tuple[CleanupTarget, ...] = field(repr=False)
    temporal_filter: CleanupTemporalFilter = field(repr=False)
    read_state: CleanupReadState
    excluded_label_ids: tuple[str, ...] = field(default=(), repr=False)
    keep_latest_per_flow: int = 0
    version: int = CLEANUP_PLAN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _uuid_v4(self.command_id, "command_id")
        _validate_expected_revisions(self.expected_map_revision, self.expected_policy_revision)
        if not isinstance(self.disposition, CleanupDisposition):
            raise TypeError("disposition must be a CleanupDisposition")
        if not isinstance(self.targets, tuple) or any(
            not isinstance(item, CleanupTarget) for item in self.targets
        ):
            raise TypeError("targets must contain CleanupTarget values")
        if not 1 <= len(self.targets) <= MAX_TARGETS:
            raise ValueError("targets must contain between one and 100 values")
        if any(item.kind is CleanupTargetKind.LABEL for item in self.targets):
            raise ValueError("label is not a selectable target")
        keys = tuple(cleanup_target_sort_key(item) for item in self.targets)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError("targets must be canonical, unique and ordered")
        if not isinstance(self.temporal_filter, _TEMPORAL_TYPES):
            raise TypeError("temporal_filter must be a closed temporal filter")
        if not isinstance(self.read_state, CleanupReadState):
            raise TypeError("read_state must be a CleanupReadState")
        if not isinstance(self.excluded_label_ids, tuple):
            raise TypeError("excluded_label_ids must be a tuple")
        if len(self.excluded_label_ids) > MAX_EXCLUDED_LABELS:
            raise ValueError("excluded_label_ids exceeds the contract limit")
        for label_id in self.excluded_label_ids:
            _versioned_id(label_id, "excluded label id", _LABEL_ID)
        if self.excluded_label_ids != tuple(sorted(set(self.excluded_label_ids))):
            raise ValueError("excluded_label_ids must be canonical and unique")
        _integer(
            self.keep_latest_per_flow,
            "keep_latest_per_flow",
            maximum=MAX_KEEP_LATEST_PER_FLOW,
        )
        _exact_version(self.version, CLEANUP_PLAN_CONTRACT_VERSION)

    def __repr__(self) -> str:
        return (
            "CreateCleanupPlanCommand(command_id=<redacted>, revisions=<redacted>, "
            f"disposition={self.disposition.value!r}, target_count={len(self.targets)}, "
            f"temporal_kind={self.temporal_filter.kind.value!r}, "
            f"read_state={self.read_state.value!r}, "
            f"excluded_label_count={len(self.excluded_label_ids)}, "
            f"keep_latest_per_flow={self.keep_latest_per_flow}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RevalidateCleanupPlanCommand:
    command_id: str = field(repr=False)
    expected_plan_revision: int
    expected_map_revision: str = field(repr=False)
    expected_policy_revision: int
    version: int = CLEANUP_PLAN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _uuid_v4(self.command_id, "command_id")
        _integer(self.expected_plan_revision, "expected_plan_revision", minimum=1)
        _validate_expected_revisions(self.expected_map_revision, self.expected_policy_revision)
        _exact_version(self.version, CLEANUP_PLAN_CONTRACT_VERSION)

    def __repr__(self) -> str:
        return (
            "RevalidateCleanupPlanCommand(command_id=<redacted>, "
            f"expected_plan_revision={self.expected_plan_revision}, "
            "map_revision=<redacted>, policy_revision=<redacted>, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelCleanupPlanCommand:
    command_id: str = field(repr=False)
    expected_plan_revision: int
    version: int = CLEANUP_PLAN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _uuid_v4(self.command_id, "command_id")
        _integer(self.expected_plan_revision, "expected_plan_revision", minimum=1)
        _exact_version(self.version, CLEANUP_PLAN_CONTRACT_VERSION)

    def __repr__(self) -> str:
        return (
            "CancelCleanupPlanCommand(command_id=<redacted>, "
            f"expected_plan_revision={self.expected_plan_revision}, "
            f"version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanSelection:
    disposition: CleanupDisposition
    targets: tuple[CleanupTarget, ...] = field(repr=False)
    target_snapshots: tuple[CleanupTargetSnapshot, ...] = field(repr=False)
    temporal_filter: ResolvedTemporalFilter = field(repr=False)
    read_state: CleanupReadState
    excluded_label_ids: tuple[str, ...] = field(repr=False)
    excluded_label_snapshots: tuple[CleanupLabelSnapshot, ...] = field(repr=False)
    keep_latest_per_flow: int
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CleanupDisposition):
            raise TypeError("disposition must be a CleanupDisposition")
        if not isinstance(self.targets, tuple) or any(
            not isinstance(item, CleanupTarget) for item in self.targets
        ):
            raise TypeError("targets must contain CleanupTarget values")
        if not 1 <= len(self.targets) <= MAX_TARGETS:
            raise ValueError("targets must contain between one and 100 values")
        if any(item.kind is CleanupTargetKind.LABEL for item in self.targets):
            raise ValueError("label cannot be a cleanup target")
        target_keys = tuple(cleanup_target_sort_key(item) for item in self.targets)
        if len(set(target_keys)) != len(target_keys):
            raise ValueError("targets must not contain duplicates")
        if target_keys != tuple(sorted(target_keys)):
            raise ValueError("targets must use canonical order")
        if not isinstance(self.target_snapshots, tuple) or any(
            not isinstance(item, _TARGET_SNAPSHOT_TYPES) for item in self.target_snapshots
        ):
            raise TypeError("target_snapshots must contain closed snapshot values")
        snapshot_keys = tuple(
            (_TARGET_KIND_RANK[item.kind], item.target_id) for item in self.target_snapshots
        )
        if target_keys != snapshot_keys:
            raise ValueError("target snapshots must correspond to targets in canonical order")
        if not isinstance(self.temporal_filter, ResolvedTemporalFilter):
            raise TypeError("temporal_filter must be a ResolvedTemporalFilter")
        if not isinstance(self.read_state, CleanupReadState):
            raise TypeError("read_state must be a CleanupReadState")
        if not isinstance(self.excluded_label_ids, tuple):
            raise TypeError("excluded_label_ids must be a tuple")
        if len(self.excluded_label_ids) > MAX_EXCLUDED_LABELS:
            raise ValueError("excluded_label_ids cannot exceed 100 values")
        for label_id in self.excluded_label_ids:
            _versioned_id(label_id, "excluded_label_id", _LABEL_ID)
        if len(set(self.excluded_label_ids)) != len(self.excluded_label_ids):
            raise ValueError("excluded_label_ids must not contain duplicates")
        if self.excluded_label_ids != tuple(sorted(self.excluded_label_ids)):
            raise ValueError("excluded_label_ids must use canonical order")
        if not isinstance(self.excluded_label_snapshots, tuple) or any(
            not isinstance(item, CleanupLabelSnapshot) for item in self.excluded_label_snapshots
        ):
            raise TypeError("excluded_label_snapshots must contain CleanupLabelSnapshot values")
        label_ids = tuple(item.label_id for item in self.excluded_label_snapshots)
        if self.excluded_label_ids != label_ids:
            raise ValueError("excluded label snapshots must correspond to label IDs")
        _integer(
            self.keep_latest_per_flow,
            "keep_latest_per_flow",
            maximum=MAX_KEEP_LATEST_PER_FLOW,
        )
        _exact_version(self.version)

    @property
    def storage_effect(self) -> CleanupStorageEffect:
        if self.disposition is CleanupDisposition.ARCHIVE:
            return CleanupStorageEffect.NONE
        return CleanupStorageEffect.NOT_GUARANTEED

    def __repr__(self) -> str:
        return (
            f"CleanupPlanSelection(disposition={self.disposition.value!r}, "
            f"target_count={len(self.targets)}, temporal_kind="
            f"{self.temporal_filter.requested.kind.value!r}, "
            f"read_state={self.read_state.value!r}, "
            f"excluded_label_count={len(self.excluded_label_ids)}, "
            f"keep_latest_per_flow={self.keep_latest_per_flow}, version={self.version})"
        )


_REASON_RANK = {reason: index for index, reason in enumerate(CleanupExclusionReason)}
_CREATION_REASONS = frozenset(tuple(CleanupExclusionReason)[:18])
_POLICY_PROTECTION_REASONS = frozenset(tuple(CleanupExclusionReason)[:14])


def canonical_reason_codes(
    values: tuple[CleanupExclusionReason, ...],
) -> tuple[CleanupExclusionReason, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CleanupExclusionReason) for item in values
    ):
        raise TypeError("reason_codes must contain CleanupExclusionReason values")
    if len(set(values)) != len(values):
        raise ValueError("reason_codes must not contain duplicates")
    if values != tuple(sorted(values, key=_REASON_RANK.__getitem__)):
        raise ValueError("reason_codes must use contractual precedence")
    return values


def cleanup_creation_reason_codes(
    values: tuple[CleanupExclusionReason, ...],
) -> tuple[CleanupExclusionReason, ...]:
    canonical_reason_codes(values)
    if any(reason not in _CREATION_REASONS for reason in values):
        raise ValueError("creation members cannot contain revalidation-only reasons")
    return values


def cleanup_removal_reason_codes(
    values: tuple[CleanupExclusionReason, ...],
) -> tuple[CleanupExclusionReason, ...]:
    canonical_reason_codes(values)
    if not values:
        raise ValueError("a removal requires at least one reason")
    if (
        CleanupExclusionReason.MISSING_AFTER_CREATION in values
        and values != (CleanupExclusionReason.MISSING_AFTER_CREATION,)
    ):
        raise ValueError("missing_after_creation must be the only removal reason")
    has_current_protection = any(reason in _POLICY_PROTECTION_REASONS for reason in values)
    has_protection_change = CleanupExclusionReason.PROTECTION_CHANGED in values
    if has_current_protection != has_protection_change:
        raise ValueError("current protection reasons and protection_changed must occur together")
    return values


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanMember:
    provider_message_id: str = field(repr=False)
    message_id: str = field(repr=False)
    initial_state: CleanupMemberInitialState
    received_at: datetime
    size_estimate_bytes: int
    source_id: str = field(repr=False)
    flow_id: str = field(repr=False)
    read_state: CleanupReadState
    reason_codes: tuple[CleanupExclusionReason, ...]
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.provider_message_id, "provider_message_id")
        _versioned_id(self.message_id, "message_id", _MESSAGE_ID)
        if not isinstance(self.initial_state, CleanupMemberInitialState):
            raise TypeError("initial_state must be a CleanupMemberInitialState")
        object.__setattr__(self, "received_at", _utc_datetime(self.received_at, "received_at"))
        _integer(
            self.size_estimate_bytes,
            "size_estimate_bytes",
            maximum=MAX_MESSAGE_SIZE_ESTIMATE_BYTES,
        )
        _versioned_id(self.source_id, "source_id", _SOURCE_ID)
        _versioned_id(self.flow_id, "flow_id", _FLOW_ID)
        if (
            not isinstance(self.read_state, CleanupReadState)
            or self.read_state is CleanupReadState.ANY
        ):
            raise ValueError("member read_state must be read or unread")
        cleanup_creation_reason_codes(self.reason_codes)
        if self.initial_state is CleanupMemberInitialState.SELECTED and self.reason_codes:
            raise ValueError("an initially selected member cannot contain reasons")
        if self.initial_state is CleanupMemberInitialState.EXCLUDED and not self.reason_codes:
            raise ValueError("an initially excluded member requires reasons")
        _exact_version(self.version)

    def __repr__(self) -> str:
        return (
            "CleanupPlanMember(ids=<redacted>, "
            f"initial_state={self.initial_state.value!r}, received_at=<redacted>, "
            f"size_estimate_bytes={self.size_estimate_bytes}, "
            f"read_state={self.read_state.value!r}, "
            f"reason_count={len(self.reason_codes)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanMemberRemoval:
    provider_message_id: str = field(repr=False)
    message_id: str = field(repr=False)
    revision: int
    recorded_at: datetime
    reason_codes: tuple[CleanupExclusionReason, ...]
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.provider_message_id, "provider_message_id")
        _versioned_id(self.message_id, "message_id", _MESSAGE_ID)
        _integer(self.revision, "revision", minimum=2)
        object.__setattr__(self, "recorded_at", _utc_datetime(self.recorded_at, "recorded_at"))
        cleanup_removal_reason_codes(self.reason_codes)
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanSample:
    kind: CleanupSampleKind
    position: int
    message_id: str = field(repr=False)
    received_at: datetime
    sender_name: str | None = field(repr=False)
    sender_address: str | None = field(repr=False)
    subject: str | None = field(repr=False)
    size_estimate_bytes: int
    source_id: str = field(repr=False)
    flow_id: str = field(repr=False)
    read_state: CleanupReadState
    exclusion_reasons: tuple[CleanupExclusionReason, ...]
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CleanupSampleKind):
            raise TypeError("kind must be a CleanupSampleKind")
        limit = (
            MAX_INCLUDED_SAMPLES
            if self.kind is CleanupSampleKind.INCLUDED
            else MAX_EXCLUDED_SAMPLES
        )
        _integer(self.position, "position", maximum=limit - 1)
        _versioned_id(self.message_id, "message_id", _MESSAGE_ID)
        object.__setattr__(self, "received_at", _utc_datetime(self.received_at, "received_at"))
        _optional_visible_text(self.sender_name, "sender_name")
        _optional_visible_text(self.sender_address, "sender_address")
        _optional_visible_text(self.subject, "subject")
        _integer(
            self.size_estimate_bytes,
            "size_estimate_bytes",
            maximum=MAX_MESSAGE_SIZE_ESTIMATE_BYTES,
        )
        _versioned_id(self.source_id, "source_id", _SOURCE_ID)
        _versioned_id(self.flow_id, "flow_id", _FLOW_ID)
        if (
            not isinstance(self.read_state, CleanupReadState)
            or self.read_state is CleanupReadState.ANY
        ):
            raise ValueError("sample read_state must be read or unread")
        canonical_reason_codes(self.exclusion_reasons)
        if self.kind is CleanupSampleKind.INCLUDED and self.exclusion_reasons:
            raise ValueError("included samples cannot contain exclusion reasons")
        if self.kind is CleanupSampleKind.EXCLUDED and not self.exclusion_reasons:
            raise ValueError("excluded samples require exclusion reasons")
        _exact_version(self.version)

    def __repr__(self) -> str:
        return (
            f"CleanupPlanSample(kind={self.kind.value!r}, position={self.position}, "
            "message_id=<redacted>, metadata=<redacted>, "
            f"size_estimate_bytes={self.size_estimate_bytes}, "
            f"reason_count={len(self.exclusion_reasons)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanEvent:
    revision: int
    type: CleanupEventType
    recorded_at: datetime
    state: CleanupPlanState
    observed_map_revision: str | None = field(repr=False)
    observed_policy_revision: int | None = field(repr=False)
    removed_count: int
    remaining_count: int
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        _integer(self.revision, "revision", minimum=1)
        if not isinstance(self.type, CleanupEventType):
            raise TypeError("type must be a CleanupEventType")
        object.__setattr__(self, "recorded_at", _utc_datetime(self.recorded_at, "recorded_at"))
        if not isinstance(self.state, CleanupPlanState) or self.state is CleanupPlanState.EXPIRED:
            raise ValueError("events cannot persist expired state")
        if (self.observed_map_revision is None) != (self.observed_policy_revision is None):
            raise ValueError("observed revisions must both be present or absent")
        if (
            self.observed_map_revision is not None
            and _MAP_REVISION.fullmatch(self.observed_map_revision) is None
        ):
            raise ValueError("observed_map_revision is invalid")
        if self.observed_policy_revision is not None:
            _integer(self.observed_policy_revision, "observed_policy_revision")
        if self.type is CleanupEventType.CANCELLED:
            if self.observed_map_revision is not None:
                raise ValueError("cancelled event must not observe map revisions")
        elif self.observed_map_revision is None:
            raise ValueError("non-cancel event must observe map revisions")
        _integer(self.removed_count, "removed_count")
        _integer(self.remaining_count, "remaining_count")
        if self.type is CleanupEventType.CREATED and (
            self.revision != 1 or self.removed_count != 0
        ):
            raise ValueError("created event must be revision one with zero removals")
        if self.type is CleanupEventType.CREATED:
            if self.state not in (CleanupPlanState.FROZEN, CleanupPlanState.INVALIDATED):
                raise ValueError("created event has an invalid state")
            if (self.state is CleanupPlanState.FROZEN) != (self.remaining_count > 0):
                raise ValueError("created event state must match remaining members")
        elif self.type is CleanupEventType.REVALIDATED:
            if (
                self.state not in (CleanupPlanState.FROZEN, CleanupPlanState.REDUCED)
                or self.removed_count != 0
                or self.remaining_count == 0
            ):
                raise ValueError("revalidated event must preserve an active selection")
        elif self.type is CleanupEventType.REDUCED:
            if (
                self.state is not CleanupPlanState.REDUCED
                or self.removed_count == 0
                or self.remaining_count == 0
            ):
                raise ValueError("reduced event must remove members and remain active")
        elif self.type is CleanupEventType.INVALIDATED:
            if (
                self.state is not CleanupPlanState.INVALIDATED
                or self.removed_count == 0
                or self.remaining_count != 0
            ):
                raise ValueError("invalidated event must remove the remaining selection")
        elif self.type is CleanupEventType.CANCELLED and (
            self.state is not CleanupPlanState.CANCELLED
            or self.removed_count != 0
            or self.remaining_count == 0
        ):
            raise ValueError("cancelled event must preserve a non-empty preview")
        _exact_version(self.version)


@dataclass(frozen=True, slots=True, kw_only=True)
class CleanupPlanReceipt:
    command_id: str = field(repr=False)
    request_fingerprint: str = field(repr=False)
    status: CleanupCommandStatus
    replayed: bool
    command_revision: int
    plan_id: str = field(repr=False)
    removed_count: int | None = None
    version: int = CLEANUP_PLAN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _uuid_v4(self.command_id, "command_id")
        if _FINGERPRINT.fullmatch(self.request_fingerprint) is None:
            raise ValueError("request_fingerprint must be a SHA-256 digest")
        if not isinstance(self.status, CleanupCommandStatus):
            raise TypeError("status must be a CleanupCommandStatus")
        if not isinstance(self.replayed, bool):
            raise TypeError("replayed must be a boolean")
        _integer(self.command_revision, "command_revision", minimum=1)
        _plan_id(self.plan_id)
        if self.status is CleanupCommandStatus.REVALIDATED:
            if self.removed_count is None:
                raise ValueError("revalidation receipt requires removed_count")
            _integer(self.removed_count, "removed_count")
        elif self.removed_count is not None:
            raise ValueError("only revalidation receipt may contain removed_count")
        _exact_version(self.version, CLEANUP_PLAN_CONTRACT_VERSION)

    def __repr__(self) -> str:
        return (
            "CleanupPlanReceipt(command_id=<redacted>, fingerprint=<redacted>, "
            f"status={self.status.value!r}, replayed={self.replayed}, "
            f"command_revision={self.command_revision}, plan_id=<redacted>, "
            f"removed_count={self.removed_count!r}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedCleanupPlan:
    account_key: str = field(repr=False)
    plan_id: str = field(repr=False)
    selection: CleanupPlanSelection = field(repr=False)
    created_from_input_revision: str = field(repr=False)
    created_from_map_revision: str = field(repr=False)
    created_from_policy_revision: int = field(repr=False)
    created_at: datetime
    expires_at: datetime
    members: tuple[CleanupPlanMember, ...] = field(repr=False)
    samples: tuple[CleanupPlanSample, ...] = field(repr=False)
    events: tuple[CleanupPlanEvent, ...]
    removals: tuple[CleanupPlanMemberRemoval, ...] = field(default=(), repr=False)
    version: int = CLEANUP_PLAN_MODEL_VERSION

    def __post_init__(self) -> None:
        validate_account_key(self.account_key)
        _plan_id(self.plan_id)
        if not isinstance(self.selection, CleanupPlanSelection):
            raise TypeError("selection must be a CleanupPlanSelection")
        if _INPUT_REVISION.fullmatch(self.created_from_input_revision) is None:
            raise ValueError("created_from_input_revision is invalid")
        if _MAP_REVISION.fullmatch(self.created_from_map_revision) is None:
            raise ValueError("created_from_map_revision is invalid")
        _integer(self.created_from_policy_revision, "created_from_policy_revision")
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "expires_at", _utc_datetime(self.expires_at, "expires_at"))
        if (self.expires_at - self.created_at).total_seconds() != CLEANUP_PLAN_VALIDITY_SECONDS:
            raise ValueError("expires_at must be exactly 24 hours after created_at")
        if not isinstance(self.members, tuple) or any(
            not isinstance(item, CleanupPlanMember) for item in self.members
        ):
            raise TypeError("members must contain CleanupPlanMember values")
        if not self.members or len(self.members) > MAX_CONSIDERED_MESSAGES:
            raise ValueError("members must contain the non-empty considered universe")
        member_ids = tuple(item.message_id for item in self.members)
        if len(set(member_ids)) != len(member_ids) or member_ids != tuple(sorted(member_ids)):
            raise ValueError("members must be unique and ordered by local ID")
        provider_ids = tuple(item.provider_message_id for item in self.members)
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("members must not duplicate provider identities")
        if not isinstance(self.samples, tuple) or any(
            not isinstance(item, CleanupPlanSample) for item in self.samples
        ):
            raise TypeError("samples must contain CleanupPlanSample values")
        members_by_message_id = {item.message_id: item for item in self.members}
        for sample in self.samples:
            member = members_by_message_id.get(sample.message_id)
            if member is None:
                raise ValueError("samples must reference existing plan members")
            expected_kind = (
                CleanupSampleKind.INCLUDED
                if member.initial_state is CleanupMemberInitialState.SELECTED
                else CleanupSampleKind.EXCLUDED
            )
            if sample.kind is not expected_kind:
                raise ValueError("sample kind must match member initial state")
            if (
                sample.received_at != member.received_at
                or sample.size_estimate_bytes != member.size_estimate_bytes
                or sample.source_id != member.source_id
                or sample.flow_id != member.flow_id
                or sample.read_state is not member.read_state
                or sample.exclusion_reasons != member.reason_codes
            ):
                raise ValueError("sample snapshot must match its plan member")
        sample_message_ids = tuple(item.message_id for item in self.samples)
        if len(set(sample_message_ids)) != len(sample_message_ids):
            raise ValueError("samples must not duplicate plan members")
        for kind, limit in (
            (CleanupSampleKind.INCLUDED, MAX_INCLUDED_SAMPLES),
            (CleanupSampleKind.EXCLUDED, MAX_EXCLUDED_SAMPLES),
        ):
            values = tuple(item for item in self.samples if item.kind is kind)
            if len(values) > limit or tuple(item.position for item in values) != tuple(
                range(len(values))
            ):
                raise ValueError("sample positions must be contiguous and bounded")
            canonical_values = tuple(sorted(values, key=lambda item: item.message_id))
            canonical_values = tuple(
                sorted(
                    canonical_values,
                    key=lambda item: item.received_at,
                    reverse=True,
                )
            )
            if values != canonical_values:
                raise ValueError("samples must use canonical preview order")
        if not isinstance(self.events, tuple) or any(
            not isinstance(item, CleanupPlanEvent) for item in self.events
        ):
            raise TypeError("events must contain CleanupPlanEvent values")
        if not self.events or tuple(item.revision for item in self.events) != tuple(
            range(1, len(self.events) + 1)
        ):
            raise ValueError("events must form a complete revision ledger")
        if self.events[0].type is not CleanupEventType.CREATED:
            raise ValueError("the first event must be created")
        first_event = self.events[0]
        if (
            first_event.recorded_at != self.created_at
            or first_event.observed_map_revision != self.created_from_map_revision
            or first_event.observed_policy_revision != self.created_from_policy_revision
        ):
            raise ValueError("created event must match the frozen plan header")
        if any(
            event.recorded_at < self.created_at or event.recorded_at >= self.expires_at
            for event in self.events
        ):
            raise ValueError("persisted events must occur during plan validity")
        for previous, current in zip(self.events, self.events[1:], strict=False):
            if previous.state in (CleanupPlanState.CANCELLED, CleanupPlanState.INVALIDATED):
                raise ValueError("terminal plan states cannot be revived")
            if current.recorded_at < previous.recorded_at:
                raise ValueError("cleanup event times must be monotonic")
            if current.type is CleanupEventType.REVALIDATED:
                valid_transition = (
                    current.state is previous.state
                    and current.remaining_count == previous.remaining_count
                )
            elif current.type in (CleanupEventType.REDUCED, CleanupEventType.INVALIDATED):
                valid_transition = (
                    current.remaining_count
                    == previous.remaining_count - current.removed_count
                )
            elif current.type is CleanupEventType.CANCELLED:
                valid_transition = current.remaining_count == previous.remaining_count
            else:
                valid_transition = False
            if not valid_transition:
                raise ValueError("cleanup event ledger contains an invalid transition")
        if not isinstance(self.removals, tuple) or any(
            not isinstance(item, CleanupPlanMemberRemoval) for item in self.removals
        ):
            raise TypeError("removals must contain CleanupPlanMemberRemoval values")
        removal_ids = tuple(item.message_id for item in self.removals)
        if len(set(removal_ids)) != len(removal_ids):
            raise ValueError("a member may be removed only once")
        if any(
            item.message_id not in members_by_message_id
            or members_by_message_id[item.message_id].initial_state
            is not CleanupMemberInitialState.SELECTED
            or item.provider_message_id
            != members_by_message_id[item.message_id].provider_message_id
            or item.revision > len(self.events)
            or item.recorded_at != self.events[item.revision - 1].recorded_at
            for item in self.removals
        ):
            raise ValueError("removals must reference selected members and valid events")
        if any(
            event.removed_count
            != sum(removal.revision == event.revision for removal in self.removals)
            for event in self.events
        ):
            raise ValueError("event removal counts must match the append-only ledger")
        selected_count = self.selected_at_creation_count
        if self.events[0].remaining_count != selected_count:
            raise ValueError("created event remaining_count must match initial selection")
        if self.events[-1].remaining_count != self.current_eligible_count:
            raise ValueError("last event remaining_count must match current eligibility")
        if self.persisted_state is CleanupPlanState.FROZEN and self.removals:
            raise ValueError("a frozen plan cannot contain removals")
        if self.persisted_state is CleanupPlanState.REDUCED and (
            not self.removals or self.current_eligible_count == 0
        ):
            raise ValueError("a reduced plan requires removals and remaining members")
        if self.persisted_state is CleanupPlanState.INVALIDATED and self.current_eligible_count:
            raise ValueError("an invalidated plan cannot contain eligible members")
        _integer(
            self.selected_at_creation_size_estimate_bytes,
            "selected_at_creation_size_estimate_bytes",
            maximum=MAX_AGGREGATE_SIZE_ESTIMATE_BYTES,
        )
        _integer(
            self.excluded_at_creation_size_estimate_bytes,
            "excluded_at_creation_size_estimate_bytes",
            maximum=MAX_AGGREGATE_SIZE_ESTIMATE_BYTES,
        )
        _integer(
            self.current_eligible_size_estimate_bytes,
            "current_eligible_size_estimate_bytes",
            maximum=MAX_AGGREGATE_SIZE_ESTIMATE_BYTES,
        )
        _exact_version(self.version)

    @property
    def plan_revision(self) -> int:
        return self.events[-1].revision

    @property
    def persisted_state(self) -> CleanupPlanState:
        return self.events[-1].state

    @property
    def storage_effect(self) -> CleanupStorageEffect:
        return self.selection.storage_effect

    @property
    def effective_freed_bytes(self) -> None:
        return None

    @property
    def can_execute(self) -> bool:
        return False

    @property
    def selected_at_creation_count(self) -> int:
        return sum(
            item.initial_state is CleanupMemberInitialState.SELECTED for item in self.members
        )

    @property
    def selected_at_creation_size_estimate_bytes(self) -> int:
        return sum(
            item.size_estimate_bytes
            for item in self.members
            if item.initial_state is CleanupMemberInitialState.SELECTED
        )

    @property
    def excluded_at_creation_count(self) -> int:
        return len(self.members) - self.selected_at_creation_count

    @property
    def excluded_at_creation_size_estimate_bytes(self) -> int:
        return sum(
            item.size_estimate_bytes
            for item in self.members
            if item.initial_state is CleanupMemberInitialState.EXCLUDED
        )

    @property
    def current_eligible_count(self) -> int:
        return self.selected_at_creation_count - len(self.removals)

    @property
    def current_eligible_size_estimate_bytes(self) -> int:
        removed = {item.message_id for item in self.removals}
        return sum(
            item.size_estimate_bytes
            for item in self.members
            if item.initial_state is CleanupMemberInitialState.SELECTED
            and item.message_id not in removed
        )

    @property
    def last_revalidated_at(self) -> datetime | None:
        values = tuple(
            item.recorded_at
            for item in self.events
            if item.type
            in (
                CleanupEventType.REVALIDATED,
                CleanupEventType.REDUCED,
                CleanupEventType.INVALIDATED,
            )
            and item.revision > 1
        )
        return values[-1] if values else None

    def __repr__(self) -> str:
        return (
            "PersistedCleanupPlan(account_key=<redacted>, plan_id=<redacted>, "
            f"plan_revision={self.plan_revision}, state={self.persisted_state.value!r}, "
            f"member_count={len(self.members)}, removal_count={len(self.removals)}, "
            f"event_count={len(self.events)}, version={self.version})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedCleanupPlanCreation:
    plan: PersistedCleanupPlan = field(repr=False)
    receipt: CleanupPlanReceipt

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PersistedCleanupPlan):
            raise TypeError("plan must be a PersistedCleanupPlan")
        if not isinstance(self.receipt, CleanupPlanReceipt):
            raise TypeError("receipt must be a CleanupPlanReceipt")
        if self.receipt.status is not CleanupCommandStatus.CREATED:
            raise ValueError("creation result requires a created receipt")
        if self.receipt.plan_id != self.plan.plan_id or self.receipt.command_revision != 1:
            raise ValueError("creation receipt does not match plan")


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedCleanupPlanRevalidation:
    plan: PersistedCleanupPlan = field(repr=False)
    event: CleanupPlanEvent
    removals: tuple[CleanupPlanMemberRemoval, ...] = field(repr=False)
    receipt: CleanupPlanReceipt

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PersistedCleanupPlan):
            raise TypeError("plan must be a PersistedCleanupPlan")
        if not isinstance(self.event, CleanupPlanEvent):
            raise TypeError("event must be a CleanupPlanEvent")
        if not isinstance(self.removals, tuple) or any(
            not isinstance(item, CleanupPlanMemberRemoval) for item in self.removals
        ):
            raise TypeError("removals must contain CleanupPlanMemberRemoval values")
        if not isinstance(self.receipt, CleanupPlanReceipt):
            raise TypeError("receipt must be a CleanupPlanReceipt")
        if self.receipt.status is not CleanupCommandStatus.REVALIDATED:
            raise ValueError("revalidation result requires a revalidated receipt")
        if (
            self.receipt.plan_id != self.plan.plan_id
            or self.receipt.command_revision != self.event.revision
            or self.receipt.removed_count != len(self.removals)
            or self.plan.events[-1] != self.event
        ):
            raise ValueError("revalidation result is internally inconsistent")


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedCleanupPlanCancellation:
    plan: PersistedCleanupPlan = field(repr=False)
    event: CleanupPlanEvent
    receipt: CleanupPlanReceipt

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PersistedCleanupPlan):
            raise TypeError("plan must be a PersistedCleanupPlan")
        if not isinstance(self.event, CleanupPlanEvent):
            raise TypeError("event must be a CleanupPlanEvent")
        if not isinstance(self.receipt, CleanupPlanReceipt):
            raise TypeError("receipt must be a CleanupPlanReceipt")
        if self.receipt.status is not CleanupCommandStatus.CANCELLED:
            raise ValueError("cancellation result requires a cancelled receipt")
        if (
            self.receipt.plan_id != self.plan.plan_id
            or self.receipt.command_revision != self.event.revision
            or self.plan.events[-1] != self.event
        ):
            raise ValueError("cancellation result is internally inconsistent")


# A creation prepared entirely in memory is the immutable draft the repository
# persists atomically together with its command receipt.
CleanupPlanDraft: TypeAlias = PreparedCleanupPlanCreation
