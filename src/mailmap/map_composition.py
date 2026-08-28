from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

from mailmap.classification_domain import classify_indexed_records
from mailmap.classification_model import (
    CLASSIFICATION_MODEL_VERSION,
    ClassificationError,
    ClassificationEvidence,
    ClassificationResult,
)
from mailmap.index_model import (
    INDEX_RECORD_VERSION,
    IndexedMessageRecord,
    SyncCheckpoint,
    SyncState,
)
from mailmap.map_model import (
    MAP_CONTRACT_VERSION,
    MAP_DATA_MODE,
    MapClassificationEvidence,
    MapCompositionError,
    MapCompositionErrorCode,
    MapDecision,
    MapDecisionHistory,
    MapEvidence,
    MapFlow,
    MapMergeSourcesDecision,
    MapMessageSample,
    MapMonthlyVolume,
    MapObservedTarget,
    MapPartitionGroupSummary,
    MapPartitionSourceDecision,
    MapPolicyEvidence,
    MapPolicyReview,
    MapPolicyReviewBinding,
    MapProjection,
    MapProtection,
    MapProtectTargetDecision,
    MapSetFlowDisplayNameDecision,
    MapSetFlowIntentionDecision,
    MapSetSourceDisplayNameDecision,
    MapSetSourceRubroDecision,
    MapSource,
    MapSourceDetail,
    MapSummary,
    MapSync,
    MapUndoPolicyDecision,
)
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SyntheticMapGateError,
    assert_synthetic_map_snapshot,
)
from mailmap.policy_domain import apply_local_policies, prepare_policy_decision
from mailmap.policy_model import (
    POLICY_MODEL_VERSION,
    POLICY_RESULT_VERSION,
    ActivePolicy,
    EffectiveEvidence,
    EffectiveFlow,
    EffectiveFlowSelector,
    EffectiveMessage,
    EffectiveSource,
    EffectiveSourceKind,
    EffectiveSourceSelector,
    LabelSelector,
    MergeSources,
    MessageSelector,
    PartitionAnchor,
    PartitionAnchorKind,
    PartitionSource,
    PolicyAnchorRole,
    PolicyApplicationResult,
    PolicyBindingStatus,
    PolicyDecisionCommand,
    PolicyDecisionEvidence,
    PolicyError,
    PolicyEvent,
    PreparedPolicyAnchor,
    PreparedPolicyDecision,
    ProtectTarget,
    SenderSelector,
    SetFlowDisplayName,
    SetFlowIntention,
    SetSourceDisplayName,
    SetSourceRubro,
    UndoPolicy,
    is_policy_decision_command,
)

MAP_COMPOSITION_VERSION = 1

_CORDOBA = ZoneInfo("America/Argentina/Cordoba")
_INPUT_REVISION = re.compile(r"^input-v1-[0-9a-f]{64}$")


class MapSnapshotLike(Protocol):
    @property
    def account_key(self) -> str: ...

    @property
    def account_exists(self) -> bool: ...

    @property
    def indexed_account_keys(self) -> tuple[str, ...]: ...

    @property
    def fixture_version(self) -> str | None: ...

    @property
    def records(self) -> tuple[IndexedMessageRecord, ...]: ...

    @property
    def checkpoint(self) -> SyncCheckpoint | None: ...

    @property
    def policy_history(self) -> tuple[PolicyEvent, ...]: ...

    @property
    def active_policies(self) -> tuple[ActivePolicy, ...]: ...

    @property
    def policy_revision(self) -> int: ...

    @property
    def input_revision(self) -> str: ...


def validate_synthetic_snapshot(snapshot: MapSnapshotLike) -> None:
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
        if _INPUT_REVISION.fullmatch(snapshot.input_revision) is None:
            raise MapCompositionError(MapCompositionErrorCode.INVALID_INPUT)
        if not isinstance(snapshot.policy_revision, int) or isinstance(
            snapshot.policy_revision, bool
        ) or snapshot.policy_revision < 0:
            raise MapCompositionError(MapCompositionErrorCode.INVALID_INPUT)
        expected_revision = (
            snapshot.policy_history[-1].account_revision
            if snapshot.policy_history
            else 0
        )
        if snapshot.policy_revision != expected_revision:
            raise MapCompositionError(MapCompositionErrorCode.INVALID_INPUT)
    except SyntheticMapGateError:
        raise MapCompositionError(MapCompositionErrorCode.MAP_UNAVAILABLE) from None
    except MapCompositionError:
        raise
    except (AttributeError, TypeError, ValueError):
        raise MapCompositionError(MapCompositionErrorCode.INVALID_INPUT) from None


def _map_revision(input_revision: str) -> str:
    payload = {
        "classificationModelVersion": CLASSIFICATION_MODEL_VERSION,
        "indexRecordVersion": INDEX_RECORD_VERSION,
        "inputRevision": input_revision,
        "mapCompositionVersion": MAP_COMPOSITION_VERSION,
        "policyModelVersion": POLICY_MODEL_VERSION,
        "policyResultVersion": POLICY_RESULT_VERSION,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"map-v1-{hashlib.sha256(encoded).hexdigest()}"


def local_message_id(account_key: str, provider_message_id: str) -> str:
    if not account_key or not provider_message_id:
        raise MapCompositionError(MapCompositionErrorCode.INVALID_INPUT)
    digest = hashlib.sha256(
        f"mailcleanup.map.message.v1\0{account_key}\0{provider_message_id}".encode()
    ).hexdigest()
    return f"message-v1-{digest}"


def _classification_evidence(value: ClassificationEvidence) -> MapClassificationEvidence:
    return MapClassificationEvidence(
        code=value.code.value,
        label=value.label,
        detail=value.detail,
        strength=value.strength,
        origin=value.origin,
    )


def _evidence(value: EffectiveEvidence) -> MapEvidence:
    if isinstance(value, ClassificationEvidence):
        return _classification_evidence(value)
    if isinstance(value, PolicyDecisionEvidence):
        return MapPolicyEvidence(code=value.code, decision_id=value.decision_id)
    raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)


def _ordered_evidence(values: tuple[EffectiveEvidence, ...]) -> tuple[MapEvidence, ...]:
    converted = tuple(_evidence(item) for item in values)

    def key(item: MapEvidence) -> tuple[str, ...]:
        if isinstance(item, MapClassificationEvidence):
            return (
                "classification",
                item.code,
                item.strength.value,
                item.origin.value,
                item.label,
                item.detail,
            )
        return ("policy", item.code.value, item.decision_id)

    return tuple(sorted(converted, key=key))


def _automatic_evidence(
    values: tuple[ClassificationEvidence, ...],
) -> tuple[MapClassificationEvidence, ...]:
    return tuple(
        sorted(
            (_classification_evidence(item) for item in values),
            key=lambda item: (
                item.code,
                item.strength.value,
                item.origin.value,
                item.label,
                item.detail,
            ),
        )
    )


def _protection(value: EffectiveMessage | EffectiveSource | EffectiveFlow) -> MapProtection:
    return MapProtection(
        automatic=value.automatic_protection,
        effective=value.effective_protection,
        protected=value.protected,
        review_required=value.review_required,
        hard_excluded=value.hard_excluded,
        reasons=value.protection_reasons,
    )


def _sync(checkpoint: SyncCheckpoint | None) -> MapSync:
    if checkpoint is None:
        return MapSync(
            state=SyncState.NOT_STARTED,
            mode=None,
            processed_count=0,
            started_at=None,
            updated_at=None,
            error_code=None,
            partial=True,
        )
    return MapSync(
        state=checkpoint.state,
        mode=checkpoint.mode,
        processed_count=checkpoint.processed_count,
        started_at=checkpoint.started_at,
        updated_at=checkpoint.updated_at,
        error_code=checkpoint.error_code,
        partial=checkpoint.state is not SyncState.COMPLETED,
    )


def _monthly_volume(records: tuple[IndexedMessageRecord, ...]) -> tuple[MapMonthlyVolume, ...]:
    counts: dict[str, tuple[int, int]] = {}
    for record in records:
        month = record.received_at.astimezone(_CORDOBA).strftime("%Y-%m")
        message_count, total_bytes = counts.get(month, (0, 0))
        counts[month] = (message_count + 1, total_bytes + record.size_estimate_bytes)
    return tuple(
        MapMonthlyVolume(month=month, message_count=count, total_bytes=size)
        for month, (count, size) in sorted(counts.items())
    )


def _source_senders(records: tuple[IndexedMessageRecord, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {record.sender_address for record in records if record.sender_address is not None},
            key=lambda value: (value.casefold(), value),
        )
    )


def _source_domains(
    records: tuple[IndexedMessageRecord, ...],
    senders: tuple[str, ...],
) -> tuple[str, ...]:
    values = {
        record.authenticated_domain.casefold()
        for record in records
        if record.authenticated_domain is not None
    }
    values.update(sender.rsplit("@", 1)[-1].casefold() for sender in senders if "@" in sender)
    return tuple(sorted(values))


def _flow_projection(
    flow: EffectiveFlow,
    messages: tuple[EffectiveMessage, ...],
    records_by_id: dict[str, IndexedMessageRecord],
) -> MapFlow:
    records = tuple(records_by_id[item.provider_message_id] for item in messages)
    return MapFlow(
        id=flow.effective_flow_id,
        source_id=flow.effective_source_id,
        automatic_flow_id=flow.automatic_flow_id,
        automatic_display_name=flow.automatic_display_name,
        effective_display_name=flow.effective_display_name,
        automatic_intention=flow.automatic_intention,
        effective_intention=flow.effective_intention,
        subscription=flow.subscription,
        automatic_confidence=flow.automatic_confidence,
        effective_confidence=flow.effective_confidence,
        message_count=len(messages),
        protected_message_count=sum(item.protected for item in messages),
        review_required_message_count=sum(item.review_required for item in messages),
        hard_excluded_message_count=sum(item.hard_excluded for item in messages),
        total_bytes=sum(item.size_estimate_bytes for item in records),
        first_seen=min(item.received_at for item in records),
        last_seen=max(item.received_at for item in records),
        protection=_protection(flow),
        automatic_evidence=_automatic_evidence(flow.automatic_evidence),
        effective_evidence=_ordered_evidence(flow.effective_evidence),
        decision_ids=flow.decision_ids,
        structural_decision_ids=flow.structural_decision_ids,
    )


def _source_projection(
    source: EffectiveSource,
    messages: tuple[EffectiveMessage, ...],
    flows: tuple[MapFlow, ...],
    records_by_id: dict[str, IndexedMessageRecord],
) -> MapSource:
    records = tuple(records_by_id[item.provider_message_id] for item in messages)
    senders = _source_senders(records)
    return MapSource(
        id=source.effective_source_id,
        automatic_source_ids=source.automatic_source_ids,
        automatic_display_name=source.automatic_display_name,
        effective_display_name=source.effective_display_name,
        automatic_rubro=source.automatic_rubro,
        effective_rubro=source.effective_rubro,
        automatic_confidence=source.automatic_confidence,
        effective_confidence=source.effective_confidence,
        message_count=len(messages),
        flow_count=len(flows),
        protected_message_count=sum(item.protected for item in messages),
        review_required_message_count=sum(item.review_required for item in messages),
        hard_excluded_message_count=sum(item.hard_excluded for item in messages),
        total_bytes=sum(item.size_estimate_bytes for item in records),
        first_seen=min(item.received_at for item in records),
        last_seen=max(item.received_at for item in records),
        senders=senders,
        domains=_source_domains(records, senders),
        monthly_volume=_monthly_volume(records),
        protection=_protection(source),
        automatic_evidence=_automatic_evidence(source.automatic_evidence),
        effective_evidence=_ordered_evidence(source.effective_evidence),
        decision_ids=source.decision_ids,
        structural_decision_ids=source.structural_decision_ids,
        flows=flows,
    )


def _sample(
    account_key: str,
    record: IndexedMessageRecord,
    message: EffectiveMessage,
) -> MapMessageSample:
    return MapMessageSample(
        id=local_message_id(account_key, record.provider_message_id),
        received_at=record.received_at,
        sender_name=record.sender_name,
        sender_address=record.sender_address,
        subject=record.subject,
        label_ids=record.label_ids,
        category=record.category,
        size_estimate_bytes=record.size_estimate_bytes,
        source_id=message.effective_source_id,
        flow_id=message.effective_flow_id,
        automatic_rubro=message.automatic_rubro,
        effective_rubro=message.effective_rubro,
        automatic_intention=message.automatic_intention,
        effective_intention=message.effective_intention,
        subscription=message.subscription,
        automatic_confidence=message.automatic_confidence,
        effective_confidence=message.effective_confidence,
        protection=_protection(message),
    )


def _target_anchor(event: PolicyEvent) -> PreparedPolicyAnchor:
    matches = tuple(anchor for anchor in event.anchors if anchor.role is PolicyAnchorRole.TARGET)
    if len(matches) != 1:
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
    return matches[0]


def _public_target_kind(
    selector: object,
) -> Literal["source", "flow", "message", "sender", "label"]:
    if isinstance(selector, EffectiveSourceSelector):
        return "source"
    if isinstance(selector, EffectiveFlowSelector):
        return "flow"
    if isinstance(selector, MessageSelector):
        return "message"
    if isinstance(selector, SenderSelector):
        return "sender"
    if isinstance(selector, LabelSelector):
        return "label"
    raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)


def _observed_target(event: PolicyEvent) -> MapObservedTarget:
    anchor = _target_anchor(event)
    return MapObservedTarget(
        kind=_public_target_kind(anchor.selector),
        observed_effective_id=anchor.observed_effective_id,
        observed_source_ids=anchor.observed_source_ids,
        observed_flow_ids=anchor.observed_flow_ids,
    )


def _partition_group_summaries(event: PolicyEvent) -> tuple[MapPartitionGroupSummary, ...]:
    command = event.command
    if not isinstance(command, PartitionSource):
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
    values: list[MapPartitionGroupSummary] = []
    for group_index in range(len(command.groups)):
        anchors = tuple(
            anchor
            for anchor in event.anchors
            if anchor.role is PolicyAnchorRole.PARTITION_MEMBER
            and anchor.group_order == group_index
        )
        if not anchors or any(
            not isinstance(anchor.selector, PartitionAnchor) for anchor in anchors
        ):
            raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
        partition_anchors = tuple(
            anchor.selector
            for anchor in anchors
            if isinstance(anchor.selector, PartitionAnchor)
        )
        values.append(
            MapPartitionGroupSummary(
                group_index=group_index,
                anchor_count=len(anchors),
                anchor_kinds=tuple(
                    sorted({anchor.kind.value for anchor in partition_anchors})
                ),
                observed_source_ids=tuple(
                    sorted(
                        {
                            source_id
                            for anchor in anchors
                            for source_id in anchor.observed_source_ids
                        }
                    )
                ),
                observed_flow_ids=tuple(
                    sorted(
                        {
                            flow_id
                            for anchor in anchors
                            for flow_id in anchor.observed_flow_ids
                        }
                    )
                ),
            )
        )
    return tuple(values)


def _decision_history(
    history: tuple[PolicyEvent, ...],
    active_policies: tuple[ActivePolicy, ...],
    effective: PolicyApplicationResult,
) -> MapDecisionHistory:
    active_ids = {policy.decision_id for policy in active_policies}
    bindings = {binding.decision_id: binding for binding in effective.bindings}
    values: list[MapDecision] = []
    for event in history:
        command = event.command
        if is_policy_decision_command(command):
            active = command.decision_id in active_ids
            binding = bindings.get(command.decision_id)
            supersedes = command.supersedes_decision_ids
        else:
            active = False
            binding = None
            supersedes = ()
        binding_status = binding.status if binding is not None else None
        current_target_ids = binding.current_effective_ids if binding is not None else ()

        if isinstance(command, SetSourceDisplayName):
            target = _observed_target(event)
            if target.observed_effective_id is None:
                raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
            item: MapDecision = MapSetSourceDisplayNameDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                source_id=target.observed_effective_id,
                display_name=command.display_name,
            )
        elif isinstance(command, SetSourceRubro):
            target = _observed_target(event)
            if target.observed_effective_id is None:
                raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
            item = MapSetSourceRubroDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                source_id=target.observed_effective_id,
                rubro=command.rubro,
            )
        elif isinstance(command, SetFlowDisplayName):
            target = _observed_target(event)
            if target.observed_effective_id is None:
                raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
            item = MapSetFlowDisplayNameDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                flow_id=target.observed_effective_id,
                display_name=command.display_name,
            )
        elif isinstance(command, SetFlowIntention):
            target = _observed_target(event)
            if target.observed_effective_id is None:
                raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
            item = MapSetFlowIntentionDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                flow_id=target.observed_effective_id,
                intention=command.intention,
            )
        elif isinstance(command, MergeSources):
            source_ids = tuple(
                sorted(
                    anchor.observed_effective_id
                    for anchor in event.anchors
                    if anchor.role is PolicyAnchorRole.MERGE_PARTICIPANT
                    and anchor.observed_effective_id is not None
                )
            )
            item = MapMergeSourcesDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                source_ids=source_ids,
            )
        elif isinstance(command, PartitionSource):
            target = _observed_target(event)
            if target.observed_effective_id is None:
                raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
            groups = _partition_group_summaries(event)
            item = MapPartitionSourceDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                source_id=target.observed_effective_id,
                group_count=len(groups),
                groups=groups,
            )
        elif isinstance(command, ProtectTarget):
            item = MapProtectTargetDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=active,
                undoable=active,
                supersedes_decision_ids=supersedes,
                binding_status=binding_status,
                current_target_ids=current_target_ids,
                decision_id=command.decision_id,
                target=_observed_target(event),
            )
        elif isinstance(command, UndoPolicy):
            item = MapUndoPolicyDecision(
                command_id=command.command_id,
                revision=event.account_revision,
                occurred_at=command.occurred_at,
                active=False,
                undoable=False,
                supersedes_decision_ids=(),
                binding_status=None,
                current_target_ids=(),
                target_decision_id=command.target_decision_id,
            )
        else:
            raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
        values.append(item)
    return MapDecisionHistory(
        contract_version=MAP_CONTRACT_VERSION,
        data_mode=MAP_DATA_MODE,
        policy_revision=len(history),
        events=tuple(values),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class MapCompositionResult:
    projection: MapProjection
    records: tuple[IndexedMessageRecord, ...] = field(repr=False)
    classification: ClassificationResult = field(repr=False)
    effective: PolicyApplicationResult = field(repr=False)
    active_policies: tuple[ActivePolicy, ...] = field(repr=False)
    policy_history: tuple[PolicyEvent, ...] = field(repr=False)
    source_selectors: tuple[tuple[str, EffectiveSourceSelector], ...] = field(repr=False)
    flow_selectors: tuple[tuple[str, EffectiveFlowSelector], ...] = field(repr=False)
    message_selectors: tuple[tuple[str, MessageSelector], ...] = field(repr=False)
    records_by_message_id: tuple[tuple[str, IndexedMessageRecord], ...] = field(repr=False)
    samples: tuple[MapMessageSample, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.projection, MapProjection):
            raise TypeError("projection must be a MapProjection")
        for field_name in (
            "records",
            "active_policies",
            "policy_history",
            "source_selectors",
            "flow_selectors",
            "message_selectors",
            "records_by_message_id",
            "samples",
        ):
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple")

    def __repr__(self) -> str:
        return (
            "MapCompositionResult("
            f"map_revision={self.projection.map_revision!r}, "
            f"message_count={len(self.records)}, "
            f"source_count={len(self.source_selectors)}, "
            f"flow_count={len(self.flow_selectors)}, "
            f"policy_revision={self.projection.policy_revision})"
        )

    def resolve_source(self, source_id: str) -> EffectiveSourceSelector | None:
        return next((value for key, value in self.source_selectors if key == source_id), None)

    def resolve_flow(self, flow_id: str) -> EffectiveFlowSelector | None:
        return next((value for key, value in self.flow_selectors if key == flow_id), None)

    def resolve_message(self, message_id: str) -> MessageSelector | None:
        return next((value for key, value in self.message_selectors if key == message_id), None)

    def record_for_message(self, message_id: str) -> IndexedMessageRecord | None:
        return next((value for key, value in self.records_by_message_id if key == message_id), None)

    def resolve_sender(self, sender_address: str) -> SenderSelector | None:
        if not isinstance(sender_address, str):
            return None
        normalized = sender_address.strip().casefold()
        if normalized != sender_address or not any(
            record.sender_address == normalized for record in self.records
        ):
            return None
        try:
            return SenderSelector(
                account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
                sender_address=normalized,
            )
        except (TypeError, ValueError):
            return None

    def resolve_label(self, label_id: str) -> LabelSelector | None:
        if (
            not isinstance(label_id, str)
            or not label_id
            or label_id != label_id.strip()
            or not any(label_id in record.label_ids for record in self.records)
        ):
            return None
        try:
            return LabelSelector(
                account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
                label_id=label_id,
            )
        except (TypeError, ValueError):
            return None

    def partition_anchor_for_source_flow(
        self,
        source_id: str,
        flow_id: str,
    ) -> PartitionAnchor | None:
        source = self.resolve_source(source_id)
        flow = self.resolve_flow(flow_id)
        if source is None or flow is None or flow.effective_source != source:
            return None
        return PartitionAnchor(kind=PartitionAnchorKind.FLOW, flow=flow.automatic_flow)

    def partition_anchor_for_source_message(
        self,
        source_id: str,
        message_id: str,
    ) -> PartitionAnchor | None:
        selector = self.resolve_message(message_id)
        sample = next((item for item in self.samples if item.id == message_id), None)
        if selector is None or sample is None or sample.source_id != source_id:
            return None
        return PartitionAnchor(
            kind=PartitionAnchorKind.MESSAGE,
            provider_message_id=selector.provider_message_id,
        )

    def partition_anchor_for_source_sender(
        self,
        source_id: str,
        sender_address: str,
    ) -> PartitionAnchor | None:
        source = next((item for item in self.projection.sources if item.id == source_id), None)
        selector = self.resolve_sender(sender_address)
        if source is None or selector is None or selector.sender_address not in source.senders:
            return None
        return PartitionAnchor(
            kind=PartitionAnchorKind.SENDER,
            sender_address=selector.sender_address,
        )

    def canonical_partition_anchors(self, source_id: str) -> tuple[PartitionAnchor, ...]:
        """Return one deterministic complete flow-based partition proposal.

        It is not an allowlist: public sender, flow and fallback-message anchors
        remain valid when D5 resolves them as complete and disjoint.
        """
        selector = self.resolve_source(source_id)
        if selector is None or selector.kind is not EffectiveSourceKind.AUTOMATIC:
            return ()
        anchors = tuple(
            PartitionAnchor(kind=PartitionAnchorKind.FLOW, flow=flow.automatic_flow)
            for flow_id, flow in self.flow_selectors
            if flow.effective_source == selector
            and any(
                projected.id == flow_id and projected.source_id == source_id
                for source in self.projection.sources
                for projected in source.flows
            )
        )
        return tuple(sorted(anchors, key=lambda item: item.canonical_key))

    def prepare_decision(self, command: PolicyDecisionCommand) -> PreparedPolicyDecision:
        return prepare_policy_decision(
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            records=self.records,
            classification=self.classification,
            active_policies=self.active_policies,
            command=command,
        )

    def decision_history(self) -> MapDecisionHistory:
        try:
            return _decision_history(
                self.policy_history,
                self.active_policies,
                self.effective,
            )
        except MapCompositionError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError):
            raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH) from None

    def source_detail(self, source_id: str, *, limit: int = 5) -> MapSourceDetail | None:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 5:
            raise ValueError("limit must be between zero and five")
        source = next((item for item in self.projection.sources if item.id == source_id), None)
        if source is None:
            return None
        values = tuple(
            sorted(
                (item for item in self.samples if item.source_id == source_id),
                key=lambda item: (-item.received_at.timestamp(), item.id),
            )[:limit]
        )
        return MapSourceDetail(source=source, recent_messages=values)


def _compose(snapshot: MapSnapshotLike) -> MapCompositionResult:
    validate_synthetic_snapshot(snapshot)
    records = tuple(snapshot.records)
    classification = classify_indexed_records(records)
    effective = apply_local_policies(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        records,
        classification,
        tuple(snapshot.active_policies),
    )

    record_ids = tuple(sorted(record.provider_message_id for record in records))
    if len(record_ids) != len(set(record_ids)):
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
    if record_ids != tuple(item.provider_message_id for item in classification.messages):
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
    if record_ids != tuple(item.provider_message_id for item in effective.messages):
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)

    records_by_id = {record.provider_message_id: record for record in records}
    messages_by_source: dict[str, list[EffectiveMessage]] = defaultdict(list)
    messages_by_flow: dict[str, list[EffectiveMessage]] = defaultdict(list)
    for message in effective.messages:
        messages_by_source[message.effective_source_id].append(message)
        messages_by_flow[message.effective_flow_id].append(message)

    projected_flows: dict[str, MapFlow] = {}
    for flow in effective.flows:
        members = tuple(messages_by_flow[flow.effective_flow_id])
        if not members:
            raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
        projected_flows[flow.effective_flow_id] = _flow_projection(
            flow,
            members,
            records_by_id,
        )

    projected_sources: list[MapSource] = []
    for source in effective.sources:
        members = tuple(messages_by_source[source.effective_source_id])
        if not members:
            raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH)
        source_flows = tuple(
            sorted(
                (
                    projected_flows[flow.effective_flow_id]
                    for flow in effective.flows
                    if flow.effective_source_id == source.effective_source_id
                ),
                key=lambda item: (
                    -item.message_count,
                    item.effective_display_name.casefold(),
                    item.id,
                ),
            )
        )
        projected_sources.append(
            _source_projection(source, members, source_flows, records_by_id)
        )
    sources = tuple(
        sorted(
            projected_sources,
            key=lambda item: (
                -item.message_count,
                item.effective_display_name.casefold(),
                item.id,
            ),
        )
    )

    all_records = tuple(records_by_id[item.provider_message_id] for item in effective.messages)
    summary = MapSummary(
        message_count=len(effective.messages),
        source_count=len(effective.sources),
        flow_count=len(effective.flows),
        protected_message_count=sum(item.protected for item in effective.messages),
        review_required_message_count=sum(
            item.review_required for item in effective.messages
        ),
        hard_excluded_message_count=sum(item.hard_excluded for item in effective.messages),
        total_bytes=sum(item.size_estimate_bytes for item in all_records),
        first_seen=min((item.received_at for item in all_records), default=None),
        last_seen=max((item.received_at for item in all_records), default=None),
    )
    review_bindings = tuple(
        MapPolicyReviewBinding(
            decision_id=item.decision_id,
            status=item.status,
            current_effective_ids=item.current_effective_ids,
        )
        for item in effective.bindings
        if item.status not in {PolicyBindingStatus.EXACT, PolicyBindingStatus.REBOUND}
    )
    policy_review = MapPolicyReview(
        total=len(review_bindings),
        bindings=review_bindings,
    )
    projection = MapProjection(
        contract_version=MAP_CONTRACT_VERSION,
        data_mode=MAP_DATA_MODE,
        map_revision=_map_revision(snapshot.input_revision),
        policy_revision=snapshot.policy_revision,
        sync=_sync(snapshot.checkpoint),
        summary=summary,
        policy_review=policy_review,
        sources=sources,
    )

    samples = tuple(
        _sample(
            SYNTHETIC_MAP_ACCOUNT_KEY,
            records_by_id[message.provider_message_id],
            message,
        )
        for message in effective.messages
    )
    return MapCompositionResult(
        projection=projection,
        records=records,
        classification=classification,
        effective=effective,
        active_policies=tuple(snapshot.active_policies),
        policy_history=tuple(snapshot.policy_history),
        source_selectors=tuple(
            (source.effective_source_id, source.selector) for source in effective.sources
        ),
        flow_selectors=tuple(
            (flow.effective_flow_id, flow.selector) for flow in effective.flows
        ),
        message_selectors=tuple(
            (
                local_message_id(SYNTHETIC_MAP_ACCOUNT_KEY, message.provider_message_id),
                MessageSelector(
                    account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
                    provider_message_id=message.provider_message_id,
                ),
            )
            for message in effective.messages
        ),
        records_by_message_id=tuple(
            (
                local_message_id(SYNTHETIC_MAP_ACCOUNT_KEY, record.provider_message_id),
                record,
            )
            for record in records
        ),
        samples=samples,
    )


def compose_map(snapshot: MapSnapshotLike) -> MapCompositionResult:
    try:
        return _compose(snapshot)
    except MapCompositionError:
        raise
    except (ClassificationError, PolicyError, AttributeError, KeyError, TypeError, ValueError):
        raise MapCompositionError(MapCompositionErrorCode.COMPOSITION_MISMATCH) from None
