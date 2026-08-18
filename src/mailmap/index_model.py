from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

INDEX_RECORD_VERSION = 1

_EMAIL_LIKE = re.compile(r"^[^@\s]+@[^@\s]+$")
_ERROR_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_AUTH_RESULTS = frozenset({"pass", "fail", "neutral", "unknown"})


def validate_account_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("account_key must be a string")
    if not value or value != value.strip():
        raise ValueError("account_key must be a non-empty opaque identifier")
    if "@" in value or _EMAIL_LIKE.fullmatch(value):
        raise ValueError("account_key must not have the form of an email address")
    return value


def validate_opaque_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty opaque identifier")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or None")
    return value


def _optional_opaque_identifier(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return validate_opaque_identifier(value, field_name)


class SyncMode(StrEnum):
    FULL = "full"
    PARTIAL = "partial"


class SyncState(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    REQUIRES_FULL_RESYNC = "requires_full_resync"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class IndexedMessageRecord:
    account_key: str
    provider_message_id: str
    provider_thread_id: str
    received_at: datetime
    sender_name: str | None
    sender_address: str | None
    subject: str | None
    label_ids: tuple[str, ...]
    category: str | None
    size_estimate_bytes: int
    authenticated_domain: str | None
    list_id: str | None
    list_unsubscribe: str | None
    list_unsubscribe_post: str | None
    dkim_result: str | None
    dmarc_result: str | None
    record_version: int = INDEX_RECORD_VERSION

    def __post_init__(self) -> None:
        validate_account_key(self.account_key)
        validate_opaque_identifier(self.provider_message_id, "provider_message_id")
        validate_opaque_identifier(self.provider_thread_id, "provider_thread_id")
        object.__setattr__(
            self, "received_at", _utc_datetime(self.received_at, "received_at")
        )

        for field_name in (
            "sender_name",
            "sender_address",
            "subject",
            "category",
            "authenticated_domain",
            "list_id",
            "list_unsubscribe",
            "list_unsubscribe_post",
        ):
            _optional_text(getattr(self, field_name), field_name)

        if not isinstance(self.label_ids, tuple):
            raise TypeError("label_ids must be a tuple")
        for label_id in self.label_ids:
            validate_opaque_identifier(label_id, "label_ids item")
        object.__setattr__(self, "label_ids", tuple(sorted(set(self.label_ids))))

        if isinstance(self.size_estimate_bytes, bool) or not isinstance(
            self.size_estimate_bytes, int
        ):
            raise TypeError("size_estimate_bytes must be an integer")
        if self.size_estimate_bytes < 0:
            raise ValueError("size_estimate_bytes must be greater than or equal to zero")

        for field_name in ("dkim_result", "dmarc_result"):
            value = getattr(self, field_name)
            if value is not None and value not in _AUTH_RESULTS:
                raise ValueError(
                    f"{field_name} must be pass, fail, neutral, unknown, or None"
                )

        if isinstance(self.record_version, bool) or self.record_version != INDEX_RECORD_VERSION:
            raise ValueError(f"record_version must be {INDEX_RECORD_VERSION}")


@dataclass(frozen=True, slots=True)
class SyncCheckpoint:
    account_key: str
    scan_id: str
    mode: SyncMode
    state: SyncState
    page_token: str | None
    history_id: str | None
    processed_count: int
    started_at: datetime | None
    updated_at: datetime
    error_code: str | None

    def __post_init__(self) -> None:
        validate_account_key(self.account_key)
        validate_opaque_identifier(self.scan_id, "scan_id")
        if not isinstance(self.mode, SyncMode):
            raise ValueError("mode must be a SyncMode")
        if not isinstance(self.state, SyncState):
            raise ValueError("state must be a SyncState")

        page_token = _optional_opaque_identifier(self.page_token, "page_token")
        _optional_opaque_identifier(self.history_id, "history_id")
        if self.state is SyncState.COMPLETED and page_token is not None:
            raise ValueError("completed checkpoints must not contain a page_token")
        if self.state is SyncState.REQUIRES_FULL_RESYNC:
            object.__setattr__(self, "page_token", None)

        if isinstance(self.processed_count, bool) or not isinstance(self.processed_count, int):
            raise TypeError("processed_count must be an integer")
        if self.processed_count < 0:
            raise ValueError("processed_count must be greater than or equal to zero")

        if self.started_at is not None:
            object.__setattr__(
                self, "started_at", _utc_datetime(self.started_at, "started_at")
            )
        object.__setattr__(self, "updated_at", _utc_datetime(self.updated_at, "updated_at"))

        if self.error_code is not None:
            if not isinstance(self.error_code, str):
                raise TypeError("error_code must be a string or None")
            if not _ERROR_CODE.fullmatch(self.error_code):
                raise ValueError("error_code must be a controlled code")
