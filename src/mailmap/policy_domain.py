from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from mailmap.classification_model import (
    CLASSIFICATION_MODEL_VERSION,
    ClassificationEvidence,
    ClassificationResult,
    ClassifiedFlow,
    ClassifiedMessage,
    ClassifiedSource,
    FlowAnchorKind,
    FlowIdentityDescriptor,
    SourceAnchorKind,
    SourceIdentityDescriptor,
)
from mailmap.index_model import IndexedMessageRecord, validate_account_key
from mailmap.model import Confianza, Intencion, Proteccion, Rubro, Suscripcion
from mailmap.policy_model import (
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
    PolicyBinding,
    PolicyBindingStatus,
    PolicyDecisionCommand,
    PolicyDecisionEvidence,
    PolicyError,
    PolicyErrorCode,
    PolicyEvidenceCode,
    PolicyProtectionReason,
    PolicyRelationKind,
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
    evidence_sort_key,
    is_policy_decision_command,
)

_ID_NAMESPACE = "mailcleanup.local-policy.v1"
_CONFIDENCE_ORDER = (
    Confianza.ALTA,
    Confianza.MEDIA,
    Confianza.BAJA,
    Confianza.CONTRADICTORIA,
)
_HARD_LABEL_REASONS = {
    "SENT": PolicyProtectionReason.SENT,
    "DRAFT": PolicyProtectionReason.DRAFT,
    "TRASH": PolicyProtectionReason.TRASH,
}
_STRUCTURAL_COMMANDS = (MergeSources, PartitionSource)


@dataclass(frozen=True, slots=True)
class _ValidatedInput:
    account_key: str = field(repr=False)
    records: tuple[IndexedMessageRecord, ...] = field(repr=False)
    classification: ClassificationResult = field(repr=False)
    policies: tuple[ActivePolicy, ...] = field(repr=False)
    records_by_id: dict[str, IndexedMessageRecord] = field(repr=False)
    messages_by_id: dict[str, ClassifiedMessage] = field(repr=False)
    sources_by_id: dict[str, ClassifiedSource] = field(repr=False)
    flows_by_id: dict[str, ClassifiedFlow] = field(repr=False)


@dataclass(slots=True)
class _SourceState:
    selector: EffectiveSourceSelector = field(repr=False)
    effective_source_id: str
    automatic_source_ids: tuple[str, ...]
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    flow_ids: tuple[str, ...]
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_confidence: Confianza
    effective_confidence: Confianza
    automatic_evidence: tuple[ClassificationEvidence, ...] = field(repr=False)
    policy_evidence: list[PolicyDecisionEvidence] = field(default_factory=list, repr=False)
    decision_ids: set[str] = field(default_factory=set, repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)


@dataclass(slots=True)
class _FlowState:
    selector: EffectiveFlowSelector = field(repr=False)
    effective_flow_id: str
    effective_source_id: str
    automatic_flow_id: str
    automatic_display_name: str = field(repr=False)
    effective_display_name: str = field(repr=False)
    message_ids: tuple[str, ...] = field(repr=False)
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    automatic_evidence: tuple[ClassificationEvidence, ...] = field(repr=False)
    policy_evidence: list[PolicyDecisionEvidence] = field(default_factory=list, repr=False)
    decision_ids: set[str] = field(default_factory=set, repr=False)
    structural_decision_ids: tuple[str, ...] = field(default=(), repr=False)


@dataclass(frozen=True, slots=True)
class _Candidate:
    effective_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    flow_ids: tuple[str, ...]
    structural_decision_ids: tuple[str, ...]
    message_ids: tuple[str, ...]


@dataclass(slots=True)
class _MessageProtection:
    automatic_reasons: set[PolicyProtectionReason] = field(default_factory=set)
    effective_reasons: set[PolicyProtectionReason] = field(default_factory=set)
    decision_ids: set[str] = field(default_factory=set)
    review_required: bool = False


def _validated_input(
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    policies: Iterable[ActivePolicy],
) -> _ValidatedInput:
    try:
        validated_account = validate_account_key(account_key)
        materialized_records = tuple(records)
        materialized_policies = tuple(policies)
    except Exception:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
    if not isinstance(classification, ClassificationResult):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if classification.version != CLASSIFICATION_MODEL_VERSION:
        raise PolicyError(PolicyErrorCode.UNKNOWN_POLICY_VERSION)
    if any(not isinstance(record, IndexedMessageRecord) for record in materialized_records):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if any(record.account_key != validated_account for record in materialized_records):
        raise PolicyError(PolicyErrorCode.MIXED_ACCOUNTS)
    record_ids = tuple(record.provider_message_id for record in materialized_records)
    if len(set(record_ids)) != len(record_ids):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    ordered_records = tuple(
        sorted(materialized_records, key=lambda item: item.provider_message_id)
    )
    classified_ids = tuple(message.provider_message_id for message in classification.messages)
    if tuple(sorted(record_ids)) != classified_ids:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if ordered_records:
        if classification.account_key != validated_account:
            raise PolicyError(PolicyErrorCode.MIXED_ACCOUNTS)
    elif classification.account_key is not None or (
        classification.messages or classification.sources or classification.flows
    ):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if any(not isinstance(policy, ActivePolicy) for policy in materialized_policies):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if any(policy.account_key != validated_account for policy in materialized_policies):
        raise PolicyError(PolicyErrorCode.MIXED_ACCOUNTS)
    decision_ids = tuple(policy.decision_id for policy in materialized_policies)
    revisions = tuple(policy.account_revision for policy in materialized_policies)
    if len(set(decision_ids)) != len(decision_ids) or len(set(revisions)) != len(revisions):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    ordered_policies = tuple(
        sorted(
            materialized_policies,
            key=lambda item: (item.account_revision, item.decision_id),
        )
    )
    return _ValidatedInput(
        account_key=validated_account,
        records=ordered_records,
        classification=classification,
        policies=ordered_policies,
        records_by_id={record.provider_message_id: record for record in ordered_records},
        messages_by_id={
            message.provider_message_id: message for message in classification.messages
        },
        sources_by_id={source.source_id: source for source in classification.sources},
        flows_by_id={flow.flow_id: flow for flow in classification.flows},
    )


def _flatten_key(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(part for item in value for part in _flatten_key(item))
    return (str(value),)


def _effective_identifier(
    kind: str,
    selector: EffectiveSourceSelector | EffectiveFlowSelector,
) -> str:
    canonical = "\x1f".join(
        (_ID_NAMESPACE, kind, *_flatten_key(selector.canonical_key))
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"effective-{kind}-v1-{digest}"


def _worst_confidence(values: Iterable[Confianza]) -> Confianza:
    materialized = tuple(values)
    if not materialized:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return max(materialized, key=_CONFIDENCE_ORDER.index)


def _classification_evidence(
    values: Iterable[ClassificationEvidence],
) -> tuple[ClassificationEvidence, ...]:
    selected = {evidence_sort_key(value): value for value in values}
    return tuple(selected[key] for key in sorted(selected))


def _effective_evidence(values: Iterable[EffectiveEvidence]) -> tuple[EffectiveEvidence, ...]:
    selected = {evidence_sort_key(value): value for value in values}
    return tuple(selected[key] for key in sorted(selected))


def _policy_evidence(command: PolicyDecisionCommand) -> PolicyDecisionEvidence:
    code = {
        SetSourceDisplayName: PolicyEvidenceCode.SOURCE_DISPLAY_NAME,
        SetSourceRubro: PolicyEvidenceCode.SOURCE_RUBRO,
        SetFlowDisplayName: PolicyEvidenceCode.FLOW_DISPLAY_NAME,
        SetFlowIntention: PolicyEvidenceCode.FLOW_INTENTION,
        MergeSources: PolicyEvidenceCode.MERGE_SOURCES,
        PartitionSource: PolicyEvidenceCode.PARTITION_SOURCE,
        ProtectTarget: PolicyEvidenceCode.PROTECT_TARGET,
    }[type(command)]
    return PolicyDecisionEvidence(code=code, decision_id=command.decision_id)


def _common_rubro(
    message_ids: Iterable[str], messages_by_id: dict[str, ClassifiedMessage]
) -> Rubro:
    rubros = {messages_by_id[message_id].rubro for message_id in message_ids}
    return next(iter(rubros)) if len(rubros) == 1 else Rubro.DESCONOCIDO


def _automatic_source_selector(
    account_key: str, descriptor: SourceIdentityDescriptor
) -> EffectiveSourceSelector:
    return EffectiveSourceSelector(
        account_key=account_key,
        kind=EffectiveSourceKind.AUTOMATIC,
        automatic_sources=(descriptor,),
    )


def _source_state(
    *,
    data: _ValidatedInput,
    selector: EffectiveSourceSelector,
    message_ids: tuple[str, ...],
    automatic_source_ids: tuple[str, ...],
    structural_command: PolicyDecisionCommand | None = None,
) -> _SourceState:
    sources = tuple(data.sources_by_id[source_id] for source_id in automatic_source_ids)
    if selector.kind is EffectiveSourceKind.MERGED:
        automatic_display_name = "Fuente combinada"
    else:
        automatic_display_name = sources[0].display_name
    related_flow_ids = {
        data.messages_by_id[message_id].flow_id for message_id in message_ids
    }
    evidence = _classification_evidence(
        (
            *(item for source in sources for item in source.evidence),
            *(
                item
                for message_id in message_ids
                for item in data.messages_by_id[message_id].evidence
            ),
            *(
                item
                for flow_id in related_flow_ids
                for item in data.flows_by_id[flow_id].evidence
            ),
        )
    )
    policy_values: list[PolicyDecisionEvidence] = []
    decision_ids: set[str] = set()
    structural_ids: tuple[str, ...] = ()
    if structural_command is not None:
        policy_values.append(_policy_evidence(structural_command))
        decision_ids.add(structural_command.decision_id)
        structural_ids = (structural_command.decision_id,)
    confidence = _worst_confidence(
        data.messages_by_id[message_id].confianza for message_id in message_ids
    )
    rubro = _common_rubro(message_ids, data.messages_by_id)
    return _SourceState(
        selector=selector,
        effective_source_id=_effective_identifier("source", selector),
        automatic_source_ids=automatic_source_ids,
        automatic_display_name=automatic_display_name,
        effective_display_name=automatic_display_name,
        message_ids=message_ids,
        flow_ids=(),
        automatic_rubro=rubro,
        effective_rubro=rubro,
        automatic_confidence=confidence,
        effective_confidence=confidence,
        automatic_evidence=evidence,
        policy_evidence=policy_values,
        decision_ids=decision_ids,
        structural_decision_ids=structural_ids,
    )


def _baseline_sources(data: _ValidatedInput) -> dict[str, _SourceState]:
    states: dict[str, _SourceState] = {}
    for source in data.classification.sources:
        selector = _automatic_source_selector(data.account_key, source.identity_descriptor)
        state = _source_state(
            data=data,
            selector=selector,
            message_ids=source.message_ids,
            automatic_source_ids=(source.source_id,),
        )
        states[state.effective_source_id] = state
    return states


def _build_flows(
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
) -> tuple[dict[str, _FlowState], dict[str, str], dict[str, str]]:
    flows: dict[str, _FlowState] = {}
    message_to_source: dict[str, str] = {}
    message_to_flow: dict[str, str] = {}
    for source in sources.values():
        for message_id in source.message_ids:
            if message_id in message_to_source:
                raise PolicyError(PolicyErrorCode.INVALID_INPUT)
            message_to_source[message_id] = source.effective_source_id
        source_flow_ids: list[str] = []
        for automatic_flow in data.classification.flows:
            members = tuple(
                message_id
                for message_id in automatic_flow.message_ids
                if message_id in source.message_ids
            )
            if not members:
                continue
            selector = EffectiveFlowSelector(
                account_key=data.account_key,
                automatic_flow=automatic_flow.identity_descriptor,
                effective_source=source.selector,
            )
            effective_flow_id = _effective_identifier("flow", selector)
            evidence = _classification_evidence(
                (
                    *automatic_flow.evidence,
                    *(
                        item
                        for message_id in members
                        for item in data.messages_by_id[message_id].evidence
                    ),
                )
            )
            # A structural policy may split an automatic flow, but it must not
            # improve the confidence D4 assigned to that flow.  In particular,
            # a fragment containing only the stronger members still inherits
            # the original flow's conservative confidence.
            confidence = automatic_flow.confianza
            state = _FlowState(
                selector=selector,
                effective_flow_id=effective_flow_id,
                effective_source_id=source.effective_source_id,
                automatic_flow_id=automatic_flow.flow_id,
                automatic_display_name=automatic_flow.display_name,
                effective_display_name=automatic_flow.display_name,
                message_ids=members,
                automatic_intention=automatic_flow.intencion,
                effective_intention=automatic_flow.intencion,
                subscription=automatic_flow.suscripcion,
                automatic_confidence=confidence,
                effective_confidence=confidence,
                automatic_evidence=evidence,
                policy_evidence=list(source.policy_evidence),
                decision_ids=set(source.decision_ids),
                structural_decision_ids=source.structural_decision_ids,
            )
            flows[effective_flow_id] = state
            source_flow_ids.append(effective_flow_id)
            for message_id in members:
                if message_id in message_to_flow:
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                message_to_flow[message_id] = effective_flow_id
        source.flow_ids = tuple(sorted(source_flow_ids))
    expected = set(data.messages_by_id)
    if set(message_to_source) != expected or set(message_to_flow) != expected:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return flows, message_to_source, message_to_flow


def _source_flow_ids(data: _ValidatedInput, message_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted({data.messages_by_id[message_id].flow_id for message_id in message_ids})
    )


def _source_for_selector(
    sources: dict[str, _SourceState], selector: EffectiveSourceSelector
) -> _SourceState | None:
    matches = [source for source in sources.values() if source.selector == selector]
    if len(matches) > 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return matches[0] if matches else None


def _flow_for_selector(
    flows: dict[str, _FlowState], selector: EffectiveFlowSelector
) -> _FlowState | None:
    matches = [flow for flow in flows.values() if flow.selector == selector]
    if len(matches) > 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return matches[0] if matches else None


def _partition_anchor_message_ids(
    anchor: PartitionAnchor,
    allowed_message_ids: Iterable[str],
    data: _ValidatedInput,
) -> tuple[str, ...]:
    allowed = frozenset(allowed_message_ids)
    if anchor.kind is PartitionAnchorKind.SENDER:
        return tuple(
            sorted(
                message_id
                for message_id in allowed
                if _canonical_sender_for_message(message_id, data)
                == anchor.sender_address
            )
        )
    if anchor.kind is PartitionAnchorKind.FLOW:
        return tuple(
            sorted(
                message_id
                for flow in data.classification.flows
                if flow.identity_descriptor == anchor.flow
                for message_id in flow.message_ids
                if message_id in allowed
            )
        )
    return (
        (anchor.provider_message_id,)
        if anchor.provider_message_id in allowed
        else ()
    )


def _canonical_sender_for_message(
    message_id: str,
    data: _ValidatedInput,
) -> str | None:
    record_value = data.records_by_id[message_id].sender_address
    if record_value is None:
        return None
    descriptor = data.sources_by_id[
        data.messages_by_id[message_id].source_id
    ].identity_descriptor
    normalized_record = record_value.strip().casefold()
    matches = tuple(
        sender
        for sender in descriptor.sender_addresses
        if sender == normalized_record
    )
    if len(matches) > 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return matches[0] if matches else None


def _message_partition_anchor_is_fallback(
    anchor: PartitionAnchor,
    data: _ValidatedInput,
) -> bool:
    if anchor.kind is not PartitionAnchorKind.MESSAGE:
        return True
    message_id = anchor.provider_message_id
    if message_id is None or message_id not in data.records_by_id:
        return False
    if _canonical_sender_for_message(message_id, data) is not None:
        return False
    classified = data.messages_by_id[message_id]
    return (
        data.flows_by_id[classified.flow_id].identity_descriptor.kind
        is FlowAnchorKind.ISOLATED_MESSAGE
    )


def _partition_groups(
    groups: tuple[tuple[PartitionAnchor, ...], ...],
    source_message_ids: tuple[str, ...],
    data: _ValidatedInput,
) -> tuple[tuple[str, ...], ...] | None:
    resolved: list[tuple[str, ...]] = []
    seen: set[str] = set()
    for group in groups:
        matched_ids = tuple(
            message_id
            for anchor in group
            for message_id in _partition_anchor_message_ids(
                anchor, source_message_ids, data
            )
        )
        if len(matched_ids) != len(set(matched_ids)):
            return None
        group_ids = tuple(sorted(matched_ids))
        if not group_ids or any(message_id in seen for message_id in group_ids):
            return None
        seen.update(group_ids)
        resolved.append(group_ids)
    if seen != set(source_message_ids):
        return None
    return tuple(resolved)


def _candidate_for_source(
    source: _SourceState,
    data: _ValidatedInput,
) -> _Candidate:
    return _Candidate(
        effective_ids=(source.effective_source_id,),
        source_ids=source.automatic_source_ids,
        flow_ids=_source_flow_ids(data, source.message_ids),
        structural_decision_ids=source.structural_decision_ids,
        message_ids=source.message_ids,
    )


def _empty_candidate() -> _Candidate:
    return _Candidate(
        effective_ids=(),
        source_ids=(),
        flow_ids=(),
        structural_decision_ids=(),
        message_ids=(),
    )


def _merge_candidates(values: Iterable[_Candidate]) -> _Candidate:
    materialized = tuple(values)
    return _Candidate(
        effective_ids=tuple(
            sorted({item for value in materialized for item in value.effective_ids})
        ),
        source_ids=tuple(
            sorted({item for value in materialized for item in value.source_ids})
        ),
        flow_ids=tuple(
            sorted({item for value in materialized for item in value.flow_ids})
        ),
        structural_decision_ids=tuple(
            sorted(
                {
                    item
                    for value in materialized
                    for item in value.structural_decision_ids
                }
            )
        ),
        message_ids=tuple(
            sorted({item for value in materialized for item in value.message_ids})
        ),
    )


def _status_for_exact_anchor(
    anchor: PreparedPolicyAnchor,
    candidate: _Candidate,
) -> PolicyBindingStatus:
    if anchor.structural_decision_ids != candidate.structural_decision_ids:
        return PolicyBindingStatus.NEEDS_REVIEW
    observed_effective = (
        (anchor.observed_effective_id,)
        if anchor.observed_effective_id is not None
        else ()
    )
    if observed_effective != candidate.effective_ids:
        return PolicyBindingStatus.NEEDS_REVIEW
    if (
        anchor.observed_source_ids == candidate.source_ids
        and anchor.observed_flow_ids == candidate.flow_ids
    ):
        return PolicyBindingStatus.EXACT
    return PolicyBindingStatus.REBOUND


def _source_descriptors_share_anchor(
    historical: SourceIdentityDescriptor,
    current: SourceIdentityDescriptor,
) -> bool:
    if historical.kind is not current.kind:
        return False
    if historical.kind is SourceAnchorKind.ISOLATED_MESSAGE:
        return historical.isolated_message_id == current.isolated_message_id
    return bool(
        set(historical.sender_addresses).intersection(current.sender_addresses)
    )


def _source_selector_shares_anchor(
    historical: EffectiveSourceSelector,
    current: EffectiveSourceSelector,
) -> bool:
    return any(
        _source_descriptors_share_anchor(left, right)
        for left in historical.automatic_sources
        for right in current.automatic_sources
    )


def _flow_descriptors_share_anchor(
    historical: FlowIdentityDescriptor,
    current: FlowIdentityDescriptor,
) -> bool:
    return (
        historical.kind is current.kind
        and historical.list_id == current.list_id
        and historical.sender_address == current.sender_address
        and historical.automatic_intention is current.automatic_intention
        and historical.isolated_message_id == current.isolated_message_id
        and _source_descriptors_share_anchor(historical.source, current.source)
    )


def _resolve_source_anchor(
    anchor: PreparedPolicyAnchor,
    sources: dict[str, _SourceState],
    data: _ValidatedInput,
) -> tuple[PolicyBindingStatus, _Candidate]:
    if not isinstance(anchor.selector, EffectiveSourceSelector):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    exact = _source_for_selector(sources, anchor.selector)
    if exact is not None:
        candidate = _candidate_for_source(exact, data)
        return _status_for_exact_anchor(anchor, candidate), candidate
    fallbacks = tuple(
        source
        for source in sources.values()
        if set(anchor.observed_source_ids).intersection(source.automatic_source_ids)
        or anchor.observed_effective_id == source.effective_source_id
        or _source_selector_shares_anchor(anchor.selector, source.selector)
    )
    if not fallbacks:
        return PolicyBindingStatus.ORPHANED, _empty_candidate()
    candidate = _merge_candidates(_candidate_for_source(source, data) for source in fallbacks)
    if anchor.structural_decision_ids != candidate.structural_decision_ids:
        return PolicyBindingStatus.NEEDS_REVIEW, candidate
    if len(fallbacks) == 1:
        return PolicyBindingStatus.NEEDS_REVIEW, candidate
    return PolicyBindingStatus.AMBIGUOUS, candidate


def _combined_status(values: Iterable[PolicyBindingStatus]) -> PolicyBindingStatus:
    statuses = tuple(values)
    if not statuses:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    if PolicyBindingStatus.CONFLICT in statuses:
        return PolicyBindingStatus.CONFLICT
    if PolicyBindingStatus.AMBIGUOUS in statuses:
        return PolicyBindingStatus.AMBIGUOUS
    if all(status is PolicyBindingStatus.ORPHANED for status in statuses):
        return PolicyBindingStatus.ORPHANED
    if any(
        status in {PolicyBindingStatus.NEEDS_REVIEW, PolicyBindingStatus.ORPHANED}
        for status in statuses
    ):
        return PolicyBindingStatus.NEEDS_REVIEW
    if any(status is PolicyBindingStatus.REBOUND for status in statuses):
        return PolicyBindingStatus.REBOUND
    return PolicyBindingStatus.EXACT


def _binding(
    policy: ActivePolicy,
    status: PolicyBindingStatus,
    candidate: _Candidate,
) -> PolicyBinding:
    return PolicyBinding(
        decision_id=policy.decision_id,
        status=status,
        selectors=tuple(anchor.selector for anchor in policy.anchors),
        observed_effective_ids=tuple(
            sorted(
                {
                    anchor.observed_effective_id
                    for anchor in policy.anchors
                    if anchor.observed_effective_id is not None
                }
            )
        ),
        current_effective_ids=candidate.effective_ids,
        observed_source_ids=tuple(
            sorted(
                {
                    source_id
                    for anchor in policy.anchors
                    for source_id in anchor.observed_source_ids
                }
            )
        ),
        current_source_ids=candidate.source_ids,
        observed_flow_ids=tuple(
            sorted(
                {
                    flow_id
                    for anchor in policy.anchors
                    for flow_id in anchor.observed_flow_ids
                }
            )
        ),
        current_flow_ids=candidate.flow_ids,
        structural_decision_ids=tuple(
            sorted(
                {
                    decision_id
                    for anchor in policy.anchors
                    for decision_id in anchor.structural_decision_ids
                }
            )
        ),
        current_structural_decision_ids=candidate.structural_decision_ids,
        affected_message_ids=candidate.message_ids,
    )


def _structural_binding(
    policy: ActivePolicy,
    sources: dict[str, _SourceState],
    data: _ValidatedInput,
) -> PolicyBinding:
    command = policy.command
    if isinstance(command, MergeSources):
        resolved = tuple(
            _resolve_source_anchor(anchor, sources, data) for anchor in policy.anchors
        )
        return _binding(
            policy,
            _combined_status(status for status, _candidate in resolved),
            _merge_candidates(candidate for _status, candidate in resolved),
        )
    if not isinstance(command, PartitionSource):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    target = policy.anchors[0]
    target_status, target_candidate = _resolve_source_anchor(target, sources, data)
    target_source = _source_for_selector(sources, command.source_selector)
    if target_source is None or target_status not in {
        PolicyBindingStatus.EXACT,
        PolicyBindingStatus.REBOUND,
    }:
        return _binding(policy, target_status, target_candidate)
    groups = tuple(tuple(group.anchors) for group in command.groups)
    if any(
        not _message_partition_anchor_is_fallback(anchor, data)
        for group in groups
        for anchor in group
    ):
        return _binding(policy, PolicyBindingStatus.NEEDS_REVIEW, target_candidate)
    resolved_groups = _partition_groups(groups, target_source.message_ids, data)
    if resolved_groups is None:
        return _binding(policy, PolicyBindingStatus.NEEDS_REVIEW, target_candidate)
    member_statuses: list[PolicyBindingStatus] = [target_status]
    members = policy.anchors[1:]
    for member in members:
        if not isinstance(member.selector, PartitionAnchor):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        current_ids = _partition_anchor_message_ids(
            member.selector, target_source.message_ids, data
        )
        current = _Candidate(
            effective_ids=(),
            source_ids=tuple(
                sorted(
                    {
                        data.messages_by_id[message_id].source_id
                        for message_id in current_ids
                    }
                )
            ),
            flow_ids=tuple(
                sorted(
                    {
                        data.messages_by_id[message_id].flow_id
                        for message_id in current_ids
                    }
                )
            ),
            structural_decision_ids=(),
            message_ids=current_ids,
        )
        if not current_ids:
            member_statuses.append(PolicyBindingStatus.NEEDS_REVIEW)
        elif (
            member.observed_source_ids == current.source_ids
            and member.observed_flow_ids == current.flow_ids
        ):
            member_statuses.append(PolicyBindingStatus.EXACT)
        else:
            member_statuses.append(PolicyBindingStatus.REBOUND)
    return _binding(policy, _combined_status(member_statuses), target_candidate)


def _structural_source_descriptors(
    command: PolicyDecisionCommand,
) -> tuple[SourceIdentityDescriptor, ...]:
    if isinstance(command, MergeSources):
        return tuple(
            selector.automatic_sources[0] for selector in command.source_selectors
        )
    if isinstance(command, PartitionSource):
        return command.source_selector.automatic_sources
    return ()


def _mark_structural_conflicts(
    policies: tuple[ActivePolicy, ...],
    bindings: dict[str, PolicyBinding],
) -> None:
    conflicting: set[str] = set()
    for index, left in enumerate(policies):
        left_binding = bindings[left.decision_id]
        left_descriptors = _structural_source_descriptors(left.command)
        for right in policies[index + 1 :]:
            right_binding = bindings[right.decision_id]
            historical_overlap = any(
                _source_descriptors_share_anchor(left_descriptor, right_descriptor)
                for left_descriptor in left_descriptors
                for right_descriptor in _structural_source_descriptors(right.command)
            )
            current_overlap = bool(
                set(left_binding.affected_message_ids).intersection(
                    right_binding.affected_message_ids
                )
            )
            if historical_overlap or current_overlap:
                conflicting.update((left.decision_id, right.decision_id))
    for decision_id in conflicting:
        bindings[decision_id] = replace(
            bindings[decision_id], status=PolicyBindingStatus.CONFLICT
        )


def _apply_merge(
    policy: ActivePolicy,
    sources: dict[str, _SourceState],
    data: _ValidatedInput,
) -> None:
    command = policy.command
    if not isinstance(command, MergeSources):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    participants = tuple(
        _source_for_selector(sources, selector) for selector in command.source_selectors
    )
    if any(participant is None for participant in participants):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    selected = tuple(
        participant for participant in participants if participant is not None
    )
    selector = EffectiveSourceSelector(
        account_key=data.account_key,
        kind=EffectiveSourceKind.MERGED,
        automatic_sources=tuple(
            item for source_selector in command.source_selectors
            for item in source_selector.automatic_sources
        ),
    )
    merged = _source_state(
        data=data,
        selector=selector,
        message_ids=tuple(
            sorted({message_id for source in selected for message_id in source.message_ids})
        ),
        automatic_source_ids=tuple(
            sorted(
                {
                    source_id
                    for source in selected
                    for source_id in source.automatic_source_ids
                }
            )
        ),
        structural_command=command,
    )
    for source in selected:
        sources.pop(source.effective_source_id)
    sources[merged.effective_source_id] = merged


def _apply_partition(
    policy: ActivePolicy,
    sources: dict[str, _SourceState],
    data: _ValidatedInput,
) -> None:
    command = policy.command
    if not isinstance(command, PartitionSource):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    target = _source_for_selector(sources, command.source_selector)
    if target is None:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    group_anchors = tuple(tuple(group.anchors) for group in command.groups)
    resolved = _partition_groups(group_anchors, target.message_ids, data)
    if resolved is None:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    sources.pop(target.effective_source_id)
    for group, message_ids in zip(command.groups, resolved, strict=True):
        selector = EffectiveSourceSelector(
            account_key=data.account_key,
            kind=EffectiveSourceKind.PARTITION_GROUP,
            automatic_sources=command.source_selector.automatic_sources,
            partition_anchors=group.anchors,
        )
        state = _source_state(
            data=data,
            selector=selector,
            message_ids=message_ids,
            automatic_source_ids=target.automatic_source_ids,
            structural_command=command,
        )
        sources[state.effective_source_id] = state


def _candidate_for_flow(
    flow: _FlowState,
    sources: dict[str, _SourceState],
) -> _Candidate:
    source = sources[flow.effective_source_id]
    return _Candidate(
        effective_ids=(flow.effective_flow_id,),
        source_ids=source.automatic_source_ids,
        flow_ids=(flow.automatic_flow_id,),
        structural_decision_ids=flow.structural_decision_ids,
        message_ids=flow.message_ids,
    )


def _candidate_for_message_ids(
    message_ids: Iterable[str],
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_to_source: dict[str, str],
    message_to_flow: dict[str, str],
) -> _Candidate:
    ordered = tuple(sorted(set(message_ids)))
    effective_source_ids = {
        message_to_source[message_id] for message_id in ordered
    }
    effective_flow_ids = {message_to_flow[message_id] for message_id in ordered}
    return _Candidate(
        effective_ids=tuple(sorted((*effective_source_ids, *effective_flow_ids))),
        source_ids=tuple(
            sorted({data.messages_by_id[message_id].source_id for message_id in ordered})
        ),
        flow_ids=tuple(
            sorted({data.messages_by_id[message_id].flow_id for message_id in ordered})
        ),
        structural_decision_ids=tuple(
            sorted(
                {
                    decision_id
                    for effective_source_id in effective_source_ids
                    for decision_id in sources[
                        effective_source_id
                    ].structural_decision_ids
                }
                | {
                    decision_id
                    for effective_flow_id in effective_flow_ids
                    for decision_id in flows[
                        effective_flow_id
                    ].structural_decision_ids
                }
            )
        ),
        message_ids=ordered,
    )


def _resolve_target_anchor(
    anchor: PreparedPolicyAnchor,
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_to_source: dict[str, str],
    message_to_flow: dict[str, str],
) -> tuple[PolicyBindingStatus, _Candidate]:
    selector = anchor.selector
    if isinstance(selector, EffectiveSourceSelector):
        exact = _source_for_selector(sources, selector)
        if exact is not None:
            candidate = _candidate_for_source(exact, data)
            return _status_for_exact_anchor(anchor, candidate), candidate
        fallbacks = tuple(
            source
            for source in sources.values()
            if set(anchor.observed_source_ids).intersection(source.automatic_source_ids)
            or anchor.observed_effective_id == source.effective_source_id
            or _source_selector_shares_anchor(selector, source.selector)
        )
        if not fallbacks:
            return PolicyBindingStatus.ORPHANED, _empty_candidate()
        candidate = _merge_candidates(
            _candidate_for_source(source, data) for source in fallbacks
        )
        if anchor.structural_decision_ids != candidate.structural_decision_ids:
            return PolicyBindingStatus.NEEDS_REVIEW, candidate
        return (
            PolicyBindingStatus.NEEDS_REVIEW
            if len(fallbacks) == 1
            else PolicyBindingStatus.AMBIGUOUS,
            candidate,
        )
    if isinstance(selector, EffectiveFlowSelector):
        exact_flow = _flow_for_selector(flows, selector)
        if exact_flow is not None:
            candidate = _candidate_for_flow(exact_flow, sources)
            return _status_for_exact_anchor(anchor, candidate), candidate
        flow_fallbacks = tuple(
            flow
            for flow in flows.values()
            if flow.automatic_flow_id in anchor.observed_flow_ids
            or anchor.observed_effective_id == flow.effective_flow_id
            or _flow_descriptors_share_anchor(
                selector.automatic_flow, flow.selector.automatic_flow
            )
        )
        if not flow_fallbacks:
            flow_fallbacks = tuple(
                flow
                for flow in flows.values()
                if _source_descriptors_share_anchor(
                    selector.automatic_flow.source,
                    flow.selector.automatic_flow.source,
                )
            )
        if not flow_fallbacks:
            return PolicyBindingStatus.ORPHANED, _empty_candidate()
        candidate = _merge_candidates(
            _candidate_for_flow(flow, sources) for flow in flow_fallbacks
        )
        if anchor.structural_decision_ids != candidate.structural_decision_ids:
            return PolicyBindingStatus.NEEDS_REVIEW, candidate
        return (
            PolicyBindingStatus.NEEDS_REVIEW
            if len(flow_fallbacks) == 1
            else PolicyBindingStatus.AMBIGUOUS,
            candidate,
        )
    message_ids: tuple[str, ...]
    if isinstance(selector, MessageSelector):
        message_ids = (
            (selector.provider_message_id,)
            if selector.provider_message_id in data.records_by_id
            else ()
        )
    elif isinstance(selector, SenderSelector):
        message_ids = tuple(
            message_id
            for message_id in data.records_by_id
            if _canonical_sender_for_message(message_id, data)
            == selector.sender_address
        )
    elif isinstance(selector, LabelSelector):
        message_ids = tuple(
            record.provider_message_id
            for record in data.records
            if selector.label_id in record.label_ids
        )
    else:
        raise PolicyError(PolicyErrorCode.UNSUPPORTED_TARGET)
    if not message_ids:
        return PolicyBindingStatus.ORPHANED, _empty_candidate()
    return (
        PolicyBindingStatus.EXACT,
        _candidate_for_message_ids(
            message_ids,
            data,
            sources,
            flows,
            message_to_source,
            message_to_flow,
        ),
    )


def _nonstructural_binding(
    policy: ActivePolicy,
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_to_source: dict[str, str],
    message_to_flow: dict[str, str],
) -> PolicyBinding:
    if len(policy.anchors) != 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    status, candidate = _resolve_target_anchor(
        policy.anchors[0],
        data,
        sources,
        flows,
        message_to_source,
        message_to_flow,
    )
    return _binding(policy, status, candidate)


def _correction_field(command: PolicyDecisionCommand) -> str | None:
    if isinstance(command, SetSourceDisplayName):
        return "source_display_name"
    if isinstance(command, SetSourceRubro):
        return "source_rubro"
    if isinstance(command, SetFlowDisplayName):
        return "flow_display_name"
    if isinstance(command, SetFlowIntention):
        return "flow_intention"
    return None


def _mark_correction_conflicts(
    policies: tuple[ActivePolicy, ...],
    bindings: dict[str, PolicyBinding],
) -> None:
    conflicting: set[str] = set()
    for index, left in enumerate(policies):
        field_name = _correction_field(left.command)
        if field_name is None:
            continue
        left_binding = bindings[left.decision_id]
        for right in policies[index + 1 :]:
            if _correction_field(right.command) != field_name:
                continue
            right_binding = bindings[right.decision_id]
            if set(left_binding.affected_message_ids).intersection(
                right_binding.affected_message_ids
            ):
                conflicting.update((left.decision_id, right.decision_id))
    for decision_id in conflicting:
        bindings[decision_id] = replace(
            bindings[decision_id], status=PolicyBindingStatus.CONFLICT
        )


def _apply_nonstructural_policy(
    policy: ActivePolicy,
    binding: PolicyBinding,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_policy_evidence: dict[str, list[PolicyDecisionEvidence]],
    message_decision_ids: dict[str, set[str]],
) -> None:
    if binding.status not in {
        PolicyBindingStatus.EXACT,
        PolicyBindingStatus.REBOUND,
    }:
        return
    command = policy.command
    evidence = _policy_evidence(command)
    if isinstance(command, SetSourceDisplayName):
        source = _source_for_selector(sources, command.selector)
        if source is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        source.effective_display_name = command.display_name
        source.policy_evidence.append(evidence)
        source.decision_ids.add(command.decision_id)
    elif isinstance(command, SetSourceRubro):
        source = _source_for_selector(sources, command.selector)
        if source is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        source.effective_rubro = command.rubro
        source.policy_evidence.append(evidence)
        source.decision_ids.add(command.decision_id)
    elif isinstance(command, SetFlowDisplayName):
        flow = _flow_for_selector(flows, command.selector)
        if flow is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        flow.effective_display_name = command.display_name
        flow.policy_evidence.append(evidence)
        flow.decision_ids.add(command.decision_id)
    elif isinstance(command, SetFlowIntention):
        flow = _flow_for_selector(flows, command.selector)
        if flow is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        flow.effective_intention = command.intention
        flow.policy_evidence.append(evidence)
        flow.decision_ids.add(command.decision_id)
    elif isinstance(command, ProtectTarget):
        for message_id in binding.affected_message_ids:
            message_policy_evidence[message_id].append(evidence)
            message_decision_ids[message_id].add(command.decision_id)
    else:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)


def _automatic_protection_reasons(
    record: IndexedMessageRecord,
    message: ClassifiedMessage,
) -> set[PolicyProtectionReason]:
    labels = {label.upper() for label in record.label_ids}
    reasons = {
        reason for label, reason in _HARD_LABEL_REASONS.items() if label in labels
    }
    if "STARRED" in labels:
        reasons.add(PolicyProtectionReason.STARRED)
    if "IMPORTANT" in labels:
        reasons.add(PolicyProtectionReason.IMPORTANT)
    if message.intencion is Intencion.SEGURIDAD:
        reasons.add(PolicyProtectionReason.SECURITY)
    if message.intencion is Intencion.DOCUMENTO:
        reasons.add(PolicyProtectionReason.DOCUMENT)
    if message.intencion is Intencion.PERSONAL:
        reasons.add(PolicyProtectionReason.PERSONAL)
    if message.confianza is Confianza.BAJA:
        reasons.add(PolicyProtectionReason.LOW_CONFIDENCE)
    if message.confianza is Confianza.CONTRADICTORIA:
        reasons.add(PolicyProtectionReason.CONTRADICTION)
    return reasons


def _protection_category(reasons: set[PolicyProtectionReason]) -> Proteccion:
    if reasons.intersection(
        {PolicyProtectionReason.SECURITY, PolicyProtectionReason.PERSONAL}
    ):
        return Proteccion.CRITICA
    if PolicyProtectionReason.DOCUMENT in reasons:
        return Proteccion.DOCUMENTAL
    if reasons.intersection(
        {
            PolicyProtectionReason.SENT,
            PolicyProtectionReason.DRAFT,
            PolicyProtectionReason.TRASH,
            PolicyProtectionReason.STARRED,
            PolicyProtectionReason.IMPORTANT,
            PolicyProtectionReason.PROTECTED_LABEL,
            PolicyProtectionReason.MANUAL_POLICY,
        }
    ):
        return Proteccion.USUARIO
    if reasons:
        return Proteccion.REVISION
    return Proteccion.ORDINARIA


def _mixed_conversation_protection(
    protections: dict[str, _MessageProtection],
    data: _ValidatedInput,
    *,
    automatic: bool,
) -> None:
    by_thread: dict[str, list[str]] = defaultdict(list)
    for record in data.records:
        by_thread[record.provider_thread_id].append(record.provider_message_id)
    for message_ids in by_thread.values():
        reason_sets = (
            [protections[message_id].automatic_reasons for message_id in message_ids]
            if automatic
            else [protections[message_id].effective_reasons for message_id in message_ids]
        )
        if not any(reason_sets) or all(reason_sets):
            continue
        for message_id in message_ids:
            if automatic:
                protections[message_id].automatic_reasons.add(
                    PolicyProtectionReason.MIXED_CONVERSATION
                )
            protections[message_id].effective_reasons.add(
                PolicyProtectionReason.MIXED_CONVERSATION
            )
            protections[message_id].review_required = True


def _protection_states(
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_to_source: dict[str, str],
    message_to_flow: dict[str, str],
    bindings: dict[str, PolicyBinding],
    policies_by_id: dict[str, ActivePolicy],
    message_decision_ids: dict[str, set[str]],
) -> dict[str, _MessageProtection]:
    protections = {
        message_id: _MessageProtection(
            automatic_reasons=_automatic_protection_reasons(
                data.records_by_id[message_id], data.messages_by_id[message_id]
            )
        )
        for message_id in data.messages_by_id
    }
    for protection in protections.values():
        protection.effective_reasons.update(protection.automatic_reasons)
    _mixed_conversation_protection(protections, data, automatic=True)
    for message_id, decision_ids in message_decision_ids.items():
        if decision_ids:
            protections[message_id].effective_reasons.add(
                PolicyProtectionReason.MANUAL_POLICY
            )
            protections[message_id].decision_ids.update(decision_ids)
    for decision_id, binding in bindings.items():
        policy = policies_by_id[decision_id]
        if (
            binding.status in {PolicyBindingStatus.EXACT, PolicyBindingStatus.REBOUND}
            and isinstance(policy.command, ProtectTarget)
            and isinstance(policy.command.selector, LabelSelector)
        ):
            for message_id in binding.affected_message_ids:
                protections[message_id].effective_reasons.add(
                    PolicyProtectionReason.PROTECTED_LABEL
                )
    for flow in flows.values():
        if flow.effective_intention in {
            Intencion.SEGURIDAD,
            Intencion.DOCUMENTO,
            Intencion.PERSONAL,
        } and flow.effective_intention is not flow.automatic_intention:
            reason = {
                Intencion.SEGURIDAD: PolicyProtectionReason.SECURITY,
                Intencion.DOCUMENTO: PolicyProtectionReason.DOCUMENT,
                Intencion.PERSONAL: PolicyProtectionReason.PERSONAL,
            }[flow.effective_intention]
            for message_id in flow.message_ids:
                protections[message_id].effective_reasons.add(reason)
                protections[message_id].decision_ids.update(flow.decision_ids)
    for decision_id, binding in bindings.items():
        if binding.status in {
            PolicyBindingStatus.EXACT,
            PolicyBindingStatus.REBOUND,
            PolicyBindingStatus.ORPHANED,
        }:
            continue
        for message_id in binding.affected_message_ids:
            protections[message_id].effective_reasons.add(
                PolicyProtectionReason.POLICY_REVIEW
            )
            protections[message_id].decision_ids.add(decision_id)
            protections[message_id].review_required = True
    for message_id, protection in protections.items():
        source = sources[message_to_source[message_id]]
        flow = flows[message_to_flow[message_id]]
        protection.decision_ids.update(source.decision_ids)
        protection.decision_ids.update(flow.decision_ids)
        if data.messages_by_id[message_id].confianza in {
            Confianza.BAJA,
            Confianza.CONTRADICTORIA,
        }:
            protection.review_required = True
        if any(
            bindings[decision_id].status
            not in {PolicyBindingStatus.EXACT, PolicyBindingStatus.REBOUND}
            for decision_id in protection.decision_ids
            if decision_id in policies_by_id
        ):
            protection.review_required = True
    _mixed_conversation_protection(protections, data, automatic=False)
    return protections


def _ordered_reasons(
    values: Iterable[PolicyProtectionReason],
) -> tuple[PolicyProtectionReason, ...]:
    return tuple(sorted(set(values), key=lambda item: item.value))


def _hard_excluded(reasons: Iterable[PolicyProtectionReason]) -> bool:
    return bool(
        set(reasons).intersection(
            {
                PolicyProtectionReason.SENT,
                PolicyProtectionReason.DRAFT,
                PolicyProtectionReason.TRASH,
            }
        )
    )


def _message_outputs(
    data: _ValidatedInput,
    sources: dict[str, _SourceState],
    flows: dict[str, _FlowState],
    message_to_source: dict[str, str],
    message_to_flow: dict[str, str],
    protections: dict[str, _MessageProtection],
    message_policy_evidence: dict[str, list[PolicyDecisionEvidence]],
) -> tuple[EffectiveMessage, ...]:
    results: list[EffectiveMessage] = []
    for message_id in sorted(data.messages_by_id):
        automatic = data.messages_by_id[message_id]
        source = sources[message_to_source[message_id]]
        flow = flows[message_to_flow[message_id]]
        protection = protections[message_id]
        effective_reasons = _ordered_reasons(protection.effective_reasons)
        policy_values = _effective_evidence(
            (
                *source.policy_evidence,
                *flow.policy_evidence,
                *message_policy_evidence[message_id],
            )
        )
        decision_ids = tuple(
            sorted(
                {
                    item.decision_id
                    for item in policy_values
                    if isinstance(item, PolicyDecisionEvidence)
                }
                | protection.decision_ids
            )
        )
        results.append(
            EffectiveMessage(
                provider_message_id=message_id,
                automatic_source_id=automatic.source_id,
                effective_source_id=source.effective_source_id,
                automatic_flow_id=automatic.flow_id,
                effective_flow_id=flow.effective_flow_id,
                automatic_rubro=automatic.rubro,
                effective_rubro=source.effective_rubro,
                automatic_intention=automatic.intencion,
                effective_intention=flow.effective_intention,
                subscription=automatic.suscripcion,
                automatic_confidence=automatic.confianza,
                effective_confidence=automatic.confianza,
                automatic_protection=_protection_category(
                    protection.automatic_reasons
                ),
                effective_protection=_protection_category(
                    protection.effective_reasons
                ),
                protected=bool(effective_reasons),
                review_required=protection.review_required,
                hard_excluded=_hard_excluded(effective_reasons),
                protection_reasons=effective_reasons,
                decision_ids=decision_ids,
                automatic_evidence=automatic.evidence,
                effective_evidence=_effective_evidence(
                    (*automatic.evidence, *policy_values)
                ),
            )
        )
    return tuple(results)


def _aggregate_message_protection(
    messages: Iterable[EffectiveMessage],
) -> tuple[
    Proteccion,
    Proteccion,
    bool,
    bool,
    bool,
    tuple[PolicyProtectionReason, ...],
    tuple[str, ...],
]:
    materialized = tuple(messages)
    reasons = _ordered_reasons(
        reason for message in materialized for reason in message.protection_reasons
    )
    automatic_categories = tuple(
        message.automatic_protection for message in materialized
    )
    automatic = max(
        automatic_categories,
        key=(
            Proteccion.ORDINARIA,
            Proteccion.REVISION,
            Proteccion.USUARIO,
            Proteccion.DOCUMENTAL,
            Proteccion.CRITICA,
        ).index,
    )
    return (
        automatic,
        _protection_category(set(reasons)),
        any(message.protected for message in materialized),
        any(message.review_required for message in materialized),
        any(message.hard_excluded for message in materialized),
        reasons,
        tuple(
            sorted(
                {
                    decision_id
                    for message in materialized
                    for decision_id in message.decision_ids
                }
            )
        ),
    )


def _flow_outputs(
    flows: dict[str, _FlowState],
    messages: tuple[EffectiveMessage, ...],
) -> tuple[EffectiveFlow, ...]:
    messages_by_flow: dict[str, list[EffectiveMessage]] = defaultdict(list)
    for message in messages:
        messages_by_flow[message.effective_flow_id].append(message)
    results: list[EffectiveFlow] = []
    for effective_flow_id in sorted(flows):
        state = flows[effective_flow_id]
        members = tuple(
            sorted(
                messages_by_flow[effective_flow_id],
                key=lambda item: item.provider_message_id,
            )
        )
        (
            automatic_protection,
            effective_protection,
            protected,
            review_required,
            hard_excluded,
            reasons,
            decision_ids,
        ) = _aggregate_message_protection(members)
        policy_evidence = _effective_evidence(
            (
                *state.policy_evidence,
                *(
                    item
                    for message in members
                    for item in message.effective_evidence
                    if isinstance(item, PolicyDecisionEvidence)
                ),
            )
        )
        results.append(
            EffectiveFlow(
                effective_flow_id=effective_flow_id,
                effective_source_id=state.effective_source_id,
                selector=state.selector,
                automatic_flow_id=state.automatic_flow_id,
                automatic_display_name=state.automatic_display_name,
                effective_display_name=state.effective_display_name,
                message_ids=tuple(message.provider_message_id for message in members),
                automatic_intention=state.automatic_intention,
                effective_intention=state.effective_intention,
                subscription=state.subscription,
                automatic_confidence=state.automatic_confidence,
                effective_confidence=state.effective_confidence,
                automatic_protection=automatic_protection,
                effective_protection=effective_protection,
                protected=protected,
                review_required=review_required,
                hard_excluded=hard_excluded,
                protection_reasons=reasons,
                decision_ids=decision_ids,
                automatic_evidence=state.automatic_evidence,
                effective_evidence=_effective_evidence(
                    (*state.automatic_evidence, *policy_evidence)
                ),
                structural_decision_ids=state.structural_decision_ids,
            )
        )
    return tuple(results)


def _source_outputs(
    sources: dict[str, _SourceState],
    messages: tuple[EffectiveMessage, ...],
    flows: tuple[EffectiveFlow, ...],
) -> tuple[EffectiveSource, ...]:
    messages_by_source: dict[str, list[EffectiveMessage]] = defaultdict(list)
    flows_by_source: dict[str, list[EffectiveFlow]] = defaultdict(list)
    for message in messages:
        messages_by_source[message.effective_source_id].append(message)
    for flow in flows:
        flows_by_source[flow.effective_source_id].append(flow)
    results: list[EffectiveSource] = []
    for effective_source_id in sorted(sources):
        state = sources[effective_source_id]
        members = tuple(
            sorted(
                messages_by_source[effective_source_id],
                key=lambda item: item.provider_message_id,
            )
        )
        source_flows = tuple(
            sorted(
                flows_by_source[effective_source_id],
                key=lambda item: item.effective_flow_id,
            )
        )
        (
            automatic_protection,
            effective_protection,
            protected,
            review_required,
            hard_excluded,
            reasons,
            decision_ids,
        ) = _aggregate_message_protection(members)
        policy_evidence = _effective_evidence(
            (
                *state.policy_evidence,
                *(
                    item
                    for message in members
                    for item in message.effective_evidence
                    if isinstance(item, PolicyDecisionEvidence)
                ),
            )
        )
        results.append(
            EffectiveSource(
                effective_source_id=effective_source_id,
                selector=state.selector,
                automatic_source_ids=state.automatic_source_ids,
                automatic_display_name=state.automatic_display_name,
                effective_display_name=state.effective_display_name,
                message_ids=tuple(message.provider_message_id for message in members),
                flow_ids=tuple(flow.effective_flow_id for flow in source_flows),
                automatic_rubro=state.automatic_rubro,
                effective_rubro=state.effective_rubro,
                automatic_confidence=state.automatic_confidence,
                effective_confidence=state.effective_confidence,
                automatic_protection=automatic_protection,
                effective_protection=effective_protection,
                protected=protected,
                review_required=review_required,
                hard_excluded=hard_excluded,
                protection_reasons=reasons,
                decision_ids=decision_ids,
                automatic_evidence=state.automatic_evidence,
                effective_evidence=_effective_evidence(
                    (*state.automatic_evidence, *policy_evidence)
                ),
                structural_decision_ids=state.structural_decision_ids,
            )
        )
    return tuple(results)


def _apply_local_policies(
    data: _ValidatedInput,
) -> PolicyApplicationResult:
    sources = _baseline_sources(data)
    structural = tuple(
        policy
        for policy in data.policies
        if isinstance(policy.command, _STRUCTURAL_COMMANDS)
    )
    nonstructural = tuple(
        policy
        for policy in data.policies
        if not isinstance(policy.command, _STRUCTURAL_COMMANDS)
    )
    bindings: dict[str, PolicyBinding] = {
        policy.decision_id: _structural_binding(policy, sources, data)
        for policy in structural
    }
    _mark_structural_conflicts(structural, bindings)
    for policy in structural:
        if bindings[policy.decision_id].status not in {
            PolicyBindingStatus.EXACT,
            PolicyBindingStatus.REBOUND,
        }:
            continue
        if isinstance(policy.command, MergeSources):
            _apply_merge(policy, sources, data)
        else:
            _apply_partition(policy, sources, data)
    flows, message_to_source, message_to_flow = _build_flows(data, sources)
    for policy in nonstructural:
        bindings[policy.decision_id] = _nonstructural_binding(
            policy,
            data,
            sources,
            flows,
            message_to_source,
            message_to_flow,
        )
    _mark_correction_conflicts(nonstructural, bindings)
    message_policy_evidence: dict[str, list[PolicyDecisionEvidence]] = defaultdict(list)
    message_decision_ids: dict[str, set[str]] = defaultdict(set)
    for policy in nonstructural:
        _apply_nonstructural_policy(
            policy,
            bindings[policy.decision_id],
            sources,
            flows,
            message_policy_evidence,
            message_decision_ids,
        )
    policies_by_id = {policy.decision_id: policy for policy in data.policies}
    for decision_id, binding in bindings.items():
        if binding.status in {
            PolicyBindingStatus.EXACT,
            PolicyBindingStatus.REBOUND,
            PolicyBindingStatus.ORPHANED,
        }:
            continue
        evidence = _policy_evidence(policies_by_id[decision_id].command)
        for message_id in binding.affected_message_ids:
            message_policy_evidence[message_id].append(evidence)
            message_decision_ids[message_id].add(decision_id)
    protections = _protection_states(
        data,
        sources,
        flows,
        message_to_source,
        message_to_flow,
        bindings,
        policies_by_id,
        message_decision_ids,
    )
    message_results = _message_outputs(
        data,
        sources,
        flows,
        message_to_source,
        message_to_flow,
        protections,
        message_policy_evidence,
    )
    flow_results = _flow_outputs(flows, message_results)
    source_results = _source_outputs(sources, message_results, flow_results)
    return PolicyApplicationResult(
        account_key=data.account_key,
        messages=message_results,
        sources=source_results,
        flows=flow_results,
        bindings=tuple(bindings[decision_id] for decision_id in sorted(bindings)),
    )


def apply_local_policies(
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    policies: Iterable[ActivePolicy],
) -> PolicyApplicationResult:
    try:
        data = _validated_input(account_key, records, classification, policies)
        return _apply_local_policies(data)
    except PolicyError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None


def _supersedes_compatible(
    command: PolicyDecisionCommand,
    policy: ActivePolicy,
) -> bool:
    current = policy.command
    if isinstance(command, _STRUCTURAL_COMMANDS):
        if not isinstance(current, _STRUCTURAL_COMMANDS):
            return False
        return any(
            _source_descriptors_share_anchor(left, right)
            for left in _structural_source_descriptors(command)
            for right in _structural_source_descriptors(current)
        )
    if isinstance(command, ProtectTarget):
        return isinstance(current, ProtectTarget) and current.selector == command.selector
    if _correction_field(command) != _correction_field(current):
        return False
    command_selector = _command_target_selector(command)
    current_selector = _command_target_selector(current)
    if command_selector == current_selector:
        return True
    if isinstance(command_selector, EffectiveSourceSelector) and isinstance(
        current_selector, EffectiveSourceSelector
    ):
        return _source_selector_shares_anchor(command_selector, current_selector)
    if isinstance(command_selector, EffectiveFlowSelector) and isinstance(
        current_selector, EffectiveFlowSelector
    ):
        return _flow_descriptors_share_anchor(
            command_selector.automatic_flow, current_selector.automatic_flow
        )
    return False


def _command_target_selector(
    command: PolicyDecisionCommand,
) -> PolicyTargetSelector | None:
    if isinstance(
        command,
        (
            SetSourceDisplayName,
            SetSourceRubro,
            SetFlowDisplayName,
            SetFlowIntention,
            ProtectTarget,
        ),
    ):
        return command.selector
    return None


def _source_result_for_selector(
    result: PolicyApplicationResult,
    selector: EffectiveSourceSelector,
) -> EffectiveSource | None:
    matches = tuple(source for source in result.sources if source.selector == selector)
    if len(matches) > 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return matches[0] if matches else None


def _flow_result_for_selector(
    result: PolicyApplicationResult,
    selector: EffectiveFlowSelector,
) -> EffectiveFlow | None:
    matches = tuple(flow for flow in result.flows if flow.selector == selector)
    if len(matches) > 1:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)
    return matches[0] if matches else None


def _observed_ids_for_messages(
    message_ids: Iterable[str],
    data: _ValidatedInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    materialized = tuple(message_ids)
    return (
        tuple(
            sorted(
                {data.messages_by_id[message_id].source_id for message_id in materialized}
            )
        ),
        tuple(
            sorted(
                {data.messages_by_id[message_id].flow_id for message_id in materialized}
            )
        ),
    )


def _prepared_source_anchor(
    *,
    anchor_order: int,
    role: PolicyAnchorRole,
    source: EffectiveSource,
    classification_version: int,
    data: _ValidatedInput,
) -> PreparedPolicyAnchor:
    observed_source_ids, observed_flow_ids = _observed_ids_for_messages(
        source.message_ids,
        data,
    )
    return PreparedPolicyAnchor(
        anchor_order=anchor_order,
        role=role,
        selector=source.selector,
        classification_version=classification_version,
        observed_effective_id=source.effective_source_id,
        observed_source_ids=observed_source_ids,
        observed_flow_ids=observed_flow_ids,
        structural_decision_ids=source.structural_decision_ids,
    )


def _prepared_flow_anchor(
    *,
    anchor_order: int,
    role: PolicyAnchorRole,
    flow: EffectiveFlow,
    classification_version: int,
    data: _ValidatedInput,
) -> PreparedPolicyAnchor:
    observed_source_ids, observed_flow_ids = _observed_ids_for_messages(
        flow.message_ids, data
    )
    return PreparedPolicyAnchor(
        anchor_order=anchor_order,
        role=role,
        selector=flow.selector,
        classification_version=classification_version,
        observed_effective_id=flow.effective_flow_id,
        observed_source_ids=observed_source_ids,
        observed_flow_ids=observed_flow_ids,
        structural_decision_ids=flow.structural_decision_ids,
    )


def _direct_target_messages(
    selector: PolicyTargetSelector,
    data: _ValidatedInput,
    result: PolicyApplicationResult,
) -> tuple[EffectiveMessage, ...]:
    by_id = {message.provider_message_id: message for message in result.messages}
    if isinstance(selector, MessageSelector):
        message = by_id.get(selector.provider_message_id)
        return (message,) if message is not None else ()
    if isinstance(selector, SenderSelector):
        ids = tuple(
            message_id
            for message_id in data.records_by_id
            if _canonical_sender_for_message(message_id, data)
            == selector.sender_address
        )
    elif isinstance(selector, LabelSelector):
        ids = tuple(
            record.provider_message_id
            for record in data.records
            if selector.label_id in record.label_ids
        )
    else:
        raise PolicyError(PolicyErrorCode.UNSUPPORTED_TARGET)
    return tuple(by_id[message_id] for message_id in ids)


def _prepared_direct_anchor(
    *,
    selector: MessageSelector | SenderSelector | LabelSelector,
    messages: tuple[EffectiveMessage, ...],
    classification_version: int,
    data: _ValidatedInput,
) -> PreparedPolicyAnchor:
    observed_source_ids, observed_flow_ids = _observed_ids_for_messages(
        (message.provider_message_id for message in messages), data
    )
    return PreparedPolicyAnchor(
        anchor_order=0,
        role=PolicyAnchorRole.TARGET,
        selector=selector,
        classification_version=classification_version,
        observed_source_ids=observed_source_ids,
        observed_flow_ids=observed_flow_ids,
        structural_decision_ids=(),
    )


def _prepared_relations(
    command: PolicyDecisionCommand,
    anchors: tuple[PreparedPolicyAnchor, ...],
) -> tuple[PreparedPolicyRelation, ...]:
    values: list[PreparedPolicyRelation] = []
    for decision_id in command.supersedes_decision_ids:
        values.append(
            PreparedPolicyRelation(
                relation_order=len(values),
                kind=PolicyRelationKind.SUPERSEDES,
                target_decision_id=decision_id,
            )
        )
    for anchor in anchors:
        for decision_id in anchor.structural_decision_ids:
            values.append(
                PreparedPolicyRelation(
                    relation_order=len(values),
                    kind=PolicyRelationKind.STRUCTURAL_CONTEXT,
                    target_decision_id=decision_id,
                    anchor_order=anchor.anchor_order,
                )
            )
    return tuple(values)


def _reject_remaining_conflicts(
    command: PolicyDecisionCommand,
    remaining: tuple[ActivePolicy, ...],
    result: PolicyApplicationResult,
    target_effective_ids: tuple[str, ...],
) -> None:
    bindings = {binding.decision_id: binding for binding in result.bindings}
    if isinstance(command, _STRUCTURAL_COMMANDS):
        descriptors = _structural_source_descriptors(command)
        if any(
            any(
                _source_descriptors_share_anchor(left, right)
                for left in descriptors
                for right in _structural_source_descriptors(policy.command)
            )
            or set(bindings[policy.decision_id].current_effective_ids).intersection(
                target_effective_ids
            )
            for policy in remaining
            if isinstance(policy.command, _STRUCTURAL_COMMANDS)
        ):
            raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
        return
    field_name = _correction_field(command)
    if field_name is None:
        return
    if any(
        _correction_field(policy.command) == field_name
        and set(bindings[policy.decision_id].current_effective_ids).intersection(
            target_effective_ids
        )
        for policy in remaining
    ):
        raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)


def _prepare_policy_decision(
    data: _ValidatedInput,
    command: PolicyDecisionCommand,
) -> PreparedPolicyDecision:
    policies_by_id = {policy.decision_id: policy for policy in data.policies}
    superseded: list[ActivePolicy] = []
    for decision_id in command.supersedes_decision_ids:
        policy = policies_by_id.get(decision_id)
        if policy is None or not _supersedes_compatible(command, policy):
            raise PolicyError(PolicyErrorCode.POLICY_CONFLICT)
        superseded.append(policy)
    superseded_ids = {policy.decision_id for policy in superseded}
    remaining = tuple(
        policy for policy in data.policies if policy.decision_id not in superseded_ids
    )
    view_data = replace(data, policies=remaining)
    result = _apply_local_policies(view_data)
    classification_version = data.classification.version
    anchors: tuple[PreparedPolicyAnchor, ...]
    target_effective_ids: tuple[str, ...] = ()

    if isinstance(command, (SetSourceDisplayName, SetSourceRubro)):
        source = _source_result_for_selector(result, command.selector)
        if source is None:
            raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
        anchors = (
            _prepared_source_anchor(
                anchor_order=0,
                role=PolicyAnchorRole.TARGET,
                source=source,
                classification_version=classification_version,
                data=data,
            ),
        )
        target_effective_ids = (source.effective_source_id,)
    elif isinstance(command, (SetFlowDisplayName, SetFlowIntention)):
        flow = _flow_result_for_selector(result, command.selector)
        if flow is None:
            raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
        anchors = (
            _prepared_flow_anchor(
                anchor_order=0,
                role=PolicyAnchorRole.TARGET,
                flow=flow,
                classification_version=classification_version,
                data=data,
            ),
        )
        target_effective_ids = (flow.effective_flow_id,)
    elif isinstance(command, MergeSources):
        sources = tuple(
            _source_result_for_selector(result, selector)
            for selector in command.source_selectors
        )
        if any(source is None for source in sources):
            _reject_remaining_conflicts(command, remaining, result, ())
            raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
        resolved_sources = tuple(source for source in sources if source is not None)
        anchors = tuple(
            _prepared_source_anchor(
                anchor_order=index,
                role=PolicyAnchorRole.MERGE_PARTICIPANT,
                source=source,
                classification_version=classification_version,
                data=data,
            )
            for index, source in enumerate(resolved_sources)
        )
        target_effective_ids = tuple(
            source.effective_source_id for source in resolved_sources
        )
    elif isinstance(command, PartitionSource):
        source = _source_result_for_selector(result, command.source_selector)
        if source is None:
            _reject_remaining_conflicts(command, remaining, result, ())
            raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
        if any(
            not _message_partition_anchor_is_fallback(anchor, data)
            for group in command.groups
            for anchor in group.anchors
        ):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        resolved_groups = _partition_groups(
            tuple(tuple(group.anchors) for group in command.groups),
            source.message_ids,
            data,
        )
        if resolved_groups is None:
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        values: list[PreparedPolicyAnchor] = [
            _prepared_source_anchor(
                anchor_order=0,
                role=PolicyAnchorRole.TARGET,
                source=source,
                classification_version=classification_version,
                data=data,
            )
        ]
        for group_order, (group, message_ids) in enumerate(
            zip(command.groups, resolved_groups, strict=True)
        ):
            for anchor in group.anchors:
                matched_ids = _partition_anchor_message_ids(
                    anchor, message_ids, data
                )
                if not matched_ids:
                    raise PolicyError(PolicyErrorCode.INVALID_INPUT)
                observed_source_ids, observed_flow_ids = _observed_ids_for_messages(
                    matched_ids, data
                )
                values.append(
                    PreparedPolicyAnchor(
                        anchor_order=len(values),
                        role=PolicyAnchorRole.PARTITION_MEMBER,
                        selector=anchor,
                        group_order=group_order,
                        classification_version=classification_version,
                        observed_source_ids=observed_source_ids,
                        observed_flow_ids=observed_flow_ids,
                    )
                )
        anchors = tuple(values)
        target_effective_ids = (source.effective_source_id,)
    elif isinstance(command, ProtectTarget):
        if isinstance(command.selector, EffectiveSourceSelector):
            source = _source_result_for_selector(result, command.selector)
            if source is None:
                raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
            anchors = (
                _prepared_source_anchor(
                    anchor_order=0,
                    role=PolicyAnchorRole.TARGET,
                    source=source,
                    classification_version=classification_version,
                    data=data,
                ),
            )
            target_effective_ids = (source.effective_source_id,)
        elif isinstance(command.selector, EffectiveFlowSelector):
            flow = _flow_result_for_selector(result, command.selector)
            if flow is None:
                raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
            anchors = (
                _prepared_flow_anchor(
                    anchor_order=0,
                    role=PolicyAnchorRole.TARGET,
                    flow=flow,
                    classification_version=classification_version,
                    data=data,
                ),
            )
            target_effective_ids = (flow.effective_flow_id,)
        else:
            messages = _direct_target_messages(command.selector, data, result)
            if not messages:
                raise PolicyError(PolicyErrorCode.TARGET_NOT_FOUND)
            if not isinstance(
                command.selector, (MessageSelector, SenderSelector, LabelSelector)
            ):
                raise PolicyError(PolicyErrorCode.UNSUPPORTED_TARGET)
            anchors = (
                _prepared_direct_anchor(
                    selector=command.selector,
                    messages=messages,
                    classification_version=classification_version,
                    data=data,
                ),
            )
            target_effective_ids = tuple(
                sorted(
                    {
                        message.effective_source_id
                        for message in messages
                    }
                    | {message.effective_flow_id for message in messages}
                )
            )
    else:
        raise PolicyError(PolicyErrorCode.INVALID_INPUT)

    _reject_remaining_conflicts(
        command, remaining, result, target_effective_ids
    )
    relations = _prepared_relations(command, anchors)
    return PreparedPolicyDecision(
        command=command,
        anchors=anchors,
        relations=relations,
    )


def prepare_policy_decision(
    *,
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    active_policies: Iterable[ActivePolicy],
    command: PolicyDecisionCommand,
) -> PreparedPolicyDecision:
    try:
        if not is_policy_decision_command(command):
            raise PolicyError(PolicyErrorCode.INVALID_INPUT)
        data = _validated_input(
            account_key,
            records,
            classification,
            active_policies,
        )
        if command.account_key != data.account_key:
            raise PolicyError(PolicyErrorCode.MIXED_ACCOUNTS)
        return _prepare_policy_decision(data, command)
    except PolicyError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        raise PolicyError(PolicyErrorCode.INVALID_INPUT) from None
