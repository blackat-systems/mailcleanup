from __future__ import annotations

import pytest

from mailmap.gmail_readonly_policy import (
    EXCLUDED_SYSTEM_LABELS,
    GMAIL_API_ORIGIN,
    GMAIL_HEADER_TOTAL_LIMIT_BYTES,
    GMAIL_HEADER_VALUE_LIMIT_BYTES,
    GMAIL_LIST_PAGE_LIMIT,
    GMAIL_METADATA_HEADERS,
    GMAIL_RETRY_ATTEMPT_LIMIT,
    GMAIL_RETRY_DELAY_LIMIT_SECONDS,
    READ_ONLY_HTTP_METHODS,
    RETRYABLE_HTTP_STATUSES,
    canonical_metadata_headers,
    validate_readonly_gmail_endpoint,
)


def test_policy_is_minimal_bounded_and_read_only() -> None:
    assert GMAIL_API_ORIGIN == "https://gmail.googleapis.com"
    assert {"GET"} == READ_ONLY_HTTP_METHODS
    assert GMAIL_LIST_PAGE_LIMIT == 500
    assert GMAIL_HEADER_VALUE_LIMIT_BYTES == 16 * 1024
    assert GMAIL_HEADER_TOTAL_LIMIT_BYTES == 64 * 1024
    assert GMAIL_RETRY_ATTEMPT_LIMIT == 5
    assert GMAIL_RETRY_DELAY_LIMIT_SECONDS == 32.0
    assert {429, 500, 502, 503, 504} == RETRYABLE_HTTP_STATUSES
    assert {"SENT", "DRAFT", "TRASH"} == EXCLUDED_SYSTEM_LABELS


def test_metadata_header_allowlist_is_exact() -> None:
    assert GMAIL_METADATA_HEADERS == (
        "From",
        "Subject",
        "List-ID",
        "List-Unsubscribe",
        "List-Unsubscribe-Post",
        "Authentication-Results",
    )
    assert canonical_metadata_headers(tuple(reversed(GMAIL_METADATA_HEADERS))) == (
        GMAIL_METADATA_HEADERS
    )


@pytest.mark.parametrize(
    "headers",
    [
        ("From", "Subject"),
        (*GMAIL_METADATA_HEADERS, "To"),
        (*GMAIL_METADATA_HEADERS, "Snippet"),
        (*GMAIL_METADATA_HEADERS, "From"),
    ],
)
def test_metadata_header_allowlist_fails_closed(headers: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        canonical_metadata_headers(headers)


@pytest.mark.parametrize(
    "url",
    [
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/msg-synthetic-001",
        "https://gmail.googleapis.com/gmail/v1/users/me/history",
    ],
)
def test_exact_readonly_endpoints_are_allowed(url: str) -> None:
    assert validate_readonly_gmail_endpoint(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://gmail.googleapis.com/gmail/v1/users/me/messages",
        "https://gmail.googleapis.com:443/gmail/v1/users/me/messages",
        "https://gmail.googleapis.com.evil.example/gmail/v1/users/me/messages",
        "https://" + "user@" + "gmail.googleapis.com/gmail/v1/users/me/messages",
        "https://gmail.googleapis.com/gmail/v1/users/other/messages",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/id/modify",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages#fragment",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/id?format=RAW",
    ],
)
def test_endpoints_outside_exact_allowlist_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        validate_readonly_gmail_endpoint(url)
