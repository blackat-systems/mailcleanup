from __future__ import annotations

from urllib.parse import urlsplit

GMAIL_API_ORIGIN = "https://gmail.googleapis.com"
GMAIL_API_PREFIX = "/gmail/v1/users/me"

GMAIL_METADATA_HEADERS = (
    "From",
    "Subject",
    "List-ID",
    "List-Unsubscribe",
    "List-Unsubscribe-Post",
    "Authentication-Results",
)

GMAIL_LIST_PAGE_LIMIT = 500
GMAIL_HEADER_VALUE_LIMIT_BYTES = 16 * 1024
GMAIL_HEADER_TOTAL_LIMIT_BYTES = 64 * 1024
GMAIL_RETRY_ATTEMPT_LIMIT = 5
GMAIL_RETRY_DELAY_LIMIT_SECONDS = 32.0

EXCLUDED_SYSTEM_LABELS = frozenset({"SENT", "DRAFT", "TRASH"})
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
READ_ONLY_HTTP_METHODS = frozenset({"GET"})

_COLLECTION_PATHS = frozenset(
    {
        f"{GMAIL_API_PREFIX}/profile",
        f"{GMAIL_API_PREFIX}/labels",
        f"{GMAIL_API_PREFIX}/messages",
        f"{GMAIL_API_PREFIX}/history",
    }
)
_MESSAGE_PATH_PREFIX = f"{GMAIL_API_PREFIX}/messages/"


def validate_readonly_gmail_endpoint(url: str) -> str:
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "gmail.googleapis.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
    ):
        raise ValueError("endpoint must use the exact Gmail API HTTPS origin without query")

    path_allowed = parsed.path in _COLLECTION_PATHS
    if parsed.path.startswith(_MESSAGE_PATH_PREFIX):
        message_id = parsed.path.removeprefix(_MESSAGE_PATH_PREFIX)
        path_allowed = bool(message_id) and "/" not in message_id
    if not path_allowed:
        raise ValueError("endpoint is outside the read-only Gmail inventory allowlist")
    return url


def canonical_metadata_headers(headers: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(headers, tuple):
        raise TypeError("headers must be a tuple")
    by_casefold = {header.casefold(): header for header in GMAIL_METADATA_HEADERS}
    requested = tuple(header.casefold() for header in headers)
    if len(set(requested)) != len(requested):
        raise ValueError("metadata headers must not contain duplicates")
    if set(requested) != set(by_casefold):
        raise ValueError("metadata headers must match the exact approved allowlist")
    return GMAIL_METADATA_HEADERS
