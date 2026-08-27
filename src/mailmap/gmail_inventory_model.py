from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from mailmap.gmail_readonly_policy import (
    GMAIL_HEADER_TOTAL_LIMIT_BYTES,
    GMAIL_HEADER_VALUE_LIMIT_BYTES,
    GMAIL_LIST_PAGE_LIMIT,
    GMAIL_METADATA_HEADERS,
)
from mailmap.index_model import SyncCheckpoint, SyncMode, SyncState, validate_opaque_identifier
from mailmap.session_model import GMAIL_METADATA_SCOPE, SessionIdentity, normalize_account_address


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical value")
    return value


def _optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _non_empty(value, field_name)


def _strict_non_negative(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


def _canonical_labels(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("label_ids must be a tuple")
    for value in values:
        validate_opaque_identifier(value, "label_id")
    return tuple(sorted(set(values)))


class MetadataFormat(StrEnum):
    METADATA = "METADATA"


class FullScanPhase(StrEnum):
    NORMAL = "normal"
    SPAM = "spam"


class HistoryChangeKind(StrEnum):
    ADDED = "added"
    LABELS_CHANGED = "labels_changed"
    DELETED = "deleted"


class InventoryOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    REQUIRES_FULL_RESYNC = "requires_full_resync"
    FAILED = "failed"


class InventoryErrorCode(StrEnum):
    INVALID_RESPONSE = "invalid_response"
    HEADER_LIMIT_EXCEEDED = "header_limit_exceeded"
    IDENTITY_MISMATCH = "identity_mismatch"
    CHECKPOINT_INVALID = "checkpoint_invalid"
    CHECKPOINT_MISSING = "checkpoint_missing"
    TRANSPORT_FAILED = "transport_failed"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    RETRY_EXHAUSTED = "retry_exhausted"
    RETRY_POLICY_INVALID = "retry_policy_invalid"
    CLOCK_INVALID = "clock_invalid"
    CONTROL_INVALID = "control_invalid"
    PERSISTENCE_FAILED = "persistence_failed"
    HISTORY_EXPIRED = "history_expired"


class RemoteErrorCode(StrEnum):
    RATE_LIMITED = "rate_limited"
    USER_RATE_LIMIT_EXCEEDED = "user_rate_limit_exceeded"
    QUOTA_EXCEEDED = "quota_exceeded"
    BACKEND_ERROR = "backend_error"
    HISTORY_NOT_FOUND = "history_not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


class InventoryError(RuntimeError):
    def __init__(self, code: InventoryErrorCode) -> None:
        if not isinstance(code, InventoryErrorCode):
            raise TypeError("code must be an InventoryErrorCode")
        self.code = code
        super().__init__(code.value)

    def __repr__(self) -> str:
        return f"InventoryError(code={self.code.value!r})"


class InventoryTransportError(RuntimeError):
    def __init__(self, code: RemoteErrorCode, *, status: int | None = None) -> None:
        if not isinstance(code, RemoteErrorCode):
            raise TypeError("code must be a RemoteErrorCode")
        if status is not None and (
            isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599
        ):
            raise ValueError("status must be an HTTP status or None")
        self.code = code
        self.status = status
        super().__init__(code.value)

    def __repr__(self) -> str:
        return (
            "InventoryTransportError("
            f"code={self.code.value!r}, status={self.status!r})"
        )


@dataclass(frozen=True, slots=True)
class InventorySession:
    identity: SessionIdentity = field(repr=False)
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SessionIdentity):
            raise TypeError("identity must be a SessionIdentity")
        if self.scopes != (GMAIL_METADATA_SCOPE,):
            raise ValueError("inventory session must contain only the metadata scope")

    def __repr__(self) -> str:
        return "InventorySession(identity=<redacted>, scopes=<metadata-only>)"


@dataclass(frozen=True, slots=True)
class ProfileRequest:
    user_id: str = field(default="me", init=False)


@dataclass(frozen=True, slots=True)
class LabelsRequest:
    user_id: str = field(default="me", init=False)


@dataclass(frozen=True, slots=True)
class MessageListRequest:
    page_token: str | None = field(default=None, repr=False)
    label_ids: tuple[str, ...] = ()
    include_spam_trash: bool = False
    max_results: int = GMAIL_LIST_PAGE_LIMIT
    user_id: str = field(default="me", init=False)

    def __post_init__(self) -> None:
        _optional_non_empty(self.page_token, "page_token")
        if self.label_ids not in ((), ("SPAM",)):
            raise ValueError("message listing supports only normal or SPAM inventory")
        if not isinstance(self.include_spam_trash, bool):
            raise TypeError("include_spam_trash must be a bool")
        if self.include_spam_trash != (self.label_ids == ("SPAM",)):
            raise ValueError("include_spam_trash is reserved for the SPAM branch")
        if isinstance(self.max_results, bool) or not isinstance(self.max_results, int):
            raise TypeError("max_results must be an integer")
        if not 1 <= self.max_results <= GMAIL_LIST_PAGE_LIMIT:
            raise ValueError("max_results exceeds the read-only page limit")


@dataclass(frozen=True, slots=True)
class MessageMetadataRequest:
    message_id: str = field(repr=False)
    user_id: str = field(default="me", init=False)
    format: MetadataFormat = field(default=MetadataFormat.METADATA, init=False)
    metadata_headers: tuple[str, ...] = field(default=GMAIL_METADATA_HEADERS, init=False)

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.message_id, "message_id")

    def __repr__(self) -> str:
        return (
            "MessageMetadataRequest(message_id=<redacted>, user_id='me', "
            "format='METADATA', metadata_headers=<approved>)"
        )


@dataclass(frozen=True, slots=True)
class HistoryRequest:
    start_history_id: str = field(repr=False)
    page_token: str | None = field(default=None, repr=False)
    max_results: int = GMAIL_LIST_PAGE_LIMIT
    user_id: str = field(default="me", init=False)

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.start_history_id, "start_history_id")
        _optional_non_empty(self.page_token, "page_token")
        if isinstance(self.max_results, bool) or not isinstance(self.max_results, int):
            raise TypeError("max_results must be an integer")
        if not 1 <= self.max_results <= GMAIL_LIST_PAGE_LIMIT:
            raise ValueError("max_results exceeds the read-only page limit")


@dataclass(frozen=True, slots=True)
class ProfileResponse:
    account_address: str = field(repr=False)
    history_id: str = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_address", normalize_account_address(self.account_address)
        )
        validate_opaque_identifier(self.history_id, "history_id")

    def __repr__(self) -> str:
        return "ProfileResponse(account_address=<redacted>, history_id=<redacted>)"


@dataclass(frozen=True, slots=True)
class LabelRef:
    label_id: str = field(repr=False)

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.label_id, "label_id")

    def __repr__(self) -> str:
        return "LabelRef(label_id=<redacted>)"


@dataclass(frozen=True, slots=True)
class LabelListResponse:
    labels: tuple[LabelRef, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.labels, tuple) or any(
            not isinstance(label, LabelRef) for label in self.labels
        ):
            raise TypeError("labels must be a tuple of LabelRef values")
        identities = tuple(label.label_id for label in self.labels)
        if len(set(identities)) != len(identities):
            raise ValueError("labels must not contain duplicate IDs")

    def __repr__(self) -> str:
        return f"LabelListResponse(count={len(self.labels)})"


@dataclass(frozen=True, slots=True)
class MessageRef:
    message_id: str = field(repr=False)

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.message_id, "message_id")

    def __repr__(self) -> str:
        return "MessageRef(message_id=<redacted>)"


@dataclass(frozen=True, slots=True)
class MessageListPage:
    messages: tuple[MessageRef, ...] = field(repr=False)
    next_page_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.messages, tuple) or any(
            not isinstance(message, MessageRef) for message in self.messages
        ):
            raise TypeError("messages must be a tuple of MessageRef values")
        if len(self.messages) > GMAIL_LIST_PAGE_LIMIT:
            raise ValueError("message page exceeds the read-only page limit")
        identities = tuple(message.message_id for message in self.messages)
        if len(set(identities)) != len(identities):
            raise ValueError("message page must not contain duplicate IDs")
        _optional_non_empty(self.next_page_token, "next_page_token")

    def __repr__(self) -> str:
        return (
            f"MessageListPage(count={len(self.messages)}, "
            f"has_next={self.next_page_token is not None})"
        )


@dataclass(frozen=True, slots=True)
class MetadataHeader:
    name: str
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.value, str):
            raise TypeError("metadata header name and value must be strings")
        canonical = {
            approved.casefold(): approved for approved in GMAIL_METADATA_HEADERS
        }.get(self.name.casefold())
        if canonical is None:
            raise ValueError("metadata header is outside the approved allowlist")
        if len(self.value.encode("utf-8")) > GMAIL_HEADER_VALUE_LIMIT_BYTES:
            raise InventoryError(InventoryErrorCode.HEADER_LIMIT_EXCEEDED)
        object.__setattr__(self, "name", canonical)

    def __repr__(self) -> str:
        return f"MetadataHeader(name={self.name!r}, value=<redacted>)"


@dataclass(frozen=True, slots=True)
class MessageMetadata:
    message_id: str = field(repr=False)
    thread_id: str = field(repr=False)
    received_at: datetime
    label_ids: tuple[str, ...] = field(repr=False)
    size_estimate_bytes: int
    headers: tuple[MetadataHeader, ...] = field(repr=False)

    def __post_init__(self) -> None:
        validate_opaque_identifier(self.message_id, "message_id")
        validate_opaque_identifier(self.thread_id, "thread_id")
        object.__setattr__(
            self, "received_at", _utc_datetime(self.received_at, "received_at")
        )
        object.__setattr__(self, "label_ids", _canonical_labels(self.label_ids))
        _strict_non_negative(self.size_estimate_bytes, "size_estimate_bytes")
        if not isinstance(self.headers, tuple) or any(
            not isinstance(header, MetadataHeader) for header in self.headers
        ):
            raise TypeError("headers must be a tuple of MetadataHeader values")
        header_names = tuple(header.name for header in self.headers)
        if len(set(header_names)) != len(header_names):
            raise ValueError("metadata headers must not contain duplicate names")
        total_bytes = sum(len(header.value.encode("utf-8")) for header in self.headers)
        if total_bytes > GMAIL_HEADER_TOTAL_LIMIT_BYTES:
            raise InventoryError(InventoryErrorCode.HEADER_LIMIT_EXCEEDED)

    def __repr__(self) -> str:
        return (
            "MessageMetadata(message_id=<redacted>, thread_id=<redacted>, "
            f"received_at={self.received_at!r}, label_count={len(self.label_ids)}, "
            f"size_estimate_bytes={self.size_estimate_bytes}, headers=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class HistoryChange:
    kind: HistoryChangeKind
    message_id: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, HistoryChangeKind):
            raise TypeError("kind must be a HistoryChangeKind")
        validate_opaque_identifier(self.message_id, "message_id")

    def __repr__(self) -> str:
        return f"HistoryChange(kind={self.kind.value!r}, message_id=<redacted>)"


@dataclass(frozen=True, slots=True)
class HistoryPage:
    changes: tuple[HistoryChange, ...] = field(repr=False)
    history_id: str = field(repr=False)
    next_page_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.changes, tuple) or any(
            not isinstance(change, HistoryChange) for change in self.changes
        ):
            raise TypeError("changes must be a tuple of HistoryChange values")
        identities = tuple((change.kind, change.message_id) for change in self.changes)
        if len(set(identities)) != len(identities):
            raise ValueError("history page must not contain duplicate changes")
        validate_opaque_identifier(self.history_id, "history_id")
        _optional_non_empty(self.next_page_token, "next_page_token")

    def __repr__(self) -> str:
        return (
            f"HistoryPage(change_count={len(self.changes)}, history_id=<redacted>, "
            f"has_next={self.next_page_token is not None})"
        )


@dataclass(frozen=True, slots=True)
class InventoryResult:
    mode: SyncMode
    outcome: InventoryOutcome
    processed_count: int
    checkpoint: SyncCheckpoint = field(repr=False)
    checkpoint_persisted: bool
    error_code: InventoryErrorCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SyncMode):
            raise TypeError("mode must be a SyncMode")
        if not isinstance(self.outcome, InventoryOutcome):
            raise TypeError("outcome must be an InventoryOutcome")
        _strict_non_negative(self.processed_count, "processed_count")
        if not isinstance(self.checkpoint, SyncCheckpoint):
            raise TypeError("checkpoint must be a SyncCheckpoint")
        if self.checkpoint.mode is not self.mode:
            raise ValueError("result mode must match checkpoint mode")
        if not isinstance(self.checkpoint_persisted, bool):
            raise TypeError("checkpoint_persisted must be a bool")
        if self.error_code is not None and not isinstance(
            self.error_code, InventoryErrorCode
        ):
            raise TypeError("error_code must be an InventoryErrorCode or None")
        required_states = {
            InventoryOutcome.COMPLETED: SyncState.COMPLETED,
            InventoryOutcome.PAUSED: SyncState.PAUSED,
            InventoryOutcome.REQUIRES_FULL_RESYNC: SyncState.REQUIRES_FULL_RESYNC,
            InventoryOutcome.FAILED: SyncState.FAILED,
        }
        required = required_states.get(self.outcome)
        if required is not None and self.checkpoint.state is not required:
            raise ValueError("result outcome must match checkpoint state")
        if self.outcome in (InventoryOutcome.FAILED, InventoryOutcome.REQUIRES_FULL_RESYNC):
            if self.error_code is None:
                raise ValueError("failed results must contain a controlled error code")
        elif self.error_code is not None:
            raise ValueError("successful or interrupted results must not contain an error code")

    def __repr__(self) -> str:
        return (
            f"InventoryResult(mode={self.mode.value!r}, outcome={self.outcome.value!r}, "
            f"processed_count={self.processed_count}, checkpoint=<redacted>, "
            f"checkpoint_persisted={self.checkpoint_persisted!r}, "
            f"error_code={self.error_code.value if self.error_code else None!r})"
        )
