from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from urllib.parse import urlsplit

from mailmap.index_model import IndexedMessageRecord, SyncCheckpoint
from mailmap.policy_model import ActivePolicy, PolicyEvent, PreparedPolicyDecision, UndoPolicy

SYNTHETIC_MAP_ACCOUNT_KEY = "synthetic-map-v1"
SYNTHETIC_MAP_FIXTURE_VERSION = "map-total-synthetic-v1"

_EMAIL = re.compile(
    r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?P<domain>[A-Za-z0-9.-]+)",
    re.IGNORECASE,
)
_AUTHORITY_URL = re.compile(
    r"(?:(?:[A-Za-z][A-Za-z0-9+.-]*:)?//)[^\s<>\"']+",
    re.IGNORECASE,
)


class SyntheticMapGateError(ValueError):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("synthetic_map_gate_failed")

    def __repr__(self) -> str:
        return "SyntheticMapGateError()"


def _reject() -> None:
    raise SyntheticMapGateError()


def _is_example_domain(value: str) -> bool:
    normalized = value.rstrip(".").casefold()
    return bool(normalized) and normalized.endswith(".example")


def _assert_text_is_synthetic(value: str) -> None:
    if any(not _is_example_domain(match.group("domain")) for match in _EMAIL.finditer(value)):
        _reject()
    for match in _AUTHORITY_URL.finditer(value):
        candidate = match.group(0).rstrip(".,;:!?)]}")
        parsed = urlsplit(candidate)
        if parsed.hostname is None or not _is_example_domain(parsed.hostname):
            _reject()


def _assert_value_is_synthetic(value: object, seen: set[int] | None = None) -> None:
    if value is None or isinstance(value, (bool, int, float, bytes, date, datetime)):
        return
    if isinstance(value, Enum):
        _assert_value_is_synthetic(value.value, seen)
        return
    if isinstance(value, str):
        _assert_text_is_synthetic(value)
        return

    active = seen if seen is not None else set()
    identity = id(value)
    if identity in active:
        return
    active.add(identity)
    try:
        if is_dataclass(value) and not isinstance(value, type):
            for item in fields(value):
                _assert_value_is_synthetic(getattr(value, item.name), active)
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                _assert_value_is_synthetic(key, active)
                _assert_value_is_synthetic(item, active)
            return
        if isinstance(value, Iterable):
            for item in value:
                _assert_value_is_synthetic(item, active)
            return
    finally:
        active.remove(identity)
    _reject()


def _assert_record(record: IndexedMessageRecord) -> None:
    if not isinstance(record, IndexedMessageRecord):
        _reject()
    if record.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
        _reject()
    _assert_value_is_synthetic(record)

    if (
        record.sender_address is not None
        and "@" in record.sender_address
        and not _is_example_domain(record.sender_address.rsplit("@", 1)[1])
    ):
        _reject()
    if record.authenticated_domain is not None and not _is_example_domain(
        record.authenticated_domain
    ):
        _reject()
    if record.list_id is not None:
        list_id = record.list_id.strip()
        if list_id.startswith("<") and list_id.endswith(">"):
            list_id = list_id[1:-1].strip()
        if not list_id or any(character.isspace() for character in list_id):
            _reject()
        domain = list_id.rsplit("@", 1)[-1]
        if not _is_example_domain(domain):
            _reject()


def assert_synthetic_fixture_payload(
    *,
    account_key: str,
    fixture_version: str,
    records: tuple[IndexedMessageRecord, ...],
    checkpoint: SyncCheckpoint,
    policy_events: tuple[PolicyEvent, ...],
) -> None:
    if account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
        _reject()
    if fixture_version != SYNTHETIC_MAP_FIXTURE_VERSION:
        _reject()
    if not isinstance(records, tuple) or not isinstance(policy_events, tuple):
        _reject()
    for record in records:
        _assert_record(record)
    if not isinstance(checkpoint, SyncCheckpoint):
        _reject()
    if checkpoint.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
        _reject()
    _assert_value_is_synthetic(checkpoint)
    for event in policy_events:
        if not isinstance(event, PolicyEvent):
            _reject()
        if event.command.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
            _reject()
        _assert_value_is_synthetic(event)


def assert_synthetic_policy_candidate(
    value: PreparedPolicyDecision | UndoPolicy,
) -> None:
    if not isinstance(value, (PreparedPolicyDecision, UndoPolicy)):
        _reject()
    account_key = (
        value.command.account_key
        if isinstance(value, PreparedPolicyDecision)
        else value.account_key
    )
    if account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
        _reject()
    _assert_value_is_synthetic(value)


def assert_synthetic_map_snapshot(
    *,
    account_key: str,
    account_exists: bool,
    indexed_account_keys: tuple[str, ...],
    fixture_version: str | None,
    records: tuple[IndexedMessageRecord, ...],
    checkpoint: SyncCheckpoint | None,
    policy_history: tuple[PolicyEvent, ...],
    active_policies: tuple[ActivePolicy, ...],
) -> None:
    if account_key != SYNTHETIC_MAP_ACCOUNT_KEY or not account_exists:
        _reject()
    if indexed_account_keys != (SYNTHETIC_MAP_ACCOUNT_KEY,):
        _reject()
    if fixture_version != SYNTHETIC_MAP_FIXTURE_VERSION:
        _reject()
    for record in records:
        _assert_record(record)
    if checkpoint is not None:
        if checkpoint.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
            _reject()
        _assert_value_is_synthetic(checkpoint)
    for event in policy_history:
        if not isinstance(event, PolicyEvent):
            _reject()
        if event.command.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
            _reject()
        _assert_value_is_synthetic(event)
    for policy in active_policies:
        if not isinstance(policy, ActivePolicy):
            _reject()
        if policy.account_key != SYNTHETIC_MAP_ACCOUNT_KEY:
            _reject()
        _assert_value_is_synthetic(policy)
