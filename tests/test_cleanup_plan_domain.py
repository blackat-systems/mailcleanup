from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache

import pytest

import mailmap.cleanup_plan_domain as cleanup_domain
from mailmap.classification_model import FlowAnchorKind, SourceAnchorKind
from mailmap.cleanup_plan_domain import (
    build_cleanup_target_catalog,
    canonical_sender_address_v1,
    cleanup_command_fingerprint,
    cleanup_member_current_state,
    cleanup_member_reason_codes,
    effective_plan_state,
    label_target_id_v1,
    prepare_cleanup_plan_cancellation,
    prepare_cleanup_plan_creation,
    prepare_cleanup_plan_revalidation,
    resolve_temporal_filter,
    sender_target_id_v1,
)
from mailmap.cleanup_plan_model import (
    CLEANUP_PLAN_CONTRACT_VERSION,
    MAX_AGGREGATE_SIZE_ESTIMATE_BYTES,
    MAX_CONSIDERED_MESSAGES,
    MAX_MESSAGE_SIZE_ESTIMATE_BYTES,
    AllTemporalFilter,
    BeforeDateTemporalFilter,
    CancelCleanupPlanCommand,
    CleanupCommandStatus,
    CleanupDisposition,
    CleanupEventType,
    CleanupExclusionReason,
    CleanupMemberCurrentState,
    CleanupMemberInitialState,
    CleanupPlanError,
    CleanupPlanErrorCode,
    CleanupPlanEvent,
    CleanupPlanMemberRemoval,
    CleanupPlanSample,
    CleanupPlanState,
    CleanupReadState,
    CleanupSampleKind,
    CleanupStorageEffect,
    CleanupTarget,
    CleanupTargetCatalogItem,
    CleanupTargetKind,
    CleanupTemporalFilter,
    CreateCleanupPlanCommand,
    DateRangeTemporalFilter,
    FlowCatalogItem,
    LabelCatalogItem,
    OlderThanDaysTemporalFilter,
    PersistedCleanupPlan,
    PreparedCleanupPlanCreation,
    RevalidateCleanupPlanCommand,
    SenderCatalogItem,
    SourceCatalogItem,
    cleanup_target_sort_key,
)
from mailmap.index_model import IndexedMessageRecord
from mailmap.map_composition import MapCompositionResult, compose_map
from mailmap.map_fixtures import SyntheticMapFixture, canonical_synthetic_map_fixture
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SYNTHETIC_MAP_FIXTURE_VERSION,
)
from mailmap.model import Proteccion
from mailmap.policy_model import PolicyProtectionReason
from mailmap.repository import MapInputSnapshot

_NOW = datetime(2026, 8, 29, 15, 30, tzinfo=UTC)
_INPUT_A = "input-v1-" + ("a" * 64)
_INPUT_B = "input-v1-" + ("b" * 64)
_INPUT_C = "input-v1-" + ("c" * 64)
_PLAN_A = "cleanup-plan-v1-30000000-0000-4000-8000-000000000001"
_PLAN_B = "cleanup-plan-v1-30000000-0000-4000-8000-000000000002"
_CREATE_COMMAND_ID = "40000000-0000-4000-8000-000000000001"
_REVALIDATE_COMMAND_ID = "40000000-0000-4000-8000-000000000002"
_CANCEL_COMMAND_ID = "40000000-0000-4000-8000-000000000003"
_REVALIDATE_COMMAND_ID_2 = "40000000-0000-4000-8000-000000000004"
_RECORD_START = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


@lru_cache(maxsize=1)
def _fixture() -> SyntheticMapFixture:
    return canonical_synthetic_map_fixture()


def _composition(
    records: tuple[IndexedMessageRecord, ...] | None = None,
    *,
    input_revision: str = _INPUT_A,
) -> MapCompositionResult:
    fixture = _fixture()
    selected_records = fixture.records if records is None else records
    snapshot = MapInputSnapshot(
        account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
        account_exists=True,
        indexed_account_keys=(SYNTHETIC_MAP_ACCOUNT_KEY,),
        fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
        records=selected_records,
        checkpoint=replace(fixture.checkpoint, processed_count=len(selected_records)),
        policy_history=(),
        active_policies=(),
        policy_revision=0,
        input_revision=input_revision,
    )
    return compose_map(snapshot)


@lru_cache(maxsize=1)
def _ordinary_template() -> IndexedMessageRecord:
    composition = _composition()
    classified_messages = {
        message.provider_message_id: message for message in composition.classification.messages
    }
    sources = {source.source_id: source for source in composition.classification.sources}
    flows = {flow.flow_id: flow for flow in composition.classification.flows}
    ordinary_ids = set()
    for message in composition.effective.messages:
        classified = classified_messages[message.provider_message_id]
        if (
            not message.protected
            and not message.review_required
            and not message.hard_excluded
            and not message.protection_reasons
            and sources[classified.source_id].identity_descriptor.kind is SourceAnchorKind.SENDERS
            and flows[classified.flow_id].identity_descriptor.kind
            is not FlowAnchorKind.ISOLATED_MESSAGE
        ):
            ordinary_ids.add(message.provider_message_id)
    candidates = tuple(
        record
        for record in composition.records
        if record.provider_message_id in ordinary_ids
        and record.sender_address is not None
        and record.authenticated_domain is not None
    )
    assert candidates, "the canonical synthetic fixture must expose an ordinary sender"
    return candidates[0]


def _ordinary_records(
    count: int,
    *,
    labels: tuple[tuple[str, ...], ...] | None = None,
    sizes: tuple[int, ...] | None = None,
    start: datetime = _RECORD_START,
) -> tuple[IndexedMessageRecord, ...]:
    template = _ordinary_template()
    selected_labels = labels or tuple(("INBOX",) for _ in range(count))
    selected_sizes = sizes or tuple(1_000 + index for index in range(count))
    assert len(selected_labels) == count
    assert len(selected_sizes) == count
    return tuple(
        replace(
            template,
            provider_message_id=f"synthetic-domain-message-{index:06d}",
            provider_thread_id=f"synthetic-domain-thread-{index:06d}",
            received_at=start + timedelta(minutes=index),
            label_ids=selected_labels[index],
            size_estimate_bytes=selected_sizes[index],
        )
        for index in range(count)
    )


def _target(item: CleanupTargetCatalogItem) -> CleanupTarget:
    return CleanupTarget(kind=item.kind, target_id=item.target_id)


def _source_item(composition: MapCompositionResult) -> SourceCatalogItem:
    values = tuple(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, SourceCatalogItem)
    )
    assert values
    return values[0]


def _source_and_flow(
    composition: MapCompositionResult,
) -> tuple[SourceCatalogItem, FlowCatalogItem]:
    catalog = build_cleanup_target_catalog(composition)
    sources = tuple(item for item in catalog if isinstance(item, SourceCatalogItem))
    assert len(sources) == 1
    flows = tuple(
        item
        for item in catalog
        if isinstance(item, FlowCatalogItem) and item.source_id == sources[0].target_id
    )
    assert len(flows) == 1
    return sources[0], flows[0]


def _create_command(
    composition: MapCompositionResult,
    *,
    targets: tuple[CleanupTarget, ...] | None = None,
    temporal_filter: CleanupTemporalFilter | None = None,
    read_state: CleanupReadState = CleanupReadState.ANY,
    excluded_label_ids: tuple[str, ...] = (),
    keep_latest_per_flow: int = 0,
    disposition: CleanupDisposition = CleanupDisposition.ARCHIVE,
    command_id: str = _CREATE_COMMAND_ID,
) -> CreateCleanupPlanCommand:
    selected_targets = targets or (_target(_source_item(composition)),)
    return CreateCleanupPlanCommand(
        command_id=command_id,
        expected_map_revision=composition.projection.map_revision,
        expected_policy_revision=composition.projection.policy_revision,
        disposition=disposition,
        targets=tuple(sorted(selected_targets, key=cleanup_target_sort_key)),
        temporal_filter=temporal_filter or AllTemporalFilter(),
        read_state=read_state,
        excluded_label_ids=tuple(sorted(excluded_label_ids)),
        keep_latest_per_flow=keep_latest_per_flow,
    )


def _create_plan(
    composition: MapCompositionResult,
    *,
    command: CreateCleanupPlanCommand | None = None,
    plan_id: str = _PLAN_A,
    command_now: datetime = _NOW,
    input_revision: str = _INPUT_A,
) -> PreparedCleanupPlanCreation:
    return prepare_cleanup_plan_creation(
        composition,
        command or _create_command(composition),
        plan_id=plan_id,
        command_now=command_now,
        input_revision=input_revision,
    )


def _revalidation_command(
    plan: PersistedCleanupPlan,
    composition: MapCompositionResult,
    *,
    command_id: str = _REVALIDATE_COMMAND_ID,
) -> RevalidateCleanupPlanCommand:
    return RevalidateCleanupPlanCommand(
        command_id=command_id,
        expected_plan_revision=plan.plan_revision,
        expected_map_revision=composition.projection.map_revision,
        expected_policy_revision=composition.projection.policy_revision,
    )


def _selected_provider_ids(plan: PersistedCleanupPlan) -> set[str]:
    return {
        member.provider_message_id
        for member in plan.members
        if member.initial_state is CleanupMemberInitialState.SELECTED
    }


def _eligible_provider_ids(plan: PersistedCleanupPlan) -> set[str]:
    return {
        member.provider_message_id
        for member in plan.members
        if cleanup_member_current_state(plan, member) is CleanupMemberCurrentState.ELIGIBLE
    }


def _assert_domain_error(
    expected: CleanupPlanErrorCode,
    action: object,
) -> None:
    assert callable(action)
    with pytest.raises(CleanupPlanError) as raised:
        action()
    assert raised.value.code is expected


def test_models_are_closed_immutable_versioned_and_redacted() -> None:
    composition = _composition()
    command = _create_command(composition)
    prepared = _create_plan(composition, command=command)
    plan = prepared.plan
    sample = plan.samples[0]

    assert command.version == CLEANUP_PLAN_CONTRACT_VERSION
    assert plan.version == 1
    assert sample.version == 1
    assert not hasattr(command, "__dict__")
    assert not hasattr(plan, "__dict__")
    assert not hasattr(sample, "__dict__")
    with pytest.raises(FrozenInstanceError):
        command.keep_latest_per_flow = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.events = ()  # type: ignore[misc]

    command_repr = repr(command)
    assert command.command_id not in command_repr
    assert command.expected_map_revision not in command_repr
    assert all(target.target_id not in command_repr for target in command.targets)
    plan_repr = repr(plan)
    assert plan.account_key not in plan_repr
    assert plan.plan_id not in plan_repr
    sample_repr = repr(sample)
    assert sample.message_id not in sample_repr
    for metadata in (sample.sender_name, sample.sender_address, sample.subject):
        if metadata:
            assert metadata not in sample_repr

    error = CleanupPlanError(CleanupPlanErrorCode.INVALID_REQUEST)
    assert not hasattr(error, "__dict__")
    with pytest.raises(AttributeError):
        error.code = CleanupPlanErrorCode.INTERNAL_ERROR  # type: ignore[misc]
    with pytest.raises(ValueError):
        AllTemporalFilter(version=2)
    with pytest.raises(ValueError):
        CleanupDisposition("unsubscribe")


def test_model_invariants_reject_terminal_revival_and_invalid_reason_contexts() -> None:
    plan = _create_plan(_composition(_ordinary_records(2))).plan
    cancelled = prepare_cleanup_plan_cancellation(
        plan,
        CancelCleanupPlanCommand(
            command_id=_CANCEL_COMMAND_ID,
            expected_plan_revision=plan.plan_revision,
        ),
        command_now=_NOW + timedelta(minutes=1),
    ).plan
    revived = CleanupPlanEvent(
        revision=3,
        type=CleanupEventType.REVALIDATED,
        recorded_at=_NOW + timedelta(minutes=2),
        state=CleanupPlanState.FROZEN,
        observed_map_revision=plan.created_from_map_revision,
        observed_policy_revision=plan.created_from_policy_revision,
        removed_count=0,
        remaining_count=plan.current_eligible_count,
    )
    with pytest.raises(ValueError, match="terminal plan states cannot be revived"):
        replace(cancelled, events=cancelled.events + (revived,))
    created_event = plan.events[0]
    with pytest.raises(ValueError, match="created event must match"):
        replace(
            plan,
            events=(
                replace(
                    created_event,
                    recorded_at=plan.created_at + timedelta(microseconds=1),
                ),
            ),
        )
    different_map_revision = "map-v1-" + ("0" * 64)
    if different_map_revision == plan.created_from_map_revision:
        different_map_revision = "map-v1-" + ("1" * 64)
    with pytest.raises(ValueError, match="created event must match"):
        replace(
            plan,
            events=(
                replace(
                    created_event,
                    observed_map_revision=different_map_revision,
                ),
            ),
        )
    event_at_expiry = CleanupPlanEvent(
        revision=2,
        type=CleanupEventType.REVALIDATED,
        recorded_at=plan.expires_at,
        state=CleanupPlanState.FROZEN,
        observed_map_revision=plan.created_from_map_revision,
        observed_policy_revision=plan.created_from_policy_revision,
        removed_count=0,
        remaining_count=plan.current_eligible_count,
    )
    with pytest.raises(ValueError, match="events must occur during plan validity"):
        replace(plan, events=plan.events + (event_at_expiry,))

    selected = next(
        member
        for member in plan.members
        if member.initial_state is CleanupMemberInitialState.SELECTED
    )
    with pytest.raises(ValueError, match="creation members cannot contain"):
        replace(
            selected,
            initial_state=CleanupMemberInitialState.EXCLUDED,
            reason_codes=(CleanupExclusionReason.MISSING_AFTER_CREATION,),
        )
    removal_fields = {
        "provider_message_id": selected.provider_message_id,
        "message_id": selected.message_id,
        "revision": 2,
        "recorded_at": _NOW + timedelta(minutes=1),
    }
    with pytest.raises(ValueError, match="missing_after_creation must be the only"):
        CleanupPlanMemberRemoval(
            **removal_fields,
            reason_codes=(
                CleanupExclusionReason.MISSING_AFTER_CREATION,
                CleanupExclusionReason.SCOPE_CHANGED,
            ),
        )
    with pytest.raises(ValueError, match="must occur together"):
        CleanupPlanMemberRemoval(
            **removal_fields,
            reason_codes=(CleanupExclusionReason.PROTECTION_CHANGED,),
        )
    with pytest.raises(ValueError, match="must occur together"):
        CleanupPlanMemberRemoval(
            **removal_fields,
            reason_codes=(CleanupExclusionReason.STARRED,),
        )


def test_persisted_selection_reimposes_target_bounds_uniqueness_and_order() -> None:
    composition = _composition(_ordinary_records(1))
    plan = _create_plan(composition).plan
    selection = plan.selection
    snapshot = selection.target_snapshots[0]

    with pytest.raises(ValueError, match="between one and 100"):
        replace(selection, targets=(), target_snapshots=())
    with pytest.raises(ValueError, match="must not contain duplicates"):
        replace(
            selection,
            targets=(selection.targets[0], selection.targets[0]),
            target_snapshots=(snapshot, snapshot),
        )

    target_low = CleanupTarget(
        kind=CleanupTargetKind.SOURCE,
        target_id="effective-source-v1-" + f"{1:024x}",
    )
    target_high = CleanupTarget(
        kind=CleanupTargetKind.SOURCE,
        target_id="effective-source-v1-" + f"{2:024x}",
    )
    snapshot_low = replace(snapshot, target_id=target_low.target_id)
    snapshot_high = replace(snapshot, target_id=target_high.target_id)
    with pytest.raises(ValueError, match="canonical order"):
        replace(
            selection,
            targets=(target_high, target_low),
            target_snapshots=(snapshot_high, snapshot_low),
        )

    targets = tuple(
        CleanupTarget(
            kind=CleanupTargetKind.SOURCE,
            target_id="effective-source-v1-" + f"{index:024x}",
        )
        for index in range(1, 102)
    )
    snapshots = tuple(replace(snapshot, target_id=target.target_id) for target in targets)
    with pytest.raises(ValueError, match="between one and 100"):
        replace(selection, targets=targets, target_snapshots=snapshots)

    label = next(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, LabelCatalogItem)
    )
    with pytest.raises(ValueError, match="label cannot be a cleanup target"):
        replace(
            selection,
            targets=(CleanupTarget(kind=label.kind, target_id=label.target_id),),
            target_snapshots=(snapshot,),
        )
    with pytest.raises(ValueError, match="snapshots must correspond"):
        replace(selection, target_snapshots=())


def test_persisted_selection_reimposes_excluded_label_bounds_uniqueness_and_order() -> None:
    composition = _composition(_ordinary_records(1))
    label = next(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, LabelCatalogItem)
    )
    command = _create_command(composition, excluded_label_ids=(label.target_id,))
    selection = _create_plan(composition, command=command).plan.selection
    snapshot = selection.excluded_label_snapshots[0]

    with pytest.raises(ValueError, match="must not contain duplicates"):
        replace(
            selection,
            excluded_label_ids=(label.target_id, label.target_id),
            excluded_label_snapshots=(snapshot, snapshot),
        )

    label_low = "label-v1-" + f"{1:064x}"
    label_high = "label-v1-" + f"{2:064x}"
    with pytest.raises(ValueError, match="canonical order"):
        replace(
            selection,
            excluded_label_ids=(label_high, label_low),
            excluded_label_snapshots=(
                replace(snapshot, label_id=label_high),
                replace(snapshot, label_id=label_low),
            ),
        )

    label_ids = tuple("label-v1-" + f"{index:064x}" for index in range(1, 102))
    label_snapshots = tuple(replace(snapshot, label_id=value) for value in label_ids)
    with pytest.raises(ValueError, match="cannot exceed 100"):
        replace(
            selection,
            excluded_label_ids=label_ids,
            excluded_label_snapshots=label_snapshots,
        )
    with pytest.raises(ValueError, match="snapshots must correspond"):
        replace(selection, excluded_label_snapshots=())


def test_persisted_plan_samples_must_reference_and_match_frozen_members() -> None:
    composition = _composition(_ordinary_records(3))
    command = _create_command(composition, keep_latest_per_flow=1)
    plan = _create_plan(composition, command=command).plan
    included = next(item for item in plan.samples if item.kind is CleanupSampleKind.INCLUDED)
    excluded_samples = tuple(
        item for item in plan.samples if item.kind is CleanupSampleKind.EXCLUDED
    )
    assert len(excluded_samples) == 2
    excluded = excluded_samples[0]

    with pytest.raises(ValueError, match="reference existing"):
        replace(
            plan,
            samples=(
                replace(included, message_id="message-v1-" + ("f" * 64)),
            ),
        )
    with pytest.raises(ValueError, match="kind must match"):
        replace(
            plan,
            samples=(
                replace(
                    included,
                    kind=CleanupSampleKind.EXCLUDED,
                    exclusion_reasons=(CleanupExclusionReason.KEEP_LATEST,),
                ),
            ),
        )
    with pytest.raises(ValueError, match="kind must match"):
        replace(
            plan,
            samples=(
                replace(
                    excluded,
                    kind=CleanupSampleKind.INCLUDED,
                    exclusion_reasons=(),
                ),
            ),
        )

    mismatches = (
        replace(included, received_at=included.received_at + timedelta(microseconds=1)),
        replace(included, size_estimate_bytes=included.size_estimate_bytes + 1),
        replace(included, source_id="effective-source-v1-" + ("f" * 24)),
        replace(included, flow_id="effective-flow-v1-" + ("f" * 24)),
        replace(
            included,
            read_state=(
                CleanupReadState.READ
                if included.read_state is CleanupReadState.UNREAD
                else CleanupReadState.UNREAD
            ),
        ),
        replace(
            excluded,
            exclusion_reasons=(CleanupExclusionReason.OUTSIDE_DATE,),
        ),
    )
    for sample in mismatches:
        with pytest.raises(ValueError, match="snapshot must match"):
            replace(plan, samples=(sample,))

    with pytest.raises(ValueError, match="must not duplicate"):
        replace(
            plan,
            samples=(excluded, replace(excluded, position=1)),
        )
    with pytest.raises(ValueError, match="canonical preview order"):
        replace(
            plan,
            samples=(
                replace(excluded_samples[1], position=0),
                replace(excluded_samples[0], position=1),
            ),
        )


def test_sender_canonicalization_and_local_ids_are_stable_and_opaque() -> None:
    composition = _composition()
    classified_messages = {
        item.provider_message_id: item for item in composition.classification.messages
    }
    descriptors = {
        item.source_id: item.identity_descriptor for item in composition.classification.sources
    }
    record = next(item for item in composition.records if item.sender_address is not None)
    descriptor = descriptors[classified_messages[record.provider_message_id].source_id]
    assert record.sender_address is not None
    normalized = record.sender_address.strip().casefold()
    variant = replace(record, sender_address=f"  {record.sender_address.upper()}  ")

    assert canonical_sender_address_v1(variant, descriptor) == normalized
    assert canonical_sender_address_v1(replace(record, sender_address=None), descriptor) is None
    wrong_descriptor = next(
        value for value in descriptors.values() if normalized not in value.sender_addresses
    )
    _assert_domain_error(
        CleanupPlanErrorCode.STUDY_UNAVAILABLE,
        lambda: canonical_sender_address_v1(record, wrong_descriptor),
    )

    expected_sender_digest = hashlib.sha256(
        ("mailcleanup.study.sender.v1\0" + SYNTHETIC_MAP_ACCOUNT_KEY + "\0" + normalized).encode(
            "utf-8"
        )
    ).hexdigest()
    assert sender_target_id_v1(SYNTHETIC_MAP_ACCOUNT_KEY, normalized) == (
        "sender-v1-" + expected_sender_digest
    )
    assert sender_target_id_v1("synthetic-map-v2", normalized) != sender_target_id_v1(
        SYNTHETIC_MAP_ACCOUNT_KEY, normalized
    )

    expected_label_digest = hashlib.sha256(
        ("mailcleanup.study.label.v1\0" + SYNTHETIC_MAP_ACCOUNT_KEY + "\0INBOX").encode("utf-8")
    ).hexdigest()
    assert label_target_id_v1(SYNTHETIC_MAP_ACCOUNT_KEY, "INBOX") == (
        "label-v1-" + expected_label_digest
    )


def test_sender_without_address_does_not_create_a_sender_target() -> None:
    record = replace(
        _ordinary_records(1)[0],
        sender_address=None,
        authenticated_domain=None,
        list_id=None,
        list_unsubscribe=None,
        list_unsubscribe_post=None,
        dkim_result=None,
        dmarc_result=None,
    )
    catalog = build_cleanup_target_catalog(_composition((record,)))
    assert not any(isinstance(item, SenderCatalogItem) for item in catalog)


def test_catalog_has_closed_allowlist_and_exact_total_order() -> None:
    record = replace(
        _ordinary_records(1)[0],
        label_ids=("CUSTOM_SYNTHETIC", "INBOX"),
    )
    catalog = build_cleanup_target_catalog(_composition((record,)))
    kind_rank = {
        CleanupTargetKind.SOURCE: 0,
        CleanupTargetKind.FLOW: 1,
        CleanupTargetKind.SENDER: 2,
        CleanupTargetKind.LABEL: 3,
    }

    def visible_text(item: CleanupTargetCatalogItem) -> str:
        if isinstance(item, SenderCatalogItem):
            return item.display_address
        return item.display_name

    assert tuple(
        (kind_rank[item.kind], visible_text(item).casefold(), item.target_id) for item in catalog
    ) == tuple(
        sorted(
            (
                kind_rank[item.kind],
                visible_text(item).casefold(),
                item.target_id,
            )
            for item in catalog
        )
    )
    label_items = tuple(item for item in catalog if isinstance(item, LabelCatalogItem))
    assert {item.provider_label_id for item in label_items} == {"INBOX"}
    assert "CUSTOM_SYNTHETIC" not in {item.provider_label_id for item in label_items}
    assert {item.kind for item in catalog} == {
        CleanupTargetKind.SOURCE,
        CleanupTargetKind.FLOW,
        CleanupTargetKind.SENDER,
        CleanupTargetKind.LABEL,
    }


def test_label_is_catalog_only_and_never_a_selectable_target() -> None:
    composition = _composition(_ordinary_records(1))
    label = next(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, LabelCatalogItem)
    )
    with pytest.raises(ValueError, match="label is not a selectable target"):
        _create_command(composition, targets=(_target(label),))

    unknown_label_id = label_target_id_v1(SYNTHETIC_MAP_ACCOUNT_KEY, "CUSTOM_SYNTHETIC")
    command = _create_command(composition, excluded_label_ids=(unknown_label_id,))
    _assert_domain_error(
        CleanupPlanErrorCode.UNSUPPORTED_TARGET,
        lambda: _create_plan(composition, command=command),
    )


@pytest.mark.parametrize(
    "kind",
    [CleanupTargetKind.SOURCE, CleanupTargetKind.FLOW, CleanupTargetKind.SENDER],
)
def test_source_flow_and_opaque_sender_targets_select_exact_members(
    kind: CleanupTargetKind,
) -> None:
    composition = _composition()
    item = next(value for value in build_cleanup_target_catalog(composition) if value.kind is kind)
    plan = _create_plan(
        composition,
        command=_create_command(composition, targets=(_target(item),)),
    ).plan
    assert len(plan.members) == item.message_count
    assert len({member.provider_message_id for member in plan.members}) == len(plan.members)


def test_overlapping_source_and_flow_targets_are_deduplicated() -> None:
    records = _ordinary_records(3)
    composition = _composition(records)
    source, flow = _source_and_flow(composition)
    command = _create_command(
        composition,
        targets=(_target(flow), _target(source)),
    )
    plan = _create_plan(composition, command=command).plan

    assert command.targets == tuple(sorted(command.targets, key=cleanup_target_sort_key))
    assert len(plan.members) == len(records)
    assert {member.provider_message_id for member in plan.members} == {
        record.provider_message_id for record in records
    }


@pytest.mark.parametrize(
    ("requested", "expected_lower", "expected_upper"),
    [
        (
            BeforeDateTemporalFilter(date=date(2026, 3, 1)),
            None,
            datetime(2026, 3, 1, 3, 0, tzinfo=UTC),
        ),
        (
            DateRangeTemporalFilter(
                on_or_after_date=date(2026, 2, 1),
                before_date=date(2026, 3, 1),
            ),
            datetime(2026, 2, 1, 3, 0, tzinfo=UTC),
            datetime(2026, 3, 1, 3, 0, tzinfo=UTC),
        ),
        (
            OlderThanDaysTemporalFilter(days=1),
            None,
            datetime(2025, 12, 30, 3, 0, tzinfo=UTC),
        ),
    ],
)
def test_temporal_filters_resolve_from_cordoba_civil_dates(
    requested: CleanupTemporalFilter,
    expected_lower: datetime | None,
    expected_upper: datetime | None,
) -> None:
    command_now = datetime(2026, 1, 1, 2, 30, tzinfo=UTC)
    resolved = resolve_temporal_filter(requested, command_now)
    assert resolved.time_zone == "America/Argentina/Cordoba"
    assert resolved.resolved_on_or_after_utc == expected_lower
    assert resolved.resolved_before_utc == expected_upper


def test_before_date_is_exclusive_at_cordoba_midnight() -> None:
    records = _ordinary_records(2)
    records = (
        replace(records[0], received_at=datetime(2026, 3, 1, 2, 59, 59, tzinfo=UTC)),
        replace(records[1], received_at=datetime(2026, 3, 1, 3, 0, tzinfo=UTC)),
    )
    composition = _composition(records)
    command = _create_command(
        composition,
        temporal_filter=BeforeDateTemporalFilter(date=date(2026, 3, 1)),
    )
    plan = _create_plan(composition, command=command).plan
    members = {item.provider_message_id: item for item in plan.members}

    assert members[records[0].provider_message_id].initial_state is (
        CleanupMemberInitialState.SELECTED
    )
    assert members[records[1].provider_message_id].reason_codes == (
        CleanupExclusionReason.OUTSIDE_DATE,
    )
    _assert_domain_error(
        CleanupPlanErrorCode.INVALID_FILTER,
        lambda: resolve_temporal_filter(AllTemporalFilter(), datetime(2026, 1, 1)),
    )


def test_read_state_uses_only_unread_and_excluded_labels_use_local_ids() -> None:
    records = _ordinary_records(
        3,
        labels=(
            ("CATEGORY_SOCIAL", "INBOX", "UNREAD"),
            ("CATEGORY_SOCIAL", "INBOX"),
            ("INBOX",),
        ),
    )
    composition = _composition(records)
    social = next(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, LabelCatalogItem) and item.provider_label_id == "CATEGORY_SOCIAL"
    )
    command = _create_command(
        composition,
        read_state=CleanupReadState.READ,
        excluded_label_ids=(social.target_id,),
    )
    plan = _create_plan(composition, command=command).plan
    members = {member.provider_message_id: member for member in plan.members}

    assert members[records[0].provider_message_id].reason_codes == (
        CleanupExclusionReason.READ_STATE_MISMATCH,
        CleanupExclusionReason.EXCLUDED_LABEL,
    )
    assert members[records[1].provider_message_id].reason_codes == (
        CleanupExclusionReason.EXCLUDED_LABEL,
    )
    assert members[records[2].provider_message_id].reason_codes == ()
    assert members[records[2].provider_message_id].read_state is CleanupReadState.READ


def test_reason_catalog_contains_exactly_21_values_in_contract_order() -> None:
    assert tuple(reason.value for reason in CleanupExclusionReason) == (
        "sent",
        "draft",
        "trash",
        "starred",
        "important",
        "protected_label",
        "security",
        "document",
        "personal",
        "low_confidence",
        "contradiction",
        "mixed_conversation",
        "manual_policy",
        "policy_review",
        "outside_date",
        "read_state_mismatch",
        "excluded_label",
        "keep_latest",
        "missing_after_creation",
        "scope_changed",
        "protection_changed",
    )


def test_all_14_policy_reasons_map_without_loss_to_cleanup_reasons() -> None:
    composition = _composition()
    base = next(item for item in composition.effective.messages if not item.protected)
    assert len(tuple(PolicyProtectionReason)) == 14

    for reason in PolicyProtectionReason:
        protected = replace(
            base,
            effective_protection=Proteccion.CRITICA,
            protected=True,
            review_required=False,
            hard_excluded=False,
            protection_reasons=(reason,),
        )
        assert cleanup_domain._policy_reasons(protected) == (CleanupExclusionReason(reason.value),)


def test_concurrent_exclusion_conditions_accumulate_deduplicate_and_order() -> None:
    record = _ordinary_records(
        1,
        labels=(("CATEGORY_SOCIAL", "INBOX", "STARRED", "UNREAD"),),
    )[0]
    composition = _composition((record,))
    social = next(
        item
        for item in build_cleanup_target_catalog(composition)
        if isinstance(item, LabelCatalogItem) and item.provider_label_id == "CATEGORY_SOCIAL"
    )
    command = _create_command(
        composition,
        temporal_filter=BeforeDateTemporalFilter(date=date(2020, 1, 1)),
        read_state=CleanupReadState.READ,
        excluded_label_ids=(social.target_id,),
    )
    member = _create_plan(composition, command=command).plan.members[0]

    assert member.reason_codes == (
        CleanupExclusionReason.STARRED,
        CleanupExclusionReason.OUTSIDE_DATE,
        CleanupExclusionReason.READ_STATE_MISMATCH,
        CleanupExclusionReason.EXCLUDED_LABEL,
    )


def test_keep_latest_zero_is_disabled() -> None:
    records = _ordinary_records(4)
    composition = _composition(records)
    plan = _create_plan(
        composition,
        command=_create_command(composition, keep_latest_per_flow=0),
    ).plan

    assert _selected_provider_ids(plan) == {record.provider_message_id for record in records}
    assert all(
        CleanupExclusionReason.KEEP_LATEST not in member.reason_codes for member in plan.members
    )


def test_protected_and_filter_failing_messages_do_not_consume_keep_latest_quota() -> None:
    records = _ordinary_records(
        4,
        labels=(
            ("INBOX",),
            ("INBOX",),
            ("INBOX", "UNREAD"),
            ("INBOX", "STARRED"),
        ),
    )
    composition = _composition(records)
    command = _create_command(
        composition,
        read_state=CleanupReadState.READ,
        keep_latest_per_flow=1,
    )
    plan = _create_plan(composition, command=command).plan
    members = {item.provider_message_id: item for item in plan.members}

    assert _selected_provider_ids(plan) == {records[1].provider_message_id}
    assert members[records[0].provider_message_id].reason_codes == (
        CleanupExclusionReason.KEEP_LATEST,
    )
    assert members[records[2].provider_message_id].reason_codes == (
        CleanupExclusionReason.READ_STATE_MISMATCH,
    )
    assert CleanupExclusionReason.STARRED in members[records[3].provider_message_id].reason_codes


def test_universe_limit_is_checked_before_any_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composition = _composition(_ordinary_records(1))
    existing_plan = _create_plan(
        composition,
        command=_create_command(composition, keep_latest_per_flow=1),
    ).plan
    index = cleanup_domain._index_composition(composition)
    catalog_by_id = cleanup_domain._catalog_by_id(composition)
    target = _target(_source_item(composition))

    def over_limit(*args: object, **kwargs: object) -> set[str]:
        return {f"synthetic-over-limit-{index:06d}" for index in range(MAX_CONSIDERED_MESSAGES + 1)}

    monkeypatch.setattr(cleanup_domain, "_provider_ids_for_target", over_limit)
    _assert_domain_error(
        CleanupPlanErrorCode.PLAN_TOO_LARGE,
        lambda: cleanup_domain._target_universe(
            (target,),
            index,
            catalog_by_id,
            allow_missing_sender=False,
        ),
    )
    _assert_domain_error(
        CleanupPlanErrorCode.PLAN_TOO_LARGE,
        lambda: _create_plan(
            composition,
            command=_create_command(
                composition,
                temporal_filter=BeforeDateTemporalFilter(date=date(1900, 1, 1)),
            ),
            plan_id=_PLAN_B,
        ),
    )
    _assert_domain_error(
        CleanupPlanErrorCode.PLAN_TOO_LARGE,
        lambda: prepare_cleanup_plan_revalidation(
            composition,
            existing_plan,
            _revalidation_command(existing_plan, composition),
            command_now=_NOW + timedelta(minutes=1),
        ),
    )


def test_empty_selection_is_persisted_but_absent_target_is_an_error() -> None:
    records = _ordinary_records(2)
    composition = _composition(records)
    empty_command = _create_command(
        composition,
        temporal_filter=BeforeDateTemporalFilter(date=date(1900, 1, 1)),
    )
    prepared = _create_plan(composition, command=empty_command)
    plan = prepared.plan

    assert prepared.receipt.status is CleanupCommandStatus.CREATED
    assert plan.persisted_state is CleanupPlanState.INVALIDATED
    assert plan.selected_at_creation_count == 0
    assert plan.selected_at_creation_size_estimate_bytes == 0
    assert plan.current_eligible_count == 0
    assert plan.excluded_at_creation_count == len(records)
    assert plan.events == (
        replace(
            plan.events[0],
            revision=1,
            type=CleanupEventType.CREATED,
            state=CleanupPlanState.INVALIDATED,
            removed_count=0,
            remaining_count=0,
        ),
    )

    missing_target = CleanupTarget(
        kind=CleanupTargetKind.SOURCE,
        target_id="effective-source-v1-" + ("0" * 24),
    )
    missing_command = _create_command(composition, targets=(missing_target,))
    _assert_domain_error(
        CleanupPlanErrorCode.TARGET_NOT_FOUND,
        lambda: _create_plan(composition, command=missing_command, plan_id=_PLAN_B),
    )


def test_sizes_and_samples_are_exact_bounded_and_deterministic() -> None:
    sizes = tuple(100 + index for index in range(12))
    labels = tuple(("INBOX", "STARRED") if index < 6 else ("INBOX",) for index in range(12))
    records = _ordinary_records(12, labels=labels, sizes=sizes)
    composition = _composition(records)
    plan = _create_plan(composition).plan

    assert plan.selected_at_creation_count == 6
    assert plan.excluded_at_creation_count == 6
    assert plan.selected_at_creation_size_estimate_bytes == sum(sizes[6:])
    assert plan.excluded_at_creation_size_estimate_bytes == sum(sizes[:6])
    assert plan.current_eligible_size_estimate_bytes == sum(sizes[6:])
    assert plan.effective_freed_bytes is None
    included = tuple(sample for sample in plan.samples if sample.kind is CleanupSampleKind.INCLUDED)
    excluded = tuple(sample for sample in plan.samples if sample.kind is CleanupSampleKind.EXCLUDED)
    assert len(included) == 5
    assert len(excluded) == 5
    assert tuple(item.position for item in included) == tuple(range(5))
    assert tuple(item.position for item in excluded) == tuple(range(5))

    selected_members = sorted(
        (
            member
            for member in plan.members
            if member.initial_state is CleanupMemberInitialState.SELECTED
        ),
        key=lambda member: (-member.received_at.timestamp(), member.message_id),
    )[:5]
    excluded_members = sorted(
        (
            member
            for member in plan.members
            if member.initial_state is CleanupMemberInitialState.EXCLUDED
        ),
        key=lambda member: (-member.received_at.timestamp(), member.message_id),
    )[:5]
    assert tuple(item.message_id for item in included) == tuple(
        item.message_id for item in selected_members
    )
    assert tuple(item.message_id for item in excluded) == tuple(
        item.message_id for item in excluded_members
    )
    assert set(CleanupPlanSample.__slots__) == {
        "kind",
        "position",
        "message_id",
        "received_at",
        "sender_name",
        "sender_address",
        "subject",
        "size_estimate_bytes",
        "source_id",
        "flow_id",
        "read_state",
        "exclusion_reasons",
        "version",
    }


def test_individual_size_ceiling_is_exact_and_overflow_is_rejected() -> None:
    at_limit = replace(
        _ordinary_records(1)[0],
        size_estimate_bytes=MAX_MESSAGE_SIZE_ESTIMATE_BYTES,
    )
    at_limit_composition = _composition((at_limit,))
    plan = _create_plan(at_limit_composition).plan
    assert plan.selected_at_creation_size_estimate_bytes == MAX_MESSAGE_SIZE_ESTIMATE_BYTES

    over_limit = replace(
        at_limit,
        size_estimate_bytes=MAX_MESSAGE_SIZE_ESTIMATE_BYTES + 1,
    )
    over_limit_composition = _composition((over_limit,), input_revision=_INPUT_B)
    _assert_domain_error(
        CleanupPlanErrorCode.STUDY_UNAVAILABLE,
        lambda: _create_plan(
            over_limit_composition,
            command=_create_command(over_limit_composition),
        ),
    )

    member = plan.members[0]
    at_aggregate_limit = (member,) * MAX_CONSIDERED_MESSAGES
    assert (
        sum(item.size_estimate_bytes for item in at_aggregate_limit)
        == MAX_AGGREGATE_SIZE_ESTIMATE_BYTES
    )
    cleanup_domain._validate_aggregate_sizes(at_aggregate_limit)
    _assert_domain_error(
        CleanupPlanErrorCode.STUDY_UNAVAILABLE,
        lambda: cleanup_domain._validate_aggregate_sizes(at_aggregate_limit + (member,)),
    )


def test_revalidation_without_changes_appends_one_revision_and_no_removals() -> None:
    records = _ordinary_records(2)
    initial = _composition(records)
    plan = _create_plan(initial).plan
    current = _composition(records, input_revision=_INPUT_B)
    command = _revalidation_command(plan, current)
    prepared = prepare_cleanup_plan_revalidation(
        current,
        plan,
        command,
        command_now=_NOW + timedelta(minutes=1),
    )

    assert prepared.removals == ()
    assert prepared.event.type is CleanupEventType.REVALIDATED
    assert prepared.event.revision == 2
    assert prepared.plan.plan_revision == 2
    assert prepared.plan.persisted_state is CleanupPlanState.FROZEN
    assert prepared.plan.members == plan.members


def test_missing_member_gets_only_missing_after_creation() -> None:
    records = _ordinary_records(2)
    plan = _create_plan(_composition(records)).plan
    current = _composition((records[1],), input_revision=_INPUT_B)
    prepared = prepare_cleanup_plan_revalidation(
        current,
        plan,
        _revalidation_command(plan, current),
        command_now=_NOW + timedelta(minutes=1),
    )

    assert len(prepared.removals) == 1
    assert prepared.removals[0].provider_message_id == records[0].provider_message_id
    assert prepared.removals[0].reason_codes == (CleanupExclusionReason.MISSING_AFTER_CREATION,)
    assert prepared.plan.persisted_state is CleanupPlanState.REDUCED


def test_new_protection_accumulates_current_reason_and_protection_changed() -> None:
    records = _ordinary_records(2)
    plan = _create_plan(_composition(records)).plan
    protected_records = (
        replace(records[0], label_ids=("INBOX", "STARRED")),
        records[1],
    )
    current = _composition(protected_records, input_revision=_INPUT_B)
    prepared = prepare_cleanup_plan_revalidation(
        current,
        plan,
        _revalidation_command(plan, current),
        command_now=_NOW + timedelta(minutes=1),
    )

    assert len(prepared.removals) == 1
    assert prepared.removals[0].provider_message_id == records[0].provider_message_id
    assert prepared.removals[0].reason_codes == (
        CleanupExclusionReason.STARRED,
        CleanupExclusionReason.PROTECTION_CHANGED,
    )
    removed_member = next(
        member
        for member in prepared.plan.members
        if member.provider_message_id == records[0].provider_message_id
    )
    assert cleanup_member_reason_codes(prepared.plan, removed_member) == (
        CleanupExclusionReason.STARRED,
        CleanupExclusionReason.PROTECTION_CHANGED,
    )


def test_new_protection_recalculates_keep_latest_without_promoting_excluded_members() -> None:
    records = _ordinary_records(3)
    initial = _composition(records)
    plan = _create_plan(
        initial,
        command=_create_command(initial, keep_latest_per_flow=1),
    ).plan
    newest = records[-1]
    assert _selected_provider_ids(plan) == {newest.provider_message_id}

    current = _composition(
        records[:-1] + (replace(newest, label_ids=("INBOX", "STARRED")),),
        input_revision=_INPUT_B,
    )
    prepared = prepare_cleanup_plan_revalidation(
        current,
        plan,
        _revalidation_command(plan, current),
        command_now=_NOW + timedelta(minutes=1),
    )

    assert prepared.plan.persisted_state is CleanupPlanState.INVALIDATED
    assert prepared.plan.current_eligible_count == 0
    assert len(prepared.removals) == 1
    assert prepared.removals[0].provider_message_id == newest.provider_message_id
    assert prepared.removals[0].reason_codes == (
        CleanupExclusionReason.STARRED,
        CleanupExclusionReason.PROTECTION_CHANGED,
    )
    assert all(
        member.initial_state is CleanupMemberInitialState.EXCLUDED
        for member in prepared.plan.members
        if member.provider_message_id != newest.provider_message_id
    )


def test_quota_and_samples_use_exact_datetime_order_without_float_precision_loss() -> None:
    records = _ordinary_records(2)
    identity_plan = _create_plan(_composition(records)).plan
    message_id_by_provider = {
        member.provider_message_id: member.message_id for member in identity_plan.members
    }
    older = datetime(9999, 12, 31, 23, 59, 59, 998_000, tzinfo=UTC)
    newer = older + timedelta(microseconds=1)
    assert older.timestamp() == newer.timestamp()
    provider_ordered = sorted(records, key=lambda item: item.provider_message_id)
    quota_records = (
        replace(provider_ordered[0], received_at=older),
        replace(provider_ordered[1], received_at=newer),
    )
    quota_composition = _composition(quota_records, input_revision=_INPUT_B)

    quota_plan = _create_plan(
        quota_composition,
        command=_create_command(
            quota_composition,
            keep_latest_per_flow=1,
            command_id=_REVALIDATE_COMMAND_ID_2,
        ),
        plan_id=_PLAN_B,
        input_revision=_INPUT_B,
    ).plan
    assert _selected_provider_ids(quota_plan) == {
        provider_ordered[1].provider_message_id
    }

    message_id_ordered = sorted(
        records,
        key=lambda item: message_id_by_provider[item.provider_message_id],
    )
    sample_records = (
        replace(message_id_ordered[0], received_at=older),
        replace(message_id_ordered[1], received_at=newer),
    )
    sample_composition = _composition(sample_records, input_revision=_INPUT_C)
    sample_plan = _create_plan(
        sample_composition,
        command=_create_command(sample_composition),
        input_revision=_INPUT_C,
    ).plan
    newer_member = next(
        member
        for member in sample_plan.members
        if member.provider_message_id == message_id_ordered[1].provider_message_id
    )
    included = tuple(
        sample for sample in sample_plan.samples if sample.kind is CleanupSampleKind.INCLUDED
    )
    assert included[0].message_id == newer_member.message_id


@pytest.mark.parametrize("target_kind", [CleanupTargetKind.SOURCE, CleanupTargetKind.FLOW])
def test_structural_source_or_flow_change_invalidates_without_guessing(
    target_kind: CleanupTargetKind,
) -> None:
    records = _ordinary_records(2)
    initial = _composition(records)
    source, flow = _source_and_flow(initial)
    selected_item: CleanupTargetCatalogItem = (
        source if target_kind is CleanupTargetKind.SOURCE else flow
    )
    command = _create_command(initial, targets=(_target(selected_item),))
    plan = _create_plan(initial, command=command).plan

    if target_kind is CleanupTargetKind.SOURCE:
        changed_records = tuple(
            replace(
                record,
                sender_name="Fuente Sintetica Cambiada",
                sender_address="cambio@estructura.example",
                authenticated_domain="estructura.example",
                list_id="<cambio.estructura.example>",
            )
            for record in records
        )
    else:
        changed_records = tuple(
            replace(record, list_id="<cambio.flujo.example>") for record in records
        )
    current = _composition(changed_records, input_revision=_INPUT_B)
    prepared = prepare_cleanup_plan_revalidation(
        current,
        plan,
        _revalidation_command(plan, current),
        command_now=_NOW + timedelta(minutes=1),
    )

    assert prepared.plan.persisted_state is CleanupPlanState.INVALIDATED
    assert len(prepared.removals) == plan.selected_at_creation_count
    assert all(
        removal.reason_codes == (CleanupExclusionReason.SCOPE_CHANGED,)
        for removal in prepared.removals
    )


def test_new_messages_consume_quota_but_never_join_or_revive_the_plan() -> None:
    initial_records = _ordinary_records(3)
    initial = _composition(initial_records)
    command = _create_command(initial, keep_latest_per_flow=2)
    plan = _create_plan(initial, command=command).plan
    initially_selected = _selected_provider_ids(plan)
    assert initially_selected == {
        initial_records[1].provider_message_id,
        initial_records[2].provider_message_id,
    }

    current_records = _ordinary_records(4)
    current = _composition(current_records, input_revision=_INPUT_B)
    first = prepare_cleanup_plan_revalidation(
        current,
        plan,
        _revalidation_command(plan, current),
        command_now=_NOW + timedelta(minutes=1),
    )
    assert {item.provider_message_id for item in first.removals} == {
        initial_records[1].provider_message_id
    }
    assert _eligible_provider_ids(first.plan) == {initial_records[2].provider_message_id}
    assert current_records[3].provider_message_id not in {
        member.provider_message_id for member in first.plan.members
    }
    assert initial_records[0].provider_message_id not in _selected_provider_ids(first.plan)

    without_new_message = _composition(initial_records, input_revision=_INPUT_C)
    second = prepare_cleanup_plan_revalidation(
        without_new_message,
        first.plan,
        _revalidation_command(
            first.plan,
            without_new_message,
            command_id=_REVALIDATE_COMMAND_ID_2,
        ),
        command_now=_NOW + timedelta(minutes=2),
    )
    assert second.removals == ()
    assert second.plan.persisted_state is CleanupPlanState.REDUCED
    assert _eligible_provider_ids(second.plan) == {initial_records[2].provider_message_id}
    assert _eligible_provider_ids(second.plan) <= initially_selected


def test_cancellation_is_append_only_terminal_and_preserves_preview() -> None:
    plan = _create_plan(_composition(_ordinary_records(2))).plan
    command = CancelCleanupPlanCommand(
        command_id=_CANCEL_COMMAND_ID,
        expected_plan_revision=plan.plan_revision,
    )
    prepared = prepare_cleanup_plan_cancellation(
        plan,
        command,
        command_now=_NOW + timedelta(minutes=1),
    )

    assert prepared.plan.persisted_state is CleanupPlanState.CANCELLED
    assert prepared.plan.plan_revision == 2
    assert prepared.plan.members == plan.members
    assert prepared.plan.samples == plan.samples
    assert prepared.event.type is CleanupEventType.CANCELLED
    assert prepared.event.observed_map_revision is None
    assert prepared.event.observed_policy_revision is None
    assert prepared.receipt.status is CleanupCommandStatus.CANCELLED
    assert prepared.plan.can_execute is False
    assert effective_plan_state(prepared.plan, _NOW + timedelta(days=2)) is (
        CleanupPlanState.CANCELLED
    )
    _assert_domain_error(
        CleanupPlanErrorCode.INVALID_TRANSITION,
        lambda: prepare_cleanup_plan_cancellation(
            prepared.plan,
            CancelCleanupPlanCommand(
                command_id="40000000-0000-4000-8000-000000000005",
                expected_plan_revision=prepared.plan.plan_revision,
            ),
            command_now=_NOW + timedelta(minutes=2),
        ),
    )


def test_cancel_uses_terminal_precedence_then_plan_revision_cas() -> None:
    composition = _composition(_ordinary_records(1))
    frozen = _create_plan(composition).plan
    wrong_revision = CancelCleanupPlanCommand(
        command_id=_CANCEL_COMMAND_ID,
        expected_plan_revision=frozen.plan_revision + 1,
    )
    _assert_domain_error(
        CleanupPlanErrorCode.PLAN_REVISION_CONFLICT,
        lambda: prepare_cleanup_plan_cancellation(
            frozen,
            wrong_revision,
            command_now=_NOW + timedelta(minutes=1),
        ),
    )

    invalidated = _create_plan(
        composition,
        command=_create_command(
            composition,
            temporal_filter=BeforeDateTemporalFilter(date=date(1900, 1, 1)),
        ),
        plan_id=_PLAN_B,
    ).plan
    _assert_domain_error(
        CleanupPlanErrorCode.INVALID_TRANSITION,
        lambda: prepare_cleanup_plan_cancellation(
            invalidated,
            CancelCleanupPlanCommand(
                command_id="40000000-0000-4000-8000-000000000006",
                expected_plan_revision=999,
            ),
            command_now=_NOW + timedelta(minutes=1),
        ),
    )


def test_expiration_is_derived_at_exactly_24_hours_from_injected_clock() -> None:
    composition = _composition(_ordinary_records(1))
    plan = _create_plan(composition, command_now=_NOW).plan
    assert plan.created_at == _NOW
    assert plan.events[0].recorded_at == _NOW
    assert plan.expires_at == _NOW + timedelta(seconds=86_400)
    assert effective_plan_state(plan, plan.expires_at - timedelta(microseconds=1)) is (
        CleanupPlanState.FROZEN
    )
    assert effective_plan_state(plan, plan.expires_at) is CleanupPlanState.EXPIRED

    current = _composition(_ordinary_records(1), input_revision=_INPUT_B)
    expired_command = RevalidateCleanupPlanCommand(
        command_id=_REVALIDATE_COMMAND_ID,
        expected_plan_revision=999,
        expected_map_revision=current.projection.map_revision,
        expected_policy_revision=current.projection.policy_revision,
    )
    _assert_domain_error(
        CleanupPlanErrorCode.PLAN_EXPIRED,
        lambda: prepare_cleanup_plan_revalidation(
            current,
            plan,
            expired_command,
            command_now=plan.expires_at,
        ),
    )
    assert plan.plan_revision == 1
    assert plan.persisted_state is CleanupPlanState.FROZEN


def test_disposition_storage_effect_is_inert_and_can_execute_is_always_false() -> None:
    composition = _composition(_ordinary_records(1))
    archive = _create_plan(composition).plan
    trash = _create_plan(
        composition,
        command=_create_command(
            composition,
            disposition=CleanupDisposition.TRASH,
            command_id="40000000-0000-4000-8000-000000000007",
        ),
        plan_id=_PLAN_B,
    ).plan

    assert archive.storage_effect is CleanupStorageEffect.NONE
    assert trash.storage_effect is CleanupStorageEffect.NOT_GUARANTEED
    assert archive.can_execute is False
    assert trash.can_execute is False
    assert archive.effective_freed_bytes is None
    assert trash.effective_freed_bytes is None


def test_command_fingerprint_covers_contract_method_path_plan_and_body() -> None:
    composition = _composition(_ordinary_records(1))
    command = _create_command(composition)
    body = (
        command.command_id,
        command.expected_map_revision,
        command.expected_policy_revision,
        command.disposition.value,
        tuple((item.kind.value, item.target_id) for item in command.targets),
        (command.temporal_filter.kind.value,),
        command.read_state.value,
        command.excluded_label_ids,
        command.keep_latest_per_flow,
    )
    payload = (
        CLEANUP_PLAN_CONTRACT_VERSION,
        "POST",
        "/api/v3/study/plans",
        body,
    )
    expected = hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert cleanup_command_fingerprint(command) == expected
    assert cleanup_command_fingerprint(command) == cleanup_command_fingerprint(command)
    changed = replace(command, keep_latest_per_flow=1)
    assert cleanup_command_fingerprint(changed) != expected

    revalidate = RevalidateCleanupPlanCommand(
        command_id=_REVALIDATE_COMMAND_ID,
        expected_plan_revision=1,
        expected_map_revision=composition.projection.map_revision,
        expected_policy_revision=composition.projection.policy_revision,
    )
    assert cleanup_command_fingerprint(revalidate, plan_id=_PLAN_A) != (
        cleanup_command_fingerprint(revalidate, plan_id=_PLAN_B)
    )
    cancel = CancelCleanupPlanCommand(
        command_id=_REVALIDATE_COMMAND_ID,
        expected_plan_revision=1,
    )
    assert cleanup_command_fingerprint(cancel, plan_id=_PLAN_A) != (
        cleanup_command_fingerprint(revalidate, plan_id=_PLAN_A)
    )
    _assert_domain_error(
        CleanupPlanErrorCode.INVALID_REQUEST,
        lambda: cleanup_command_fingerprint(command, plan_id=_PLAN_A),
    )
