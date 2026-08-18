from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

GMAIL_METADATA_SCOPE = "https://www.googleapis.com/auth/gmail.metadata"
SESSION_RECORD_VERSION = 1

_ACCOUNT_ADDRESS = re.compile(r"^[^@\s]+@[^@\s]+$")


def utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


def normalize_account_address(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("account address must be a string")
    normalized = value.strip().casefold()
    if not normalized or not _ACCOUNT_ADDRESS.fullmatch(normalized):
        raise ValueError("account address must have a valid form")
    return normalized


def validate_session_account_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("account_key must be a string")
    if value != value.strip():
        raise ValueError("account_key must be a canonical UUID")
    try:
        parsed = UUID(value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("account_key must be an opaque UUID") from None
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("account_key must be a canonical UUID4")
    return value


class SessionState(StrEnum):
    DISCONNECTED = "disconnected"
    AUTHORIZING = "authorizing"
    CONNECTED = "connected"
    REFRESH_REQUIRED = "refresh_required"
    REVOKED = "revoked"
    SCOPE_MISMATCH = "scope_mismatch"
    ACCOUNT_MISMATCH = "account_mismatch"
    FAILED = "failed"


class SessionErrorCode(StrEnum):
    NO_PENDING_AUTHORIZATION = "no_pending_authorization"
    CALLBACK_INVALID = "callback_invalid"
    CALLBACK_ERROR = "callback_error"
    STATE_MISMATCH = "state_mismatch"
    CALLBACK_REPLAYED = "callback_replayed"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    BROWSER_DISABLED = "browser_disabled"
    CALLBACK_BINDING_INVALID = "callback_binding_invalid"
    AUTHORIZATION_URI_INVALID = "authorization_uri_invalid"
    RANDOM_SOURCE_INVALID = "random_source_invalid"
    CLOCK_INVALID = "clock_invalid"
    EXCHANGE_FAILED = "exchange_failed"
    SCOPE_MISMATCH = "scope_mismatch"
    PROFILE_FAILED = "profile_failed"
    ACCOUNT_MISMATCH = "account_mismatch"
    STORE_FAILED = "store_failed"
    STORED_DATA_INVALID = "stored_data_invalid"
    REFRESH_FAILED = "refresh_failed"
    REVOCATION_FAILED = "revocation_failed"
    SESSION_NOT_FOUND = "session_not_found"


class SessionError(RuntimeError):
    def __init__(self, code: SessionErrorCode) -> None:
        if not isinstance(code, SessionErrorCode):
            raise TypeError("code must be a SessionErrorCode")
        self.code = code
        super().__init__(code.value)

    def __repr__(self) -> str:
        return f"SessionError(code={self.code.value!r})"


class AuthorizationCallbackError(StrEnum):
    ACCESS_DENIED = "access_denied"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    account_key: str
    address: str = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_key", validate_session_account_key(self.account_key)
        )
        object.__setattr__(self, "address", normalize_account_address(self.address))

    def __repr__(self) -> str:
        return f"SessionIdentity(account_key={self.account_key!r}, address=<redacted>)"


@dataclass(frozen=True, slots=True)
class CredentialBundle:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.access_token, str) or not self.access_token:
            raise ValueError("access_token must be a non-empty string")
        if self.refresh_token is not None and (
            not isinstance(self.refresh_token, str) or not self.refresh_token
        ):
            raise ValueError("refresh_token must be a non-empty string or None")
        object.__setattr__(self, "expires_at", utc_datetime(self.expires_at, "expires_at"))
        if not isinstance(self.scopes, tuple) or not self.scopes:
            raise ValueError("scopes must be a non-empty tuple")
        if any(not isinstance(scope, str) or not scope for scope in self.scopes):
            raise ValueError("scopes must contain non-empty strings")
        if len(set(self.scopes)) != len(self.scopes):
            raise ValueError("scopes must not contain duplicates")

    def __repr__(self) -> str:
        return (
            "CredentialBundle(access_token=<redacted>, refresh_token=<redacted>, "
            f"expires_at={self.expires_at!r}, scopes=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class CallbackBinding:
    redirect_uri: str
    uses_ephemeral_port: bool

    def __repr__(self) -> str:
        return (
            "CallbackBinding(redirect_uri=<redacted>, "
            f"uses_ephemeral_port={self.uses_ephemeral_port!r})"
        )


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationRequest:
    redirect_uri: str
    state: str
    code_challenge: str
    scopes: tuple[str, ...]
    response_type: str = "code"
    code_challenge_method: str = "S256"

    def __repr__(self) -> str:
        return (
            "OAuthAuthorizationRequest(redirect_uri=<redacted>, state=<redacted>, "
            "code_challenge=<redacted>, "
            f"scopes={self.scopes!r}, response_type={self.response_type!r}, "
            f"code_challenge_method={self.code_challenge_method!r})"
        )


@dataclass(frozen=True, slots=True)
class PendingAuthorization:
    authorization_uri: str
    redirect_uri: str
    expires_at: datetime
    state: SessionState = SessionState.AUTHORIZING

    def __post_init__(self) -> None:
        object.__setattr__(self, "expires_at", utc_datetime(self.expires_at, "expires_at"))
        if self.state is not SessionState.AUTHORIZING:
            raise ValueError("pending authorization state must be authorizing")

    def __repr__(self) -> str:
        return (
            "PendingAuthorization(authorization_uri=<redacted>, "
            f"redirect_uri=<redacted>, expires_at={self.expires_at!r}, "
            f"state={self.state!r})"
        )


@dataclass(frozen=True, slots=True)
class AuthorizationCallback:
    state: str
    code: str | None = None
    error: AuthorizationCallbackError | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, str) or not self.state:
            raise ValueError("callback state must be a non-empty string")
        if (self.code is None) == (self.error is None):
            raise ValueError("callback must contain exactly one result")
        if self.code is not None and (not isinstance(self.code, str) or not self.code):
            raise ValueError("authorization code must be a non-empty string")
        if self.error is not None and not isinstance(self.error, AuthorizationCallbackError):
            raise TypeError("callback error must be an AuthorizationCallbackError")

    def __repr__(self) -> str:
        return "AuthorizationCallback(state=<redacted>, code=<redacted>, error=<redacted>)"


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    state: SessionState
    identity: SessionIdentity | None = None
    error_code: SessionErrorCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, SessionState):
            raise TypeError("state must be a SessionState")
        if self.error_code is not None and not isinstance(self.error_code, SessionErrorCode):
            raise TypeError("error_code must be a SessionErrorCode or None")


@dataclass(frozen=True, slots=True)
class RevocationResult:
    remote_revoked: bool
    state: SessionState
    error_code: SessionErrorCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.remote_revoked, bool):
            raise TypeError("remote_revoked must be a bool")
        if not isinstance(self.state, SessionState):
            raise TypeError("state must be a SessionState")
        if self.error_code is not None and not isinstance(self.error_code, SessionErrorCode):
            raise TypeError("error_code must be a SessionErrorCode or None")


@dataclass(frozen=True, slots=True)
class StoredSessionRecord:
    identity: SessionIdentity
    credentials: CredentialBundle
    revoked: bool = False
    record_version: int = SESSION_RECORD_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SessionIdentity):
            raise TypeError("identity must be a SessionIdentity")
        if not isinstance(self.credentials, CredentialBundle):
            raise TypeError("credentials must be a CredentialBundle")
        if not isinstance(self.revoked, bool):
            raise TypeError("revoked must be a bool")
        if self.record_version != SESSION_RECORD_VERSION:
            raise ValueError(f"record_version must be {SESSION_RECORD_VERSION}")

    def __repr__(self) -> str:
        return (
            "StoredSessionRecord(identity=<redacted>, credentials=<redacted>, "
            f"revoked={self.revoked!r}, record_version={self.record_version!r})"
        )
