from __future__ import annotations

import socket
import sqlite3
import urllib.request
import webbrowser
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from mailmap.gmail_inventory import (
    GmailReadonlyInventory,
    parse_history_page,
    parse_label_list_response,
    parse_message_list_page,
    parse_message_metadata,
    parse_profile_response,
)
from mailmap.gmail_inventory_model import (
    HistoryChange,
    HistoryChangeKind,
    HistoryPage,
    HistoryRequest,
    InventoryError,
    InventoryErrorCode,
    InventoryOutcome,
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
    MetadataFormat,
    MetadataHeader,
    ProfileRequest,
    ProfileResponse,
    RemoteErrorCode,
)
from mailmap.gmail_readonly_policy import GMAIL_LIST_PAGE_LIMIT, GMAIL_METADATA_HEADERS
from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint, SyncMode, SyncState
from mailmap.repository import Repository
from mailmap.session_model import GMAIL_METADATA_SCOPE, SessionIdentity

ACCOUNT_A = "11111111-1111-4111-8111-111111111111"
ACCOUNT_B = "22222222-2222-4222-8222-222222222222"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


class SyntheticTransport:
    def __init__(self) -> None:
        self.profile_response = ProfileResponse(
            account_address="persona@inventory.example",
            history_id="history-profile-synthetic",
        )
        self.labels_response = LabelListResponse(
            labels=(LabelRef("INBOX"), LabelRef("SPAM"), LabelRef("SENT"))
        )
        self.message_pages: dict[
            tuple[tuple[str, ...], str | None], MessageListPage
        ] = {
            ((), None): MessageListPage(messages=(), next_page_token=None),
            (("SPAM",), None): MessageListPage(messages=(), next_page_token=None),
        }
        self.metadata: dict[str, MessageMetadata] = {}
        self.history_pages: dict[str | None, HistoryPage] = {}
        self.profile_failures: list[InventoryTransportError] = []
        self.history_failures: list[InventoryTransportError] = []
        self.profile_requests: list[ProfileRequest] = []
        self.label_requests: list[LabelsRequest] = []
        self.message_list_requests: list[MessageListRequest] = []
        self.metadata_requests: list[MessageMetadataRequest] = []
        self.history_requests: list[HistoryRequest] = []
        self.on_metadata: Any = None

    def get_profile(self, request: ProfileRequest) -> ProfileResponse:
        self.profile_requests.append(request)
        if self.profile_failures:
            raise self.profile_failures.pop(0)
        return self.profile_response

    def list_labels(self, request: LabelsRequest) -> LabelListResponse:
        self.label_requests.append(request)
        return self.labels_response

    def list_messages(self, request: MessageListRequest) -> MessageListPage:
        self.message_list_requests.append(request)
        return self.message_pages[(request.label_ids, request.page_token)]

    def get_message_metadata(self, request: MessageMetadataRequest) -> MessageMetadata:
        self.metadata_requests.append(request)
        response = self.metadata[request.message_id]
        if self.on_metadata is not None:
            self.on_metadata()
        return response

    def list_history(self, request: HistoryRequest) -> HistoryPage:
        self.history_requests.append(request)
        if self.history_failures:
            raise self.history_failures.pop(0)
        return self.history_pages[request.page_token]


class Control:
    def __init__(self) -> None:
        self.cancelled = False
        self.paused = False

    def is_cancelled(self) -> bool:
        return self.cancelled

    def is_paused(self) -> bool:
        return self.paused


def _session(
    *, account_key: str = ACCOUNT_A, address: str = "persona@inventory.example"
) -> InventorySession:
    return InventorySession(
        identity=SessionIdentity(account_key=account_key, address=address),
        scopes=(GMAIL_METADATA_SCOPE,),
    )


def _metadata_payload(
    message_id: str,
    *,
    labels: tuple[str, ...] = ("INBOX",),
    subject: str = "Asunto sintético",
    sender: str = "Fuente Sintética <fuente@inventory.example>",
    size: int = 2048,
    extra_headers: tuple[dict[str, str], ...] = (),
) -> dict[str, object]:
    return {
        "id": message_id,
        "threadId": f"thread-{message_id}",
        "internalDate": str(int(NOW.timestamp() * 1000)),
        "labelIds": list(labels),
        "sizeEstimate": size,
        "snippet": "debe descartarse",
        "raw": "debe descartarse",
        "payload": {
            "mimeType": "text/html",
            "body": {"data": "debe descartarse"},
            "parts": [{"filename": "debe-descartarse.pdf"}],
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": subject},
                {"name": "List-ID", "value": "lista.inventory.example"},
                {
                    "name": "List-Unsubscribe",
                    "value": "https://inventory.example/unsubscribe/synthetic",
                },
                {
                    "name": "List-Unsubscribe-Post",
                    "value": "List-Unsubscribe=One-Click",
                },
                {
                    "name": "Authentication-Results",
                    "value": (
                        "mx.inventory.example; dkim=pass header.d=inventory.example; "
                        "dmarc=pass"
                    ),
                },
                {"name": "To", "value": "destino@inventory.example"},
                {"name": "Message-ID", "value": "discarded-synthetic"},
                *extra_headers,
            ],
        },
        "unexpected": {"nested": "discarded"},
    }


def _metadata(
    message_id: str,
    *,
    labels: tuple[str, ...] = ("INBOX",),
    subject: str = "Asunto sintético",
    size: int = 2048,
) -> MessageMetadata:
    return parse_message_metadata(
        _metadata_payload(
            message_id,
            labels=labels,
            subject=subject,
            size=size,
        )
    )


def _service(
    transport: SyntheticTransport,
    repository: Repository,
    *,
    control: Control | None = None,
    cancelled: Any = None,
    sleeps: list[float] | None = None,
    jitter: Any = None,
) -> GmailReadonlyInventory:
    active_control = control or Control()
    recorded_sleeps = sleeps if sleeps is not None else []
    return GmailReadonlyInventory(
        transport,
        repository,
        clock=lambda: NOW,
        sleeper=recorded_sleeps.append,
        jitter=jitter or (lambda _delay: 0.0),
        cancelled=cancelled or active_control.is_cancelled,
        pause_requested=active_control.is_paused,
    )


def _indexed_record(
    message_id: str,
    *,
    account_key: str = ACCOUNT_A,
    subject: str = "Estado previo sintético",
) -> IndexedMessageRecord:
    return IndexedMessageRecord(
        account_key=account_key,
        provider_message_id=message_id,
        provider_thread_id=f"thread-{message_id}",
        received_at=NOW,
        sender_name="Fuente Sintética",
        sender_address="fuente@inventory.example",
        subject=subject,
        label_ids=("INBOX",),
        category=None,
        size_estimate_bytes=1024,
        authenticated_domain="inventory.example",
        list_id=None,
        list_unsubscribe=None,
        list_unsubscribe_post=None,
        dkim_result="pass",
        dmarc_result="pass",
    )


def _completed_checkpoint(
    *, account_key: str = ACCOUNT_A, scan_id: str = "full-seed-synthetic"
) -> SyncCheckpoint:
    return SyncCheckpoint(
        account_key=account_key,
        scan_id=scan_id,
        mode=SyncMode.FULL,
        state=SyncState.COMPLETED,
        page_token=None,
        history_id="history-consolidated-synthetic",
        processed_count=1,
        started_at=NOW - timedelta(minutes=5),
        updated_at=NOW,
        error_code=None,
    )


def test_models_are_closed_frozen_minimal_and_scope_locked() -> None:
    request = MessageListRequest()
    metadata_request = MessageMetadataRequest("message-synthetic-001")

    assert request.max_results == GMAIL_LIST_PAGE_LIMIT
    assert not hasattr(request, "q")
    assert not hasattr(request, "url")
    assert not hasattr(request, "method")
    assert metadata_request.format is MetadataFormat.METADATA
    assert metadata_request.metadata_headers == GMAIL_METADATA_HEADERS
    assert not hasattr(metadata_request, "fields")
    assert not hasattr(metadata_request, "scope")
    assert not hasattr(request, "__dict__")
    with pytest.raises(FrozenInstanceError):
        request.max_results = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        MessageMetadataRequest(
            "message-synthetic-001", format=MetadataFormat.METADATA  # type: ignore[call-arg]
        )
    with pytest.raises(ValueError, match="page limit"):
        MessageListRequest(max_results=GMAIL_LIST_PAGE_LIMIT + 1)
    with pytest.raises(ValueError, match="metadata scope"):
        InventorySession(identity=_session().identity, scopes=("synthetic.invalid",))


def test_boundary_discards_extra_fields_and_normalizes_only_approved_metadata() -> None:
    profile = parse_profile_response(
        {
            "emailAddress": "PERSONA@INVENTORY.EXAMPLE",
            "historyId": "history-synthetic",
            "messagesTotal": 999,
        }
    )
    labels = parse_label_list_response(
        {
            "labels": [
                {"id": "INBOX", "name": "Privado descartado", "color": {"x": "y"}}
            ],
            "extra": "discarded",
        }
    )
    page = parse_message_list_page(
        {
            "messages": [{"id": "message-synthetic-001", "threadId": "discarded"}],
            "resultSizeEstimate": 1,
        }
    )
    metadata = _metadata(
        "message-synthetic-001",
        labels=("STARRED", "INBOX", "STARRED", "CATEGORY_UPDATES"),
    )

    assert profile.account_address == "persona@inventory.example"
    assert labels.labels == (LabelRef("INBOX"),)
    assert page.messages == (MessageRef("message-synthetic-001"),)
    assert metadata.received_at == NOW
    assert metadata.label_ids == ("CATEGORY_UPDATES", "INBOX", "STARRED")
    assert tuple(header.name for header in metadata.headers) == GMAIL_METADATA_HEADERS
    assert not hasattr(metadata, "snippet")
    assert not hasattr(metadata, "raw")
    assert not hasattr(metadata, "mime_type")
    assert not hasattr(metadata, "attachments")
    assert not hasattr(metadata, "recipients")


def test_header_value_and_total_limits_fail_with_controlled_errors() -> None:
    with pytest.raises(InventoryError) as value_error:
        MetadataHeader(name="Subject", value="x" * (16 * 1024 + 1))
    assert value_error.value.code is InventoryErrorCode.HEADER_LIMIT_EXCEEDED

    headers = tuple(
        MetadataHeader(name=name, value="x" * 12_000)
        for name in GMAIL_METADATA_HEADERS
    )
    with pytest.raises(InventoryError) as total_error:
        MessageMetadata(
            message_id="message-synthetic-limits",
            thread_id="thread-synthetic-limits",
            received_at=NOW,
            label_ids=("INBOX",),
            size_estimate_bytes=1,
            headers=headers,
        )
    assert total_error.value.code is InventoryErrorCode.HEADER_LIMIT_EXCEEDED

    with pytest.raises(InventoryError) as boundary_error:
        parse_message_metadata(
            _metadata_payload(
                "message-synthetic-boundary",
                extra_headers=({"name": "Subject", "value": "duplicate"},),
            )
        )
    assert boundary_error.value.code is InventoryErrorCode.INVALID_RESPONSE


def test_dates_sizes_and_identifiers_are_strict_and_utc() -> None:
    local = datetime(2026, 8, 18, 9, 0, tzinfo=timezone(timedelta(hours=-3)))
    metadata = replace(
        _metadata("message-synthetic-validation"),
        received_at=local,
        label_ids=("IMPORTANT", "INBOX", "IMPORTANT"),
    )
    assert metadata.received_at == NOW
    assert metadata.label_ids == ("IMPORTANT", "INBOX")
    with pytest.raises(ValueError, match="timezone"):
        replace(metadata, received_at=datetime(2026, 8, 18, 12, 0))
    with pytest.raises(ValueError, match="greater than"):
        replace(metadata, size_estimate_bytes=-1)
    with pytest.raises(ValueError, match="non-empty"):
        replace(metadata, message_id="")


def test_full_scan_paginates_then_scans_spam_and_excludes_protected_system_labels(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "full.db")
    transport = SyntheticTransport()
    transport.message_pages = {
        ((), None): MessageListPage(
            messages=(MessageRef("message-normal-001"), MessageRef("message-sent")),
            next_page_token="page-normal-002",
        ),
        ((), "page-normal-002"): MessageListPage(
            messages=(MessageRef("message-normal-002"),),
            next_page_token=None,
        ),
        (("SPAM",), None): MessageListPage(
            messages=(MessageRef("message-spam"), MessageRef("message-spam-trash")),
            next_page_token=None,
        ),
    }
    transport.metadata = {
        "message-normal-001": _metadata("message-normal-001"),
        "message-normal-002": _metadata(
            "message-normal-002", labels=("CATEGORY_UPDATES", "INBOX")
        ),
        "message-sent": _metadata("message-sent", labels=("INBOX", "SENT")),
        "message-spam": _metadata("message-spam", labels=("SPAM",)),
        "message-spam-trash": _metadata(
            "message-spam-trash", labels=("SPAM", "TRASH")
        ),
    }

    result = _service(transport, repository).scan_full(
        _session(), "scan-full-synthetic"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
    assert result.processed_count == 5
    assert [
        record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)
    ] == ["message-normal-001", "message-normal-002", "message-spam"]
    normalized = {
        record.provider_message_id: record
        for record in repository.indexed_messages(ACCOUNT_A)
    }
    assert normalized["message-normal-001"].sender_address == "fuente@inventory.example"
    assert normalized["message-normal-001"].authenticated_domain == "inventory.example"
    assert normalized["message-normal-001"].dkim_result == "pass"
    assert normalized["message-normal-001"].dmarc_result == "pass"
    assert normalized["message-normal-002"].category == "updates"
    assert [
        (request.label_ids, request.include_spam_trash, request.page_token)
        for request in transport.message_list_requests
    ] == [
        ((), False, None),
        ((), False, "page-normal-002"),
        (("SPAM",), True, None),
    ]
    assert all(request.max_results == 500 for request in transport.message_list_requests)
    assert all(not hasattr(request, "q") for request in transport.message_list_requests)
    assert all(
        request.format is MetadataFormat.METADATA
        and request.metadata_headers == GMAIL_METADATA_HEADERS
        for request in transport.metadata_requests
    )
    checkpoint = repository.sync_checkpoint(ACCOUNT_A)
    assert checkpoint is not None
    assert checkpoint.state is SyncState.COMPLETED
    assert checkpoint.page_token is None
    assert checkpoint.history_id == "history-profile-synthetic"


def test_empty_full_scan_persists_final_checkpoint_without_records(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "empty.db")
    result = _service(SyntheticTransport(), repository).scan_full(
        _session(), "scan-empty-synthetic"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
    assert result.processed_count == 0
    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) == result.checkpoint


def test_new_full_scan_removes_records_missing_from_the_new_inventory(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "full-replacement.db")
    stale = _indexed_record("message-stale")
    repository.save_index_page(ACCOUNT_A, (stale,), _completed_checkpoint())

    result = _service(SyntheticTransport(), repository).scan_full(
        _session(), "scan-full-replacement-synthetic"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
    assert repository.indexed_messages(ACCOUNT_A) == ()
    assert repository.sync_checkpoint(ACCOUNT_A) == result.checkpoint


def test_page_and_checkpoint_roll_back_together_when_checkpoint_write_fails(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "rollback.db")
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_progress_checkpoint
            BEFORE UPDATE ON sync_checkpoints
            WHEN NEW.processed_count > 0
            BEGIN
                SELECT RAISE(ABORT, 'synthetic_progress_failure');
            END
            """
        )
    transport = SyntheticTransport()
    transport.message_pages[((), None)] = MessageListPage(
        messages=(MessageRef("message-atomic"),), next_page_token=None
    )
    transport.metadata["message-atomic"] = _metadata("message-atomic")

    result = _service(transport, repository).scan_full(
        _session(), "scan-rollback-synthetic"
    )

    assert result.outcome is InventoryOutcome.FAILED
    assert result.error_code is InventoryErrorCode.PERSISTENCE_FAILED
    assert result.checkpoint_persisted is False
    assert repository.indexed_messages(ACCOUNT_A) == ()
    durable = repository.sync_checkpoint(ACCOUNT_A)
    assert durable is not None
    assert durable.processed_count == 0
    assert durable.state is SyncState.RUNNING


def test_cancellation_after_a_page_resumes_without_duplicates(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "resume.db")
    transport = SyntheticTransport()
    transport.message_pages = {
        ((), None): MessageListPage(
            messages=(MessageRef("message-resume-001"),),
            next_page_token="page-resume-002",
        ),
        ((), "page-resume-002"): MessageListPage(
            messages=(MessageRef("message-resume-002"),), next_page_token=None
        ),
        (("SPAM",), None): MessageListPage(messages=(), next_page_token=None),
    }
    transport.metadata = {
        "message-resume-001": _metadata("message-resume-001"),
        "message-resume-002": _metadata("message-resume-002"),
    }

    def cancel_after_first_page() -> bool:
        checkpoint = repository.sync_checkpoint(ACCOUNT_A)
        return checkpoint is not None and checkpoint.processed_count == 1

    interrupted = _service(
        transport, repository, cancelled=cancel_after_first_page
    ).scan_full(_session(), "scan-resume-synthetic")
    resumed = _service(transport, repository).scan_full(
        _session(), "scan-resume-synthetic"
    )

    assert interrupted.outcome is InventoryOutcome.CANCELLED
    assert interrupted.processed_count == 1
    assert resumed.outcome is InventoryOutcome.COMPLETED
    assert resumed.processed_count == 2
    assert [
        record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)
    ] == ["message-resume-001", "message-resume-002"]
    assert [request.page_token for request in transport.message_list_requests] == [
        None,
        "page-resume-002",
        None,
    ]


def test_cancellation_is_checked_after_fetch_and_before_page_persistence(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "cancel-before-save.db")
    transport = SyntheticTransport()
    control = Control()
    transport.message_pages[((), None)] = MessageListPage(
        messages=(MessageRef("message-cancelled"),), next_page_token=None
    )
    transport.metadata["message-cancelled"] = _metadata("message-cancelled")
    transport.on_metadata = lambda: setattr(control, "cancelled", True)

    result = _service(transport, repository, control=control).scan_full(
        _session(), "scan-cancel-before-save"
    )

    assert result.outcome is InventoryOutcome.CANCELLED
    assert repository.indexed_messages(ACCOUNT_A) == ()
    durable = repository.sync_checkpoint(ACCOUNT_A)
    assert durable is not None
    assert durable.processed_count == 0


def test_pause_persists_an_atomic_resume_point(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "pause.db")
    transport = SyntheticTransport()
    control = Control()
    transport.message_pages[((), None)] = MessageListPage(
        messages=(MessageRef("message-paused"),), next_page_token=None
    )
    transport.metadata["message-paused"] = _metadata("message-paused")
    transport.on_metadata = lambda: setattr(control, "paused", True)

    paused = _service(transport, repository, control=control).scan_full(
        _session(), "scan-pause-synthetic"
    )
    control.paused = False
    transport.on_metadata = None
    resumed = _service(transport, repository, control=control).scan_full(
        _session(), "scan-pause-synthetic"
    )

    assert paused.outcome is InventoryOutcome.PAUSED
    assert paused.checkpoint.state is SyncState.PAUSED
    assert paused.processed_count == 1
    assert resumed.outcome is InventoryOutcome.COMPLETED
    assert [
        record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)
    ] == ["message-paused"]


def test_partial_sync_applies_add_label_change_delete_and_exclusion_per_account(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "partial.db")
    repository.save_index_page(
        ACCOUNT_A,
        (
            _indexed_record("message-updated"),
            _indexed_record("message-deleted"),
            _indexed_record("message-now-sent"),
        ),
        _completed_checkpoint(),
    )
    repository.save_index_page(
        ACCOUNT_B,
        (_indexed_record("message-deleted", account_key=ACCOUNT_B),),
        _completed_checkpoint(account_key=ACCOUNT_B, scan_id="full-seed-account-b"),
    )
    transport = SyntheticTransport()
    transport.history_pages[None] = HistoryPage(
        changes=(
            HistoryChange(HistoryChangeKind.ADDED, "message-new"),
            HistoryChange(HistoryChangeKind.LABELS_CHANGED, "message-updated"),
            HistoryChange(HistoryChangeKind.LABELS_CHANGED, "message-now-sent"),
            HistoryChange(HistoryChangeKind.DELETED, "message-deleted"),
        ),
        history_id="history-consolidated-new",
        next_page_token=None,
    )
    transport.metadata = {
        "message-new": _metadata("message-new", subject="Nuevo sintético"),
        "message-updated": _metadata(
            "message-updated", labels=("IMPORTANT", "INBOX"), subject="Actualizado"
        ),
        "message-now-sent": _metadata(
            "message-now-sent", labels=("INBOX", "SENT")
        ),
    }

    result = _service(transport, repository).scan_partial(
        _session(), "scan-partial-synthetic"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
    assert result.processed_count == 4
    account_a = {
        record.provider_message_id: record
        for record in repository.indexed_messages(ACCOUNT_A)
    }
    assert set(account_a) == {"message-new", "message-updated"}
    assert account_a["message-updated"].subject == "Actualizado"
    assert account_a["message-updated"].label_ids == ("IMPORTANT", "INBOX")
    assert [
        record.provider_message_id for record in repository.indexed_messages(ACCOUNT_B)
    ] == ["message-deleted"]
    checkpoint = repository.sync_checkpoint(ACCOUNT_A)
    assert checkpoint is not None
    assert checkpoint.mode is SyncMode.PARTIAL
    assert checkpoint.history_id == "history-consolidated-new"


def test_partial_checkpoint_failure_rolls_back_add_update_and_delete_together(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "partial-rollback.db")
    original_update = _indexed_record("message-updated")
    original_delete = _indexed_record("message-deleted")
    repository.save_index_page(
        ACCOUNT_A,
        (original_update, original_delete),
        _completed_checkpoint(),
    )
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_partial_progress_checkpoint
            BEFORE UPDATE ON sync_checkpoints
            WHEN NEW.processed_count > 0
            BEGIN
                SELECT RAISE(ABORT, 'synthetic_partial_progress_failure');
            END
            """
        )
    transport = SyntheticTransport()
    transport.history_pages[None] = HistoryPage(
        changes=(
            HistoryChange(HistoryChangeKind.ADDED, "message-added"),
            HistoryChange(HistoryChangeKind.LABELS_CHANGED, "message-updated"),
            HistoryChange(HistoryChangeKind.DELETED, "message-deleted"),
        ),
        history_id="history-after-failed-page",
        next_page_token=None,
    )
    transport.metadata = {
        "message-added": _metadata("message-added"),
        "message-updated": _metadata(
            "message-updated", subject="Cambio que debe revertirse"
        ),
    }

    result = _service(transport, repository).scan_partial(
        _session(), "scan-partial-rollback-synthetic"
    )

    assert result.outcome is InventoryOutcome.FAILED
    assert result.error_code is InventoryErrorCode.PERSISTENCE_FAILED
    assert repository.indexed_messages(ACCOUNT_A) == (
        original_delete,
        original_update,
    )
    durable = repository.sync_checkpoint(ACCOUNT_A)
    assert durable is not None
    assert durable.scan_id == "scan-partial-rollback-synthetic"
    assert durable.state is SyncState.RUNNING
    assert durable.processed_count == 0
    assert durable.error_code is None


def test_partial_sync_paginates_from_one_consolidated_history_id(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "partial-pages.db")
    repository.save_index_page(ACCOUNT_A, (), _completed_checkpoint())
    transport = SyntheticTransport()
    transport.history_pages = {
        None: HistoryPage(
            changes=(HistoryChange(HistoryChangeKind.ADDED, "message-page-001"),),
            history_id="history-new-synthetic",
            next_page_token="history-page-002",
        ),
        "history-page-002": HistoryPage(
            changes=(HistoryChange(HistoryChangeKind.ADDED, "message-page-002"),),
            history_id="history-new-synthetic",
            next_page_token=None,
        ),
    }
    transport.metadata = {
        "message-page-001": _metadata("message-page-001"),
        "message-page-002": _metadata("message-page-002"),
    }

    result = _service(transport, repository).scan_partial(
        _session(), "scan-partial-pages"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
    assert result.processed_count == 2
    assert [request.start_history_id for request in transport.history_requests] == [
        "history-consolidated-synthetic",
        "history-consolidated-synthetic",
    ]
    assert [request.page_token for request in transport.history_requests] == [
        None,
        "history-page-002",
    ]
    assert {
        record.provider_message_id for record in repository.indexed_messages(ACCOUNT_A)
    } == {"message-page-001", "message-page-002"}


def test_history_404_marks_requires_full_resync_without_partial_results(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "history-expired.db")
    existing = _indexed_record("message-preserved")
    repository.save_index_page(ACCOUNT_A, (existing,), _completed_checkpoint())
    transport = SyntheticTransport()
    transport.history_failures.append(
        InventoryTransportError(RemoteErrorCode.HISTORY_NOT_FOUND, status=404)
    )

    result = _service(transport, repository).scan_partial(
        _session(), "scan-history-expired"
    )

    assert result.outcome is InventoryOutcome.REQUIRES_FULL_RESYNC
    assert result.error_code is InventoryErrorCode.HISTORY_EXPIRED
    assert repository.indexed_messages(ACCOUNT_A) == (existing,)
    checkpoint = repository.sync_checkpoint(ACCOUNT_A)
    assert checkpoint is not None
    assert checkpoint.state is SyncState.REQUIRES_FULL_RESYNC
    assert checkpoint.page_token is None
    assert checkpoint.history_id == "history-consolidated-synthetic"


def test_history_boundary_flattens_only_supported_changes_and_discards_extras() -> None:
    page = parse_history_page(
        {
            "historyId": "history-new-synthetic",
            "history": [
                {
                    "id": "history-entry-discarded",
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "message-added",
                                "threadId": "discarded",
                                "snippet": "discarded",
                            }
                        }
                    ],
                    "labelsAdded": [
                        {
                            "message": {"id": "message-label"},
                            "labelIds": ["INBOX"],
                        }
                    ],
                    "labelsRemoved": [
                        {"message": {"id": "message-label"}, "labelIds": ["UNREAD"]}
                    ],
                    "messagesDeleted": [
                        {"message": {"id": "message-deleted", "payload": "discarded"}}
                    ],
                }
            ],
            "unexpected": "discarded",
        }
    )

    assert page.changes == (
        HistoryChange(HistoryChangeKind.ADDED, "message-added"),
        HistoryChange(HistoryChangeKind.LABELS_CHANGED, "message-label"),
        HistoryChange(HistoryChangeKind.DELETED, "message-deleted"),
    )
    assert not hasattr(page.changes[0], "snippet")
    assert not hasattr(page.changes[1], "label_ids")


def test_transient_retries_are_bounded_backed_off_and_use_injected_sleep(
    tmp_path: Path,
) -> None:
    repository = Repository(tmp_path / "retry.db")
    transport = SyntheticTransport()
    transport.profile_failures.extend(
        (
            InventoryTransportError(RemoteErrorCode.RATE_LIMITED, status=429),
            InventoryTransportError(RemoteErrorCode.BACKEND_ERROR, status=503),
        )
    )
    sleeps: list[float] = []

    result = _service(
        transport,
        repository,
        sleeps=sleeps,
        jitter=lambda _delay: 0.5,
    ).scan_full(_session(), "scan-retry-synthetic")

    assert result.outcome is InventoryOutcome.COMPLETED
    assert len(transport.profile_requests) == 3
    assert sleeps == [1.5, 2.5]
    assert all(delay <= 32 for delay in sleeps)


def test_retry_stops_after_five_attempts_and_permanent_errors_are_not_retried(
    tmp_path: Path,
) -> None:
    retry_repository = Repository(tmp_path / "retry-limit.db")
    retry_transport = SyntheticTransport()
    retry_transport.profile_failures.extend(
        InventoryTransportError(RemoteErrorCode.BACKEND_ERROR, status=503)
        for _ in range(5)
    )
    retry_sleeps: list[float] = []
    exhausted = _service(
        retry_transport, retry_repository, sleeps=retry_sleeps
    ).scan_full(_session(), "scan-retry-limit")

    permanent_repository = Repository(tmp_path / "permanent.db")
    permanent_transport = SyntheticTransport()
    permanent_transport.profile_failures.append(
        InventoryTransportError(RemoteErrorCode.PERMISSION_DENIED, status=403)
    )
    permanent_sleeps: list[float] = []
    permanent = _service(
        permanent_transport, permanent_repository, sleeps=permanent_sleeps
    ).scan_full(_session(), "scan-permanent-error")

    assert exhausted.outcome is InventoryOutcome.FAILED
    assert exhausted.error_code is InventoryErrorCode.RETRY_EXHAUSTED
    assert len(retry_transport.profile_requests) == 5
    assert retry_sleeps == [1.0, 2.0, 4.0, 8.0]
    assert permanent.outcome is InventoryOutcome.FAILED
    assert permanent.error_code is InventoryErrorCode.PERMISSION_DENIED
    assert len(permanent_transport.profile_requests) == 1
    assert permanent_sleeps == []


def test_identity_mismatch_never_reads_or_persists_the_index(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "identity.db")
    transport = SyntheticTransport()
    transport.profile_response = ProfileResponse(
        account_address="otra@inventory.example",
        history_id="history-other-synthetic",
    )

    result = _service(transport, repository).scan_full(
        _session(), "scan-identity-mismatch"
    )

    assert result.outcome is InventoryOutcome.FAILED
    assert result.error_code is InventoryErrorCode.IDENTITY_MISMATCH
    assert result.checkpoint_persisted is False
    assert transport.label_requests == []
    assert repository.sync_checkpoint(ACCOUNT_A) is None


def test_representations_and_errors_redact_ids_addresses_subjects_headers_and_tokens(
    tmp_path: Path,
) -> None:
    metadata = _metadata(
        "message-sensitive-synthetic",
        subject="Asunto privado sintético",
    )
    request = MessageMetadataRequest("message-sensitive-synthetic")
    transport_error = InventoryTransportError(
        RemoteErrorCode.RATE_LIMITED, status=429
    )
    repository = Repository(tmp_path / "repr.db")
    result = _service(SyntheticTransport(), repository).scan_full(
        _session(), "scan-repr-synthetic"
    )
    rendered = " ".join(
        (
            repr(_session()),
            repr(metadata),
            repr(request),
            repr(transport_error),
            repr(InventoryError(InventoryErrorCode.INVALID_RESPONSE)),
            repr(result),
        )
    )

    assert "persona@inventory.example" not in rendered
    assert "message-sensitive-synthetic" not in rendered
    assert "Asunto privado sintético" not in rendered
    assert "https://inventory.example/unsubscribe/synthetic" not in rendered
    assert "history-profile-synthetic" not in rendered


def test_inventory_uses_no_socket_urlopen_or_browser_even_when_effectively_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external capability attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setattr(webbrowser, "open", blocked)
    repository = Repository(tmp_path / "network-blocked.db")

    result = _service(SyntheticTransport(), repository).scan_full(
        _session(), "scan-network-blocked"
    )

    assert result.outcome is InventoryOutcome.COMPLETED
