from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol, TypeVar, cast
from urllib.parse import SplitResult, parse_qs, urlsplit
from uuid import UUID, uuid4

from mailmap.session_model import (
    GMAIL_METADATA_SCOPE,
    SESSION_RECORD_VERSION,
    AuthorizationCallback,
    CallbackBinding,
    CredentialBundle,
    OAuthAuthorizationRequest,
    PendingAuthorization,
    RevocationResult,
    SessionError,
    SessionErrorCode,
    SessionIdentity,
    SessionSnapshot,
    SessionState,
    StoredSessionRecord,
    normalize_account_address,
    utc_datetime,
    validate_session_account_key,
)

_AUTHORIZATION_HOST = "accounts.google.com"
_AUTHORIZATION_PATH = "/o/oauth2/v2/auth"
_CALLBACK_PATH = "/oauth2/callback"
_PKCE_VALUE = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
_STATE_VALUE = re.compile(r"^[A-Za-z0-9._~-]{43,256}$")
_MAX_AUTHORIZATION_URI_LENGTH = 4096
_MAX_STORED_SESSION_BYTES = 64 * 1024
_MAX_AUTHORIZATION_TTL = timedelta(minutes=5)

_T = TypeVar("_T")
_CALL_FAILED = object()


def _controlled_call(
    operation: Callable[[], _T], error_code: SessionErrorCode
) -> _T:
    result: _T | object
    try:
        result = operation()
    except Exception:
        result = _CALL_FAILED
    if result is _CALL_FAILED:
        raise SessionError(error_code)
    return cast(_T, result)


class OAuthTransportPort(Protocol):
    def authorization_uri(self, request: OAuthAuthorizationRequest) -> str: ...

    def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> CredentialBundle: ...

    def refresh(self, credentials: CredentialBundle) -> CredentialBundle: ...

    def revoke(self, token: str) -> bool: ...


class GmailProfilePort(Protocol):
    def account_address(self, credentials: CredentialBundle) -> str: ...


class SecretStorePort(Protocol):
    def save(self, account_key: str, plaintext: bytes) -> None: ...

    def load(self, account_key: str) -> bytes | None: ...

    def delete(self, account_key: str) -> None: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class RandomSourcePort(Protocol):
    def token_urlsafe(self, byte_count: int) -> str: ...

    def uuid4(self) -> UUID: ...


class CallbackPort(Protocol):
    def reserve_loopback(self) -> CallbackBinding: ...


class AuthorizationBrowserPort(Protocol):
    def open_external(self, authorization_uri: str) -> None: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class SecureRandomSource:
    def token_urlsafe(self, byte_count: int) -> str:
        return secrets.token_urlsafe(byte_count)

    def uuid4(self) -> UUID:
        return uuid4()


class DisabledAuthorizationBrowser:
    def open_external(self, authorization_uri: str) -> None:
        del authorization_uri
        raise SessionError(SessionErrorCode.BROWSER_DISABLED)


@dataclass(frozen=True, slots=True)
class _PendingAttempt:
    authorization_uri: str
    redirect_uri: str
    state: str
    code_verifier: str
    expires_at: datetime
    expected_account: str | None

    def public(self) -> PendingAuthorization:
        return PendingAuthorization(
            authorization_uri=self.authorization_uri,
            redirect_uri=self.redirect_uri,
            expires_at=self.expires_at,
        )

    def __repr__(self) -> str:
        return (
            "_PendingAttempt(authorization_uri=<redacted>, redirect_uri=<redacted>, "
            "state=<redacted>, code_verifier=<redacted>, "
            f"expires_at={self.expires_at!r}, expected_account=<redacted>)"
        )


class SecureGmailSession:
    def __init__(
        self,
        *,
        transport: OAuthTransportPort,
        profile: GmailProfilePort,
        secret_store: SecretStorePort,
        callback: CallbackPort,
        clock: ClockPort | None = None,
        random_source: RandomSourcePort | None = None,
        browser: AuthorizationBrowserPort | None = None,
        authorization_ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        if not timedelta(0) < authorization_ttl <= _MAX_AUTHORIZATION_TTL:
            raise ValueError("authorization_ttl must be positive and at most five minutes")
        self._transport = transport
        self._profile = profile
        self._secret_store = secret_store
        self._callback = callback
        self._clock = clock or SystemClock()
        self._random = random_source or SecureRandomSource()
        self._browser = browser or DisabledAuthorizationBrowser()
        self._authorization_ttl = authorization_ttl
        self._pending: _PendingAttempt | None = None
        self._consumed_state_digests: deque[bytes] = deque(maxlen=64)
        self._active_snapshots: dict[str, SessionSnapshot] = {}

    def prepare_authorization(self, expected_account: str | None) -> PendingAuthorization:
        expected = (
            normalize_account_address(expected_account)
            if expected_account is not None
            else None
        )
        now = self._now()
        verifier = self._random_value(64, _PKCE_VALUE)
        state = self._random_value(32, _STATE_VALUE)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        binding = _controlled_call(
            self._callback.reserve_loopback,
            SessionErrorCode.CALLBACK_BINDING_INVALID,
        )
        self._validate_callback_binding(binding)

        request = OAuthAuthorizationRequest(
            redirect_uri=binding.redirect_uri,
            state=state,
            code_challenge=challenge,
            scopes=(GMAIL_METADATA_SCOPE,),
        )
        authorization_uri = _controlled_call(
            lambda: self._transport.authorization_uri(request),
            SessionErrorCode.AUTHORIZATION_URI_INVALID,
        )
        self._validate_authorization_uri(authorization_uri, request)

        if self._pending is not None:
            self._remember_consumed_state(self._pending.state)
        attempt = _PendingAttempt(
            authorization_uri=authorization_uri,
            redirect_uri=binding.redirect_uri,
            state=state,
            code_verifier=verifier,
            expires_at=now + self._authorization_ttl,
            expected_account=expected,
        )
        self._pending = attempt
        return attempt.public()

    def present_authorization(self, pending: PendingAuthorization) -> None:
        attempt = self._pending
        if attempt is None or pending != attempt.public():
            raise SessionError(SessionErrorCode.NO_PENDING_AUTHORIZATION)
        if self._now() >= attempt.expires_at:
            self._consume_attempt(attempt)
            raise SessionError(SessionErrorCode.AUTHORIZATION_EXPIRED)
        request = OAuthAuthorizationRequest(
            redirect_uri=attempt.redirect_uri,
            state=attempt.state,
            code_challenge=self._pkce_challenge(attempt.code_verifier),
            scopes=(GMAIL_METADATA_SCOPE,),
        )
        self._validate_authorization_uri(attempt.authorization_uri, request)
        _controlled_call(
            lambda: self._browser.open_external(attempt.authorization_uri),
            SessionErrorCode.BROWSER_DISABLED,
        )

    def complete_authorization(
        self, callback: AuthorizationCallback
    ) -> SessionIdentity:
        attempt = self._pending
        if attempt is None:
            code = (
                SessionErrorCode.CALLBACK_REPLAYED
                if self._was_consumed(callback.state)
                else SessionErrorCode.NO_PENDING_AUTHORIZATION
            )
            raise SessionError(code)
        if not hmac.compare_digest(callback.state, attempt.state):
            code = (
                SessionErrorCode.CALLBACK_REPLAYED
                if self._was_consumed(callback.state)
                else SessionErrorCode.STATE_MISMATCH
            )
            raise SessionError(code)

        self._consume_attempt(attempt)
        if self._now() >= attempt.expires_at:
            raise SessionError(SessionErrorCode.AUTHORIZATION_EXPIRED)
        if callback.error is not None:
            raise SessionError(SessionErrorCode.CALLBACK_ERROR)
        if callback.code is None:
            raise SessionError(SessionErrorCode.CALLBACK_INVALID)
        authorization_code = callback.code

        credentials = _controlled_call(
            lambda: self._transport.exchange_code(
                code=authorization_code,
                code_verifier=attempt.code_verifier,
                redirect_uri=attempt.redirect_uri,
            ),
            SessionErrorCode.EXCHANGE_FAILED,
        )
        if not isinstance(credentials, CredentialBundle):
            raise SessionError(SessionErrorCode.EXCHANGE_FAILED)
        self._require_exact_scope(credentials)
        if credentials.expires_at <= self._now():
            raise SessionError(SessionErrorCode.EXCHANGE_FAILED)

        address = self._verified_address(credentials)
        if attempt.expected_account is not None and not hmac.compare_digest(
            address, attempt.expected_account
        ):
            raise SessionError(SessionErrorCode.ACCOUNT_MISMATCH)

        identity = _controlled_call(
            lambda: SessionIdentity(
                account_key=str(self._random.uuid4()),
                address=address,
            ),
            SessionErrorCode.RANDOM_SOURCE_INVALID,
        )
        record = StoredSessionRecord(identity=identity, credentials=credentials)
        self._save_record(record)
        self._active_snapshots[identity.account_key] = SessionSnapshot(
            state=SessionState.CONNECTED,
            identity=identity,
        )
        return identity

    def restore_session(self, account_key: str) -> SessionSnapshot:
        validate_session_account_key(account_key)
        record = self._load_record(account_key)
        if record is None:
            snapshot = SessionSnapshot(state=SessionState.DISCONNECTED)
        elif record.credentials.scopes != (GMAIL_METADATA_SCOPE,):
            snapshot = SessionSnapshot(
                state=SessionState.SCOPE_MISMATCH,
                identity=record.identity,
                error_code=SessionErrorCode.SCOPE_MISMATCH,
            )
        elif record.revoked:
            snapshot = SessionSnapshot(
                state=SessionState.REVOKED,
                identity=record.identity,
            )
        elif record.credentials.expires_at <= self._now():
            snapshot = SessionSnapshot(
                state=SessionState.REFRESH_REQUIRED,
                identity=record.identity,
            )
        else:
            snapshot = SessionSnapshot(
                state=SessionState.CONNECTED,
                identity=record.identity,
            )
        self._active_snapshots[account_key] = snapshot
        return snapshot

    def refresh_session(self, account_key: str) -> SessionSnapshot:
        validate_session_account_key(account_key)
        record = self._load_record(account_key)
        if record is None:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.DISCONNECTED,
                    error_code=SessionErrorCode.SESSION_NOT_FOUND,
                ),
            )
        if record.credentials.scopes != (GMAIL_METADATA_SCOPE,):
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.SCOPE_MISMATCH,
                    identity=record.identity,
                    error_code=SessionErrorCode.SCOPE_MISMATCH,
                ),
            )
        if record.revoked:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(state=SessionState.REVOKED, identity=record.identity),
            )
        if record.credentials.refresh_token is None:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.REFRESH_REQUIRED,
                    identity=record.identity,
                    error_code=SessionErrorCode.REFRESH_FAILED,
                ),
            )

        try:
            refreshed = self._transport.refresh(record.credentials)
        except Exception:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.REFRESH_REQUIRED,
                    identity=record.identity,
                    error_code=SessionErrorCode.REFRESH_FAILED,
                ),
            )
        if not isinstance(refreshed, CredentialBundle):
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.REFRESH_REQUIRED,
                    identity=record.identity,
                    error_code=SessionErrorCode.REFRESH_FAILED,
                ),
            )
        if refreshed.scopes != (GMAIL_METADATA_SCOPE,):
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.SCOPE_MISMATCH,
                    identity=record.identity,
                    error_code=SessionErrorCode.SCOPE_MISMATCH,
                ),
            )
        if refreshed.expires_at <= self._now():
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.REFRESH_REQUIRED,
                    identity=record.identity,
                    error_code=SessionErrorCode.REFRESH_FAILED,
                ),
            )
        if refreshed.refresh_token is None:
            refreshed = replace(
                refreshed,
                refresh_token=record.credentials.refresh_token,
            )
        try:
            refreshed_address = self._verified_address(refreshed)
        except SessionError:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.FAILED,
                    identity=record.identity,
                    error_code=SessionErrorCode.PROFILE_FAILED,
                ),
            )
        if not hmac.compare_digest(refreshed_address, record.identity.address):
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.ACCOUNT_MISMATCH,
                    identity=record.identity,
                    error_code=SessionErrorCode.ACCOUNT_MISMATCH,
                ),
            )

        updated = replace(record, credentials=refreshed)
        try:
            self._save_record(updated)
        except SessionError:
            return self._set_snapshot(
                account_key,
                SessionSnapshot(
                    state=SessionState.FAILED,
                    identity=record.identity,
                    error_code=SessionErrorCode.STORE_FAILED,
                ),
            )
        return self._set_snapshot(
            account_key,
            SessionSnapshot(state=SessionState.CONNECTED, identity=record.identity),
        )

    def disconnect_local(self, account_key: str) -> None:
        validate_session_account_key(account_key)
        self._active_snapshots[account_key] = SessionSnapshot(
            state=SessionState.DISCONNECTED
        )

    def revoke_remote(self, account_key: str) -> RevocationResult:
        validate_session_account_key(account_key)
        record = self._load_record(account_key)
        if record is None:
            return RevocationResult(
                remote_revoked=False,
                state=SessionState.DISCONNECTED,
                error_code=SessionErrorCode.SESSION_NOT_FOUND,
            )
        if record.revoked:
            return RevocationResult(
                remote_revoked=True,
                state=SessionState.REVOKED,
            )

        token = record.credentials.refresh_token or record.credentials.access_token
        try:
            remote_revoked = self._transport.revoke(token)
        except Exception:
            remote_revoked = False
        if remote_revoked is not True:
            state = (
                SessionState.REFRESH_REQUIRED
                if record.credentials.expires_at <= self._now()
                else SessionState.CONNECTED
            )
            self._active_snapshots[account_key] = SessionSnapshot(
                state=state,
                identity=record.identity,
                error_code=SessionErrorCode.REVOCATION_FAILED,
            )
            return RevocationResult(
                remote_revoked=False,
                state=state,
                error_code=SessionErrorCode.REVOCATION_FAILED,
            )

        revoked_record = replace(record, revoked=True)
        try:
            self._save_record(revoked_record)
        except SessionError:
            self._active_snapshots[account_key] = SessionSnapshot(
                state=SessionState.FAILED,
                identity=record.identity,
                error_code=SessionErrorCode.STORE_FAILED,
            )
            return RevocationResult(
                remote_revoked=True,
                state=SessionState.FAILED,
                error_code=SessionErrorCode.STORE_FAILED,
            )
        self._active_snapshots[account_key] = SessionSnapshot(
            state=SessionState.REVOKED,
            identity=record.identity,
        )
        return RevocationResult(remote_revoked=True, state=SessionState.REVOKED)

    def forget_local(self, account_key: str) -> None:
        validate_session_account_key(account_key)
        _controlled_call(
            lambda: self._secret_store.delete(account_key),
            SessionErrorCode.STORE_FAILED,
        )
        self._active_snapshots[account_key] = SessionSnapshot(
            state=SessionState.DISCONNECTED
        )

    def current_snapshot(self, account_key: str) -> SessionSnapshot:
        validate_session_account_key(account_key)
        return self._active_snapshots.get(
            account_key, SessionSnapshot(state=SessionState.DISCONNECTED)
        )

    def _verified_address(self, credentials: CredentialBundle) -> str:
        return _controlled_call(
            lambda: normalize_account_address(
                self._profile.account_address(credentials)
            ),
            SessionErrorCode.PROFILE_FAILED,
        )

    def _require_exact_scope(self, credentials: CredentialBundle) -> None:
        if credentials.scopes != (GMAIL_METADATA_SCOPE,):
            raise SessionError(SessionErrorCode.SCOPE_MISMATCH)

    def _now(self) -> datetime:
        return _controlled_call(
            lambda: utc_datetime(self._clock.now(), "clock value"),
            SessionErrorCode.CLOCK_INVALID,
        )

    def _random_value(self, byte_count: int, pattern: re.Pattern[str]) -> str:
        value = _controlled_call(
            lambda: self._random.token_urlsafe(byte_count),
            SessionErrorCode.RANDOM_SOURCE_INVALID,
        )
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise SessionError(SessionErrorCode.RANDOM_SOURCE_INVALID)
        return value

    @staticmethod
    def _pkce_challenge(verifier: str) -> str:
        return base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

    @staticmethod
    def _validate_callback_binding(binding: CallbackBinding) -> None:
        if not isinstance(binding, CallbackBinding) or not binding.uses_ephemeral_port:
            raise SessionError(SessionErrorCode.CALLBACK_BINDING_INVALID)
        try:
            parts = urlsplit(binding.redirect_uri)
            port = parts.port
        except (TypeError, ValueError):
            raise SessionError(SessionErrorCode.CALLBACK_BINDING_INVALID) from None
        if (
            parts.scheme != "http"
            or parts.hostname != "127.0.0.1"
            or port is None
            or not 1 <= port <= 65535
            or parts.username is not None
            or parts.password is not None
            or parts.path != _CALLBACK_PATH
            or parts.query
            or parts.fragment
        ):
            raise SessionError(SessionErrorCode.CALLBACK_BINDING_INVALID)

    @staticmethod
    def _validate_authorization_uri(
        authorization_uri: str, request: OAuthAuthorizationRequest
    ) -> None:
        if (
            not isinstance(authorization_uri, str)
            or not authorization_uri
            or len(authorization_uri) > _MAX_AUTHORIZATION_URI_LENGTH
        ):
            raise SessionError(SessionErrorCode.AUTHORIZATION_URI_INVALID)
        def parse_authorization_uri() -> tuple[
            SplitResult, int | None, dict[str, list[str]]
        ]:
            parts = urlsplit(authorization_uri)
            port = parts.port
            query = parse_qs(
                parts.query,
                keep_blank_values=True,
                strict_parsing=True,
            )
            return parts, port, query

        parts, port, query = _controlled_call(
            parse_authorization_uri,
            SessionErrorCode.AUTHORIZATION_URI_INVALID,
        )
        if (
            parts.scheme != "https"
            or parts.hostname != _AUTHORIZATION_HOST
            or port not in (None, 443)
            or parts.username is not None
            or parts.password is not None
            or parts.path != _AUTHORIZATION_PATH
            or parts.fragment
        ):
            raise SessionError(SessionErrorCode.AUTHORIZATION_URI_INVALID)
        required = {
            "client_id": None,
            "redirect_uri": request.redirect_uri,
            "response_type": request.response_type,
            "scope": GMAIL_METADATA_SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "state": request.state,
            "code_challenge": request.code_challenge,
            "code_challenge_method": request.code_challenge_method,
        }
        for name, expected in required.items():
            values = query.get(name)
            if values is None or len(values) != 1 or not values[0]:
                raise SessionError(SessionErrorCode.AUTHORIZATION_URI_INVALID)
            if expected is not None and not hmac.compare_digest(values[0], expected):
                raise SessionError(SessionErrorCode.AUTHORIZATION_URI_INVALID)

    def _consume_attempt(self, attempt: _PendingAttempt) -> None:
        self._remember_consumed_state(attempt.state)
        if self._pending is attempt:
            self._pending = None

    def _remember_consumed_state(self, state: str) -> None:
        self._consumed_state_digests.append(hashlib.sha256(state.encode("ascii")).digest())

    def _was_consumed(self, state: str) -> bool:
        digest = hashlib.sha256(state.encode("utf-8")).digest()
        return any(
            hmac.compare_digest(digest, consumed)
            for consumed in self._consumed_state_digests
        )

    def _save_record(self, record: StoredSessionRecord) -> None:
        plaintext = self._encode_record(record)
        _controlled_call(
            lambda: self._secret_store.save(record.identity.account_key, plaintext),
            SessionErrorCode.STORE_FAILED,
        )

    def _load_record(self, account_key: str) -> StoredSessionRecord | None:
        plaintext = _controlled_call(
            lambda: self._secret_store.load(account_key),
            SessionErrorCode.STORE_FAILED,
        )
        if plaintext is None:
            return None
        record = self._decode_record(plaintext)
        if not hmac.compare_digest(record.identity.account_key, account_key):
            raise SessionError(SessionErrorCode.STORED_DATA_INVALID)
        return record

    @staticmethod
    def _encode_record(record: StoredSessionRecord) -> bytes:
        payload = {
            "record_version": record.record_version,
            "account_key": record.identity.account_key,
            "address": record.identity.address,
            "revoked": record.revoked,
            "credentials": {
                "access_token": record.credentials.access_token,
                "refresh_token": record.credentials.refresh_token,
                "expires_at": record.credentials.expires_at.isoformat(),
                "scopes": list(record.credentials.scopes),
            },
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(encoded) > _MAX_STORED_SESSION_BYTES:
            raise SessionError(SessionErrorCode.STORED_DATA_INVALID)
        return encoded

    @staticmethod
    def _decode_record(plaintext: bytes) -> StoredSessionRecord:
        if not isinstance(plaintext, bytes) or not 0 < len(plaintext) <= _MAX_STORED_SESSION_BYTES:
            raise SessionError(SessionErrorCode.STORED_DATA_INVALID)

        def parse_record() -> StoredSessionRecord:
            payload = json.loads(plaintext.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != {
                "record_version",
                "account_key",
                "address",
                "revoked",
                "credentials",
            }:
                raise ValueError
            if type(payload["record_version"]) is not int:
                raise ValueError
            if type(payload["revoked"]) is not bool:
                raise ValueError
            credentials = payload["credentials"]
            if not isinstance(credentials, dict) or set(credentials) != {
                "access_token",
                "refresh_token",
                "expires_at",
                "scopes",
            }:
                raise ValueError
            scopes = credentials["scopes"]
            if not isinstance(scopes, list) or not all(
                isinstance(scope, str) for scope in scopes
            ):
                raise ValueError
            return StoredSessionRecord(
                identity=SessionIdentity(
                    account_key=payload["account_key"],
                    address=payload["address"],
                ),
                credentials=CredentialBundle(
                    access_token=credentials["access_token"],
                    refresh_token=credentials["refresh_token"],
                    expires_at=datetime.fromisoformat(credentials["expires_at"]),
                    scopes=tuple(scopes),
                ),
                revoked=payload["revoked"],
                record_version=payload["record_version"],
            )

        record = _controlled_call(
            parse_record,
            SessionErrorCode.STORED_DATA_INVALID,
        )
        if record.record_version != SESSION_RECORD_VERSION:
            raise SessionError(SessionErrorCode.STORED_DATA_INVALID)
        return record

    def _set_snapshot(
        self, account_key: str, snapshot: SessionSnapshot
    ) -> SessionSnapshot:
        self._active_snapshots[account_key] = snapshot
        return snapshot
