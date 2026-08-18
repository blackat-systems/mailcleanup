from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import urllib.request
import webbrowser
from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

import pytest

import mailmap.windows_secret_store as secret_store_module
from mailmap.oauth_session import SecureGmailSession
from mailmap.session_model import (
    GMAIL_METADATA_SCOPE,
    AuthorizationCallback,
    AuthorizationCallbackError,
    CallbackBinding,
    CredentialBundle,
    OAuthAuthorizationRequest,
    PendingAuthorization,
    SessionError,
    SessionErrorCode,
    SessionIdentity,
    SessionState,
)
from mailmap.windows_secret_store import (
    SecretStoreError,
    SecretStoreErrorCode,
    WindowsDpapiProtector,
    WindowsSecretStore,
)

NOW = datetime(2026, 8, 18, 15, 0, tzinfo=UTC)
ACCOUNT_ADDRESS = "persona.sintetica@correo.example"
OTHER_ACCOUNT_ADDRESS = "otra.persona@correo.example"
ACCOUNT_KEY = "11111111-1111-4111-8111-111111111111"
SECOND_ACCOUNT_KEY = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(autouse=True)
def block_real_network_and_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external I/O is forbidden in D2 tests")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setattr(webbrowser, "open", blocked)


@dataclass
class FakeClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value

    def advance(self, delta: timedelta) -> None:
        self.value += delta


class FakeRandom:
    def __init__(self) -> None:
        self.token_calls: list[int] = []
        self.uuid_values = [UUID(ACCOUNT_KEY), UUID(SECOND_ACCOUNT_KEY)]

    def token_urlsafe(self, byte_count: int) -> str:
        self.token_calls.append(byte_count)
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        character = characters[len(self.token_calls)]
        length = 86 if byte_count == 64 else 43
        return character * length

    def uuid4(self) -> UUID:
        return self.uuid_values.pop(0)


class FakeCallbackPort:
    def __init__(self) -> None:
        self.ports = iter((49151, 49152, 49153, 49154))
        self.override: CallbackBinding | None = None

    def reserve_loopback(self) -> CallbackBinding:
        if self.override is not None:
            return self.override
        return CallbackBinding(
            redirect_uri=f"http://127.0.0.1:{next(self.ports)}/oauth2/callback",
            uses_ephemeral_port=True,
        )


class FakeBrowser:
    def __init__(self) -> None:
        self.presented: list[str] = []

    def open_external(self, authorization_uri: str) -> None:
        self.presented.append(authorization_uri)


class FakeTransport:
    def __init__(self, credentials: CredentialBundle) -> None:
        self.exchange_credentials = credentials
        self.refresh_credentials = replace(
            credentials,
            access_token="access-synthetic-refreshed",
            expires_at=credentials.expires_at + timedelta(hours=1),
        )
        self.requests: list[OAuthAuthorizationRequest] = []
        self.exchange_calls: list[tuple[str, str, str]] = []
        self.refresh_calls: list[CredentialBundle] = []
        self.revoke_calls: list[str] = []
        self.exchange_error: Exception | None = None
        self.refresh_error: Exception | None = None
        self.revoke_error: Exception | None = None
        self.revoke_result = True
        self.authorization_host = "accounts.google.com"

    def authorization_uri(self, request: OAuthAuthorizationRequest) -> str:
        self.requests.append(request)
        query = urlencode(
            {
                "client_id": "synthetic-client.apps.example",
                "redirect_uri": request.redirect_uri,
                "response_type": request.response_type,
                "scope": " ".join(request.scopes),
                "access_type": "offline",
                "state": request.state,
                "code_challenge": request.code_challenge,
                "code_challenge_method": request.code_challenge_method,
                "include_granted_scopes": "true",
            }
        )
        return f"https://{self.authorization_host}/o/oauth2/v2/auth?{query}"

    def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> CredentialBundle:
        self.exchange_calls.append((code, code_verifier, redirect_uri))
        if self.exchange_error is not None:
            raise self.exchange_error
        return self.exchange_credentials

    def refresh(self, credentials: CredentialBundle) -> CredentialBundle:
        self.refresh_calls.append(credentials)
        if self.refresh_error is not None:
            raise self.refresh_error
        return self.refresh_credentials

    def revoke(self, token: str) -> bool:
        self.revoke_calls.append(token)
        if self.revoke_error is not None:
            raise self.revoke_error
        return self.revoke_result


class FakeProfile:
    def __init__(self, address: str = ACCOUNT_ADDRESS) -> None:
        self.address = address
        self.calls: list[CredentialBundle] = []
        self.error: Exception | None = None

    def account_address(self, credentials: CredentialBundle) -> str:
        self.calls.append(credentials)
        if self.error is not None:
            raise self.error
        return self.address


class MemorySecretStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.save_calls: list[str] = []
        self.delete_calls: list[str] = []
        self.fail_save = False

    def save(self, account_key: str, plaintext: bytes) -> None:
        self.save_calls.append(account_key)
        if self.fail_save:
            raise RuntimeError("synthetic storage failure")
        self.values[account_key] = plaintext

    def load(self, account_key: str) -> bytes | None:
        return self.values.get(account_key)

    def delete(self, account_key: str) -> None:
        self.delete_calls.append(account_key)
        self.values.pop(account_key, None)


@dataclass
class Harness:
    session: SecureGmailSession
    clock: FakeClock
    random: FakeRandom
    callback: FakeCallbackPort
    browser: FakeBrowser
    transport: FakeTransport
    profile: FakeProfile
    store: MemorySecretStore


def credential_bundle(
    *,
    scopes: tuple[str, ...] = (GMAIL_METADATA_SCOPE,),
    expires_at: datetime = NOW + timedelta(hours=1),
    refresh_token: str | None = "refresh-synthetic-secret",
) -> CredentialBundle:
    return CredentialBundle(
        access_token="access-synthetic-secret",
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=scopes,
    )


def harness(*, credentials: CredentialBundle | None = None) -> Harness:
    clock = FakeClock()
    random = FakeRandom()
    callback = FakeCallbackPort()
    browser = FakeBrowser()
    transport = FakeTransport(credentials or credential_bundle())
    profile = FakeProfile()
    store = MemorySecretStore()
    session = SecureGmailSession(
        transport=transport,
        profile=profile,
        secret_store=store,
        callback=callback,
        clock=clock,
        random_source=random,
        browser=browser,
    )
    return Harness(session, clock, random, callback, browser, transport, profile, store)


def prepare_and_callback(
    context: Harness, expected_account: str | None = ACCOUNT_ADDRESS
) -> tuple[PendingAuthorization, AuthorizationCallback]:
    pending = context.session.prepare_authorization(expected_account)
    request = context.transport.requests[-1]
    return pending, AuthorizationCallback(
        state=request.state,
        code="authorization-code-synthetic",
    )


def complete(context: Harness, expected_account: str | None = ACCOUNT_ADDRESS) -> SessionIdentity:
    _pending, callback = prepare_and_callback(context, expected_account)
    return context.session.complete_authorization(callback)


def test_models_are_closed_frozen_and_redact_private_values() -> None:
    identity = SessionIdentity(ACCOUNT_KEY, ACCOUNT_ADDRESS)
    credentials = credential_bundle()
    callback = AuthorizationCallback(state="s" * 43, code="code-private-synthetic")
    pending = PendingAuthorization(
        authorization_uri="https://accounts.google.com/private-synthetic",
        redirect_uri="http://127.0.0.1:49151/oauth2/callback",
        expires_at=NOW,
    )

    rendered = " ".join(map(repr, (identity, credentials, callback, pending)))
    assert ACCOUNT_ADDRESS not in rendered
    assert credentials.access_token not in rendered
    assert credentials.refresh_token not in rendered
    assert GMAIL_METADATA_SCOPE not in repr(credentials)
    assert callback.state not in rendered
    assert callback.code not in rendered
    assert pending.authorization_uri not in rendered
    assert not hasattr(identity, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identity.account_key = SECOND_ACCOUNT_KEY  # type: ignore[misc]
    with pytest.raises(TypeError):
        SessionIdentity(ACCOUNT_KEY, ACCOUNT_ADDRESS, extra=True)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "scopes",
    (
        ("https://www.googleapis.com/auth/userinfo.email",),
        (GMAIL_METADATA_SCOPE, "https://www.googleapis.com/auth/userinfo.email"),
    ),
)
def test_only_exact_metadata_scope_is_accepted(scopes: tuple[str, ...]) -> None:
    context = harness(credentials=credential_bundle(scopes=scopes))
    _pending, callback = prepare_and_callback(context)

    with pytest.raises(SessionError) as raised:
        context.session.complete_authorization(callback)

    assert raised.value.code is SessionErrorCode.SCOPE_MISMATCH
    assert context.store.values == {}
    assert context.profile.calls == []
    assert context.transport.requests[-1].scopes == (GMAIL_METADATA_SCOPE,)


def test_pkce_s256_state_and_ephemeral_loopback_are_new_for_each_attempt() -> None:
    context = harness()

    first = context.session.prepare_authorization(None)
    first_request = context.transport.requests[-1]
    first_verifier = "B" * 86
    second = context.session.prepare_authorization(None)
    second_request = context.transport.requests[-1]

    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(first_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    assert first_request.code_challenge == expected_challenge
    assert first_request.code_challenge_method == "S256"
    assert first_request.response_type == "code"
    assert first_request.scopes == (GMAIL_METADATA_SCOPE,)
    assert first_request.state != second_request.state
    assert first.redirect_uri == "http://127.0.0.1:49151/oauth2/callback"
    assert second.redirect_uri == "http://127.0.0.1:49152/oauth2/callback"
    assert context.random.token_calls == [64, 32, 64, 32]


def test_authorization_ttl_cannot_exceed_five_minutes() -> None:
    context = harness()

    with pytest.raises(ValueError, match="at most five minutes"):
        SecureGmailSession(
            transport=context.transport,
            profile=context.profile,
            secret_store=context.store,
            callback=context.callback,
            clock=context.clock,
            random_source=context.random,
            browser=context.browser,
            authorization_ttl=timedelta(minutes=5, microseconds=1),
        )


@pytest.mark.parametrize(
    "binding",
    (
        CallbackBinding("http://localhost:49151/oauth2/callback", True),
        CallbackBinding("http://127.0.0.1:8765/oauth2/callback", False),
        CallbackBinding("http://127.0.0.1:49151/other", True),
        CallbackBinding("https://127.0.0.1:49151/oauth2/callback", True),
    ),
)
def test_callback_rejects_non_numeric_non_ephemeral_or_wrong_binding(
    binding: CallbackBinding,
) -> None:
    context = harness()
    context.callback.override = binding

    with pytest.raises(SessionError) as raised:
        context.session.prepare_authorization(None)

    assert raised.value.code is SessionErrorCode.CALLBACK_BINDING_INVALID
    assert context.transport.requests == []


def test_authorization_uri_is_restricted_to_google_authorization_host() -> None:
    context = harness()
    context.transport.authorization_host = "login.invalid.example"

    with pytest.raises(SessionError) as raised:
        context.session.prepare_authorization(None)

    assert raised.value.code is SessionErrorCode.AUTHORIZATION_URI_INVALID


def test_prepare_never_opens_browser_and_present_uses_only_injected_port() -> None:
    context = harness()
    pending = context.session.prepare_authorization(None)

    assert context.browser.presented == []
    context.session.present_authorization(pending)

    assert context.browser.presented == [pending.authorization_uri]


def test_default_browser_remains_disabled() -> None:
    context = harness()
    context.session = SecureGmailSession(
        transport=context.transport,
        profile=context.profile,
        secret_store=context.store,
        callback=context.callback,
        clock=context.clock,
        random_source=context.random,
    )
    pending = context.session.prepare_authorization(None)

    with pytest.raises(SessionError) as raised:
        context.session.present_authorization(pending)

    assert raised.value.code is SessionErrorCode.BROWSER_DISABLED


def test_wrong_state_does_not_exchange_and_valid_state_is_single_use() -> None:
    context = harness()
    _pending, callback = prepare_and_callback(context)
    wrong = AuthorizationCallback(state="Z" * 43, code=callback.code)

    with pytest.raises(SessionError) as wrong_state:
        context.session.complete_authorization(wrong)
    assert wrong_state.value.code is SessionErrorCode.STATE_MISMATCH
    assert context.transport.exchange_calls == []

    identity = context.session.complete_authorization(callback)
    assert identity.account_key == ACCOUNT_KEY
    with pytest.raises(SessionError) as replayed:
        context.session.complete_authorization(callback)
    assert replayed.value.code is SessionErrorCode.CALLBACK_REPLAYED
    assert len(context.transport.exchange_calls) == 1


def test_expired_or_error_callback_never_exchanges_or_persists() -> None:
    expired = harness()
    _pending, expired_callback = prepare_and_callback(expired)
    expired.clock.advance(timedelta(minutes=5))

    with pytest.raises(SessionError) as late:
        expired.session.complete_authorization(expired_callback)
    assert late.value.code is SessionErrorCode.AUTHORIZATION_EXPIRED
    assert expired.transport.exchange_calls == []
    assert expired.store.values == {}

    denied = harness()
    denied.session.prepare_authorization(None)
    denied_callback = AuthorizationCallback(
        state=denied.transport.requests[-1].state,
        error=AuthorizationCallbackError.ACCESS_DENIED,
    )
    with pytest.raises(SessionError) as callback_error:
        denied.session.complete_authorization(denied_callback)
    assert callback_error.value.code is SessionErrorCode.CALLBACK_ERROR
    assert denied.transport.exchange_calls == []
    assert denied.store.values == {}


def test_expired_exchanged_credentials_are_rejected_before_profile_or_storage() -> None:
    context = harness(credentials=credential_bundle(expires_at=NOW))
    _pending, callback = prepare_and_callback(context)

    with pytest.raises(SessionError) as raised:
        context.session.complete_authorization(callback)

    assert raised.value.code is SessionErrorCode.EXCHANGE_FAILED
    assert context.profile.calls == []
    assert context.store.values == {}


def test_expected_account_is_normalized_and_mismatch_prevents_persistence() -> None:
    matching = harness()
    identity = complete(matching, f"  {ACCOUNT_ADDRESS.upper()}  ")
    assert identity.address == ACCOUNT_ADDRESS

    mismatching = harness()
    _pending, callback = prepare_and_callback(mismatching, OTHER_ACCOUNT_ADDRESS)
    with pytest.raises(SessionError) as raised:
        mismatching.session.complete_authorization(callback)
    assert raised.value.code is SessionErrorCode.ACCOUNT_MISMATCH
    assert mismatching.store.values == {}
    assert mismatching.store.save_calls == []


def test_persistence_happens_only_after_scope_and_profile_validation() -> None:
    context = harness()
    context.profile.error = RuntimeError(
        f"remote profile included {ACCOUNT_ADDRESS} and access-synthetic-secret"
    )
    _pending, callback = prepare_and_callback(context)

    with pytest.raises(SessionError) as raised:
        context.session.complete_authorization(callback)

    assert raised.value.code is SessionErrorCode.PROFILE_FAILED
    assert repr(raised.value) == "SessionError(code='profile_failed')"
    assert raised.value.__context__ is None
    assert ACCOUNT_ADDRESS not in str(raised.value)
    assert "access-synthetic-secret" not in str(raised.value)
    assert context.store.values == {}


def test_account_key_is_opaque_and_stable_across_restore_and_refresh() -> None:
    context = harness()
    identity = complete(context)
    stored_before_refresh = context.store.values[identity.account_key]

    restored = context.session.restore_session(identity.account_key)
    refreshed = context.session.refresh_session(identity.account_key)

    assert identity.account_key == ACCOUNT_KEY
    assert "@" not in identity.account_key
    assert restored == replace(restored, state=SessionState.CONNECTED)
    assert restored.identity == identity
    assert refreshed.state is SessionState.CONNECTED
    assert refreshed.identity == identity
    assert context.store.values[identity.account_key] != stored_before_refresh
    assert len(context.profile.calls) == 2


def test_restore_reports_refresh_required_after_expiry() -> None:
    context = harness()
    identity = complete(context)
    context.clock.advance(timedelta(hours=2))

    snapshot = context.session.restore_session(identity.account_key)

    assert snapshot.state is SessionState.REFRESH_REQUIRED
    assert snapshot.identity == identity


def test_restore_rejects_unexpected_scope_and_non_closed_stored_shape() -> None:
    context = harness()
    identity = complete(context)
    payload = json.loads(context.store.values[identity.account_key])
    payload["credentials"]["scopes"] = [
        GMAIL_METADATA_SCOPE,
        "https://www.googleapis.com/auth/userinfo.email",
    ]
    context.store.values[identity.account_key] = json.dumps(payload).encode("utf-8")

    snapshot = context.session.restore_session(identity.account_key)

    assert snapshot.state is SessionState.SCOPE_MISMATCH
    assert snapshot.error_code is SessionErrorCode.SCOPE_MISMATCH

    payload["unexpected"] = "synthetic-extra-field"
    context.store.values[identity.account_key] = json.dumps(payload).encode("utf-8")
    with pytest.raises(SessionError) as raised:
        context.session.restore_session(identity.account_key)
    assert raised.value.code is SessionErrorCode.STORED_DATA_INVALID
    assert raised.value.__context__ is None


def test_refresh_failure_is_controlled_and_preserves_previous_credentials() -> None:
    context = harness()
    identity = complete(context)
    previous = context.store.values[identity.account_key]
    context.transport.refresh_error = RuntimeError(
        f"remote body with {ACCOUNT_ADDRESS} access-synthetic-secret"
    )

    snapshot = context.session.refresh_session(identity.account_key)

    assert snapshot.state is SessionState.REFRESH_REQUIRED
    assert snapshot.error_code is SessionErrorCode.REFRESH_FAILED
    assert ACCOUNT_ADDRESS not in repr(snapshot)
    assert "access-synthetic-secret" not in repr(snapshot)
    assert context.store.values[identity.account_key] == previous


def test_refresh_preserves_existing_refresh_token_when_provider_omits_it() -> None:
    context = harness()
    identity = complete(context)
    context.transport.refresh_credentials = credential_bundle(
        expires_at=NOW + timedelta(hours=2),
        refresh_token=None,
    )

    snapshot = context.session.refresh_session(identity.account_key)
    payload = json.loads(context.store.values[identity.account_key])

    assert snapshot.state is SessionState.CONNECTED
    assert payload["credentials"]["refresh_token"] == "refresh-synthetic-secret"


def test_refresh_rejects_expired_credentials_without_overwriting() -> None:
    context = harness()
    identity = complete(context)
    previous = context.store.values[identity.account_key]
    context.transport.refresh_credentials = credential_bundle(
        expires_at=NOW,
        refresh_token="refresh-synthetic-new",
    )

    snapshot = context.session.refresh_session(identity.account_key)

    assert snapshot.state is SessionState.REFRESH_REQUIRED
    assert snapshot.error_code is SessionErrorCode.REFRESH_FAILED
    assert context.profile.calls == [context.transport.exchange_credentials]
    assert context.store.values[identity.account_key] == previous


def test_refresh_rejects_scope_or_identity_change_without_overwriting() -> None:
    wrong_scope = harness()
    identity = complete(wrong_scope)
    previous = wrong_scope.store.values[identity.account_key]
    wrong_scope.transport.refresh_credentials = credential_bundle(
        scopes=("https://www.googleapis.com/auth/userinfo.email",)
    )
    scope_snapshot = wrong_scope.session.refresh_session(identity.account_key)
    assert scope_snapshot.state is SessionState.SCOPE_MISMATCH
    assert wrong_scope.store.values[identity.account_key] == previous

    wrong_identity = harness()
    second_identity = complete(wrong_identity)
    second_previous = wrong_identity.store.values[second_identity.account_key]
    wrong_identity.profile.address = OTHER_ACCOUNT_ADDRESS
    account_snapshot = wrong_identity.session.refresh_session(second_identity.account_key)
    assert account_snapshot.state is SessionState.ACCOUNT_MISMATCH
    assert wrong_identity.store.values[second_identity.account_key] == second_previous


def test_disconnect_is_local_only_and_does_not_delete_or_revoke() -> None:
    context = harness()
    identity = complete(context)

    context.session.disconnect_local(identity.account_key)

    assert context.session.current_snapshot(identity.account_key).state is SessionState.DISCONNECTED
    assert identity.account_key in context.store.values
    assert context.store.delete_calls == []
    assert context.transport.revoke_calls == []
    assert context.session.restore_session(identity.account_key).state is SessionState.CONNECTED


def test_remote_revocation_success_is_persisted_but_not_forgotten() -> None:
    context = harness()
    identity = complete(context)

    result = context.session.revoke_remote(identity.account_key)

    assert result.remote_revoked is True
    assert result.state is SessionState.REVOKED
    assert context.transport.revoke_calls == ["refresh-synthetic-secret"]
    assert identity.account_key in context.store.values
    assert context.store.delete_calls == []
    assert context.session.restore_session(identity.account_key).state is SessionState.REVOKED


def test_remote_revocation_failure_is_not_success_and_preserves_retry_material() -> None:
    context = harness()
    identity = complete(context)
    previous = context.store.values[identity.account_key]
    context.transport.revoke_error = RuntimeError(
        "synthetic remote body access-synthetic-secret"
    )

    result = context.session.revoke_remote(identity.account_key)

    assert result.remote_revoked is False
    assert result.error_code is SessionErrorCode.REVOCATION_FAILED
    assert context.store.values[identity.account_key] == previous
    assert context.store.delete_calls == []


def test_forget_local_is_explicit_and_independent() -> None:
    context = harness()
    identity = complete(context)

    context.session.forget_local(identity.account_key)

    assert identity.account_key not in context.store.values
    assert context.store.delete_calls == [identity.account_key]
    assert context.transport.revoke_calls == []
    assert context.session.restore_session(identity.account_key).state is SessionState.DISCONNECTED


class FakeDpapiBackend:
    def __init__(self) -> None:
        self.protect_flags: list[int] = []
        self.unprotect_flags: list[int] = []

    def protect(self, plaintext: bytes, *, flags: int) -> bytes:
        self.protect_flags.append(flags)
        return b"ciphertext:" + plaintext[::-1]

    def unprotect(self, ciphertext: bytes, *, flags: int) -> bytes:
        self.unprotect_flags.append(flags)
        prefix = b"ciphertext:"
        if not ciphertext.startswith(prefix):
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED)
        return ciphertext[len(prefix) :][::-1]


def test_dpapi_uses_current_user_scope_and_store_is_versioned_and_atomic(
    tmp_path: Path,
) -> None:
    backend = FakeDpapiBackend()
    protector = WindowsDpapiProtector(backend)
    directory = tmp_path / "MailCleanup" / "credentials"
    store = WindowsSecretStore(directory=directory, protector=protector)
    plaintext = b"synthetic credential payload"

    store.save(ACCOUNT_KEY, plaintext)
    path = store.credential_path(ACCOUNT_KEY)
    persisted = path.read_bytes()

    assert store.directory == directory
    assert path.name == f"{ACCOUNT_KEY}.credential"
    assert ACCOUNT_ADDRESS not in str(path)
    assert plaintext not in persisted
    assert persisted.startswith(secret_store_module._FORMAT_MAGIC)
    assert store.load(ACCOUNT_KEY) == plaintext
    assert backend.protect_flags == [1]
    assert backend.unprotect_flags == [1]
    assert all(flag & 0x4 == 0 for flag in (*backend.protect_flags, *backend.unprotect_flags))
    assert list(directory.glob("*.tmp")) == []


def test_secret_store_rejects_corruption_before_decrypting(tmp_path: Path) -> None:
    backend = FakeDpapiBackend()
    store = WindowsSecretStore(
        directory=tmp_path / "credentials",
        protector=WindowsDpapiProtector(backend),
    )
    path = store.credential_path(ACCOUNT_KEY)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"invalid synthetic envelope")

    with pytest.raises(SecretStoreError) as raised:
        store.load(ACCOUNT_KEY)

    assert raised.value.code is SecretStoreErrorCode.CORRUPT
    assert backend.unprotect_flags == []


def test_failed_atomic_replace_keeps_previous_ciphertext(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WindowsSecretStore(
        directory=tmp_path / "credentials",
        protector=WindowsDpapiProtector(FakeDpapiBackend()),
    )
    store.save(ACCOUNT_KEY, b"first synthetic payload")
    path = store.credential_path(ACCOUNT_KEY)
    previous = path.read_bytes()

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("synthetic atomic replacement failure")

    monkeypatch.setattr(secret_store_module.os, "replace", fail_replace)
    with pytest.raises(SecretStoreError) as raised:
        store.save(ACCOUNT_KEY, b"second synthetic payload")

    assert raised.value.code is SecretStoreErrorCode.IO_FAILED
    assert path.read_bytes() == previous
    assert list(path.parent.glob("*.tmp")) == []


@pytest.mark.skipif(os.name != "nt", reason="DPAPI is only available on Windows")
def test_real_user_dpapi_round_trip_uses_only_synthetic_secret() -> None:
    protector = WindowsDpapiProtector()
    plaintext = b"mailcleanup synthetic dpapi validation"

    try:
        ciphertext = protector.protect(plaintext)
    except SecretStoreError as error:
        if error.code is SecretStoreErrorCode.UNAVAILABLE:
            pytest.skip("DPAPI user profile is unavailable in this execution context")
        raise

    assert ciphertext != plaintext
    assert protector.unprotect(ciphertext) == plaintext
