from __future__ import annotations

import base64
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from email.utils import parseaddr
from functools import partial
from typing import Protocol, TypeVar, cast

from mailmap.gmail_inventory_model import (
    FullScanPhase,
    HistoryChange,
    HistoryChangeKind,
    HistoryPage,
    HistoryRequest,
    InventoryError,
    InventoryErrorCode,
    InventoryOutcome,
    InventoryResult,
    InventorySession,
    InventoryTransportError,
    LabelListResponse,
    LabelRef,
    LabelsRequest,
    MessageListPage,
    MessageListRequest,
    MessageMetadata,
    MessageMetadataRequest,
    MessageRef,
    MetadataHeader,
    ProfileRequest,
    ProfileResponse,
    RemoteErrorCode,
)
from mailmap.gmail_readonly_policy import (
    EXCLUDED_SYSTEM_LABELS,
    GMAIL_METADATA_HEADERS,
    GMAIL_RETRY_ATTEMPT_LIMIT,
    GMAIL_RETRY_DELAY_LIMIT_SECONDS,
    RETRYABLE_HTTP_STATUSES,
)
from mailmap.index_model import (
    IndexedMessageRecord,
    SyncCheckpoint,
    SyncMode,
    SyncState,
    validate_opaque_identifier,
)

T = TypeVar("T")

_FULL_CURSOR_PREFIX = "mailcleanup-full-v1"
_PARTIAL_CURSOR_PREFIX = "mailcleanup-partial-v1"
_RETRYABLE_REMOTE_CODES = frozenset(
    {
        RemoteErrorCode.RATE_LIMITED,
        RemoteErrorCode.USER_RATE_LIMIT_EXCEEDED,
        RemoteErrorCode.QUOTA_EXCEEDED,
        RemoteErrorCode.BACKEND_ERROR,
    }
)
_NON_PERSISTABLE_FAILURES = frozenset(
    {
        InventoryErrorCode.IDENTITY_MISMATCH,
        InventoryErrorCode.CHECKPOINT_INVALID,
        InventoryErrorCode.CHECKPOINT_MISSING,
        InventoryErrorCode.PERSISTENCE_FAILED,
        InventoryErrorCode.CLOCK_INVALID,
        InventoryErrorCode.CONTROL_INVALID,
    }
)
_AUTH_RESULT = re.compile(r"(?:^|[;\s])(?P<kind>dkim|dmarc)\s*=\s*(?P<value>[a-z]+)", re.I)
_DKIM_DOMAIN = re.compile(r"(?:^|[;\s])header\.d\s*=\s*(?P<domain>[a-z0-9.-]+)", re.I)
_ALLOWED_AUTH_RESULTS = frozenset({"pass", "fail", "neutral"})
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class GmailInventoryTransport(Protocol):
    def get_profile(self, request: ProfileRequest) -> ProfileResponse: ...

    def list_labels(self, request: LabelsRequest) -> LabelListResponse: ...

    def list_messages(self, request: MessageListRequest) -> MessageListPage: ...

    def get_message_metadata(self, request: MessageMetadataRequest) -> MessageMetadata: ...

    def list_history(self, request: HistoryRequest) -> HistoryPage: ...


class InventoryIndex(Protocol):
    def apply_index_page(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        deleted_message_ids: Iterable[str],
        checkpoint: SyncCheckpoint,
    ) -> None: ...

    def start_full_index(
        self, account_key: str, checkpoint: SyncCheckpoint
    ) -> None: ...

    def sync_checkpoint(self, account_key: str) -> SyncCheckpoint | None: ...


class _Cancelled(Exception):
    pass


class _Paused(Exception):
    pass


class _HistoryExpired(Exception):
    pass


def _invalid_response() -> InventoryError:
    return InventoryError(InventoryErrorCode.INVALID_RESPONSE)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _invalid_response()
    return cast(Mapping[str, object], value)


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise _invalid_response()
    return cast(Sequence[object], value)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise _invalid_response()
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _text(value)


def _strict_non_negative_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _invalid_response()
    return value


def _boundary(factory: Callable[[], T]) -> T:
    try:
        return factory()
    except InventoryError:
        raise
    except (OverflowError, OSError, TypeError, ValueError):
        raise _invalid_response() from None


def parse_profile_response(payload: Mapping[str, object]) -> ProfileResponse:
    data = _mapping(payload)
    return _boundary(
        lambda: ProfileResponse(
            account_address=_text(data.get("emailAddress")),
            history_id=_text(data.get("historyId")),
        )
    )


def parse_label_list_response(payload: Mapping[str, object]) -> LabelListResponse:
    data = _mapping(payload)

    def build() -> LabelListResponse:
        raw_labels = data.get("labels", ())
        labels = tuple(
            LabelRef(label_id=_text(_mapping(raw_label).get("id")))
            for raw_label in _sequence(raw_labels)
        )
        return LabelListResponse(labels=labels)

    return _boundary(build)


def parse_message_list_page(payload: Mapping[str, object]) -> MessageListPage:
    data = _mapping(payload)

    def build() -> MessageListPage:
        raw_messages = data.get("messages", ())
        messages = tuple(
            MessageRef(message_id=_text(_mapping(raw_message).get("id")))
            for raw_message in _sequence(raw_messages)
        )
        return MessageListPage(
            messages=messages,
            next_page_token=_optional_text(data.get("nextPageToken")),
        )

    return _boundary(build)


def _received_at_from_milliseconds(value: object) -> datetime:
    text = _text(value)
    if not text.isdecimal():
        raise _invalid_response()
    return datetime.fromtimestamp(int(text) / 1000, tz=UTC)


def parse_message_metadata(payload: Mapping[str, object]) -> MessageMetadata:
    data = _mapping(payload)

    def build() -> MessageMetadata:
        raw_labels = _sequence(data.get("labelIds", ()))
        labels = tuple(_text(label) for label in raw_labels)
        raw_payload = _mapping(data.get("payload"))
        raw_headers = _sequence(raw_payload.get("headers", ()))
        approved = {name.casefold() for name in GMAIL_METADATA_HEADERS}
        headers: list[MetadataHeader] = []
        for raw_header in raw_headers:
            header = _mapping(raw_header)
            name = _text(header.get("name"))
            if name.casefold() not in approved:
                continue
            value = header.get("value")
            if not isinstance(value, str):
                raise _invalid_response()
            headers.append(MetadataHeader(name=name, value=value))
        return MessageMetadata(
            message_id=_text(data.get("id")),
            thread_id=_text(data.get("threadId")),
            received_at=_received_at_from_milliseconds(data.get("internalDate")),
            label_ids=labels,
            size_estimate_bytes=_strict_non_negative_integer(data.get("sizeEstimate")),
            headers=tuple(headers),
        )

    return _boundary(build)


def parse_history_page(payload: Mapping[str, object]) -> HistoryPage:
    data = _mapping(payload)

    def build() -> HistoryPage:
        changes: list[HistoryChange] = []
        seen: set[tuple[HistoryChangeKind, str]] = set()
        fields = (
            ("messagesAdded", HistoryChangeKind.ADDED),
            ("labelsAdded", HistoryChangeKind.LABELS_CHANGED),
            ("labelsRemoved", HistoryChangeKind.LABELS_CHANGED),
            ("messagesDeleted", HistoryChangeKind.DELETED),
        )
        for raw_history in _sequence(data.get("history", ())):
            history = _mapping(raw_history)
            for field_name, kind in fields:
                for raw_event in _sequence(history.get(field_name, ())):
                    event = _mapping(raw_event)
                    message = _mapping(event.get("message"))
                    message_id = _text(message.get("id"))
                    identity = (kind, message_id)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    changes.append(HistoryChange(kind=kind, message_id=message_id))
        return HistoryPage(
            changes=tuple(changes),
            history_id=_text(data.get("historyId")),
            next_page_token=_optional_text(data.get("nextPageToken")),
        )

    return _boundary(build)


def _encode_cursor(prefix: str, token: str | None) -> str:
    encoded = "-"
    if token is not None:
        encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")
    return f"{prefix}:{encoded}"


def _decode_cursor(prefix: str, value: str) -> str | None:
    expected = f"{prefix}:"
    if not value.startswith(expected):
        raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
    encoded = value.removeprefix(expected)
    if encoded == "-":
        return None
    if not encoded:
        raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
    try:
        decoded = base64.b64decode(encoded, altchars=b"-_", validate=True).decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID) from None
    if not decoded or decoded != decoded.strip():
        raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
    return decoded


def _encode_full_cursor(phase: FullScanPhase, token: str | None) -> str:
    return _encode_cursor(f"{_FULL_CURSOR_PREFIX}:{phase.value}", token)


def _decode_full_cursor(value: str) -> tuple[FullScanPhase, str | None]:
    for phase in FullScanPhase:
        prefix = f"{_FULL_CURSOR_PREFIX}:{phase.value}"
        if value.startswith(f"{prefix}:"):
            return phase, _decode_cursor(prefix, value)
    raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)


def _normalized_authentication(
    value: str | None,
) -> tuple[str | None, str | None, str | None]:
    if value is None:
        return None, None, None
    results: dict[str, str] = {}
    for match in _AUTH_RESULT.finditer(value):
        kind = match.group("kind").casefold()
        raw_result = match.group("value").casefold()
        results.setdefault(
            kind, raw_result if raw_result in _ALLOWED_AUTH_RESULTS else "unknown"
        )
    dkim_result = results.get("dkim")
    dmarc_result = results.get("dmarc")
    authenticated_domain: str | None = None
    if dkim_result == "pass" and (domain_match := _DKIM_DOMAIN.search(value)) is not None:
        authenticated_domain = domain_match.group("domain").casefold().rstrip(".") or None
    return dkim_result, dmarc_result, authenticated_domain


def _normalize_index_record(
    account_key: str, metadata: MessageMetadata
) -> IndexedMessageRecord:
    values = {header.name: header.value for header in metadata.headers}
    sender_name: str | None = None
    sender_address: str | None = None
    if (from_value := values.get("From")) is not None:
        parsed_name, parsed_address = parseaddr(from_value)
        normalized_address = parsed_address.strip().casefold()
        if normalized_address and "@" in normalized_address:
            sender_address = normalized_address
            sender_name = parsed_name.strip() or None
    categories = sorted(
        label_id.removeprefix("CATEGORY_").casefold()
        for label_id in metadata.label_ids
        if label_id.startswith("CATEGORY_") and label_id != "CATEGORY_"
    )
    category = categories[0] if len(categories) == 1 else None
    dkim_result, dmarc_result, authenticated_domain = _normalized_authentication(
        values.get("Authentication-Results")
    )
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=metadata.message_id,
        provider_thread_id=metadata.thread_id,
        received_at=metadata.received_at,
        sender_name=sender_name,
        sender_address=sender_address,
        subject=values.get("Subject"),
        label_ids=metadata.label_ids,
        category=category,
        size_estimate_bytes=metadata.size_estimate_bytes,
        authenticated_domain=authenticated_domain,
        list_id=values.get("List-ID"),
        list_unsubscribe=values.get("List-Unsubscribe"),
        list_unsubscribe_post=values.get("List-Unsubscribe-Post"),
        dkim_result=dkim_result,
        dmarc_result=dmarc_result,
    )


class GmailReadonlyInventory:
    def __init__(
        self,
        transport: GmailInventoryTransport,
        index: InventoryIndex,
        *,
        clock: Callable[[], datetime],
        sleeper: Callable[[float], None],
        jitter: Callable[[float], float],
        cancelled: Callable[[], bool],
        pause_requested: Callable[[], bool],
    ) -> None:
        self._transport = transport
        self._index = index
        self._clock = clock
        self._sleeper = sleeper
        self._jitter = jitter
        self._cancelled = cancelled
        self._pause_requested = pause_requested

    def _now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise InventoryError(InventoryErrorCode.CLOCK_INVALID) from None
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise InventoryError(InventoryErrorCode.CLOCK_INVALID)
        return value.astimezone(UTC)

    @staticmethod
    def _flag(callback: Callable[[], bool]) -> bool:
        try:
            value = callback()
        except Exception:
            raise InventoryError(InventoryErrorCode.CONTROL_INVALID) from None
        if not isinstance(value, bool):
            raise InventoryError(InventoryErrorCode.CONTROL_INVALID)
        return value

    def _before_remote(self) -> None:
        if self._flag(self._cancelled):
            raise _Cancelled
        if self._flag(self._pause_requested):
            raise _Paused

    def _before_persist(self) -> None:
        if self._flag(self._cancelled):
            raise _Cancelled

    def _is_pause_requested(self) -> bool:
        return self._flag(self._pause_requested)

    def _retry_delay(self, attempt: int) -> float:
        base_delay = float(2 ** (attempt - 1))
        try:
            jitter = self._jitter(base_delay)
        except Exception:
            raise InventoryError(InventoryErrorCode.RETRY_POLICY_INVALID) from None
        if (
            isinstance(jitter, bool)
            or not isinstance(jitter, (int, float))
            or not math.isfinite(float(jitter))
            or jitter < 0
        ):
            raise InventoryError(InventoryErrorCode.RETRY_POLICY_INVALID)
        return min(base_delay + float(jitter), GMAIL_RETRY_DELAY_LIMIT_SECONDS)

    @staticmethod
    def _is_retryable(error: InventoryTransportError) -> bool:
        if error.code in (
            RemoteErrorCode.HISTORY_NOT_FOUND,
            RemoteErrorCode.PERMISSION_DENIED,
            RemoteErrorCode.INVALID_RESPONSE,
        ):
            return False
        return error.status in RETRYABLE_HTTP_STATUSES or error.code in _RETRYABLE_REMOTE_CODES

    @staticmethod
    def _transport_failure_code(error: InventoryTransportError) -> InventoryErrorCode:
        if error.status == 403 or error.code is RemoteErrorCode.PERMISSION_DENIED:
            return InventoryErrorCode.PERMISSION_DENIED
        if error.status == 404:
            return InventoryErrorCode.NOT_FOUND
        return InventoryErrorCode.TRANSPORT_FAILED

    def _remote(self, call: Callable[[], T], *, history: bool = False) -> T:
        for attempt in range(1, GMAIL_RETRY_ATTEMPT_LIMIT + 1):
            self._before_remote()
            try:
                return call()
            except InventoryTransportError as error:
                if history and error.status == 404:
                    raise _HistoryExpired from None
                if not self._is_retryable(error):
                    raise InventoryError(self._transport_failure_code(error)) from None
                if attempt == GMAIL_RETRY_ATTEMPT_LIMIT:
                    raise InventoryError(InventoryErrorCode.RETRY_EXHAUSTED) from None
                delay = self._retry_delay(attempt)
                self._before_remote()
                try:
                    self._sleeper(delay)
                except Exception:
                    raise InventoryError(InventoryErrorCode.RETRY_POLICY_INVALID) from None
            except InventoryError:
                raise
            except Exception:
                raise InventoryError(InventoryErrorCode.TRANSPORT_FAILED) from None
        raise InventoryError(InventoryErrorCode.RETRY_EXHAUSTED)

    def _profile(self, session: InventorySession) -> ProfileResponse:
        response = self._remote(lambda: self._transport.get_profile(ProfileRequest()))
        if not isinstance(response, ProfileResponse):
            raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)
        if response.account_address != session.identity.address:
            raise InventoryError(InventoryErrorCode.IDENTITY_MISMATCH)
        return response

    def _labels(self) -> None:
        response = self._remote(lambda: self._transport.list_labels(LabelsRequest()))
        if not isinstance(response, LabelListResponse):
            raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)

    def _read_checkpoint(self, account_key: str) -> SyncCheckpoint | None:
        try:
            return self._index.sync_checkpoint(account_key)
        except Exception:
            raise InventoryError(InventoryErrorCode.PERSISTENCE_FAILED) from None

    def _apply(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        deleted_message_ids: Iterable[str],
        checkpoint: SyncCheckpoint,
    ) -> None:
        self._before_persist()
        try:
            self._index.apply_index_page(
                account_key,
                records,
                deleted_message_ids,
                checkpoint,
            )
        except Exception:
            raise InventoryError(InventoryErrorCode.PERSISTENCE_FAILED) from None

    def _start_full(self, account_key: str, checkpoint: SyncCheckpoint) -> None:
        self._before_persist()
        try:
            self._index.start_full_index(account_key, checkpoint)
        except Exception:
            raise InventoryError(InventoryErrorCode.PERSISTENCE_FAILED) from None

    @staticmethod
    def _result(
        checkpoint: SyncCheckpoint,
        outcome: InventoryOutcome,
        *,
        persisted: bool,
        error_code: InventoryErrorCode | None = None,
    ) -> InventoryResult:
        return InventoryResult(
            mode=checkpoint.mode,
            outcome=outcome,
            processed_count=checkpoint.processed_count,
            checkpoint=checkpoint,
            checkpoint_persisted=persisted,
            error_code=error_code,
        )

    def _failed_result(
        self,
        checkpoint: SyncCheckpoint,
        error_code: InventoryErrorCode,
        *,
        identity_verified: bool,
    ) -> InventoryResult:
        try:
            updated_at = self._now()
        except InventoryError:
            updated_at = checkpoint.updated_at
        failed = replace(
            checkpoint,
            state=SyncState.FAILED,
            updated_at=updated_at,
            error_code=error_code.value,
        )
        persisted = False
        if identity_verified and error_code not in _NON_PERSISTABLE_FAILURES:
            try:
                self._apply(failed.account_key, (), (), failed)
                persisted = True
            except _Cancelled:
                return self._result(checkpoint, InventoryOutcome.CANCELLED, persisted=False)
            except InventoryError:
                failed = replace(
                    failed,
                    error_code=InventoryErrorCode.PERSISTENCE_FAILED.value,
                )
                error_code = InventoryErrorCode.PERSISTENCE_FAILED
        return self._result(
            failed,
            InventoryOutcome.FAILED,
            persisted=persisted,
            error_code=error_code,
        )

    def _paused_result(
        self,
        checkpoint: SyncCheckpoint,
        *,
        identity_verified: bool,
        persisted: bool,
    ) -> InventoryResult:
        paused = replace(
            checkpoint,
            state=SyncState.PAUSED,
            updated_at=self._now(),
            error_code=None,
        )
        if not identity_verified:
            return self._result(paused, InventoryOutcome.PAUSED, persisted=False)
        try:
            self._apply(paused.account_key, (), (), paused)
        except _Cancelled:
            return self._result(checkpoint, InventoryOutcome.CANCELLED, persisted=persisted)
        except InventoryError as error:
            return self._failed_result(
                paused,
                error.code,
                identity_verified=identity_verified,
            )
        return self._result(paused, InventoryOutcome.PAUSED, persisted=True)

    def _metadata(self, message_id: str) -> MessageMetadata:
        response = self._remote(
            lambda: self._transport.get_message_metadata(
                MessageMetadataRequest(message_id=message_id)
            )
        )
        if not isinstance(response, MessageMetadata) or response.message_id != message_id:
            raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)
        return response

    @staticmethod
    def _is_excluded(metadata: MessageMetadata) -> bool:
        return not EXCLUDED_SYSTEM_LABELS.isdisjoint(metadata.label_ids)

    def scan_full(self, session: InventorySession, scan_id: str) -> InventoryResult:
        validate_opaque_identifier(scan_id, "scan_id")
        try:
            started_at = self._now()
        except InventoryError as error:
            checkpoint = SyncCheckpoint(
                account_key=session.identity.account_key,
                scan_id=scan_id,
                mode=SyncMode.FULL,
                state=SyncState.NOT_STARTED,
                page_token=_encode_full_cursor(FullScanPhase.NORMAL, None),
                history_id=None,
                processed_count=0,
                started_at=None,
                updated_at=_EPOCH,
                error_code=None,
            )
            return self._failed_result(checkpoint, error.code, identity_verified=False)

        checkpoint = SyncCheckpoint(
            account_key=session.identity.account_key,
            scan_id=scan_id,
            mode=SyncMode.FULL,
            state=SyncState.NOT_STARTED,
            page_token=_encode_full_cursor(FullScanPhase.NORMAL, None),
            history_id=None,
            processed_count=0,
            started_at=started_at,
            updated_at=started_at,
            error_code=None,
        )
        persisted = False
        identity_verified = False
        try:
            profile = self._profile(session)
            identity_verified = True
            self._labels()
            existing = self._read_checkpoint(session.identity.account_key)
            if existing is not None and existing.scan_id == scan_id:
                if existing.mode is not SyncMode.FULL:
                    raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
                checkpoint = existing
                persisted = True
                if existing.state is SyncState.COMPLETED:
                    return self._result(existing, InventoryOutcome.COMPLETED, persisted=True)
                if existing.state not in (
                    SyncState.NOT_STARTED,
                    SyncState.RUNNING,
                    SyncState.PAUSED,
                    SyncState.FAILED,
                ):
                    raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
            else:
                checkpoint = replace(
                    checkpoint,
                    state=SyncState.RUNNING,
                    history_id=profile.history_id,
                )
                self._start_full(session.identity.account_key, checkpoint)
                persisted = True

            if checkpoint.page_token is None:
                raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
            phase, page_token = _decode_full_cursor(checkpoint.page_token)

            while True:
                request = MessageListRequest(
                    page_token=page_token,
                    label_ids=("SPAM",) if phase is FullScanPhase.SPAM else (),
                    include_spam_trash=phase is FullScanPhase.SPAM,
                )
                page = self._remote(partial(self._transport.list_messages, request))
                if not isinstance(page, MessageListPage):
                    raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)
                if page.next_page_token is not None and page.next_page_token == page_token:
                    raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)

                records: list[IndexedMessageRecord] = []
                for message in page.messages:
                    metadata = self._metadata(message.message_id)
                    if self._is_excluded(metadata):
                        continue
                    if phase is FullScanPhase.NORMAL and "SPAM" in metadata.label_ids:
                        continue
                    records.append(
                        _normalize_index_record(session.identity.account_key, metadata)
                    )

                completed = phase is FullScanPhase.SPAM and page.next_page_token is None
                if completed:
                    next_phase = FullScanPhase.SPAM
                    next_token = None
                    encoded_cursor = None
                elif page.next_page_token is not None:
                    next_phase = phase
                    next_token = page.next_page_token
                    encoded_cursor = _encode_full_cursor(next_phase, next_token)
                else:
                    next_phase = FullScanPhase.SPAM
                    next_token = None
                    encoded_cursor = _encode_full_cursor(next_phase, next_token)

                pause_after_page = self._is_pause_requested() and not completed
                state = (
                    SyncState.COMPLETED
                    if completed
                    else SyncState.PAUSED
                    if pause_after_page
                    else SyncState.RUNNING
                )
                next_checkpoint = replace(
                    checkpoint,
                    state=state,
                    page_token=encoded_cursor,
                    processed_count=checkpoint.processed_count + len(page.messages),
                    updated_at=self._now(),
                    error_code=None,
                )
                self._apply(
                    session.identity.account_key,
                    records,
                    (),
                    next_checkpoint,
                )
                checkpoint = next_checkpoint
                persisted = True
                if completed:
                    return self._result(checkpoint, InventoryOutcome.COMPLETED, persisted=True)
                if pause_after_page:
                    return self._result(checkpoint, InventoryOutcome.PAUSED, persisted=True)
                phase, page_token = next_phase, next_token
        except _Cancelled:
            return self._result(checkpoint, InventoryOutcome.CANCELLED, persisted=persisted)
        except _Paused:
            return self._paused_result(
                checkpoint,
                identity_verified=identity_verified,
                persisted=persisted,
            )
        except InventoryError as error:
            return self._failed_result(
                checkpoint,
                error.code,
                identity_verified=identity_verified,
            )

    def scan_partial(self, session: InventorySession, scan_id: str) -> InventoryResult:
        validate_opaque_identifier(scan_id, "scan_id")
        try:
            started_at = self._now()
        except InventoryError as error:
            checkpoint = SyncCheckpoint(
                account_key=session.identity.account_key,
                scan_id=scan_id,
                mode=SyncMode.PARTIAL,
                state=SyncState.NOT_STARTED,
                page_token=_encode_cursor(_PARTIAL_CURSOR_PREFIX, None),
                history_id=None,
                processed_count=0,
                started_at=None,
                updated_at=_EPOCH,
                error_code=None,
            )
            return self._failed_result(checkpoint, error.code, identity_verified=False)

        checkpoint = SyncCheckpoint(
            account_key=session.identity.account_key,
            scan_id=scan_id,
            mode=SyncMode.PARTIAL,
            state=SyncState.NOT_STARTED,
            page_token=_encode_cursor(_PARTIAL_CURSOR_PREFIX, None),
            history_id=None,
            processed_count=0,
            started_at=started_at,
            updated_at=started_at,
            error_code=None,
        )
        persisted = False
        identity_verified = False
        start_history_id: str | None = None
        try:
            self._profile(session)
            identity_verified = True
            self._labels()
            existing = self._read_checkpoint(session.identity.account_key)
            if existing is not None and existing.scan_id == scan_id:
                if existing.mode is not SyncMode.PARTIAL or existing.history_id is None:
                    raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
                checkpoint = existing
                persisted = True
                start_history_id = existing.history_id
                if existing.state is SyncState.COMPLETED:
                    return self._result(existing, InventoryOutcome.COMPLETED, persisted=True)
                if existing.state is SyncState.REQUIRES_FULL_RESYNC:
                    return self._result(
                        existing,
                        InventoryOutcome.REQUIRES_FULL_RESYNC,
                        persisted=True,
                        error_code=InventoryErrorCode.HISTORY_EXPIRED,
                    )
                if existing.state not in (
                    SyncState.NOT_STARTED,
                    SyncState.RUNNING,
                    SyncState.PAUSED,
                    SyncState.FAILED,
                ):
                    raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
            else:
                if (
                    existing is None
                    or existing.state is not SyncState.COMPLETED
                    or existing.history_id is None
                ):
                    raise InventoryError(InventoryErrorCode.CHECKPOINT_MISSING)
                start_history_id = existing.history_id
                checkpoint = replace(
                    checkpoint,
                    state=SyncState.RUNNING,
                    history_id=start_history_id,
                )
                self._apply(session.identity.account_key, (), (), checkpoint)
                persisted = True

            if checkpoint.page_token is None or start_history_id is None:
                raise InventoryError(InventoryErrorCode.CHECKPOINT_INVALID)
            page_token = _decode_cursor(_PARTIAL_CURSOR_PREFIX, checkpoint.page_token)

            while True:
                request = HistoryRequest(
                    start_history_id=start_history_id,
                    page_token=page_token,
                )
                try:
                    page = self._remote(
                        partial(self._transport.list_history, request), history=True
                    )
                except _HistoryExpired:
                    resync = replace(
                        checkpoint,
                        state=SyncState.REQUIRES_FULL_RESYNC,
                        page_token=None,
                        history_id=start_history_id,
                        updated_at=self._now(),
                        error_code=InventoryErrorCode.HISTORY_EXPIRED.value,
                    )
                    self._apply(session.identity.account_key, (), (), resync)
                    return self._result(
                        resync,
                        InventoryOutcome.REQUIRES_FULL_RESYNC,
                        persisted=True,
                        error_code=InventoryErrorCode.HISTORY_EXPIRED,
                    )
                if not isinstance(page, HistoryPage):
                    raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)
                if page.next_page_token is not None and page.next_page_token == page_token:
                    raise InventoryError(InventoryErrorCode.INVALID_RESPONSE)

                deleted_ids = {
                    change.message_id
                    for change in page.changes
                    if change.kind is HistoryChangeKind.DELETED
                }
                changed_ids = {
                    change.message_id
                    for change in page.changes
                    if change.kind is not HistoryChangeKind.DELETED
                } - deleted_ids
                records: list[IndexedMessageRecord] = []
                for message_id in sorted(changed_ids):
                    metadata = self._metadata(message_id)
                    if self._is_excluded(metadata):
                        deleted_ids.add(message_id)
                        continue
                    records.append(
                        _normalize_index_record(session.identity.account_key, metadata)
                    )

                completed = page.next_page_token is None
                next_token = page.next_page_token
                encoded_cursor = (
                    None
                    if completed
                    else _encode_cursor(_PARTIAL_CURSOR_PREFIX, next_token)
                )
                pause_after_page = self._is_pause_requested() and not completed
                state = (
                    SyncState.COMPLETED
                    if completed
                    else SyncState.PAUSED
                    if pause_after_page
                    else SyncState.RUNNING
                )
                next_checkpoint = replace(
                    checkpoint,
                    state=state,
                    page_token=encoded_cursor,
                    history_id=page.history_id if completed else start_history_id,
                    processed_count=(
                        checkpoint.processed_count + len(deleted_ids | changed_ids)
                    ),
                    updated_at=self._now(),
                    error_code=None,
                )
                self._apply(
                    session.identity.account_key,
                    records,
                    sorted(deleted_ids),
                    next_checkpoint,
                )
                checkpoint = next_checkpoint
                persisted = True
                if completed:
                    return self._result(checkpoint, InventoryOutcome.COMPLETED, persisted=True)
                if pause_after_page:
                    return self._result(checkpoint, InventoryOutcome.PAUSED, persisted=True)
                page_token = next_token
        except _Cancelled:
            return self._result(checkpoint, InventoryOutcome.CANCELLED, persisted=persisted)
        except _Paused:
            return self._paused_result(
                checkpoint,
                identity_verified=identity_verified,
                persisted=persisted,
            )
        except InventoryError as error:
            return self._failed_result(
                checkpoint,
                error.code,
                identity_verified=identity_verified,
            )
