from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import UTC, datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

from mailmap.fixtures import synthetic_messages
from mailmap.index_model import (
    IndexedMessageRecord,
    SyncCheckpoint,
    SyncMode,
    SyncState,
    validate_account_key,
    validate_opaque_identifier,
)
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_FIXTURE_VERSION,
    SyntheticMapGateError,
    assert_synthetic_fixture_payload,
    assert_synthetic_map_snapshot,
    assert_synthetic_policy_candidate,
)
from mailmap.model import DATASET_VERSION, Intencion, Proteccion, Rubro, SyntheticMessage
from mailmap.policy_model import (
    ActivePolicy,
    EffectiveFlowSelector,
    EffectiveSourceKind,
    EffectiveSourceSelector,
    FlowIdentityDescriptor,
    LabelSelector,
    LocalPolicyCommand,
    MergeSources,
    MessageSelector,
    PartitionAnchor,
    PartitionAnchorKind,
    PartitionGroup,
    PartitionSource,
    PolicyAnchorRole,
    PolicyCommandType,
    PolicyError,
    PolicyErrorCode,
    PolicyEvent,
    PolicyRelationKind,
    PolicySelectorKind,
    PolicyTargetSelector,
    PreparedPolicyAnchor,
    PreparedPolicyDecision,
    PreparedPolicyRelation,
    ProtectTarget,
    SenderSelector,
    SetFlowDisplayName,
    SetFlowIntention,
    SetSourceDisplayName,
    SetSourceRubro,
    SourceIdentityDescriptor,
    UndoPolicy,
    flow_identity_descriptor_from_parts,
    is_policy_decision_command,
    policy_selector_kind,
    source_identity_descriptor_from_parts,
)

MAP_INPUT_REVISION_VERSION = 1
MAP_POLICY_REQUEST_CONTRACT_VERSION = 1

_MAP_INPUT_REVISION = re.compile(r"^input-v1-[0-9a-f]{64}$")
_SHA256_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class MapRepositoryErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    MAP_REVISION_CONFLICT = "map_revision_conflict"
    COMMAND_ID_CONFLICT = "command_id_conflict"
    MAP_UNAVAILABLE = "map_unavailable"
    RECEIPT_CORRUPT = "receipt_corrupt"


class MapRepositoryError(RuntimeError):
    __slots__ = ()
    _RUNTIME_ATTRIBUTES = frozenset(
        {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
    )

    def __init__(self, code: MapRepositoryErrorCode) -> None:
        if not isinstance(code, MapRepositoryErrorCode):
            raise TypeError("code must be a MapRepositoryErrorCode")
        super().__init__(code.value)

    @property
    def code(self) -> MapRepositoryErrorCode:
        return MapRepositoryErrorCode(self.args[0])

    def __getattribute__(self, name: str) -> object:
        if name == "__dict__":
            raise AttributeError("MapRepositoryError is closed")
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__setattr__(self, name, value)
            return
        raise AttributeError("MapRepositoryError is immutable")

    def __delattr__(self, name: str) -> None:
        if name in self._RUNTIME_ATTRIBUTES:
            BaseException.__delattr__(self, name)
            return
        raise AttributeError("MapRepositoryError is immutable")

    def __repr__(self) -> str:
        return f"MapRepositoryError(code={self.code.value!r})"


@dataclass(frozen=True, slots=True, kw_only=True)
class MapInputSnapshot:
    account_key: str = field(repr=False)
    account_exists: bool
    indexed_account_keys: tuple[str, ...] = field(repr=False)
    fixture_version: str | None = field(repr=False)
    records: tuple[IndexedMessageRecord, ...] = field(repr=False)
    checkpoint: SyncCheckpoint | None = field(repr=False)
    policy_history: tuple[PolicyEvent, ...] = field(repr=False)
    active_policies: tuple[ActivePolicy, ...] = field(repr=False)
    policy_revision: int
    input_revision: str = field(repr=False)

    def __post_init__(self) -> None:
        validate_account_key(self.account_key)
        if not isinstance(self.account_exists, bool):
            raise TypeError("account_exists must be a boolean")
        if not isinstance(self.indexed_account_keys, tuple):
            raise TypeError("indexed_account_keys must be a tuple")
        for account_key in self.indexed_account_keys:
            validate_account_key(account_key)
        if self.indexed_account_keys != tuple(sorted(set(self.indexed_account_keys))):
            raise ValueError("indexed_account_keys must be canonical")
        if self.account_exists != (self.account_key in self.indexed_account_keys):
            raise ValueError("account_exists does not match indexed_account_keys")
        if self.fixture_version is not None and (
            not isinstance(self.fixture_version, str)
            or not self.fixture_version
            or self.fixture_version != self.fixture_version.strip()
        ):
            raise ValueError("fixture_version must be normalized or None")
        if not isinstance(self.records, tuple) or any(
            not isinstance(record, IndexedMessageRecord) for record in self.records
        ):
            raise TypeError("records must contain IndexedMessageRecord values")
        if any(record.account_key != self.account_key for record in self.records):
            raise ValueError("records reference another account")
        if self.checkpoint is not None and not isinstance(
            self.checkpoint, SyncCheckpoint
        ):
            raise TypeError("checkpoint must be a SyncCheckpoint or None")
        if self.checkpoint is not None and self.checkpoint.account_key != self.account_key:
            raise ValueError("checkpoint references another account")
        if not isinstance(self.policy_history, tuple) or any(
            not isinstance(event, PolicyEvent) for event in self.policy_history
        ):
            raise TypeError("policy_history must contain PolicyEvent values")
        if any(
            event.command.account_key != self.account_key for event in self.policy_history
        ):
            raise ValueError("policy_history references another account")
        if not isinstance(self.active_policies, tuple) or any(
            not isinstance(policy, ActivePolicy) for policy in self.active_policies
        ):
            raise TypeError("active_policies must contain ActivePolicy values")
        if any(policy.account_key != self.account_key for policy in self.active_policies):
            raise ValueError("active_policies reference another account")
        if isinstance(self.policy_revision, bool) or not isinstance(
            self.policy_revision, int
        ):
            raise TypeError("policy_revision must be an integer")
        expected_revision = (
            self.policy_history[-1].account_revision if self.policy_history else 0
        )
        if self.policy_revision != expected_revision:
            raise ValueError("policy_revision does not match policy_history")
        if _MAP_INPUT_REVISION.fullmatch(self.input_revision) is None:
            raise ValueError("input_revision must be a versioned opaque identifier")
        if not self.account_exists and (
            self.records
            or self.checkpoint is not None
            or self.policy_history
            or self.active_policies
            or self.policy_revision != 0
        ):
            raise ValueError("a missing account cannot contain account-scoped data")

    def __repr__(self) -> str:
        return (
            "MapInputSnapshot("
            f"account_exists={self.account_exists}, "
            f"indexed_account_count={len(self.indexed_account_keys)}, "
            f"fixture_version_present={self.fixture_version is not None}, "
            f"record_count={len(self.records)}, "
            "checkpoint_state="
            f"{self.checkpoint.state.value if self.checkpoint is not None else None!r}, "
            f"policy_event_count={len(self.policy_history)}, "
            f"active_policy_count={len(self.active_policies)}, "
            f"policy_revision={self.policy_revision}, "
            f"input_revision_version={MAP_INPUT_REVISION_VERSION})"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MapPolicyWriteResult:
    event: PolicyEvent = field(repr=False)
    replayed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.event, PolicyEvent):
            raise TypeError("event must be a PolicyEvent")
        if not isinstance(self.replayed, bool):
            raise TypeError("replayed must be a boolean")

    def __repr__(self) -> str:
        return (
            "MapPolicyWriteResult(event=<redacted>, "
            f"command_type={self.event.command.command_type.value!r}, "
            f"account_revision={self.event.account_revision}, "
            f"replayed={self.replayed})"
        )


def _canonical_json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical datetimes must include timezone information")
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require string keys")
        return {
            key: _canonical_json_value(item)
            for key, item in sorted(value.items())
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _canonical_json_value(getattr(value, item.name))
            for item in fields(value)
        }
    raise TypeError("value is not canonically serializable")


def _sha256_revision(payload: object) -> str:
    serialized = json.dumps(
        _canonical_json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"input-v{MAP_INPUT_REVISION_VERSION}-{hashlib.sha256(serialized).hexdigest()}"

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            labels_json TEXT NOT NULL,
            gmail_category TEXT NOT NULL,
            authenticated_domain TEXT,
            list_id TEXT,
            unsubscribe_method TEXT,
            dkim_pass INTEGER NOT NULL,
            dmarc_pass INTEGER NOT NULL,
            brand_hint TEXT,
            rubro_hint TEXT,
            flow_hint TEXT,
            personal_signal INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL,
            failure_state TEXT,
            fixture_tags_json TEXT NOT NULL,
            revision INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_received_at ON messages(received_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sender_email ON messages(sender_email);
        CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            selection_json TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS indexed_accounts (
            account_key TEXT PRIMARY KEY
                CHECK(length(trim(account_key)) > 0 AND instr(account_key, '@') = 0)
        );
        CREATE TABLE IF NOT EXISTS indexed_messages (
            account_key TEXT NOT NULL,
            provider_message_id TEXT NOT NULL CHECK(length(trim(provider_message_id)) > 0),
            provider_thread_id TEXT NOT NULL CHECK(length(trim(provider_thread_id)) > 0),
            received_at TEXT NOT NULL,
            sender_name TEXT,
            sender_address TEXT,
            subject TEXT,
            label_ids_json TEXT NOT NULL,
            category TEXT,
            size_estimate_bytes INTEGER NOT NULL CHECK(size_estimate_bytes >= 0),
            authenticated_domain TEXT,
            list_id TEXT,
            list_unsubscribe TEXT,
            list_unsubscribe_post TEXT,
            dkim_result TEXT CHECK(
                dkim_result IS NULL OR dkim_result IN ('pass', 'fail', 'neutral', 'unknown')
            ),
            dmarc_result TEXT CHECK(
                dmarc_result IS NULL OR dmarc_result IN ('pass', 'fail', 'neutral', 'unknown')
            ),
            record_version INTEGER NOT NULL CHECK(record_version = 1),
            PRIMARY KEY (account_key, provider_message_id),
            FOREIGN KEY (account_key) REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_received
            ON indexed_messages(account_key, received_at DESC, provider_message_id ASC);
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_thread
            ON indexed_messages(account_key, provider_thread_id);
        CREATE INDEX IF NOT EXISTS idx_indexed_messages_sender
            ON indexed_messages(account_key, sender_address);
        CREATE TABLE IF NOT EXISTS sync_checkpoints (
            account_key TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL CHECK(length(trim(scan_id)) > 0),
            mode TEXT NOT NULL CHECK(mode IN ('full', 'partial')),
            state TEXT NOT NULL CHECK(state IN (
                'not_started', 'running', 'paused', 'completed',
                'requires_full_resync', 'failed'
            )),
            page_token TEXT,
            history_id TEXT,
            processed_count INTEGER NOT NULL CHECK(processed_count >= 0),
            started_at TEXT,
            updated_at TEXT NOT NULL,
            error_code TEXT,
            CHECK(state != 'completed' OR page_token IS NULL),
            CHECK(state != 'requires_full_resync' OR page_token IS NULL),
            FOREIGN KEY (account_key) REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE local_policy_events (
            account_key TEXT NOT NULL
                CHECK(length(trim(account_key)) > 0 AND instr(account_key, '@') = 0),
            account_revision INTEGER NOT NULL CHECK(account_revision > 0),
            command_id TEXT NOT NULL CHECK(length(trim(command_id)) > 0),
            command_type TEXT NOT NULL CHECK(command_type IN (
                'set_source_display_name', 'set_source_rubro',
                'set_flow_display_name', 'set_flow_intention',
                'merge_sources', 'partition_source', 'protect_target', 'undo_policy'
            )),
            policy_version INTEGER NOT NULL CHECK(policy_version = 1),
            occurred_at TEXT NOT NULL CHECK(
                occurred_at = trim(occurred_at)
                AND instr(occurred_at, 'T') = 11
                AND substr(occurred_at, -6) = '+00:00'
                AND julianday(occurred_at) IS NOT NULL
            ),
            expected_revision INTEGER NOT NULL CHECK(expected_revision >= 0),
            decision_id TEXT CHECK(decision_id IS NULL OR length(trim(decision_id)) > 0),
            target_decision_id TEXT
                CHECK(target_decision_id IS NULL OR length(trim(target_decision_id)) > 0),
            display_name TEXT CHECK(display_name IS NULL OR length(trim(display_name)) > 0),
            rubro TEXT CHECK(rubro IS NULL OR rubro IN (
                'Medios y contenido', 'Software y servicios digitales',
                'Comercio y compras', 'Finanzas', 'Trabajo y educación',
                'Salud y gobierno', 'Viajes y entretenimiento',
                'Social y comunidades', 'Servicios domésticos', 'Personal', 'Desconocido'
            )),
            intention TEXT CHECK(intention IS NULL OR intention IN (
                'Seguridad', 'Documento o comprobante', 'Operativo o soporte',
                'Notificación', 'Informativo o editorial', 'Promocional o venta',
                'Comunicación personal', 'Sospechoso', 'Desconocido'
            )),
            protection TEXT CHECK(
                protection IS NULL OR protection = 'Elegida por el usuario'
            ),
            PRIMARY KEY (account_key, account_revision),
            UNIQUE (account_key, command_id),
            UNIQUE (account_key, decision_id),
            CHECK(account_revision = expected_revision + 1),
            CHECK(
                (command_type = 'set_source_display_name'
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NOT NULL AND rubro IS NULL
                    AND intention IS NULL AND protection IS NULL)
                OR
                (command_type = 'set_source_rubro'
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NULL AND rubro IS NOT NULL
                    AND intention IS NULL AND protection IS NULL)
                OR
                (command_type = 'set_flow_display_name'
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NOT NULL AND rubro IS NULL
                    AND intention IS NULL AND protection IS NULL)
                OR
                (command_type = 'set_flow_intention'
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NULL AND rubro IS NULL
                    AND intention IS NOT NULL AND protection IS NULL)
                OR
                (command_type IN ('merge_sources', 'partition_source')
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NULL AND rubro IS NULL
                    AND intention IS NULL AND protection IS NULL)
                OR
                (command_type = 'protect_target'
                    AND decision_id IS NOT NULL AND target_decision_id IS NULL
                    AND display_name IS NULL AND rubro IS NULL
                    AND intention IS NULL
                    AND protection = 'Elegida por el usuario')
                OR
                (command_type = 'undo_policy'
                    AND decision_id IS NULL AND target_decision_id IS NOT NULL
                    AND display_name IS NULL AND rubro IS NULL
                    AND intention IS NULL AND protection IS NULL)
            ),
            FOREIGN KEY (account_key) REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
        );
        CREATE INDEX idx_local_policy_events_history
            ON local_policy_events(account_key, account_revision);
        CREATE INDEX idx_local_policy_events_command
            ON local_policy_events(account_key, command_id);

        CREATE TABLE local_policy_anchors (
            account_key TEXT NOT NULL,
            account_revision INTEGER NOT NULL,
            anchor_order INTEGER NOT NULL CHECK(anchor_order >= 0),
            role TEXT NOT NULL CHECK(role IN (
                'target', 'merge_participant', 'partition_member'
            )),
            group_order INTEGER CHECK(group_order IS NULL OR group_order >= 0),
            selector_kind TEXT NOT NULL CHECK(selector_kind IN (
                'message', 'sender', 'label', 'effective_source',
                'effective_flow', 'partition_anchor'
            )),
            selector_version INTEGER NOT NULL CHECK(selector_version = 1),
            effective_source_kind TEXT CHECK(effective_source_kind IS NULL OR
                effective_source_kind IN ('automatic', 'merged', 'partition_group')),
            provider_message_id TEXT,
            target_sender_address TEXT,
            label_id TEXT,
            flow_kind TEXT CHECK(flow_kind IS NULL OR flow_kind IN (
                'list_intent', 'sender_intent', 'isolated_message'
            )),
            flow_version INTEGER CHECK(flow_version IS NULL OR flow_version = 1),
            flow_list_id TEXT,
            flow_sender_address TEXT,
            flow_automatic_intention TEXT CHECK(
                flow_automatic_intention IS NULL OR flow_automatic_intention IN (
                    'Seguridad', 'Documento o comprobante', 'Operativo o soporte',
                    'Notificación', 'Informativo o editorial', 'Promocional o venta',
                    'Comunicación personal', 'Sospechoso', 'Desconocido'
                )
            ),
            flow_isolated_message_id TEXT,
            flow_source_order INTEGER CHECK(
                flow_source_order IS NULL OR flow_source_order >= 0
            ),
            partition_anchor_kind TEXT CHECK(
                partition_anchor_kind IS NULL OR partition_anchor_kind IN (
                    'sender', 'flow', 'message'
                )
            ),
            partition_anchor_version INTEGER CHECK(
                partition_anchor_version IS NULL OR partition_anchor_version = 1
            ),
            partition_sender_address TEXT,
            partition_message_id TEXT,
            observed_effective_id TEXT,
            classification_version INTEGER NOT NULL CHECK(classification_version = 2),
            policy_version INTEGER NOT NULL CHECK(policy_version = 1),
            PRIMARY KEY (account_key, account_revision, anchor_order),
            CHECK(
                (role = 'partition_member' AND group_order IS NOT NULL
                    AND selector_kind = 'partition_anchor')
                OR
                (role != 'partition_member' AND group_order IS NULL
                    AND selector_kind != 'partition_anchor')
            ),
            CHECK(
                (selector_kind = 'message'
                    AND provider_message_id IS NOT NULL
                    AND target_sender_address IS NULL AND label_id IS NULL
                    AND effective_source_kind IS NULL AND flow_kind IS NULL
                    AND partition_anchor_kind IS NULL
                    AND observed_effective_id IS NULL)
                OR
                (selector_kind = 'sender'
                    AND provider_message_id IS NULL
                    AND target_sender_address IS NOT NULL AND label_id IS NULL
                    AND effective_source_kind IS NULL AND flow_kind IS NULL
                    AND partition_anchor_kind IS NULL
                    AND observed_effective_id IS NULL)
                OR
                (selector_kind = 'label'
                    AND provider_message_id IS NULL
                    AND target_sender_address IS NULL AND label_id IS NOT NULL
                    AND effective_source_kind IS NULL AND flow_kind IS NULL
                    AND partition_anchor_kind IS NULL
                    AND observed_effective_id IS NULL)
                OR
                (selector_kind = 'effective_source'
                    AND provider_message_id IS NULL
                    AND target_sender_address IS NULL AND label_id IS NULL
                    AND effective_source_kind IS NOT NULL AND flow_kind IS NULL
                    AND partition_anchor_kind IS NULL
                    AND observed_effective_id IS NOT NULL)
                OR
                (selector_kind = 'effective_flow'
                    AND provider_message_id IS NULL
                    AND target_sender_address IS NULL AND label_id IS NULL
                    AND effective_source_kind IS NOT NULL AND flow_kind IS NOT NULL
                    AND flow_version = 1 AND flow_automatic_intention IS NOT NULL
                    AND flow_source_order IS NOT NULL
                    AND partition_anchor_kind IS NULL
                    AND observed_effective_id IS NOT NULL)
                OR
                (selector_kind = 'partition_anchor'
                    AND provider_message_id IS NULL
                    AND target_sender_address IS NULL AND label_id IS NULL
                    AND effective_source_kind IS NULL
                    AND partition_anchor_kind IS NOT NULL
                    AND partition_anchor_version = 1
                    AND observed_effective_id IS NULL)
            ),
            CHECK(
                flow_kind IS NULL
                OR (flow_kind = 'list_intent'
                    AND flow_list_id IS NOT NULL
                    AND flow_sender_address IS NULL
                    AND flow_isolated_message_id IS NULL)
                OR (flow_kind = 'sender_intent'
                    AND flow_list_id IS NULL
                    AND flow_sender_address IS NOT NULL
                    AND flow_isolated_message_id IS NULL)
                OR (flow_kind = 'isolated_message'
                    AND flow_list_id IS NULL
                    AND flow_sender_address IS NULL
                    AND flow_isolated_message_id IS NOT NULL)
            ),
            CHECK(
                flow_kind IS NOT NULL
                OR (flow_version IS NULL AND flow_list_id IS NULL
                    AND flow_sender_address IS NULL
                    AND flow_automatic_intention IS NULL
                    AND flow_isolated_message_id IS NULL
                    AND flow_source_order IS NULL)
            ),
            CHECK(
                partition_anchor_kind IS NULL
                OR (partition_anchor_kind = 'sender'
                    AND partition_sender_address IS NOT NULL
                    AND partition_message_id IS NULL AND flow_kind IS NULL)
                OR (partition_anchor_kind = 'message'
                    AND partition_sender_address IS NULL
                    AND partition_message_id IS NOT NULL AND flow_kind IS NULL)
                OR (partition_anchor_kind = 'flow'
                    AND partition_sender_address IS NULL
                    AND partition_message_id IS NULL AND flow_kind IS NOT NULL
                    AND flow_version = 1 AND flow_automatic_intention IS NOT NULL
                    AND flow_source_order IS NOT NULL)
            ),
            CHECK(
                partition_anchor_kind IS NOT NULL
                OR (partition_anchor_version IS NULL
                    AND partition_sender_address IS NULL
                    AND partition_message_id IS NULL)
            ),
            FOREIGN KEY (account_key, account_revision)
                REFERENCES local_policy_events(account_key, account_revision)
                ON DELETE CASCADE
        );
        CREATE INDEX idx_local_policy_anchors_role
            ON local_policy_anchors(account_key, account_revision, role, anchor_order);

        CREATE TABLE local_policy_anchor_sources (
            account_key TEXT NOT NULL,
            account_revision INTEGER NOT NULL,
            anchor_order INTEGER NOT NULL,
            source_order INTEGER NOT NULL CHECK(source_order >= 0),
            member_order INTEGER NOT NULL CHECK(member_order >= 0),
            source_kind TEXT NOT NULL CHECK(source_kind IN ('senders', 'isolated_message')),
            source_version INTEGER NOT NULL CHECK(source_version = 1),
            sender_address TEXT,
            isolated_message_id TEXT,
            PRIMARY KEY (
                account_key, account_revision, anchor_order, source_order, member_order
            ),
            CHECK(
                (source_kind = 'senders'
                    AND sender_address IS NOT NULL AND isolated_message_id IS NULL)
                OR
                (source_kind = 'isolated_message'
                    AND member_order = 0 AND sender_address IS NULL
                    AND isolated_message_id IS NOT NULL)
            ),
            FOREIGN KEY (account_key, account_revision, anchor_order)
                REFERENCES local_policy_anchors(
                    account_key, account_revision, anchor_order
                ) ON DELETE CASCADE
        );

        CREATE TABLE local_policy_partition_members (
            account_key TEXT NOT NULL,
            account_revision INTEGER NOT NULL,
            anchor_order INTEGER NOT NULL,
            member_order INTEGER NOT NULL CHECK(member_order >= 0),
            anchor_kind TEXT NOT NULL CHECK(anchor_kind IN ('sender', 'flow', 'message')),
            anchor_version INTEGER NOT NULL CHECK(anchor_version = 1),
            sender_address TEXT,
            provider_message_id TEXT,
            flow_kind TEXT CHECK(flow_kind IS NULL OR flow_kind IN (
                'list_intent', 'sender_intent', 'isolated_message'
            )),
            flow_version INTEGER CHECK(flow_version IS NULL OR flow_version = 1),
            flow_list_id TEXT,
            flow_sender_address TEXT,
            flow_automatic_intention TEXT CHECK(
                flow_automatic_intention IS NULL OR flow_automatic_intention IN (
                    'Seguridad', 'Documento o comprobante', 'Operativo o soporte',
                    'Notificación', 'Informativo o editorial', 'Promocional o venta',
                    'Comunicación personal', 'Sospechoso', 'Desconocido'
                )
            ),
            flow_isolated_message_id TEXT,
            PRIMARY KEY (account_key, account_revision, anchor_order, member_order),
            CHECK(
                (anchor_kind = 'sender' AND sender_address IS NOT NULL
                    AND provider_message_id IS NULL AND flow_kind IS NULL)
                OR
                (anchor_kind = 'message' AND sender_address IS NULL
                    AND provider_message_id IS NOT NULL AND flow_kind IS NULL)
                OR
                (anchor_kind = 'flow' AND sender_address IS NULL
                    AND provider_message_id IS NULL AND flow_kind IS NOT NULL
                    AND flow_version = 1 AND flow_automatic_intention IS NOT NULL)
            ),
            CHECK(
                flow_kind IS NULL
                OR (flow_kind = 'list_intent' AND flow_list_id IS NOT NULL
                    AND flow_sender_address IS NULL
                    AND flow_isolated_message_id IS NULL)
                OR (flow_kind = 'sender_intent' AND flow_list_id IS NULL
                    AND flow_sender_address IS NOT NULL
                    AND flow_isolated_message_id IS NULL)
                OR (flow_kind = 'isolated_message' AND flow_list_id IS NULL
                    AND flow_sender_address IS NULL
                    AND flow_isolated_message_id IS NOT NULL)
            ),
            CHECK(
                flow_kind IS NOT NULL
                OR (flow_version IS NULL AND flow_list_id IS NULL
                    AND flow_sender_address IS NULL
                    AND flow_automatic_intention IS NULL
                    AND flow_isolated_message_id IS NULL)
            ),
            FOREIGN KEY (account_key, account_revision, anchor_order)
                REFERENCES local_policy_anchors(
                    account_key, account_revision, anchor_order
                ) ON DELETE CASCADE
        );

        CREATE TABLE local_policy_observed_ids (
            account_key TEXT NOT NULL,
            account_revision INTEGER NOT NULL,
            anchor_order INTEGER NOT NULL,
            observed_kind TEXT NOT NULL CHECK(observed_kind IN ('source', 'flow')),
            observed_order INTEGER NOT NULL CHECK(observed_order >= 0),
            observed_id TEXT NOT NULL CHECK(length(trim(observed_id)) > 0),
            PRIMARY KEY (
                account_key, account_revision, anchor_order,
                observed_kind, observed_order
            ),
            UNIQUE (
                account_key, account_revision, anchor_order,
                observed_kind, observed_id
            ),
            FOREIGN KEY (account_key, account_revision, anchor_order)
                REFERENCES local_policy_anchors(
                    account_key, account_revision, anchor_order
                ) ON DELETE CASCADE
        );

        CREATE TABLE local_policy_relations (
            account_key TEXT NOT NULL,
            account_revision INTEGER NOT NULL,
            relation_order INTEGER NOT NULL CHECK(relation_order >= 0),
            relation_kind TEXT NOT NULL CHECK(relation_kind IN (
                'supersedes', 'undoes', 'structural_context'
            )),
            anchor_order INTEGER,
            target_decision_id TEXT NOT NULL CHECK(length(trim(target_decision_id)) > 0),
            policy_version INTEGER NOT NULL CHECK(policy_version = 1),
            PRIMARY KEY (account_key, account_revision, relation_order),
            UNIQUE (
                account_key, account_revision, relation_kind,
                anchor_order, target_decision_id
            ),
            CHECK(
                (relation_kind = 'structural_context' AND anchor_order IS NOT NULL)
                OR
                (relation_kind != 'structural_context' AND anchor_order IS NULL)
            ),
            FOREIGN KEY (account_key, account_revision)
                REFERENCES local_policy_events(account_key, account_revision)
                ON DELETE CASCADE,
            FOREIGN KEY (account_key, target_decision_id)
                REFERENCES local_policy_events(account_key, decision_id),
            FOREIGN KEY (account_key, account_revision, anchor_order)
                REFERENCES local_policy_anchors(
                    account_key, account_revision, anchor_order
                ) ON DELETE CASCADE
        );
        CREATE INDEX idx_local_policy_relations_target
            ON local_policy_relations(account_key, target_decision_id, relation_kind);
        CREATE UNIQUE INDEX idx_local_policy_relations_unique
            ON local_policy_relations(
                account_key, account_revision, relation_kind,
                ifnull(anchor_order, -1), target_decision_id
            );
        """,
    ),
    (
        4,
        """
        CREATE TABLE map_policy_requests (
            account_key TEXT NOT NULL,
            command_id TEXT NOT NULL CHECK(length(trim(command_id)) > 0),
            contract_version INTEGER NOT NULL CHECK(contract_version = 1),
            request_fingerprint TEXT NOT NULL CHECK(
                length(request_fingerprint) = 64
                AND request_fingerprint NOT GLOB '*[^0-9a-f]*'
            ),
            PRIMARY KEY (account_key, command_id),
            FOREIGN KEY (account_key, command_id)
                REFERENCES local_policy_events(account_key, command_id)
                ON DELETE CASCADE,
            FOREIGN KEY (account_key)
                REFERENCES indexed_accounts(account_key)
                ON DELETE CASCADE
        );
        CREATE INDEX idx_map_policy_requests_event
            ON map_policy_requests(account_key, command_id);
        """,
    ),
)


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()
        self._seed_if_needed()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                int(row[0])
                for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
            }
            for version, script in MIGRATIONS:
                if version in applied:
                    continue
                connection.executescript("BEGIN IMMEDIATE;\n" + script)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, datetime.now().astimezone().isoformat()),
                )

    def _seed_if_needed(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_meta WHERE key = 'dataset_version'"
            ).fetchone()
            if row and row[0] == DATASET_VERSION:
                return
            connection.execute("DELETE FROM plans")
            connection.execute("DELETE FROM messages")
            self._insert_messages(connection, synthetic_messages())
            connection.execute(
                "INSERT INTO app_meta(key, value) VALUES ('dataset_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (DATASET_VERSION,),
            )
            connection.execute(
                "INSERT INTO app_meta(key, value) VALUES ('mode', 'synthetic') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )

    def _insert_messages(
        self, connection: sqlite3.Connection, messages: Iterable[SyntheticMessage]
    ) -> None:
        connection.executemany(
            """
            INSERT INTO messages(
                id, thread_id, received_at, sender_name, sender_email, subject,
                labels_json, gmail_category, authenticated_domain, list_id,
                unsubscribe_method, dkim_pass, dmarc_pass, brand_hint, rubro_hint,
                flow_hint, personal_signal, size_bytes, failure_state,
                fixture_tags_json, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    message.id,
                    message.thread_id,
                    message.received_at.isoformat(),
                    message.sender_name,
                    message.sender_email,
                    message.subject,
                    json.dumps(message.labels, ensure_ascii=False),
                    message.gmail_category,
                    message.authenticated_domain,
                    message.list_id,
                    message.unsubscribe_method,
                    int(message.dkim_pass),
                    int(message.dmarc_pass),
                    message.brand_hint,
                    message.rubro_hint.value if message.rubro_hint else None,
                    message.flow_hint.value if message.flow_hint else None,
                    int(message.personal_signal),
                    message.size_bytes,
                    message.failure_state,
                    json.dumps(message.fixture_tags, ensure_ascii=False),
                    message.revision,
                )
                for message in messages
            ],
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> SyntheticMessage:
        return SyntheticMessage(
            id=str(row["id"]),
            thread_id=str(row["thread_id"]),
            received_at=datetime.fromisoformat(str(row["received_at"])),
            sender_name=str(row["sender_name"]),
            sender_email=str(row["sender_email"]),
            subject=str(row["subject"]),
            labels=tuple(json.loads(str(row["labels_json"]))),
            gmail_category=str(row["gmail_category"]),
            authenticated_domain=(
                str(row["authenticated_domain"]) if row["authenticated_domain"] else None
            ),
            list_id=str(row["list_id"]) if row["list_id"] else None,
            unsubscribe_method=(
                str(row["unsubscribe_method"]) if row["unsubscribe_method"] else None
            ),
            dkim_pass=bool(row["dkim_pass"]),
            dmarc_pass=bool(row["dmarc_pass"]),
            brand_hint=str(row["brand_hint"]) if row["brand_hint"] else None,
            rubro_hint=Rubro(str(row["rubro_hint"])) if row["rubro_hint"] else None,
            flow_hint=Intencion(str(row["flow_hint"])) if row["flow_hint"] else None,
            personal_signal=bool(row["personal_signal"]),
            size_bytes=int(row["size_bytes"]),
            failure_state=str(row["failure_state"]) if row["failure_state"] else None,
            fixture_tags=tuple(json.loads(str(row["fixture_tags_json"]))),
            revision=int(row["revision"]),
        )

    def messages(self) -> tuple[SyntheticMessage, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages ORDER BY received_at DESC, id ASC"
            ).fetchall()
        return tuple(self._message_from_row(row) for row in rows)

    def message(self, message_id: str) -> SyntheticMessage | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
        return self._message_from_row(row) if row else None

    def update_labels(self, message_id: str, labels: tuple[str, ...]) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE messages SET labels_json = ?, revision = revision + 1 WHERE id = ?",
                (json.dumps(labels, ensure_ascii=False), message_id),
            )
            if updated.rowcount != 1:
                raise KeyError(message_id)

    def save_plan(
        self,
        *,
        plan_id: str,
        created_at: str,
        selection: dict[str, Any],
        snapshot: dict[str, Any],
        status: str = "simulated",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plans(id, created_at, selection_json, snapshot_json, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    created_at = excluded.created_at,
                    selection_json = excluded.selection_json,
                    snapshot_json = excluded.snapshot_json,
                    status = excluded.status
                """,
                (
                    plan_id,
                    created_at,
                    json.dumps(selection, ensure_ascii=False, sort_keys=True),
                    json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                    status,
                ),
            )

    def plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "createdAt": str(row["created_at"]),
            "selection": json.loads(str(row["selection_json"])),
            "snapshot": json.loads(str(row["snapshot_json"])),
            "status": str(row["status"]),
        }

    def plans(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM plans ORDER BY created_at DESC").fetchall()
        return [plan for row in rows if (plan := self.plan(str(row["id"]))) is not None]

    @staticmethod
    def _indexed_message_values(record: IndexedMessageRecord) -> tuple[object, ...]:
        return (
            record.account_key,
            record.provider_message_id,
            record.provider_thread_id,
            record.received_at.isoformat(),
            record.sender_name,
            record.sender_address,
            record.subject,
            json.dumps(record.label_ids, ensure_ascii=False, separators=(",", ":")),
            record.category,
            record.size_estimate_bytes,
            record.authenticated_domain,
            record.list_id,
            record.list_unsubscribe,
            record.list_unsubscribe_post,
            record.dkim_result,
            record.dmarc_result,
            record.record_version,
        )

    @staticmethod
    def _indexed_message_from_row(row: sqlite3.Row) -> IndexedMessageRecord:
        raw_labels = json.loads(str(row["label_ids_json"]))
        if not isinstance(raw_labels, list) or not all(
            isinstance(label, str) for label in raw_labels
        ):
            raise ValueError("Stored label_ids_json is not a string list")
        labels = tuple(label for label in raw_labels if isinstance(label, str))
        return IndexedMessageRecord(
            account_key=str(row["account_key"]),
            provider_message_id=str(row["provider_message_id"]),
            provider_thread_id=str(row["provider_thread_id"]),
            received_at=datetime.fromisoformat(str(row["received_at"])),
            sender_name=str(row["sender_name"]) if row["sender_name"] is not None else None,
            sender_address=(
                str(row["sender_address"]) if row["sender_address"] is not None else None
            ),
            subject=str(row["subject"]) if row["subject"] is not None else None,
            label_ids=labels,
            category=str(row["category"]) if row["category"] is not None else None,
            size_estimate_bytes=int(row["size_estimate_bytes"]),
            authenticated_domain=(
                str(row["authenticated_domain"])
                if row["authenticated_domain"] is not None
                else None
            ),
            list_id=str(row["list_id"]) if row["list_id"] is not None else None,
            list_unsubscribe=(
                str(row["list_unsubscribe"])
                if row["list_unsubscribe"] is not None
                else None
            ),
            list_unsubscribe_post=(
                str(row["list_unsubscribe_post"])
                if row["list_unsubscribe_post"] is not None
                else None
            ),
            dkim_result=(
                str(row["dkim_result"]) if row["dkim_result"] is not None else None
            ),
            dmarc_result=(
                str(row["dmarc_result"]) if row["dmarc_result"] is not None else None
            ),
            record_version=int(row["record_version"]),
        )

    @staticmethod
    def _checkpoint_values(checkpoint: SyncCheckpoint) -> tuple[object, ...]:
        return (
            checkpoint.account_key,
            checkpoint.scan_id,
            checkpoint.mode.value,
            checkpoint.state.value,
            checkpoint.page_token,
            checkpoint.history_id,
            checkpoint.processed_count,
            checkpoint.started_at.isoformat() if checkpoint.started_at else None,
            checkpoint.updated_at.isoformat(),
            checkpoint.error_code,
        )

    @staticmethod
    def _checkpoint_from_row(row: sqlite3.Row) -> SyncCheckpoint:
        return SyncCheckpoint(
            account_key=str(row["account_key"]),
            scan_id=str(row["scan_id"]),
            mode=SyncMode(str(row["mode"])),
            state=SyncState(str(row["state"])),
            page_token=str(row["page_token"]) if row["page_token"] is not None else None,
            history_id=str(row["history_id"]) if row["history_id"] is not None else None,
            processed_count=int(row["processed_count"]),
            started_at=(
                datetime.fromisoformat(str(row["started_at"]))
                if row["started_at"] is not None
                else None
            ),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            error_code=str(row["error_code"]) if row["error_code"] is not None else None,
        )

    @staticmethod
    def _policy_event_values(
        command: LocalPolicyCommand,
        account_revision: int,
    ) -> tuple[object, ...]:
        decision_id: str | None = None
        target_decision_id: str | None = None
        display_name: str | None = None
        rubro: str | None = None
        intention: str | None = None
        protection: str | None = None
        if is_policy_decision_command(command):
            decision_id = command.decision_id
            if isinstance(command, (SetSourceDisplayName, SetFlowDisplayName)):
                display_name = command.display_name
            elif isinstance(command, SetSourceRubro):
                rubro = command.rubro.value
            elif isinstance(command, SetFlowIntention):
                intention = command.intention.value
            elif isinstance(command, ProtectTarget):
                protection = command.protection.value
        elif isinstance(command, UndoPolicy):
            target_decision_id = command.target_decision_id
        else:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        return (
            command.account_key,
            account_revision,
            command.command_id,
            command.command_type.value,
            command.version,
            command.occurred_at.isoformat(),
            command.expected_revision,
            decision_id,
            target_decision_id,
            display_name,
            rubro,
            intention,
            protection,
        )

    @staticmethod
    def _insert_policy_event(
        connection: sqlite3.Connection,
        command: LocalPolicyCommand,
        account_revision: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO local_policy_events(
                account_key, account_revision, command_id, command_type,
                policy_version, occurred_at, expected_revision, decision_id,
                target_decision_id, display_name, rubro, intention, protection
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            Repository._policy_event_values(command, account_revision),
        )

    @staticmethod
    def _flow_parts(
        flow: FlowIdentityDescriptor,
        source_order: int,
    ) -> tuple[object, ...]:
        return (
            flow.kind.value,
            flow.version,
            flow.list_id,
            flow.sender_address,
            flow.automatic_intention.value,
            flow.isolated_message_id,
            source_order,
        )

    @staticmethod
    def _insert_anchor_sources(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        anchor_order: int,
        sources: tuple[SourceIdentityDescriptor, ...],
    ) -> None:
        rows: list[tuple[object, ...]] = []
        for source_order, source in enumerate(sources):
            if source.sender_addresses:
                rows.extend(
                    (
                        account_key,
                        account_revision,
                        anchor_order,
                        source_order,
                        member_order,
                        source.kind.value,
                        source.version,
                        sender_address,
                        None,
                    )
                    for member_order, sender_address in enumerate(
                        source.sender_addresses
                    )
                )
            else:
                rows.append(
                    (
                        account_key,
                        account_revision,
                        anchor_order,
                        source_order,
                        0,
                        source.kind.value,
                        source.version,
                        None,
                        source.isolated_message_id,
                    )
                )
        connection.executemany(
            """
            INSERT INTO local_policy_anchor_sources(
                account_key, account_revision, anchor_order, source_order,
                member_order, source_kind, source_version, sender_address,
                isolated_message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    @staticmethod
    def _insert_partition_members(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        anchor_order: int,
        anchors: tuple[PartitionAnchor, ...],
    ) -> None:
        rows: list[tuple[object, ...]] = []
        for member_order, anchor in enumerate(anchors):
            flow_parts: tuple[object, ...] = (None, None, None, None, None, None)
            if anchor.flow is not None:
                flow_parts = Repository._flow_parts(anchor.flow, 0)[:-1]
            rows.append(
                (
                    account_key,
                    account_revision,
                    anchor_order,
                    member_order,
                    anchor.kind.value,
                    anchor.version,
                    anchor.sender_address,
                    anchor.provider_message_id,
                    *flow_parts,
                )
            )
        connection.executemany(
            """
            INSERT INTO local_policy_partition_members(
                account_key, account_revision, anchor_order, member_order,
                anchor_kind, anchor_version, sender_address,
                provider_message_id, flow_kind, flow_version, flow_list_id,
                flow_sender_address, flow_automatic_intention,
                flow_isolated_message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    @staticmethod
    def _insert_policy_anchor(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        anchor: PreparedPolicyAnchor,
    ) -> None:
        selector = anchor.selector
        selector_kind = policy_selector_kind(selector)
        effective_source_kind: str | None = None
        provider_message_id: str | None = None
        target_sender_address: str | None = None
        label_id: str | None = None
        flow_parts: tuple[object, ...] = (None, None, None, None, None, None, None)
        partition_anchor_kind: str | None = None
        partition_anchor_version: int | None = None
        partition_sender_address: str | None = None
        partition_message_id: str | None = None
        sources: tuple[SourceIdentityDescriptor, ...] = ()
        partition_members: tuple[PartitionAnchor, ...] = ()
        if isinstance(selector, MessageSelector):
            provider_message_id = selector.provider_message_id
        elif isinstance(selector, SenderSelector):
            target_sender_address = selector.sender_address
        elif isinstance(selector, LabelSelector):
            label_id = selector.label_id
        elif isinstance(selector, EffectiveSourceSelector):
            effective_source_kind = selector.kind.value
            sources = selector.automatic_sources
            partition_members = selector.partition_anchors
        elif isinstance(selector, EffectiveFlowSelector):
            effective_source_kind = selector.effective_source.kind.value
            sources = selector.effective_source.automatic_sources
            partition_members = selector.effective_source.partition_anchors
            flow_source_order = sources.index(selector.automatic_flow.source)
            flow_parts = Repository._flow_parts(
                selector.automatic_flow, flow_source_order
            )
        elif isinstance(selector, PartitionAnchor):
            partition_anchor_kind = selector.kind.value
            partition_anchor_version = selector.version
            partition_sender_address = selector.sender_address
            partition_message_id = selector.provider_message_id
            if selector.flow is not None:
                sources = (selector.flow.source,)
                flow_parts = Repository._flow_parts(selector.flow, 0)
        else:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        connection.execute(
            """
            INSERT INTO local_policy_anchors(
                account_key, account_revision, anchor_order, role, group_order,
                selector_kind, selector_version, effective_source_kind,
                provider_message_id, target_sender_address, label_id,
                flow_kind, flow_version, flow_list_id, flow_sender_address,
                flow_automatic_intention, flow_isolated_message_id,
                flow_source_order, partition_anchor_kind,
                partition_anchor_version, partition_sender_address,
                partition_message_id, observed_effective_id,
                classification_version, policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_key,
                account_revision,
                anchor.anchor_order,
                anchor.role.value,
                anchor.group_order,
                selector_kind.value,
                selector.version,
                effective_source_kind,
                provider_message_id,
                target_sender_address,
                label_id,
                *flow_parts,
                partition_anchor_kind,
                partition_anchor_version,
                partition_sender_address,
                partition_message_id,
                anchor.observed_effective_id,
                anchor.classification_version,
                anchor.version,
            ),
        )
        if sources:
            Repository._insert_anchor_sources(
                connection,
                account_key,
                account_revision,
                anchor.anchor_order,
                sources,
            )
        if partition_members:
            Repository._insert_partition_members(
                connection,
                account_key,
                account_revision,
                anchor.anchor_order,
                partition_members,
            )
        observed_rows = [
            (
                account_key,
                account_revision,
                anchor.anchor_order,
                kind,
                index,
                observed_id,
            )
            for kind, values in (
                ("source", anchor.observed_source_ids),
                ("flow", anchor.observed_flow_ids),
            )
            for index, observed_id in enumerate(values)
        ]
        connection.executemany(
            """
            INSERT INTO local_policy_observed_ids(
                account_key, account_revision, anchor_order,
                observed_kind, observed_order, observed_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            observed_rows,
        )

    @staticmethod
    def _insert_policy_relation(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        relation: PreparedPolicyRelation,
    ) -> None:
        connection.execute(
            """
            INSERT INTO local_policy_relations(
                account_key, account_revision, relation_order, relation_kind,
                anchor_order, target_decision_id, policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_key,
                account_revision,
                relation.relation_order,
                relation.kind.value,
                relation.anchor_order,
                relation.target_decision_id,
                relation.version,
            ),
        )

    @staticmethod
    def _source_descriptors_for_anchor(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        anchor_order: int,
    ) -> tuple[SourceIdentityDescriptor, ...]:
        rows = connection.execute(
            """
            SELECT * FROM local_policy_anchor_sources
            WHERE account_key = ? AND account_revision = ? AND anchor_order = ?
            ORDER BY source_order, member_order
            """,
            (account_key, account_revision, anchor_order),
        ).fetchall()
        grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in rows:
            grouped[int(row["source_order"])].append(row)
        if tuple(grouped) != tuple(range(len(grouped))):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        results: list[SourceIdentityDescriptor] = []
        for source_order in range(len(grouped)):
            members = grouped[source_order]
            if tuple(int(row["member_order"]) for row in members) != tuple(
                range(len(members))
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            kinds = {str(row["source_kind"]) for row in members}
            versions = {int(row["source_version"]) for row in members}
            if len(kinds) != 1 or len(versions) != 1:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            results.append(
                source_identity_descriptor_from_parts(
                    kind=next(iter(kinds)),
                    sender_addresses=tuple(
                        str(row["sender_address"])
                        for row in members
                        if row["sender_address"] is not None
                    ),
                    isolated_message_id=(
                        str(members[0]["isolated_message_id"])
                        if members[0]["isolated_message_id"] is not None
                        else None
                    ),
                    version=next(iter(versions)),
                )
            )
        return tuple(results)

    @staticmethod
    def _flow_from_columns(
        row: sqlite3.Row,
        source: SourceIdentityDescriptor,
    ) -> FlowIdentityDescriptor:
        if row["flow_kind"] is None or row["flow_version"] is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        return flow_identity_descriptor_from_parts(
            kind=str(row["flow_kind"]),
            source=source,
            list_id=(
                str(row["flow_list_id"])
                if row["flow_list_id"] is not None
                else None
            ),
            sender_address=(
                str(row["flow_sender_address"])
                if row["flow_sender_address"] is not None
                else None
            ),
            automatic_intention=Intencion(str(row["flow_automatic_intention"])),
            isolated_message_id=(
                str(row["flow_isolated_message_id"])
                if row["flow_isolated_message_id"] is not None
                else None
            ),
            version=int(row["flow_version"]),
        )

    @staticmethod
    def _partition_members_for_anchor(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        anchor_order: int,
        sources: tuple[SourceIdentityDescriptor, ...],
    ) -> tuple[PartitionAnchor, ...]:
        rows = connection.execute(
            """
            SELECT * FROM local_policy_partition_members
            WHERE account_key = ? AND account_revision = ? AND anchor_order = ?
            ORDER BY member_order
            """,
            (account_key, account_revision, anchor_order),
        ).fetchall()
        if tuple(int(row["member_order"]) for row in rows) != tuple(range(len(rows))):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        results: list[PartitionAnchor] = []
        for row in rows:
            kind = PartitionAnchorKind(str(row["anchor_kind"]))
            flow: FlowIdentityDescriptor | None = None
            if kind is PartitionAnchorKind.FLOW:
                if len(sources) != 1:
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                flow = Repository._flow_from_columns(row, sources[0])
            results.append(
                PartitionAnchor(
                    kind=kind,
                    sender_address=(
                        str(row["sender_address"])
                        if row["sender_address"] is not None
                        else None
                    ),
                    flow=flow,
                    provider_message_id=(
                        str(row["provider_message_id"])
                        if row["provider_message_id"] is not None
                        else None
                    ),
                    version=int(row["anchor_version"]),
                )
            )
        return tuple(results)

    @staticmethod
    def _selector_from_anchor_row(
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> PolicyTargetSelector | PartitionAnchor:
        account_key = str(row["account_key"])
        account_revision = int(row["account_revision"])
        anchor_order = int(row["anchor_order"])
        selector_kind = PolicySelectorKind(str(row["selector_kind"]))
        selector_version = int(row["selector_version"])
        sources = Repository._source_descriptors_for_anchor(
            connection, account_key, account_revision, anchor_order
        )
        partition_members = Repository._partition_members_for_anchor(
            connection,
            account_key,
            account_revision,
            anchor_order,
            sources,
        )
        if selector_kind is PolicySelectorKind.MESSAGE:
            if sources or partition_members:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return MessageSelector(
                account_key=account_key,
                provider_message_id=str(row["provider_message_id"]),
                version=selector_version,
            )
        if selector_kind is PolicySelectorKind.SENDER:
            if sources or partition_members:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return SenderSelector(
                account_key=account_key,
                sender_address=str(row["target_sender_address"]),
                version=selector_version,
            )
        if selector_kind is PolicySelectorKind.LABEL:
            if sources or partition_members:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return LabelSelector(
                account_key=account_key,
                label_id=str(row["label_id"]),
                version=selector_version,
            )
        if selector_kind in {
            PolicySelectorKind.EFFECTIVE_SOURCE,
            PolicySelectorKind.EFFECTIVE_FLOW,
        }:
            effective_source = EffectiveSourceSelector(
                account_key=account_key,
                kind=EffectiveSourceKind(str(row["effective_source_kind"])),
                automatic_sources=sources,
                partition_anchors=partition_members,
                version=selector_version,
            )
            if selector_kind is PolicySelectorKind.EFFECTIVE_SOURCE:
                return effective_source
            source_order = int(row["flow_source_order"])
            if source_order < 0 or source_order >= len(sources):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return EffectiveFlowSelector(
                account_key=account_key,
                automatic_flow=Repository._flow_from_columns(
                    row, sources[source_order]
                ),
                effective_source=effective_source,
                version=selector_version,
            )
        if selector_kind is not PolicySelectorKind.PARTITION_ANCHOR:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        kind = PartitionAnchorKind(str(row["partition_anchor_kind"]))
        flow = None
        if kind is PartitionAnchorKind.FLOW:
            if len(sources) != 1:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            flow = Repository._flow_from_columns(row, sources[0])
        elif sources or partition_members:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        return PartitionAnchor(
            kind=kind,
            sender_address=(
                str(row["partition_sender_address"])
                if row["partition_sender_address"] is not None
                else None
            ),
            flow=flow,
            provider_message_id=(
                str(row["partition_message_id"])
                if row["partition_message_id"] is not None
                else None
            ),
            version=selector_version,
        )

    @staticmethod
    def _relations_for_event(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
    ) -> tuple[PreparedPolicyRelation, ...]:
        rows = connection.execute(
            """
            SELECT * FROM local_policy_relations
            WHERE account_key = ? AND account_revision = ?
            ORDER BY relation_order
            """,
            (account_key, account_revision),
        ).fetchall()
        if any(int(row["policy_version"]) != 1 for row in rows):
            raise PolicyError(PolicyErrorCode.UNKNOWN_POLICY_VERSION)
        return tuple(
            PreparedPolicyRelation(
                relation_order=int(row["relation_order"]),
                kind=PolicyRelationKind(str(row["relation_kind"])),
                target_decision_id=str(row["target_decision_id"]),
                anchor_order=(
                    int(row["anchor_order"])
                    if row["anchor_order"] is not None
                    else None
                ),
                version=int(row["policy_version"]),
            )
            for row in rows
        )

    @staticmethod
    def _anchors_for_event(
        connection: sqlite3.Connection,
        account_key: str,
        account_revision: int,
        relations: tuple[PreparedPolicyRelation, ...],
    ) -> tuple[PreparedPolicyAnchor, ...]:
        rows = connection.execute(
            """
            SELECT * FROM local_policy_anchors
            WHERE account_key = ? AND account_revision = ?
            ORDER BY anchor_order
            """,
            (account_key, account_revision),
        ).fetchall()
        results: list[PreparedPolicyAnchor] = []
        for row in rows:
            if int(row["policy_version"]) != 1:
                raise PolicyError(PolicyErrorCode.UNKNOWN_POLICY_VERSION)
            anchor_order = int(row["anchor_order"])
            observed_rows = connection.execute(
                """
                SELECT observed_kind, observed_order, observed_id
                FROM local_policy_observed_ids
                WHERE account_key = ? AND account_revision = ? AND anchor_order = ?
                ORDER BY observed_kind, observed_order
                """,
                (account_key, account_revision, anchor_order),
            ).fetchall()
            for observed_kind in ("source", "flow"):
                orders = tuple(
                    int(observed["observed_order"])
                    for observed in observed_rows
                    if str(observed["observed_kind"]) == observed_kind
                )
                if orders != tuple(range(len(orders))):
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            observed_source_ids = tuple(
                str(observed["observed_id"])
                for observed in observed_rows
                if str(observed["observed_kind"]) == "source"
            )
            observed_flow_ids = tuple(
                str(observed["observed_id"])
                for observed in observed_rows
                if str(observed["observed_kind"]) == "flow"
            )
            structural_ids = tuple(
                relation.target_decision_id
                for relation in relations
                if relation.kind is PolicyRelationKind.STRUCTURAL_CONTEXT
                and relation.anchor_order == anchor_order
            )
            results.append(
                PreparedPolicyAnchor(
                    anchor_order=anchor_order,
                    role=PolicyAnchorRole(str(row["role"])),
                    selector=Repository._selector_from_anchor_row(connection, row),
                    group_order=(
                        int(row["group_order"])
                        if row["group_order"] is not None
                        else None
                    ),
                    classification_version=int(row["classification_version"]),
                    observed_effective_id=(
                        str(row["observed_effective_id"])
                        if row["observed_effective_id"] is not None
                        else None
                    ),
                    observed_source_ids=observed_source_ids,
                    observed_flow_ids=observed_flow_ids,
                    structural_decision_ids=structural_ids,
                    version=int(row["policy_version"]),
                )
            )
        return tuple(results)

    @staticmethod
    def _command_from_event_row(
        row: sqlite3.Row,
        anchors: tuple[PreparedPolicyAnchor, ...],
        relations: tuple[PreparedPolicyRelation, ...],
    ) -> LocalPolicyCommand:
        account_key = str(row["account_key"])
        command_id = str(row["command_id"])
        occurred_at = datetime.fromisoformat(str(row["occurred_at"]))
        expected_revision = int(row["expected_revision"])
        version = int(row["policy_version"])
        command_type = PolicyCommandType(str(row["command_type"]))
        supersedes = tuple(
            relation.target_decision_id
            for relation in relations
            if relation.kind is PolicyRelationKind.SUPERSEDES
        )
        decision_id = (
            str(row["decision_id"]) if row["decision_id"] is not None else None
        )

        if command_type is PolicyCommandType.UNDO_POLICY:
            if row["target_decision_id"] is None:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return UndoPolicy(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                target_decision_id=str(row["target_decision_id"]),
                version=version,
            )
        if decision_id is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)

        if command_type is PolicyCommandType.SET_SOURCE_DISPLAY_NAME:
            if len(anchors) != 1 or not isinstance(
                anchors[0].selector, EffectiveSourceSelector
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return SetSourceDisplayName(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                selector=anchors[0].selector,
                display_name=str(row["display_name"]),
            )
        if command_type is PolicyCommandType.SET_SOURCE_RUBRO:
            if len(anchors) != 1 or not isinstance(
                anchors[0].selector, EffectiveSourceSelector
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return SetSourceRubro(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                selector=anchors[0].selector,
                rubro=Rubro(str(row["rubro"])),
            )
        if command_type is PolicyCommandType.SET_FLOW_DISPLAY_NAME:
            if len(anchors) != 1 or not isinstance(
                anchors[0].selector, EffectiveFlowSelector
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return SetFlowDisplayName(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                selector=anchors[0].selector,
                display_name=str(row["display_name"]),
            )
        if command_type is PolicyCommandType.SET_FLOW_INTENTION:
            if len(anchors) != 1 or not isinstance(
                anchors[0].selector, EffectiveFlowSelector
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return SetFlowIntention(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                selector=anchors[0].selector,
                intention=Intencion(str(row["intention"])),
            )
        if command_type is PolicyCommandType.MERGE_SOURCES:
            if any(
                anchor.role is not PolicyAnchorRole.MERGE_PARTICIPANT
                or not isinstance(anchor.selector, EffectiveSourceSelector)
                for anchor in anchors
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return MergeSources(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                source_selectors=tuple(
                    anchor.selector
                    for anchor in anchors
                    if isinstance(anchor.selector, EffectiveSourceSelector)
                ),
            )
        if command_type is PolicyCommandType.PARTITION_SOURCE:
            if not anchors or not isinstance(
                anchors[0].selector, EffectiveSourceSelector
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            members = anchors[1:]
            group_orders = tuple(
                anchor.group_order for anchor in members if anchor.group_order is not None
            )
            if not group_orders or set(group_orders) != set(
                range(max(group_orders) + 1)
            ):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            groups = tuple(
                PartitionGroup(
                    anchors=tuple(
                        anchor.selector
                        for anchor in members
                        if anchor.group_order == group_order
                        and isinstance(anchor.selector, PartitionAnchor)
                    )
                )
                for group_order in range(max(group_orders) + 1)
            )
            return PartitionSource(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                source_selector=anchors[0].selector,
                groups=groups,
            )
        if command_type is PolicyCommandType.PROTECT_TARGET:
            if len(anchors) != 1 or isinstance(anchors[0].selector, PartitionAnchor):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            return ProtectTarget(
                command_id=command_id,
                account_key=account_key,
                occurred_at=occurred_at,
                expected_revision=expected_revision,
                decision_id=decision_id,
                supersedes_decision_ids=supersedes,
                version=version,
                selector=anchors[0].selector,
                protection=Proteccion(str(row["protection"])),
            )
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)

    @staticmethod
    def _event_from_row(
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> PolicyEvent:
        try:
            if int(row["policy_version"]) != 1:
                raise PolicyError(PolicyErrorCode.UNKNOWN_POLICY_VERSION)
            account_key = str(row["account_key"])
            account_revision = int(row["account_revision"])
            relations = Repository._relations_for_event(
                connection, account_key, account_revision
            )
            anchors = Repository._anchors_for_event(
                connection, account_key, account_revision, relations
            )
            return PolicyEvent(
                command=Repository._command_from_event_row(row, anchors, relations),
                account_revision=account_revision,
                anchors=anchors,
                relations=relations,
                version=int(row["policy_version"]),
            )
        except PolicyError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None

    @staticmethod
    def _policy_history_conn(
        connection: sqlite3.Connection,
        account_key: str,
    ) -> tuple[PolicyEvent, ...]:
        rows = connection.execute(
            "SELECT * FROM local_policy_events WHERE account_key = ? "
            "ORDER BY account_revision",
            (account_key,),
        ).fetchall()
        return tuple(Repository._event_from_row(connection, row) for row in rows)

    @staticmethod
    def _policy_event_for_command_conn(
        connection: sqlite3.Connection,
        command: LocalPolicyCommand,
    ) -> PolicyEvent | None:
        row = connection.execute(
            "SELECT * FROM local_policy_events "
            "WHERE account_key = ? AND command_id = ?",
            (command.account_key, command.command_id),
        ).fetchone()
        if row is None:
            return None
        event = Repository._event_from_row(connection, row)
        if event.command != command:
            raise PolicyError(PolicyErrorCode.COMMAND_ID_CONFLICT)
        return event

    @staticmethod
    def _active_policies_from_events(
        events: tuple[PolicyEvent, ...],
    ) -> tuple[ActivePolicy, ...]:
        active: dict[str, ActivePolicy] = {}
        decisions: dict[str, ActivePolicy] = {}
        explicitly_undone: set[str] = set()
        expected_revision = 1
        for event in events:
            if event.account_revision != expected_revision:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            expected_revision += 1
            command = event.command
            if is_policy_decision_command(command):
                if command.decision_id in decisions:
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                supersedes = tuple(
                    relation.target_decision_id
                    for relation in event.relations
                    if relation.kind is PolicyRelationKind.SUPERSEDES
                )
                if any(decision_id not in active for decision_id in supersedes):
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                for decision_id in supersedes:
                    del active[decision_id]
                policy = ActivePolicy(
                    command=command,
                    account_revision=event.account_revision,
                    anchors=event.anchors,
                    relations=event.relations,
                    version=event.version,
                )
                active[command.decision_id] = policy
                decisions[command.decision_id] = policy
                continue

            if not isinstance(command, UndoPolicy):
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            target = active.pop(command.target_decision_id, None)
            if target is None:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            explicitly_undone.add(command.target_decision_id)
            for decision_id in target.command.supersedes_decision_ids:
                previous = decisions.get(decision_id)
                if previous is None:
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                if decision_id in explicitly_undone:
                    continue
                if any(
                    decision_id in policy.command.supersedes_decision_ids
                    for policy in active.values()
                ):
                    continue
                active[decision_id] = previous
        return tuple(active[decision_id] for decision_id in sorted(active))

    @staticmethod
    def _active_policies_conn(
        connection: sqlite3.Connection,
        account_key: str,
    ) -> tuple[ActivePolicy, ...]:
        return Repository._active_policies_from_events(
            Repository._policy_history_conn(connection, account_key)
        )

    @staticmethod
    def _structural_source_descriptors(
        command: LocalPolicyCommand,
    ) -> tuple[SourceIdentityDescriptor, ...]:
        if isinstance(command, MergeSources):
            return tuple(
                source
                for selector in command.source_selectors
                for source in selector.automatic_sources
            )
        if isinstance(command, PartitionSource):
            return command.source_selector.automatic_sources
        return ()

    @staticmethod
    def _correction_field(command: LocalPolicyCommand) -> str | None:
        if isinstance(command, SetSourceDisplayName):
            return "source_display_name"
        if isinstance(command, SetSourceRubro):
            return "source_rubro"
        if isinstance(command, SetFlowDisplayName):
            return "flow_display_name"
        if isinstance(command, SetFlowIntention):
            return "flow_intention"
        return None

    @staticmethod
    def _source_descriptors_share_anchor(
        left: SourceIdentityDescriptor,
        right: SourceIdentityDescriptor,
    ) -> bool:
        if left.kind is not right.kind:
            return False
        if left.sender_addresses or right.sender_addresses:
            return bool(set(left.sender_addresses).intersection(right.sender_addresses))
        return left.isolated_message_id == right.isolated_message_id

    @staticmethod
    def _source_selectors_share_anchor(
        left: EffectiveSourceSelector,
        right: EffectiveSourceSelector,
    ) -> bool:
        return any(
            Repository._source_descriptors_share_anchor(left_source, right_source)
            for left_source in left.automatic_sources
            for right_source in right.automatic_sources
        )

    @staticmethod
    def _target_selectors_share_anchor(
        left: object,
        right: object,
    ) -> bool:
        if left == right:
            return True
        if isinstance(left, EffectiveSourceSelector) and isinstance(
            right, EffectiveSourceSelector
        ):
            return Repository._source_selectors_share_anchor(left, right)
        if isinstance(left, EffectiveFlowSelector) and isinstance(
            right, EffectiveFlowSelector
        ):
            left_flow = left.automatic_flow
            right_flow = right.automatic_flow
            return (
                left_flow.kind is right_flow.kind
                and left_flow.list_id == right_flow.list_id
                and left_flow.sender_address == right_flow.sender_address
                and left_flow.automatic_intention is right_flow.automatic_intention
                and left_flow.isolated_message_id == right_flow.isolated_message_id
                and Repository._source_descriptors_share_anchor(
                    left_flow.source, right_flow.source
                )
            )
        return False

    @staticmethod
    def _supersedes_compatible(
        command: LocalPolicyCommand,
        active: ActivePolicy,
    ) -> bool:
        current = active.command
        command_sources = Repository._structural_source_descriptors(command)
        current_sources = Repository._structural_source_descriptors(current)
        if command_sources:
            return any(
                Repository._source_descriptors_share_anchor(left, right)
                for left in command_sources
                for right in current_sources
            )
        if isinstance(command, ProtectTarget):
            return isinstance(current, ProtectTarget) and current.selector == command.selector
        return (
            Repository._correction_field(command)
            == Repository._correction_field(current)
            and Repository._correction_field(command) is not None
            and Repository._target_selectors_share_anchor(
                getattr(command, "selector", None),
                getattr(current, "selector", None),
            )
        )

    @staticmethod
    def _structural_policy_creates_selector(
        policy: ActivePolicy,
        selector: EffectiveSourceSelector,
    ) -> bool:
        command = policy.command
        if isinstance(command, MergeSources):
            created = EffectiveSourceSelector(
                account_key=command.account_key,
                kind=EffectiveSourceKind.MERGED,
                automatic_sources=tuple(
                    source
                    for participant in command.source_selectors
                    for source in participant.automatic_sources
                ),
            )
            return selector == created
        if isinstance(command, PartitionSource):
            return any(
                selector
                == EffectiveSourceSelector(
                    account_key=command.account_key,
                    kind=EffectiveSourceKind.PARTITION_GROUP,
                    automatic_sources=command.source_selector.automatic_sources,
                    partition_anchors=group.anchors,
                )
                for group in command.groups
            )
        return False

    @staticmethod
    def _validate_anchor_structural_context(
        anchor: PreparedPolicyAnchor,
        active_policies: tuple[ActivePolicy, ...],
    ) -> None:
        selector = anchor.selector
        effective_source: EffectiveSourceSelector | None = None
        if isinstance(selector, EffectiveSourceSelector):
            effective_source = selector
        elif isinstance(selector, EffectiveFlowSelector):
            effective_source = selector.effective_source
        if effective_source is None:
            if anchor.structural_decision_ids:
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
            return
        if effective_source.kind is EffectiveSourceKind.AUTOMATIC:
            expected: tuple[str, ...] = ()
            if any(
                any(
                    Repository._source_descriptors_share_anchor(left, right)
                    for left in effective_source.automatic_sources
                    for right in Repository._structural_source_descriptors(
                        policy.command
                    )
                )
                for policy in active_policies
                if isinstance(policy.command, (MergeSources, PartitionSource))
            ):
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
        else:
            expected = tuple(
                sorted(
                    policy.decision_id
                    for policy in active_policies
                    if Repository._structural_policy_creates_selector(
                        policy, effective_source
                    )
                )
            )
            if len(expected) != 1:
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
        if anchor.structural_decision_ids != expected:
            raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)

    @staticmethod
    def _validate_prepared_against_active(
        prepared: PreparedPolicyDecision,
        active_policies: tuple[ActivePolicy, ...],
    ) -> None:
        command = prepared.command
        active_by_id = {policy.decision_id: policy for policy in active_policies}
        superseded_ids = set(command.supersedes_decision_ids)
        for decision_id in command.supersedes_decision_ids:
            active = active_by_id.get(decision_id)
            if active is None or not Repository._supersedes_compatible(command, active):
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)

        remaining = tuple(
            policy
            for policy in active_policies
            if policy.decision_id not in superseded_ids
        )
        for anchor in prepared.anchors:
            Repository._validate_anchor_structural_context(anchor, remaining)

        for relation in prepared.relations:
            if relation.target_decision_id == command.decision_id:
                raise PolicyError(PolicyErrorCode.INVALID_TRANSITION)
            if relation.kind is not PolicyRelationKind.STRUCTURAL_CONTEXT:
                continue
            active = active_by_id.get(relation.target_decision_id)
            if active is None or not isinstance(
                active.command, (MergeSources, PartitionSource)
            ):
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
            if relation.target_decision_id in superseded_ids:
                raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)

        structural_sources = Repository._structural_source_descriptors(command)
        if structural_sources and any(
            any(
                Repository._source_descriptors_share_anchor(left, right)
                for left in structural_sources
                for right in Repository._structural_source_descriptors(
                    policy.command
                )
            )
            for policy in remaining
            if isinstance(policy.command, (MergeSources, PartitionSource))
        ):
            raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)

        field_name = Repository._correction_field(command)
        if field_name is None:
            return
        prepared_effective_ids = {
            anchor.observed_effective_id
            for anchor in prepared.anchors
            if anchor.observed_effective_id is not None
        }
        if any(
            Repository._correction_field(policy.command) == field_name
            and (
                getattr(policy.command, "selector", None)
                == getattr(command, "selector", None)
                or Repository._target_selectors_share_anchor(
                    getattr(policy.command, "selector", None),
                    getattr(command, "selector", None),
                )
                or prepared_effective_ids.intersection(
                    anchor.observed_effective_id
                    for anchor in policy.anchors
                    if anchor.observed_effective_id is not None
                )
            )
            for policy in remaining
        ):
            raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)

    @staticmethod
    def _account_exists_conn(
        connection: sqlite3.Connection,
        account_key: str,
    ) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM indexed_accounts WHERE account_key = ?",
                (account_key,),
            ).fetchone()
            is not None
        )

    @staticmethod
    def _current_policy_revision_conn(
        connection: sqlite3.Connection,
        account_key: str,
    ) -> int:
        row = connection.execute(
            "SELECT MAX(account_revision) FROM local_policy_events "
            "WHERE account_key = ?",
            (account_key,),
        ).fetchone()
        return int(row[0] or 0)

    @staticmethod
    def _map_input_snapshot_conn(
        connection: sqlite3.Connection,
        account_key: str,
    ) -> MapInputSnapshot:
        indexed_account_keys = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT account_key FROM indexed_accounts ORDER BY account_key"
            ).fetchall()
        )
        account_exists = account_key in indexed_account_keys
        fixture_row = connection.execute(
            "SELECT value FROM app_meta WHERE key = 'map_fixture_version'"
        ).fetchone()
        fixture_version = str(fixture_row[0]) if fixture_row is not None else None

        message_rows = connection.execute(
            "SELECT * FROM indexed_messages WHERE account_key = ? "
            "ORDER BY received_at DESC, provider_message_id ASC",
            (account_key,),
        ).fetchall()
        records = tuple(Repository._indexed_message_from_row(row) for row in message_rows)
        checkpoint_row = connection.execute(
            "SELECT * FROM sync_checkpoints WHERE account_key = ?",
            (account_key,),
        ).fetchone()
        checkpoint = (
            Repository._checkpoint_from_row(checkpoint_row)
            if checkpoint_row is not None
            else None
        )
        policy_history = Repository._policy_history_conn(connection, account_key)
        active_policies = Repository._active_policies_from_events(policy_history)
        policy_revision = (
            policy_history[-1].account_revision if policy_history else 0
        )

        raw_policy_rows: dict[str, list[dict[str, Any]]] = {}
        policy_queries = (
            (
                "local_policy_events",
                "SELECT * FROM local_policy_events WHERE account_key = ? "
                "ORDER BY account_revision",
            ),
            (
                "local_policy_anchors",
                "SELECT * FROM local_policy_anchors WHERE account_key = ? "
                "ORDER BY account_revision, anchor_order",
            ),
            (
                "local_policy_anchor_sources",
                "SELECT * FROM local_policy_anchor_sources WHERE account_key = ? "
                "ORDER BY account_revision, anchor_order, source_order, member_order",
            ),
            (
                "local_policy_partition_members",
                "SELECT * FROM local_policy_partition_members WHERE account_key = ? "
                "ORDER BY account_revision, anchor_order, member_order",
            ),
            (
                "local_policy_observed_ids",
                "SELECT * FROM local_policy_observed_ids WHERE account_key = ? "
                "ORDER BY account_revision, anchor_order, observed_kind, observed_order",
            ),
            (
                "local_policy_relations",
                "SELECT * FROM local_policy_relations WHERE account_key = ? "
                "ORDER BY account_revision, relation_order",
            ),
        )
        for table_name, query in policy_queries:
            raw_policy_rows[table_name] = [
                dict(row) for row in connection.execute(query, (account_key,)).fetchall()
            ]

        revision_payload = {
            "account_key": account_key,
            "account_exists": account_exists,
            "indexed_account_keys": indexed_account_keys,
            "fixture_version": fixture_version,
            "indexed_messages": [dict(row) for row in message_rows],
            "sync_checkpoint": (
                dict(checkpoint_row) if checkpoint_row is not None else None
            ),
            "policy_ledger": raw_policy_rows,
        }
        return MapInputSnapshot(
            account_key=account_key,
            account_exists=account_exists,
            indexed_account_keys=indexed_account_keys,
            fixture_version=fixture_version,
            records=records,
            checkpoint=checkpoint,
            policy_history=policy_history,
            active_policies=active_policies,
            policy_revision=policy_revision,
            input_revision=_sha256_revision(revision_payload),
        )

    def map_input_snapshot(self, account_key: str) -> MapInputSnapshot:
        try:
            validated_account_key = validate_account_key(account_key)
        except (TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                return self._map_input_snapshot_conn(connection, validated_account_key)
        except MapRepositoryError:
            raise
        except (PolicyError, sqlite3.DatabaseError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE) from None

    def install_synthetic_map_fixture(
        self,
        account_key: str,
        fixture_version: str,
        records: tuple[IndexedMessageRecord, ...],
        checkpoint: SyncCheckpoint,
        policy_events: tuple[PolicyEvent, ...],
    ) -> MapInputSnapshot:
        try:
            validated_account_key = validate_account_key(account_key)
            if (
                not isinstance(fixture_version, str)
                or not fixture_version
                or fixture_version != fixture_version.strip()
            ):
                raise ValueError("fixture_version must be normalized")
            if not isinstance(records, tuple) or any(
                not isinstance(record, IndexedMessageRecord) for record in records
            ):
                raise TypeError("records must contain IndexedMessageRecord values")
            if any(record.account_key != validated_account_key for record in records):
                raise ValueError("records reference another account")
            message_ids = tuple(record.provider_message_id for record in records)
            if len(message_ids) != len(set(message_ids)):
                raise ValueError("records contain duplicate provider_message_id values")
            validated_records = tuple(replace(record) for record in records)
            if not isinstance(checkpoint, SyncCheckpoint):
                raise TypeError("checkpoint must be a SyncCheckpoint")
            validated_checkpoint = replace(checkpoint)
            if validated_checkpoint.account_key != validated_account_key:
                raise ValueError("checkpoint references another account")
            if not isinstance(policy_events, tuple) or any(
                not isinstance(event, PolicyEvent) for event in policy_events
            ):
                raise TypeError("policy_events must contain PolicyEvent values")

            validated_events: list[PolicyEvent] = []
            for expected_revision, event in enumerate(policy_events, start=1):
                validated_event = PolicyEvent(
                    command=event.command,
                    account_revision=event.account_revision,
                    anchors=event.anchors,
                    relations=event.relations,
                    version=event.version,
                )
                if validated_event.command.account_key != validated_account_key:
                    raise ValueError("policy event references another account")
                if validated_event.account_revision != expected_revision:
                    raise ValueError("policy events must form a contiguous sequence")
                if is_policy_decision_command(validated_event.command):
                    prepared = PreparedPolicyDecision(
                        command=validated_event.command,
                        anchors=validated_event.anchors,
                        relations=validated_event.relations,
                        version=validated_event.version,
                    )
                    self._validate_prepared_against_active(
                        prepared,
                        self._active_policies_from_events(tuple(validated_events)),
                    )
                validated_events.append(validated_event)
                self._active_policies_from_events(tuple(validated_events))
            validated_policy_events = tuple(validated_events)
            assert_synthetic_fixture_payload(
                account_key=validated_account_key,
                fixture_version=fixture_version,
                records=validated_records,
                checkpoint=validated_checkpoint,
                policy_events=validated_policy_events,
            )
        except SyntheticMapGateError:
            raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE) from None
        except (PolicyError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                assert_synthetic_fixture_payload(
                    account_key=validated_account_key,
                    fixture_version=fixture_version,
                    records=validated_records,
                    checkpoint=validated_checkpoint,
                    policy_events=validated_policy_events,
                )
                if (
                    connection.execute("SELECT 1 FROM indexed_accounts LIMIT 1").fetchone()
                    is not None
                    or connection.execute(
                        "SELECT 1 FROM app_meta WHERE key = 'map_fixture_version'"
                    ).fetchone()
                    is not None
                ):
                    raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE)

                connection.execute(
                    "INSERT INTO indexed_accounts(account_key) VALUES (?)",
                    (validated_account_key,),
                )
                self._upsert_index_records(connection, validated_records)
                self._upsert_checkpoint(connection, validated_checkpoint)
                for event in validated_policy_events:
                    self._insert_policy_event(
                        connection, event.command, event.account_revision
                    )
                    for anchor in event.anchors:
                        self._insert_policy_anchor(
                            connection,
                            validated_account_key,
                            event.account_revision,
                            anchor,
                        )
                    for relation in event.relations:
                        self._insert_policy_relation(
                            connection,
                            validated_account_key,
                            event.account_revision,
                            relation,
                        )
                connection.execute(
                    "INSERT INTO app_meta(key, value) "
                    "VALUES ('map_fixture_version', ?)",
                    (fixture_version,),
                )
                snapshot = self._map_input_snapshot_conn(
                    connection, validated_account_key
                )
                self._assert_map_snapshot_gate(
                    snapshot, SYNTHETIC_MAP_FIXTURE_VERSION
                )
                return snapshot
        except SyntheticMapGateError:
            raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE) from None
        except MapRepositoryError:
            raise
        except (PolicyError, sqlite3.DatabaseError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None

    @staticmethod
    def _validate_map_receipt_metadata(
        *,
        request_fingerprint: str,
        contract_version: int,
    ) -> None:
        if (
            not isinstance(request_fingerprint, str)
            or _SHA256_FINGERPRINT.fullmatch(request_fingerprint) is None
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)
        if (
            isinstance(contract_version, bool)
            or not isinstance(contract_version, int)
            or contract_version != MAP_POLICY_REQUEST_CONTRACT_VERSION
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)

    @staticmethod
    def _validate_map_write_metadata(
        *,
        expected_input_revision: str,
        request_fingerprint: str,
        required_fixture_version: str,
        contract_version: int,
    ) -> None:
        Repository._validate_map_receipt_metadata(
            request_fingerprint=request_fingerprint,
            contract_version=contract_version,
        )
        if (
            not isinstance(expected_input_revision, str)
            or _MAP_INPUT_REVISION.fullmatch(expected_input_revision) is None
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)
        if (
            not isinstance(required_fixture_version, str)
            or not required_fixture_version
            or required_fixture_version != required_fixture_version.strip()
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)

    @staticmethod
    def _map_policy_replay_conn(
        connection: sqlite3.Connection,
        *,
        account_key: str,
        command_id: str,
        request_fingerprint: str,
        contract_version: int,
    ) -> MapPolicyWriteResult | None:
        receipt = connection.execute(
            "SELECT contract_version, request_fingerprint "
            "FROM map_policy_requests WHERE account_key = ? AND command_id = ?",
            (account_key, command_id),
        ).fetchone()
        event_row = connection.execute(
            "SELECT * FROM local_policy_events "
            "WHERE account_key = ? AND command_id = ?",
            (account_key, command_id),
        ).fetchone()
        if receipt is None:
            if event_row is not None:
                raise MapRepositoryError(MapRepositoryErrorCode.COMMAND_ID_CONFLICT)
            return None
        if event_row is None:
            raise MapRepositoryError(MapRepositoryErrorCode.RECEIPT_CORRUPT)

        stored_version = receipt["contract_version"]
        stored_fingerprint = receipt["request_fingerprint"]
        if (
            isinstance(stored_version, bool)
            or not isinstance(stored_version, int)
            or stored_version != MAP_POLICY_REQUEST_CONTRACT_VERSION
            or not isinstance(stored_fingerprint, str)
            or _SHA256_FINGERPRINT.fullmatch(stored_fingerprint) is None
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.RECEIPT_CORRUPT)
        if (
            stored_version != contract_version
            or stored_fingerprint != request_fingerprint
        ):
            raise MapRepositoryError(MapRepositoryErrorCode.COMMAND_ID_CONFLICT)
        try:
            event = Repository._event_from_row(connection, event_row)
        except PolicyError:
            raise MapRepositoryError(MapRepositoryErrorCode.RECEIPT_CORRUPT) from None
        return MapPolicyWriteResult(event=event, replayed=True)

    def map_policy_replay(
        self,
        account_key: str,
        command_id: str,
        *,
        request_fingerprint: str,
        contract_version: int = MAP_POLICY_REQUEST_CONTRACT_VERSION,
    ) -> MapPolicyWriteResult | None:
        try:
            validated_account_key = validate_account_key(account_key)
            validated_command_id = validate_opaque_identifier(command_id, "command_id")
            self._validate_map_receipt_metadata(
                request_fingerprint=request_fingerprint,
                contract_version=contract_version,
            )
        except MapRepositoryError:
            raise
        except (TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                return self._map_policy_replay_conn(
                    connection,
                    account_key=validated_account_key,
                    command_id=validated_command_id,
                    request_fingerprint=request_fingerprint,
                    contract_version=contract_version,
                )
        except MapRepositoryError:
            raise
        except (PolicyError, sqlite3.DatabaseError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.RECEIPT_CORRUPT) from None

    @staticmethod
    def _assert_map_snapshot_gate(
        snapshot: MapInputSnapshot,
        required_fixture_version: str,
    ) -> None:
        if required_fixture_version != SYNTHETIC_MAP_FIXTURE_VERSION:
            raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE)
        try:
            assert_synthetic_map_snapshot(
                account_key=snapshot.account_key,
                account_exists=snapshot.account_exists,
                indexed_account_keys=snapshot.indexed_account_keys,
                fixture_version=snapshot.fixture_version,
                records=snapshot.records,
                checkpoint=snapshot.checkpoint,
                policy_history=snapshot.policy_history,
                active_policies=snapshot.active_policies,
            )
        except SyntheticMapGateError:
            raise MapRepositoryError(MapRepositoryErrorCode.MAP_UNAVAILABLE) from None

    @staticmethod
    def _insert_map_policy_receipt(
        connection: sqlite3.Connection,
        *,
        account_key: str,
        command_id: str,
        request_fingerprint: str,
        contract_version: int,
    ) -> None:
        connection.execute(
            "INSERT INTO map_policy_requests("
            "account_key, command_id, contract_version, request_fingerprint"
            ") VALUES (?, ?, ?, ?)",
            (account_key, command_id, contract_version, request_fingerprint),
        )

    @staticmethod
    def _record_policy_conn(
        connection: sqlite3.Connection,
        prepared: PreparedPolicyDecision,
    ) -> PolicyEvent:
        command = prepared.command
        if not Repository._account_exists_conn(connection, command.account_key):
            raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
        current_revision = Repository._current_policy_revision_conn(
            connection, command.account_key
        )
        if command.expected_revision != current_revision:
            raise PolicyError(PolicyErrorCode.REVISION_CONFLICT)
        if (
            connection.execute(
                "SELECT 1 FROM local_policy_events "
                "WHERE account_key = ? AND decision_id = ?",
                (command.account_key, command.decision_id),
            ).fetchone()
            is not None
        ):
            raise PolicyError(PolicyErrorCode.INVALID_TRANSITION)

        active = Repository._active_policies_conn(connection, command.account_key)
        Repository._validate_prepared_against_active(prepared, active)
        account_revision = current_revision + 1
        Repository._insert_policy_event(connection, command, account_revision)
        for anchor in prepared.anchors:
            Repository._insert_policy_anchor(
                connection, command.account_key, account_revision, anchor
            )
        for relation in prepared.relations:
            Repository._insert_policy_relation(
                connection, command.account_key, account_revision, relation
            )
        row = connection.execute(
            "SELECT * FROM local_policy_events "
            "WHERE account_key = ? AND account_revision = ?",
            (command.account_key, account_revision),
        ).fetchone()
        if row is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        return Repository._event_from_row(connection, row)

    @staticmethod
    def _undo_policy_conn(
        connection: sqlite3.Connection,
        command: UndoPolicy,
    ) -> PolicyEvent:
        current_revision = Repository._current_policy_revision_conn(
            connection, command.account_key
        )
        if command.expected_revision != current_revision:
            raise PolicyError(PolicyErrorCode.REVISION_CONFLICT)
        if not Repository._account_exists_conn(connection, command.account_key):
            raise PolicyError(PolicyErrorCode.INVALID_TRANSITION)
        active = {
            policy.decision_id: policy
            for policy in Repository._active_policies_conn(
                connection, command.account_key
            )
        }
        if command.target_decision_id not in active:
            raise PolicyError(PolicyErrorCode.INVALID_TRANSITION)

        account_revision = current_revision + 1
        relation = PreparedPolicyRelation(
            relation_order=0,
            kind=PolicyRelationKind.UNDOES,
            target_decision_id=command.target_decision_id,
        )
        Repository._insert_policy_event(connection, command, account_revision)
        Repository._insert_policy_relation(
            connection, command.account_key, account_revision, relation
        )
        row = connection.execute(
            "SELECT * FROM local_policy_events "
            "WHERE account_key = ? AND account_revision = ?",
            (command.account_key, account_revision),
        ).fetchone()
        if row is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        return Repository._event_from_row(connection, row)

    def policy_event_for_command(
        self,
        command: LocalPolicyCommand,
    ) -> PolicyEvent | None:
        if not is_policy_decision_command(command) and not isinstance(
            command, UndoPolicy
        ):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._policy_event_for_command_conn(connection, command)

    def record_policy(self, prepared: PreparedPolicyDecision) -> PolicyEvent:
        if not isinstance(prepared, PreparedPolicyDecision):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        command = prepared.command
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = self._policy_event_for_command_conn(connection, command)
                if replay is not None:
                    return replay

                validated = PreparedPolicyDecision(
                    command=command,
                    anchors=prepared.anchors,
                    relations=prepared.relations,
                    version=prepared.version,
                )
                return self._record_policy_conn(connection, validated)
        except sqlite3.IntegrityError:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
        except PolicyError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None

    def undo_policy(self, command: UndoPolicy) -> PolicyEvent:
        if not isinstance(command, UndoPolicy):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = self._policy_event_for_command_conn(connection, command)
                if replay is not None:
                    return replay
                return self._undo_policy_conn(connection, command)
        except sqlite3.IntegrityError:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
        except PolicyError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None

    def record_map_policy(
        self,
        prepared: PreparedPolicyDecision,
        *,
        expected_input_revision: str,
        request_fingerprint: str,
        required_fixture_version: str,
        contract_version: int = MAP_POLICY_REQUEST_CONTRACT_VERSION,
    ) -> MapPolicyWriteResult:
        if not isinstance(prepared, PreparedPolicyDecision):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)
        self._validate_map_write_metadata(
            expected_input_revision=expected_input_revision,
            request_fingerprint=request_fingerprint,
            required_fixture_version=required_fixture_version,
            contract_version=contract_version,
        )
        try:
            validated = PreparedPolicyDecision(
                command=prepared.command,
                anchors=prepared.anchors,
                relations=prepared.relations,
                version=prepared.version,
            )
            assert_synthetic_policy_candidate(validated)
        except SyntheticMapGateError:
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        except (TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        command = validated.command
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = self._map_policy_replay_conn(
                    connection,
                    account_key=command.account_key,
                    command_id=command.command_id,
                    request_fingerprint=request_fingerprint,
                    contract_version=contract_version,
                )
                if replay is not None:
                    return replay

                snapshot = self._map_input_snapshot_conn(
                    connection, command.account_key
                )
                self._assert_map_snapshot_gate(snapshot, required_fixture_version)
                if snapshot.input_revision != expected_input_revision:
                    raise MapRepositoryError(
                        MapRepositoryErrorCode.MAP_REVISION_CONFLICT
                    )
                if command.expected_revision != snapshot.policy_revision:
                    raise PolicyError(PolicyErrorCode.REVISION_CONFLICT)

                event = self._record_policy_conn(connection, validated)
                self._assert_map_snapshot_gate(
                    self._map_input_snapshot_conn(connection, command.account_key),
                    required_fixture_version,
                )
                self._insert_map_policy_receipt(
                    connection,
                    account_key=command.account_key,
                    command_id=command.command_id,
                    request_fingerprint=request_fingerprint,
                    contract_version=contract_version,
                )
                return MapPolicyWriteResult(event=event, replayed=False)
        except (MapRepositoryError, PolicyError):
            raise
        except sqlite3.IntegrityError:
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        except (AttributeError, KeyError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None

    def undo_map_policy(
        self,
        command: UndoPolicy,
        *,
        expected_input_revision: str,
        request_fingerprint: str,
        required_fixture_version: str,
        contract_version: int = MAP_POLICY_REQUEST_CONTRACT_VERSION,
    ) -> MapPolicyWriteResult:
        if not isinstance(command, UndoPolicy):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT)
        self._validate_map_write_metadata(
            expected_input_revision=expected_input_revision,
            request_fingerprint=request_fingerprint,
            required_fixture_version=required_fixture_version,
            contract_version=contract_version,
        )
        try:
            validated = UndoPolicy(
                command_id=command.command_id,
                account_key=command.account_key,
                occurred_at=command.occurred_at,
                expected_revision=command.expected_revision,
                target_decision_id=command.target_decision_id,
                version=command.version,
            )
            assert_synthetic_policy_candidate(validated)
        except SyntheticMapGateError:
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        except (TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = self._map_policy_replay_conn(
                    connection,
                    account_key=validated.account_key,
                    command_id=validated.command_id,
                    request_fingerprint=request_fingerprint,
                    contract_version=contract_version,
                )
                if replay is not None:
                    return replay

                snapshot = self._map_input_snapshot_conn(
                    connection, validated.account_key
                )
                self._assert_map_snapshot_gate(snapshot, required_fixture_version)
                if snapshot.input_revision != expected_input_revision:
                    raise MapRepositoryError(
                        MapRepositoryErrorCode.MAP_REVISION_CONFLICT
                    )
                if validated.expected_revision != snapshot.policy_revision:
                    raise PolicyError(PolicyErrorCode.REVISION_CONFLICT)

                event = self._undo_policy_conn(connection, validated)
                self._assert_map_snapshot_gate(
                    self._map_input_snapshot_conn(connection, validated.account_key),
                    required_fixture_version,
                )
                self._insert_map_policy_receipt(
                    connection,
                    account_key=validated.account_key,
                    command_id=validated.command_id,
                    request_fingerprint=request_fingerprint,
                    contract_version=contract_version,
                )
                return MapPolicyWriteResult(event=event, replayed=False)
        except (MapRepositoryError, PolicyError):
            raise
        except sqlite3.IntegrityError:
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None
        except (AttributeError, KeyError, TypeError, ValueError):
            raise MapRepositoryError(MapRepositoryErrorCode.INVALID_INPUT) from None

    def policy_history(self, account_key: str) -> tuple[PolicyEvent, ...]:
        try:
            validated_account_key = validate_account_key(account_key)
        except (TypeError, ValueError):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._policy_history_conn(connection, validated_account_key)

    def active_policies(self, account_key: str) -> tuple[ActivePolicy, ...]:
        try:
            validated_account_key = validate_account_key(account_key)
        except (TypeError, ValueError):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._active_policies_conn(connection, validated_account_key)

    def save_index_page(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        checkpoint: SyncCheckpoint,
    ) -> None:
        self.apply_index_page(account_key, records, (), checkpoint)

    def apply_index_page(
        self,
        account_key: str,
        records: Iterable[IndexedMessageRecord],
        deleted_message_ids: Iterable[str],
        checkpoint: SyncCheckpoint,
    ) -> None:
        validated_account_key = validate_account_key(account_key)
        if not isinstance(checkpoint, SyncCheckpoint):
            raise TypeError("checkpoint must be a SyncCheckpoint")
        validated_checkpoint = replace(checkpoint)
        if validated_checkpoint.account_key != validated_account_key:
            raise ValueError("checkpoint account_key does not match apply_index_page account_key")

        validated_records: list[IndexedMessageRecord] = []
        identities: set[str] = set()
        for record in records:
            if not isinstance(record, IndexedMessageRecord):
                raise TypeError("records must contain IndexedMessageRecord values")
            validated_record = replace(record)
            if validated_record.account_key != validated_account_key:
                raise ValueError("record account_key does not match apply_index_page account_key")
            if validated_record.provider_message_id in identities:
                raise ValueError("records contains a duplicate provider_message_id")
            identities.add(validated_record.provider_message_id)
            validated_records.append(validated_record)

        validated_deleted_ids = tuple(
            sorted(
                {
                    validate_opaque_identifier(message_id, "provider_message_id")
                    for message_id in deleted_message_ids
                }
            )
        )
        overlap = identities.intersection(validated_deleted_ids)
        if overlap:
            raise ValueError("a provider_message_id cannot be updated and deleted together")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_index_account(connection, validated_account_key)
            connection.executemany(
                "DELETE FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                [
                    (validated_account_key, message_id)
                    for message_id in validated_deleted_ids
                ],
            )
            self._upsert_index_records(connection, validated_records)
            self._upsert_checkpoint(connection, validated_checkpoint)

    def start_full_index(
        self, account_key: str, checkpoint: SyncCheckpoint
    ) -> None:
        validated_account_key = validate_account_key(account_key)
        if not isinstance(checkpoint, SyncCheckpoint):
            raise TypeError("checkpoint must be a SyncCheckpoint")
        validated_checkpoint = replace(checkpoint)
        if validated_checkpoint.account_key != validated_account_key:
            raise ValueError("checkpoint account_key does not match start_full_index account_key")
        if validated_checkpoint.mode is not SyncMode.FULL:
            raise ValueError("start_full_index requires a full checkpoint")
        if validated_checkpoint.state is not SyncState.RUNNING:
            raise ValueError("start_full_index requires a running checkpoint")
        if validated_checkpoint.processed_count != 0:
            raise ValueError("start_full_index requires processed_count zero")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_index_account(connection, validated_account_key)
            connection.execute(
                "DELETE FROM indexed_messages WHERE account_key = ?",
                (validated_account_key,),
            )
            self._upsert_checkpoint(connection, validated_checkpoint)

    @staticmethod
    def _ensure_index_account(
        connection: sqlite3.Connection, account_key: str
    ) -> None:
        connection.execute(
            "INSERT INTO indexed_accounts(account_key) VALUES (?) "
            "ON CONFLICT(account_key) DO NOTHING",
            (account_key,),
        )

    def _upsert_index_records(
        self,
        connection: sqlite3.Connection,
        records: Iterable[IndexedMessageRecord],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO indexed_messages(
                account_key, provider_message_id, provider_thread_id, received_at,
                sender_name, sender_address, subject, label_ids_json, category,
                size_estimate_bytes, authenticated_domain, list_id, list_unsubscribe,
                list_unsubscribe_post, dkim_result, dmarc_result, record_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_key, provider_message_id) DO UPDATE SET
                provider_thread_id = excluded.provider_thread_id,
                received_at = excluded.received_at,
                sender_name = excluded.sender_name,
                sender_address = excluded.sender_address,
                subject = excluded.subject,
                label_ids_json = excluded.label_ids_json,
                category = excluded.category,
                size_estimate_bytes = excluded.size_estimate_bytes,
                authenticated_domain = excluded.authenticated_domain,
                list_id = excluded.list_id,
                list_unsubscribe = excluded.list_unsubscribe,
                list_unsubscribe_post = excluded.list_unsubscribe_post,
                dkim_result = excluded.dkim_result,
                dmarc_result = excluded.dmarc_result,
                record_version = excluded.record_version
            """,
            [self._indexed_message_values(record) for record in records],
        )

    def _upsert_checkpoint(
        self, connection: sqlite3.Connection, checkpoint: SyncCheckpoint
    ) -> None:
        connection.execute(
            """
            INSERT INTO sync_checkpoints(
                account_key, scan_id, mode, state, page_token, history_id,
                processed_count, started_at, updated_at, error_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_key) DO UPDATE SET
                scan_id = excluded.scan_id,
                mode = excluded.mode,
                state = excluded.state,
                page_token = excluded.page_token,
                history_id = excluded.history_id,
                processed_count = excluded.processed_count,
                started_at = excluded.started_at,
                updated_at = excluded.updated_at,
                error_code = excluded.error_code
            """,
            self._checkpoint_values(checkpoint),
        )

    def indexed_messages(self, account_key: str) -> tuple[IndexedMessageRecord, ...]:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM indexed_messages WHERE account_key = ? "
                "ORDER BY received_at DESC, provider_message_id ASC",
                (validated_account_key,),
            ).fetchall()
        return tuple(self._indexed_message_from_row(row) for row in rows)

    def indexed_message(
        self, account_key: str, provider_message_id: str
    ) -> IndexedMessageRecord | None:
        validated_account_key = validate_account_key(account_key)
        validated_message_id = validate_opaque_identifier(
            provider_message_id, "provider_message_id"
        )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                (validated_account_key, validated_message_id),
            ).fetchone()
        return self._indexed_message_from_row(row) if row else None

    def sync_checkpoint(self, account_key: str) -> SyncCheckpoint | None:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sync_checkpoints WHERE account_key = ?",
                (validated_account_key,),
            ).fetchone()
        return self._checkpoint_from_row(row) if row else None

    def delete_indexed_messages(
        self, account_key: str, provider_message_ids: Iterable[str]
    ) -> int:
        validated_account_key = validate_account_key(account_key)
        validated_ids = tuple(
            sorted(
                {
                    validate_opaque_identifier(message_id, "provider_message_id")
                    for message_id in provider_message_ids
                }
            )
        )
        if not validated_ids:
            return 0
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.executemany(
                "DELETE FROM indexed_messages "
                "WHERE account_key = ? AND provider_message_id = ?",
                [(validated_account_key, message_id) for message_id in validated_ids],
            )
            return cursor.rowcount

    def delete_account_index(self, account_key: str) -> None:
        validated_account_key = validate_account_key(account_key)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM indexed_accounts WHERE account_key = ?",
                (validated_account_key,),
            )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
