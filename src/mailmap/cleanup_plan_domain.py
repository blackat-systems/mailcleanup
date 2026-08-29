from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol, TypeAlias
from zoneinfo import ZoneInfo

from mailmap.classification_model import (
    ClassificationResult,
    SourceIdentityDescriptor,
)
from mailmap.cleanup_plan_model import (
    CLEANUP_PLAN_CONTRACT_VERSION,
    CLEANUP_PLAN_TIME_ZONE,
    CLEANUP_PLAN_VALIDITY_SECONDS,
    MAX_AGGREGATE_SIZE_ESTIMATE_BYTES,
    MAX_CONSIDERED_MESSAGES,
    MAX_EXCLUDED_SAMPLES,
    MAX_INCLUDED_SAMPLES,
    MAX_MESSAGE_SIZE_ESTIMATE_BYTES,
    AllTemporalFilter,
    BeforeDateTemporalFilter,
    CancelCleanupPlanCommand,
    CleanupCommandStatus,
    CleanupEventType,
    CleanupExclusionReason,
    CleanupLabelSnapshot,
    CleanupMemberCurrentState,
    CleanupMemberInitialState,
    CleanupPlanError,
    CleanupPlanErrorCode,
    CleanupPlanEvent,
    CleanupPlanMember,
    CleanupPlanMemberRemoval,
    CleanupPlanReceipt,
    CleanupPlanSample,
    CleanupPlanSelection,
    CleanupPlanState,
    CleanupReadState,
    CleanupSampleKind,
    CleanupTarget,
    CleanupTargetCatalogItem,
    CleanupTargetKind,
    CleanupTargetSnapshot,
    CleanupTemporalFilter,
    CreateCleanupPlanCommand,
    DateRangeTemporalFilter,
    FlowCatalogItem,
    FlowTargetSnapshot,
    LabelCatalogItem,
    OlderThanDaysTemporalFilter,
    PersistedCleanupPlan,
    PreparedCleanupPlanCancellation,
    PreparedCleanupPlanCreation,
    PreparedCleanupPlanRevalidation,
    ResolvedTemporalFilter,
    RevalidateCleanupPlanCommand,
    SenderCatalogItem,
    SenderTargetSnapshot,
    SourceCatalogItem,
    SourceTargetSnapshot,
)
from mailmap.index_model import IndexedMessageRecord
from mailmap.map_composition import (
    MapCompositionResult,
    MapSnapshotLike,
    compose_map,
    local_message_id,
)
from mailmap.map_model import MapCompositionError, MapProjection
from mailmap.policy_model import (
    EffectiveFlowSelector,
    EffectiveMessage,
    EffectiveSourceSelector,
    PolicyApplicationResult,
)

_CORDOBA = ZoneInfo(CLEANUP_PLAN_TIME_ZONE)
_SYSTEM_LABELS: tuple[tuple[str, str], ...] = (
    ("INBOX", "Recibidos"),
    ("CATEGORY_PERSONAL", "Principal"),
    ("CATEGORY_SOCIAL", "Social"),
    ("CATEGORY_PROMOTIONS", "Promociones"),
    ("CATEGORY_UPDATES", "Actualizaciones"),
    ("CATEGORY_FORUMS", "Foros"),
)
_CATALOG_RANK = {
    CleanupTargetKind.SOURCE: 0,
    CleanupTargetKind.FLOW: 1,
    CleanupTargetKind.SENDER: 2,
    CleanupTargetKind.LABEL: 3,
}
_REASON_RANK = {reason: index for index, reason in enumerate(CleanupExclusionReason)}


class CleanupPlanCompositionLike(Protocol):
    @property
    def projection(self) -> MapProjection: ...

    @property
    def records(self) -> tuple[IndexedMessageRecord, ...]: ...

    @property
    def classification(self) -> ClassificationResult: ...

    @property
    def effective(self) -> PolicyApplicationResult: ...

    @property
    def source_selectors(self) -> tuple[tuple[str, EffectiveSourceSelector], ...]: ...

    @property
    def flow_selectors(self) -> tuple[tuple[str, EffectiveFlowSelector], ...]: ...


@dataclass(frozen=True, slots=True)
class _CompositionIndex:
    account_key: str = field(repr=False)
    projection: MapProjection
    records_by_provider_id: dict[str, IndexedMessageRecord] = field(repr=False)
    classified_source_by_message_id: dict[str, SourceIdentityDescriptor] = field(repr=False)
    effective_by_provider_id: dict[str, EffectiveMessage] = field(repr=False)
    source_selectors: dict[str, EffectiveSourceSelector] = field(repr=False)
    flow_selectors: dict[str, EffectiveFlowSelector] = field(repr=False)


def _study_unavailable() -> CleanupPlanError:
    return CleanupPlanError(CleanupPlanErrorCode.STUDY_UNAVAILABLE)


def compose_cleanup_plan_snapshot(
    snapshot: MapSnapshotLike,
) -> MapCompositionResult:
    """Compose the one authorized D1+D4+D5 snapshot behind the D7 boundary."""

    try:
        return compose_map(snapshot)
    except MapCompositionError:
        raise _study_unavailable() from None
    except (AttributeError, KeyError, TypeError, ValueError):
        raise _study_unavailable() from None


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_FILTER)
    return value.astimezone(UTC)


def _visible_metadata(value: str | None) -> None:
    if value is not None and (not isinstance(value, str) or len(value.encode("utf-8")) > 16_384):
        raise _study_unavailable()


def _index_composition(composition: CleanupPlanCompositionLike) -> _CompositionIndex:
    try:
        if not isinstance(composition.projection, MapProjection):
            raise TypeError
        if not isinstance(composition.classification, ClassificationResult):
            raise TypeError
        if not isinstance(composition.effective, PolicyApplicationResult):
            raise TypeError
        records = composition.records
        if not isinstance(records, tuple) or any(
            not isinstance(item, IndexedMessageRecord) for item in records
        ):
            raise TypeError
        account_key = composition.effective.account_key
        if composition.classification.account_key != account_key:
            raise ValueError
        if any(record.account_key != account_key for record in records):
            raise ValueError

        records_by_provider_id = {item.provider_message_id: item for item in records}
        if len(records_by_provider_id) != len(records):
            raise ValueError
        effective_by_provider_id = {
            item.provider_message_id: item for item in composition.effective.messages
        }
        if set(effective_by_provider_id) != set(records_by_provider_id):
            raise ValueError
        classified_messages = {
            item.provider_message_id: item for item in composition.classification.messages
        }
        classified_sources = {
            item.source_id: item.identity_descriptor for item in composition.classification.sources
        }
        if set(classified_messages) != set(records_by_provider_id):
            raise ValueError
        classified_source_by_message_id = {
            provider_message_id: classified_sources[item.source_id]
            for provider_message_id, item in classified_messages.items()
        }
        source_selectors = dict(composition.source_selectors)
        flow_selectors = dict(composition.flow_selectors)
        if len(source_selectors) != len(composition.source_selectors):
            raise ValueError
        if len(flow_selectors) != len(composition.flow_selectors):
            raise ValueError
        projected_sources = {source.id for source in composition.projection.sources}
        projected_flows = {
            flow.id for source in composition.projection.sources for flow in source.flows
        }
        if projected_sources != set(source_selectors) or projected_flows != set(flow_selectors):
            raise ValueError
        for record in records:
            if (
                isinstance(record.size_estimate_bytes, bool)
                or record.size_estimate_bytes < 0
                or record.size_estimate_bytes > MAX_MESSAGE_SIZE_ESTIMATE_BYTES
            ):
                raise ValueError
            for value in (record.sender_name, record.sender_address, record.subject):
                _visible_metadata(value)
        return _CompositionIndex(
            account_key=account_key,
            projection=composition.projection,
            records_by_provider_id=records_by_provider_id,
            classified_source_by_message_id=classified_source_by_message_id,
            effective_by_provider_id=effective_by_provider_id,
            source_selectors=source_selectors,
            flow_selectors=flow_selectors,
        )
    except CleanupPlanError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        raise _study_unavailable() from None


def canonical_sender_address_v1(
    record: IndexedMessageRecord,
    source_descriptor: SourceIdentityDescriptor,
) -> str | None:
    """Return the only sender identity C6 may use for a classified record."""

    if not isinstance(record, IndexedMessageRecord) or not isinstance(
        source_descriptor, SourceIdentityDescriptor
    ):
        raise _study_unavailable()
    if record.sender_address is None:
        return None
    normalized = record.sender_address.strip().casefold()
    if not normalized or normalized not in source_descriptor.sender_addresses:
        raise _study_unavailable()
    return normalized


def sender_target_id_v1(account_key: str, canonical_sender_address: str) -> str:
    if not isinstance(account_key, str) or not account_key or "@" in account_key:
        raise _study_unavailable()
    if (
        not isinstance(canonical_sender_address, str)
        or not canonical_sender_address
        or canonical_sender_address != canonical_sender_address.strip().casefold()
    ):
        raise _study_unavailable()
    digest = hashlib.sha256(
        ("mailcleanup.study.sender.v1\0" + account_key + "\0" + canonical_sender_address).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"sender-v1-{digest}"


def label_target_id_v1(account_key: str, provider_label_id: str) -> str:
    if not isinstance(account_key, str) or not account_key or "@" in account_key:
        raise _study_unavailable()
    if (
        not isinstance(provider_label_id, str)
        or not provider_label_id
        or provider_label_id != provider_label_id.strip()
    ):
        raise _study_unavailable()
    digest = hashlib.sha256(
        ("mailcleanup.study.label.v1\0" + account_key + "\0" + provider_label_id).encode("utf-8")
    ).hexdigest()
    return f"label-v1-{digest}"


def _selector_fingerprint(
    selector: EffectiveSourceSelector | EffectiveFlowSelector,
) -> str:
    encoded = json.dumps(
        selector.canonical_key,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _catalog_text(value: CleanupTargetCatalogItem) -> str:
    if isinstance(value, (SourceCatalogItem, FlowCatalogItem, LabelCatalogItem)):
        return value.display_name
    if isinstance(value, SenderCatalogItem):
        return value.display_address
    raise _study_unavailable()


def _catalog_sort_key(value: CleanupTargetCatalogItem) -> tuple[int, str, str]:
    return (_CATALOG_RANK[value.kind], _catalog_text(value).casefold(), value.target_id)


def build_cleanup_target_catalog(
    composition: CleanupPlanCompositionLike,
) -> tuple[CleanupTargetCatalogItem, ...]:
    index = _index_composition(composition)
    values: list[CleanupTargetCatalogItem] = []

    for source in composition.projection.sources:
        _visible_metadata(source.effective_display_name)
        selector = index.source_selectors[source.id]
        values.append(
            SourceCatalogItem(
                target_id=source.id,
                display_name=source.effective_display_name,
                message_count=source.message_count,
                selector_fingerprint=_selector_fingerprint(selector),
            )
        )
        for flow in source.flows:
            _visible_metadata(flow.effective_display_name)
            flow_selector = index.flow_selectors[flow.id]
            values.append(
                FlowCatalogItem(
                    target_id=flow.id,
                    source_id=source.id,
                    display_name=flow.effective_display_name,
                    message_count=flow.message_count,
                    selector_fingerprint=_selector_fingerprint(flow_selector),
                )
            )

    sender_counts: dict[str, int] = {}
    for provider_message_id, record in index.records_by_provider_id.items():
        sender_address = canonical_sender_address_v1(
            record, index.classified_source_by_message_id[provider_message_id]
        )
        if sender_address is not None:
            sender_counts[sender_address] = sender_counts.get(sender_address, 0) + 1
    for sender_address, message_count in sender_counts.items():
        values.append(
            SenderCatalogItem(
                target_id=sender_target_id_v1(index.account_key, sender_address),
                display_address=sender_address,
                message_count=message_count,
            )
        )

    label_names = dict(_SYSTEM_LABELS)
    label_counts = {
        provider_label_id: sum(
            provider_label_id in record.label_ids
            for record in index.records_by_provider_id.values()
        )
        for provider_label_id in label_names
    }
    for provider_label_id, display_name in _SYSTEM_LABELS:
        message_count = label_counts[provider_label_id]
        if message_count:
            values.append(
                LabelCatalogItem(
                    target_id=label_target_id_v1(index.account_key, provider_label_id),
                    display_name=display_name,
                    provider_label_id=provider_label_id,
                    message_count=message_count,
                )
            )

    result = tuple(sorted(values, key=_catalog_sort_key))
    if len({item.target_id for item in result}) != len(result):
        raise _study_unavailable()
    return result


def _civil_midnight(value: date) -> datetime:
    candidate = datetime.combine(value, time.min, tzinfo=_CORDOBA)
    utc_value = candidate.astimezone(UTC)
    round_trip = utc_value.astimezone(_CORDOBA)
    if round_trip.date() != value or round_trip.time() != time.min:
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_FILTER)
    return utc_value


def resolve_temporal_filter(
    requested: CleanupTemporalFilter,
    command_now: datetime,
) -> ResolvedTemporalFilter:
    now = _utc(command_now)
    try:
        if isinstance(requested, AllTemporalFilter):
            return ResolvedTemporalFilter(
                requested=requested,
                resolved_on_or_after_utc=None,
                resolved_before_utc=None,
            )
        if isinstance(requested, BeforeDateTemporalFilter):
            return ResolvedTemporalFilter(
                requested=requested,
                resolved_on_or_after_utc=None,
                resolved_before_utc=_civil_midnight(requested.date),
            )
        if isinstance(requested, DateRangeTemporalFilter):
            return ResolvedTemporalFilter(
                requested=requested,
                resolved_on_or_after_utc=_civil_midnight(requested.on_or_after_date),
                resolved_before_utc=_civil_midnight(requested.before_date),
            )
        if isinstance(requested, OlderThanDaysTemporalFilter):
            local_date = now.astimezone(_CORDOBA).date()
            return ResolvedTemporalFilter(
                requested=requested,
                resolved_on_or_after_utc=None,
                resolved_before_utc=_civil_midnight(local_date - timedelta(days=requested.days)),
            )
    except (OverflowError, TypeError, ValueError):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_FILTER) from None
    raise CleanupPlanError(CleanupPlanErrorCode.INVALID_FILTER)


def _temporal_payload(value: CleanupTemporalFilter) -> tuple[str, ...]:
    if isinstance(value, AllTemporalFilter):
        return (value.kind.value,)
    if isinstance(value, BeforeDateTemporalFilter):
        return (value.kind.value, value.date.isoformat())
    if isinstance(value, DateRangeTemporalFilter):
        return (
            value.kind.value,
            value.on_or_after_date.isoformat(),
            value.before_date.isoformat(),
        )
    if isinstance(value, OlderThanDaysTemporalFilter):
        return (value.kind.value, str(value.days))
    raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)


CleanupCommand: TypeAlias = (
    CreateCleanupPlanCommand | RevalidateCleanupPlanCommand | CancelCleanupPlanCommand
)


def cleanup_command_fingerprint(
    command: CleanupCommand,
    *,
    plan_id: str | None = None,
) -> str:
    if isinstance(command, CreateCleanupPlanCommand):
        if plan_id is not None:
            raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
        path = "/api/v3/study/plans"
        body: tuple[object, ...] = (
            command.command_id,
            command.expected_map_revision,
            command.expected_policy_revision,
            command.disposition.value,
            tuple((item.kind.value, item.target_id) for item in command.targets),
            _temporal_payload(command.temporal_filter),
            command.read_state.value,
            command.excluded_label_ids,
            command.keep_latest_per_flow,
        )
    elif isinstance(command, RevalidateCleanupPlanCommand):
        if plan_id is None:
            raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
        path = f"/api/v3/study/plans/{plan_id}/revalidate"
        body = (
            command.command_id,
            command.expected_plan_revision,
            command.expected_map_revision,
            command.expected_policy_revision,
        )
    elif isinstance(command, CancelCleanupPlanCommand):
        if plan_id is None:
            raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
        path = f"/api/v3/study/plans/{plan_id}/cancel"
        body = (command.command_id, command.expected_plan_revision)
    else:
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    payload = (
        CLEANUP_PLAN_CONTRACT_VERSION,
        "POST",
        path,
        body,
    )
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _catalog_by_id(
    composition: CleanupPlanCompositionLike,
) -> dict[str, CleanupTargetCatalogItem]:
    return {item.target_id: item for item in build_cleanup_target_catalog(composition)}


def _target_snapshot(value: CleanupTargetCatalogItem) -> CleanupTargetSnapshot:
    if isinstance(value, SourceCatalogItem):
        return SourceTargetSnapshot(
            target_id=value.target_id,
            display_name=value.display_name,
            selector_fingerprint=value.selector_fingerprint,
        )
    if isinstance(value, FlowCatalogItem):
        return FlowTargetSnapshot(
            target_id=value.target_id,
            display_name=value.display_name,
            selector_fingerprint=value.selector_fingerprint,
        )
    if isinstance(value, SenderCatalogItem):
        return SenderTargetSnapshot(
            target_id=value.target_id,
            display_address=value.display_address,
        )
    raise CleanupPlanError(CleanupPlanErrorCode.UNSUPPORTED_TARGET)


def _provider_ids_for_target(
    target: CleanupTarget,
    index: _CompositionIndex,
    catalog_by_id: dict[str, CleanupTargetCatalogItem],
    *,
    allow_missing_sender: bool,
) -> set[str]:
    item = catalog_by_id.get(target.target_id)
    if item is None:
        if allow_missing_sender and target.kind is CleanupTargetKind.SENDER:
            return set()
        raise CleanupPlanError(CleanupPlanErrorCode.TARGET_NOT_FOUND)
    if item.kind is not target.kind or target.kind is CleanupTargetKind.LABEL:
        raise CleanupPlanError(CleanupPlanErrorCode.UNSUPPORTED_TARGET)
    if target.kind is CleanupTargetKind.SOURCE:
        return {
            provider_message_id
            for provider_message_id, effective in index.effective_by_provider_id.items()
            if effective.effective_source_id == target.target_id
        }
    if target.kind is CleanupTargetKind.FLOW:
        return {
            provider_message_id
            for provider_message_id, effective in index.effective_by_provider_id.items()
            if effective.effective_flow_id == target.target_id
        }
    assert isinstance(item, SenderCatalogItem)
    result: set[str] = set()
    for provider_message_id, record in index.records_by_provider_id.items():
        sender_address = canonical_sender_address_v1(
            record, index.classified_source_by_message_id[provider_message_id]
        )
        if sender_address == item.display_address:
            result.add(provider_message_id)
    return result


def _target_universe(
    targets: tuple[CleanupTarget, ...],
    index: _CompositionIndex,
    catalog_by_id: dict[str, CleanupTargetCatalogItem],
    *,
    allow_missing_sender: bool,
) -> set[str]:
    values: set[str] = set()
    for target in targets:
        values.update(
            _provider_ids_for_target(
                target,
                index,
                catalog_by_id,
                allow_missing_sender=allow_missing_sender,
            )
        )
    if len(values) > MAX_CONSIDERED_MESSAGES:
        raise CleanupPlanError(CleanupPlanErrorCode.PLAN_TOO_LARGE)
    return values


def _record_read_state(record: IndexedMessageRecord) -> CleanupReadState:
    if "UNREAD" in record.label_ids:
        return CleanupReadState.UNREAD
    return CleanupReadState.READ


def _policy_reasons(value: EffectiveMessage) -> tuple[CleanupExclusionReason, ...]:
    try:
        reasons = tuple(CleanupExclusionReason(reason.value) for reason in value.protection_reasons)
    except (AttributeError, ValueError):
        raise _study_unavailable() from None
    if (value.protected or value.review_required or value.hard_excluded) and not reasons:
        raise _study_unavailable()
    if not (value.protected or value.review_required or value.hard_excluded) and reasons:
        raise _study_unavailable()
    return reasons


def _ordered_reasons(
    values: set[CleanupExclusionReason],
) -> tuple[CleanupExclusionReason, ...]:
    return tuple(sorted(values, key=_REASON_RANK.__getitem__))


def _base_reasons(
    record: IndexedMessageRecord,
    effective: EffectiveMessage,
    selection: CleanupPlanSelection,
) -> tuple[CleanupExclusionReason, ...]:
    reasons = set(_policy_reasons(effective))
    lower = selection.temporal_filter.resolved_on_or_after_utc
    upper = selection.temporal_filter.resolved_before_utc
    if (lower is not None and record.received_at < lower) or (
        upper is not None and record.received_at >= upper
    ):
        reasons.add(CleanupExclusionReason.OUTSIDE_DATE)
    current_read_state = _record_read_state(record)
    if (
        selection.read_state is not CleanupReadState.ANY
        and current_read_state is not selection.read_state
    ):
        reasons.add(CleanupExclusionReason.READ_STATE_MISMATCH)
    excluded_provider_labels = {
        item.provider_label_id for item in selection.excluded_label_snapshots
    }
    if any(label_id in excluded_provider_labels for label_id in record.label_ids):
        reasons.add(CleanupExclusionReason.EXCLUDED_LABEL)
    return _ordered_reasons(reasons)


def _quota_allowed(
    universe: set[str],
    index: _CompositionIndex,
    selection: CleanupPlanSelection,
) -> set[str]:
    if selection.keep_latest_per_flow == 0:
        return {
            provider_message_id
            for provider_message_id in universe
            if not _base_reasons(
                index.records_by_provider_id[provider_message_id],
                index.effective_by_provider_id[provider_message_id],
                selection,
            )
        }
    candidates_by_flow: dict[str, list[IndexedMessageRecord]] = {}
    for provider_message_id in universe:
        record = index.records_by_provider_id[provider_message_id]
        effective = index.effective_by_provider_id[provider_message_id]
        if _base_reasons(record, effective, selection):
            continue
        candidates_by_flow.setdefault(effective.effective_flow_id, []).append(record)
    allowed: set[str] = set()
    for records in candidates_by_flow.values():
        ordered = sorted(records, key=lambda item: item.provider_message_id)
        ordered.sort(key=lambda item: item.received_at, reverse=True)
        allowed.update(
            item.provider_message_id for item in ordered[: selection.keep_latest_per_flow]
        )
    return allowed


def _member(
    record: IndexedMessageRecord,
    effective: EffectiveMessage,
    reasons: tuple[CleanupExclusionReason, ...],
    account_key: str,
) -> CleanupPlanMember:
    return CleanupPlanMember(
        provider_message_id=record.provider_message_id,
        message_id=local_message_id(account_key, record.provider_message_id),
        initial_state=(
            CleanupMemberInitialState.EXCLUDED if reasons else CleanupMemberInitialState.SELECTED
        ),
        received_at=record.received_at,
        size_estimate_bytes=record.size_estimate_bytes,
        source_id=effective.effective_source_id,
        flow_id=effective.effective_flow_id,
        read_state=_record_read_state(record),
        reason_codes=reasons,
    )


def _sample(
    *,
    kind: CleanupSampleKind,
    position: int,
    member: CleanupPlanMember,
    record: IndexedMessageRecord,
) -> CleanupPlanSample:
    return CleanupPlanSample(
        kind=kind,
        position=position,
        message_id=member.message_id,
        received_at=member.received_at,
        sender_name=record.sender_name,
        sender_address=record.sender_address,
        subject=record.subject,
        size_estimate_bytes=member.size_estimate_bytes,
        source_id=member.source_id,
        flow_id=member.flow_id,
        read_state=member.read_state,
        exclusion_reasons=member.reason_codes,
    )


def _samples(
    members: tuple[CleanupPlanMember, ...],
    index: _CompositionIndex,
) -> tuple[CleanupPlanSample, ...]:
    selected = sorted(
        (item for item in members if item.initial_state is CleanupMemberInitialState.SELECTED),
        key=lambda item: item.message_id,
    )
    selected.sort(key=lambda item: item.received_at, reverse=True)
    selected = selected[:MAX_INCLUDED_SAMPLES]
    excluded = sorted(
        (item for item in members if item.initial_state is CleanupMemberInitialState.EXCLUDED),
        key=lambda item: item.message_id,
    )
    excluded.sort(key=lambda item: item.received_at, reverse=True)
    excluded = excluded[:MAX_EXCLUDED_SAMPLES]
    values = [
        _sample(
            kind=CleanupSampleKind.INCLUDED,
            position=position,
            member=member,
            record=index.records_by_provider_id[member.provider_message_id],
        )
        for position, member in enumerate(selected)
    ]
    values.extend(
        _sample(
            kind=CleanupSampleKind.EXCLUDED,
            position=position,
            member=member,
            record=index.records_by_provider_id[member.provider_message_id],
        )
        for position, member in enumerate(excluded)
    )
    return tuple(values)


def _validate_aggregate_sizes(members: tuple[CleanupPlanMember, ...]) -> None:
    selected = sum(
        item.size_estimate_bytes
        for item in members
        if item.initial_state is CleanupMemberInitialState.SELECTED
    )
    excluded = sum(
        item.size_estimate_bytes
        for item in members
        if item.initial_state is CleanupMemberInitialState.EXCLUDED
    )
    if (
        selected > MAX_AGGREGATE_SIZE_ESTIMATE_BYTES
        or excluded > MAX_AGGREGATE_SIZE_ESTIMATE_BYTES
        or selected + excluded > MAX_AGGREGATE_SIZE_ESTIMATE_BYTES
    ):
        raise _study_unavailable()


def prepare_cleanup_plan_creation(
    composition: CleanupPlanCompositionLike,
    command: CreateCleanupPlanCommand,
    *,
    plan_id: str,
    command_now: datetime,
    input_revision: str,
) -> PreparedCleanupPlanCreation:
    if not isinstance(command, CreateCleanupPlanCommand):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    now = _utc(command_now)
    index = _index_composition(composition)
    if command.expected_map_revision != index.projection.map_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.MAP_REVISION_CONFLICT)
    if command.expected_policy_revision != index.projection.policy_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.POLICY_REVISION_CONFLICT)

    catalog_by_id = _catalog_by_id(composition)
    target_snapshots: list[CleanupTargetSnapshot] = []
    for target in command.targets:
        item = catalog_by_id.get(target.target_id)
        if item is None:
            raise CleanupPlanError(CleanupPlanErrorCode.TARGET_NOT_FOUND)
        if item.kind is not target.kind or isinstance(item, LabelCatalogItem):
            raise CleanupPlanError(CleanupPlanErrorCode.UNSUPPORTED_TARGET)
        target_snapshots.append(_target_snapshot(item))
    label_snapshots: list[CleanupLabelSnapshot] = []
    for label_id in command.excluded_label_ids:
        item = catalog_by_id.get(label_id)
        if not isinstance(item, LabelCatalogItem):
            raise CleanupPlanError(CleanupPlanErrorCode.UNSUPPORTED_TARGET)
        label_snapshots.append(
            CleanupLabelSnapshot(
                label_id=item.target_id,
                display_name=item.display_name,
                provider_label_id=item.provider_label_id,
            )
        )

    universe = _target_universe(
        command.targets,
        index,
        catalog_by_id,
        allow_missing_sender=False,
    )
    if not universe:
        raise CleanupPlanError(CleanupPlanErrorCode.TARGET_NOT_FOUND)
    selection = CleanupPlanSelection(
        disposition=command.disposition,
        targets=command.targets,
        target_snapshots=tuple(target_snapshots),
        temporal_filter=resolve_temporal_filter(command.temporal_filter, now),
        read_state=command.read_state,
        excluded_label_ids=command.excluded_label_ids,
        excluded_label_snapshots=tuple(label_snapshots),
        keep_latest_per_flow=command.keep_latest_per_flow,
    )
    quota_allowed = _quota_allowed(universe, index, selection)
    members: list[CleanupPlanMember] = []
    for provider_message_id in universe:
        record = index.records_by_provider_id[provider_message_id]
        effective = index.effective_by_provider_id[provider_message_id]
        reasons = set(_base_reasons(record, effective, selection))
        if not reasons and provider_message_id not in quota_allowed:
            reasons.add(CleanupExclusionReason.KEEP_LATEST)
        members.append(
            _member(
                record,
                effective,
                _ordered_reasons(reasons),
                index.account_key,
            )
        )
    frozen_members = tuple(sorted(members, key=lambda item: item.message_id))
    _validate_aggregate_sizes(frozen_members)
    selected_count = sum(
        item.initial_state is CleanupMemberInitialState.SELECTED for item in frozen_members
    )
    initial_state = CleanupPlanState.FROZEN if selected_count else CleanupPlanState.INVALIDATED
    event = CleanupPlanEvent(
        revision=1,
        type=CleanupEventType.CREATED,
        recorded_at=now,
        state=initial_state,
        observed_map_revision=index.projection.map_revision,
        observed_policy_revision=index.projection.policy_revision,
        removed_count=0,
        remaining_count=selected_count,
    )
    try:
        plan = PersistedCleanupPlan(
            account_key=index.account_key,
            plan_id=plan_id,
            selection=selection,
            created_from_input_revision=input_revision,
            created_from_map_revision=index.projection.map_revision,
            created_from_policy_revision=index.projection.policy_revision,
            created_at=now,
            expires_at=now + timedelta(seconds=CLEANUP_PLAN_VALIDITY_SECONDS),
            members=frozen_members,
            samples=_samples(frozen_members, index),
            events=(event,),
        )
    except CleanupPlanError:
        raise
    except (TypeError, ValueError):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST) from None
    receipt = CleanupPlanReceipt(
        command_id=command.command_id,
        request_fingerprint=cleanup_command_fingerprint(command),
        status=CleanupCommandStatus.CREATED,
        replayed=False,
        command_revision=1,
        plan_id=plan.plan_id,
    )
    return PreparedCleanupPlanCreation(plan=plan, receipt=receipt)


def effective_plan_state(
    plan: PersistedCleanupPlan,
    command_now: datetime,
) -> CleanupPlanState:
    if not isinstance(plan, PersistedCleanupPlan):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    now = _utc(command_now)
    if plan.persisted_state in (
        CleanupPlanState.CANCELLED,
        CleanupPlanState.INVALIDATED,
    ):
        return plan.persisted_state
    if now >= plan.expires_at:
        return CleanupPlanState.EXPIRED
    return plan.persisted_state


def _structural_targets_are_current(
    plan: PersistedCleanupPlan,
    catalog_by_id: dict[str, CleanupTargetCatalogItem],
) -> bool:
    for snapshot in plan.selection.target_snapshots:
        if isinstance(snapshot, SourceTargetSnapshot):
            current = catalog_by_id.get(snapshot.target_id)
            if not isinstance(current, SourceCatalogItem) or (
                current.selector_fingerprint != snapshot.selector_fingerprint
            ):
                return False
        elif isinstance(snapshot, FlowTargetSnapshot):
            current = catalog_by_id.get(snapshot.target_id)
            if not isinstance(current, FlowCatalogItem) or (
                current.selector_fingerprint != snapshot.selector_fingerprint
            ):
                return False
    return True


def prepare_cleanup_plan_revalidation(
    composition: CleanupPlanCompositionLike,
    plan: PersistedCleanupPlan,
    command: RevalidateCleanupPlanCommand,
    *,
    command_now: datetime,
) -> PreparedCleanupPlanRevalidation:
    if not isinstance(plan, PersistedCleanupPlan) or not isinstance(
        command, RevalidateCleanupPlanCommand
    ):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    now = _utc(command_now)
    state = effective_plan_state(plan, now)
    if state is CleanupPlanState.EXPIRED:
        raise CleanupPlanError(CleanupPlanErrorCode.PLAN_EXPIRED)
    if state in (CleanupPlanState.CANCELLED, CleanupPlanState.INVALIDATED):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_TRANSITION)
    if command.expected_plan_revision != plan.plan_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.PLAN_REVISION_CONFLICT)

    index = _index_composition(composition)
    if index.account_key != plan.account_key:
        raise CleanupPlanError(CleanupPlanErrorCode.ACCOUNT_UNAVAILABLE)
    if command.expected_map_revision != index.projection.map_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.MAP_REVISION_CONFLICT)
    if command.expected_policy_revision != index.projection.policy_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.POLICY_REVISION_CONFLICT)
    catalog_by_id = _catalog_by_id(composition)
    structural_targets_current = _structural_targets_are_current(plan, catalog_by_id)
    if structural_targets_current:
        universe = _target_universe(
            plan.selection.targets,
            index,
            catalog_by_id,
            allow_missing_sender=True,
        )
        quota_allowed = _quota_allowed(universe, index, plan.selection)
    else:
        universe = set()
        quota_allowed = set()

    already_removed = {item.message_id for item in plan.removals}
    still_eligible = tuple(
        item
        for item in plan.members
        if item.initial_state is CleanupMemberInitialState.SELECTED
        and item.message_id not in already_removed
    )
    revision = plan.plan_revision + 1
    new_removals: list[CleanupPlanMemberRemoval] = []
    for member in still_eligible:
        reasons: set[CleanupExclusionReason] = set()
        if not structural_targets_current:
            reasons.add(CleanupExclusionReason.SCOPE_CHANGED)
        else:
            record = index.records_by_provider_id.get(member.provider_message_id)
            if record is None:
                reasons = {CleanupExclusionReason.MISSING_AFTER_CREATION}
            else:
                effective = index.effective_by_provider_id[member.provider_message_id]
                if member.provider_message_id not in universe:
                    reasons.add(CleanupExclusionReason.SCOPE_CHANGED)
                base_reasons = set(_base_reasons(record, effective, plan.selection))
                protection_reasons = set(_policy_reasons(effective))
                if protection_reasons:
                    base_reasons.add(CleanupExclusionReason.PROTECTION_CHANGED)
                reasons.update(base_reasons)
                if not reasons and member.provider_message_id not in quota_allowed:
                    reasons.add(CleanupExclusionReason.KEEP_LATEST)
        if reasons:
            new_removals.append(
                CleanupPlanMemberRemoval(
                    provider_message_id=member.provider_message_id,
                    message_id=member.message_id,
                    revision=revision,
                    recorded_at=now,
                    reason_codes=_ordered_reasons(reasons),
                )
            )

    remaining_count = len(still_eligible) - len(new_removals)
    if not new_removals:
        event_type = CleanupEventType.REVALIDATED
        next_state = plan.persisted_state
    elif remaining_count:
        event_type = CleanupEventType.REDUCED
        next_state = CleanupPlanState.REDUCED
    else:
        event_type = CleanupEventType.INVALIDATED
        next_state = CleanupPlanState.INVALIDATED
    event = CleanupPlanEvent(
        revision=revision,
        type=event_type,
        recorded_at=now,
        state=next_state,
        observed_map_revision=index.projection.map_revision,
        observed_policy_revision=index.projection.policy_revision,
        removed_count=len(new_removals),
        remaining_count=remaining_count,
    )
    updated = replace(
        plan,
        events=plan.events + (event,),
        removals=plan.removals + tuple(new_removals),
    )
    receipt = CleanupPlanReceipt(
        command_id=command.command_id,
        request_fingerprint=cleanup_command_fingerprint(command, plan_id=plan.plan_id),
        status=CleanupCommandStatus.REVALIDATED,
        replayed=False,
        command_revision=revision,
        plan_id=plan.plan_id,
        removed_count=len(new_removals),
    )
    return PreparedCleanupPlanRevalidation(
        plan=updated,
        event=event,
        removals=tuple(new_removals),
        receipt=receipt,
    )


def prepare_cleanup_plan_cancellation(
    plan: PersistedCleanupPlan,
    command: CancelCleanupPlanCommand,
    *,
    command_now: datetime,
) -> PreparedCleanupPlanCancellation:
    if not isinstance(plan, PersistedCleanupPlan) or not isinstance(
        command, CancelCleanupPlanCommand
    ):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    now = _utc(command_now)
    state = effective_plan_state(plan, now)
    if state is CleanupPlanState.EXPIRED:
        raise CleanupPlanError(CleanupPlanErrorCode.PLAN_EXPIRED)
    if state in (CleanupPlanState.CANCELLED, CleanupPlanState.INVALIDATED):
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_TRANSITION)
    if command.expected_plan_revision != plan.plan_revision:
        raise CleanupPlanError(CleanupPlanErrorCode.PLAN_REVISION_CONFLICT)
    revision = plan.plan_revision + 1
    event = CleanupPlanEvent(
        revision=revision,
        type=CleanupEventType.CANCELLED,
        recorded_at=now,
        state=CleanupPlanState.CANCELLED,
        observed_map_revision=None,
        observed_policy_revision=None,
        removed_count=0,
        remaining_count=plan.current_eligible_count,
    )
    updated = replace(plan, events=plan.events + (event,))
    receipt = CleanupPlanReceipt(
        command_id=command.command_id,
        request_fingerprint=cleanup_command_fingerprint(command, plan_id=plan.plan_id),
        status=CleanupCommandStatus.CANCELLED,
        replayed=False,
        command_revision=revision,
        plan_id=plan.plan_id,
    )
    return PreparedCleanupPlanCancellation(plan=updated, event=event, receipt=receipt)


def cleanup_member_current_state(
    plan: PersistedCleanupPlan,
    member: CleanupPlanMember,
) -> CleanupMemberCurrentState:
    if member not in plan.members:
        raise CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    if member.initial_state is CleanupMemberInitialState.EXCLUDED:
        return CleanupMemberCurrentState.EXCLUDED
    if any(item.message_id == member.message_id for item in plan.removals):
        return CleanupMemberCurrentState.REMOVED
    return CleanupMemberCurrentState.ELIGIBLE


def cleanup_member_reason_codes(
    plan: PersistedCleanupPlan,
    member: CleanupPlanMember,
) -> tuple[CleanupExclusionReason, ...]:
    state = cleanup_member_current_state(plan, member)
    if state is CleanupMemberCurrentState.EXCLUDED:
        return member.reason_codes
    if state is CleanupMemberCurrentState.REMOVED:
        removal = next(item for item in plan.removals if item.message_id == member.message_id)
        return removal.reason_codes
    return ()
